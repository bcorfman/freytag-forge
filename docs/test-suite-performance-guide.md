# Test-suite performance guide

The suite covers offline causal/storylet authoring, the fact-backed V2 runtime,
SQLite persistence, Cloudflare transport normalization, the hosted adapter, and
deployment-channel isolation. This guide reflects the checked-in test and CI
configuration; `tests/conftest.py`, `pyproject.toml`, and
`.github/workflows/test.yml` remain the executable sources of truth.

## Classification

Every collected test receives one performance tier and one quality class.

| Dimension | Values | Current behavior |
| --- | --- | --- |
| Performance | `unit`, `component`, `integration`, `evaluation` | `tests/conftest.py` assigns listed boundary-heavy files explicitly; unlisted files default to `unit`. |
| Quality | `runtime_safety`, `authoring_quality` | The explicit authoring file set receives `authoring_quality`; unlisted files default to `runtime_safety`. |

Collection also rejects duplicate `test_*` function definitions. Collection
totals are informational and must never become a fixed-count quality gate.
`--strict-test-budgets` optionally enforces the existing unit/component runtime
and construction budgets. `--tier-report=PATH` writes per-test timing,
classification, and construction evidence.

The causal-spatial Phase 0 characterization is authoring-quality coverage. It
uses small immutable fixture projections and does not call a provider, write a
candidate, or mutate a reviewed artifact.

The causal-spatial Phase 2 contract suite is also authoring-quality coverage.
It validates immutable performance profiles, interaction frames, namespace
binding, lifecycle markers, movement eligibility, and agency minima across all
supported genres without invoking runtime or a provider.

## Local commands

Always keep pytest temporary files on the Linux filesystem in WSL:

```text
TMPDIR=/tmp uv run pytest -q
```

Useful focused variants are:

```text
TMPDIR=/tmp uv run pytest -q --no-cov -m authoring_quality
TMPDIR=/tmp uv run pytest -q --no-cov -m "unit or component"
TMPDIR=/tmp uv run pytest -q --no-cov --collect-only
TMPDIR=/tmp uv run pytest -q --cov -n 2 --tier-report=/tmp/test-suite-health.json
TMPDIR=/tmp uv run pytest -q --cov-context=test
```

Use `--durations=50` only for diagnosis. A benchmark record should include the
commit, exact command, coverage mode, pytest elapsed time, and the generated
health artifact. Local timings do not establish a CI target.

## CI jobs

The main test workflow currently runs three prerequisite jobs before staging:

- **Cutover contracts** runs fatal Ruff diagnostics, the compiled-story/runtime/
  Cloudflare contract slice, and the hosted adapter/channel-isolation smoke.
- **Fast feedback (unit and component)** runs the marked fast tiers without
  coverage.
- **Required coverage gate** runs the full suite with two pytest workers,
  branch coverage, the project-wide 90% floor, and a health report artifact.

`Coverage context report (informational)` is a separate nightly/manual workflow.
The benchmark workflows are diagnostic and do not replace the required coverage
gate. Live hosted and OpenAI tests remain explicitly gated and skip without
their operator-owned opt-ins and credentials.

## Maintenance rules

- Add a filename to the explicit tier or quality maps only when the boundary
  warrants it; otherwise document the intentional default.
- Keep shared test setup immutable or freshly cloned so fact mutations cannot
  leak between cases.
- Test provider recovery with injected transports. Ordinary successful turns
  allow one inference request and at most one shared recovery request.
- Preserve the full behavioral suite and 90% coverage floor; do not optimize by
  deleting distinct safety contracts.
- Update this guide whenever CI job names, pytest commands, classification
  behavior, or health-report fields change.
