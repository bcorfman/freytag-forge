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
TMPDIR=/tmp uv run pytest -q                                  # full suite without coverage
TMPDIR=/tmp uv run pytest -q --cov                           # full suite + 90% coverage gate
TMPDIR=/tmp uv run pytest -q --run-nightly  # full suite including nightly end-to-end tests
TMPDIR=/tmp uv run pytest -q --no-cov -m authoring_quality    # package authoring checks
TMPDIR=/tmp uv run pytest -q --cov --cov-report= --cov-fail-under=0 -n 4 --shard-index N --shard-count 6  # one CI coverage shard; files are assigned by tests/shard_durations.json
uv run coverage combine coverage-data && uv run coverage report  # nightly gate (coverage-nightly.yml)
uv run ruff check . && uv run ruff format --check .
# Repair lint/format debt when needed: uv run ruff check --fix . && uv run ruff format .
(cd frontend && node --test e2e/*.test.js src/*.test.js)
cd frontend && npm test && npm run build
```

**Pass:** all tests pass; the `--cov` run reaches at least 90% coverage; Ruff
reports no remaining issues; `npm test` passes and Vite writes `frontend/dist/`.

**Cleanup:** None. `frontend/dist/` is generated; delete it freely.

**Notes:** CI (`.github/workflows/test.yml`) runs static checks and six `--no-cov`
test shards, then deploys the tested SHA to staging and reruns
`tests/test_web_demo.py tests/test_cloudflare_transport.py` against the
adapter contract. `coverage-nightly.yml` enforces the 90% coverage floor on a
schedule, not on pushes. `frozen-runtime-regression.yml` runs
`tests/test_markdown_story_package.py` weekly.

## 2. Focused checks by boundary

Use while editing; finish with section 1.

| Boundary | Tests |
| --- | --- |
| Package loading and lints (`must_convey`, `delivery_text`, narration term traps, custody, placements) | `tests/test_markdown_story_package.py` |
| Knowledge projection, save/load stability, leakage matrix | `tests/test_knowledge_projection.py tests/test_knowledge_leakage_matrix.py` |
| Narration safety, reviewed leak vocabulary and reveal conveyance | `tests/test_narration_safety.py tests/test_leak_terms.py tests/test_must_convey.py tests/test_narration_corpus.py`; regenerate with `TMPDIR=/tmp uv run python scripts/regenerate_narration_corpus_verdicts.py`; add runs with `uv run python scripts/extract_narration_corpus.py RUN_DIR`. |
| Spine expectation and prompt order | `tests/test_spine_expected_reveals.py tests/test_1a_spine_prompts.py`; regenerate the JSON with `uv run python -m scripts.generate_spine_expected_reveals`. The generator replays the real runtime with a network-free scripted provider that assembles prompts and selects eligible exact handoffs. It retains 2C C-R2 and writes sorted per-scene reveal sets. Inspect turn records separately to verify reveal order, spacing and deadline use; this replay does not measure live narration or semantic fallback behavior. |
| Shared guard earning and card characterization | `tests/test_reference_protected.py tests/test_guard_vocabulary.py`; each package leak term is tested independently at scene start and after its owning knowledge effects. The synthetic held-transit-card test records that narration guards both bare/article forms before recovery, while reference resolution can still resolve bare `card` to the transit card. |
| Authored reveal handoff (matcher, composition, prompt exclusion) | `tests/test_candidate_matcher.py tests/test_cloudflare_transport.py` |
| Pacing windows, handoff fallback, full canonical journeys | `tests/test_scene_relative_pacing.py tests/test_pacing_handoff.py tests/test_canon_journey.py` |
| API payloads and player-visible segments | `tests/test_web_demo.py` |
| Bench harness and ledger | `tests/test_bench.py` |

```bash
TMPDIR=/tmp uv run pytest -q --no-cov <tests from the table>
```

**Pass:** assertions pass. Coverage exit status is irrelevant here.
