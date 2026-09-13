# Missed-obligation escalation

Make every scene react to what the player has overlooked, instead of advancing
through a schedule of reveals. The story pressure arrives on its own timetable;
what that pressure *does* depends on the world's physical state, and what
Kristin notices depends on her knowledge state.

Status: design agreed; every open question answered on 2026-09-13 (see the end
of this plan). Execution is tracked in
[missed-obligation-escalation-implementation.md](missed-obligation-escalation-implementation.md). Re-checked against the
code on 2026-09-13: none of the four layers beyond Opportunity is built, and
`latest_turn` still has no runtime effect.

**Terminology (settled 2026-09-13).** The fourth layer is called **Deadline**.
It is the pacing fallback: at `handoff_after_turns` the engine stages
`staged_handoff_fact_ids` and delivers `handoffs.yaml` fallback text. Code
identifiers (`handoffs.yaml`, `staged_handoff_fact_ids`, `_prepare_handoff`)
keep their names. "Handoff" in prose is reserved for the unrelated *authored
reveal handoff*: an `action_evidence` matcher that inserts a candidate's
`delivery_text` on the turn the player earns it (see `docs/PRD.md`).

## The four layers

| Layer | Purpose | Commits a fact? |
|---|---|---|
| **Opportunity** | Reward a relevant player action with the normal storylet. Player-led discovery, unchanged from today. | Yes, when realized |
| **Cue** | If a required thread is still unresolved, re-surface a clue the player already has, angled at the next action. | No |
| **Complication** | An independent external clock creates pressure around the missing thread. | Pressure facts only |
| **Deadline** | At the hard deadline, deliver only what is indispensable for leaving the scene, and charge for it. | Yes |

The layers escalate but do not replace one another: Opportunity stays available
throughout, so a player who plays well simply never reaches Cue or
Complication for that thread.

### The causal rule that makes this work

The patrol does not arrive because Kristin failed to find the card. The patrol
cannot know what the player knows. Instead:

- The patrol arrives **because its own timetable says so**.
- **What it does** depends on the physical state of the card.
- **What Kristin notices or infers** depends on her knowledge state.
- **Which recovery opportunity is foregrounded** depends on the missing
  obligation.

This is the difference between a world that reacts to player ignorance — which
teaches players that stalling produces content, and punishes thoroughness with
a patrol — and a world that runs on its own and lands differently depending on
where you are. Keep this distinction; it is the whole design.

## What already exists (verified 2026-09-13)

- `Storylet` and `StoryletRoute` carry `earliest_turn`, `target_turn`, and
  `latest_turn`. There are **30** route storylets; only `SL-1A-D` (4),
  `SL-3C-D` (4) and `SL-3C-E` (5) have `latest_turn` ≥ 4.
- `pacing.yaml` gives each scene `min_turns`, `nudge_after_turns`,
  `handoff_after_turns`, and holds four timed `events` that assert pressure
  facts (`pressure_1a`, `purge_2c`, `override_deadline_3a`,
  `destruction_3b`). `PacingEvent` is documented in code as "a
  package-declared, deterministic deadline complication"; it carries only
  `effects` and an optional `transition_id`.
- **Gap analysis is already built, from bridge activation.**
  `RuntimeEngine._bridge_delivery_fact_ids` takes the scene's first unfired
  bridge event whose `activation` is unsatisfied and returns
  `activation.minimal_undelivered_facts()` filtered to facts with a
  `handoffs.yaml` delivery. The same list feeds both tiers:
  `staged_hint_fact_ids` from `nudge_after_turns` and
  `staged_handoff_fact_ids` from `handoff_after_turns`, restaged every turn
  (`>=`). Both live on `RuntimeState`/`RuntimeSnapshot`; `KnowledgeProjector`
  only renders them.
- **Every bridge-activation fact in every scene has a `handoffs.yaml`
  delivery.** The Deadline layer is therefore already a backstop for every
  bridge gap. Transition triggers are not deliveries: they are committed by the
  bridge event's operations, by pacing events (`patrol_return_pressure`), or by
  delivery `costs` (`memory_card_in_kristins_custody`).
