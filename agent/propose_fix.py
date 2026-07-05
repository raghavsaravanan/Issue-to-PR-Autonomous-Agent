"""
Step 3: the agent's brain - feed AI Agent the issue + the buggy code,
get back a fixed version and a plain-English rationale.
"""

import os
import subprocess
from google import genai
from read_context import get_issue, get_file_contents

TESTING_REPO_PATH = "/Users/raghav.s18/Documents/Projects/Testing"
TARGET_FILE = "main.py"

client = genai.Client(api_key=os.environ["GEMINI_API_KEY"])


def propose_fix(issue_title: str, issue_body: str, code: str) -> tuple[str, str]:
    """Ask AI Agent to fix the bug. Returns (fixed_code, rationale)."""
    prompt = f"""You are fixing a bug in a Python file based on a GitHub issue.

ISSUE TITLE: {issue_title}
ISSUE BODY: {issue_body}

CURRENT FILE CONTENTS:
```python
{code}

Fix the bug. Respond in exactly this format, with no other text:

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
    fixed_code = text.split("===FIXED_CODE===")[1].split("===RATIONALE===")[0].strip()
    rationale = text.split("===RATIONALE===")[1].strip()
    return fixed_code, rationale


def apply_fix_to_branch(fixed_code: str, branch_name: str) -> None:
    """Create a new branch in the target repo and write the fix to it."""
    subprocess.run(["git", "checkout", "-b", branch_name], cwd=TESTING_REPO_PATH, check=True)
    with open(f"{TESTING_REPO_PATH}/{TARGET_FILE}", "w") as f:
        f.write(fixed_code + "\n")
    subprocess.run(["git", "add", TARGET_FILE], cwd=TESTING_REPO_PATH, check=True)
    subprocess.run(["git", "commit", "-m", "Agent: candidate fix"], cwd=TESTING_REPO_PATH, check=True)


if __name__ == "__main__":
    issue = get_issue("raghavsaravanan/Testing", 1)
    code = get_file_contents(TESTING_REPO_PATH, TARGET_FILE)

    fixed_code, rationale = propose_fix(issue["title"], issue["body"], code)

    print("=== RATIONALE ===")
    print(rationale)
    print("\n=== FIXED CODE ===")
    print(fixed_code)

    apply_fix_to_branch(fixed_code, "agent/fix-issue-1")
    print("\nCommitted fix to branch 'agent/fix-issue-1' in the Testing repo.")