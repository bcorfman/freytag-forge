# Phase 1 implementation plan: the 1C incident slice

Status: proposed, 2026-10-22, baseline `984767a3`. Nothing below is implemented.
Parent: [game-reimagination-plan.md](game-reimagination-plan.md). Contract:
[1c-contract-result.md](1c-contract-result.md). Catalogue:
[game-reimagination-phase0.md](game-reimagination-phase0.md).

## Resume here

Decisions in section 5 are made. Steps 1 and 2 are done and verified (below);
step 1 is `8c4447ca`, step 2 is the commit that records this entry. Next: step 3
(engine: outcome resolution, outcome-scoped cost, completion without the floor),
as a Ringer manifest.

## Step 1 result (2026-10-22)

Ringer run `game-reimagination-phase1`, Codex Luna medium, 1 attempt, 100k
tokens, 357 s. Added `tests/test_incident_characterization.py`: 6 pass, 1
skipped. Ruff clean on the file; the worker's check also passed the full
suite. Findings, all from executed tests:

- Exclusivity is not symmetric. A-R1 fired makes A-R2 report `STORYLET_SPENT`,
  but A-R2 fired makes A-R1 report `ALREADY_ESTABLISHED`, because
  `explain_reveal` checks established effects first. Either way the second is
  ineligible.
- The evidence-gap cost is applied **only on the forced-handoff path**. An
  earned `k_sl_1c_b_r1` does not assert it. Putting the cost in outcome B's own
  `establishes` therefore works, and the delivery cost can simply be removed.
- The `min_turns` floor holds: 1C stays through turn 6 and enters 2A at turn 7,
  with bridge and entry segments. The loader rejects a pacing event after the
  floor.
- A rejected turn restores turn index, facts, fired and active events exactly,
  and the pressure event does not fire; the next accepted turn fires it. Its
  complication text lands in `last_turn_delivery`, not in returned segments.
- **Contract conflict:** a player who does nothing is forced into 2A at turn 11
  by the deadline backstop, which delivers the missing facts and
  `facility_infiltration_needed`. This is the "deadline supplies an unearned
  advantage" behavior the 1C contract forbids. Step 3/4 must replace it for
  incident scenes.
- Not pinned: clarification does not advance pacing. No short 1C command
  reaches `ClarificationTurn` in today's resolver, so that test is a skip.
  Cover it in step 4 with a synthetic fixture.

## Step 2 result (2026-10-22)

Ringer run `game-reimagination-phase1`, Codex Luna medium, 1 attempt, 101k
tokens, 597 s. Added optional `incidents.yaml`: `Incident` and `IncidentOutcome`
models, `StoryPackage.incidents` (default `()`), `_validate_incidents`, the
synthetic package `tests/fixtures/stories/lighthouse-incident`, and
`tests/test_incident_loader.py` (16 pass). Full suite 2,978 passed, 16 skipped;
Ruff clean. No runtime change; the engine does not act on incidents yet.

- Declaration shape: an incident names its scene, two or more outcomes, a
  `missed_window_event_id` (an existing pacing event), a
  `successor_transition_id`, optional `observation_knowledge_ids` and
  `completes_scene` (default true). An outcome names one realization of the
  shared storylet, its `advantages` and its `costs`. Both must be asserted true
  by that realization, so the cost is the realization's own operation.
- Exclusivity is by shared storylet with distinct realizations (step 1 finding).
  Advantage sets are disjoint across outcomes.
- The loader rejects the 11 listed cases. A missed-window event cannot touch an
  outcome fact or carry the successor transition. A delivery cost in the
  incident scene cannot duplicate an outcome cost.
- Ids are snake_case (`_ID`), so the contract's `I-1C-freight-transfer` becomes
  something like `i_1c_freight_transfer` in step 6.
- `storygame/audit.py` enumerates `storylet-routes.yaml`; it was not changed.
  Check in step 6 whether the audit needs to read `incidents.yaml`.
- Gap to fix in step 3's manifest: no test covers an `incidents.yaml` that is
  not a mapping, although the spec asked for one. Reading the loader, a YAML
  list there would raise `AttributeError` on `.get`, not `StoryPackageError`.

## 1. What exists today (read in source, 2026-10-22)

| Need from the contract | What the code does now | Gap |
| --- | --- | --- |
| Two exclusive outcomes | A reveal is `explain_reveal`-ineligible once its storylet is in `fired_event_ids` (`reveal_eligibility.py:55`), so two realizations of one storylet are already exclusive | None for exclusivity itself. Nothing names them as outcomes |
| Outcome-scoped cost | `KnowledgeDefinition.establishes` is a tuple of assert/retract operations (`models.py:151`), so a reveal can carry its own cost. `FactDelivery.costs` binds a cost to a fact, not an outcome (`models.py:633`; applied at `engine.py:1435`) | Whether a normally earned reveal also applies the delivery's `costs` is **not verified**. The contract's cost must come only from outcome B |
| Complete without waiting | `_apply_authored_transition` skips any transition until `min_turns` (`engine.py:994`). `loader.py:819` rejects a pacing event whose `at_turn` exceeds `min_turns` | A per-transition or per-outcome way to bypass the floor, or a 1C `min_turns` lowered with the pressure event moved before it |
| Missed-window outcome | `PacingEvent.effects` assert facts at a turn (`models.py:577`), driven by the clock, with no `when` on the player's choice except `when` guards | A pressure event whose effects depend on "no outcome chosen", plus a withdrawal that is not the 2A handoff |
| Bridge activation by either outcome | `ActivationRule` has `all_facts_true`, `any_of`, `at_least` (`models.py:25`) | None. Bridge can be re-declared with `any_of` over the two outcomes |
| Traversal | `worldkeeper` has parent containment only. A grep for connection or traversal found no declaration | New: a package-declared connection with an access fact, destination and arrival text |
| Free observation | Reveal `requires` is a conjunction of `FactPredicate` | None |
| Rejected input does not burn the window | `_activate_pacing` runs after a committed turn only on the commit path; rejection restores the snapshot | Verify with a test that clarification and rejection do not advance the pressure event |
| 2A variants keyed to the advantages | Not read: 2A storylets, entry text and reveals | Read 2A before specifying step 6 |

