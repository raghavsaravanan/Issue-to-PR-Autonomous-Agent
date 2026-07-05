"""
Step 2: gather the "input package" the AI will read -
the GitHub issue text, plus the buggy code it's about.
"""

import json
import subprocess


def get_issue(repo: str, issue_number: int) -> dict:
    """Fetch an issue's title and body using the GitHub CLI."""
    result = subprocess.run(
        ["gh", "issue", "view", str(issue_number), "--repo", repo, "--json", "title,body"],
        capture_output=True, text=True, check=True,
    )
    return json.loads(result.stdout)


def get_file_contents(local_repo_path: str, file_path: str) -> str:
    """Read a source file from the target repo's local clone."""
    full_path = f"{local_repo_path}/{file_path}"
    with open(full_path, "r") as f:
        return f.read()


if __name__ == "__main__":
    issue = get_issue("raghavsaravanan/Testing", 1)
    code = get_file_contents("/Users/raghav.s18/Documents/Projects/Testing", "main.py")

    print("=== ISSUE ===")
    print(f"Title: {issue['title']}")
    print(f"Body: {issue['body']}")
    print("\n=== CODE (main.py) ===")
    print(code)