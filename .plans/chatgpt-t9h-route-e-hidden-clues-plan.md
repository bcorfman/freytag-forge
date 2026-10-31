# Route E: hidden bench discovery

Status: proposed authoring only, for Brandon's review. Written 2026-10-28
(America/New_York), against HEAD `f8e0aa1cefd4e6a7319a17bfde6bb79ce8212b9c`.
No implementation, package, test, historical artifact, or deployment changes
are authorized by this document. No billed calls were made.

Resume here: review the exact story changes below, then validate an approved
candidate with the free checks before commissioning a billed probe. The hidden
location is decided; the discovery wording, earning boundary, automatic pickup,
and fallback wording below are proposals. Approval of hiding the clues is not
approval of all these details.

## Recommendation and boundaries

Keep the three existing `under: true` placements. Add `hidden: true` to each
item. A separate discovery, `bench_clues_recovered`, records finding and taking
all three. Its one-way `on_assert` effects move each to Kristin and reveal it,
exactly as memory-card recovery does. A later drop never retracts discovery or
offers it again. Do not use `brandon_face_known` for this event.

Require an explicit underside investigation. A general look, inspection, check,
or search of the bench does not earn discovery. This follows the 1A split
between inspecting the drawer and searching underneath it. There is no new
bench nudge storylet: the existing bench lead and revised safe cue supply the
place to investigate. Whether that is sufficient guidance is a live question.

Discovery names the three objects, but does not interpret the numbers or show
the photographed man's face. Reading the photograph remains a separate beat.
This is a proposed narrative distinction, not a new runtime mechanism. Taking
all three during an underside look follows the memory-card precedent, but is
still a plot choice for Brandon to approve.

Remove the premature cue and stale location wording before adding anything.
Do not add a bench `view`, underside placement prose, a narrator rule, a wider
observation exemption, a parser verb table, a new place, a hidden compartment,
an envelope, tape, or an invented list of numbers. The bench remains a fixed
seat. Nothing here resolves the independent drain-verifier or related-pickup
issues in the earlier Route E diagnosis.

## What the investigation establishes

Read: AGENTS instructions; PRD; contributor, workflow, grounding, narrator,
scene-fixing and player-input guides; testing and promotion runbooks; the 1A
and 1B sections of all seven story sources; the earlier Route E diagnosis;
the grounded-environment plan and relevant visibility, underside-scope,
search-opening and T9h preregistrations. Consulted the historical W1–W14
record at `5ea0119955c62b84699a8dc7878a4af770b55a7e` and its contents-giving
amendment. Current grounding guidance supersedes old W5 place examples.
Used the indexed codebase to inspect the route and reveal eligibility.

### The 1A precedent, including its limits

* `plot.md` puts the card under `michelle_drawer`. Hidden canon states where
  Michelle left it. The public opening gives the KMS carving and lower gap.
* `world.yaml` marks the card hidden. `memory_card_recovered.on_assert` moves
  it to Kristin with authored `text: with Kristin`, then reveals it. That fact
  records an event, not present custody (W7). W1/W4 keep location in the tree;
  W9's contents expansion still excludes hidden items.
* `k_sl_1a_b_r0` requires an underside action, reach to the drawer, and no
  officer in the house. It supplies the delivery and is `voiceable: false`.
  `k_sl_1a_b_r0w` is the officer-present alternative, with challenge/mark facts.
  Neither opening the drawer nor a broad inspection earns the card.
* `k_sl_1a_f_r1/r2` supply the gap instead. The repeatable r2 nudge is not the
  discovery. T9f applied the existing `voiceable: false` mechanism to these
  two public observations after officers spoke their statement text.
* `SL-1A-E` has its own source, activation, completion and realization IDs;
  recovery is separate from reading the card's files and recording. Reusing a
  source that completes on interpretation could strand a new discovery.
* `handoffs.yaml` has a **different**, deadline fallback: the
  `continuity_initiative_known` delivery recovers/reads the card and its costs
  assert `memory_card_recovered`. Do not copy that automatic deadline recovery
  for these clues: the request says the player earns their discovery.
* `pacing.yaml` sends the patrol at turn 4, into the house at 5, away at 7,
  and back at 9. It does not expose the card by listing it in pressure prose.
  1B's pursuit at 4 and lockdown at 8 likewise need no clue list or new event.
