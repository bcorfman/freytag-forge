# Story authoring, test contracts, and compiled runtime data

Status: proposed, updated 2026-11-09. Initial concrete comparison, second (2C
incident) slice, Phase 0 baseline measurements, and the non-blind requirement 5
(Reyes/card) analysis completed; the blind LLM review, author review and
model decision are open. Implementation, test changes, and deployment have not started. This plan is separate
from ongoing story edits and does not supersede their active plans.

## Resume here

The [concrete comparison](story-data-comparison.md) traces quiet/witnessed memory-card
recovery through its 1B pursuit consequence, models four alternatives, and walks
through identical edits. The initial recommendation is **readable declarative
scene/reveal authoring with typed graph semantics and compiled runtime views**.
This is supported by the inspected slice, not yet validated for the whole story.

Phase 0 evidence is in [story-data-phase0.md](story-data-phase0.md): load, turn and
suite baselines, three measured edits, whole-story duplication counts, ownership map,
2C slice, and a generated reading view. Key result: load 0.36 s and per-turn
projection 3–6 ms, so speed is not the case for change; ownership and coupling are.

Requirement 5 adds a causal narrative review gate: use the Reyes/card demand to
demonstrate LLM-assisted discovery of missing responses and consequences, not just
reference tracing. The comparison now has a [Reyes/card section](story-data-comparison.md#6-requirement-5-slice-reyes-demands-the-recovered-card)
(2026-11-09): sourced canon, a read-only probe, five gaps, and what each model must
hold. It is **not** the blind discovery demonstration (the drafter has seen the
answer). Notable result: after the card is handed to Reyes, the card-reading claim
and the `t_1a_1b` dependency check are unchanged, because `required_dependencies`
means not destroyed/incapacitated, not held. Relation kinds (hold, know, reach,
exist) must be typed in any chosen model.

Decided 2026-11-09: pilot scene 1A (starts after the arrival-glance edits are
committed); budgets accepted as listed in the Phase 0 report; blind review by both a
fresh Claude subagent and ChatGPT Desktop on the same packets.

Reading view approved 2026-11-09 (Brandon, after the revisions made with the
drafter): the situation-centered trace is acceptable for the pilot. It is still a
generated view, not an authoring format.

Cases chosen 2026-11-09 (Brandon accepted the drafter's suggestions): Reyes/card
(known), held-out **1B.4 park ambush** (fallback 2A.4 if the author has no known gap
in 1B.4), control **`i_2a_real_leak`**. The held-out answer key must be written by
the author and kept out of the packets and out of the drafter's context. The trace
renderer is Reyes-specific (hardcoded trigger and simulation), so packets for the
other two cases need a generalized renderer first.

Build go-ahead (Brandon, 2026-11-09): "I like the gaps that it finds now. I'll amend
it later if I find more weaknesses. Proceed past this point to build the features
into the project." Drafter's reading: the Reyes gap findings are accepted as enough
evidence for requirement 5; the held-out/control blind run and the 1B.4 answer key
are **deferred, not cancelled** (they stay open as a later quality check), and
Phase 1 starts with the situation-trace view. Not yet decided by Brandon: the
storage model and the compiled authoring schema; the chosen direction stays the
initial recommendation (declarative scene/reveal authoring, typed graph semantics,
compiled runtime views).

Build slices (code via Ringer, Luna):
1. **Situation trace, general (built 2026-11-09, uncommitted).** Ringer reported FAIL
   only because the manifest's own scope filter misspelled an unrelated modified file
   (`1a-password-officer-plan.md`); the corrected check passes by hand: 14 tests,
   ruff, no story names in the module, Reyes sections 1-3 equal the prototype. Known
   thin spots: a transition anchor shows no situation prose; the "engine checks"
   table says nothing about custody beyond "does not check who holds anything". `storygame/story_package/situation_trace.py`,
   `scripts/situation_trace.py <anchor>`, tests. Anchors: pacing event, incident,
   transition. Data-driven sections 1-3 only; no responses or gaps (blind-safe).
   Manifest: `scripts/ringer/story-data/situation-trace-slice1-manifest.json`.
   Check proves sections 1-3 equal the prototype's output for the Reyes anchor.
2. Gap checks as a registry of named, tested checks (custody, co-location, no strand),
   parameterized by anchor; port the three Reyes gaps without hardcoded ids.
3. Review-record overlay (canon / inferred / question / proposal) with checked
   evidence references, never compiled into runtime facts.
4. Impact report (forward/reverse dependencies for a fact or passage).
Then Phase 1 schema and compiler contract.

Packet design (2026-11-09, proposed, awaiting Brandon's OK): the three cases are
anchored differently (Reyes = pacing event `officer_presses_1a`; 1B.4 = scene
beats, with `pursuit_1b`/`park_lockdown_1b` pressures and exit `t_1b_1c`;
`i_2a_real_leak` = an incident with two outcomes, recovery storylet and successor
`t_2a_2b`). So the generalized renderer takes an anchor (event, incident, or scene
exit) and emits only the data-driven sections: the situation and its prose, where it
leads, what the exit needs with producers, and the story-says versus engine-checks
table. A blind packet **omits** the plausible-responses table and the gaps section.
Responses are what the reviewer must propose, and a drafter-written list would make
the run non-blind (as Reyes section 4 already is). Code changes go through Ringer.
Blocked on Brandon: the 1B.4 answer key, written without sharing it with the
drafter (or "no known gap", which switches the held-out case to 2A.4).

Next: build neutral packets and run both reviewers; then replace the conditional sketch
with the chosen model. What to do about Reyes and a surrendered card is a separate
story repair and is not part of the migration. Measure physical storage
only after that. No graph library,
relational backend, or custom graph implementation is selected. See the comparison
for evidence, limitations, and revised rankings; the generic comparison below
remains the framework for the broader pilot.

## 1. Requirements and diagnosis

1. Make story changes local: an ordinary change should be expressible through
   one cohesive authoring operation, without manually synchronizing several
   representations. Do not assume that locality requires one file per scene.
2. Give every fact definition, authored passage, and executable effect one
   canonical owner. Remove copied passages and formatting-dependent mutations
   from tests without weakening independent behavioral expectations.
3. Make loading and runtime access efficient, with measured budgets for build
   time, cold/warm load, memory, artifact size, and per-turn queries.
4. Keep the story easy for an author to follow and edit. Preserve readable
   narrative order, colocate prose with behavior, and provide understandable
   forward/backward dependency navigation. Raw nodes, tables, or IDs are not
   sufficient authoring interfaces.
5. Make the representation support a competent LLM in finding and helping repair
   story gaps: missing causal links, credible responses, consequences, and reasons
   to continue. Present findings and proposed repairs in plain language with
   traceable evidence and downstream effects, so the author is not left to
   discover the gaps alone. Distinguish established canon from inference,
   unresolved questions, and proposed additions.

Evidence from the current repository:

- `data/stories/continuity-initiative/` has nine source files: plot, world,
  knowledge, pacing, storylets, routes, handoffs, incidents, and connections.
- `docs/markdown-story-authoring/package-and-story-structure.md` explicitly
  requires the knowledge fact catalog to match the world fact catalog. Storylet
  prose and executable realizations also live in different files.
- `storygame/story_package/models.py:StoryPackage` already provides a typed,
  immutable package and `knowledge_indexes`. The redesign should build on this
  boundary rather than replace the engine wholesale.
- `storygame/story_package/loader.py:load_story_package` already caches frozen
  packages by root and fingerprint. Repeated YAML parsing is not an established
  explanation for every slow test or turn; profile before optimizing it.
- `tests/test_1a_arrival_glance.py` contains full opening, glance, and delivery
  passages. `tests/test_delivery_variants.py`, `tests/test_trailing_pacing_events.py`,
  and `tests/test_world_placements.py` include source-string replacements.
  Such tests couple unrelated runtime checks to prose or serialization layout.
- The existing [test consolidation plan](test-suite-consolidation-plan.md) and
  [ledger](test-suite-consolidation-ledger.md) already track test overlap and
  regression protection. Coordinate with that work; repeated setup alone does
  not establish that a test is disposable.

These are inspected examples, not a complete duplication audit or a performance
measurement. The main design problem appears to be ownership and coupling;
changing the storage engine alone would leave that problem intact.

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

## 4. Delivery phases

### Phase 0 — Conceptual decision, baseline, and ownership map

- [x] Complete an initial conceptual exercise on a real reveal and cross-scene
  dependency; record alternatives, edit walkthroughs, tests, and limitations in
  [the comparison](story-data-comparison.md).
- [x] Extend to a later incident/cost/recovery slice (2C, in the Phase 0 evidence).
- [x] Validate a readable authoring prototype with the author. Author verdict,
  2026-11-09: the first generated view (organized by storylet) was **not
  acceptable**; neither the author nor the drafter could naturally trace story gaps
  in it. It lists what a reveal contains but not what follows from a situation or
  what the next scene needs. Replacement under way: a situation-centered trace
  (see "Reading-view requirement" in section 2). Re-review done 2026-11-09:
  Brandon accepts the revised situation trace. Still not an authoring format.
- [ ] Extend the conceptual comparison to requirement 5 using the Reyes/card
  situation: represent goals, response consequences, continuation requirements,
  and unknowns; demonstrate an evidence-linked LLM gap report and repair options.
  Done 2026-11-09: representation of the situation under all four models, canon
  evidence table, deterministic probe, non-blind gap list. Open: blind LLM review
  of the Reyes case, a held-out case and a control (cases not chosen), and the
  author's assessment.
- [ ] Replace the conditional implementation sketch with the selected model;
  choose storage and implementation mechanisms only afterward.
- [x] Record baseline commit and working-tree state; isolate this work from
  ongoing story changes before conversion (detached worktree at `2bb01bbc`).
- [x] Choose one representative scene after concurrent edits settle. Include
  claims, delivery variants, pacing, and a cross-scene dependency in the pilot.
  Decided 2026-11-09 (Brandon): **1A**. Conversion starts after the seven
  uncommitted arrival-glance edits are committed.
- [x] Agree performance budgets. Decided 2026-11-09 (Brandon): cold load ≤ 0.5 s,
  cached load ≤ 2 ms, per-turn knowledge projection ≤ 10 ms, package memory
  ≤ 5 MiB, nothing slower than today. They guard against regression; they are
  not targets.
- [x] Choose held-out and control cases (2026-11-09: 1B.4 held-out, `i_2a_real_leak`
  control; answer key for 1B.4 pending from the author).
- [ ] Choose reviewers for the requirement 5 blind run. Decided 2026-11-09
  (Brandon): run both a fresh-context Claude subagent and ChatGPT Desktop on the
  same neutral packets, then compare. Packets are not built yet; the held-out and
  control cases are not chosen.
- [x] Map each concept to all authored definitions, generated views, tests,
  probes, Ringer manifests, and browser consumers. Distinguish deliberate
  repetition from competing definitions.
- [x] Measure three representative edits: prose-only, reveal/effect, and
  cross-scene dependency (rename proxy). Files touched, copies, and failing tests
  recorded; elapsed authoring time not measured (needs the author).
- [x] Profile cold/warm package loading, relevant query/turn preparation,
  package memory, and representative tests. Record environment, repeated-run
  variance, and coverage mode; separate model/network latency.

Exit: a justified conceptual-model decision, ownership table, baseline evidence,
agreed performance budgets, an author-reviewed reading/editing prototype, and
evidence that the representation supports causal gap discovery and repair review.
Do not invent a speedup percentage before these measurements.

### Phase 1 — Schema and compiler contract

- [ ] Specify typed records, stable IDs, reference resolution, source maps,
  disclosure boundaries, and versioning. Document migration mappings.
- [ ] Specify causal-review records and provenance for canon, inferred concerns,
  open questions, and repair proposals. Define how accepted proposals update the
  sole authoring source without leaking review material into narrator inputs.
- [ ] Implement minimal cross-genre fixtures and schema/validator tests first.
- [ ] Implement the normalized representation and adapter to `StoryPackage`.
- [ ] Add deterministic build and duplicate/dangling-reference rejection.
- [ ] Produce a readable generated story view and dependency/impact report,
  including the situation trace, continuation requirements with promise-versus-check
  display, and review overlay described under "Reading-view requirement".

Exit: a small authored story compiles with current safety boundaries intact.

### Phase 2 — One-scene migration and test pilot

- [ ] Convert the selected scene mechanically; produce an old-to-new semantic
  diff of IDs, predicates, effects, passages, placements, and disclosure scopes.
- [ ] Keep legacy and new loading as explicit package modes during migration;
  no silent precedence between competing definitions. A temporary hybrid pilot
  needs an explicit ownership manifest rejecting duplicate owners.
- [ ] Replace copied setup/prose in the pilot tests using the test design above.
- [ ] Compare package semantics and deterministic runtime traces against the
  baseline; allow only reviewed representation differences.
- [ ] Repeat the representative edits and measurements from Phase 0.
- [ ] Evaluate causal review on the required example, a held-out gap, and an
  adequate-continuation control; have the author assess explanation and repair
  quality. Keep any accepted narrative repair separate from migration parity.

Exit: ordinary pilot prose changes require one canonical passage edit and no
unrelated mechanics-test changes; deliberate editorial checks remain explicit.
No safety regression and no unexplained performance regression within the
agreed measurement tolerance. Revise the schema if local editing still fans out.

### Phase 3 — Full story and consumer migration

- [ ] Convert remaining scenes and shared definitions incrementally, preserving
  references and current behavior. Include another genre as a portability gate.
- [ ] Migrate active tests, E2E setup, probes, and Ringer manifests to stable
  record operations and shared fixture contracts.
- [ ] Retire redundant legacy authoring sources after parity; retain exports
  only as generated views. Remove obsolete dual-loader paths at cutover.
- [ ] Update authoring documentation and PRD to the adopted format.
- [ ] Decide save compatibility explicitly: preserve identity only if semantic
  equivalence is established; otherwise version/reject or provide a tested
  migration. Never silently reinterpret a saved session.

### Phase 4 — Measured optimization and release

- [ ] Profile the migrated implementation; add indexes only for demonstrated
  expensive access patterns.
- [ ] Evaluate physical representations appropriate to the selected conceptual
  model if evidence identifies a storage/load bottleneck. Do not privilege a
  relational artifact or custom indexes by default. Record the evidence.
- [ ] Run required verification from the [testing runbook](../docs/testing-runbook.md),
  including targeted regression coverage, cross-genre safety, persistence,
  full-suite checks, Ruff, and the project coverage requirements.
- [ ] Follow the [promotion guide](../docs/railway-production-promotion.md) for
  staging and SHA-bound hosted/E2E verification before production promotion.
- [ ] Record evidence, commit, remaining risks, and resume instructions in this
  plan after each completed phase. Update existing runbook entries if commands
  or verification boundaries change.

## 5. Acceptance and scope limits

Success means fewer independently maintained definitions and fewer files changed
per ordinary story edit, with measured runtime efficiency and unchanged safety.
There must be one authored definition per fact and reusable passage, stable IDs
through prose renames, deterministic compilation, actionable reference errors,
and independently meaningful regression assertions.
The author must also be able to follow and edit the narrative, understand an
LLM's evidence-linked gap findings, and assess proposed repairs and their later
consequences. The author must be able to trace a gap such as the Reyes demand
through the generated view unaided, which the first prototype did not allow. Passing schema and runtime tests alone does not satisfy this gate.

Do not remove tests merely to reduce counts, select libraries before the
conceptual decision, add a visual editor in this migration, or change narrative
behavior while proving representation parity. Any future editor must edit the
chosen canonical model rather than establish a competing authority.

Planning verification: inspected repository documentation, package models and
loader, representative story sources and tests, and existing consolidation plans.
The initial concrete comparison ran 75 existing focused tests, all passing in
8.16s; details and snapshot identity are in the linked report. No implementation
or alternative-model benchmark ran. Performance benefits remain hypotheses until
the phase gates above are measured.
