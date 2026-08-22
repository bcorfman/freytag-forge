# Genre-blueprint authoring baseline

Phases 0–5 establish the authoring boundary and its first fact-backed V2
runtime realization. Blueprints remain immutable and do not replace canonical
runtime facts.

## Phase-1 generic contract

`storygame.authoring.blueprint_contracts` defines the frozen
`story-blueprint-v1` authoring artifact. A blueprint carries source-outline
provenance, canonical truths, protected facts, revelations, realization routes,
required and optional beats, opposition clocks, and viable end states. Its
local validator rejects duplicate or unknown IDs, revelation cycles,
unreleased protected facts, route-less required revelations, invalid route
references, endings that omit required revelations, and optional beats that
silently become the only satisfier of a required outcome.
Every declared end state must contain at least one required outcome and one
required truth; a nonviable ending is omitted rather than represented with
empty requirement arrays.

The authoring validator first builds one symbol registry for every declared
truth, participant, location, route, event, opportunity, revelation, outcome,
beat, and ending. It then binds every reference through its declared namespace
in stable path order. Duplicate declarations and all bindable reference
failures are reported together; wrong-namespace failures identify the expected
and supplied namespaces, and an unambiguous opportunity-to-truth correction is
shown where available. Binding is read-only and does not alter the candidate.

After binding, semantic validation uses one immutable bound projection of the
candidate. Map reachability, event ordering, evidence ownership, endings,
profile rules, and the local fairness/completeness reviewers follow those
typed links instead of repeatedly resolving raw IDs. The compiler keeps each
reviewer's diagnostics grouped and reports all independent findings available
within the same bounded repair attempt.

Routes provide declarative truth satisfiers, availability constraints, eligible
location classes, and a bounded failure-forward result. Evidence placements
declare immutable custody and their valid location classes; participant
knowledge declares what each party starts knowing. They are not executable
runtime effects. Phase 5 realizes accepted declarations into a dedicated V2
fact map using the shared typed turn contract; no blueprint prose can mutate
session state.

Knowledge protections gate what reaches the player-facing observer context until
their release revelations complete. They do not prohibit legitimate NPC knowledge:
for example, a culprit may know their own act before the player can discover it.

Minimal immutable fixtures live in `data/story_blueprints/v1/` for mystery,
fantasy, sci-fi, and relationship stories. The authoring-quality contract tests
load each fixture. `compiled_story_as_blueprint` is a temporary one-way,
reduced projection from the retained public `CompiledStory` API, avoiding a
second causal authority while consumers migrate.

## Phase-2 genre profiles

Versioned YAML profiles in `data/genre_profiles/` declare causal roles, allowed
revelation roles, phase ordering, required turning points, ending truths,
evidence-route requirements, and generic policy mappings for mystery, fantasy,
sci-fi, and relationship stories. `GenreProfileRegistry` injects a validator
selected by the blueprint's declared genre; shared engine and runtime code do
not branch on genre names.

`genre_causality` binds profile-defined roles to canonical truths, while each
revelation may declare a profile-defined role and subject role. The declarative
adapter validates role cardinality, revelation legality, phase order, turning
points, ending support, required evidence routes, circular proof, and (where a
profile requests it) climaxes backed by required discoveries. Mystery requires
one complete crime solution and its victim, perpetrator, motive, means,
opportunity, method, time window, concealment, and evidence-backed
identification/exoneration routes. Its profile also requires two declared
alternative suspect hypotheses, each with separate playable supporting and
exonerating truths. Fantasy, sci-fi, and relationship profiles
instead require rule/source/cost, failure/constraint/remedy/trade-off, and
wound/need/choice/outcome structures.

Adding a genre requires a profile, an injected validator adapter where the
declarative adapter is insufficient, and valid/invalid fixtures. It does not
authorize a new runtime branch or make a blueprint mutable.

## Phase-3 compilation and evaluation