* T9b/T9d demonstrated the underside-search path and distinction from public
  drawer contents. An empty hidden-item observation requirement is intentional
  before discovery, but cannot prove that prose found the right thing.
  The delivery must be scored with the narration. T8's exhausted-underside
  correction is not permission to say an unrecovered hidden object is absent.

### Route E evidence and current harness

Historical rows: `bench/results/environment-narration/t9h/smoke/e/rows/rows.json`
and `summary.json`. Both opening payloads expose the token in THINGS. Both
openings append the token/number/photo cue. Both first inspections name clues
on the bench, and both first underside turns say nothing useful is underneath.
The recorded handoff and delivery fields are null: these are not earned finds.
The second opening narrates taking the token, although an opening does not
apply its proposed capture. The earlier diagnosis establishes the subsequent
under-to-on capture corruption and empty observation scope. Do not infer that
opening prose changed durable state.

The current parent plan already records the harness improvement: complete
world relations/hidden/axes, state digests, previews and opening proposed item
facts. Do not propose building that again. The current scene-start test's
explicit expectation that the clues are **not hidden** must change after
approval. The cap-exception row was found not to roll back fully; retain that
finding rather than counting a cap as an ordinary clean rejection.

### Later uses that must survive

| Clue | Later use | What recovery must preserve |
| --- | --- | --- |
| Transit token (`transit_card`) | `k_sl_1b_a_r1` compares it with numbers to establish `transport_route_identified`; B-R1 and C also provide route alternatives; 1C lists the token | Existing identity, intact/destroyed axis and `unavailable: destroyed`; movable custody; no decoding on discovery |
| Handwritten number sequence | A-R1 needs both token and numbers; handoff describes a freight-terminal/evacuation-tunnel lead | Actual declared object, readable after recovery; no invented digits, decoded meaning, or extra date-list object |
| Michelle's photograph | A-R2 connects its face with the follower; B-R1 uses showing it to the man for identity, warning, trust and route | Not a generic photograph of Michelle alone: storylets describe Michelle with Brandon; discovery does not yet identify the face or name him |

`brandon_face_known` is not `brandon_identified`. B-R1 currently does **not**
require prior A-R2, so showing an already recovered photo directly must still
work. B-R2, asking the man about Michelle, does not require a photograph in
its knowledge contract. Preserve that route. Its route-definition dramatic
intent currently says photograph, a mismatch corrected below. C-R1/R2 require
identity and the warning, and may independently establish the route while
escaping. The departure bridge requires route, identity, warning and resolved
pursuit; it does not require recovered clues. Keep that alternative intact.

A-R1 and A-R2 share a completing storylet: either interpretation can spend
SL-1B-A. This proposal preserves that choice; it does not promise that both
interpretations remain separately earnable afterward. Test each from a fresh
post-discovery state, and test direct showing as the continuation.

## Exact proposed source edits

Every edit below is a **PLOT CHANGE — approval required before application**,
including companion world and route declarations. Paths are relative to
`data/stories/continuity-initiative/`. Only the listed spans change. “Absent”
means insert at the stated anchor; it is not an instruction to replace a file.
No generated projection is edited. Test work is specified separately rather
than inventing test code during a no-code planning task.

### 1. `plot.md` — PLOT CHANGE

Immediately after the scene 1B `**Plot:**` paragraph, old: absent.

New:

```markdown
**Hidden canon:** Michelle left a transit token, a handwritten number sequence and her photograph under the park bench. All three stay hidden until Kristin searches beneath the bench. She retrieves them together and keeps them with her. Finding them does not identify the transport route or the man in the photograph.
```

In 1B.1, old:

```text
The records suggest that the mass disappearance was preceded by years of secret tests.
```

New:

```text
Kristin searches beneath the park bench and retrieves Michelle's transit token, handwritten number sequence and photograph. She keeps all three with her. Comparing the token with the sequence identifies a freight route out of the city. Studying the photograph reveals that it shows the man watching her. Showing it to him gives him a reason to identify himself.

The records suggest that the mass disappearance was preceded by years of secret tests.
```

This is canon, not a public Details list or entry sentence. Capture the actual
compiled prompt to prove it stays out before discovery. If the compiler
projects this paragraph early, stop: follow the same hidden-canon/knowledge
separation as 1A rather than making the entire paragraph public.

In 1B.2, old:

```text
The man watching Kristin waits near the service path, close enough for Kristin to show him Michelle's photograph.
```

New:

```text
The man watching Kristin waits near the service path. Once Kristin has recovered Michelle's photograph, she can show it to him. She can also question him about Michelle.
```

