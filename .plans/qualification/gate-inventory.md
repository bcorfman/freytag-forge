# Gate inventory (ladder rung R0)

Part of the [gate-proving ladder](gate-proving-ladder.md). Built 2026-11-23 at `main` `97fdde35` from a read-only survey of the source, git history and CI workflows. No tests were run. The only measurement was the free, read-only `scripts/audit_copied_prose.py`.

**Read this when:** you start R1 or R2, add or remove a gate, or need to know which gate blocked a change and why it exists.

## Summary

- **A single story change can be blocked by about 22 content gates.** Inside them sit roughly 360 individual rules:
  - 8 layer-1 and 18 layer-2 source rules;
  - about 250 load-time error sites across 15 package validators;
  - 6 gap rules;
  - 31 runtime rejection codes;
  - about 25 fix-plan lints and 11 contract lints;
  - 8 fun checks.

  Eight more gates are process gates that never judge content.
- **The heaviest false-block risk is concentrated, not spread evenly.** Five places deserve R1 first (listed under "R1 priorities" below):
  - the live gate's all-or-nothing replicate rule;
  - the hosted stuck heuristic;
  - runtime rejections feeding that gate;
  - the full CI suite as a story gate;
  - station 10 needing eight yeses.
- **Four signals are measured by two or more gates** (stuck, leaks, prompt size, "every state has a way out"). These are where R2 conflicts and R1 merge candidates will come from.
- **Copied prose in tests is nearly gone:** 3 test files copy 4 authored sentences. But 279 of the 400 test files name real-story IDs or the story path, and the full suite runs in CI before any factory merge. How many of those pin behaviour rather than just load the package is unmeasured (R1 task).

## Content gates

"Hard" blocks the ticket. "Ratchet" blocks only new failures against a baseline. "Report" never blocks. The origin column is the commit that introduced the gate (found with `git log -S`), the nearest free proxy for the incident it exists for.

### Authoring and compile time (deterministic, free)

| # | Gate | Where it runs | Reads | Kind | Origin |
|---|---|---|---|---|---|
| 1 | Source layer 1: 8 shape rules (`L1.enum`, `id_pattern`, `missing_key`, `unknown_key`, `type`, `match_scene`, `lexicon_off`, `plural_off`) | `story_source/l1_root.py`; station 5 `source_tree`; story CLI on every write | Source YAML | Hard | `f2ad94d3` (11-16) |
| 2 | Source layer 2: 18 reference and ownership rules (`L2.claim_authorized`, `ending_scene`, `incident_observes_outcomes`, `match_coverage`, `override_add_only`, `ownership`, `scene_scope`, `dangling_ref`, `duplicate_id`, `fact_declaring_scene`, `fact_one_owner`, `unplaced_fact`, `drop_unused`, `lock_stale`, `order_id`, `delivery_unseen`, `transition_source`, catalog) | `story_source/l2_*.py`; station 5; story CLI | Source YAML | Hard | `0ca388be`, `b751478e` (11-16) to `50ab46ae` (11-18) |
| 3 | Source compile | `compile_source_tree`; station 5 | Source to package | Hard | — |
| 4 | Package load validators: 15 functions, about 203 error sites in `loader.py` and 49 in `models.py`. Covers disclosure guards, knowledge, authored handoffs, ending, narration term traps, entry variants, deliveries, incidents, connections, transition trigger sources, resolution entry guarantees, required reveal prerequisites, incidental declarations, scene placements, axes | `story_package/loader.py`, `models.py`; every load, so every later gate | Compiled package | Hard | 2026-08-30 to 11-02; e.g. `3f2f1bc7` "Reject story packages that could strand a scene exit" |
| 5 | Gap rules: `no_strand`, `single_reveal_strand`, `no_producer`, `custody`, `co_location`, `twin_reveals` | `story_package/gap_rules.py`; station 5 `gap_delta` | Package | **Ratchet** (new results only; existing gaps pass) | `f403c4ae`, `4e233612` (11-10); `twin_reveals` `3d83a6c9` (11-21) |
| 6 | Carry matrix, one branch | `factory/checks/carry_matrix.py`; station 5 | Package, scripted provider | Hard (stuck or unreachable state) | `6b3bf8b9` (11-20) |
| 7 | Carry matrix, pairwise | `carry-matrix-nightly.yml` | Package | Report (uploads artifact) | — |
| 8 | Prompt size cap: 6,500 characters of worst-case narration context per scene, warning at 6,400 | `tests/test_prompt_budget.py`, `tests/test_audit_budget.py`, `storygame/audit_budget.py` | Package, assembled prompts | Hard (CI test) | `41e567b0` (11-02) |
| 9 | Leak and disclosure tests (declared-name leak scan, enforced leak terms, disclosure guards, knowledge-leakage matrix) | `tests/test_leak_terms_enforced.py`, `test_disclosure_guards.py`, `test_knowledge_leakage_matrix.py` and others | Package, narration | Hard (CI test) | — |
| 10 | Scripted journeys (92) and the unreachable ratchet | `tests/test_game_path_journeys.py` (nightly), `test_known_unreachable_ratchet.py`; `journey_reachability_check()` not yet wired into station 5 | Package, scripted play | Hard nightly; ratchet hard in CI | #820, #825 (11-23) |
| 11 | Full test suite: 400 files, six shards | `test.yml` on every PR; station 5 runs only the ticket's listed tests, then station 9 re-runs free gates and CI runs everything | Code and package | Hard before any merge | — |
| 12 | Contract lint: 11 rules (`contract.beats`, `clock`, `delay_cost`, `feeling`, `harm_ladder`, `npc`, `pacing`, `placeholder`, `setpiece`, `shape`, `world_need`) | `factory/contracts/lint.py`; stations 0 and 1 | Scene contracts (none authored yet) | Hard | — |
| 13 | World-need check | `factory/checks/world_need.py`; station 2 | Contract plus package | Hard (opens world tickets) | — |

