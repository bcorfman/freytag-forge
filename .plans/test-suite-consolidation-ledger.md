# Test-suite consolidation ledger

Status: draft 1, 2026-10-23, HEAD `5ea3c750`. Built from the Phase 1 evidence in
[test-suite-consolidation-plan.md](test-suite-consolidation-plan.md) sections 2b and 2c.
No test was changed. One row per candidate cluster, not per test; the per-test data stays in
`/home/bcorfman/dev/ringer-work/test-review/` (`analysis/coverage-analysis/coverage-analysis.json`,
`pertest-nocov.json`, `round2/scan2/scan2.json`).

## How to read the numbers

- **Seconds** come from one quiet no-coverage run (3:31 wall, 16 workers, 2,994 tests, 0 failed).
  They are per-test times under 16-way load, so they sum to 2,184 s, not the 3:31 wall time.
  Use them to rank, not to promise a saving.
- **No-unique** means the test covers no line or branch arc of `storygame/` that no other test
  covers. It is an overlap signal only. Almost every test is no-unique (2,494 of 2,756), so it
  cannot justify a deletion alone. The mutant panel (plan D7) is what decides.
- **Unstable** tests (40) differ between two identical coverage runs. None is credited as a
  retained cover.
- **Verdicts** use the plan's section 5 words. `Needs panel` means: no deletion until the mutant
  panel shows the candidate is never the only test that fails for a real past defect.

## Rows

| id | class | cluster | tests | seconds (no-cov) | evidence | proposed verdict | status |
| --- | --- | --- | --- | --- | --- | --- | --- |
| L1 | A | `test_existing_arm_dry_run_remains_byte_stable` in `test_3c_families_offer_arm.py` and `test_3c_no_close_arm.py` | 2 | 64.6 and 42.8 | Bodies are character-identical: same `probe.dry_run` call, same checked-in `bench/results/stage7-3c-carried-dry`. No unique coverage | **Delete one** (a human picks which file keeps it; both files were added on 2026-10-22). Saves 42.8 to 64.6 s of the 2,184 s sum, 2 to 3% | ready for review |
| L2 | B | `test_engine_path_preserves_negation_scope` (`test_command_split_negation.py`) vs `test_engine_provider_path_respects_negation_scope` (`test_negation_scope.py`) | 6 cases | 1.0 | Same body, but the inputs differ ("anything yet" with a comma versus a semicolon) | **Merge** into one parametrized test keeping every case. Negligible time; reduces copy-edit risk only | ready for review |
| L3 | B | `test_scene_2c_c_r1_matches_natural_player_actions` vs `..._entry_text_actions` in `test_candidate_matcher.py` | 2 tests, 11 cases | under 1 | Same body, different input lists | **Merge** only if the two lists carry different intent; otherwise **Keep** | needs human |
| L4 | B | 19 near-duplicate clusters from the looser scan (ratio at least 0.75) | not counted | not summed | The four largest clusters I read are same-file tests differing in one setup call or one assertion, so they check different outcomes; the rest are unread | **Keep**; fold into parametrization only when a file is touched for another reason | no action |
| L5 | C/D | Closed 3C experiment arms: `test_3c_families_offer_arm`, `test_3c_item_facts_arm`, `test_3c_no_close_arm` | 14 | 148 | All 14 no-unique. Two of them (the L1 pair) take 43 and 65 s and replay checked-in dry-run artifacts | **Needs panel**, then human: which arm results are still contract, which only history | batch (b) |
| L6 | C | Heavy 3C replays: `test_3c_carried_start`, `test_3c_kristin_place`, `test_3c_item_facts_capture`, `test_3c_state_compare`, `test_three_c_prefix`, `test_3c_cue_chain` and the rest of the 3C family | 174 in 22 files | 581 (27% of the suite), 562 of it no-unique | 153 no-unique. Five tests above 30 s are here: `item_facts_capture` 71, `families_offer_arm` 65, `kristin_place` 64, `no_close_arm` 43, `three_c_prefix` 30 | **Needs panel**. Highest payoff in the suite | batch (b) |
| L7 | B/C | `test_bench_item_facts.py` and the other `test_bench*` files | 369 in 4 files | 249; item_facts alone 209 | 278 no-unique; 12 parametrize decorators over 278 tests | **Needs panel**, parametrization audit by hand (decision D1) | batch (d) |
| L8 | C | `*_repro` characterizations: `test_2c_paths_repro`, `test_concealment_repro`, `test_drawer_avoidance_repro`, `test_late_scene_repro` | 47 in 4 files | 74 | 44 no-unique; each replays a multi-scene path. Whether a journey asserts the same observable is not yet checked | **Needs panel**, then a human check that a journey asserts the same observable | batch (c) |
| L9 | B | Per-scene `*_spine_prompts` files | 9 in 7 files | 4 | Small, one frozen (`1c`) | **Merge** into one parametrized file after reimagination step 7; time gain negligible, maintenance gain only | batch (e), low priority |
| L10 | D | `test_phase3_evidence`, `test_phase4_api_contracts`, `test_phase4_evidence` | 6 in 3 files | 2 | 3 no-unique; no obsolescence signal found | **Needs human**: are the phase contracts still stated elsewhere? | batch (f), low priority |
| L11 | C | Journeys: `test_game_path_journeys`, `test_evidence_gap_journeys`, `test_canon_journey`, `test_game_path_completion` | 359 (71 + 16 + 5 + 267) | 610 (486 + 103 + 19 + 2) | All no-unique; all frozen by the reimagination plan | **Frozen**. Time sits in the engine (`facts.matching`, `knowledge._established`), not in the tests | phase 4 |
| L12 | D | One unconditional `pytest.skip` in `test_incident_characterization` | 1 | 0 | Frozen file | **Frozen** | phase 4 |
| L13 | none | 238 tests with no `storygame` coverage (bench harness, script and data tests, the 16 skips) | 238 | not summed | Coverage cannot rank them: 47 in `test_raw_language_corpus`, 33 in `test_bench`, 16 in `test_pipeline_eval`, 13 in `test_game_path_completion` and others | **Needs human** read by file; not part of any batch until read | open |

Not found: no test references a removed module, symbol or `.plans/` file (the scan reported
none; its three missing-path findings in `test_shard_balance` are intended fixtures). The
obsolete-test class D is nearly empty on this evidence.

## What this means for the stop rule

The plan stops Phase 3 if under about 10% of the 1,949 file seconds (about 195 s) is removable
outside the frozen set. Upper bound from coverage alone, non-frozen: 1,193 s no-unique. The
rows that matter are L1, L5, L6, L7 and L8: 562 + 148 + 209 + 74 = about 990 s of no-unique
tests, plus L1. That clears 195 s only as an upper bound; the real figure waits for the mutant
panel. The honest expected result is a fraction of that, concentrated in the 3C family.

## Next

1. Build the mutant panel (D7) on L5, L6, L7, L8 first: 50 commits whose `storygame/` part
   reverse-applies at HEAD; record each commit's kill set across the full suite.
2. Brandon reviews this ledger by cluster, then the reviewer pass on every Delete or Merge row.
3. Batch (a): L1 and the two Merge rows, as one Ringer manifest.