Entry, placements and Details remain as written. In particular do not add
clue names to 1B.1 Details. The later 1B.2 Details already names the photograph;
free prompt captures must check that hidden-item filtering suppresses it until
recovery, including on a photo-free B-R2 path.

### 2. `world.yaml` — PLOT CHANGE

Old:

```yaml
- id: transit_card
  name: Transit token
  axes:
  - {intact: [], destroyed: [broken, snapped, crushed]}
  unavailable: destroyed
- id: michelle_photograph
  name: Michelle's photograph
  scoped_aliases: [photograph, photo]
- id: number_sequence
  name: handwritten number sequence
  aliases: [number sequence, handwritten sequence]
```

New:

```yaml
- id: transit_card
  name: Transit token
  hidden: true
  axes:
  - {intact: [], destroyed: [broken, snapped, crushed]}
  unavailable: destroyed
- id: michelle_photograph
  name: Michelle's photograph
  hidden: true
  scoped_aliases: [photograph, photo]
- id: number_sequence
  name: handwritten number sequence
  hidden: true
  aliases: [number sequence, handwritten sequence]
```

Immediately before `- transport_route_identified` in `facts`, old: absent.

New:

```yaml
- id: bench_clues_recovered
  on_assert:
  - {move: transit_card, parent: kristin, text: with Kristin}
  - {reveal: transit_card}
  - {move: number_sequence, parent: kristin, text: with Kristin}
  - {reveal: number_sequence}
  - {move: michelle_photograph, parent: kristin, text: with Kristin}
  - {reveal: michelle_photograph}
```

No change to the memory-card word guard. The new discovery's explicit
`leak_terms` below guard multiword clue names. Do not silently create global
single-word guards for “number” or “picture”; those can break unrelated scenes.

### 3. `knowledge.yaml` — PLOT CHANGE

In `facts`, immediately before `transport_route_identified`, old: absent.

New:

```yaml
- id: bench_clues_recovered
  purpose: Kristin has recovered the three clues hidden under the park bench.
```

In `knowledge`, immediately before `k_sl_1b_a_r1`, old: absent.

New:

```yaml
- id: k_sl_1b_d_r1
  statement: Kristin finds Michelle's transit token, handwritten number sequence and photograph under the park bench and keeps them with her.
  voiceable: false
  reach_entity_ids: [park_bench]
  earn_when: looks, searches, inspects or checks beneath the park bench
  action_evidence:
  - [look, search, inspect, check]
  - [under, beneath, underside]
  - [park bench, bench]
  entity_ids: [kristin, park_bench, transit_card, number_sequence, michelle_photograph]
  aliases: [bench clues recovered]
  audience: {kind: public, player_visible: true}
  available_in_scenes: [1B]
  requires:
  - fact_id: bench_clues_recovered
    equals: false
  establishes:
  - op: assert
    fact_id: bench_clues_recovered
    value: true
  source:
    kind: storylet_realization
    storylet_id: SL-1B-D
    realization_id: SL-1B-D-R1
  relevance:
    entity_ids: [park_bench]
    priority: 10
  leak_terms:
  - transit token
  - handwritten number sequence
  - number sequence
  - handwritten sequence
  - Michelle's photograph
  - Michelle's photo
  - bench clues recovered
  delivery_text: "Kristin reaches beneath the park bench. She retrieves a transit token, a handwritten number sequence and Michelle's photograph. She keeps all three with her."
```

No `must_convey` is added just to restate the entire delivery; the exact authored
delivery is the disclosure boundary. Existing multi-group evidence and reach
are reused. These particular earning words and this three-item delivery are
new authoring, not a measured win. `feel` is intentionally not smuggled into
the exact list: test the semantic path first, then seek an author-reviewed
alias if it misses, as the player-input guide requires.

For each of `k_sl_1b_a_r1`, `k_sl_1b_a_r2`, `k_sl_1b_b_r1`, old:

```yaml
  requires: []
```

New:

```yaml
  requires:
  - fact_id: bench_clues_recovered
    equals: true
```

In `k_sl_1b_a_r2`, old:

```yaml
  statement: 'A photograph hidden in Michelle’s dead drop gives Kristin the face of the man who has been following her.'
  earn_when: examines Michelle's photograph beneath the park bench
```

New:

```yaml
  statement: 'The photograph recovered from Michelle’s dead drop gives Kristin the face of the man who has been following her.'
  earn_when: examines Michelle's recovered photograph
```

