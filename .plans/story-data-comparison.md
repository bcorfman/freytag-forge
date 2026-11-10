# Story data comparison using the witnessed memory-card recovery

Status: initial comparison completed, 2026-11-09. Design sketches, source tracing,
and focused existing tests; no implementation or storage benchmark. Companion to
[the redesign plan](story-data-redesign-plan.md).

## Conclusion

Recommend **readable declarative scene/reveal documents with a typed story graph
as their semantic model, compiled into immutable runtime projections**. The
canonical declarations own the data; graph indexes and reading views are derived.
This does not require writing a graph library or selecting a database now.

The fourth requirement—an author must easily follow and edit the story—changes
how this recommendation should be presented and evaluated. A raw graph is not
an adequate authoring interface. The author should read scenes in narrative order
and edit a reveal's prose, conditions, and consequences together. Graph traversal
should explain references and consequences rather than become the author's job.

This slice supports that direction on maintenance grounds. It does not establish
a runtime performance winner or prove that the format is comfortable for the
author. A readable prototype and the author's editing experience are still gates.

## Evidence and boundaries

Inspected working tree at HEAD `2bb01bbcdb8343f48b371cd64c24abfe25a403d5`.
Existing uncommitted edits included knowledge/pacing, arrival-glance tests, and
Ringer manifests. They were not changed by this exercise. Findings describe the
working tree, not an assumed clean release.

SHA-256 prefixes of the inspected source files, for identifying this snapshot:

| File in `data/stories/continuity-initiative/` | Hash prefix |
| --- | --- |
| plot.md | b387c09ba4864849 |
| world.yaml | f628aca7db86f087 |
| knowledge.yaml | f62d1684f1e52d43 |
| storylet-routes.yaml | 65315c3c7fb40603 |
| storylets.md | f65405cdb595da27 |
| pacing.yaml | c029d82840f047b6 |
| handoffs.yaml | 2d919d177c6fd25d |

The slice is `SL-1A-E`, its quiet/witnessed card-recovery claims
`k_sl_1a_b_r0` and `k_sl_1a_b_r0w`, and the latter's effect on `pursuit_1b`.
This includes a physical item, protected vocabulary, two alternative reveals,
world effects, pacing, an outgoing transition, and a later scene consequence.
It is a meaningful example, not an inventory of every story mechanism.

## 1. Trace of the actual story

| Responsibility | Current source | Why it matters |
| --- | --- | --- |
| Card begins under the drawer; drawer belongs to the workstation | [plot.md](../data/stories/continuity-initiative/plot.md), scene 1A metadata and hidden canon | Physical reach and narrative explanation must agree |
| Recovery moves/reveals the card | [world.yaml](../data/stories/continuity-initiative/world.yaml), `memory_card_recovered.on_assert` | An asserted fact changes custody through world effects |
| Word guard unlocks after recovery | Same file, `memory_card_word_guard` | A reference to an entity must not grant unearned disclosure |
| Fact purpose | [knowledge.yaml](../data/stories/continuity-initiative/knowledge.yaml), facts catalog | Human meaning of the fact |
| Fact definition and usage lists | [storylet-routes.yaml](../data/stories/continuity-initiative/storylet-routes.yaml), `new_fact_ids` | Another description plus manually recorded consumers |
| Dramatic purpose, alternatives, effects, completion, window | [storylets.md](../data/stories/continuity-initiative/storylets.md), `SL-1A-E` | Readable guidance separately describing executable declarations |
| Activation and executable operations | `storylet-routes.yaml`, `SL-1A-E`, R1/R2 | Requires card not yet recovered; each realization owns an operation list |
| Earning, scope, audience, prerequisites, effects, delivery | `knowledge.yaml`, quiet and witnessed claims | Quiet requires patrol absent; witnessed requires patrol present |
| Officer pressure | [pacing.yaml](../data/stories/continuity-initiative/pacing.yaml), officer demand and departure | `card_challenged` influences subsequent pressure |
| Later consequence | Same file, `pursuit_1b` | At turn 4 in 1B, `kristin_marked_by_patrol` selects the description-aware pursuit passage |
| Leaving 1A | Same file, `t_1a_1b` | Requires recovered card, actionable lead, and patrol pressure; also requires the card entity |
| Alternate fallback producer | [handoffs.yaml](../data/stories/continuity-initiative/handoffs.yaml), `continuity_initiative_known.costs` | Can also assert card recovery; recovery does not have just one producer |

