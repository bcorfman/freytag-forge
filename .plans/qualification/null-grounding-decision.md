# Outcome contract: where the null grounding comes from

**Status: adopted by the owner, 2026-11-23.** From a read-only Opus review at `main` `97fdde35`. The contract wording below is applied to `qual-20261122/qualification/step2-spec.md` item 2, and F3 now lists pacing events. Nothing was built, run or billed. It closes the design gap that blocked task 2.2b in [Step 2](step-2-measurement.md): the contract needs `null_grounding_ids`, and no saved report records them. Build work is tracked as checkboxes in Step 2.

**Read this when:** you build 2.2b (telemetry capture), change how `classify_run` treats timed reveals, design the F3 anti-flattening guards, or edit the "pressure event" rule in `qual-20261122/qualification/step2-spec.md`.

## Summary

Before this decision, the contract said a reveal is progress only if it would not also appear under a null action (`wait`) on the same state (`step2-spec.md:33`). Two sources were proposed:

- **Option A:** derive it from what the engine fires on its own (pacing events and clock-triggered storylets), with no model call.
- **Option B:** make one real narration call per turn on a copy of the state.

**Decision: a narrowed Option A, "pacing-only replay".** Before each turn's pacing pass, the engine replays only that pass on a copy of the pre-command state. The copy gets the same turn advance and none of the command's effects. Every pacing event that fires in the replay is a pressure event, and the knowledge it makes deliverable goes into `null_grounding_ids`. Clock-opened storylets are left out. No narration call is made.

The criterion was fun as the plans define it, not cost.

## Why not Option A as written

A storylet the clock opens only becomes available. The player still has to act to get it.

- `_activate_pacing` adds a storylet to `active_event_ids` when `earliest_turn <= turns_since_entry` (`storygame/runtime/engine.py:1359-1366`).
- Delivery still needs the command to match: exact match first, then the semantic matcher (`storygame/runtime/cloudflare.py:514-520`).
- In Continuity Initiative, 57 of 69 storylets are clock-open from scene entry, and 25 are gated on facts a pacing event sets. (Counted from a read-only load of the package.)
- Counting clock-triggered storylets as null grounding would erase nearly every earned reveal. In 1C replicates 1 and 3, every new grounding is the command's matched candidate (`reports/r4-1C.json`), and those turns would read as futile.
- The factory would then "repair" healthy scenes by broadening matchers and adding handoffs. That is the flattening the qualification plan warns about (fun requirement 4).

## Why not Option B

- **Its baseline is random.** The narrator is told to pick randomly when several candidates match (`cloudflare.py:963-969`). The baseline would differ between replicates and between hosted play and the probe. That breaks the contract's purity (`outcome_contract_fixtures/README.md:3`) and the cross-path parity M1 requires.
- **Noise feeds the probe keep rule.** The cheapest way for the factory to cut that noise is to make every reveal a deterministic exact-match handoff and broaden matchers, which flattens the game.
- **It costs the live player, or the measure drifts from play.** In live play it doubles narration calls against the 10-second latency target and uses up the shared 40-call semantic-matcher budget (`cloudflare.py:658`). Run only in the harness, the measured play is no longer the delivered play.
- **There is no null action to call.** "Wait." is an ordinary narrated turn, and "wait" is a retraction word in the matcher (`storygame/runtime/candidate_matcher.py:44-46`).
- **Its one advantage barely shows.** It could catch the narrator volunteering a non-pacing reveal on a futile turn. In all 54 turns of the r4-3B, r4-1C and r4-2C reports, every new grounding ID equals `matched_candidate`.

## How pacing-only replay steers repairs toward fun

- **The world pushing and the player pushing stay separate.** A pacing event earns pacing credit (it resets `quiet_stretch`, `factory/outcome_contract.py:194`). Only the player's command earns credit against stuck. That is the thriller contract: a visible clock plus earned exits ([factory plan, Pace](../Continuity%20Initiative%20dark%20factory%20plan.md#pace-the-thriller-contract)).
- **Timed hints can't hide stuck turns.** A scene can't pass by adding hint beats on a timer.
- **The world reacting to the player still counts.** A pacing event that fires only because the command changed a fact won't fire in the replay, so it counts as progress. An example is the `restricted_corridor_access` guards in `data/stories/continuity-initiative/source/scenes/2A.yaml:263,301`.
- **Its own risk.** The factory could turn clock beats into command-gated reveals to earn progress credit, losing the visible clock. **Added to the F3 guard set (2026-11-23):** a candidate must not lose a pacing event the control delivered. Before this, the list covered earned reveals, NPC moves, exploration and payoffs, but not pressure events.