- `_prepare_handoff` already commits the staged deliveries plus their `costs`,
  the bridge operations and the transition in one turn.
- `TurnDelivery` already records `hint_staged`, `handoff_staged`,
  `fallback_used` and `must_convey_misses` per turn.
- `tests/test_canon_journey.py::test_no_single_reveal_can_strand_a_scene_exit`
  checks that no single realization strands a scene exit — but it ignores turn
  order and runs against this package only.
- `knowledge.yaml` scopes entries with `available_in_scenes` (76 entries).
- `bench compare` pools ledger rows per arm and reports Welch's t-test and the
  minimum detectable effect.

### What is missing

- **`latest_turn` has no runtime effect whatsoever.** `_activate_pacing` never
  consults it. Every storylet window is an opening time with no closing time.
- **Nothing selects a realization by world state.** `RouteRealization` has
  `dramatic_intent`, `operations`, `eligible_storylet_event_id`,
  `helps_transition_triggers` and `protected_knowledge_boundaries`, but no state
  guard; realizations reach the narrator as knowledge candidates keyed by
  `source.realization_id`. `PacingEvent` has no realizations at all.
- **Dead authored fields.** `pacing_impact` is authored on all 30 storylets in
  `storylets.md`, every one `brief_delay`, and read only by the model and
  loader. `helps_transition_triggers` and `pressure_role` are also never read
  at runtime.
- Only four scenes have a concrete timed complication. The 2026-09-08 pacing
  decision below has not shipped.
- The KMS carving exists only as the beat 1A.1 detail `KMS initials in drawer`
  and one prose sentence in `plot.md`. It reaches the narrator on scene entry
  and while 1A.1 is projected, then drops out; it is not a fact, knowledge entry
  or placement (resolved by Q10).

## Design decisions already settled

### 1. Obligations are derived, not authored

Do **not** author a parallel per-scene obligation list. A scene's obligations
are already authored, validated, and enforced.

**Correction (2026-09-13), confirmed under Q3.** The original text derived
obligations from `Transition.triggers` plus `required_dependencies`. The engine
does not: it derives the gap from the scene's **bridge activation rule**, and
the transition triggers are the facts that bridge (and the clock) then commit.
In 1A, `bridge_1a_actionable_lead` needs only `continuity_initiative_known`,
which commits `michelle_lead_actionable`; `t_1a_1b` additionally needs
`patrol_return_pressure` (clock) and `memory_card_in_kristins_custody`
(recovery or delivery cost):

```yaml
- id: t_1a_1b
  triggers:
  - {fact_id: michelle_lead_actionable, equals: true}
  - {fact_id: patrol_return_pressure, equals: true}
  - {fact_id: memory_card_in_kristins_custody, equals: true}
  required_dependencies: [memory_card]
```

A hand-written list would duplicate this and drift from what actually gates the
scene.

Note that `patrol_return_pressure` is itself a trigger for `t_1a_1b`, and
`purge_clock_started` is required by `bridge_2c_combined_plan`: in 1A and 2C the
Complication layer is already load-bearing for scene exit, not decoration.

### 2. Do not duplicate item possession as a fact

`required_dependencies: [memory_card]` guards against the item being lost, but
it does not prove possession. Scene 1A has one positively named custody fact,
`memory_card_in_kristins_custody`, rather than a location fact such as
`memory_card_still_in_house`. It is asserted on recovery and by the handoff
fallback's `costs`, is a trigger on `t_1a_1b`, and gates `SL-1A-D`. An absent
fact satisfies `equals: false`, so it needs no seeding, and the loader rejects
an `equals: false` trigger on a fact nothing asserts true. `item_placements`
entries may carry `while_fact_false: <custody fact>` so the engine stops stating
a placement once the item moves. Use that pattern for any other item: one
custody fact per item, never an item ID as proof of possession.

### 3. Three kinds of fact, kept separate

- **Physical** — where a thing is, independent of anyone's knowledge
  (`memory_card_in_kristins_custody`).
- **Epistemic** — what Kristin knows or has inferred (`kms_marker_noticed`,
  `michelle_hiding_intent_inferred`).