The dependency chain is concrete:

```text
patrol present + reachable drawer + active SL-1A-E + card not already recovered
  -> witnessed claim k_sl_1a_b_r0w / realization SL-1A-E-R2
     -> memory_card_recovered -> world custody/reveal + word guard + exit dependency
     -> card_challenged -> officer demand / departure behavior
     -> kristin_marked_by_patrol -> scene 1B pursuit passage selection
```

This is an authoring dependency diagram, not permission for graph reachability to
establish runtime facts. Eligibility and atomic fact commits remain authoritative.

### What is repetition, and what must remain distinct

The quiet and witnessed claims have **nine equal fields** in the inspected YAML:
`reach_entity_ids`, `earn_when`, `action_evidence`, `entity_ids`, `audience`,
`available_in_scenes`, `relevance`, `leak_terms`, and `must_convey`.
Their common search/reach/disclosure specification can have one explicit owner.
Their differing prerequisites, statements, delivery endings, and effects are real
branches and must stay visible to the author. Quiet recovery also explicitly has
`voiceable: false`; do not flatten away that difference.

The witnessed operation list appears in both the route realization and the claim:
assert recovery, challenge, and patrol mark. The loader checks claim effects are
a **subset** of source operations, not necessarily the whole list
(`storygame/story_package/loader.py:_validate_knowledge`). Therefore a replacement
must preserve claim-to-effect membership, not blindly assign every source effect
to every claim. In this slice they match, but that is not a universal schema rule.

References to the same fact in an exit condition, guard, and later pacing event
are legitimate relationships, not duplicate definitions. They should be traceable
and indexed, not erased. Fact purpose and author-facing summaries can be generated
from canonical declarations where they convey the same meaning. Literary prose
and a guard vocabulary list serve different purposes and cannot all be derived
safely from one string.

### Tests and consumers

[tests/test_1a_witnessed_recovery.py](../tests/test_1a_witnessed_recovery.py)
independently checks the three witnessed facts, possession, no witnessed effects
on quiet recovery, no retroactive witnessing, physical reach, prompt continuity,
1B pursuit variants, and snapshot restoration. These are distinct protections.
It also copies the witnessed statement and both pursuit passages into constants.

[tests/test_1a_officer_press.py](../tests/test_1a_officer_press.py) copies demand
and departure passages. [tests/test_drawer_gap_nudge.py](../tests/test_drawer_gap_nudge.py)
checks the shared action-language boundary. A simple literal scan of top-level
`tests/test_*.py` found the witnessed claim ID in 8 files, recovery fact ID in 41,
and patrol-mark fact ID in 3. These are scope signals, not redundant-test counts.

Existing Ringer builders also embed historical meanings of the same IDs. For
example, `scripts/ringer/1a-password-officer/build_drawer_close_manifests.py`
describes `k_sl_1a_b_r0w` as an opening response; the current witnessed-recovery
test and data use it for card recovery. Treat experiment instructions as
version-bound history, not an additional live story definition. Stable IDs need
a policy against repurposing unrelated concepts.

The focused cross-scene test injects the patrol-mark fact into a 1B state; it
checks the consumer, not a complete 1A-to-1B journey. No browser journey parity or
live narrator quality was established in this exercise.

## 2. Same slice represented four ways

These are partial schema sketches, not loadable package replacements. Existing
IDs are retained; angle-bracket text denotes references to existing authored
content rather than newly written story passages.

