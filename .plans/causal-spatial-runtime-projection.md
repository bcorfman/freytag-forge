# Causal spatial and conversational projection plan

## Status

**Phases 0–1 complete; Phases 2–9 proposed.** This plan closes two connected
gaps between an approved causal blueprint and a playable runtime:

1. reviewed people, subjects, evidence, and groups must survive compilation as a
   spatial fact-backed world; and
2. those people must be able to initiate and sustain storylet-backed dramatic
   interactions with attributed speech, embodied action, stable voice, and
   committed consequences.

The plan applies to every supported genre. It does not add a mystery-specific
parser, infer placement or personality from prose, prescribe canned dialogue,
or hand-edit reviewed artifacts.

## Current baseline

The compiler prompt already requires backward planning: terminal truths, causal
events and timeline, then evidence/testimony/reachable opportunities and
concrete locations. The Vale reviewed blueprint contains 12 causal events, 21
evidence opportunities across eight locations, 15 realization routes, and 18
storylets.

The reviewed-blueprint-to-`CompiledStory` bridge discards evidence
opportunities, causal-event locations, and storylet availability locations.
`Participant` has only `id` and `role`; it has no declared public
presentation, initial placement, movement, or performance profile. Runtime
therefore creates only `at(player, opening)`, with no present NPCs, scene
subjects, evidence, or custody facts. The UI can advertise actions that the fact
world cannot support.

The current conversation boundary has a second, independent loss:

- `DialogueProposal` carries one speech string rather than an ordered
  interaction performance;
- dialogue is accepted only when the player explicitly addresses one visible
  NPC, so an NPC cannot initiate an eligible storylet interaction;
- when dialogue is present, runtime returns it instead of accompanying
  narration, so an embodied action beat is discarded;
- `Storylet` declares a dramatic question and realization modes but no
  initiator, social objective, tactic, response obligation, or multi-turn
  interaction frame; and
- the hosted API flattens the response to one line, preventing attributed speech
  and action beats from being rendered separately.

Spatial validity alone would therefore produce safe, addressable NPCs without
guaranteeing responsive, characterful conversation.

## Outcome

Every reviewed package must compile to a spatial runtime projection containing:

- named public NPC presentation and initial `at`/`present` facts;
- declared scene subjects, including inspectable people, remains, structures,
  vehicles, and other non-inventory targets;
- realized evidence/item/custody facts at declared causal locations;
- fact-triggered NPC/evidence movement or availability transitions;
- typed group encounters for an actual present ensemble; and
- player suggestions only when a current fact-backed target exists.

Every dialogue-capable package must also support:

- stable public NPC performance profiles without fixed dialogue lines;
- responsive player-initiated conversation with the addressed present NPC;
- bounded NPC-initiated conversation only through an eligible opening
  interaction or active storylet frame;
- multi-turn interactions that remain active until declared completion or abort;
- ordered, attributed speech and expressive or material action beats;
- speaker-private knowledge, current scene goals, relationships, stance, and
  recent interaction continuity in model context;
- atomic commit of movement, discovery, transfer, relationship, and other
  durable effects before any matching action beat is rendered; and
- structured API/frontend rendering that preserves speaker labels, quoted
  speech, and separate stage directions.

Facts remain the sole canonical mutable authority. Packages and storylets are
immutable inputs; transcript prose and UI segments are projections of accepted
decisions.

## Conversation experience target

A successful interaction should be able to produce this generic sequence
without authoring its literal prose:

1. an eligible present NPC initiates with a recognizable public manner and a
   dramatic objective;
2. the NPC's speech is attributed by public name and paired with an embodied,
   scene-compatible action;
3. the player answers freely;
4. the same NPC responds directly to the player's concern while retaining voice,
   stance, topic, and relationship continuity; and
5. any claimed relocation or other material change is already canonical fact
   before the corresponding action beat appears.

The player may ignore, refuse, redirect, interrupt, or leave. A conversational
storylet frames dramatic opportunity; it never becomes a command menu or forces
a prescribed response.

## Non-negotiable constraints

- No shared code may branch on a story ID, genre, person, victim, weapon, or
  mystery premise.
