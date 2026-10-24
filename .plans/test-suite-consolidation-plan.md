# Consolidate the test suite: remove duplicate, overlapping, subsumed and obsolete tests

Status: proposed, 2026-10-22, baseline `398bcbbb`. Nothing below is started. No
test was deleted or edited to write this plan.

## Resume here

Phase 1 evidence is in (sections 2b to 2d) and the first ledger draft is
[test-suite-consolidation-ledger.md](test-suite-consolidation-ledger.md). Mutant panel done (section 2e). Next: apply it to ledger rows L5 to L8; then Brandon's cluster
review of the ledger, then batch (a): rows L1 to L3. D1 to D4 keep their recommended defaults.
Answered 2026-10-23: engine Codex Luna low, D5 (b) profile now and speed up later, D6
regenerate `shard_durations.json` from the Phase 1 junit data, D7 yes.

## 1. Goal and what counts as success

Remove tests that add no protection, so the suite runs faster and is cheaper to
change, without lowering what it catches. A test is a candidate when it is:

- **A. Exact duplicate:** same body as another test.
- **B. Overlapping:** same behavior reached through a different fixture or a
  copy-edited file. Merge into one parametrized test.
- **C. Subsumed:** a lower-level path test whose observable outcome a higher-level
  journey or integration test already asserts, and would fail if it broke.
- **D. Obsolete:** pins behavior or an experiment that no longer exists, or
  references a removed symbol, file or plan.

Success is measured, never by test count (the runbook forbids pinned counts):

1. Covered lines and branches of `storygame/` after each batch are a superset of
   the baseline's. This is stricter than the 90% project floor.
2. The regression replay panel (section 4) still catches every mutant it caught.
3. Full-suite CPU seconds (from `--tier-report`) and CI shard balance improve.
   No target number is promised.
4. Ruff clean; the full suite passes; `--cov` stays at or above 90%.

## 2. What exists today (measured 2026-10-22)

| Fact | Value | Source |
| --- | --- | --- |
| Test files / test functions / collected tests | 186 / 1,661 / 2,994 | `tests/test_*.py`, `ast`, `pytest --collect-only` |
| Parametrize decorators; test lines | 197; about 39,900 | `grep`, `wc` |
| Recorded weights in `tests/shard_durations.json` | 160 files, sum 5,217; conditions unknown | CI sharding input. **Not comparable to a current run** (see 2a) |
| Identical-body tests | 2 groups: `test_existing_arm_dry_run_remains_byte_stable` in `test_3c_families_offer_arm.py` and `test_3c_no_close_arm.py`; `test_engine_path_preserves_negation_scope` vs `test_engine_provider_path_respects_negation_scope` in `test_command_split_negation.py` and `test_negation_scope.py` | `ast` dump hash, bodies over 400 characters |
| Stale doc reference | `docs/test-suite-performance-guide.md` runs `tests/test_conversation_quality_phase8.py`, which does not exist | `grep` |
| Where coverage runs | Push and PR CI: six shards and a fast-feedback job, all `--no-cov`. The 90% gate runs only in `coverage-nightly.yml` (daily 06:17 UTC or manual); `coverage-context-report` is nightly and informational; the benchmark workflows are manual. The runbook (lines 38, 51) and performance guide (line 40) still say the required gate is in the `tests` workflow | `.github/workflows/*.yml`. Gate enforcement by `fail_under` is inferred from `pyproject.toml`, not run |
| Existing evidence tooling | `--tier-report` writes per-test tier and timing; `.github/workflows/coverage-context-report.yml` runs `--cov --cov-context=test` nightly and uploads the report | `tests/conftest.py`, workflow |
| Suspect clusters by name only | 3C experiment arms and probes (`test_3c_*_arm.py`, `*_probe.py`, 118 tests across 20 files); `*_repro.py` characterizations; per-scene `*_spine_prompts.py`; `phase*` files; frozen `continuity_initiative_pre_3c_adoption` fixture | file names |

The last row is a list of places to look, **not findings**. Names suggest overlap
but prove nothing. The exact-duplicate scan catches only byte-identical bodies;
near-duplicates need Phase 1.

