# Story data redesign — design reference

Moved verbatim from [the redesign plan](story-data-redesign-plan.md) on 2026-11-09 so
the plan stays short. This is background, not status: the plan owns decisions, order
of work and what is open. Read this when you need the reasoning behind a rule in the
plan: the model comparison framework, the full requirement 5 text and reading-view
requirement, the conditional (not selected) implementation sketch, or the test
design table. Section numbers are the old plan's.

## 2. Conceptual comparison — decision still open

Separate the semantic model (what constitutes a story), the authoring interface
(how someone changes it), and the physical representation (how it is stored and
queried). Choosing a graph does not imply running a server; choosing documents
does not require scattered files; choosing relations does not require authors
to edit tables. An immutable runtime projection can serve any of these models.

The following tradeoffs are project-specific design hypotheses, not measured
performance rankings or product recommendations.

| Conceptual model | Ease of changing this story | Repetition and test implications | Efficiency and main tradeoff |
| --- | --- | --- | --- |
| Knowledge graph: entities, claims, events, passages, and explicit typed relationships | A shared concept is edited once; dependencies and cross-scene consequences can be traversed. A scene is a view of connected records, so cohesive editing needs an aggregate view or operation. | Shared identities replace repeated definitions. Relationship constraints can replace hand-maintained cross-reference checks. Independent behavioral tests are still needed. | Natural candidate for dependency traversal and reverse impact queries. Scene assembly, edge metadata, and indexes have costs; a graph is not automatically faster for whole-scene reads. |
| Document/aggregate model: a scene contains its local narrative and mechanics | Strong locality for changes contained in a scene, and readable prose beside its rules. Shared entities and cross-scene concepts need references and explicit ownership. | Eliminates subsystem-file duplication locally; embedding shared concepts in multiple scenes would recreate update problems. Tests should address records rather than text layout. | Potentially simple whole-scene reads. Cross-scene dependencies require indexing or reference traversal; large aggregates can make small updates awkward. |
| Normalized relational model: typed records connected through keys and relation tables | Makes canonical ownership and integrity explicit. Scene editing needs an assembled view or transaction across records; raw tables would be a poor authoring experience. | Normalization addresses repeated definitions; referential constraints catch structural mistakes. Neither proves narrative intent nor removes copied test expectations automatically. | Suitable candidate for filtered sets and joins. Variable-depth dependencies and relationship-rich records may require more involved queries. Performance depends on access paths, not the label “relational.” |
| Declarative story language/compiler: explicit constructs for scenes, reveals, conditions, effects, and text | Can express a narrative change as one domain-level declaration, deriving companion representations. Must remain readable and avoid becoming a general programming language. | Removes repetition caused by separately authoring consequences that can be derived. Adds language/compiler tests but can reduce repetitive per-story structural checks. | Can compile to compact runtime indexes. Compiler maintenance, diagnostics, and rule semantics are additional complexity. A language can use graph, document, or relational semantics underneath. |
| Hybrid: one canonical semantic model with generated authoring/runtime views | Could combine coherent scene editing with shared graph identities and bounded runtime reads. | Works only if every editable value has one owner and view edits have an unambiguous write-back operation. | Additional projections may improve reads but add build/invalidation complexity. Multiple independently editable stores would recreate the original problem. |

### What a knowledge graph would mean here

Model a passage, a claim, the event that delivers it, and the fact it establishes
as distinct identified concepts, connected by typed relationships. This makes
questions such as “what can reveal this fact?”, “what depends on this reveal?”,
and “where is this passage used?” part of the model rather than scattered text
searches. This is a substantive advantage for the project's continuity problem,
not merely a possible performance optimization.