`storygame.authoring.blueprint_compiler.BlueprintCompiler` accepts one raw
outline, a selected injected `GenreProfileRegistry`, and a provider transport.
The transport receives an explicit `json_object=True` choice. A JSON-mode
rejection uses the single shared fallback request with `json_object=False`.
Malformed responses and local schema/profile/provenance failures use the same
single recovery request while retaining `json_object=True`; after that the
compiler raises `BLUEPRINT_COMPILATION_EXHAUSTED`. No rejected response is a
playable authoring input. When local validation supplies a safe diagnostic, the
recovery request receives it and must return the complete corrected object.
That request also receives the rejected candidate as inert JSON data, so it can
preserve valid authored fields instead of regenerating the blueprint wholesale.
The same preservation rule applies to critic-driven repair, including
route-fairness and Freytag diagnostics.
Every parseable repair candidate also receives a compact local ID ledger for
truths, participants, locations, events, opportunities, realization routes,
revelations, outcomes, and beats. The repair prompt treats existing IDs and
collection membership as stable unless the diagnostic directly requires a
change, and maps each reference-bearing field to its permitted ID namespace.
This ledger is compiler context, never fictional content.
The ledger is derived from the shared symbol registry and includes optional
beats and end states as well as the required collections. A deterministic
candidate-to-candidate audit classifies additions, removals, renames, ownership
changes, and reference changes by namespace. The compiler gives the repair
request the prior valid ledger and rejects an unrelated destructive change with
an explicit `UNRELATED_REPAIR_CHANGE` diagnostic; it never silently restores
or merges the candidate. Full-object responses still use the existing single
repair request budget, and an approved repair is validated and critic-reviewed
again before acceptance.
When invalid source-owned metadata masks deeper structural or timeline failures,
the compiler performs a diagnostic-only source-normalized preflight and includes
those latent failures in the same repair instruction; the original candidate is
still rejected until it declares the correct source metadata itself.
Timeline diagnostics name every infeasible ordering pair in one pass, and the
prompt requires each constrained predecessor to end no later than its successor
begins.
Evidence opportunities must bind to realization routes, not connected map routes;
the compiler batches every invalid opportunity-to-realization-route reference in
the one recovery diagnostic.
It also distinguishes an opportunity's participant holder from its location, and
reports the exact invalid reference field rather than an ambiguous unknown ID.
Opportunity ownership is a partition: an opportunity may appear only on the
realization route named by its `route_id`. Alternative-suspect supporting and
exonerating evidence stays on that suspect's own playable routes and must not be
copied into the terminal culprit's solution-synthesis routes. A custody repair
removes the misplaced route reference while preserving the opportunity's declared
owner and the separate alternative-suspect routes.
Every evidence opportunity also has to be reachable from an initially accessible
location through an authored connected-route graph; the prompt requires a map
connection or a reachable evidence placement before it returns a candidate.
Those connections must reflect the outline's declared setting through
setting-appropriate transition locations and layered travel, rather than using
an implausible direct edge solely to pass reachability validation.
The compiler prompt also enumerates the generic top-level and nested collection
shapes; it does not send a provider-enforced schema, and local validation stays
authoritative. It additionally specifies JSON primitive types so the candidate
cannot replace boolean, numeric, or array fields with prose.
For malformed candidates, local validation batches up to 20 structural failures
into that one repair prompt, preventing a costly field-by-field recovery cycle.
The prompt states bounded numeric values, required Freytag phases, and the
closed optional-beat purpose vocabulary before generation. It also makes the
profile's scalar identifier and the alternative-satisfier rule explicit: every
`alternative_satisfier` optional beat must declare a `required_outcome_id`,
and optional beats cannot be the only way to satisfy a required outcome. Local
validation reports all missing alternative-satisfier outcomes together so one
bounded repair can correct the complete candidate. A plausible alternative
suspect is not automatically an alternative satisfier; use that purpose only
when the beat genuinely provides another way to satisfy a declared outcome.
It explicitly names the literal schema version and requires realization-route
opportunity IDs to agree with each opportunity's declared route ID.
Every failure-forward declaration names at least one bounded consequence truth.
It must also either establish one of the failed route's own result truths or
offer an alternative realization route, preventing dead-end investigations.
On an `UNKNOWN_REFERENCE` repair, the compiler explicitly requires every truth
reference—including failure-forward and suspect-hypothesis references—to match
one of the candidate's declared truth IDs; an error never authorizes inventing
a replacement ID.

The compiler plans from the profile terminal truth and asks for phases,
required and optional beats, routes, protections, pressure, and
failure-forward declarations. It validates the selected outline ID and SHA-256
hash against the candidate's source provenance before critique. Injected
continuity, causality, and dialogue critics receive the complete blueprint and
opening facts. `RouteFairnessCritic` additionally requires the profile's
`minimum_routes_per_required_revelation` genuinely distinct route roles for
every required revelation (default: two). One injected repairer may revise a
rejected candidate; the repaired result is fully revalidated and re-reviewed.
Freytag revelation gates use the declared required-beat sequence, rather than
pressure values, so a resolution may correctly lower dramatic pressure after a
climax gate.