- **Pressure** — what the world is doing (`patrol_search_active`,
  `house_marked_for_return`).

A complication reads physical and pressure state; a cue reads epistemic state.

### 4. Give `latest_turn` runtime meaning

This is the cheapest large win available: the deadlines are already authored on
all 30 storylets, and today they do nothing. Expiry semantics are settled under
Q2.

### 5. The engine selects the realization; the narrator never does

Pass the model **one** realization. Do not hand it several plus a condition.
Everything measured on this narrator says it does what the authored material
makes easy and drifts otherwise — it placed an object on the wrong surface in
26% of turns with the right answer sitting in the prompt. Conditional selection
is engine work.

### 6. Never name the state that is not true

A rule or realization must state what *is* the case. Naming the wrong value
measurably makes it more likely: `"A counter is not a floor."` raised
off-canon placements from 13/50 to 21/50, while
`"Michelle's phone is on the kitchen floor."` took them to 0/50.

## Worked example — scene 1A

1. **Opportunity.** Searching the workstation uncovers the card. Unchanged.
2. **Cue.** If the actionable lead is still absent, foreground the carved KMS
   initials. Commits nothing; re-presents what Kristin already saw.
3. **Complication.** The patrol arrives on its own schedule and begins
   searching Michelle's office.
4. **Adaptive realization**, selected by the engine:
   - card still hidden → an officer concentrates on the drawer, confirming
     something there matters;
   - Kristin has the card → the patrol searches for it and pressure shifts to
     concealing it;
   - Kristin already understands the lead → pure exit pressure, no repeated
     discovery.
5. **Deadline with a cost.** If the lead is still missing at the deadline, an
   authored observation exposes the card or its information — and charges for
   it: the patrol notices her interest, the house is marked, or she leaves
   hurriedly.

The boundary to hold: the patrol makes the drawer *salient*; it never opens it.
Pressure that hands over knowledge collapses Complication into Deadline and
violates `pacing_events_must_create_observable_pressure_not_unearned_knowledge`.

## Carried-forward defects

Found by a separate continuity audit, re-verified against the package on
2026-09-12. They are real today, independent of the four layers, and can each
ship as its own brief. Deadline migration of a scene may rewrite its bridge, so
check that before fixing bridge prose.

- **3C resolution cascade (highest value).** `_apply_canonical_route_events`
  (`storygame/runtime/canonical_events.py`) commits each event and marks it
  fired before checking the next, and the six `canonical_resolution_events` are
  declared in chain order. Once `truth_no_longer_containable` holds, archive,
  escape, network consequences, Phase Two and completion all commit in one pass,
  before their storylets narrate anything. Still present 2026-09-13. Sequence
  them, or require each one's player-visible realization before it commits.
  `portable_archive_secured` has no world item: 3C declares `memory_card`
  instead, so add `portable_archive` with custody starting at Rebecca and
  introduce it before Kristin must secure it.
- **Bridges claim more than their activation guarantees.** `t_1b_1c` says the
  transit card opened the route, but `bridge_1b_departure` can fire without
  `transport_route_identified`. `t_2b_2c` claims Michelle's selection, Kristin
  as bait, Brandon's name and Michelle's resistance, but
  `bridge_2b_archive_crisis` needs only `janus_evidence` plus two of three
  facts, none of them Michelle's selection. `t_2c_3a` claims Michelle's coded
  message, which `bridge_2c_combined_plan` does not require. Every bridge
  states only facts its candidate establishes; a fallback that supplies a fact
  also supplies its item.
- **Stale item declarations.** `memory_card` in 2B, 2C and 3C (the operative
  evidence is the JANUS archive) and `override_codes` in 3B. Deleting them
  removes the object the narrator reaches for wrongly.