- Do not infer a person's room, public identity, manner, or voice from role,
  evidence holder, name, or prose. These must be declared and validated.
- Ordinary play remains LLM-proposal-first. Interaction frames guide dramatic
  performance but never replace interpretation with fixed player commands.
- A group encounter is not dialogue with an NPC named `household`. Every
  responder must be declared, present, named, and knowledge-safe.
- NPC initiation is legal only for a declared, currently eligible interaction
  frame whose initiator is present and available.
- Player-initiated dialogue retains addressed-target validation. The engine must
  not silently redirect speech to a nearby NPC.
- The LLM authors speech, intent realization, and expressive action. Policy
  validates identity, presence, knowledge, membership, effects, and protected
  information before commit.
- Expressive action may describe a transient gesture, expression, posture, or
  tone. Material action may describe only a visible change backed by accepted
  effects.
- Literal utterances and stage directions are event/transcript evidence, never
  canonical world truth.
- A normal turn still prefers one provider request and permits at most one
  shared recovery request. Dialogue quality critics remain offline or in
  bounded recovery, never an extra fast-path call.
- Do not hand-edit generated candidate, reviewed, compiled-story, audit, or
  runtime projections. Correct source or compiler contracts, then regenerate,
  review, and promote.

## Target authoring contracts

### Participant placement and movement

Extend `Participant` with public presentation, initial location/availability,
performance-profile reference, and movement-plan references:

```yaml
participants:
  - id: beatrice_harrow
    public_name: Beatrice Harrow
    public_role: estate solicitor
    public_description: Immaculately composed, with a watchful stillness.
    initial_location_id: grand_foyer
    initial_availability: present
    performance_profile_id: beatrice_public_manner
    movement_plan_ids: [beatrice_withdraws_to_study]
```

Add generic `NpcMovementPlan` declarations naming participant,
source/destination, fact-based activation/abort conditions, and whether the
player may accompany them. Validate route reachability and incompatible
simultaneous locations.

### NPC performance profiles

A performance profile guides model-authored behavior without supplying fixed
lines:

```yaml
npc_performance_profiles:
  - id: guarded_ally_manner
    participant_id: ally
    public_manner: guarded, protective, and decisive
    voice:
      register: familiar and direct
      cadence: brief observations followed by a concrete proposal
      diction: practical and specific
      avoidances: [bureaucratic phrasing, exposition dumps, repeated catchphrases]
    behavioral_cues:
      - checks the surroundings before discussing danger
      - reassures through decisive action rather than long explanation
```

Voice and behavioral cues are public performance guidance. Protected motives,
private knowledge, and deceptive intent remain facts exposed only through the
speaker-safe context boundary.

### Scene subjects and evidence realization

Add `SceneSubject` for inspectable non-inventory things:

```yaml
scene_subjects:
  - id: victim_remains
    kind: person
    location_id: west_gallery
    inspectable: true
    public_description: The victim remains where the household found them.
    evidence_opportunity_ids: [opportunity_wound, opportunity_gallery_clock]
```

Keep `EvidenceOpportunity` as the causal source of holder/location. Add
realization data naming whether an opportunity becomes physical scene evidence,
a document, testimony, or another askable/inspectable target. Project location
and custody into facts.

### Group encounters

Add immutable `GroupEncounter` declarations:

```yaml
group_encounters:
  - id: foyer_assembly
    location_id: grand_foyer
    label: gathered household
    participant_ids: [beatrice_harrow, thomas_pike, julian_vale, clara_mere, lydia_fenn]
    introduction_effects: [met_beatrice, met_thomas, met_julian, met_clara, met_lydia]
```

### Storylet interaction frames

Dialogue-capable storylets may reference one or more immutable
`InteractionFrame` declarations:

```yaml
interaction_frames:
  - id: ally_moves_conversation_to_privacy
    storylet_id: watched_market_transition
    initiator_id: ally
    participant_ids: [ally, player]
    initiation: npc_initiated
    dramatic_objective: Move the conversation somewhere private.
    opening_move: Greet warmly, signal immediate risk, and propose relocation.
    response_obligations:
      - answer a direct concern about immediate safety
      - preserve the ally's guarded confidence
    allowed_tactics: [reassure, warn, invite, deflect]
    permitted_movement_plan_ids: [market_to_alley]
    completion_truth_id: private_conversation_reached
    abort_truth_ids: [player_refuses_private_route]
```

