# Missed-obligation escalation

Make every scene react to what the player has overlooked, instead of advancing
through a schedule of reveals. The story pressure arrives on its own timetable;
what that pressure *does* depends on the world's physical state, and what
Kristin notices depends on her knowledge state.

Status: design agreed, not yet specified to implementation depth. The open
questions at the end are the work remaining before this can be broken into
Ringer tasks. Re-checked against the code on 2026-09-13: none of the four layers
beyond Opportunity is built, and `latest_turn` still has no runtime effect.

**Terminology warning.** "Handoff" in this plan means the pacing fallback: at
`handoff_after_turns` the engine stages `staged_handoff_fact_ids` and delivers
`handoffs.yaml` fallback text. The engine now also has an unrelated *authored
reveal handoff*: an `action_evidence` matcher that inserts a candidate's
`delivery_text` on the turn the player earns it (see `docs/PRD.md`). Name the
layer distinctly before specifying this plan, or the two will be conflated.

## The four layers

| Layer | Purpose | Commits a fact? |
|---|---|---|
| **Opportunity** | Reward a relevant player action with the normal storylet. Player-led discovery, unchanged from today. | Yes, when realized |
| **Cue** | If a required thread is still unresolved, re-surface a clue the player already has, angled at the next action. | No |
| **Complication** | An independent external clock creates pressure around the missing thread. | Pressure facts only |
| **Handoff** | At the hard deadline, deliver only what is indispensable for leaving the scene, and charge for it. | Yes |

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

## What already exists (verified)

- `Storylet` and `StoryletRoute` carry `earliest_turn`, `target_turn`,
  `latest_turn`, and a `pacing_impact` of
  `none | brief_delay | pressure_increase | advance_readiness`.
- `pacing.yaml` gives each scene `min_turns`, `nudge_after_turns`,
  `handoff_after_turns`, and holds four timed `events` that assert pressure
  facts (`pressure_1a`, `purge_2c`, `override_deadline_3a`,
  `destruction_3b`).
- `ActivationRule.minimal_undelivered_facts()` already returns "the smallest
  stable set of facts which completes this rule" — the gap analysis this design
  needs.
- The engine already stages two tiers: `staged_hint_fact_ids` and
  `staged_handoff_fact_ids`, rendered as distinct narrator instructions.
- `handoffs.yaml` already carries `must_convey` groups and `fallback_text` per
  fact.

### What is missing

- **`latest_turn` has no runtime effect whatsoever.** It is read only by the
  `Storylet` / `StoryletRoute` validators and the loader's window checks;
  `_activate_pacing` never consults it. Every storylet window is an opening
  time with no closing time.
- Only four scenes have a concrete timed complication. The rest rely on the
  generic nudge/handoff thresholds.
- The KMS carving exists only as the beat detail string `KMS initials in
  drawer` and one prose sentence in `plot.md`. It is not a fact, so the
  narrator cannot recall it later — runtime context is a projection of
  committed facts, not transcript memory.

## Design decisions already settled

### 1. Obligations are derived, not authored

Do **not** author a parallel per-scene obligation list. A scene's obligations
are already authored, validated, and enforced as its transition's predicates:

```yaml
- id: t_1a_1b
  triggers:
  - {fact_id: michelle_lead_actionable, equals: true}
  - {fact_id: patrol_return_pressure, equals: true}
  required_dependencies: [memory_card]
```

Derive the unmet obligation set from `Transition.triggers` plus
`required_dependencies` for the scene's outgoing transitions, and rank with
`minimal_undelivered_facts()`. A hand-written list would duplicate this and
drift from what actually gates the scene.

Note that `patrol_return_pressure` is itself a trigger for `t_1a_1b`: in 1A the
Complication layer is already load-bearing for scene exit, not decoration.

### 2. Do not duplicate item possession as a fact