The compiler sends the full normalized authoring context to its provider:
opening-public boundary, hard constraints, creative direction, and extensions.
Hard constraints are non-negotiable source facts, not creative suggestions; a
candidate that substitutes their identities, events, motives, methods, or
required resolution outcomes must be rejected during editorial review.
Each terminal end-state truth must be declared consistently in a causal event,
an evidence opportunity, and a realization route, so the critic can prove its
complete playable chain.
Authoring controls remain outside the fictional world: local compilation
rejects explicit references to reviewed causal artifacts, compiler artifacts,
blueprint candidates, source provenance, and story blueprints in fictional
fields while retaining provenance as artifact metadata.
Every required revelation must use the profile's minimum number of distinct
evidence-opportunity kinds across its realization routes; multiple routes of
one evidence type do not establish route fairness.

`BlueprintCompilation` retains a review record: prompt version, source outline
hash and ID, model metadata, validation diagnostics, critic results, request
count, and whether repair occurred. The `storygame-blueprint` operator command
is deliberately live-only: both `--live` and
`FREYTAG_ENABLE_LIVE_COMPILER=1` are required, a transport factory is injected,
and output must be a new `*.candidate.json` envelope. It never overwrites a
reviewed fixture or makes raw outlines runtime inputs.

## Phase-5 compiler operations

The compiler pipeline is staged: syntax parsing, symbol definitions, reference
binding, semantic passes, and critics. The bound IR is an immutable validation
projection; it is discarded after the candidate is accepted or rejected and
never becomes runtime state.

Reference fields use explicit namespaces:

| Reference family | Namespace |
| --- | --- |
| truths, prerequisites, knowledge, and protections | `truth` |
| actors, holders, and hypothesis participants | `participant` |
| map and opportunity locations | `location` |
| map endpoints | `connected_route` |
| causal prerequisites and timeline endpoints | `causal_event` |
| evidence ownership | `evidence_opportunity` |
| opportunity ownership and failure-forward alternatives | `realization_route` |
| revelation and beat gates | `revelation`, `required_beat` |
| outcomes, beats, and endings | `required_outcome`, `required_beat`, `optional_beat`, `end_state` |

Binding diagnostics are deterministic and grouped by source path. Each records
the expected namespace, supplied ID, supplied namespace when known, and a
suggestion only when the mapping is unambiguous. `UNKNOWN_REFERENCE` remains
the compatibility code for an unbound ID. Syntax failures stop before binding,
binding failures stop before semantic passes, and no unbound candidate is
accepted.

Repair context contains the rejected JSON, the current symbol ledger, and the
prior valid ledger. The local structural diff classifies declaration additions,
removals, renames, ownership changes, and reference changes by namespace. An
unrelated destructive change produces `UNRELATED_REPAIR_CHANGE` and is
rejected; the compiler never silently restores or merges a repair. The local
check is authoritative, so the prompt does not duplicate ID-preservation or
destructive-change policy as a second rule system.

For operator troubleshooting, inspect stages in order: malformed output or
schema errors indicate a provider-boundary problem; `UNKNOWN_REFERENCE` or a
wrong-namespace diagnostic indicates a candidate binding problem;
`UNRELATED_REPAIR_CHANGE` indicates that the repair changed unrelated story
content; semantic or critic diagnostics indicate a graph or profile defect.
The compiler has one initial request and at most one recovery request. An
exhausted run is a non-playable diagnostic artifact, never a reviewed or
runtime input.

## Authority map

| Artifact | Lifecycle and purpose | May mutate during a session? |
| --- | --- | --- |
| `data/story_outlines.yaml` raw outline | Offline source material selected while building an authoring input. It is never a runtime input. | No |
| `WorldPackage` | Validated expansion of an outline, genre template, curve, opening setup, map, characters, and items. It is realized into the V1 fact-backed world. | No |
| Legacy `StoryPackage` | Offline evaluation projection of `WorldPackage`, used to assess clues, causal assumptions, and endings. | No |
| `CompiledStory` | Immutable V2 fixture input, currently carrying a reduced beat/protection graph for `RuntimeState` bootstrap. | No |
| Story Blueprint (planned) | Versioned, immutable causal authoring artifact compiled offline from a raw outline and genre profile. It will supersede the reduced causal role of `CompiledStory` through a documented migration. | No |
| Canonical facts | Assertable/retractable runtime truth. Policy validates every accepted delta before atomic commit. | **Yes — the sole mutable authority** |
| `RuntimeState` | V2 session container and projection boundary; its mutable state must be realized from and reconciled with canonical facts as the blueprint migration proceeds. | Only through the fact-backed commit boundary |
| `StoryState.json`, `STORY.md`, traces, transcripts, saves | Integrity-checked, orchestrator-written projections of accepted facts and decisions. Saves restore facts through their migration boundary; none is a competing mutation authority. | No |