- **Pacing reaction window.** A visible timed threat must precede the deadline
  by two complete turns, and every optional storylet's `latest_turn` must leave
  a turn before `handoff_after_turns` (required storylets do not expire; see Q2
  amendment). Only four scenes have a pressure event. Decided
  (2026-09-08), **not shipped as of 2026-09-13**: add `pursuit_1b` (turn 2, does
  not resolve the pursuit), a 1C security escalation, visible 2A scrutiny
  (Rebecca stays hidden) and a 3C collapse escalation, all at turn 2; move
  `destruction_3b` from turn 4 to 3; widen 1B to `2/4/5` and 3C to `2/4/6`;
  raise `budget_seconds` to 1890. These land as one change with
  `tests/test_scene_relative_pacing.py`: its `expected_windows` dict, the
  over-budget probe (`1890` → `1889`), and the sum-equals-budget assertion
  relaxed to `<=`.
- **Hiding-spot disclosure (found 2026-09-13).** `_placement_rules` sends
  "Hidden memory card is taped under a drawer in Michelle's workstation." in
  every 1A prompt until `memory_card_in_kristins_custody` holds, and `SL-1A-B`'s
  beat details also locate the card. Beat 1A.2 ("hidden memory card; taped
  drawer"; "Kristin finds a hidden memory card taped beneath a drawer") is linked
  from `SL-1A-A` (open from turn 0), `SL-1A-B` and `SL-1A-D`, and
  `_candidate_beats` projects a linked beat for *every* projected candidate —
  including runtime-owned reveals (all six 1A reveals carry `action_evidence`
  and `delivery_text`) that the narrator is never allowed to select. Experience
  says narration discloses it often. **Decided (2026-09-13):**
  - delete the standing `memory_card` placement and rename the item "Michelle's
    memory card";
  - carry the location only in the `SL-1A-B` reveal `delivery_text` and the 1A
    Deadline fallback;
  - strip the card's location and "hidden" wording from beat 1A.2's details and
    prose in `plot.md` (chosen over filtering beats to model-selectable
    candidates, and over projecting beats only on the matched turn), and keep
    the location canonical in `plot.md` as a scene-level `**Hidden canon:**`
    line beside `**Setting:**`, `**Characters:**` and `**Plot:**`, before
    `### Scene 1A.1`. Verified 2026-09-13: text between the front matter and
    the first beat heading belongs to no beat, and no runtime path sends it to
    the narrator; text after the last beat would be absorbed into beat 1A.4, so
    the line must precede the first beat. The audit's plot vocabulary and the
    bench judge's scene block both still include it;
  - add "Michelle's workstation drawers are shut." through a new scene-metadata
    `setting_facts` list rendered as rules beside placements;
  - no loader check for hidden-item placements; the rule "a hidden item's
    location belongs in its reveal, not in `item_placements`" goes in the
    authoring guide.

  Implementation Phase 1.
- **Deferred until they surface in play:** 2A credentials visibly created by
  `SL-2A-B` before the supervisor confrontation (not re-verified), and an
  authored transit-card placement in 1B behind a `while_fact_false` guard.

## Open questions — what must be settled before implementation

Question numbers are stable; they are listed in dependency order, foundational
first. Each was re-verified against the code on 2026-09-13.

### 1. Foundations

9. **Scene exemptions.** 3C is a resolution scene and should be sequenced
   causally, not treated as a set of missed clues. Which scenes opt out, and is
   that authored or inferred? Finding: 3C has no outgoing transition or bridge,
   so a derived obligation set would already be empty there; the 3C cascade
   remains its own carried-forward defect. **Answer (2026-09-13):** infer the
   exemption from `freytag_phase`: a scene whose phase is `resolution` opts out
   of Cue, Complication-driven realization and Deadline. Today that is only 3C.
   No authored flag.
8. **Reconciling with `pacing_impact`.** Is Complication simply
   `pacing_impact: pressure_increase`, or a new concept beside it? Finding:
   `PacingEvent` is already documented as the deadline complication, and
   `pacing_impact` is dead data (30× `brief_delay`, never read at runtime).
   **Answer (2026-09-13):** Complication is `PacingEvent`. Delete
   `pacing_impact` from `storylets.md`, the `Storylet` model and the loader.
   `pressure_role` (also unread) is not decided here.
2. **What `latest_turn` expiry *does*.** Silently close the storylet, escalate
   it to the next layer, or force it. Finding: the hint and handoff tiers
   already stage every missing bridge fact regardless of which storylets are
   open, so escalation needs no new mechanism. **Answer (2026-09-13):** once
   `turns_since_entry > latest_turn`, the storylet stops activating and is
   removed from `active_event_ids` if not fired. It is never forced. Required
   gaps keep flowing through the existing Cue/Deadline tiers; Q14's static check
   guarantees that closing can never strand an exit.
   **Amendment (2026-09-13): required storylets stay open.** Finding: 14 of the
   19 storylets whose realizations assert a bridge-activation fact have
   `latest_turn` below their scene's `nudge_after_turns` (SL-1A-B `2/2/2`
   against nudge 4; SL-1B-A, 1B-B, 1C-A, 1C-B, 2A-B, 2B-A, 2B-B, 2C-B, 3A-A,
   3A-C, 3B-A, 3B-B, 3B-C likewise). Windows are authored as a staircase with
   `latest_turn == target_turn`, i.e. as pacing targets, so closing them would
   make the Cue point at an Opportunity that is already gone. Rule: a storylet
   whose realization asserts a fact in its scene's bridge activation is
   *required* and does not expire at `latest_turn`; it stays open until it fires
   or the scene is left (the Deadline covers it). Every other storylet is
   optional and closes at `latest_turn` as above. "Required" is derived, never
   authored; no windows are re-authored.

