# Test-suite guide

The suite covers the V2 compiler, runtime, persistence, hosted adapter,
deployment channel contract, and staging evaluator. Every test receives exactly
one tier through `tests/conftest.py`; collection fails for duplicate test names
or conflicting tiers. Collection totals are informational and never pinned.

| Tier | Scope |
| --- | --- |
| unit | Compiled-story contracts, runtime state, validation, pacing, and cutover guards |
| component | The Cloudflare turn-model transport boundary |
| integration | Hosted V2 session, persistence, CORS/quota, and deployed browser contracts |
| evaluation | SHA-bound staging-evaluation report construction |

Run the required local suite with:

```text
TMPDIR=/tmp uv run pytest -q
```

The full CI coverage gate runs the complete suite with two workers and enforces
90% project coverage. A successful `main` run deploys staging, verifies browser
E2E, produces the staging evaluation artifact, and records the staged SHA.
Production promotion is a separate manual workflow and repeats root browser
E2E. Use `--tier-report=/tmp/health.json` for a machine-readable timing and
construction report.