Frames declare dramatic intent and legal outcomes, not exact speech. A storylet
may remain active across several turns; activation, continuation, completion,
and abort are separate fact-backed states.

## Target runtime interaction contract

Supersede the single dialogue string with one optional typed
`InteractionProposal` shared by individual and group conversation:

```yaml
interaction:
  interaction_frame_id: ally_moves_conversation_to_privacy
  initiation: npc_initiated
  participant_ids: [ally, player]
  segments:
    - kind: speech
      speaker_id: ally
      addressee_ids: [player]
      used_fact_ids: [market_is_watched]
      text: Walk with me. There are too many ears here.
    - kind: action
      actor_id: ally
      grounding: material
      text: The ally gestures toward the quieter alley.
      effect_refs: [begin_market_to_alley]
  effects:
    - bounded typed state operations
```

Speech segments name speaker, addressees, used fact IDs, and spoken text.
Action segments are either:

- `expressive`: transient performance that creates no durable truth; or
- `material`: visible state change whose declared effect references must
  validate and commit first.

The proposal may carry a reviewed storylet realization. Interaction effects,
storylet consequences, and material action claims must succeed on one cloned
candidate before any segment is rendered.

## Delivery phases

### Phase 0 — Characterize the spatial loss

- [x] Write cross-genre characterization tests: every suggested
  social/investigation action resolves only to a declared present NPC, group,
  visible item, or scene subject.
- [x] Add a Vale regression showing that reviewed holder/location opportunities
  do not survive into runtime facts.
- [x] Add a compiler audit report for participant placements, scene subjects,
  evidence realization/custody, groups, and unsupported suggestions.
- [x] Confirm that no runtime fallback invents missing state.

**Measured exit:** Vale currently has 7 declared participants and 21 evidence
opportunities but zero projected participant placements, evidence
realizations, or custody facts. All four opening suggestions lack a current
fact-backed social or inspectable target.

### Phase 1 — Spatial identity, target, and movement contracts

- [x] Add participant public identity/presentation, placement, availability, and
  movement-plan contracts.
- [x] Add scene-subject, evidence-realization, and group-encounter contracts.
- [x] Add all corresponding symbol namespaces and immutable bound-IR links.
- [x] Validate exactly one initial placement for each active participant,
  reachability, compatible custody/location, group-member co-presence, unique
  public names in a scene, and protected-public boundary safety.
- [x] Reject any first-action suggestion without an initially eligible
  fact-backed target.
- [x] Add generic profile minima for initial social contact and evidence-route
  diversity without genre runtime branches.

**Tests:** bad references, duplicate public names, two placements, missing
placement, unreachable movement, absent group member, missing subject,
incompatible custody, protected public leak, and unsupported suggestion.

**Exit: [x]** every advertised opening target has a valid immutable spatial
declaration; no runtime projection changes yet.

### Phase 2 — NPC performance and storylet interaction contracts

- [ ] Add `NpcPerformanceProfile` and `InteractionFrame` contracts and
  namespaces.
- [ ] Link dialogue-capable storylets to frames and validate initiator,
  participant, location, movement-plan, completion, abort, and tactic
  references.
- [ ] Require NPC-initiated frames to have a present-or-movable initiator and a
  bounded completion or failure-forward exit.
- [ ] Distinguish public voice/manner from protected motives and knowledge.
- [ ] Model activation, continuation, completion, abort, and recent-use markers
  separately so a first utterance does not automatically finish an interaction.
- [ ] Add generic profile minima for conversational route diversity and
  participant agency.

**Tests:** missing profile, unknown initiator, incompatible location, frame
without dialogue realization, unreachable permitted movement, protected motive
in public profile, immediate-completion-only interaction, failure-forward
cycle, and an NPC frame that gives the player no legal response.

**Exit:** a reviewed social storylet is a coherent multi-turn dramatic
situation, not only a destination fact or dialogue-mode label.

### Phase 3 — Compiler planning and conversation critics

- [ ] Amend the compiler prompt to plan the spatial timeline before routes,
  revelations, storylets, and interaction frames.