### 2. Safety

14. **Reachability.** Expiry can now permanently close a storylet. Does any fact
    required for exit have a single source that can expire? This needs a static
    check that works zero-shot on any package. Finding: the existing stranding
    test ignores turn order and is bound to this package, and is not a loader
    check. Every bridge-activation fact has a delivery today. Candidate
    invariant for the loader: every fact in a scene's bridge activation has a
    `handoffs.yaml` delivery, and every transition trigger is committed by that
    scene's bridge operations, a pacing-event effect, or a delivery `cost` —
    making expiry unable to strand an exit regardless of storylet windows.
    **Answer (2026-09-13):** adopt that invariant as a loader validation, not a
    package test. Every fact in each scene's bridge activation must have a
    `handoffs.yaml` delivery, and every transition trigger must be committed by
    that scene's bridge operations, a pacing-event effect, or a delivery `cost`.
    Consequence: a package cannot have an exit fact reachable only through a
    storylet. No timed reachability simulation.
13. **Mutual exclusivity.** Does obligation-driven selection respect existing
    exclusivity, and can it strand a fact whose only source was the storylet
    not chosen? Finding: the engine has no exclusivity construct. Exclusivity
    today is one realization per fired storylet plus three `equals: false`
    activation guards, all in 1A; stranding by realization choice is already
    tested. Candidate answer: obligation ranking only chooses what to
    foreground among already-eligible content and never activates past a
    guard; stranding coverage folds into Q14. **Answer (2026-09-13):** closed
    with that rule. Obligation ranking foregrounds only content whose activation
    conditions already hold and never activates past a guard. Stranding is
    covered by Q14's loader invariant. No exclusivity schema.

### 3. Engine

3. **Where obligation derivation lives** — the projector or the engine.
   Finding: largely answered by code. The engine derives the gap
   (`_bridge_delivery_fact_ids`), `RuntimeState` stores the staged ids in the
   snapshot, the projector only renders them, and `TurnDelivery` exposes the
   tier to the bench. Also confirm the Decision #1 correction: the source is
   bridge activation, not `Transition.triggers`. **Answer (2026-09-13):** keep
   it in the engine as built. The engine derives the gap from bridge
   activation, `RuntimeState` holds the result as snapshot state, the projector
   only renders it, and the bench reads it through `TurnDelivery`. The Decision
   #1 correction is confirmed.
