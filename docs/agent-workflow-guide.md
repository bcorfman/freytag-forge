# Agent workflow guide

## Ownership

The repository has one maintainer, the owner.

| Responsibility | Who |
| --- | --- |
| Accepts a change | The owner. Their merge word for that PR is the human approval, at every [risk tier](../REVIEW.md#risk-tiers). An earlier word does not cover a later PR. |
| Promotes to production | The owner, by dispatching the promotion workflow or asking for it. |
| Owns rollback | The owner, using the [rollback procedure](railway-production-promotion.md#rollback). |

One exception to the merge word: the dark factory may merge a PR it generated
from a repair ticket once its free gates and CI pass and the ticket has a
passing fun review. This does not cover hand-built changes, including changes
to the factory itself, and it covers neither promotion nor rollback.

GitHub does not enforce any of this: the `main` ruleset only blocks deletion and
non-fast-forward pushes, and an author cannot approve their own PR. Risk tiers
and the `fresh-review` status are advisory.

The weekly "review outcomes" workflow reports review and promotion history
(`uv run python scripts/review_outcomes.py`). Collect that data before reducing
any review requirement.

## Working rules

- Verify CLI, environment, CI, and endpoint behavior in source, help,
  configuration, or workflows before relying on it.
- When a verification procedure changes, update its existing entry in
  [the testing runbook](testing-runbook.md) in place; add an entry only for a
  new verification boundary.
- Keep the testing runbook short; record outcomes in the plan, PR, or commit,
  not as dated observations, test counts, coverage figures, or diagnosis logs.
- Use `TMPDIR=/tmp` for pytest and `uv run python` rather than `python`.
- Never pin test collection counts.
- Update the active `.plans/` plan as soon as a feature is complete and tested,
  before starting the next one. Record the commit, verification result, and
  untested work; refresh its status and “Resume here” section.
- For staging-verified changes, merge the implementation PR and wait for the
  SHA-bound `main` CI staging deployment to succeed before staged E2E tests.
  Record the E2E result in the plan or PR. If the procedure changed, update
  its runbook entry in a final documentation-only commit; do not rerun deploy
  or E2E for that commit.
- Ringer kills checks after 60 seconds by default, while manifest `timeout_s`
  covers only the worker. Raise the check limit for full-suite, replay, or
  build checks; use task `"check_timeout_s": 900` or
  `RINGER_CHECK_TIMEOUT_S=900`, after confirming the installed `ringer.py`
  provides `check_timeout_for`.
- The Ringer check convention is a manifest check running
  `scripts/quick_suite.py` (with `--also` for journeys or heavy files relevant
  to the change) plus Ruff; the full suite runs in CI and before merge.
- A worker's own verification uses the quick tier and runs the full suite at
  most once, at the end.
