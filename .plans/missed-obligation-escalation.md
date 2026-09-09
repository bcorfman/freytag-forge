# Missed-obligation escalation

Make every scene react to what the player has overlooked, instead of advancing
through a schedule of reveals. The story pressure arrives on its own timetable;
what that pressure *does* depends on the world's physical state, and what
Kristin notices depends on her knowledge state.

Status: design agreed, not yet specified to implementation depth. The open
questions at the end are the work remaining before this can be broken into
Ringer tasks.

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
- No scene distinguishes *card still taped under the drawer* from *card
  recovered but unread*. `SL-1A-D` activates on
  `continuity_initiative_known == false AND michelle_warning_known == true`
  and knows nothing about where the card physically is.
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

`required_dependencies: [memory_card]` already tracks possession. Adding
`memory_card_recovered` creates a second source of truth that will
desynchronise. What genuinely is unrepresented is the *other* physical state —
still taped under the drawer versus recovered but unread — and only that
deserves a new fact.

### 3. Three kinds of fact, kept separate

- **Physical** — where a thing is, independent of anyone's knowledge
  (`memory_card_still_in_house`).
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

## Open questions — what must be settled before implementation

These are the gaps. Each needs an answer before this plan can be split into
Ringer tasks.

### Scheduling and state

1. **Ranking competing obligations.** 1A has two unmet triggers
   (`michelle_lead_actionable`, `patrol_return_pressure`). When several are
   unmet, which does the scheduler foreground? Candidate rules: fewest
   remaining facts, nearest `latest_turn`, or an authored priority. **Recommendation:**
   prioritize the obligation with the nearest effective deadline, then use
   `minimal_undelivered_facts()` as the tie-breaker. Do not add a separate
   authored priority list; deadlines protect causal pressure from being
   starved, while the existing minimal-fact ranking keeps the choice grounded
   in authored transition requirements. **Answer: pending.**
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
5. **Retraction discipline.** Who retracts `memory_card_still_in_house`, and
   what validates that it happens exactly when possession changes? A missed
   retraction gives a patrol hunting for a card in Kristin's pocket.
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
   that authored or inferred from `freytag_phase`?
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
    ambiguous. The story has no global 1800-second ceiling; pacing allowances
    are sized independently per scene. **Answer:** one player input plus its
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
