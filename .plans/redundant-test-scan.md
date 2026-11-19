# Redundant test scan, stage 1 (static)

2026-11-19. Read-only. Nothing deleted. Scripts: `.plans/story-data-phase0/test_static_scan.py <repo> <out.json>`, `copied_prose_legacy.py <repo>` (the old audit pointed at the frozen legacy folder).

Suite: 455 test files, 3,396 test functions (4,768 collected with parameters). Nightly context report of 2026-11-18 (SHA 55806099, before the flip) has timings only, no per-test coverage.

## Exact duplicates (delete one of each pair after a mutation check)

| Keep | Remove | Note |
| --- | --- | --- |
| `tests/test_richer_1c.py::test_existing_1c_commands_still_reach_their_reveals` | `tests/test_1c_closeout.py::test_no_other_unique_1c_handoff_changes` | identical body, same four checks |
| `tests/test_candidate_matcher.py::test_scene_2a_c_r5_matches_natural_player_actions` | `tests/test_2a_forms_words.py::test_2a_supervisor_diagnosis_selects_convincing_inspection` | same inputs, same candidates, same assertion |
| `tests/test_candidate_matcher.py::test_scene_2a_unrelated_actions_match_neither_evidence_candidate` | `tests/test_2a_forms_words.py::test_2a_unrelated_actions_do_not_select_an_inspection_outcome` | same |
| `tests/test_cloudflare_transport.py::test_transport_recovers_once_from_a_malformed_provider_envelope` | `...::test_transport_still_reasks_for_an_invalid_provider_envelope` | same file, identical body; the names claim different things, so check the intent first |
| `tests/story_source/test_l1_root.py::test_mini_ok_is_clean` | `tests/story_source/test_l1_scene.py::test_mini_ok_is_clean` | three lines, low value either way |

Not duplicates, despite equal body text: `test_command_split_negation` vs `test_negation_scope` (one input differs: "; do not" vs ", but do not"; the first has a third case).

## Biggest cost: tests of finished experiments

45 experiment-named files (probe, frozen, repro, heldout, drain, rejudge) are 10% of files and 2,735 of 16,479 file-seconds (17%) in the nightly timing. Top: `test_frozen_prompts` 377 s, `test_frozen_decode` 346 s, `test_hidden_bench_arm_probe` 289 s, `test_opening_truck_probe3/2/4/1` 270/229/214/126 s, `test_hidden_bench_prose_probe` 176 s, `test_act2_probe` 162 s, `test_slice_probe` 101 s. They test one-off scripts under `scripts/ringer/` and frozen bench runs. Open question for the owner: which scripts are retired. Where a script is retired, its test goes with it and the script moves out of the test path. `bench/frozen_*` is bench tooling, so check whether it is still used before touching it. Not verified: why they are slow (probably story load per test), and the timings predate the flip.

## Format-bound, to decouple not delete (step 3)

- 36 test files copy 67 authored sentences (327 sentences in 246 passages). Largest: `test_richer_1c` 6, `test_1a_arrival_glance` 5, `test_delivery_restatement` 5, `test_1c_stall_exit` 5, `test_richer_3a` 5.
- 10 files use the frozen legacy copy on purpose (converter, parity, dispatch tests, three others). 13 files mention legacy file names; most are lighthouse fixtures.

## Checked and not a problem

- 25 tests with no `assert` statement: the `test_l1_scene` ones assert in a shared helper; the rest are "loads without raising" smokes (a few are weak: `test_persona_summary_is_json_serializable`).
- Unconditional skips: none.
- Same error message asserted in several tests: 14 of 157 messages, mostly different layers (loader vs source check). The markdown loader tests from round 6g and the fixture tests overlap on `scoped alias`, `never_asserted_fact`, `unknown anchor`, `ambiguous anchor`, `duplicate key`; dynamic evidence needed to say which to drop.

## Next stages

2. Per-test coverage contexts, nightly only. The nightly job already runs `--cov --cov-context=test` but uploads timings only. Add the `.coverage` data (or a derived "lines only this test covers" report) to the artifact. Ringer task; no `--cov` locally.
3. Mutation checks on the candidates the report flags: delete or break the guarded line, confirm no other test fails, then delete.

## Stage 1b: probe and experiment scripts retired (2026-11-19, branch `retire-probe-scripts`, not committed)

Ringer run `probe-retire-and-coverage-report` (two tasks, both passed first try) plus `probe-retire-fix` (one task). Builders and checks in `scripts/ringer/probe-retire/`.

- Removed 213 files: 30 probe tests, `tests/fixtures/opening_truck_probe`, `bench/frozen_decode.py` and `bench/rejudge_frozen.py` with their tests (unused; only two historical run scripts named them), the folders `scripts/ringer/opening_truck`, `phase1`, `phase2`, probe files and probe data folders in `environment_narration` and `transcript_1a`, and the 3a-open-issues `stepD1V`/`stepA3` scripts. Also two tests of the deleted t9h probe manifest.
- Kept on purpose: `bench/frozen_prompts.py` (used by `bench/exit_audit.py`), all of `scripts/ringer/stage7` (its `door_probe.py` is the documented live-bench procedure in `docs/testing-runbook/live-narration-bench.md`), the `*_repro` tests and `test_2c_probe_fixes`/`test_contract_probe` (they test engine behaviour, not scripts).
- Restored because surviving code loads them: `drain_condition_judge_probe`, `j1_scope_probe`, `j1_screen_probe`, `j1c_wiring_probe`, `hidden_bench_prose_probe` (environment_narration), `act2_probe`, `slice_probe` (phase1), `boarding_probe` (transcript_1a). They now have no tests of their own.
- Suite: 4,768 collected before, 4,454 after (4,429 passed, 25 skipped, 6m51s). `tests/shard_durations.json` pruned of 32 stale entries.
- Missed by my first import scan and caught by the full suite: tests that load a script by a built path (`hidden_bench_prose_probe.py`, the t9h probe manifest). Lesson: run the full suite, not the import closure alone.
- Historical run manifests and builders under `scripts/ringer/environment_narration` still name deleted files; they are run records and were left alone.
- Added `scripts/coverage_redundancy.py` and a nightly step that uploads `artifacts/test-redundancy.json` (per-test unique lines, tests with none, identical groups). First data arrives with the next nightly run after merge. Stage 3 (mutation checks) follows from that report.
