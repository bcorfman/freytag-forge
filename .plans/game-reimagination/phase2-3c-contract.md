# Phase 2 3C propagation contract

Part of [phase2-finale.md](phase2-finale.md). Read this when you propagate the finite 3C finale into the package
files. Scope: `data/stories/continuity-initiative`. `NEW` means the id does not exist yet. Exemplars to copy shape
from: incident `i_2c_rebecca_corridor`, recovery storylet `SL-2C-E`, events `purge_window_2c` and `purge_nudge_2c`,
and the knowledge entries `k_sl_2c_d_r3`/`r4`.

Source of truth for the story is `plot.md` Scene 3C.3 and 3C.4 (already edited). Engine support exists: an incident
may omit `successor_transition_id` when its scene is the `ending` scene, and `ending.variants` (a list of
`requires` fact ids plus `text`) appends one aftermath paragraph per matching variant, in order.

## Shape

3C keeps its sequential episodes as they are: broadcast (`SL-3C-A`), archive (`SL-3C-B`). The third episode becomes
the incident. Completing it fires the ending the same turn. No new transition.

```yaml
- id: i_3c_evacuation
  scene_id: 3C
  outcomes:
  - id: evacuation_clean
    storylet_id: SL-3C-C
    realization_id: SL-3C-C-R1        # existing; keep its id, add the new asserts
    advantages: [barrier_held]
    costs: []
  - id: evacuation_costly
    storylet_id: SL-3C-C
    realization_id: SL-3C-C-R2        # NEW
    advantages: [captives_out_costly]
    costs: [lower_levels_lost]
  recovery_storylet_id: SL-3C-H       # NEW, neutral
  missed_window_event_id: evacuation_window_3c
  observation_knowledge_ids: [k_sl_3c_c_r1, k_sl_3c_c_r2, k_sl_3c_h_r1]   # use the ids the entries really get
  completes_scene: true               # no successor_transition_id
```

## New facts (boolean, initial false)

`evacuation_complete`, `barrier_held`, `captives_out_costly`, `lower_levels_lost`, `surge_forced_evacuation`,
`evacuation_window_missed`, `evacuation_surge_building`. Declare each everywhere existing facts are declared
(`world.yaml`, `storylet-routes.yaml` fact definitions, `handoffs.yaml` where a fact is delivered).

## Realizations (all assert `evacuation_complete`)

- `SL-3C-C-R1` clean: also asserts `evacuation_route_open`, `barrier_held`. Evidence: verbs restore, hold, brace,
  close, repair; nouns pumps, drainage pump controls, watertight barrier, barrier. Text: Kristin restores the pumps and
  holds the barrier until the last captive is through; the lower levels still stand.
- `SL-3C-C-R2` costly (NEW): asserts `evacuation_route_open`, `captives_out_costly`, `lower_levels_lost`. Evidence: verbs
  give up, abandon, sacrifice, flood, seal, let go; nouns lower levels, lower level, detention levels. Text: she gives the
  lower levels to the water so the captives can pass. Fold the surface-gate release into the delivery text.
- `SL-3C-H-R1` neutral recovery (NEW): requires `evacuation_window_missed`; asserts `evacuation_complete` and
  `surge_forced_evacuation`; asserts NO outcome fact and NO cost. Text: the surge pushes the captives out without her
  hand on the barrier. A zero-outcome recovery is already allowed by the loader.
- Both outcomes and the recovery must be available only after the broadcast and archive episodes
  (`truth_no_longer_containable`, `rebecca_captured`), as `SL-3C-C` is today. The recovery requires only the missed
  window, so a staller still ends.

## Events (ASSUMED timing, to be measured in Round 10)

- `evacuation_window_3c`: scene 3C, `at_turn: 9`, asserts `evacuation_window_missed`; text: the surge is on them.
- `evacuation_nudge_3c`: scene 3C, `at_turn: 10`, when the window is missed and no outcome is set, asserts
  `evacuation_surge_building`; text nudges toward the barrier and the pumps.
- Keep `collapse_3c` (turn 4) and `routes_collapse_3c` (turn 10) unless a test forces a change.

## Ending (`pacing.yaml`)

`ending.when: [{fact_id: evacuation_complete, equals: true}]`. Base `text`: dawn; Michelle alive and Kristin reunited
with her; the captives out; Brandon last seen holding the relay and his fate uncertain, said plainly; Charles still out
there; their old lives gone. Do NOT mention Phase Two in the base text. Variants, in this order, each one short
paragraph in the existing voice:

1. `[barrier_held]`: the lower levels stand and every cart came through.
2. `[lower_levels_lost]`: the lower levels went under; everyone who reached the surface lived.
3. `[surge_forced_evacuation]`: the surge, not a plan, carried the captives out; no one yet knows how many.
4. `[archive_copies_distributed]` and `[rebecca_captured]`: copies are with independent networks; the prisoners hold Rebecca.
5. `[brandon_name_kept]` / `[brandon_name_erased]`: his confession stood beside the record / his confession was the only proof.
6. `[phase_two_conflict_plan_known]`: the recovered file labels the operation Phase One and shows Phase Two.

Keep the existing `marker`.

## Phase Two becomes optional

`SL-3C-E` stays but no longer needs `resolution_complete`: make it available once `archive_copies_distributed` is true,
earned by a player action on the recovered JANUS file, setting `phase_one_label_known` and
`phase_two_conflict_plan_known` as today. It must never gate the ending. The canonical event `resolution_complete` and
its knowledge entry `k_resolution_complete` have no job once the ending is `evacuation_complete`: remove both and every
reference if the suites allow it (this also removes the guarded phrase "exposure and escape"); if a test pins them,
keep the event with activation `evacuation_complete` and say which test.

## Tests that pin the old latch

`tests/test_3c_cue_chain.py`, `tests/test_story_ending.py`, plus whatever fails among the package suites. Update them to
the redesign in the smallest way. Existing 3C journey fixtures and the carried 3C prefix (`tests/fixtures/`,
`scripts/ringer/`) may need their ending fact changed.