## 2a. Phase 0 result (2026-10-22)

Baseline `398bcbbb`, working tree plus this plan and two docs edits. Run on 16
cores (WSL), load about 1, nothing else running. Command:
`TMPDIR=/tmp .venv/bin/python -m pytest -q --no-cov -p no:cacheprovider --tier-report=...`
with the project's default `-n auto`. Raw output is in
`/home/bcorfman/dev/ringer-work/test-review/` (`run-nocov.log`, `tier-nocov.json`).

| Measure | Value |
| --- | --- |
| Result | 2,978 passed, 16 skipped |
| Wall time | 185.6 s (3:06) |
| User CPU | 2,042 s, 1,105% of one core |
| Sum of per-file seconds | 1,949 s over 186 files; 91 files under 1 s |
| Slowest single test | 66.4 s, then 57.8, 54.2, 50.2, 43.7, 38.3 s |
| Largest fixture setup | 41.9 s (`test_persona_escalation.py`), 13.6 s (`test_three_c_prefix.py`) |

Time by cluster (file seconds; clusters do not overlap):

| Cluster | Files | Seconds | Share |
| --- | --- | --- | --- |
| Journeys: `test_game_path_journeys` 454 s, `evidence_gap_journeys` 93 s, `canon_journey`, `game_path_completion` | 4 | 568 | 29% |
| 3C family: `test_3c_*`, `test_three_c_prefix` | 22 | 522 | 27% |
| `test_bench*` | 4 | 236 | 12% |
| Persona, disclosure matrix, markdown package | 3 | 125 | 6% |
| Narration corpus, safety, earned names | 10 | 78 | 4% |
| `*_repro` | 4 | 70 | 4% |
| Everything else | 139 | 350 | 18% |

What this changes:

- The old shard weights overstated cost: the same 160 files sum to 1,371 s now, and
  the per-file ratio ranges from 0.21 to 9.99. `test_bench_item_facts.py` is 197 s,
  not 1,256, and `test_game_path_journeys.py` is 454 s, not 120. The weights also
  omit 26 newer files. Since `assign_test_nodes_to_shards` reads this file, CI shard
  balance is probably poor. Not verified: no CI shard timings were read.
- Two clusters hold 56% of the time. The 3C family is a closed experiment area,
  which makes it the first review target. Six single tests of 38 to 66 s set a floor
  under the wall time: 16 workers cannot beat the longest test.
- The heavy dry-run tests include `test_existing_arm_dry_run_remains_byte_stable`,
  which exists in two files with identical bodies (54 s and 38 s). Deleting one of
  the pair saves its time at no coverage cost, subject to Phase 1 confirming it.
- The no-coverage run is what a PR pays, so the separate `--cov` baseline planned
  for Phase 0 is dropped. Phase 1's `--cov-context=test` run records the coverage
  mode time.
- The per-test inventory moves to Phase 1. `--tier-report` lists only the 50 slowest
  tests, so per-test times come from `--junitxml` in the Phase 1 run.
- Docs fixed in Phase 0: the stale `phase8` command and the stale "required
  coverage gate in CI" statements (`docs/test-suite-performance-guide.md`,
  `docs/testing-runbook.md`). All `tests/...` paths named in `docs/`, `README.md`
  and `bench/README.md` resolve.

## 2b. Phase 1 per-test coverage result (2026-10-23)

Ringer run `test-suite-consolidation-phase1-20261023T055114Z-p1978912`, Codex Luna low,
one task, two identical runs of
`pytest -q --cov --cov-context=test --junitxml=... --tier-report=...` on HEAD
`5ea3c750`. Outputs: `/home/bcorfman/dev/ringer-work/test-review/cov-run/per-test-coverage/`
(`cov-{a,b}.sqlite`, `junit-{a,b}.xml`, `per-test-{a,b}.json.gz`, `determinism.json`,
`no-storygame-coverage-{a,b}.json`). The checker is
`ringer-work/test-review/check_cov_run.py`.