### A. Typed knowledge graph

```text
Scene(1A) --offers--> Storylet(SL-1A-E)
Storylet --requires--> Predicate(memory_card_recovered = false)
Storylet --has_variant--> Realization(SL-1A-E-R2)
Claim(k_sl_1a_b_r0w) --authorized_by--> Realization(SL-1A-E-R2)
Claim --requires--> Predicate(patrol_in_house = true)
Claim --uses_action--> ActionPattern(drawer_under_search)
Claim --requires_reach--> Entity(michelle_drawer)
Claim --delivers--> Passage(witnessed_card_delivery)
Realization --has_effect--> Effect(recover_card: assert memory_card_recovered=true)
Realization --has_effect--> Effect(challenge: assert card_challenged=true)
Realization --has_effect--> Effect(mark: assert kristin_marked_by_patrol=true)
Claim --establishes--> [recover_card, challenge, mark]
Fact(memory_card_recovered) --on_assert--> <existing world operations>
PacingVariant(pursuit_marked) --requires--> Predicate(kristin_marked_by_patrol=true)
PacingEvent(pursuit_1b) --has_ordered_variant--> PacingVariant(pursuit_marked)
PacingVariant --delivers--> Passage(marked_pursuit)
```

Effect identity and shared action-pattern identity remove copied values. Merely
converting every existing field into an edge would preserve the duplication.
Reverse edges identify downstream consumers and other producers. Explicit
predicate values, effect membership, audience, and variant order are essential.
A raw node/edge representation scatters an author's reveal across many records;
it needs a cohesive editable view to satisfy the fourth requirement.

### B. Scene-centered aggregate documents

```yaml
scene: 1A
reveals:
  - storylet: SL-1A-E
    requires: {memory_card_recovered: false}
    search: <one shared drawer-under action/reach specification>
    variants:
      - claim: k_sl_1a_b_r0
        realization: SL-1A-E-R1
        requires: {patrol_in_house: false}
        effects: [recover_card]
        delivery: <quiet passage>
      - claim: k_sl_1a_b_r0w
        realization: SL-1A-E-R2
        requires: {patrol_in_house: true}
        effects: [recover_card, challenge, mark]
        delivery: <witnessed passage>
```

Shared fact/effect definitions are referenced, not copied into both scenes.
Scene 1B owns its pursuit event and references the patrol-mark fact. This is easy
to read locally; tracing the later consequence still needs a reverse-reference
view. Without that view, it repeats part of today's navigation problem.

### C. Normalized relational representation

```text
Fact(id, purpose)                     WorldEffect(fact_id, ordinal, operation)
Storylet(id, scene_id, ...)           Realization(id, storylet_id, ...)
Effect(id, op, fact_id, value)         RealizationEffect(realization_id, effect_id)
Claim(id, realization_id, ...)        ClaimEffect(claim_id, effect_id)
ActionPattern(id, ...)               ClaimAction(claim_id, action_pattern_id)
ClaimPredicate(claim_id, fact_id, comparison, value)
Passage(id, text, disclosure_scope)   ClaimDelivery(claim_id, passage_id)
PacingVariant(id, event_id, ordinal, passage_id)
PacingPredicate(variant_id, fact_id, comparison, value)
```

This represents the same identities and relationships as A. Keys prevent missing
references, but source-effect authorization, ordering, and narrative eligibility
still require domain validation. An assembled scene/reveal view could provide
identical authoring locality. Raw tables are no more author-friendly than raw
edges. No evidence from this slice proves a relational backend inferior.

### D. Declarative reveal aggregate with graph semantics

The author edits one reveal block with common behavior and explicit variants.
The following is illustrative, not a proposed final surface syntax:

