# Local deterministic and focused checks

Part of [the testing runbook](../testing-runbook.md).

## 1. Local deterministic suite

**Purpose:** The authoritative gate for runtime, package, transport, API, and
persistence behavior. Free; no network.

For the Ringer quick tier, run `uv run python scripts/quick_suite.py [--also PATH ...]`.
It skips manifest-recorded files at or above the 15-second threshold; `--also` re-includes relevant journeys.
If the manifest is missing test files, refresh it with `uv run python scripts/regen_shard_durations.py --missing-only`.
PR CI skips tests marked `nightly`; the nightly workflow runs them.

```bash
TMPDIR=/tmp uv run pytest -q -n auto                          # full suite without coverage, one worker per core
TMPDIR=/tmp uv run pytest -q --run-nightly  # full suite including nightly end-to-end tests
TMPDIR=/tmp uv run pytest -q --no-cov -m authoring_quality    # package authoring checks
TMPDIR=/tmp uv run pytest -q --no-cov -n 4 --shard-index N --shard-count 6  # one CI shard; files are assigned by tests/shard_durations.json
uv run coverage combine coverage-data && uv run coverage report  # nightly gate (coverage-nightly.yml)
uv run ruff check . && uv run ruff format --check .
# Repair lint/format debt when needed: uv run ruff check --fix . && uv run ruff format .
(cd frontend && node --test e2e/*.test.js src/*.test.js)
cd frontend && npm test && npm run build
```

**Pass:** all tests pass; Ruff reports no remaining issues; `npm test` passes and Vite writes `frontend/dist/`.
The judging tools in `frontend/e2e` read the live story through `python -m storygame.story_package.authoring_view`, so run `uv sync` first (they use `.venv/bin/python`; set `FREYTAG_PYTHON` to use another interpreter).

**Cleanup:** None. `frontend/dist/` is generated; delete it freely.

**Notes:** CI (`.github/workflows/test.yml`) runs static checks (full
`ruff check .` and `ruff format --check .`, which skip `.plans/` and
`scripts/ringer/`, plus the story format and snapshot gates) and six `--no-cov`
test shards. It then deploys the tested SHA to staging and runs
`tests/test_web_demo.py tests/test_cloudflare_transport.py` on the CI runner;
those tests do not call the deployed service. `coverage-nightly.yml` enforces the 90% coverage floor on a
schedule, not on pushes. `frozen-runtime-regression.yml` runs
`tests/test_markdown_story_package.py` weekly.

## 2. Focused checks by boundary

Use while editing; finish with section 1.

| Boundary | Tests |
| --- | --- |
| Package loading and lints (`must_convey`, `delivery_text`, narration term traps, custody, placements) | `tests/test_markdown_story_package.py` |
| Knowledge projection, save/load stability, leakage matrix | `tests/test_knowledge_projection.py tests/test_knowledge_leakage_matrix.py` |
| Narration safety, reviewed leak vocabulary and reveal conveyance | `tests/test_narration_safety.py tests/test_leak_terms.py tests/test_must_convey.py tests/test_narration_corpus.py` ([regeneration commands](focused-check-notes.md#narration-corpus)) |
| Spine expectation and prompt order | `tests/test_spine_expected_reveals.py tests/test_1a_spine_prompts.py` ([regeneration and limits](focused-check-notes.md#spine-expectation)) |
| Shared guard earning and card characterization | `tests/test_reference_protected.py tests/test_guard_vocabulary.py` ([what they cover](focused-check-notes.md#guard-earning-and-card)) |
| Authored reveal handoff (matcher, composition, prompt exclusion) | `tests/test_candidate_matcher.py tests/test_cloudflare_transport.py` |
| Witnessed card recovery, patrol consequences in 1B, officer pressure, and drawer action matching | `tests/test_1a_witnessed_recovery.py tests/test_1a_officer_press.py tests/test_drawer_gap_nudge.py` ([limits](focused-check-notes.md#recovery-pressure-and-drawer)) |
| Pacing windows, handoff fallback, full canonical journeys | `tests/test_scene_relative_pacing.py tests/test_pacing_handoff.py tests/test_canon_journey.py` |
| API payloads and player-visible segments | `tests/test_web_demo.py` |
| Package boundaries: imports into `worldkeeper`, `World` internals, story IDs in shared runtime | `tests/test_architecture_boundaries.py packages/worldkeeper/tests` |
| Review risk tiers, staging evidence, review outcome report | `tests/test_review_risk.py tests/test_staging_evidence.py tests/test_review_outcomes.py` |
| Bench harness and ledger | `tests/test_bench.py` |

```bash
TMPDIR=/tmp uv run pytest -q --no-cov <tests from the table>
```

**Pass:** assertions pass. Coverage exit status is irrelevant here.