Keep its action evidence, delivery and `brandon_face_known` effect. Keep A-R1's
comparison evidence and route effect, B-R1's four effects, and B-R2/C-R1/C-R2
requirements and effects. Do not gate all of B on recovery: that would remove
the photo-free questioning path. `explain_reveal` explicitly checks `requires`
before source activation and reach, so these are real eligibility gates, not
prose requests. Verify the normal proposal/commit path too, not only the exact
matcher; no direct proposed operation may bypass them.

### 4. `handoffs.yaml` — PLOT CHANGE

These are deadline/cue deliveries, distinct from the earned discovery's
`knowledge.yaml.delivery_text`. Do not add recovery to their `costs`.

For `transport_route_identified`, old:

```yaml
  must_convey:
  - [transit token, handwritten sequence, Michelle's dead drop, number sequence, Michelle's drop]
  - [freight terminal, transport route, evacuation tunnels, freight yard, old freight yard, yard route]
  fallback_text: >-
    The transit token and handwritten sequence from Michelle's dead drop identify the transport route. They point Kristin
    toward the supposedly abandoned freight terminal and its evacuation tunnels.
  cue_text: A transit token and a handwritten number sequence lie beside Michelle's photograph.
```

New:

```yaml
  must_convey:
  - [transport route, freight route]
  - [freight terminal, freight yard, old freight yard]
  fallback_text: >-
    The transport route leads toward the supposedly abandoned freight terminal and its evacuation tunnels.
  cue_text: The bench could be nothing, or it could hold the only lead Michelle prepared for her.
```

The new cue copies the existing 1B.1 sentence. The fallback removes a physical
claim about unrecovered objects while retaining the existing deadline route
delivery. It does not teach how the route was learned: that existing forced
progression limitation remains. The narrower `must_convey` now requires the
freight destination explicitly; check composed A-R1 and C deliveries through
the handoff validator. Do not assume their raw sentences alone suffice.

For `brandon_identified`, old:

```yaml
  must_convey:
  - [Brandon Corfman, Brandon, Michelle's photograph, Michelle's photo, photo of Michelle, picture of Michelle]
  - [identified himself, person in Michelle's photograph, source in the photograph, Brandon introduced himself, the man in Michelle's photo, identified the man in the photo, admitted he was the one in Michelle's photo]
```

New:

```yaml
  must_convey:
  - [Brandon Corfman, Brandon]
  - [identified himself, introduced himself, says his name is, said his name was]
```

Same record, old:

```yaml
  fallback_text: >-
    The man identified himself as Brandon Corfman, the person in Michelle's photograph. Kristin finally knew the source
    in the photograph had found her in the park.
  cue_text: The man watching Kristin waits near the service path. Michelle's photograph may be worth showing him.
```

New:

```yaml
  fallback_text: >-
    The man identified himself as Brandon Corfman, Michelle's contact.
  cue_text: The man watching Kristin waits near the service path.
```

Keep the `trust_brandon` retraction cost. Keep the pursuit and missing-alive
deliveries unchanged. The first cue was a certain leak of all three objects;
the identity cue and fallback were additional premature photograph references.
Deleting only the first cue cannot fix either the opening THINGS exposure or
those later references. Cue text is appended after generation: compare its
composition free, rather than billing narrator calls to test the append.

### 5. `storylet-routes.yaml` — PLOT CHANGE

In the fact registry before `transport_route_identified`, old: absent.

New:

```yaml
- id: bench_clues_recovered
  definition: Kristin has recovered the three clues hidden under the park bench.
  used_by_storylets: [SL-1B-D, SL-1B-A, SL-1B-B]
  used_by_transitions: []
```

In SL-1B-A's activation, old:

```yaml
    conditions: []
```

New:

```yaml
    conditions:
    - fact_id: bench_clues_recovered
      equals: true
```

In SL-1B-B-R2, old:

```yaml
    dramatic_intent: Kristin confronts him with the photograph; Brandon admits prior Initiative work and that the
      missing may still be alive, but withholds the protected JANUS role.
```

New:

```yaml
    dramatic_intent: Kristin questions the man about Michelle; Brandon admits he knew her and that the
      missing may still be alive, but withholds the protected JANUS role.
```

Immediately before SL-1B-A, old: absent.

New:

```yaml
- id: SL-1B-D
  scene_id: 1B
  title: Beneath the Park Bench
  activation:
    scene_id: 1B
    conditions:
    - fact_id: bench_clues_recovered
      equals: false
    pacing:
      earliest_turn: 0
      target_turn: 2
      latest_turn: 12
      pressure_bias: normal_before_target; prefer_after_target; strongly_prefer_near_latest
  pressure_role: Let a search beneath the park bench recover Michelle's clues before the park closes.
  realization_options:
  - id: SL-1B-D-R1
    dramatic_intent: Kristin searches beneath the park bench and keeps the transit token, handwritten number sequence and Michelle's photograph.
    source_beats: [scene-1b1--michelles-dead-drop]
    operations:
    - op: assert
      fact_id: bench_clues_recovered
      value: true
    eligible_storylet_event_id: null
    helps_transition_triggers: []
    protected_knowledge_boundaries:
    - brandon_history
    - janus_selection_system
    - janus_phase_two
  completion_or_abort:
    complete_when:
    - fact_id: bench_clues_recovered
      equals: true
    abort_when:
    - scene_id_not: 1B
  non_coercion_note: Offer as a consequence of free-text investigation. Do not present it as a choice or required command; equivalent careful searches may validate the same operation.
```

Independent source/completion follows SL-1A-E. It prevents finding the objects
from completing SL-1B-A before interpretation. Latest 12 keeps a late search
available within the scene's existing 13-turn ceiling; it is a proposed timing
choice. Do not add D to the departure bridge, forced fallback or obligations:
pressure must not award discovery. Keep the existing A/B/C transition routes.
Test A's existing target/latest 2/3 after a late find; if its activation window
actually prevents interpretation, stop for a narrowly specified timing
amendment rather than quietly changing all 1B timing.

### 6. `storylets.md` — PLOT CHANGE

In SL-1B-A, old Available when:

```markdown
- Kristin reaches the park/dead-drop area.
- The dead-drop materials remain recoverable.
```

New:

```markdown
- Kristin has recovered the three clues beneath the park bench.
```

In that record's Effects, old:

```markdown
- May establish possession of the `transit_card`.
```

New: delete that line. Recovery belongs to D.

In that record's Completion, old:

```markdown
- Kristin has recovered the dead-drop materials or enough of them to continue.
```

New:

```markdown
- Kristin has identified the transport route or recognized the man in the photograph.
```

In that record's Participants / items, old:

```markdown
- List of earlier disappearance dates
```

New: delete that line. It is not one of the three declared recoverable objects.
Keep the existing earlier-tests interpretation in narrative canon; this plan
does not create a fourth physical clue to satisfy stale storylet inventory.

Immediately before SL-1B-A, old: absent.

New:

```markdown
### SL-1B-D — Beneath the Park Bench

**Source beats:** [1B.1 — Michelle’s Dead Drop](plot.md#scene-1b1--michelles-dead-drop)

**Allowed scene:** `1B`

**Available when**
- Kristin has not recovered the clues under the park bench.

**Participants / items**
- Kristin Schweitzer
- Park bench
- Transit token
- Handwritten number sequence
- Michelle's photograph

**Dramatic purpose**
- Reward an underside search with the clues Michelle left for Kristin.

**Possible realizations**
- Kristin searches beneath the bench, retrieves all three clues, and keeps them with her.

**Effects**
- Sets `bench_clues_recovered`.

**Completion**
- Kristin has recovered the three clues.

**Abort**
- Kristin leaves scene 1B.

**Protected boundary**
- Finding the clues does not identify the route or the photographed man.
- It does not identify Brandon, establish trust, or reveal the fate of the missing.

**Pacing window**
- earliest: `turn 0`
- target: `turn 2`
- latest: `turn 12`

---
```

In the summary table, old:

```markdown
| [1B](plot.md#scene-1b--the-lead-in-the-park) | `SL-1B-A` … `SL-1B-C` | Dead-drop clues, Brandon trust, pursuit |
```

New:

```markdown
| [1B](plot.md#scene-1b--the-lead-in-the-park) | `SL-1B-A` … `SL-1B-D` | Hidden clue recovery, clue interpretation, Brandon trust, pursuit |
```

### 7. Files deliberately unchanged

`pacing.yaml`: old = new for every 1B record (`pursuit_1b` at 4,
`park_lockdown_1b` at 8). Neither exposes the clues. No discovery cost or timed
auto-reveal is added. Scene frames and the safe entry knowledge stay unchanged.
The six strings in `scripts/ringer/transcript_1a/live_baseline.py` stay unchanged.
No narrator/judge prompt or shared runtime change is proposed. Existing plan
and smoke records remain historical evidence, not files to rewrite as a pass.