```text
Scene 1A / The KMS Mark [SL-1A-E]
  Available: card not recovered
  Window: earliest 1, target 3, latest 12
  Search: <existing earning description and exact evidence groups>
  Reach: michelle_drawer
  Shared disclosure: <existing audience, leak terms, must-convey groups>

  Quiet [k_sl_1a_b_r0 / SL-1A-E-R1]
    When: patrol absent
    Commit: recover_card
    Voiceable: false
    Statement and delivery: <existing quiet text, edited here>

  Witnessed [k_sl_1a_b_r0w / SL-1A-E-R2]
    When: patrol present
    Commit: recover_card, challenge, mark
    Statement and delivery: <existing witnessed text, edited here>

  Completion: card recovered
  Abort: scene exited
```

The compiler generates route/claim wiring, indexes, usage lists, and reference
views from this one declaration. It retains separate claim membership when a
source has more effects than a claim establishes. Fact declarations own purposes
and world effects once; 1B's author-written pursuit branch references the mark.

This combines A's relationship model with B's editing locality. It should be a
small declarative schema, not a general programming language. Its advantage over
B alone is explicit compilation of repeated runtime views and dependency tooling;
its disadvantage is maintaining that compiler and useful diagnostics.

## 3. Identical edits walked through

These are logical edit counts from the sketches, not measured author timings.
A single “edit” can still involve several lines or UI interactions.

| Change | Current source obligations | Graph | Aggregates | Relations | Declarative + graph |
| --- | --- | --- | --- | --- | --- |
| Reword marked pursuit without changing meaning | One pacing passage plus copied expected passage in witnessed test | One passage; inspect dependent consumer | One passage in 1B | One passage row | One passage inside 1B pacing block |
| Change shared drawer-search evidence | Two knowledge claim fields | One shared action-pattern record | One common field in reveal aggregate | One action-pattern record | One shared Search declaration |
| Change witnessed marking behavior | Route operations and claim effects; inspect storylet prose, fact catalogs, 1B consumer, independent tests | One claim/source effect-membership operation if exposed as an aggregate command; otherwise multiple edges | One variant declaration with generated companion views; plain regrouping alone still duplicates effects | Membership rows in one transaction; assembled authoring operation required | One variant Commit declaration; projections regenerated, consequences reported |
| Move card recovery from 1A to 1B | Scene scope, source beat, placement/reach, timing, prose, exit prerequisites, fallback producers, tests | Rebind source scope, then traverse prerequisites/producers/consumers | Move block, then inspect cross-document references | Update scope/membership, query related dependencies | Move declaration, report unresolved narrative dependencies before build succeeds |

For all four redesigned models, transport tests can resolve canonical text by
identity. None earns that saving from storage choice alone. Independent tests
must still specify that witnessed recovery marks Kristin and quiet recovery does
not. A deliberate change to that behavior warrants changing those assertions.

Moving this reveal is **not** safely reducible to changing one scene ID. The
1A exit requires recovery; the alternate handoff can produce recovery in 1A too.
A correct impact report must show both, not simply declare a cycle or silently
relax the exit. It should ask the author to resolve whether recovery still occurs
via fallback, whether the exit changes, and how physical reach works in the new
scene. That is genuine story design work, not avoidable synchronization.

Removing the mark effect also does not create a dangling reference if the fact
still exists. It may instead leave the marked pursuit with no producer. Every
model needs producer/reachability analysis beyond basic reference integrity.

## 4. Runtime access and test implications

`loader._compile_knowledge_indexes` already produces ID, scene, fact-to-claim,
source-to-claim, prerequisite-dependent, and vocabulary indexes.
`KnowledgeProjector._candidates` starts with the active scene's indexed claim
IDs, checks eligibility, then sorts candidates. It does not find every candidate
by scanning the Markdown sources on each turn.

`reveal_eligibility.explain_reveal` checks established effects, visibility, spent
storylets, prerequisite predicates, reach, and source activation. These operations
need exact fact values and World behavior, not unconstrained graph inference.
`KnowledgeProjector._established` checks each claim effect against fact matches;
this is a potential profiling target, not an established bottleneck here.