Blueprint prose guides compilation and rendering only. It cannot execute an
effect or establish truth. A model may propose a bounded effect or a route, but
policy must validate and commit the corresponding facts before narration can
state it.

## Phase-4 Vale Mansion reviewed vertical slice

`data/story_blueprints/v1/vale_mansion_case.yaml` is the editor-reviewed
mystery vertical slice. It declares Beatrice Harrow's complete crime solution,
every relevant party's initial knowledge, the 23:42–23:50 west-gallery window,
and payment, physical, alibi, and concealment evidence. Its reveal ladder is:
suspicious death; significant payment trail; unsound groundskeeper accusation;
Harrow's means, motive, and opportunity; then a supported case decision.

Every pivotal revelation has two different declared routes, a valid location
class, availability requirements, custody via evidence placement, and a
failure-forward outcome. `tests/test_vale_mansion_blueprint.py` exercises a
physical route and a document/testimony route, early groundskeeper accusation,
an unrelated action, and failed/contaminated-clue progression. These are
authoring acceptance contracts: they prove the immutable graph is fair.
`tests/test_blueprint_runtime.py` additionally proves its Phase-5 fact
realization, protected player context, evidence-backed route validation,
atomic rejection, and failure-forward commit behavior.

## Phase-5 runtime realization

`realize_blueprint` copies a validated blueprint's canonical truth summaries,
evidence availability and custody, participant knowledge, scene state,
relationships, opposition clocks, revelation/beat state, and route history into
one mutable fact map. `ProgressionValidator` accepts a stable route ID only if
the route is currently legal and any supplied evidence IDs are available and
support its satisfiers. It commits the route's declared truths—or its bounded
failure-forward truths when `route_failed` is set—before returning. A rejected
route leaves the fact map unchanged.

For a V2 state bootstrapped with a blueprint, `BeatUpdate` requires `route_id`;
the retained bare `completion_tags` bridge cannot advance blueprint
progression. `RuntimeContextBuilder` adds only earned truth IDs and legal route
metadata to the turn prompt, preserving the existing one-request plus one
recovery-request budget. Protected canonical truth summaries never enter that
observer context before their authored route conditions have completed.

## Authoring-quality suite

`authoring_quality` and `runtime_safety` are exclusive quality classifications
that sit alongside the existing unit/component/integration/evaluation
performance tiers. The collection guard assigns exactly one of each. Run the
baseline suite with:

```text
TMPDIR=/tmp uv run pytest -q --no-cov -m authoring_quality
```

The authoring-quality baseline loads every supported genre fixture (mystery,
fantasy, sci-fi, and relationship). Pytest collection counts and optional
`--tier-report` totals are informational; no fixed collected-test count is
accepted as a quality gate.

## Measures for later phases

| Measure | Definition | Phase-0 baseline |
| --- | --- | --- |
| Compilation pass rate | Accepted blueprint compilations / attempted compilations. | Not applicable until Phase 3. |
| Genre-validator failure rate | Genre validation failures / submitted candidate blueprints, by genre and error code. | Not applicable until Phase 2. |
| Independent routes | Minimum number of distinct declared realization routes per pivotal revelation. | Vale: 2 distinct routes per pivotal revelation. |
| Premature-leak rate | Protected-truth leaks before their required facts / protected-truth exposure attempts. | Measure at runtime realization in Phase 5. |
| Clue-route completion rate | Completed declared clue routes / routes made available to scripted play. | Authoring routes are covered by two solved-route acceptance paths. |
| Fail-forward coverage | Routes with a declared viable failure-forward result / all routes. | Vale: 100% of declared routes. |
| Normal-turn model calls | Inference requests per ordinary player turn. | Preserve the current cap: one normal request plus at most one shared recovery request. |
| p95 latency | 95th percentile end-to-end ordinary-turn latency. | Preserve the under-ten-second target. |