`required_dependencies: [memory_card]` guards against the item being lost, but
it does not prove possession. Shipped since this was written: Scene 1A has one
positively named custody fact, `memory_card_in_kristins_custody`, rather than a
location fact such as `memory_card_still_in_house`. It is asserted on recovery
and by the handoff fallback's `costs`, is a trigger on `t_1a_1b`, and gates
`SL-1A-D`. An absent fact satisfies `equals: false`, so it needs no seeding, and
the loader rejects an `equals: false` trigger on a fact nothing asserts true.
`item_placements` entries may carry `while_fact_false: <custody fact>` so the
engine stops stating a placement once the item moves. Use that pattern for any
other item: one custody fact per item, never an item ID as proof of possession.

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
all 36 storylets and every route, and today they do nothing. Making expiry real
converts the Complication layer from an authoring project into a behaviour
change on data that already exists, and it works in every scene without a
per-scene pass.

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
5. **Handoff with a cost.** If the lead is still missing at the deadline, an
   authored observation exposes the card or its information — and charges for
   it: the patrol notices her interest, the house is marked, or she leaves
   hurriedly.

The boundary to hold: the patrol makes the drawer *salient*; it never opens it.
Pressure that hands over knowledge collapses Complication into Handoff and
violates `pacing_events_must_create_observable_pressure_not_unearned_knowledge`.

## Carried-forward defects

Found by a separate continuity audit, re-verified against the package on
2026-09-12. They are real today, independent of the four layers, and can each
ship as its own brief. Handoff migration of a scene may rewrite its bridge, so
check that before fixing bridge prose.

- **3C resolution cascade (highest value).** `_apply_canonical_route_events`
  (`storygame/runtime/canonical_events.py`) commits each event and marks it
  fired before checking the next, and the six `canonical_resolution_events` are
  declared in chain order. Once `truth_no_longer_containable` holds, archive,
  escape, network consequences, Phase Two and completion all commit in one pass,
  before their storylets narrate anything. Sequence them, or require each one's
  player-visible realization before it commits. `portable_archive_secured` has
  no world item: 3C declares `memory_card` instead, so add `portable_archive`
  with custody starting at Rebecca and introduce it before Kristin must secure
  it.
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
- **Pacing reaction window.** A visible timed threat must precede the handoff by
  two complete turns, and every storylet's `latest_turn` must leave a turn
  before handoff. Only four scenes have a pressure event. Decided (2026-09-08):
  add `pursuit_1b` (turn 2, does not resolve the pursuit), a 1C security
  escalation, visible 2A scrutiny (Rebecca stays hidden) and a 3C collapse
  escalation, all at turn 2; move `destruction_3b` from turn 4 to 3; widen 1B to
  `2/4/5` and 3C to `2/4/6`; raise `budget_seconds` to 1890. These land as one
  change with `tests/test_scene_relative_pacing.py`: its `expected_windows`
  dict, the over-budget probe (`1890` → `1889`), and the sum-equals-budget
  assertion relaxed to `<=`.
- **Deferred until they surface in play:** 2A credentials visibly created by
  `SL-2A-B` before the supervisor confrontation (not re-verified), and an
  authored transit-card placement in 1B behind a `while_fact_false` guard.

## Open questions — what must be settled before implementation

These are the gaps. Each needs an answer before this plan can be split into
Ringer tasks.

### Scheduling and state

1. **Ranking competing obligations.** 1A has two unmet triggers
   (`michelle_lead_actionable`, `patrol_return_pressure`). When several are
   unmet, which does the scheduler foreground? Candidate rules: fewest
   remaining facts, nearest `latest_turn`, or an authored priority.
   **Recommendation:** prioritize the obligation with the nearest effective
   deadline, then use `minimal_undelivered_facts()` as the tie-breaker. Do not
   add a separate authored priority list; deadlines protect causal pressure
   from being starved, while the existing minimal-fact ranking keeps the choice
   grounded in authored transition requirements. **Answer: pending.**
2. **What `latest_turn` expiry *does*.** Three options: silently close the
   storylet, escalate it to the next layer, or force it. They differ sharply
   for a storylet whose fact is still required for exit. Undecided.
3. **Where obligation derivation lives** — the projector (which already reads
   knowledge state) or the engine (which already owns pacing). Affects testing
   surface and whether the bench can inspect it.
4. **Cue idempotence.** A cue commits no fact, so nothing records that it fired
   — and it would repeat every turn. Needs a delivered-cue ledger on
   `RuntimeState`, and a decision about whether that ledger is snapshot state
   (survives rewind) or turn-local.
