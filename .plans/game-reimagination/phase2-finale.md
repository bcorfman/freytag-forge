# Phase 2: finite finale, portability and the 3C neutral staller

Part of the [game reimagination plan](../game-reimagination-plan.md), section 8, Phase 2. Read this when you
build or test anything in 3B to 3C, the ending, or the lighthouse fixture.

Status: built and played live once (Round 10b, 2026-11-02). Brandon asked for all three parts. Scout done; C1 to C3 (optional
successor, lighthouse ending journeys, story-specific engine branches removed), generic `ending.variants`, and the 3C
finale propagation (contract: [phase2-3c-contract.md](phase2-3c-contract.md)) are applied and uncommitted on branch
`3a-open-items-phase2`. Full suite with the coverage gate: 3,809 passed, 92.72%; ruff clean. Left: Round 10 live rows
([act2-live-smoke.md](../act2-live-smoke.md), preregistered, awaiting Brandon's go-ahead), the timing assumption
(window turn 9, nudge turn 10), and the human gates.

Constraint, same as Act 2: no new engine feature unless the scout proves a gap. It proved one small gap
(see Scout answers). Reuse incidents, recovery
storylets, `entry_variants`, `bridge_text` and the typed `ending`. Story text is written into `plot.md`
directly (Brandon, 2026-11-01), then propagated by Ringer.

## What is wrong today

- The ending latch is `phase_two_conflict_plan_known` (`pacing.yaml`, `ending.when`), set only by `SL-3C-E`
  (Phase One), which needs `resolution_complete`. A player who frees every captive still has to find a
  document to finish. That is the return-to-chamber scavenger hunt.
- `evacuation_route_open` exists but nothing records that the evacuation finished.
- A neutral staller in 3C has no exit. Phase 1 left this gap on purpose.
- Charles's threat is the *condition* of finishing instead of the sequel hook it is meant to be.

## Part A: a finite 3B to 3C crossing

One incident, `i_3c_evacuation`, owns the 3C climax. Broadcast (3C.1) and archive (3C.2) stay storylets whose
facts colour the aftermath. They are not gates.

| Piece | Design |
| --- | --- |
| Set piece | Kristin holds the pumps and one watertight barrier while Michelle leads the captives through the tunnel (3C.3). Done with the hands, not by reading. |
| Outcomes | `evacuation_clean` (barrier held, gates released once) and `evacuation_costly` (a route lost, `los_angeles_facility_lost`). Both set the explicit event `evacuation_complete`. |
| Ending latch | `ending.when: evacuation_complete`. `phase_two_conflict_plan_known` no longer ends the game. |
| Aftermath | Dawn text with variants from facts already set: `archive_copies_distributed`, `rebecca_captured`, `brandon_name_kept` or `erased`, and `truth_no_longer_containable`. Brandon's fate stays "uncertain" in text, said plainly. |
| Phase Two | `SL-3C-E` becomes an optional epilogue storylet. Its facts persist, it never gates the ending. |
| Deadline | A missed window never grants `evacuation_clean`. |

## Part B: the 3C neutral staller

A staller who earns neither outcome reaches a neutral recovery, `SL-3C-F`-style, by handoff turn plus three:
the surge forces the captives out without Kristin's hand on the barrier. It sets `evacuation_complete` and
neither outcome fact, and the aftermath picks its neutral variant. Same loader rule as 2C (a recovery may match
zero outcomes).

## Part C: lighthouse-fixture portability

Run the incident, outcome, entry-variant and ending contracts against the unrelated lighthouse package
(`tests/test_world_second_package.py` and its fixture). Pass means no story-specific branch in `storygame/`
or `packages/worldkeeper`, found by grep and by the fixture itself running a one-incident scene to an ending.

## Scout answers (Ringer `phase2-prep`, 2026-11-02; report in `~/dev/ringer-work/phase2-prep/scout-report.md`)

1. **Needs a code change.** `Incident.successor_transition_id` is required (`models.py:763-771`) and the loader
   demands a matching transition from the incident scene (`loader.py:1060-1082`). 3C has no outgoing transition, so a
   3C incident cannot load. Smallest change: make the field optional and skip the successor checks when absent.
   Generic, not story-specific.
2. **Data only.** `ending.when` is a list of fact predicates, checked after each committed turn in the ending scene
   (`engine.py:742-755`). A recovery that asserts `evacuation_complete` fires an ending whose `when` is that fact, even
   when it matches zero outcomes.
3. The 2C zero-outcome recovery rule works as is (`loader.py:1148-1161`); it needs only the optional successor.
4. **Lighthouse covers** one incident with two outcomes, floors, missed windows, recovery, entry variants and package
   boundaries. **It lacks** delivered bridge text, an `ending` in `pacing.yaml`, and any journey to an ending.
5. **Story-specific hits outside tests:** `storygame/web_demo.py:84-85` and `personas.py:72,308-309` (package paths and
   persona text: config, not engine branches), `runtime/cloudflare.py:872` (a Kristin-specific narrator rule: a real
   branch), `audit.py:23` (hard-coded scene list ending in `3C`). `packages/worldkeeper` is clean.
6. **Tests that pin the current ending latch:** `tests/test_3c_cue_chain.py`, `tests/test_story_ending.py`.

## Work items this gives

- **C1 (engine, generic):** optional `successor_transition_id`; loader tests for a last-scene incident.
- **C2 (lighthouse):** give the fixture a last-scene incident, an `ending`, and a journey that reaches it by an outcome
  and by a zero-match recovery; assert delivered bridge text. Generalize `cloudflare.py:872` and `audit.py:23`, or show
  each is data-driven; leave the package-path and persona config alone and say why.
- **A and B (story data):** `plot.md` 3C ordering and the aftermath variants, then `incidents.yaml`, `storylets.md`,
  `storylet-routes.yaml`, `knowledge.yaml`, `handoffs.yaml`, `pacing.yaml` (new `ending.when`). Update
  `test_3c_cue_chain.py` and `test_story_ending.py`.

## Tests and evidence

- Deterministic: package suites for the new ids; a journey test that reaches the ending by each outcome and by
  the neutral recovery; the lighthouse contract test.
- Model: one preregistered Round 10 of live 3C rows (clean, costly, stall), after Round 9. Not before.
- Human gate: unchanged, still open from Phase 1.

## Order

1. Scout: done. 2. C1, then C2 (code and tests, no story text). 3. Parts A and B (`plot.md`, then propagation).
4. Round 10 live rows, including the 3C first-turn overlap row.
