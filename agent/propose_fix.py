"""
The agent's brain - feed Gemini the issue + the buggy code, get back a fix,
verify it, and retry with the failure feedback a few times before giving up.
"""

import os
import sys
import subprocess
from google import genai
from read_context import get_issue, get_file_contents
from verify import run_tests, rollback
from open_pr import push_branch, get_diff_summary, open_pr
from safety import check_budget, record_pr

TESTING_REPO_PATH = "/Users/raghav.s18/Documents/Projects/Testing"
REPO = "raghavsaravanan/Testing"
MAX_ATTEMPTS = 3

# Per-issue: which file the bug lives in, and how to verify a fix.
ISSUE_CONFIG = {
    1: {
        "target_file": "main.py",
        "test_cmd": ["python3", "main.py"],
    },
    3: {
        "target_file": "test2.py",
        "test_cmd": ["python3", "-m", "pytest", "test_test2.py", "-q"],
    },
}

client = genai.Client(api_key=os.environ["GEMINI_API_KEY"])


def strip_code_fence(text: str) -> str:
    """Remove a leading/trailing ``` fence if the model added one despite instructions."""
    text = text.strip()
    if text.startswith("```"):
        text = text.split("\n", 1)[1]
    if text.endswith("```"):
        text = text.rsplit("```", 1)[0]
    return text.strip()


def propose_fix(issue_title: str, issue_body: str, code: str,
                 previous_code: str = None, previous_failure: str = None) -> tuple[str, str]:
    """Ask Gemini to fix the bug(s). Returns (fixed_code, rationale)."""
    retry_context = ""
    if previous_code and previous_failure:
        retry_context = f"""

Your previous attempt did not pass verification.

Previous attempt:
```python
{previous_code}
```

Test failure output:
{previous_failure}

Fix the remaining problem(s) shown above.
"""

    prompt = f"""You are fixing bug(s) in a Python file based on a GitHub issue.

ISSUE TITLE: {issue_title}
ISSUE BODY: {issue_body}

CURRENT FILE CONTENTS:
```python
{code}
```
{retry_context}
Fix the bug(s). Respond in exactly this format, with no other text:

===FIXED_CODE===
<the complete corrected file, nothing else>
===RATIONALE===
<one short paragraph explaining what was wrong and what you changed>
"""
    response = client.models.generate_content(
        model="gemini-2.5-flash",
        contents=prompt,
    )
    text = response.text
    fixed_code = strip_code_fence(text.split("===FIXED_CODE===")[1].split("===RATIONALE===")[0])
    rationale = text.split("===RATIONALE===")[1].strip()
    return fixed_code, rationale


def apply_fix_to_branch(fixed_code: str, branch_name: str, target_file: str, attempt: int) -> None:
    """Write the candidate fix to the agent's branch, creating it on the first attempt."""
    existing = subprocess.run(
        ["git", "branch", "--list", branch_name],
        cwd=TESTING_REPO_PATH, capture_output=True, text=True, check=True,
    )
    if existing.stdout.strip():
        subprocess.run(["git", "checkout", branch_name], cwd=TESTING_REPO_PATH, check=True)
    else:
        subprocess.run(["git", "checkout", "-b", branch_name], cwd=TESTING_REPO_PATH, check=True)

    with open(f"{TESTING_REPO_PATH}/{target_file}", "w") as f:
        f.write(fixed_code + "\n")
    subprocess.run(["git", "add", target_file], cwd=TESTING_REPO_PATH, check=True)
    subprocess.run(
        ["git", "commit", "-m", f"Agent: candidate fix (attempt {attempt})"],
        cwd=TESTING_REPO_PATH, check=True,
    )


def run_agent(issue_number: int) -> None:
    config = ISSUE_CONFIG[issue_number]
    target_file = config["target_file"]
    test_cmd = config["test_cmd"]
    branch_name = f"agent/fix-issue-{issue_number}"

    allowed, reason = check_budget(REPO)
    if not allowed:
        print(f"BUDGET CHECK FAILED: {reason}")
        raise SystemExit(1)

    issue = get_issue(REPO, issue_number)
    code = get_file_contents(TESTING_REPO_PATH, target_file)

    previous_code = None
    previous_failure = None
    fixed_code = None
    rationale = None
    passed = False
    output = ""

    for attempt in range(1, MAX_ATTEMPTS + 1):
        print(f"\n--- Attempt {attempt}/{MAX_ATTEMPTS} ---")
        fixed_code, rationale = propose_fix(
            issue["title"], issue["body"], code, previous_code, previous_failure,
        )
        print("=== RATIONALE ===")
        print(rationale)

        apply_fix_to_branch(fixed_code, branch_name, target_file, attempt)
        passed, output = run_tests(TESTING_REPO_PATH, test_cmd)

        if passed:
            print(f"\nVERIFICATION PASSED on attempt {attempt}.")
            break

        print(f"\nVERIFICATION FAILED on attempt {attempt}:")
        print(output)
        previous_code = fixed_code
        previous_failure = output

    if not passed:
        print(f"\nGiving up after {MAX_ATTEMPTS} attempts - rolling back branch '{branch_name}'. No PR will be opened.")
        rollback(TESTING_REPO_PATH, branch_name)
        return

    push_branch(TESTING_REPO_PATH, branch_name)
    diff_summary = get_diff_summary(TESTING_REPO_PATH, branch_name)
    pr_url = open_pr(TESTING_REPO_PATH, REPO, branch_name, issue_number, rationale, diff_summary)
    print(f"\nPR opened: {pr_url}")
    record_pr(REPO)


if __name__ == "__main__":
    issue_number_arg = int(sys.argv[1]) if len(sys.argv) > 1 else 1
    run_agent(issue_number_arg)