All four concepts can compile to the existing lookup structures. A graph is
particularly useful for author-facing reverse impact paths, but a relational
representation can answer the same questions, and document compilation can build
the same adjacency indexes. Therefore **do not rank their runtime speed from this
exercise**. No alternative backend, cold-load, memory, or per-turn benchmark ran.

Recommended test changes for this exact slice, not implemented:

- Keep explicit expected claim IDs, fact outcomes, custody, reach, no-retroactive
  witnessing, and snapshot assertions.
- Give pacing variants stable identities. Check marked/unmarked variant selection
  independently, then compare emitted text to that variant's canonical passage.
- Resolve the witnessed statement by claim identity when testing its transport
  into the next prompt. Keep an independent disclosure/meaning check where needed.
- Keep narrow editorial assertions only where precise wording is intentional;
  do not reconstruct the entire passage in each behavioral test.
- Share scenario setup, while retaining separate action paraphrases and negative
  eligibility conditions. Do not generate test commands from the exact matcher
  vocabulary being tested.
- Test compiler consistency generically with synthetic stories and malformed
  source. Do not replace all independent story expectations with generated ones.

## 5. Author experience and revised ranking

1. **Declarative scene/reveal authoring over a typed graph semantic model.** Best
   combined fit in this slice: narrative locality, shared definitions, generated
   repeated wiring, and explicit cross-scene traceability.
2. **Graph-first canonical records with an editable scene/reveal view.** Strong
   on dependencies; viable if the authoring view is part of the initial delivery.
   Raw graph editing does not satisfy requirement 4. Prefer this if authors
   organize work around shared concepts more often than narrative scenes.
3. **Scene aggregates plus shared references and generated dependency reports.**
   Lower conceptual overhead; close to #1 if compiler derivations remain small.
   Prefer this if a wider audit shows almost all edits stay inside scenes.
4. **Raw normalized relational authoring.** Poor direct reading experience here.
   With the same declarative authoring layer, relations become an implementation
   alternative to #1, not an inferior story design. Leave that choice open.

The important choice is authoring semantics and ownership, not whether a graph
engine or relational engine holds the result. The earlier ranking compared a
language, logical models, and storage too loosely; this ranking separates them.

Author acceptance for the prototype:

- Read scenes in order with prose, optional reveals, and branches intelligible
  without opening implementation schemas or resolving IDs manually.
- Edit the witnessed branch beside its common action and quiet alternative;
  see which fields are shared and which override them.
- Follow a named consequence to 1B, and follow it back to its producers, with
  human-readable explanations and links to editable declarations.
- Preview exactly what the player can know and what stays hidden at each step.
- Identify the sole editable source from every generated reading/impact view.
- Perform the four edits above; record time, navigation, and confusion with the
  author. A graph-shaped model must not be accepted at the expense of readability.

Remaining decision gates: model a later incident with costs/recovery and shared
claims; produce a readable authoring prototype; validate author usability; profile
current access patterns before a runtime storage choice. This exercise justifies
an initial direction and pilot, not a completed migration or performance claim.

## 6. Requirement 5 slice: Reyes demands the recovered card

Added 2026-11-09. This section models the situation under the four candidates
and records what the repository can establish deterministically. **It is not yet
the required LLM discovery demonstration.** I (the drafter) read this canon while
preparing it, so my gap list below is an author-informed reading, not a blind
finding. A blind run (Reyes case, held-out case, control) is still open.

### What canon establishes, with sources