- [ ] Require public presentation separately from private motive, knowledge,
  deception, and scene goal.
- [ ] Generate dialogue-capable storylet pools with initiators, objectives,
  multiple tactics, response obligations, movement options, and bounded exits.
- [ ] Add deterministic spatial-continuity critics for actor/means/evidence/
  witness paths and supported opening interactions.
- [ ] Add interaction critics for participant agency, conversational dead ends,
  repeated tactics, voice-profile completeness, unsupported material actions,
  and protected-knowledge safety.
- [ ] Include typed repair diagnostics within the existing one-request plus one
  recovery budget.
- [ ] Extend human review to judge whether profiles distinguish characters
  without reducing them to catchphrases or stereotypes.

**Exit:** a candidate missing playable spatial realization or a viable
dialogue-capable interaction cannot be reviewed.

### Phase 4 — Runtime projection, bootstrap, and context

- [ ] Retain all spatial, performance, group, evidence, and interaction
  declarations in `RuntimeNarrativePackage`.
- [ ] Bootstrap `at`, `present`, public identity/role, availability,
  subject location, evidence custody, and discovery facts.
- [ ] Seed explicit false-valued interaction activation/completion/abort/
  recent-use facts without making package data mutable.
- [ ] Keep movement plans immutable; change location and availability only
  through validated fact operations.
- [ ] Add observer-safe current targets and speaker-private performance,
  knowledge, motive, relationship, stance, and recent-interaction slices.
- [ ] Expose active interaction frame and continuation obligations before other
  eligible storylets, while preserving freeform play.
- [ ] Keep off-scene participants, unavailable subjects, and protected
  information out of player-visible context.

**Tests:** save/load and artifact integrity; off-scene filtering; speaker versus
observer knowledge; profile projection; active-interaction continuation;
movement-plan eligibility; all genre fixtures use the same projection code.

**Exit:** runtime contains enough canonical and immutable context to author a
grounded conversation without inventing who, where, why, or what the speaker
knows.

### Phase 5 — Individual interaction proposal and atomic commit

- [ ] Add typed speech and expressive/material action segment contracts.
- [ ] Add `InteractionProposal` with initiation mode, frame ID, participants,
  ordered segments, effects, and optional storylet realization.
- [ ] Preserve player-addressed target validation for responsive dialogue.
- [ ] Permit NPC initiation only for an eligible opening interaction or selected
  storylet frame with a present and available initiator.
- [ ] Validate every segment for identity, presence, addressee, permitted
  knowledge, protected leakage, prompt parroting, narrator substitution, and
  frame membership.
- [ ] Require each material action segment to reference effects that commit on
  the same cloned candidate before rendering.
- [ ] Commit activation and continuation facts without forcing completion on the
  opening line.
- [ ] Support refusal, interruption, redirection, departure, completion, and
  failure-forward abort through the same proposal boundary.
- [ ] Preserve the one-request normal path and shared single recovery request.

**Tests:** NPC initiates an eligible interaction; ineligible initiation fails;
player follow-up stays in the same interaction; reply addresses the actual
concern; expressive gesture needs no durable fact; claimed relocation without
effects fails; movement commits before its action segment; refusal opens the
declared alternative; malformed interaction fails closed.

**Exit:** one present NPC can initiate and sustain a grounded, responsive,
multi-turn exchange below the hosted adapter boundary.

### Phase 6 — Group encounters and scene-subject interaction

- [ ] Generalize `InteractionProposal` to multiple named responders without a
  parallel dialogue authority.
- [ ] Validate group membership, co-presence, individual voice profile,
  addressee, knowledge, and effects for every segment.
- [ ] Commit group introductions before rendering names and make focused
  individual follow-ups possible.
- [ ] Generalize inspection to visible items and declared scene subjects through
  ordered action/speech segments and the shared commit contract.
- [ ] Prevent a group or inspection response from reusing opening orientation or
  fabricating absent evidence.

**Tests:** group question introduces named people; two responders remain
individually attributed; wrong or absent member fails; individual follow-up
uses the correct profile and knowledge; subject inspection commits declared
discoveries; malformed group/inspection proposals fail closed.