| Measure | Value |
| --- | --- |
| Result, both runs | 2,994 testcases, 16 skipped, 0 failed |
| Coverage-mode wall time | 15:52 and 14:13, user CPU 9,490 s and 9,745 s (about 5x the no-coverage 3:06 and 2,042 s) |
| Tests with a coverage context | 2,756 of 2,994 |
| Tests with none | 238, in `no-storygame-coverage-*.json`. Spot check: `test_penalty_rubric` and one `test_1a_gap_pointer` test, run alone, record no test context. They run no `storygame` code (bench, script, data and authored-text tests, and the skips). Zero coverage is not redundancy, so they are judged by reading, not by coverage |
| Union of covered (file, line, arc) items | 19,120 in both runs, 0 items in only one run |
| Tests whose own set differs between runs | 40 of 2,756 |

Determinism: the union is exactly stable, so the batch gate (the union must not shrink)
is sound. Per-test sets are not: 40 tests differ, by up to about 3,000 items, in
opposite directions for neighbours (for example `test_leak_terms` gains 3,059 items
where other tests lose them). Not diagnosed; shared module-level caches warmed by
whichever test runs first on a worker would explain it, but that is a guess. Handling,
chosen so the stop rule (section 7) does not block Phase 1: a test that differs between
runs is never credited with coverage it holds in one run only when claiming a retained
test covers something, and is never deleted on unique-coverage grounds without a human
read. If the number of differing tests grows, stop and fix determinism first.

