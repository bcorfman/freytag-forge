# Design and verification

Part of [the contributor guide](../contributor-guide.md).

## Design and verification

- Use typed contracts, explicit Protocols/adapters, and constructor-injected
  dependencies. Validate at boundaries; avoid attribute probes, hidden
  instantiation, circular dependencies, and silent exception handling.
- Keep modules near 500 lines and functions near 20 cyclomatic complexity;
  split only when clarity improves.
- Write tests first, add cross-genre regression coverage, maintain at least 90%
  project coverage, and keep collection totals informational rather than gates.
- Run tests with `TMPDIR=/tmp` in WSL, use `uv run python`, and finish every
  feature change with Ruff autofix and formatting before rerunning affected
  verification.
