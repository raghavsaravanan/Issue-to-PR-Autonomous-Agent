"""
The verification gate - the agent is not allowed to open a PR unless the
tests actually pass on its candidate branch. Generalized to run whatever
test command a given issue needs (a bare script or a pytest suite), with a
hard wall-clock timeout so a hung/infinite-loop bug can't hang the agent.
"""

import subprocess


def run_tests(repo_path: str, test_cmd: list[str], timeout: int = 60) -> tuple[bool, str]:
    """Run the test command. Returns (passed, output) - output is empty on success."""
    try:
        result = subprocess.run(
            test_cmd, cwd=repo_path, capture_output=True, text=True, timeout=timeout,
        )
    except subprocess.TimeoutExpired:
        return False, f"Test run timed out after {timeout}s (possible infinite loop)."

    if result.returncode != 0:
        return False, (result.stdout + "\n" + result.stderr).strip()
    return True, ""


def rollback(repo_path: str, branch_name: str) -> None:
    """Abandon a failed candidate fix: back to main, delete the branch."""
    subprocess.run(["git", "checkout", "main"], cwd=repo_path, check=True)
    subprocess.run(["git", "branch", "-D", branch_name], cwd=repo_path, check=True)
