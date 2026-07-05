# Issue-to-PR Autonomous Agent

Label a GitHub issue, get a review-ready pull request back. A self-hosted
version of the "async cloud coding agent" product category — the same shape
as Cursor Background Agents, GitHub Copilot's coding agent, and Google Jules.

```
issue labeled "agent-fix-this"
            |
            v
  GitHub Actions trigger (Testing repo)
            |
            v  (reusable workflow call)
  Agent Core (this repo)
            |
            v
  read issue + buggy file  ->  ask Gemini to fix it
            |
            v
  commit candidate fix to agent/fix-issue-N branch
            |
            v
  run the real test suite, with a hard timeout   <-- verification gate
            |
       fail |  pass
            |    |
   feed failure  push branch + open PR
   back to Gemini,      (rationale, diff summary,
   retry (max 3x)         linked to the issue)
            |
       still failing?
            |
   roll back branch, no PR opens
```

## What's actually automated vs. manual

Being precise about this matters more than it sounds:

- **Fully automated:** the trigger. Labeling an issue in the `Testing` repo
  fires a GitHub Actions workflow immediately, no human involved.
- **Manual right now:** the worker. `agent/propose_fix.py` runs on a local
  machine, not inside the Actions job itself. Wiring the worker to run
  unattended inside CI (parameterizing file paths, GitHub Actions secrets,
  cross-repo checkout) is real infra work, called out below as a next step
  rather than glossed over.

## Why this architecture, not the "textbook" cloud one

The canonical version of this product (AWS Remote SWE Agents, Cursor
Background Agents) uses AWS Lambda + ECS Fargate + a paid cloud sandbox
(Daytona/E2B). Those are legitimate architectures, but for this build the
same properties are available for free and with less operational overhead:

| Piece | Textbook choice | This build | Why |
|---|---|---|---|
| Trigger + compute | AWS Lambda + ECS Fargate | GitHub Actions | Actions is a documented valid alternative to Fargate; free, no cloud account |
| Sandbox | Daytona / E2B | The Actions runner itself | Already an isolated, ephemeral VM |
| Agent loop | SWE-agent v2 / mini-swe-agent | Hand-written loop over the Gemini API | Same read -> propose -> apply -> test shape, but every piece is understood, not a black box |
| Verification | Full CI + coverage delta | pytest run in-process, with a hard wall-clock timeout | Same gating principle: no PR without proof |

## Safety guardrails

- **Never force-pushes.** `assert_never_force_push` raises immediately if a
  `--force`/`-f` git argument is ever passed, and GitHub branch protection
  on `Testing`'s `main` independently rejects force-pushes and branch
  deletion at the server level — defense in depth, not just app-side trust.
- **Daily budget cap.** `safety.py` tracks PRs opened per repo per day in a
  local ledger and refuses to run once the cap is hit.
- **Bounded retries.** Up to 3 attempts per issue, each retry seeded with
  the actual test failure output, then a rollback (no PR) rather than an
  infinite loop of attempts.
- **Timeout on verification.** Test runs are killed after 60s. Found this
  was necessary the hard way: one target file had a binary-search bug that
  could infinite-loop on certain inputs.

## Results

| Issue | Bug | Attempts to pass | Result |
|---|---|---|---|
| [#1](https://github.com/raghavsaravanan/Testing/issues/1) | Off-by-one in a loop bound | 1/3 | [PR #2](https://github.com/raghavsaravanan/Testing/pull/2) — merged |
| [#3](https://github.com/raghavsaravanan/Testing/issues/3) | 15+ deliberate bugs in a threaded task scheduler (races, deadlock, broken singleton, bad memoization, recursion, resource/memory leaks, sorting, binary search) | 1/3 | [PR #4](https://github.com/raghavsaravanan/Testing/pull/4) — open |

PR #4's fix was verified by re-running the test suite 5 additional times
after the fact (concurrency bugs can pass by luck once) — passed all 5,
including the thread-race and deadlock tests.

Cost per run: effectively $0 — Gemini 2.5 Flash's free tier (no card on
file) comfortably covers a demo at this scale.

## Stack

- Trigger: GitHub Actions (`Testing` repo) calling a reusable workflow
  (`Issue-to-PR-Autonomous-Agent` repo)
- Agent: Google Gemini 2.5 Flash via the `google-genai` SDK
- Verification: `pytest` (or the repo's own script) with a subprocess timeout
- PR creation: GitHub CLI (`gh`)
- Safety: local JSON budget ledger, branch-protection API, force-push guard

## Repo layout

- `agent/read_context.py` — fetch the issue + the buggy file
- `agent/propose_fix.py` — the main loop: propose, verify, retry, dispatch
- `agent/verify.py` — run the test command with a timeout; rollback on failure
- `agent/open_pr.py` — push the branch, open the PR with rationale + diff stat
- `agent/safety.py` — budget ledger + force-push guard
- `.github/workflows/agent.yml` — the reusable workflow (`workflow_call`)

## Running it

```
python3 agent/propose_fix.py <issue_number>
```

Requires `GEMINI_API_KEY` in the environment and `gh` authenticated with
repo access. `ISSUE_CONFIG` in `propose_fix.py` maps an issue number to its
target file and test command.

## Known limitations / next steps

- Worker runs locally, not inside the Actions job (see above).
- No coverage-delta gate or `needs-review` partial-pass labeling yet.
- Single target repo, no per-repo dispatcher across many repos.
- No trace/observability archive (e.g. Langfuse) linked from the PR body.
- No head-to-head cost/quality comparison against Cursor Background Agents
  or similar hosted tools yet.