**Exit:** group conversation and inspection use the same fact-backed
interaction model as individual dialogue.

### Phase 7 — Structured rendering, hosted API, and frontend

- [ ] Return ordered interaction segments from runtime while retaining
  `lines` only as a temporary compatibility projection.
- [ ] Preserve public speaker name, quoted speech, addressees, and separate
  expressive/material action blocks in the hosted response.
- [ ] Render speech and stage directions as distinct accessible frontend
  components without making styling a truth authority.
- [ ] Preserve segment structure in transcripts, traces, artifacts, and
  save/load continuation.
- [ ] Render committed state, not provider JSON, and never drop narration merely
  because dialogue exists.
- [ ] Keep non-dialogue turns compatible with the existing minimal response.

**Tests:** individual and group segment order; full-name-first then unambiguous
short-name rendering; action beat retained beside speech; API/frontend parity;
artifact round-trip; protected text absent from every segment; compatibility
line derived deterministically from accepted segments.

**Exit:** the hosted experience can visibly present attributed dialogue and
embodied action in the transcript form the runtime validated.

### Phase 8 — Conversation-quality evaluation and simulation

- [ ] Extend deterministic storylet simulation with social, distrustful,
  avoidant, adversarial, and interruption-heavy interaction policies.
- [ ] Record initiation rate, continuation rate, refusal handling, repeated
  tactic/phrase rate, speaker-substitution failures, ungrounded material-action
  rate, protected leaks, and conversational dead ends.
- [ ] Add a cross-genre transcript rubric for directness, voice specificity,
  emotional legibility, embodied behavior, continuity, and player
  responsiveness.
- [ ] Use structural assertions and rubric thresholds rather than golden prose.
- [ ] Require at least two NPC profiles in a fixture to remain distinguishable
  under the same player question.
- [ ] Verify that active conversational storylets do not crowd out unrelated
  freeform action or force their completion.
- [ ] Verify successful normal interactions use one provider request and no
  evaluation critic on the fast path.
- [ ] Add manual review of representative individual, group, refusal, movement,
  and follow-up transcripts before promotion.

**Exit:** mystery, fantasy, sci-fi, and relationship fixtures each demonstrate
one NPC-initiated exchange, one player-initiated exchange, one direct multi-turn
follow-up, one expressive action beat, and one fact-backed material action
without leaks or continuity failures.

### Phase 9 — Vale regeneration, evaluation, and promotion

- [ ] Enrich the Vale source outline/Brief with foyer ensemble, public
  identities/roles/descriptions, performance profiles, body/scene subject,
  initial placements, movement intent, evidence realization, and interaction
  frames.
- [ ] Include at least one NPC-initiated opening or early social storylet, one
  responsive individual follow-up, one group introduction, and one
  movement-capable interaction with a refusal path.
- [ ] Compile a fresh candidate through the explicit live-compiler gate; never
  edit candidate or reviewed JSON manually.
- [ ] Run spatial audit, interaction critics, deterministic simulation,
  conversation-quality evaluation, and manual playthroughs.
- [ ] Confirm the victim can be examined without solution leakage and every
  clue/witness route remains reachable and temporally plausible.
- [ ] Confirm two evidence-backed resolution paths remain viable.
- [ ] Confirm named NPC speech, responsive follow-up, embodied action, and
  committed movement retain voice and continuity without opening reuse.
- [ ] Obtain review, promote the new artifact, update the fixture map, and run
  all cross-genre tests.

**Exit:** the promoted Vale package satisfies both causal-spatial playability
and the conversation-quality acceptance record.

## Definition of done

A reviewed package cannot advertise a social or investigative action unless the
compiled fact world contains its named people or inspectable target.

A present NPC can initiate or continue a declared dramatic interaction, speak
in a stable authored voice, respond materially to the player's actual input,
and perform grounded expressive or material action beats. Speech, action, and
effects remain attributed, knowledge-safe, atomically committed, persistable,
and structurally renderable across multiple turns.

The compiler's backward chain—outcome, event, means, evidence, custody, witness,
route, scene, participant objective, interaction, consequence, and
failure-forward exit—is validated and playable without story-specific runtime
code, canned dialogue, or prose-derived truth.