| Item | Evidence | Status |
| --- | --- | --- |
| Reyes demands the card at 1A turn 7 when `card_challenged` and `patrol_in_house`; he blocks the door, hand out | `pacing.yaml`, `officer_presses_1a`; `plot.md` 1A.4 | Canon |
| Reyes is "young, polite", works from a printed list, "does not like what the list asks of him" | `plot.md` Officer Reyes; `world.yaml` `patrol_officer.narrator_bio` | Canon |
| Nothing in the story says Reyes is armed, or that he tases or shoots anyone, in 1A | Grep for armed/weapon/holster/taser/gun in plot, storylets, knowledge, pacing, world: only later-scene "armed response teams" | **Absent; the armed-officer premise is the author's, not canon** |
| The patrol leaves at turn 10 whether or not the demand was met; the demand variant adds only "radio crackles with a description that is hers... eyes on her the whole way" | `pacing.yaml`, `patrol_leaves_1a` | Canon |
| Plot says only that after a witnessed take, "the patrol's suspicion follows her out of the house" | `plot.md` 1A.4 | Canon; silent on the card's fate |
| The park lead is carried by the card's files ("dead drop at a bench in the park"); reading them asserts `michelle_lead_actionable` | `knowledge.yaml` `k_sl_1a_b_r1`; `storylet-routes.yaml` `SL-1A-B-R1`, `SL-1A-D-R1` | Canon |
| Both lead producers are card-reading acts; SL-1A-D speaks of "the memory card she is already carrying". No other 1A producer of the lead | `storylet-routes.yaml` coverage matrix and SL-1A-B/D | Canon, as searched |
| Exit `t_1a_1b` triggers on `michelle_lead_actionable`, `patrol_return_pressure`, `memory_card_recovered`, and lists `memory_card` as a required dependency | `pacing.yaml` | Canon |
| The 1B bench claims have `requires: []`; only reach to the bench is needed | `knowledge.yaml` `k_sl_1b_d_r1` | Canon |
| An earlier author decision left the response open: "card custody is untouched, so deflect, hand over or run stay the player's free-text choice"; not verified live; a three-way typed incident was proposed but its engine support was an open question | `1a-transcript-continuity-plan.md` (officer-demand entry); `1a-transcript-continuity/story-material.md` §5 | Canon decision plus recorded open question |

### Deterministic probe (read-only, no model calls)

[surrender_probe.py](story-data-phase0/surrender_probe.py) builds a witnessed
state, then moves `memory_card` to `patrol_officer`:

| State | Card parent | Read-card claim `k_sl_1a_b_r1` | `t_1a_1b` dependency check |
| --- | --- | --- | --- |
| Card kept | `kristin` | eligible | satisfied |
| Handed to Reyes | `patrol_officer` | **still eligible** | **still satisfied** |

`explain_reveal` checks facts, visibility, reach and source activity; `r1` has no
reach entity. `required_dependencies` is evaluated through
`unavailable_entity_ids`, i.e. destroyed, incapacitated, or an axis pole, not
custody (`storygame/runtime/validation.py`). So surrender changes where the card
is but gates neither reading nor leaving. The earlier note that surrender
"routes to the goal-break prompt because `t_1a_1b` requires the card" does not
match this runtime check. Limits: eligibility only. The narrator-proposal flow,
item-fact tracking of dependency names, and live behavior were not run.

### Gaps as a reviewer should report them (non-blind, proposals not canon)

1. **The demand has no authored consequence.** Evidence above: the demand sets one
   fact, `officer_demanded_card`, consumed only by departure wording. Plausible
   responses: hand it over, stall or lie, refuse and leave, run, physical
   resistance. None has a defined effect on custody, knowledge, or the patrol.
2. **Surrender and the lead are not tied.** If Kristin has already read the files,
   the lead is knowledge (`michelle_lead_actionable` persists) and surrender
   plausibly costs only the physical card. If she surrenders first, both producers
   are unreachable by canon, yet the engine would still let her "read" a card she
   no longer holds (probe). Which case holds depends on player order, which the
   story neither guarantees nor handles.
3. **Possession, knowledge, motivation and ability to leave are conflated.**
   The exit expresses existence of the card, not holding it; no record says what
   she must know or want to go to the park, or that Reyes would let her leave.
4. **Escalation is an author-raised risk with no canon support.** Reyes's
   characterization argues against it; the story never arms him. Whether
   violence is a possible response is an author decision, not a gap to fill.