### Repair-shaping gates (they judge the factory's planned change, not the story)

| # | Gate | Where | Kind | Origin |
|---|---|---|---|---|
| 14 | Fix-plan lints: about 25 `plan.*` codes, e.g. `plan.empty_effect`, `redundant_effect`, `shared_effect`, `exit_trigger`, `claim_offered`, `phrase_owned`, `contradicted_cause`, `skipped_preconditions` | `factory/stations/fix_plan.py`; planner retries on them | Hard (replan) | Mostly rounds 18 and 19 (11-22); `empty_effect` from the 19m 1A run |
| 15 | Wiring checks: `beat_position_error`, `claim_evidence_change_error` | `factory/stations/wiring.py`; station 4 | Hard (replan) | 19n (11-22) |

### Runtime, every narrated turn (deterministic validators on model output)

| # | Gate | Where | Kind |
|---|---|---|---|
| 16 | 31 proposal rejection codes, e.g. `invalid_grounding_reference`, `ungrounded_selection`, `missing_knowledge_content`, `disclosure_guard_leak`, `narration_known_term_leak`, `protected_narration_leak`, `world_fact_mutation`, `dialogue_grounding_not_sayable`, `embellishment_rejected`, `unsatisfied_transition_triggers` | `storygame/runtime/validation.py`, `cloudflare.py`, `narration_safety.py` | Rejects the turn and retries. **A rejection that reaches the player counts against gate 17.** |

### Live and billed

| # | Gate | Where | Kind | Origin |
|---|---|---|---|---|
| 17 | Live playtest gate: **every** replicate needs stuck = 0, rejected = 0, game breaks = 0, a fired transition and an earned exit | `live_playtest.py::_gate_passes`; station 7 | Hard, all or nothing | `de172eff` (11-21) |
| 18 | Hosted stuck heuristic (the input to 17): a turn is stuck unless it names an affordance, adds a storylet, or adds a grounding ID versus the previous turn | `frontend/e2e/blind-player.js::analyseRun` | Hard via 17 | — |
| 19 | Probe keep rule: candidate stuck rate at most 0.8 × control; no more rejections or game breaks; earned-exit rate not lower; control needs at least 1 stuck turn; 3 replicates | `probe.py::judge_probe`, `factory/config/probe_rules.json` (frozen); station 12 | Hard (comparative) | `478fc4c6` (11-22) |
| 20 | Probe stuck measure (the input to 19): absence of selected knowledge and new grounding across the run | `probe.py::summarize_arm` | Hard via 19 | — |

### Model judges

| # | Gate | Where | Kind | Origin |
|---|---|---|---|---|
| 21 | Fun review: 8 yes/no checks, **all** must be yes (`fits_scene`, `gives_a_reason_to_act`, `keeps_pace`, `fits_freytag_phase`, `characters_in_character`, `continuity_within_scene`, `continuity_between_scenes`, `delights_the_player`); a block sends advice back to the planner | `fun_review.py`; station 10, Opus | Hard | `33ac2fdb` (11-22) |