1. **Ranking competing obligations.** When several facts are missing, which
   does the Cue foreground? Finding: in 1A the bridge gap is a single fact;
   `patrol_return_pressure` is clock-supplied and is never a player obligation.
   Real competition occurs in two-fact `all_facts_true` bridges (1C, 2A, 2C, 3A)
   and `any_of` pools (1B, 2B, 3B), where `minimal_undelivered_facts()` already
   picks a smallest stable subset. Candidate rule: exclude pacing-event facts;
   foreground the fact whose last eligible source storylet closes soonest; break
   ties with `minimal_undelivered_facts()` order. No authored priority list.
   **Answer (2026-09-13):** use that rule. Exclude facts asserted by pacing
   events; among the remaining missing bridge facts, foreground the one whose
   last eligible, unfired source storylet reaches `latest_turn` soonest; break
   ties, including facts with no open source, by `minimal_undelivered_facts()`
   order. Note after the Q2 amendment: required source storylets no longer
   expire before the Deadline, so for bridge facts the deadline term mostly
   ties and `minimal_undelivered_facts()` order usually decides. The rule stands
   unchanged.
7. **How adaptive realizations are declared.** Finding: the premise needs
   moving. Route realizations are chosen as knowledge candidates in response to
   player action; the adaptive realizations in the worked example belong to the
   Complication, i.e. `PacingEvent`, which has none. Candidate shape: an ordered
   `realizations` list on `PacingEvent`, each with optional `when` fact
   predicates and authored text; first match wins; the loader requires the last
   entry to have no `when` (mandatory default). `effects` stay unconditional.
   Same shape as `item_placements` with `while_fact_false`. **Answer
   (2026-09-13):** adopt that shape. `PacingEvent.realizations` is an ordered
   list; each entry has optional `when` fact predicates and authored text; the
   engine passes the narrator the first matching entry only; the loader
   rejects a list whose last entry has a `when`. `effects` remain unconditional.
   Realization text states what is the case (Decision #6).

### 4. Details

4. **Cue idempotence.** A cue commits no fact, so nothing records that it fired.
   Finding: the existing hint tier already restages every turn from
   `nudge_after_turns` (`>=`), and it stages *undelivered* facts rather than
   clues the player already has. Snapshot restore is used only to discard a
   rejected or game-break turn, so any ledger belongs in snapshot state.
   Candidate answers: (a) no ledger — the Cue fires on the single turn where
   `turns_since_entry == nudge_after_turns`, idempotent by construction and
   replay-safe; (b) a `delivered_cue_ids` tuple on `RuntimeSnapshot` with a
   `SNAPSHOT_VERSION` bump. Also decide whether Cue replaces the hint tier's
   contents. **Answer (2026-09-13):** option (b). Add a `delivered_cue_ids`
   tuple to `RuntimeState` and `RuntimeSnapshot`, cleared on scene entry
   alongside the staged tiers, and bump `SNAPSHOT_VERSION` so older snapshots
   are rejected. Because the ledger is snapshot state, a turn discarded by
   validation or a game break does not count its cue as delivered. **Cue
   replaces the hint tier (2026-09-13):** from `nudge_after_turns`, each
   undelivered cue for the scene's missing bridge facts is delivered once,
   ledger-guarded, in Q1's ranking order; the every-turn instruction "Hint at
   the evidence with something a character says, notices, or hears on a radio.
   Do not make it a fact yet." (`cloudflare.py`) is removed rather than stacked
   beside the Cue.
6. **Early exit.** What happens to a scheduled complication when the player
   satisfies the transition before it fires? Finding: events are filtered by
   `current_scene_id`, so an unfired event is silently dropped on exit today. In
   1A and 2C the pressure fact is required to exit, so early exit is impossible
   there; only `override_deadline_3a` and `destruction_3b` can be skipped.
   Candidate answer: keep cancellation, and a bridge may not narrate a pressure
   its activation does not require. **Answer (2026-09-13):** keep today's
   cancellation: an unfired pacing event is dropped when its scene is left, and
   is never fired into the bridge. Authoring rule: a bridge may narrate only
   pressure facts its bridge activation requires.
10. **Promoting KMS to canon.** Finding: KMS is still only `plot.md` prose, in
    beat 1A.1's details and prose, which reach the narrator on scene entry and
    while 1A.1 is projected. Placement text is not a hidden anchor:
    `_placement_rules` sends "<item name> is <placement>." verbatim in every 1A
    prompt, so folding the carving into the `memory_card` placement would tie
    the carving to the card's hiding spot and invite unearned disclosure.
    **Answer (2026-09-13):** do not promote KMS to canon or to a placement. The
    carving lives in authored Cue text for `continuity_initiative_known` (for
    example a `cue_text` field on that `handoffs.yaml` delivery), such as
    "Kristin's initials, KMS, are carved into a drawer of Michelle's
    workstation." It reaches the narrator only on the turn that cue fires, so it
    cannot follow Kristin out of 1A and is never stated alongside the card's
    location. **Cue text home (2026-09-13):** an optional `cue_text` field on
    `FactDelivery` in `handoffs.yaml`, beside `fallback_text` and `costs`, so each
    missing fact's Cue-then-Deadline ladder is authored in one place. Not on
    `knowledge.yaml` reveals (several reveals can establish one fact) and not in
    a separate file.

### 5. Verification

15. **What "it works" means, measurably.** Finding: `TurnDelivery` already
    records which tier was staged and whether fallback text was used, so layer
    reach is observable today. Candidate answer, split by evidence gate:
    deterministic layer-reach metrics (scenes exited without Deadline, Deadline
    reached with cost applied, turns-to-exit against the pacing window) driven by
    scripted player personas through `scripted_provider` — authoritative, no
    sampling; live metrics only for narration quality (cue points at the right
    thing, complication gives no unearned knowledge), judged by LLM.
    **Answer (2026-09-13):** split by evidence gate. Authoritative evidence is
    deterministic: scripted player personas (at least thorough, stalling and
    wrong-lead) driven through the `tests/test_canon_journey.py` engine harness,
    asserting scenes exited before Deadline, Deadline reached with its cost
    applied, each cue delivered at most once, no stranded exit, and turns-to-exit
    within each scene's pacing window. Live runs are quality evidence only: cue
    relevance to the missing fact, and complications that create pressure
    without unearned knowledge, judged by LLM.
16. **Test methodology.** Live measurement needs a control arm and n ≥ 50 per
    arm; n = 10 cannot separate a 10% rate from a 25% one (p = 0.41). Finding:
    `bench compare` already provides Welch's t-test and minimum detectable
    effect. Candidate answer: live arms only for the quality questions in Q15;
    control arm is the engine with the new layers disabled; n ≥ 50 per arm via
    `bench compare`. Bench variations are package and prompt data, not engine
    switches. **Answer (2026-09-13):** the control arm is the same variation
    with a package `overrides` entry that strips cue text and `PacingEvent`
    realizations; both arms run concurrently so model drift cancels. Engine-only
    behaviour (expiry, hint-tier removal, the cue ledger) is verified by Q15's
    deterministic gate, not live. n ≥ 50 per arm, analysed with `bench compare`.
    No runtime layers-off flag and no comparison against historical ledger
    rows.

### Settled

5. **Retraction discipline.** **Closed** by the Scene 1A custody work: one
   positively named custody fact, asserted on recovery; the pressure event
   itself never changes custody, and the 1A patrol confiscates nothing. The
   rule for any future loss or confiscation is to retract the fact in the same
   accepted operation — no such path exists in the package yet.
11. **Turn accounting for optional storylets.** **Answer:** one player input
    plus its narrator resolution is one turn, including an optional storylet.
    The same scene-relative counter (`turn_index - scene_entered_at_turn`,
    verified 2026-09-13) drives `min_turns`, `nudge_after_turns`,
    `handoff_after_turns`, and `latest_turn`; there are no hidden storylet
    duration costs. If a future storylet genuinely represents several steps of
    elapsed time, author those steps explicitly or add a validated duration
    field later. Pacing allowances are sized independently per scene;
    `budget_seconds` stays a ceiling on the worst case, not a target.
12. **Turn cost for cues and complications.** **Answer:** a cue or complication
    rides on the ordinary player turn whose boundary activates it; it never
    consumes an extra hidden turn and never resets the scene-relative counter.
    The scene window itself provides the reaction allowance.