5. **The departure line cannot tell outcomes apart.** The same acknowledgement
   plays after surrender, refusal, or flight.

Candidate repair families (each needs author choice; none inserted): (a) keep
custody open and make the engine require holding the card to read or leave, which
tests the free-text design; (b) a typed hand-over/deflect/walk-out response
incident as proposed in `story-material.md` §5; (c) let the lead survive loss by
authoring a retained-memory or copy beat; (d) deliberately accept the ambiguity
and record it as intentional. Each lists the declarations and tests it touches
only after the author picks a direction.

### What each model must hold to support this review

The review needs typed notions of **Situation/pressure**, **Goal and knowledge**,
**Response family and consequence**, **Continuation requirement**, and **Review
record** (canon-tagged, inferred concern, open question, proposal). Possession,
knowledge, reach and existence must be distinct relations; gap 3 is exactly
the case where one name (`required_dependencies`) hid which relation was meant.

| Model | Strength for this review | Weakness |
| --- | --- | --- |
| Typed graph | `holds`, `knows`, `can_reach`, `exists` as separate edge types make gap 3 a checkable shape; a lead's producers and consumers are one traversal | Absence is not an edge: finding "situation with no response" needs declared expected shapes or queries; an LLM still judges plausibility |
| Scene aggregates | The demand, its departure variants and the exit sit in one block a reviewer reads in order | Cross-scene needs (1B's use of the lead) need generated reverse views; response families would be free text unless typed |
| Normalized relations | Anti-join queries find situations without responses and continuations without a producer directly | Raw tables are poor for the LLM's narrative context unless assembled into a readable packet |
| Declarative reveal + graph | Author states the pressure, its responses and what a continuation requires; the compiler emits a review packet with provenance; relation kinds are explicit in the language | Compiler and diagnostics cost; the language must not grow into general code |

Result for the ranking: requirement 5 does not overturn the earlier order, but it
adds a concrete requirement for any winner: **relation kinds must be typed**
(hold, know, reach, exist) and review records must live in an overlay that is
never compiled into runtime facts. Deterministic checks can then flag: situations
with no declared response, transitions whose required entity is non-custodial,
consumers whose only producer needs an item that a declared response can remove.
They cannot judge whether a response is plausible; that stays LLM-assisted and
author-decided. Deterministic checks are not narrative completeness.

### Remaining work for the requirement 5 demonstration

- Blind packets, one per case, built from retrieval only (the canon rows above, no
  diagnosis, no hint of the author's two questions): Reyes/card; a **held-out**
  case with a known or suspected gap; a **control** with a well-grounded
  continuation. The held-out and control cases are not chosen yet; I have not
  scanned the story for them and will not name candidates unverified.
- Reviewer output format: situation and evidence; plausible response; missing or
  contradictory consequence; downstream effect; repair options with tradeoffs and
  touched declarations/tests; one concrete proposal; canon vs inference vs
  question tags.
- Score supported findings, misses, false alarms, clarity, and whether the author
  can choose a repair. Brandon assesses; the drafter does not self-grade.

## Verification performed

Following the existing local focused-check procedure:

```bash
TMPDIR=/tmp uv run pytest -q --no-cov tests/test_1a_witnessed_recovery.py tests/test_1a_officer_press.py tests/test_drawer_gap_nudge.py
```

Result: **75 passed in 8.16s** on the inspected working tree. This verifies existing
slice behavior; the four design sketches have not been implemented or executed.
No live model calls, deployment, browser suite, full suite, or performance benchmark.
No test counts are proposed as gates. No existing story/test files were edited.

Section 6 added one read-only probe, `story-data-phase0/surrender_probe.py`, run
with `PYTHONPATH=.:packages/worldkeeper/src .venv/bin/python`. It showed the
read-card claim and the `t_1a_1b` dependency check unchanged after the card moved
to `patrol_officer`. No blind LLM review, live narration, or test run was done
for Section 6.