### Built but not yet wired

| # | Gate | Status |
|---|---|---|
| 22 | Outcome contract (`confirmed_stuck`, `unresolved`, provenance flags, pacing numbers) | `factory/outcome_contract.py`, PR #824; wiring is Step 2 tasks 2.2 to 2.4. It is meant to replace 18 and 20. |

Planned, not built: the whole-game fun gate (F1), pacing bounds (F2), the anti-flattening guards (F3), and the delivery report validator (2.6).

## Process gates (never judge content; out of scope for false-block testing)

Model pinning (`factory/guard.py`), frozen config (`factory/frozen.py`, `factory/config/**`), circuit breakers (`breakers.py`), spend and usage limits (`limits.py`, `max_usd`), Ruff, the station 9 checks (protected paths, diff unchanged during delivery, staging SHA, CI green), the 90% nightly coverage gate, and production promotion checks.

## Signals measured by more than one gate

| Signal | Gates | What R1 and R2 should test |
|---|---|---|
| Stuck | 18 (hosted), 20 (probe), 22 (contract, unwired), plus 6 and 10 structurally | Known disagreement (defect M1). R1 measures each on the same fixtures; the plan is for 22 to replace 18 and 20. |
| Leaks and disclosure | 4 (narration term traps, disclosure guards), 9 (leak tests), 16 (three leak rejection codes) | Same violation caught once or three times; a plain-name fix must pass all three. |
| Prompt size | 8 (two tests of one 6,500-character cap) | Merge candidate. |
| Every state has a way out | 4 (`transition_trigger_sources`, `required_reveal_prerequisites`), 5 (`no_strand`), 6, 7, 10 | Five ways of asking one question. Find which one catches anything the others miss. |
| Character knowledge | 16 (`dialogue_grounding_not_sayable`), 21 (`characters_in_character`), 22 (`character_knowledge` flag) | Agreement on the same fixture. |
| Continuity | 16 (`world_fact_mutation`, `canonical_fact_mutation`), 21 (two continuity checks) | Agreement on the same fixture. |

## R1 priorities: where false blocks most likely concentrate

Measured so far ([R1 results](gate-r1-results.md)): priority 2 (R1a: 12 of 15 good runs wrongly blocked), priority 3 in part (R1b: only the term-leak guard is visible in saved telemetry) and priority 4 statically (R1c: 268 of 400 files pin story IDs). Priority 1 follows from 2 and 3; priority 5 waits on R1d.

1. **Gate 17's all-or-nothing rule.** One stuck turn, one rejection or one game break in any replicate fails the scene. Gates 16 and 18 feed it, so their false-block rates multiply through it.
2. **Gate 18, the hosted stuck heuristic.** Known defects M2 and M3: it misses futile named-object commands and flags successful world actions. The seeded 3B run flagged 30 of 37 turns. Until 22 replaces it, a correct repair can fail station 7 on measurement alone.
3. **Gate 16, runtime rejections.** Each code is a classifier on model output. Their false-rejection rate on good narration has not been measured as a stack.
4. **Gate 11, the full suite as a story gate.** 279 of 400 test files name real-story IDs or the story path. A test that pins old behaviour blocks a correct story change in CI. The standing rule lets Ringer specs update such tests, but the factory's own tickets need the same allowance.
5. **Gate 21, eight yeses.** If each check wrongly says no 5% of the time, a good change passes only 66% (0.95^8). Station 10 has no measured false-block rate yet.

## What R0 could not establish

- The incident behind each gate beyond its introducing commit. The commit subjects give the reason for most of the authoring gates; the runtime codes were not traced one by one.
- How many of the 279 story-naming test files pin behaviour rather than only loading the package.
- Whether the gap-rule baseline (gate 5) currently holds known gaps that a repair could accidentally "fix" and then be blocked for touching.
- Real pass and block rates for any gate. That is R1's job.

## Next (R1)

- Build the good set from saved, evaluator-judged runs; seeded faults, one per gate purpose; meaning-preserving variants.
- Measure in the order above: 18 and 22 first (one fixture file, both measures), then 16 on saved good narration, then 11's behaviour-pinning count, then 21's calibration (Opus designs it; figures first).