## Earning actions and route behavior

All new probe/test inputs use imperative player voice. Exact evidence is a
small authored alias set, not a new command parser. Semantic fallback remains
bounded by eligibility and runtime validation. A positive below is a required
outcome for the approved design, not a claim that it was executed here.

| Fresh pre-discovery input | Required result |
| --- | --- |
| `Look under the park bench.` | Exactly D; all three recovered and carried by Kristin |
| `Search beneath the bench.` | Same |
| `Inspect the underside of the park bench.` | Same |
| `Check under the bench.` | Same |
| `Feel beneath the park bench.` | Equivalent earning act via the bounded semantic path; measure it, then author-review an alias if needed |
| `Inspect the park bench.` | No discovery or clue list |
| `Search the park bench.` | No discovery; broad search does not specify the hidden side |
| `Check the park bench.` | No discovery |
| `Sit on the park bench.` | Seating only; no discovery, no bench opening |
| `Inspect the storm drain.` | No bench discovery; preserve fixed drain and control behavior |
| `Examine Michelle's photograph.` | No reveal while hidden, even if the player guesses its name |
| `Compare the transit token with the number sequence.` | No route reveal before recovery |
| `Show Michelle's photograph to the man.` | No photo-based identity reveal before recovery |

For a deliberate raw-language safety test, preserve an existing negation-corpus
case and substitute the bench target; label it raw-language, not canonical
probe style. A denial of an underside search must never satisfy evidence.
Also test two unrelated acts whose words would accidentally fill all groups;
the exact matcher must not compose them into one earned find.

After recovery: `Examine Michelle's photograph.` earns face knowledge only;
`Compare the transit token with the number sequence.` earns the route only;
`Show Michelle's photograph to the man.` retains B-R1 even without prior face
inspection. `Ask the man about Michelle.` retains B-R2 before or after
recovery, subject to existing scene eligibility. Test those branches separately
so a spent source is not mistaken for a hidden-item failure.

Keep Route E exactly:

| Index | Existing input | Expected change |
| --- | --- | --- |
| opening | No player action | No clue names, no pickup, no recovery fact |
| 0 | `inspect the park bench` | Public bench observation, no hidden clues |
| 1 | `look under the park bench` | D delivered once; all three carried and visible; no route/face/identity facts |
| 2 | `search the park bench` | No second recovery; no restored bench custody |
| 3 | `check the park bench` | Same; pursuit pressure may occur normally |
| 4 | `look under the park bench` | No rediscovery; exhausted underside only if the current tree supports it |
| 5 | `inspect the storm drain` | Existing independent control; any rejection reported separately |

Also run a fresh underside-first state and a late search after turn 8. Recovery
must not depend on the initial inspect or on a clock-only gift. After a later
`Put the transit token under the park bench.`, the fact remains true, the token
is visible under the bench, and no “already empty” claim or duplicate discovery
is allowed. That case may expose the outstanding visibility/capture defect;
do not hide it by broadening this authoring change.

## Verification proposal, cost and tests

### Cheapest free check: static composition, then hermetic candidate

First compare two arms, current / proposed cue and fallback text, across four
frozen states: opening, ordinary bench inspection, photo-free questioning and
deadline fallback. Eight composed outputs, zero model calls, **$0**. This
immediately catches the premature names and checks must-convey/fallback text
against itself. It does not prove concealment in the narrator payload.

After plot approval, load an isolated candidate through the real package
loader, not hand-edited compiled data. Compare current / candidate across six
checkpoints (12 per package): 1B opening; broad inspection; first underside
search; post-recovery inspection; repeat underside search; deadline without
recovery. Run both the real package and a synthetic unrelated story, 24
checkpoint evaluations, **$0**. Stub network inference, not the world or
reveal validator. Record full snapshots and complete composed prose. The
current arm is a negative control: it should reproduce the old exposure.

Check exact earning evidence for the table above; preserve raw-language tests
separately. Capture opening, normal, reveal, recovery and fallback payloads
with network stubbed using the existing prompt-capture procedure
(`.plans/world-model-s1/prompt_capture.py`). Require unrelated payloads to stay
byte-identical. Hidden clue names must be absent from narrator material,
including THINGS, PLAYER, public Details, NPC talk and appended cues. A bounded
reveal selector may receive its permitted private candidate; that is distinct
from sending hidden clues to the prose narrator.

