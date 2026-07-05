"""
Step 5: close the loop - push the verified branch and open a PR,
with the agent's rationale in the body.
"""

import subprocess
from safety import assert_never_force_push


def push_branch(repo_path: str, branch_name: str) -> None:
    """Push the candidate branch to GitHub."""
    args = ["git", "push", "-u", "origin", branch_name]
    assert_never_force_push(args)
    subprocess.run(args, cwd=repo_path, check=True)


def get_diff_summary(repo_path: str, branch_name: str, base_branch: str = "main") -> str:
    """Get a short stat summary of what changed vs main."""
    result = subprocess.run(
        ["git", "diff", "--stat", f"{base_branch}...{branch_name}"],
        cwd=repo_path, capture_output=True, text=True, check=True,
    )
    return result.stdout.strip()


def open_pr(repo_path: str, repo: str, branch_name: str, issue_number: int,
            rationale: str, diff_summary: str) -> str:
    """Open a PR via the GitHub CLI. Returns the PR URL."""
    body = f"""Fixes #{issue_number}

**Rationale:**
{rationale}

**Diff summary:**
{diff_summary}

_Opened automatically by the issue-to-PR agent._
"""
    result = subprocess.run(
        ["gh", "pr", "create",
         "--repo", repo,
         "--head", branch_name,
         "--base", "main",
         "--title", f"Agent fix for #{issue_number}",
         "--body", body],
        cwd=repo_path, capture_output=True, text=True, check=True,
    )
    return result.stdout.strip()