"""
Step 4: the verification gate - the agent is not allowed to open a PR
unless the tests actually pass on its candidate branch.
"""

import subprocess

TARGET_FILE = "main.py"


def run_tests(repo_path: str) -> bool:
    """Run the target repo's test file. Return True if it passes."""
    result = subprocess.run(
        ["python3", TARGET_FILE],
        cwd=repo_path,
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        print("=== TEST FAILURE OUTPUT ===")
        print(result.stderr)
        return False
    return True


def rollback(repo_path: str, branch_name: str) -> None:
    """Abandon a failed candidate fix: back to main, delete the branch."""
    subprocess.run(["git", "checkout", "main"], cwd=repo_path, check=True)
    subprocess.run(["git", "branch", "-D", branch_name], cwd=repo_path, check=True)