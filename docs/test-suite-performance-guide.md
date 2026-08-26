# Test-suite guide

The suite covers authoring, the fact-backed runtime, persistence, Cloudflare
transport, hosted behavior, and deployment-channel isolation. `tests/conftest.py`,
`pyproject.toml`, and workflow YAML are the executable sources of truth.

## Classification

Every test receives one performance tier (`unit`, `component`, `integration`,
or `evaluation`) and one quality class (`runtime_safety` or
`authoring_quality`). Explicit boundary-heavy paths receive their configured
classification; unlisted tests default to `unit` and `runtime_safety`.
Collection rejects duplicate `test_*` function definitions. Counts are
informational, never a fixed quality gate.

Use `--strict-test-budgets` for optional budget enforcement and
`--tier-report=PATH` for timing/classification evidence. Keep fixtures immutable
or freshly cloned, and test recovery through injected transports.

## Commands

WSL test captures must use Linux temporary storage:

```text
TMPDIR=/tmp uv run pytest -q
TMPDIR=/tmp uv run pytest -q --no-cov -m authoring_quality
TMPDIR=/tmp uv run pytest -q --no-cov -m "unit or component"
TMPDIR=/tmp uv run pytest tests/test_conversation_quality_phase8.py -q --no-cov
TMPDIR=/tmp uv run pytest -q --no-cov --collect-only
TMPDIR=/tmp uv run pytest -q --cov -n 2 --tier-report=/tmp/test-suite-health.json
cd frontend && npm test && npm run build
```

Use `--durations=50` only for diagnosis. Benchmark records should retain the
commit, command, coverage mode, elapsed time, and generated health report.

## CI

The `tests` workflow runs **Cutover contracts**, **Fast feedback (unit and
component)**, and **Required coverage gate**. The coverage gate uses two
workers, branch coverage, the project-wide 90% floor, and a health artifact.
Coverage-context and benchmark workflows are informational. Live hosted and
OpenAI tests remain opt-in and skip without their credentials and flags.

## Manual Cloudflare browser evaluation

The Chromium-only Playwright suite is intentionally **not** in CI. It drives the
real deployed FastAPI/Cloudflare Worker path with goal-focused, exploratory,
social, avoidant, aggressive, and chaotic-but-legal inputs. It records ending
reachability, dead ends, scene/revelation order, fired-storylet reuse,
selection/route diversity, pressure trajectory, and blocked-action rate in
ignored `artifacts/policy-evaluation.{json,md}` reports.

Run it manually against the deployment you intend to assess:

```text
cd frontend
E2E_API_BASE_URL=https://your-api.example E2E_DEPLOYMENT_CHANNEL=production npm run test:e2e
```

`E2E_TURNS_PER_POLICY` defaults to 8. Reduce it only for a quick transport/UI
smoke check; leave the default for a full ending-reachability sample. This suite
observes actual model behavior, so report values are evaluation evidence rather
than deterministic CI thresholds.
