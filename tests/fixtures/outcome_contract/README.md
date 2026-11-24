# Outcome contract v1 (draft, frozen examples in cases.json)

One pure function classifies a run (one replicate of one scene) the same way for hosted play, the bench probe, qualification and delivery:
`classify_run(run: dict, scene: dict) -> dict` in `factory/outcome_contract.py`. It never reads files, the network or a model, and never raises on malformed input (a bad field makes that turn `unknown_telemetry` or the run `unresolved`).

## Inputs
`run`: `{replicate, entry_facts: [str], turns: [turn]}`.
`turn` fields: `turn` (int), `input`, `text`, `outcome` ("committed", or something else such as "question"), `rejected` (bool), `game_break` (null or an object), `story_complete` (bool), `grounding_ids` ([str]), `null_grounding_ids` ([str] or null: the grounding ids the same state produces when the player does nothing, i.e. a `wait`), `committed_facts` ([str] or null: facts this turn committed), `candidates_offered` ([str]), `matched_candidate` (str or null), `transition_cause` ("none", "earned", "play", "forced", "timer"), `pressure_event` (bool), `npc_move` (bool), `ending_latched` (bool), optional `recovery` `{cost_committed, cost_shown}`.
`scene`: `{id, pacing_window (int or null), terminal (bool), reveal_ids [str], delivered_before [str], ending_requires [str], non_voiceable_says [str], unlearned_terms [{term, requires}], epilogue_candidates [str]}`.

## Per-turn classification (all four are stored; raw harness flags are never replaced)
`action_outcome`, first match wins:
1. `game_break` if `game_break` is not null.
2. `rejected` if `rejected` is true or `outcome == "rejected"`.
3. `noncommitted` if `outcome != "committed"` (neutral, like rejected).
4. `unknown_telemetry` if `committed_facts` is null or `null_grounding_ids` is null.
5. `world_changed` if `committed_facts` is non-empty.
6. `explored` if the turn has a NEW attributed grounding id (below).
7. `no_effect` otherwise.
Attributed grounding = `grounding_ids` minus `null_grounding_ids`. NEW = attributed minus `scene.delivered_before` minus every grounding id of any EARLIER turn in the run.
`knowledge_progress` (bool, or null for unknown_telemetry/game_break/rejected/noncommitted turns): true when NEW intersects `scene.reveal_ids`. A world_changed turn can also have it true.
`authored_recovery` (bool): true only when `recovery.cost_committed` and `recovery.cost_shown` are both true.

## Stall runs and stuck
A stall run is a maximal sequence of turns whose `action_outcome` is `no_effect` and whose `authored_recovery` is false, ignoring neutral turns (`rejected`, `game_break`, `noncommitted`) which neither extend nor break it. Any other turn (world_changed, explored, authored_recovery true, unknown_telemetry) ends it.
- If `scene.pacing_window` is null: every `no_effect` turn is `unresolved`.
- Else if the run's length >= `pacing_window`: if at least one turn of the run has a non-empty `candidates_offered`, every turn of the run is `confirmed_stuck`; otherwise every turn of the run is `unresolved` (nothing was on offer, so it must be adjudicated, not certified).
- A `unknown_telemetry` turn is always `unresolved`.
Lists are sorted ascending turn numbers.

## Exit
If any turn has `story_complete` true: `ending` when `scene.terminal` is true and every id in `scene.ending_requires` is in `run.entry_facts` union all `committed_facts`; otherwise `unknown`. Else the last turn whose `transition_cause` is not "none" decides: "earned" or "play" -> `earned`; "forced" -> `forced`; "timer" -> `timer`; any other value -> `unknown`. No such turn -> `none`.

## Run status
`unresolved` if any unresolved turn; else `stuck` if any confirmed_stuck; else `flagged` if any provenance flag; else `healthy`.

## Extension tier (separate task)
- `provenance_flags` (list of `{turn, kind}`):
  - `bookkeeping_voiced`: a double-quoted segment in `text` contains a string from `scene.non_voiceable_says` (whitespace-normalised substring).
  - `character_knowledge`: a double-quoted segment contains an `unlearned_terms[].term` (case-sensitive) and the `requires` id is not in `scene.delivered_before` nor any grounding id of the same or an earlier turn.
  - `epilogue_not_offered` (turn null): `scene.epilogue_candidates` is non-empty, the run's exit is `ending`, and no turn at or after the first `ending_latched` turn has a `candidates_offered` entry in `epilogue_candidates`.
- `epilogue`: `{offered, taken}`; offered as above; taken when `matched_candidate` of such a turn is in `epilogue_candidates`.
- `pacing`: `scene_length` (number of turns), `turns_to_first_pressure` (turn number of the first `pressure_event`, or null), `quiet_stretch` (longest run of consecutive turns AFTER the first pressure event with no knowledge_progress, no pressure_event and no npc_move), `exploration_share` (turns with action_outcome `explored` divided by scene_length, 0.0 for no turns), `earned_reveals` (count of turns with knowledge_progress true). These are reported, never gated here.

## Telemetry gap (found while writing these examples)
Saved blind-player reports carry `grounding_ids`, `candidates_offered`, `matched_candidate`, `transition_cause`, `outcome`, `game_break`, `story_complete` per turn, but NOT `committed_facts`, `null_grounding_ids`, `pressure_event`, `npc_move`, `ending_latched` or `recovery`. On today's saved reports `classify_run` therefore returns `unknown_telemetry` for committed turns and cannot certify anything. The hosted collection path must record those fields (separate task) before this contract can certify a run.

## Comparing expected to actual
`expected` in cases.json is a subset: every key present must match the actual result; `turns` is `{"<turn number>": {field: value}}` and is compared field by field for only the turns and fields listed.