5. **Retraction discipline.** **Closed** by the Scene 1A custody work: one
   positively named custody fact, asserted on recovery; the pressure event
   itself never changes custody, and the 1A patrol confiscates nothing. The
   rule for any future loss or confiscation is to retract the fact in the same
   accepted operation — no such path exists in the package yet.
6. **Early exit.** What happens to a scheduled complication when the player
   satisfies the transition before it fires? Cancel, or fire it into the
   bridge?

### Authoring format

7. **How adaptive realizations are declared.** `storylet-routes.yaml`
   realizations have `dramatic_intent` and `operations` but no state predicate.
   Each realization needs a guard, plus a rule for what happens when no
   realization matches the current state (a default is mandatory — the engine
   must always have exactly one to pass the model).
8. **Reconciling with `pacing_impact`.** Is Complication simply
   `pacing_impact: pressure_increase`, or a new concept beside it? If the
   former, the existing field is the hook and no schema change is needed.
9. **Scene exemptions.** 3C is a resolution scene and should be sequenced
   causally, not treated as a set of missed clues. Which scenes opt out, and is
   that authored or inferred from `freytag_phase`? See the 3C cascade defect
   under "Carried-forward defects": it is today's evidence that 3C is not
   sequenced at all.
10. **Promoting KMS to canon.** It needs a fact, a `knowledge.yaml` entry, an
    audience, and a relevance entry — otherwise, once committed, it follows
    Kristin to Los Angeles. Which scenes keep it in scope?

### Budget and safety

11. **Turn accounting for optional storylets.** Optional storylets should take
    time to resolve, but the plan does not yet define how many turns they
    consume or how those turns interact with a scene's `min_turns`,
    `nudge_after_turns`, and `handoff_after_turns`. Does every resolved
    storylet consume one player turn, can an authored storylet consume several,
    and are pacing thresholds measured in player actions or elapsed storylet
    turns? The answer must account for fast players who take few actions and
    slow players who explore many optional storylets, without imposing a global
    time ceiling. **Recommendation:** treat one player input plus its
    narrator resolution as one turn by default, whether it realizes an
    optional storylet or an ordinary action. Count those turns against the
    same scene pacing counter used by `min_turns`, `nudge_after_turns`,
    `handoff_after_turns`, and `latest_turn`; do not introduce hidden,
    storylet-specific multi-turn costs in this pass. If a future storylet
    genuinely represents several steps of elapsed time, author those steps
    explicitly or add a validated duration field later. This lets fast players
    reach the scene's causal beats with fewer optional discoveries and lets
    slow players encounter more pressure without making turn duration
    ambiguous. Pacing allowances are sized independently per scene;
    `budget_seconds` stays as a ceiling on the worst case, not a target to
    compress toward. **Answer:** one player input plus its
    narrator resolution is one turn, including an optional storylet. The same
    scene-relative counter drives `min_turns`, `nudge_after_turns`,
    `handoff_after_turns`, and `latest_turn`; there are no hidden storylet
    duration costs.

12. **Turn cost for cues and complications.** Cues and complications both
    reach the player who is *already* slow. Does a cue consume a turn or ride
    along with an ordinary one? Does a complication reset `nudge_after_turns`?
    **Recommendation:** a cue or complication rides on the ordinary player turn
    whose boundary activates it; it never consumes an extra hidden turn and
    never resets the scene-relative counter. The scene window itself provides
    the reaction allowance. **Answer:** use that recommendation.
13. **Mutual exclusivity.** Storylets are sometimes mutually exclusive, and
    their outcomes persist as world knowledge. Does obligation-driven selection
    respect existing exclusivity, and can it strand a fact whose only source
    was the storylet not chosen?
14. **Reachability.** Even with adaptive realization holding the path count
    fixed, expiry can now permanently close a storylet. Does any fact required
    for exit have a single source that can expire? This needs a static check
    that works zero-shot on any package, not an inspection of this one.

### Verification

15. **What "it works" means, measurably.** The metric is not "the storylet
    fired". Candidates: proportion of scenes exited without reaching Handoff,
    proportion reaching Handoff with a cost applied, and turns-to-exit
    distribution against each scene's authored pacing window.
16. **Test methodology.** Live measurement needs a control arm and n ≥ 50 per
    arm; this session established that n = 10 cannot separate a 10% rate from a
    25% one (p = 0.41), and two conclusions drawn at n = 10 turned out to be
    sampling noise.