Relationship context must be explicit: prerequisites, audience, scene scope,
ordering, and provenance cannot disappear into generic edges. Conditional or
multi-part relationships may need their own event/claim records. RDF-style
statements and property-graph-style relationships are alternative graph shapes;
neither should be dismissed as inherently untyped. Schema constraints and
validation remain required whichever shape is selected. RDF's abstract graph
model is specified in [W3C RDF Concepts](https://www.w3.org/TR/rdf11-concepts/).

A graph alone also does not express the difference between an authored possible
reveal and a reveal actually earned in a session. Keep authored relationships
immutable and gate disclosure against committed session facts. Do not introduce
inference that grants player knowledge merely because it is reachable in the
authoring graph.

### Where other concepts may fit better

If most edits and reads are scene-local, aggregates may offer simpler authoring
than graph-first records. Embedding versus referencing is the key document-model
choice: references preserve shared identity when embedding would duplicate it.
See the primary documentation on [document relationships](https://www.mongodb.com/docs/manual/applications/data-models-relationships/).
This is a conceptual reference, not a recommendation to adopt that product.

If repetition comes mainly from separately spelling out facts, effects, claims,
and delivery wiring that follow fixed rules, a declarative language may remove
more maintenance than any storage change. Derivations must be explicit and
validated; do not infer canonical facts from prose. If stable structured records
and integrity dominate, a normalized relational model remains a serious option,
without presuming it wins because SQLite is already present in the stack.

An event log principally addresses change history and replay, not cohesive
current-story authoring; it could supplement any candidate. A containment tree
fits world placement but cannot alone represent the story's many-to-many claim
and dependency relationships. Embedding/vector retrieval does not provide exact
reference integrity and is not a substitute for canonical story structure.

### Decision exercise before implementation

Represent the same slice under graph, aggregate, and relational models; sketch
whether domain-language constructs remove additional repetition in each. Include
both a scene-local change and a shared concept used across several scenes so the
exercise does not favor scene documents by construction. Do not build three full
systems or compare libraries.

For each representation, walk through:

1. Revise one reused passage without altering its identity or disclosure scope.
2. Change a reveal prerequisite/effect and identify every affected consumer.
3. Move a reveal between scenes while preserving its cross-scene dependencies.
4. Assemble only the current audience's eligible scene material.
5. Reject dangling references, incompatible effects, and dependency cycles.
6. Update a behavior test without copying prose or deriving its expected result
   from the same production declaration it is checking.
7. Give an LLM the represented situation and relevant surrounding story; assess
   whether it identifies causal gaps and proposes understandable repairs without
   being handed the expected diagnosis or inventing canon.

Record authoritative values edited, manual synchronization steps, author-visible
complexity, independent assertions retained, and query/index operations required.
Discuss memory and load implications separately from authoring convenience.
Choose based on the user's five requirements, documenting the strongest rejected
alternative and the evidence that would reverse the decision. No candidate gets
an automatic advantage from matching the current implementation.

### Causal narrative review and assisted repair (requirement 5)

The model must support reasoning about why events follow from one another, not
only which records reference a fact. Evaluate explicit representations of:

- Situations and pressures, including demands or threats that call for a response.
- Character goals, motivations, knowledge, capabilities, and constraints, with
  source evidence and any uncertainty visible.
- Plausible response families and conditional consequences, including custody,
  information gained or lost, costs, escalation, and deliberate failure outcomes.
- Continuation requirements: what a character must know, want, possess, or be able
  to do for a subsequent scene to make sense.
- Unresolved causal links and author questions as explicit review records, rather
  than silently filling them with generated story facts.

These are authoring/review concepts. They must not introduce a second mutable
runtime truth, a fixed action menu, or an exhaustive list of allowed player
commands. Nor should every possible action need a separately authored branch.
Use general constraints and consequences where they suffice. A graph can expose
these relationships, but graph structure alone does not detect narrative gaps;
compare how each candidate supports this review and readable explanation.

**Required review case: Reyes demands the recovered memory card.** The author
has identified two questions that reference validation and existing passing tests
do not answer: what credible options does Kristin have under an armed officer's
demand, and what motivates/enables her to go to the park if she surrenders the
card? Review surrender, resistance/flight, and other plausible responses against
the actual authored situation. Being tased or shot is an author-raised plausible
risk, not an established outcome to insert automatically. Likewise, inspect what
Kristin has already learned before concluding that losing custody necessarily
removes the park lead. Distinguish possession, retained knowledge, motivation,
and physical ability to leave; a transition predicate alone proves none of these.

The reviewer should retrieve the relevant canon, alternative producers, and later
dependencies, then report each gap with:

1. The situation and source evidence, including what is absent or uncertain.
2. A plausible response and the missing or contradictory consequence.
3. The downstream scene, goal, knowledge, or possession requirement affected.
4. Alternative repair proposals, each explaining its narrative tradeoff and
   identifying the declarations and tests that would change.
5. A concrete proposed change for author review, clearly separate from canon.

An accepted repair updates the canonical authoring source and regenerates its
views. Re-run structural validation and relevant behavior checks, then review
the causal chain again. LLM suggestions do not become canon or runtime facts
without author acceptance. The representation migration itself preserves current
behavior; story repairs are separately reviewed changes, not hidden migration
side effects. Intentional ambiguity and intentional failure are valid author
decisions, not gaps that the tool must force onto a successful route.

**Reading-view requirement (author finding, 2026-11-09).** Requirement 5 applies to
the author's own view, not only to an LLM's. The first prototype was organized by
reveal, so following "what happens after this?" and "what does the next scene
need?" meant opening other records and guessing. A view that serves requirement 5
must let the author, without looking up IDs:

1. Start from a **situation** (e.g. Reyes's demand) and see its triggers, what
   produces each, and what it leads to. A situation whose outputs feed only
   wording, with no effect on custody, knowledge, or exits, shows as a dead end.
2. See the **continuation** the next scene requires, each requirement with its
   producers, and what the engine actually checks for it beside what the story
   text promises (e.g. text says "the card she is already carrying"; the engine
   checks a fact). Possession, knowledge, reach, and existence are shown as
   different things.
3. See the **plausible responses** with their effect today, simulated where the
   engine can and marked "no authored mechanics" where it cannot. Responses are
   tagged inference, not canon.
4. See **review records** (canon, inferred concern, author question, proposal)
   in a separate overlay whose evidence references are checked to exist and which
   is never compiled into runtime facts.

Computed flags in this view are structural. They point the author at a place to
look; they do not judge whether a response is plausible. The same view is the
evidence packet for the LLM reviewers, minus any diagnosis.

Acceptance for the pilot: demonstrate detection on the Reyes/card case and an
independent held-out case, with a well-grounded continuation as a control. Assess
supported findings, missed gaps, false alarms, clarity, and the author's ability
to choose a repair. Do not hardcode this example as a production rule or count
an expected diagnosis copied into the reviewer prompt as successful discovery.
LLM review is fallible assistance; deterministic checks establish structural
consistency, not narrative completeness.

### Conditional implementation sketch

The scene-document layout and compiler outline below describe one candidate,
not the selected architecture. If graph-first or relational semantics win, replace
this sketch before Phase 1. Preserve the safety and test-independence requirements
across all candidates; do not mandate a custom graph implementation.

### Authoring layout

Document-candidate layout, subject to the conceptual decision:

```text
story.yaml          # identity, schema version, scene order, shared declarations
scenes/1A.yaml      # this scene's prose and executable declarations together
scenes/1B.yaml
...
```

Use YAML block scalars for Markdown prose. Keep scene entry, beats, local
placements, storylets/realizations, claims, pacing, incidents, and outgoing
handoffs together in their owning scene. Shared entities and genuinely shared
facts belong in the root catalog. A record may reference another scene's stable
ID without duplicating its definition. Large shared catalogs may be split later
only when authoring experience warrants it.

- Stable IDs are independent of headings, names, passage wording, and file paths.
  Preserve existing IDs where possible; new IDs must not derive from prose slugs.
- Define a fact's identity, type, and purpose once. Predicates and effects refer
  to that identity; they do not redeclare its description.
- Define an executable effect bundle once on its owning event/realization.
  Claim authorization references that owner. Preserve explicit validation of
  which effects authorize each claim; do not equate all event effects with all
  claim knowledge.
- Store a passage beside its semantic owner. Reference it by ID only when the
  exact same passage is intentionally reused. Do not replace all prose with a
  disconnected global string catalog or merge passages just because their bytes
  happen to match.
- Safe framing, protected claims, delivery text, and dramatic guidance remain
  distinct fields with explicit audience/disclosure rules. Deduplication must
  never broaden narrator access to protected material.
- Generate the readable plot/story handbook and reference reports from these
  records. Generated views are disposable and never edited as a second source.
- Reject duplicate YAML keys, IDs, dangling references, invalid types, and
  ambiguous ownership. Diagnostics identify source file, record, and field.

### Compilation and runtime access

Compile authoring records into a normalized intermediate representation, validate
it, then construct the immutable runtime package. Initially adapt into the
existing `StoryPackage` contract to constrain migration scope.

Build only useful indexes: records by stable ID, records by scene, claims by
source/fact/audience, and forward/reverse dependency adjacency. Reuse existing
knowledge indexes where they already cover a need. Runtime selection should
start from the active scene and eligible scope, rather than scan the whole story.
An index improves lookup, but does not make graph traversal or eligibility
evaluation constant time; measure actual access patterns.

Keep source locations in a compiler side table for diagnostics. Produce a
deterministic artifact with schema/compiler version, source digest, and content
identity. Cache invalidation includes all compiler inputs. Verify artifact
integrity and compatibility at load; fail closed on mismatches.

The dependency graph supports impact reports: a changed passage points to its
consumers; a changed fact points to predicates, effects, claims, and test cases.
Use these reports to assist edits and focused checks, not as proof that unrelated
tests can safely be omitted from required verification.

Facts remain the sole mutable authority. Package graph edges describe authored
relationships; they are not another live world store. World-state-only traversal
and mutation remain `World` methods in `packages/worldkeeper`. The hosted adapter
stays thin; Python/FastAPI, React, and Cloudflare boundaries remain intact.

## 3. Test redesign

Separate engine mechanics, story semantics, passage transport, and editorial
wording. They need different sources of expected results.

| Test purpose | Fixture/input | Independent assertion |
| --- | --- | --- |
| Generic runtime or loader behavior | Small typed synthetic story builder | Explicit fact changes, errors, rollback, disclosure, ordering |
| Real story contract | Stable scene/event/claim IDs | Authored intent expressed as expected facts, access, prerequisites, and prohibited outcomes |
| Exact passage delivery | Resolve the canonical passage for test input/transport expectation | Correct event, recipient, turn, multiplicity, and eligibility; explicit expected identity |
| Editorial requirement | Narrow approved wording fixture or semantic rubric | Only intentional wording requirements, owned once |
| End-to-end journey | Shared scenario setup plus varied natural player actions | Independently specified outcomes, safety boundaries, and observable behavior |

Never generate expected effects from the same declarations being tested: a wrong
effect would then change both actual and expected values and pass. Canonical
passage lookup proves faithful transport, not literary correctness. Keep a small
independently maintained editorial contract where wording itself matters.

Build reusable typed fixtures and patch helpers that address records by ID and
field. Serialize through the authoring boundary when testing parsing/loading;
use direct typed builders for runtime mechanics. Keep intentionally malformed
raw-source fixtures for syntax/error tests. Remove prose `.replace(...)` setup
from ordinary behavior tests.

Share journey setup and stable case IDs across Python and browser harnesses via
a small language-neutral test-case manifest where useful. Keep this manifest
separate from production story authority. Retain paraphrases, negation cases,
ambiguous actions, and adversarial inputs; do not generate every player action
from the matcher aliases it is supposed to test. Follow the
[player-input guide](../docs/player-input-guide.md).

Do not rewrite historical captures to resemble new behavior. Classify active
regressions, frozen evidence, and obsolete experiment scaffolding using the
existing consolidation plan, including its regression/mutant safeguards.

