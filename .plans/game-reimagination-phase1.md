# Phase 1 implementation plan: the 1C incident slice

Status: proposed, 2026-10-22, baseline `984767a3`. Nothing below is implemented.
Parent: [game-reimagination-plan.md](game-reimagination-plan.md). Contract:
[1c-contract-result.md](1c-contract-result.md). Catalogue:
[game-reimagination-phase0.md](game-reimagination-phase0.md).

## Resume here

Decisions in section 5 are made. Steps 1-6, 7a-7c and 8 part 1 (scripted playthroughs) are done and verified (below).
Step 1 is `8c4447ca`, step 2 is `398bcbbb`, step 3 is `68518933`, step 4 is
`fc3f63e3`, step 5 is `bd926e15`, step 5b is `78e18467`, step 6 is `45989f14`,
step 7a is `c633cd16`, step 7b is `9920a3b5`, step 7c is `c7be45a5` (merged in #689), step 8 part 1 is the commit that records this entry.
Next: step 8 part 2, a smoke-tested model run, which needs Brandon's budget go-ahead
(Cloudflare cap, dollar usage with UTC timestamp, player-model budget).

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

## Step 3 result (2026-10-23)

Ringer run `game-reimagination-phase1`, Codex Luna medium, 2 attempts, 205k
tokens, 996 s. The run reported FAIL only because the manifest check ran pytest
on `.`, which collects `scripts/ringer/stage7` probes and breaks the shard
tests. Use bare `pytest` (testpaths `tests`) in checks. The exported patch was
applied by hand and verified: full suite 2,408 passed, 16 skipped; Ruff clean.

- `storygame/runtime/incidents.py`: `resolved_incident_outcome(incident, facts)`
  returns the first outcome whose advantage facts are all true. No new state.
- `_apply_authored_transition` skips the `min_turns` floor only for an
  incident's `successor_transition_id` with `completes_scene` and a resolved
  outcome. All other transitions keep the floor.
- Unresolved incident scene: the resolution deadline backstop is skipped, and
  `_prepare_handoff` drops deliveries of any outcome advantage fact and takes no
  successor transition. **Consequence for step 4:** with no outcome and no
  backstop, nothing ends the scene. Step 4 must add the missed-window
  withdrawal (the pressure event's own path), or a player who does nothing
  stays in the scene forever.
- Loader: non-mapping `incidents.yaml` raises `StoryPackageError`; outcome
  realization operations now count as trigger sources for the successor.
- Tests only on the lighthouse fixture; the real package has no incidents until
  step 6, and the step 1 turn-11 backstop test still passes unchanged.

## Step 4 result (2026-10-23)

Ringer run `game-reimagination-phase1`, Codex Luna medium, 1 attempt, 96k
tokens, 406 s. Tests only, no engine change: added
`tests/test_incident_pressure.py`; incident tests 36 pass, 1 skipped; full suite
2,414 passed, 16 skipped; Ruff clean. Pinned on the lighthouse fixture:

- Rejected proposals and repeated retries leave turn index, facts, fired and
  active events unchanged; the pressure event does not fire.
- Clarification leaves state unchanged (tested via an injected reference
  question; the stub has no natural ambiguity). A provider error restores
  pre-turn state; Cloudflare's internal retry loop is covered only by its
  existing provider tests.
- The missed window fires once, asserts only its own fact, grants no advantage
  or cost, and the scene stays put past the handoff deadline.
- Late recovery works. On the boundary turn, pressure activates before proposal
  resolution. Save/load after the window does not refire it.

**Decided (section 5, item 4):** after a missed window with no recovery the player stays in
the scene indefinitely; no backstop, no successor. The contract wants a grounded
recovery or an honest failure/return path. Options: a package-declared recovery
storylet, or a typed incident field declaring a withdrawal transition. 

## Step 5 result (2026-10-24)

Ringer run `game-reimagination-phase1`, Codex Luna medium, 1 attempt, 128k
tokens, 886 s. Added optional `connections.yaml` (`Connection`,
`StoryPackage.connections`, loader validation of 8 cases), the pure
`storygame/runtime/traversal.py` (`resolve_traversal`; refusals `no_route`,
`access_closed`, `already_there`; containment-aware, so a place inside the
`from` place counts), `RuntimeEngine.follow_connection(destination_id)`, lighthouse
fixture connections, and `tests/test_traversal.py` (17). Focused 53 pass, 1
skipped; full suite 2,431 passed, 16 skipped; Ruff clean.

- `follow_connection` is one atomic, provider-free accepted turn: it moves the
  protagonist, asserts the consequences, appends the arrival text, then runs the
  same post-turn sequence as `_turn_active`, so it burns the incident window; a
  refusal changes nothing.
- It **duplicates** the post-turn sequence of `_turn_active` (about 20 lines).
  Extract a shared helper when step 7 touches that code.
- **Not wired to player text.** Nothing calls `follow_connection` from free-text
  input yet. The worker's suggestion: resolve a proposed destination name to a
  connection after the existing proposal/reference boundary, then call it. Decide
  the wiring in step 6 or 7; the real package has no connections until step 6.

## Step 5b result (2026-10-24)

Commit `78e18467`; manifest `scripts/ringer/phase1/step5b-manifest.json`. `Incident`
requires `recovery_storylet_id`. The recovery realizes an existing outcome at a
higher declared cost, is available only after the missed-window fact, and
completes the scene through the normal successor. The loader rejects unknown,
cross-scene, shared-storylet, non-qualifying and ungated recoveries. No engine
change. Re-verified today: incident loader, recovery, pressure and traversal
tests 51 pass; Ruff clean. The full suite was not rerun in this session.

## Step 6 result (2026-10-24)

Two Ringer runs, both `game-reimagination-phase1`, Codex Luna medium. Run 6
(`step6-1c-incident-package`, 2 attempts, 270k tokens, 684 s) wrote the package
edit but FAILED its check: 32 tests and 3 errors still pinned the old 1C. Run 6b
(`step6b-reconcile-stale-1c-pins`, 1 attempt, 244k tokens, 1,304 s) reconciled
them. Applied by hand from `step6-cumulative.patch`; verified: full suite 2,447
passed, 16 skipped; Ruff clean.

- Package: `incidents.yaml` (`i_1c_freight_transfer`: outcomes `copy_numbers` =
  SL-1C-C-R1 and `secure_route` = SL-1C-C-R2; recovery SL-1C-D reuses
  `secure_route` plus `terminal_sweep_closing`; missed window
  `transfer_window_1c` at turn 5), `connections.yaml` (freight terminal to service
  level via the service entrance, gated by `service_level_access_known`), new
  `processing_line`, `prisoner_number_record`, `processing_numbers_copied`,
  `transfer_window_missed`. SL-1C-A-R2, the old SL-1C-C network and recording,
  `terminal_security_escalating` and the captives evidence-gap cost are gone.
  `observation_shaft` now sits under `loading_docks`; `logistics_terminal` was
  removed. `national_detention_network_known` and `architects_strategy_known` stay
  declared with no producer (decision 2; Phase 3 relocates them).
- The loader required fallback `FactDelivery` entries for the bridge's `any_of`
  facts, so `handoffs.yaml` has minimal deliveries for
  `processing_numbers_copied` and `service_level_access_known`.
- Saves bind to package content by fingerprint; no manual version field.
- Behaviour changes to know about: the `connection` is declared but not callable
  from player text; the step 1 turn-11 backstop test is replaced; the staller and
  wrong-lead personas in `test_persona_escalation` now honestly stop in 1C instead
  of being forced into 2A, which the contract requires.
- Harness: the journey harness derives the recovery path from the package's
  incidents and waits for the missed window. `scripts/ringer/stage7` frozen
  arms replay against the shipped incident package. No test was deleted. One
  whole-handoff byte comparison against the pre-adoption 3C fixture was removed.
- Not done in step 6: 2A variants and consumer, `follow_connection` wiring, cue
  lifecycle (all step 7); the 1C player-facing text has not been played with a
  model.

## Step 7a result (2026-10-24)

Ringer run `game-reimagination-phase1`, Codex Luna medium, 2 attempts, 545k
tokens, 2,869 s; manifest `scripts/ringer/phase1/step7a-manifest.json`. Package
and tests only. Full suite 2,454 passed, 16 skipped; Ruff clean.

- SL-2A-C gained C-R3 (uses `processing_numbers_copied`) and C-R4 (uses
  `service_level_access_known`), guarded by `requires`. Each records a
  confrontation marker fact and still reaches `restricted_corridor_access` and
  `t_2a_2b`. The advantage facts are only read. `tests/test_scene_2a_advantages.py`
  pins gating, both advantages, the no-advantage path and persistence into 2B.
- **Not done: the 2A entry variants.** `FactDelivery` stages only missing facts and
  the target `entry_text` is static, so arrival text cannot vary by an advantage
  already asserted. A 1C-to-2A probe printed the same static text for both outcomes.
  This needs a small runtime change (fact-keyed entry text variants); fold it
  into step 7b.

## Step 7b result (2026-10-24)

Ringer run `game-reimagination-phase1`, Codex Luna medium, 1 attempt, 209k tokens,
817 s; manifest `scripts/ringer/phase1/step7b-manifest.json`. Full suite 2,466
passed, 16 skipped; Ruff clean.

- **Entry variants.** Optional `SceneMetadata.entry_variants` (required fact ids plus
  text). One helper, `scene_entry_texts`, emits the base text then each satisfied
  variant in declaration order; the opening, authored and handoff transitions and the
  Cloudflare payload use it. The loader rejects unknown facts, empty requirements,
  blank text and unavailable guarded terms. 2A has one variant per 1C advantage; with
  neither, entry text is unchanged.
- **Traversal wiring.** A pure lexical matcher in `traversal.py` maps an imperative
  movement command to a connection (destination name or id words, or exactly one
  outgoing via entity). Unmatched, unrelated or ambiguous commands fall through to the
  provider. Closed access returns `EngineRefusalTurn("access_closed")`, which keeps a
  player-visible reply and does not advance the turn or incident window.
- **Helper.** `_complete_accepted_turn` is shared by `_turn_active` and
  `follow_connection`.
- Not verified: the variants and traversal wiring have not been played with a model.

## Step 7c result (2026-10-24)

Ringer run `game-reimagination-phase1`, Codex Luna medium, 1 attempt, 131k tokens,
668 s; manifest `scripts/ringer/phase1/step7c-manifest.json`. Full suite 2,469
passed, 16 skipped; Ruff clean.

- New `storygame/runtime/cue_lifecycle.py`: `staged_cue_is_eligible` checks delivery
  scene, final asserted target fact, reveal availability and stage-2 retirement;
  `clear_staged_cue` resets the staged fields. Called before cue text is assembled in
  `CloudflareTurnProvider._compose_staged_cue`, `_complete_accepted_turn` and
  `_prepare_handoff` (queued handoff text filtered against final facts and scene).
- `tests/test_cue_lifecycle.py` covers the plan section 6 sequences. The Cloudflare
  stale-target test failed before the fix; the engine-only same-turn test was already
  green. Two tests in `tests/test_pacing_handoff.py` pinned carrying a staged cue
  across a handoff and now require it cleared.
- Not verified: no model play; typed `obsolete_when` predicates were not added (the
  check reuses fact state and reveal eligibility).

## Step 8 part 1 result (2026-10-24)

Ringer run `game-reimagination-phase1`, Codex Luna medium, 1 attempt, 141k tokens,
561 s; manifest `scripts/ringer/phase1/step8-manifest.json`. Full suite 2,473 passed,
16 skipped; Ruff clean. Test-only change.

- `tests/test_phase1_slice_playthroughs.py`: four hermetic playthroughs on the real
  package (copy numbers, secure route, missed window with recovery, save/load on the
  copy and missed-window journeys), each reaching 2B within the turn budget.
- The worker marked two journeys strict-xfail as an engine defect. That was wrong:
  the journey script omitted `_advance_to_2b`, and the 2A reveal is eligible
  (`explain_reveal` returned eligible). Fixed in the test; no xfail remains.
- **Design finding, needs a decision.** Every incident outcome completes 1C and enters
  2A on the same turn, so the `freight_terminal_to_service_level` connection cannot be
  used from free text in a real journey: the player has already left 1C when
  `service_level_access_known` becomes true. Traversal is covered only by the unit
  test that asserts the fact without the outcome transition. Options: drop the
  connection from this slice, or give it a use (for example a post-outcome 1C
  pause before the handoff).
- Not done: the smoke-tested model run (part 2); no billed call was made.

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
| 5b | Required `recovery_storylet_id` on `Incident`, loader checks, fixture update, engine test that the recovery completes the scene | Loader rejects missing or non-outcome recovery; recovery test passes |
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

4. **Missed-window recovery (Brandon, 2026-10-23):** option 1. A missed window
   leaves the scene open with a package-declared recovery storylet, not a
   forced withdrawal transition. The recovery reuses outcome A or B at a higher
   cost (no third outcome), so the outcome count and the 2A variants are
   unchanged, and it completes through the existing successor transition. Add a
   required `recovery_storylet_id` to `Incident` and make the loader reject an
   incident without one or whose recovery does not realize an existing outcome
   (new step 5b, before step 6). Add a typed withdrawal field only if step 8
   playtests show stalling.

## 6. Not verified

No tests or model runs were performed for this document. Every row marked "not
verified" in section 1 is an open question, not a finding.