The first check failed (the worker's output was fine): my threshold treated the 238
no-context tests as a gap. Fixed in the checker, then rerun on the same outputs.

## 2c. Phase 1 analysis results (2026-10-23)

Ringer run `test-suite-consolidation-phase1-20261023T062646Z-p1995973`, four read-only
tasks, outputs in `/home/bcorfman/dev/ringer-work/test-review/analysis/<task>/`. The
run reported FAIL on all four because of two bugs in my check (it counted my own
uncommitted plan edit and old worktrees); the fixed check passes on the same outputs.

**Coverage analysis** (2,756 tests with a context; the check recomputed unique-item
counts for 25 sampled tests and 200 subset pairs):

- 2,494 tests have no unique line or arc, 290 groups have identical sets, 200,838 pairs
  are subset pairs, and a greedy cover needs 368 tests to keep all 19,120 items.
- Read these as an upper bound on overlap, not a deletion list. Line and arc coverage
  shows code ran, not that a result was asserted, so most tests overlap. The largest
  identical-set groups are parametrized suites (`test_shared_knowledge_guards` 182 and
  128 cases, `test_evidence_gap_journeys` and journeys 67, `test_candidate_matcher` 31).
- Time figures in `coverage-analysis.json` come from the coverage run and are about 5x
  inflated (one test reads 308 s against a 66 s maximum without coverage). Use them for
  ranking only. The summed "removable seconds" in the md (8,360 s) is meaningless as a
  saving.

**Duplicate and obsolescence scan** (1,661 test functions):

- 3 exact-duplicate groups: the two known pairs plus one parametrized pair, to be read.
- 0 near-duplicate clusters at ratio 0.9 with 8 or more lines. The threshold may be too
  strict; rerun at 0.7 before concluding anything.
- Obsolescence: 4 findings, 3 of them `test_shard_balance` naming a deliberately
  missing `tests/test_missing_duration.py` (false positives), and one unconditional
  `pytest.skip` in `test_incident_characterization` (frozen).
- Gap: the worker listed only module-docstring clusters. The filename clusters
  (`*_arm`, `*_probe`, `*_repro`, `*_spine_prompts`, `phase*`) were not produced.

**Regression panel feasibility:** 530 non-merge commits touch both `storygame/` and
`tests/`; 50 have a `storygame/` part that reverse-applies cleanly onto HEAD
(`git apply -R --check`, re-tested on 8 sampled commits). That is above the stop-rule
minimum of 15, so the panel is buildable. Running it costs 50 full-suite runs (about
3 min each without coverage); see D7.

**Journeys profile (D5):** serial, 71 tests, 297.7 s, 4 to 5 s each. Setup is 0 s. The
file time in the 16-core run (454 s) is larger than the serial time, which points at
contention or per-worker load, not at the tests; not established. The profile of the
slowest test (10.6 s under cProfile) puts the time in the engine, not in test setup:
`storygame/runtime/facts.py:28 matching` 2.1 s cumulative and its generator 649k calls,
`knowledge._established` 2.9 s, `reference_resolution._scene_things` 2.9 s. Per
journey the package load and state build happen once or twice, so sharing built state
(D5 option b) would save little. The lever is the runtime's per-turn fact scan, which
is a source change outside this plan. Recorded for Brandon; no action taken.

## 2d. Phase 1 round two (2026-10-23)

Ringer round two of the same job (`test-suite-consolidation-phase1`), outputs in
`ringer-work/test-review/round2/`.

- **Quiet no-coverage run with junit:** 3:31.83 wall, 2,266 s user CPU, 1,078% of one core,
  2,994 testcases, 0 failed. Per-test times sum to 2,184 s and are saved in
  `ringer-work/test-review/pertest-nocov.json`. This replaces the 5x-inflated coverage-run
  times for ranking. The Phase 0 run was 3:06; the 14% difference is not explained.
- **Looser near-duplicate scan** (ratio 0.75, Jaccard 0.6, 6 lines): 19 clusters, mostly
  same-file tests that differ in one setup call or assertion. Low payoff.
- **Filename clusters:** arm 3 files, probe 2, repro 4, spine_prompts 7, phase 3.
- **Ledger draft 1** written. Only L1 (an exact duplicate, 43 to 65 s) is a Delete today.
  L2 and L3 are Merge rows of negligible time. About 990 s of no-unique tests sit in rows
  L5 to L8, which wait for the mutant panel.

## 2e. Mutant panel result (2026-10-23)

All 50 clean commits ran as mutants (HEAD plus the `storygame/` part of one fix reverse-applied,
full suite, no coverage). Merged data: `ringer-work/test-review/panel/panel-results.json`; runners
`panel/smoke/smoke/panel_run.py` and `panel/panel_one.py` (verbose, 360 s cutoff, 120 s hang dump).

- 49 mutants have kill sets. **7 are degenerate** (kill 100 to 2,000+ tests by breaking imports or
  package load: `e346f80 775be92 7ab8092 7afb3bb ab3bd4f 90268ec b79ead5`) and are ignored for protection.
- **4 mutants are killed by no test** (`90f8d21 ff9abcd 54541e9 aae208d`): a test gap, noted for later.
- `3e8f9c6` hangs (spins in `cloudflare._is_present` inside a `turn()`); killed only by
  `test_late_scene_repro::test_nonmatching_filler_preserves_authored_custody_across_2a_to_3c` (L8, protect).
- 314 distinct tests kill at least one usable mutant.
- Per ledger row, tests that kill a small (3 or fewer kills) non-degenerate mutant: L5 0 (7 killers
  in all), L6 2 (`test_3c_cue_chain_stages_each_next_fact`, plus `test_payload_proof_removes_exactly_one_line`
  via `b0f0413`), L7 7 (`test_bench_item_facts` seed and held-by cases, `test_runtime_mode_exit_turn...`),
  L8 0 besides the hang test. These are Keep; the rest of each row is still a candidate.
- Process lessons: my first check demanded 2,900+ tests and failed valid broken-import mutants; a 15 min
  cutoff was too long (a normal mutant is about 3.5 min).

## 2f. Batch 1 and the time rule (2026-10-23)

Brandon's direction: wall time must fall by orders of magnitude; any test of 1 s or more needs a
reason; delete what does not appear to matter, reintroduce later if needed; add tests only when
complete and useful. Delete rule used: a test function of 1 s or more is deleted unless it is the
cheapest killer of a usable panel mutant or the only cover of a line or branch across `storygame`,
`bench` and `scripts` (second coverage run, `cov-run/tooling/`). Frozen files are excluded.

- 99% of the time is in 301 tests of 1 s or more (1,939 of 2,184 CPU s); the 2,693 faster tests
  are about 245 s.
- **Batch 1 (applied, uncommitted):** 143 functions, 571 cases, three whole files
  (`test_2c_assess_engine_turn`, `test_shared_knowledge_guards`, `test_tier_report_xdist`).
  Collected 2,994 to 2,423. Full suite 2,407 passed, 16 skipped.
  No-coverage wall 3:31 (or 3:06) to 2:17 (136.6 s), user CPU 2,266 s to 1,192 s.
- Coverage: 3 items lost in `scripts/ringer/stage7/3c_entry_replay_probe.py` (closed 3C experiment
  probe); accepted. Everything else in `storygame`, `bench`, `scripts` is still covered.
- Next: the frozen journeys and the 360 s of tests kept only as sole coverage. Ringer run
  `test-suite-consolidation-batch1-20261023T180825Z-p2191567`; tool and check in
  `ringer-work/test-review/batch1/`.

### Frozen set (reimagination Phase 1 owns these)

Chosen by the facts, events and ids Phase 1 steps 3 to 7 change (`evidence_gap_*`,
`facility_infiltration_needed`, `captives_confirmed_alive`, `t_1c_2a`, `bridge_1c`,
`SL-1C`, `min_turns`, `_apply_authored_transition`, incidents), plus cue lifecycle
and handoff tests.

- **Frozen files:** `test_incident_loader`, `test_incident_characterization`,
  `test_scene_1c_grounding`, `test_1c_reading_pointer`, `test_1c_spine_prompts`,
  `test_cue_spent_reveal`, `test_cue_eligibility_compare`, `test_cue_escalation`,
  `test_staged_cues`, `test_recent_cue_unit`, `test_recent_cue_reference`,
  `test_discovery_continuity`, `test_pacing_handoff`, `test_scene_relative_pacing`,
  `test_exit_backstop_invariant`, `test_evidence_penalty`,
  `test_evidence_gap_journeys`, `test_game_path_completion`,
  `test_game_path_journeys`, `test_canon_journey`, `test_verbatim_complication`.
- **Frozen rows only (1 to 12 references in a larger file):**
  `test_markdown_story_package`, and the one-reference files from the grep (for
  example `test_seating`, `test_knowledge_projection`, `test_2a_*`). Review these
  by row, not by file.
- The journeys are both frozen and the largest cost (568 s). That conflict is D5.

## 3. Constraints from the project

- Every code or test change runs as a Ringer manifest, one batch per run, with
  `"check_timeout_s"` raised for full-suite checks (agent workflow guide).
- Tests stay hermetic: no live worker, no network.
- Do not lower any gate: the 90% floor, the nightly coverage shards, `test_shard_balance`.
  PR CI runs no coverage, so a batch that loses coverage is not caught until the
  next nightly run. The per-batch coverage comparison in section 6 is the real gate.
- Ruff-format every touched file. Do not pin collection counts anywhere.
- Update the runbook and performance guide only where a deleted file or a stale
  command is named. Do not add results to the runbook.
- Record each batch in this file (commit, verification, untested work) before the
  next batch starts.
- **Do not edit tests the game reimagination owns.** Phase 1 of
  [game-reimagination-phase1.md](game-reimagination-phase1.md) is still changing
  1C, 2A, cue lifecycle, handoff and traversal behavior. Analyze these tests in
  Phase 1, but mark them frozen (section 6) until that plan's step 7 is committed.

## 4. Evidence method (Phase 1, no test edits)

Analysis scripts live outside the repo (`/home/bcorfman/dev/ringer-work/test-review/`),
run as Ringer manifests. Commit only the ledger. Promote a script into the repo
only if a later batch needs it again.

1. **Inventory.** One row per collected test: node id, file, tier, quality class,
   parametrize case count, duration from `--tier-report`, fixtures used, the
   `storygame` symbols it imports or calls.
2. **Per-test coverage.** One local run of
   `TMPDIR=/tmp uv run pytest -q --cov --cov-context=test --tier-report=...`, the
   same command the nightly workflow runs. Export covered (file, line, branch)
   sets per test. Compute: (a) tests with no unique line or branch, (b) pairs
   where one test's set contains the other's, (c) the minimal set that preserves
   the baseline union (a greedy set cover, reported as a ceiling, not a target).
3. **Near-duplicate detection.** Normalize each test body (`ast`, strip names and
   literals of fixtures) and cluster by edit similarity. Report clusters with the
   differing lines, so a human sees what differs.
4. **Obsolescence scan.** Tests that reference a symbol, module, script, package
   file or plan that no longer exists; `skip`/`skipif` cases whose condition can
   never hold; tests of experiment arms whose plan is closed; tests pinning the
   frozen pre-3C fixture; evidence files with a hard-coded redacted output.
5. **Regression replay panel (experiment).** Coverage shows a line ran, not that a
   behavior is asserted, so coverage alone cannot prove a test redundant. Build a
   panel of real mutants: take recent fix commits that change both `storygame/`
   and `tests/`, reverse-apply only the `storygame/` part to a scratch worktree
   where it applies cleanly, run the full suite, and record the failing tests as
   the mutant's kill set. A candidate is protected if it is the only killer of
   any mutant. **Stop rule:** if fewer than 15 commits reverse-apply cleanly,
   drop the panel and rely on steps 2 to 4 plus the human review in section 5.
   Record the clean-apply count; do not rename the experiment and retry.
6. **Time baseline.** One full run without coverage, plus one with, recorded in
   this file: wall time, CPU seconds, worker count. This is the "before" number.

## 5. Ledger and verdicts

`.plans/test-suite-consolidation-ledger.md`, one row per candidate (not per test):

`id | class A-D | tests | evidence | retained test that covers it | unique coverage lost | mutants only it kills | verdict | status`

Verdicts:

- **Delete:** class A or D, or class B/C with zero unique coverage, no
  mutant it alone kills, and a named retained test asserting the same outcome.
- **Merge:** class B. Fold into one parametrized test; keep every distinct case.
- **Keep:** unique coverage or unique kill, or the only test of an error branch
  or edge case.
- **Frozen:** owned by the reimagination plan. Revisit after its step 7.
- **Needs human:** assertions differ in a way the tools cannot judge.

A lower-level test subsumed by a journey is deleted only if the journey asserts the
same observable result **and** runs no more than a few times slower than the unit
test would. A unit test that localizes a failure a journey would only report as
"ending not reached" is kept when it is the single place a documented contract
(PRD, contributor guide, grounding guide) is pinned. This protection is decision D2.

Brandon reviews the ledger summary by cluster before Phase 3. Each Delete row is
checked against the test source by a Ringer read-only reviewer (a different
worker than the one that built the ledger), and I spot-check at least one per
cluster.

## 6. Phases

| Phase | Work | Exit |
| --- | --- | --- |
| 0. Baseline | **Done 2026-10-22, see 2a.** Timed no-coverage run, file-level times, frozen set, docs fixes. The `--cov` baseline and per-test inventory moved to Phase 1 | Time baseline recorded; frozen set listed |
| 1. Evidence | Section 4 steps 2 to 5; build the ledger | Ledger complete; every candidate has a verdict; panel clean-apply count recorded |
| 2. Review | Brandon's cluster review; reviewer pass on Delete rows | Approved verdict list; rows changed or rejected are recorded with the reason |
| 3. Batches | One Ringer manifest per batch, in this order: (a) exact duplicates and stale files, (b) closed 3C experiment arms and probes, (c) heavy `*_repro` and journey overlaps, (d) `bench_item_facts` parametrization audit, (e) per-scene spine-prompt files merged into a parametrized test, (f) `phase*` files. Each batch ends with a commit and a plan update | Every batch passes its check (below); time and coverage recorded per batch |
| 4. Frozen set | Scheduled 2026-10-24: after reimagination Phase 3 (migrate the adventure), not after step 7; redo the evidence for the frozen files Phase 1 changed. See the main plan's section 8. Repeat Phases 1 to 3 for the frozen tests | Frozen rows resolved |
| 5. Close | Run before reimagination Phase 4 (qualify and deliver). Regenerate `tests/shard_durations.json`; check `test_shard_balance`; confirm the runbook and guide name only existing files | Two consecutive green CI runs on `main`; before/after numbers in this file |

Batch order is by risk and payoff: (a) and (b) have the least behavior risk; (c)
and (d) hold most of the recorded time.

### Batch check (each Ringer manifest)

The worker's spec lists the exact test ids to delete or merge and may touch only
the test files named. The check must:

1. confirm each listed test no longer exists and no unlisted test was removed;
2. confirm the named retained tests still pass;
3. rerun the coverage export and fail if any baseline (file, line, branch) is no
   longer covered;
4. rerun the mutant panel (if built) and fail if any mutant lost its entire kill
   set;
5. run the full suite and `ruff check` / `ruff format --check`;
6. grep `docs/` and `tests/shard_durations.json` for removed file names.

Use `set -o pipefail` and never pipe pytest into `tail` unguarded, or a failing
check reports PASS. Set `check_timeout_s` to at least 1,500. Do not run two batches
at once: they edit the same shard file and docs.

## 7. Stop rules

- If a batch loses unique coverage or a mutant kill, revert it and move the tests
  to Keep with the reason. Do not weaken the check.
- If the coverage export disagrees between two identical runs (flaky or
  order-dependent coverage), stop and fix the determinism first.
- If Phase 1 finds under about 10% of the 1,949 file seconds removable outside the
  frozen set, report that and stop instead of running Phase 3 for a small gain.
- Never delete a test only because it is slow or only because it is old.
- Do not rewrite or improve retained tests in this plan; note them for later.

## 8. Decisions

1. **D1: scope of the bench harness tests** (`test_bench*.py`, 342 of the 1,661
   functions, 236 s, 12% of file seconds). Recommended: include them, but after the
   3C family and the duplicates. `test_bench_item_facts.py` has 12 parametrize
   decorators over 257 tests, which suggests overlap. Not verified.
2. **D2: protect failure-localizing unit tests.** Recommended: protect one test
   per documented contract, as in section 5.
3. **D3: timing against the reimagination.** Recommended: run Phases 0 to 3 now on
   everything outside the frozen set, and Phase 4 later.
4. **D4: Node tests** (`frontend/` 20 files, `bench/*.test.mjs` 5 files). Recommended:
   out of scope for the first pass; review them after Phase 5 if the Python
   result justifies it.

5. **D5: the heavy journeys are frozen.** `test_game_path_journeys.py` (454 s, 23% of
   the suite) is frozen because reimagination steps 6 to 8 will rewrite 1C. Options:
   (a) leave it until step 7, which keeps the slowest file for several steps;
   (b) speed it up now without changing assertions, for example by sharing one
   built journey state; (c) treat it as the first Phase 1 review target and accept
   a small conflict with reimagination. Recommended: (b), after Phase 1 confirms
   where its time goes. Not verified: why it takes 454 s.
6. **D6: regenerate `tests/shard_durations.json` now.** It is stale and omits 26
   files, and CI sharding reads it. Recommended: regenerate it from the Phase 1
   run, as its own small Ringer manifest, then again in Phase 5. Check the effect
   on CI shard wall times, which this plan has not measured.

7. **D7: build the mutant panel?** 50 clean commits are available. Running them is 50
   full-suite runs, about 2.5 hours of one machine, and gives the only evidence that a
   test asserts something. Recommended: yes, but first on the candidate set only (the
   tests that coverage marks as having no unique item and that are not in
   parametrized suites), not on all 2,994.

Worker engine: ask Brandon before the first run, with the numbers from
`ringer.py models --task-type code-fix`. Phase 1's choice (Codex Luna, medium)
applies to the reimagination only.

## 9. Not verified

Phase 0 measured one no-coverage run on one machine, not repeated runs or CI.
The overlap candidates in section 2 are names, not findings. Whether per-test
coverage is deterministic, whether the regression panel is buildable, how much time
is removable, why the journeys take 454 s, and how CI shards are balanced are all
open until Phase 1.