Unverified and needed before step 2: whether `_cue_reveal_available`
(`engine.py:1131`) already handles the new outcome facts, and what the
engine does at `fired_event_ids` when an outcome realization comes from a
`canonical_route_event` rather than a storylet.

## 2. Smallest design that meets the contract

Prefer reuse over a new schema, per the plan's "add schema only for fields the
slice needs". Add a typed `incident` declaration only for what the existing
mechanisms cannot say:

1. **Incident outcomes.** One new package declaration, `incidents`, with: id,
   scene, the optional free-observation reveal ids, the exclusive outcome
   realizations, each with its `establishes` operations (including its own cost
   facts), a `missed_window` outcome, and the successor transition. The loader
   rejects an outcome whose operations are undeclared facts, two outcomes that
   are not exclusive, a missed window that asserts an earned advantage, and an
   incident with no successor.
2. **Outcome-scoped cost.** The cost is part of the outcome's own operations.
   Remove the unconditional `evidence_gap_processing_numbers` cost from the
   general `captives_confirmed_alive` delivery. A loader check rejects a delivery
   cost that duplicates an incident outcome's cost.
3. **Completion.** An incident outcome, once resolved, makes its transition
   eligible without the `min_turns` floor. Implement as a typed field on the
   incident (`completes_scene: true`), not a global change to
   `_apply_authored_transition`.
4. **Pressure.** One incident-owned pressure event that fires on accepted
   actions only. At its turn, if no outcome is resolved, the missed-window
   outcome commits and withdraws the pair within the scene.
5. **Traversal.** A package-declared `connections` list: from, to, access fact
   (optional), traversal consequence and arrival text. A legal short traversal
   resolves in one action. Mutable access is a fact, not a graph service.

Nothing in the runtime may name 1C, the freight terminal or the prisoner
numbers. The lighthouse fixture (Phase 2) must be able to declare an incident
with the same fields.

## 3. Steps, each one Ringer manifest, tests first

| Step | Work | Check |
| --- | --- | --- |
| 1 | Characterization tests on the current engine: reveal exclusivity per storylet, delivery cost on the earned path, `min_turns` gate, pause behavior on rejection | New tests pass on `984767a3` and pin the facts marked unverified above |
| 2 | `incidents` model, loader validation, and the unrelated synthetic package fixture that declares one | Loader rejects each invalid case; fixture loads |
| 3 | Engine: outcome resolution, outcome-scoped cost, completion without the floor | Deterministic tests on the fixture, then on the real package |
| 4 | Pressure event, missed window, no unearned advantage on deadline | Tests: rejection, clarification and retry do not advance it; missed window grants nothing |
| 5 | `connections` and the traversal action | Tests: gated by fact, one-action arrival, unrelated entity is not a destination |
| 6 | 1C package edit: world, outcomes, bridge, `processing_line`, `prisoner_number_record`, `service_entrance` connection, remove the C chain from the path | Package loads; completion matrix and grounding checks pass |
| 7 | 1B arrival and 2A variants and consumer; discovery cue lifecycle fix | Sequences in plan section 6 |
| 8 | Scripted-provider playthroughs of both outcomes and the missed window, then a smoke-tested model run | Per the testing runbook; no billed run before a smoke test |

Each step ends with a commit, a Ruff autofix and format, and an update to this
file before the next step starts.

## 4. Stop rules (from the parent plan)

- Two unsuccessful iterations for the same symptom: stop and revisit the
  contract, do not patch wording again.
- If engine work threatens delivery, cut mandatory interactions first.
- Do not run the older plans' experiment queues alongside this slice.

## 5. Decisions (Brandon, 2026-10-22)

1. **Schema:** add the typed `incidents` and `connections` declarations
   (section 2). Step 1 pins the unverified rows first.
2. **Charles and Rebecca recording (1C.4):** option A. Drop it from the 1C path
   and leave it undelivered in Phase 1. `architects_strategy_known` is read
   nowhere outside 1C. Relocation is a Phase 3 migration item; candidate homes
   are 2C.1 (Rebecca's private channel to Brandon) and 3B.2 (the executive
   screen's channel marked Charles). Also remove `national_detention_network_known`
   from the 1C path; its content is restated at 3B/3C.
3. **Worker:** Codex Luna at medium effort for every Phase 1 step.

## 6. Not verified

No tests or model runs were performed for this document. Every row marked "not
verified" in section 1 is an open question, not a finding.
