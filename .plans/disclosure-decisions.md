# Disclosure decisions (Step 3 output)

Received 2026-10-11 after review of `.plans/disclosure-matrix.md`. These are author decisions about what narration may reveal. Rule: custody is not secrecy, and an unlock follows a learned fact, never a scene number. Skipping a reveal must not grant its knowledge. Plot references are to `data/stories/continuity-initiative/plot.md`.

## Ordinary words blocked early

| Term | Decision | Boundary |
|---|---|---|
| memory card, Michelle's memory card | Secret until found; name allowed afterward, including in 1B | `memory_card_recovered`. Finding it does not reveal its contents. Settled by W7 (custody is not secrecy) |
| card | Public | Must not disclose the hidden card or the dead drop contents before discovery |
| park bench | Public | The secret is which bench Michelle used and what she left, revealed through Michelle's files |
| infrastructure corridor | Public as a place | Knowing it exists does not give access, reveal its security advantages, or move Kristin there. Access is earned in 2A.3 |

## The eight possible early reveals

| Term | Early? | What must wait |
|---|---|---|
| purge clock | Not as an active countdown before the purge order; fear of a possible purge is fine | `purge_clock_started` (2C.2): Charles orders destruction within hours |
| false identities | Yes, as a proposed cover | `false_identities_ready`. Passing the checks is later |
| escape route | Yes, as an objective or learned route | `evacuation_route_open`: a viable path is actually open |
| rescue efforts | Yes, as an intention or ordinary description | Communities begin independent rescues, or Kristin joins them (resolution events) |
| coded message | Yes, generically (2B already has coded messages) | The 2C message's arrival and contents; its combined broadcast-and-rescue solution must be earned through the message reveal |
| archive crisis | Yes, broad description | JANUS purpose, Kristin as bait, Brandon's involvement, Michelle's resistance keep their own reveals |
| facility entrance | Yes (by 2A the facility is found) | Arrival, passing credential checks, access to restricted areas |
| uprising | Yes in 3A, once the earlier resistance information is learned | Launch happens in 3A.4; no narrating cameras disabled or checkpoints seized beforehand |

## The "never released" secrets

| Secret | Release |
|---|---|
| JANUS, JANUS selection system, selection system (this program) | 2B.1, archive discovery establishing `janus_evidence`. Not 3C |
| Brandon's history | Layered: prior Initiative work in 1B, retained access shortly after, role in building JANUS in 2B.3 gated by `brandon_janus_role_known`; his later confession makes it public |
| Phase Two | 3C.4, recovered file establishing `phase_two_conflict_plan_known`; keep the conflict-among-survivors plan secret until then |
| bare "phase" | Public (plot uses "next phase" in 1C.4); does not disclose the named Phase Two |

## Source conflicts to resolve before Step 4's pilot

Word guards alone cannot settle these; the entry knowledge asserts too early.

- `k_scene_2c_entry` (knowledge.yaml, ~line 2838) says "The purge clock is active" on 2C entry, but the plot stages the order in 2C.2 (`purge_clock_started`).
- `k_scene_2a_entry` says they are "entering the facility under false identities", but 2A starts at the hideout and `false_identities_ready` comes later.
Both verified present in knowledge.yaml on 2026-10-11. Story text changes go to the ChatGPT Desktop round, not to a hand edit.

### Resolved 2026-10-11 (PR #599, merge 73aa4997)

ChatGPT Desktop supplied the wording; a Ringer worker applied it with no deviation.

- `k_scene_2a_entry`: "Kristin must plan a way into the facility. False identities are a possible cover." Aliases unchanged.
- `k_scene_2c_entry`: "Kristin fears a possible purge. She must choose her next move." Alias `purge clock` removed; `purge` kept.
- `k_sl_2c_b_r1` and `_r2`: aliases now `purge clock started`, `purge clock`, so `purge clock` is guarded until `purge_clock_started`. Matrix: rejected early, allowed after the order.
- Objective (plot.md) and `scene_frames.pressure` (knowledge.yaml) changed for 2B, 2C and 3B to remove spoilers: "Find evidence in the records archive", "Choose the next move under growing pressure", "Reach the broadcast controls".
- Not changed: `k_scene_1b_entry` ("immediate place of pursuit"). ChatGPT called it too early only if read as current action. Left alone so this change is measured first.
- Offline: package load, full suite (1421), ruff and CI pass.

Live check (variation `bench/variations/entry-knowledge-2a-2c.json`, manifest `scripts/ringer/entry-knowledge/manifest-full.json`, results in `bench/results/entry-knowledge-full-2a|2c`, not committed). Four replicates each, first three turns plus opening read by hand, judges off:

- 2A: 0 of 4 premature credentials-ready, facility-arrival or passed-check lines. Turn 2 appends the cover and credentials delivery text on every replicate; that is the earned cooling-water reveal, not a leak.
- 2C: 0 of 4 premature purge order, countdown or combined solution. Before the fix, the single smoke replicate said "respond to the purge order" on turn 3.
- 0 failed replicates in all runs.

Still untested: legitimate reveals landing after the fix (the scripts avoid them on purpose), rejected-turn counts, and 1B. Four replicates is a smoke check, not strong evidence.

## Caveats

- The matrix's "earned rejected" table does not prove a guard never releases: its synthetic earned states may omit preceding discoveries or required world effects.
- The matrix heuristic's `suggested_class` is not a decision; these decisions supersede it. `janus` appeared under "public candidate" by heuristic error.