## Engine facts the design must respect

- **Where `grounding_ids` come from.** Only three sources add them:
  - the narrator's segments, limited to committed or selected knowledge (`storygame/runtime/validation.py:275-279`);
  - grounding the engine derives for a selected item the narrator didn't tag (`validation.py:284-301`);
  - authored handoff segments (`cloudflare.py:1552-1556`).
- **Engine-timed text carries no grounding.** Pacing complications (`engine.py:385`), staged cues (`cloudflare.py:1596`) and the placeholder segment for a transition-firing pacing event (`engine.py:1405-1407`) have none. A pressure event shows up in `grounding_ids` only when the narrator grounds a knowledge item tied to it, such as `k_inspection_window_missed` or `k_supervisor_escorting` in 2A. These are among the 31 items the narrator can select; the other 91 are delivered by the runtime.
- **There is no typed link from a pacing event to its knowledge item.** The only connection is the naming pattern (fact `inspection_window_missed`, item `k_inspection_window_missed`), and `k_supervisor_escorting` names storylet SL-2A-D as its source. Pacing-only replay needs a typed link declared in the story source, not name parsing.
- **Exploration that reveals nothing gets no grounding ID (separate, larger fun risk).** Only knowledge IDs are allowed (`validation.py:275`), so fixture IDs like `g_shelf` and `g_console` can't occur in real play. A real "look around and the world answers" turn comes out `no_effect` unless it commits a fact, and it counts toward stall runs. That pushes repairs toward "a reveal on every action". Neither option fixes this; it needs its own decision before the contract certifies anything.
- **Already-known knowledge can come back as new.** r4-2C turn 2 re-grounds `k_sl_2b_b_r4` from 2B. Unless `scene.delivered_before` is filled from earlier scenes, the contract reads it as new, marks the turn `explored`, and hides a stall.
- **Pressure events are already free to record.** The hosted payload has `fired_pacing_event_ids` (`storygame/web_demo.py:112-114`), and `turnRecord` keeps `state` (`frontend/e2e/blind-player.js:238`). The saved r4 reports dropped `state`.

## Effect on the frozen examples (`outcome_contract_fixtures/cases.json`)

| Source | Fixtures that change |
|---|---|
| Pacing-only replay | None. `timed_reveal_masks_futile_action` already has this shape. |
| Option A as written | `earned_reveal` turn 1, `healthy_no_failures` turn 2, `pacing_numbers_mixed` turn 2 and `character_cites_learned_event` turn 1 lose progress or exploration credit if the adapter treats their storylet as clock-opened. The fixtures carry no activation data, so the outcome depends on the adapter. |
| Option B | No change as data, since `classify_run` is pure. But live runs couldn't reproduce `timed_reveal…`, and the unmatched `k_c1` reveals in `healthy_no_failures` and `pacing_numbers_mixed` could flip at random. |

**The M4 fixture is to be strengthened** (a Ringer task in Step 2; the frozen copy lives in `tests/fixtures/outcome_contract/` and the workspace):

- Every input is "Wait by the door." A player who waits isn't trying to progress, and the spec asks for a timed reveal during a futile command (`step2-spec.md:46`). Use a futile command instead.
- Add two counterexamples:
  - pressure fires on a turn where the command earns a different reveal (that reveal is progress);
  - a pacing event fires only because of the command's own fact (progress).

## Open questions and the cheapest evidence

All of these are free checks.

1. **How pacing-linked items get committed and grounded.** Their `earn_when` is None. Read `KnowledgeProjector._candidates` and the 2A source, or use `bench describe/prompt` at the 2A turn-5 state. Never `bench run`, which bills.
2. **Whether a state copy plus a pacing-only replay has no side effects.** Entry snapshots already serialize state (`storygame/runtime/entry_snapshots.py:154,273`). Settle it with a unit test. If the replay is world-state-only logic, it belongs in `packages/worldkeeper`.
3. **How often the narrator volunteers reveals with no command match.** Scan all saved blind-player reports for new grounding that isn't the matched candidate.
4. **Which matcher produced `matched_candidate`** (exact or semantic). The reduced reports don't record it. 2.2b should add a per-ID `grounding_source`.

## Contract wording, applied to `step2-spec.md` item 2

Applied 2026-11-23. `classify_run` itself is unchanged; only the definition of its `null_grounding_ids` input changed. No saved report ever carried that field, so nothing needs re-adjudication and the contract stays v1:

> 2. **Knowledge progress**: a reveal the command caused. Attribution is deterministic and makes no narration call. Before the turn's pacing pass, the engine replays only that pass on a copy of the pre-command state, with the same turn advance and no command effects. Every pacing event that fires in the replay is a pressure event. The knowledge it makes deliverable, through a typed link in the package, goes in `null_grounding_ids`. A grounding in that list is a pressure event, not progress. A pacing event that fires only because the command changed a fact is the world answering the player, and its grounding is progress. A storylet the clock merely made available is never null grounding, because the player still earned it by acting. Each grounding ID records its source (command match, narrator selection, re-grounded, pacing) for the calibrated review.

## What 2.2b would then own

- Record per turn: `null_grounding_ids` (from the replay), `pressure_event` (from the `fired_pacing_event_ids` diff), `grounding_source`, and keep `state` in saved reports.
- Add the typed pacing-event-to-knowledge link in the story schema and compiler, with a validator that rejects an unlinked pacing-linked knowledge item.
- Write the replay test first. A recorded run must round-trip through `classify_run` with no `unknown_telemetry`.

## Free check results (2026-11-24)

Read-only; no model call, no code change. Reports scanned: all seven saved blind-player reports in `qual-20261122/reports/` (1B, 2A, 2B, 3A, r4-1C, r4-2C, r4-3B-seeded; 123 turns).

1. **Pacing-linked knowledge is linked through facts, not names.** A pacing event `sets` facts (2A `inspection_window_2a` sets `inspection_window_missed`; `inspection_nudge_2a` sets `supervisor_escorting`). The knowledge item that surfaces it (`k_inspection_window_missed`, `k_supervisor_escorting`) has no `earn_when` and no `action_evidence`, and is delivered as a bridge reveal that commits or reads those same facts (`2A.yaml` reveals `bridge_2a_missed_window_recovery`, claims at lines 825 and 904). So the typed link can be derived from the intersection of an event's `sets` facts and an item's `commits` or `when` facts. The validator then rejects a pacing-linked item whose facts no event sets. Whether to derive or to declare it explicitly is a design choice for the 2.2b typed-link task. I did not verify every item in the package, only 2A.
2. **Replay needs a copy; it is not safe on live state.** `RuntimeEngine._activate_pacing` (`engine.py:1330-1462`) writes facts, `fired_event_ids`, `active_event_ids`, `last_turn_delivery`, staged cue and handoff fields, applies world actions and, for a transition event, calls `apply_proposal`. Run on a `copy.deepcopy` of the pre-command state (the pattern `entry_snapshots.py:109-124` already uses) it cannot touch the live game. The side-effect-free claim still needs the unit test (original task). The event rule itself reads only facts, `turn_index`, `scene_entered_at_turn` and the package's pacing events, so most of it could be a `World` method only if `World` holds the pacing events; otherwise it stays a runtime adapter. Decide that when writing the test.
3. **Volunteered reveals: 12 of 123 turns have a new grounding that is not the matched candidate; 3 are real, 9 are re-grounding.** The earlier "all 54 turns equal `matched_candidate`" held for the three r4 reports only (r4-2C turn 2 is an exception, below).
   - Re-grounding of knowledge delivered earlier or at entry (9 turns): `k_sl_1a_b_r1` in 1B, `k_scene_2a_entry` in 2A, `k_sl_2b_b_r4` in 2C. This is the `scene.delivered_before` task, and it is the main source of false progress.
   - Pacing items with no matched candidate (2 turns): 2A replicate 1 turn 5 `k_supervisor_escorting`; 3A replicate 2 turn 7 `k_bridge_3a_command_assault`. These are what the replay is meant to classify as pressure.
   - Bridge items delivered beside a matched candidate (2 turns): `k_bridge_2b_archive_crisis` with `k_sl_2b_c_r3` in 2B. Treat as runtime-delivered; the replay decides whether they are pressure.
   - The narrator volunteering a reveal on a futile turn was not seen.
4. **Matcher source is only partly recorded.** Each turn has `semantic_match.ran` and `semantic_match.matched`. `matched` equals `matched_candidate` on 1 of 123 turns (3A); the semantic matcher ran on 57 turns and matched on one. So nearly every matched candidate came from the exact matcher or from the semantic result being dropped, and the reports cannot tell which. Capture a per-ID `grounding_source` as planned.

Effect on the tasks: the typed-link task may collapse into a derived link plus a validator; the `delivered_before` task moves up, because it affects nine times as many turns as the pacing cases.
