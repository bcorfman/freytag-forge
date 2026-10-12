# Agent workflow guide

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