Require exactly one delivery and a single atomic six-effect recovery. No
`brandon_face_known`, `brandon_identified`, `transport_route_identified`, trust,
or warning at that step. Rejected narration restores the complete snapshot,
including pacing and staged cues. Reassertion, save/load and a later drop must
not reset custody. A zero-relation observation is expected before discovery;
its empty list is not evidence of narration correctness.

### Cheapest billed probe: semantic earning boundary

The exact paths and cue append are free; the cheapest unresolved model question
is whether the existing bounded semantic matcher respects the new earning
statement. Reuse the existing matcher/probe method, through Ringer, after the
free candidate passes. Two arms: P0 current eligible 1B reveal candidates;
P1 proposed candidates at the same unrecovered checkpoint. Six inputs:
`Look under the park bench.`, `Feel beneath the park bench.`,
`Inspect the park bench.`, `Search the park bench.`,
`Examine Michelle's photograph.`, `Inspect the storm drain.`
Ten samples per input per arm = **120 logical matcher evaluations**.

Replay the actual semantic matcher request rather than a substitute question.
Use the existing adapter's actual per-candidate/request fan-out when building
the manifest: 120 logical evaluations are not necessarily 120 HTTP calls.
`_semantic_authored_handoff` limits the shortlist to six and the provider's
semantic-fallback budget to 40. Restore an independent provider/checkpoint for
each sampled action; do not reuse one provider for 120 calls and mistake budget
exhaustion for semantic refusal. Preserve the real projected shortlist and
record exclusions as well as scores. The adapter calls `reaches_reveals` once
per semantic evaluation; check its HTTP accounting rather than assuming one
request per candidate.
Budget estimate **under $0.01**, hard Worker ceiling **$0.02**, no narration
calls. Estimate is based on earlier Jev probes, not current price research or
a spend authorization. Dry-run must report the HTTP cap before a paid run.
If the actual adapter exceeds that ceiling, return a revised estimate first.

Read every answer. P1 must accept the two underside inputs in at least 9/10
samples each and select no reveal on the four near misses (zero false earns).
P0 is a diagnostic control, not a requirement to fail every input. Exact
matching may bypass this call in real play; score that free path separately.
This probe qualifies earning wording only, not concealment or narration.

### Smallest prose and integration checks

For prose, two arms (current payload / generated proposed payload) on frozen
opening, pre-find inspection and discovery states; 10 samples per state per
arm = **60 narration calls**, estimated **$0.042**, hard cap **$0.06** using
the earlier ~$0.0007/call planning estimate. Score narration plus the runtime
delivery, and item facts separately. Never put hidden clue names back into
P1's pre-find prompt for parity. No new rule arm is proposed. Stop on any
pre-find clue exposure, invented photograph content, unintended route/identity
reveal, false empty before finding, or fixed-bench move. Prompt samples cannot
replace full-turn validation.

Then a separately approved candidate-only integration smoke: unchanged Route E,
**3 replicates × 6 turns = 18 turns plus 3 openings**, expected **$0.03–$0.04**,
Worker ceiling **$0.07**, proposed total cap **240 HTTP calls**. Use the actual
dry-run request accounting to confirm headroom. New output directory and
manifest; do not rerun/overwrite the old S sample or call this T9h F. Require
every discovery to commit, no early clue exposure, correct custody, no duplicate
find, exact rollback on ordinary rejections, unchanged per-turn budgets, and
separate reporting of drain failures and latency (10 s target retained).
Three repetitions are the scene-fixing smoke minimum, not a statistical
comparison; the general runbook recommends at least four for bench comparisons.

Do not start these billed stages on the authority of this plan. Stop on a
quota, 429, 5xx or cap; retain partial artifacts and no replacement samples.
Freeze human labels before joining verdicts. No threshold waiver, production
switch or deployment follows automatically from a pass.

### Tests to add or change after approval

* Package/schema and storylet authoring tests: the new fact is declared in all
  registries; the D source exists; realization operations match knowledge;
  placements, kinds, unavailable axis and hidden flags are correct. Old
  generated-package/hash expectations must be regenerated, never hand patched.
* New focused hidden-bench discovery test module: all positive/negative inputs,
  first-turn/late discovery, reach, exactly one reveal, semantic refusal/tie,
  no same-turn comparison/identity gift, and photo/name guesses before earning.
  Include a second story with different nouns and three hidden objects.
