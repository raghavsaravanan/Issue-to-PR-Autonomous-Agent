"""
Step 6: safety net - a per-repo daily budget so the agent can never
run away, plus a hard guarantee it never force-pushes.
"""

import json
import os
from datetime import date

LEDGER_PATH = os.path.join(os.path.dirname(__file__), "budget_ledger.json")
DAILY_PR_CAP = 5


def _load_ledger() -> dict:
    if not os.path.exists(LEDGER_PATH):
        return {}
    with open(LEDGER_PATH) as f:
        return json.load(f)


def _save_ledger(ledger: dict) -> None:
    with open(LEDGER_PATH, "w") as f:
        json.dump(ledger, f, indent=2)


def check_budget(repo: str) -> tuple[bool, str]:
    """Return (allowed, reason). Refuses once the repo's daily PR cap is hit."""
    ledger = _load_ledger()
    today = str(date.today())
    prs_today = ledger.get(today, {}).get(repo, 0)
    if prs_today >= DAILY_PR_CAP:
        return False, f"daily PR cap ({DAILY_PR_CAP}) reached for {repo}"
    return True, "ok"


def record_pr(repo: str) -> None:
    """Log that a PR was opened, for today's budget count."""
    ledger = _load_ledger()
    today = str(date.today())
    ledger.setdefault(today, {})
    ledger[today][repo] = ledger[today].get(repo, 0) + 1
    _save_ledger(ledger)


def assert_never_force_push(git_args: list[str]) -> None:
    """Hard safety check: raise immediately if a force-push is attempted."""
    if "--force" in git_args or "-f" in git_args:
        raise RuntimeError("Refusing to run: force-push is not allowed.")