* `tests/test_live_baseline_scene_start.py`: change the existing clue-state
  expectation from `hidden=False` to `hidden=True`; keep `park_bench`/`under`;
  assert absence from public contexts and no opening state mutation. Do not
  hand-seed the discovery into the deterministic journey prefix.
* `tests/test_live_baseline_evidence.py`: retain all current recorder checks;
  use world snapshots/digests to demonstrate the three custody/reveal changes
  and full rollback. Keep cap failure distinct from an ordinary rejected turn.
* Existing authored-handoff/reveal-eligibility tests: A-R1/A-R2/B-R1 unavailable
  before recovery, available after it; B-R2 still available independently;
  direct operation proposals cannot bypass knowledge prerequisites; D fires
  independently of SL-1B-A. Test separate interpretation branches and source
  spending rather than promising both A realizations in one journey.
* `tests/test_voiceable_knowledge.py`: add only D's new nonvoiceable ID to the
  exact-set expectation. NPC dialogue cannot quote its discovery statement.
* `tests/test_pacing_handoff.py` and cue tests: opening and later staged cues
  reveal no clues; deadline fallback can progress without retrieving them;
  identity fallback doesn't conjure a photo; route/identity must-convey edits
  accept intended composed deliveries and reject missing information.
* Observation/underside-exhaustion and item-facts tests: hidden pre-find scope,
  no engine opening of the bench, recovery once, return of a visible token
  underneath, no false empty, custody after drop, and unrelated moves rejected.
* Journey/save-load/dependency tests: recovery persists, held objects travel,
  destruction still triggers the existing unavailable dependency handling,
  photo-free departure does not reveal the objects, and 1C remains playable.
  Update scripted player routes that currently inspect guessed hidden objects
  to earn recovery first; do not alter unrelated route strings preemptively.

Use the runbook's free focused pytest entry, then quick suite including affected
journeys. Finish implementation with Ruff autofix/format and affected checks;
full suite with the existing coverage gate once before merge. This plan does
not introduce a new verification boundary requiring a runbook rewrite. Any
later operational recipe must update the existing entry in place. Promotion
still requires the tested main SHA's staging deployment and staged evidence.

## Risks, unanswered questions and completion evidence

* The most important unverified interaction is whether the recovery's three
  story effects are applied in the observation preview baseline or mistaken
  for unrelated narrator moves. 1A proves the mechanism, not this three-item
  combination. Inspect real previews; do not add a blanket scope exemption.
* Generic “photo”/“token” hallucinations may evade multiword leak scanning even
  with the declared items hidden. Test composed prose and wrong synonyms.
  A global single-word guard is not approved here; propose one only from a
  demonstrated failure and check other scenes before broadening it.
* Handoff fallback changes intentionally remove clue provenance and narrow
  content matching. They may change which fallback sentence is appended.
  They preserve the existing deadline escape, but need author approval and
  full-output checks. If Brandon wants discovery mandatory for departure,
  that is a separate plot decision, not an implicit new bridge prerequisite.
* Physical possession is not permanently guaranteed by an event fact. Reach
  and current-world validation after putting down, losing or destroying a
  clue need explicit tests; do not reinterpret recovery as current custody.
* Late recovery may collide with A's old 2/3 pacing window, B source spending,
  or the 13-turn ceiling. The new D window alone is not proof of playability.
* Photo-free B-R2 can expose the later beat's photo Details if filtering is
  wrong. All narration paths, staged cues and forced deliveries need checking.
* The new storylet must not force a new clue at its target/latest turn. Check
  pacing without an earning action. No new discovery fallback is supplied.
* Save compatibility follows the existing package integrity rules; do not
  promise old saves will migrate across this package change.
* Hiding/moving clues out of the bench avoids their old initial place-line
  corruption; it does not repair the bench's outside sight boundary, a later
  ordinary pickup, malformed `held_by` output, cap rollback, or the drain
  question. Those retain separate investigations.

Verified in this planning task: current authored text and references, existing
reveal prerequisite/reach/source checks, the exact six Route E inputs, recorded
opening exposure and premature cues, and the distinction between physical
discovery and later interpretation. Historical measurement claims above remain
attributed to their records. No claim of live-prefix parity, live success,
candidate package loading, matcher success, synthetic regression, new pytest
results, or staging verification is made. The proposed package has not been
constructed or applied. Only this plan is written.

Document check: `git diff --check` reported no tracked whitespace errors;
the final status lists only this new plan. No pytest suite was run for this
planning-only task.
