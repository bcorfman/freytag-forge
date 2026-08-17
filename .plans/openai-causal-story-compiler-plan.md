# OpenAI-backed causal story compiler plan

## Status and decision

**Status:** proposed. No runtime behavior changes are authorized by this plan.

This plan extends the offline V2 authoring compiler; it does not add a second
compiler or make a model call during ordinary play. It supersedes
[`genre-blueprint-authoring-plan.md`](genre-blueprint-authoring-plan.md): its
useful authoring concepts are incorporated here, while its V1 fact-runtime,
package-realization, and compatibility assumptions remain retired.

The compiler will use OpenAI directly through one first-party adapter. Ollama
is deliberately out of scope for this plan: its current cloud catalog does not
provide GPT-5.6, while this plan's stated requirement is access through the
owner's `OPENAI_API_KEY`.

## Outcome

An explicit, paid, offline command can turn **any selected outline** from
[`data/story_outlines.yaml`](../data/story_outlines.yaml) into a reviewable,
typed `story-blueprint-v2` candidate using an OpenAI model. The candidate must
plan backward from the genre's terminal resolution, derive concrete reachable
locations and causal opportunities, and bind every revelation to the Freytag
progression. A mystery profile will require a complete solution graph (event,
timeline, means, motive, opportunity, concealment, proof, and alternatives)
without teaching shared runtime code any mystery-specific names.

The compiler output remains an immutable authoring artifact. Only a separately
reviewed artifact may bootstrap V2 `RuntimeState`; `RuntimeState` is the sole
mutable runtime authority.

### Vale source decision

Vale Mansion is **not** currently an entry in `data/story_outlines.yaml`.
Its surviving sources are a reduced `compiled-story-v1` fixture and a V1
blueprint—both are prior artifacts, not raw compiler input. The compiler cannot
truthfully rebuild Vale from scratch by selecting a nonexistent outline.

Before the Vale vertical slice, add one explicitly author-owned raw Vale entry
to `data/story_outlines.yaml`. It contains only the intended premise, public
opening boundary, thematic/tone constraints, and any terminal constraints the
author elects to preserve. Mark it `authoring_only` until its generated V2
artifact is reviewed. Runtime outline selection must exclude `authoring_only`
entries, while the offline compiler may select them by exact ID. This gives
Vale the same input contract as every other story without sending an
unreviewed raw outline into gameplay.

The old compiled fixture and V1 blueprint may be comparison evidence during
review, but never copied into the new candidate or treated as canonical truth.
The OpenAI compiler may create a newly coherent causal solution within the new
raw source's approved constraints; human review decides whether to accept it.

```text
outline + genre profile
        |
        v
OpenAI compiler adapter -- JSON-object request --> typed blueprint candidate
        |                                           |
        |                                      local validation
        |                                           |
        v                                           v
provenance record <--- critic / bounded repair --- causal + map + Freytag gates
                                                    |
                                                    v
                                     reviewed `CompiledStory` artifact
                                                    |
                                                    v
                                      V2 `RuntimeState` bootstrap
```

## Non-negotiable boundaries

- `OPENAI_API_KEY` is read only at the live-authoring boundary. It is never
  serialized into candidates, logs, traces, test fixtures, or GitHub output.
- The live compiler requires an explicit `--live` acknowledgement and remains
  disabled unless `FREYTAG_ENABLE_LIVE_COMPILER=1` is set. CI and ordinary game
  startup never invoke it.
- Provider output is untrusted. Request JSON-object mode for syntax, retry
  once without that option only if necessary, and validate all semantics
  locally. The two attempts share one compilation recovery budget.
- Provider/model selection is explicit. Do not infer it from prompt content or
  silently substitute a model. A live OpenAI compilation requires a model via
  `--model` or `FREYTAG_COMPILER_MODEL`.
- Outline selection is explicit. `--outline-id` resolves exactly one entry in
  `data/story_outlines.yaml`; the compiler validates the selected entry's
  declared genre and content hash before and after generation. It must never
  substitute Vale, select an outline by incidental prompt text, or contain a
  fixed list of outline IDs.
- An `authoring_only` outline is eligible only for the explicit offline
  compiler command. The hosted bootstrap rejects it until a reviewed artifact
  is promoted through the normal V2 fixture workflow.
- Shared runtime behavior remains story- and genre-agnostic. Genre-specific
  causal roles belong in versioned profile data; concrete Vale details belong
  only in its source and artifact data.
- Raw outlines are offline compiler input only; neither outlines nor candidate
  artifacts are mutable runtime authority.
- A candidate never overwrites a reviewed fixture. It is written only as a
  new `*.candidate.json` artifact with provenance and review results.

## Target authoring contracts

`story-blueprint-v2` will retain useful causal-authoring concepts—canonical truths,
knowledge assignments, protected facts, revelations, realization routes,
opposition clocks, end states, and required/optional beats—and add the missing
structured planning layer:

| Contract area | Required declaration | Local invariant |
| --- | --- | --- |
| Terminal truth | One or more profile-required end truths | Every required end state depends on a complete causal proof chain. |
| Causal graph | Typed causal events, inputs, outputs, actors, time bounds, and location IDs | Dependencies are acyclic, inputs exist before outputs, and timeline bounds are consistent. |
| Concrete world | Locations, connected routes, initial access, route aliases, and location roles | Every referenced location exists; every required opportunity is reachable from the opening under its declared prerequisites. |
| Evidence/opportunity | Evidence supports or refutes declared truths; custody, holder, and concrete placement are explicit | No clue names an unknown truth, holder, or location; a required proof has the profile-required distinct route families. |
| Knowledge | Party knowledge, protection, and release gates | An actor can only supply a clue they know; protected truth cannot become available before its gate. |
| Freytag progression | Ordered phase/beat graph with required outcomes, optional/substitutable beats, revelation gates, pressure change, and alternatives | Routes open at or after their gate, required revelations precede dependent beats, optional beats cannot become the sole route to a required ending, and pacing/progression never regress. |
| Failure forward | Each blocked or failed opportunity declares a bounded consequence and an alternate viable opportunity where required | Failure cannot silently make a required ending unreachable or prescribe a player action. |

For mystery, the **profile data** will require roles equivalent to perpetrator,
victim, decisive event, timeline, means, motive, opportunity, concealment, and
proof. Other profiles declare different terminal roles but use the same graph,
location, route, knowledge, failure-forward, and Freytag validators. For
example, sci-fi profiles may require cause, constraint, remedy, and trade-off;
fantasy profiles rule, source, and cost; relationship profiles wounds, needs,
agency-preserving choices, and viable outcomes.

### Soft-convergence and runtime-framing semantics

- A required outcome is a dramatic obligation, not a prescribed scene
  itinerary. Multiple declared, independently reachable realization routes may
  converge on the same canonical revelation or outcome; satisfying it unlocks
  a new range of declared opportunities. The compiler and validators protect
  causality, revelation order, escalation, and consequential choices—not an
  exact sequence of scenes.
- Freytag phases express pressure rather than geography. Phase and pacing data
  may constrain escalation, opposition response, revelation scale, and
  opportunity availability, but they must not require the player to occupy a
  particular location or replay a named scene to advance.
- Failure-forward declarations must specify a bounded committed consequence
  and retain a viable route to every required ending. Suitable generic
  consequences include new information, increased pressure, changed access,
  a relationship shift, or a costlier alternative; repeated attempts at the
  same blocked action are not themselves a failure-forward path.
- Scenes are ephemeral runtime framing for the active dramatic situation:
  participants, current location or declared location class, immediate
  objective, dramatic question, and pressure. They are neither authored
  completion units nor mutable authorities. Any realization route, evidence,
  location, or consequence that changes canonical state must be declared and
  validated in the reviewed artifact; the runtime must not invent or relocate
  canonical truth to force convergence.

## Implementation phases

The following phases are the delivery order. The detailed work packages below
are deliberately ordered by dependency rather than duplicated as a second set
of phases.

| Phase | Bounded deliverable | Work package |
| --- | --- | --- |
| 0 | A source-selection and provenance boundary for every outline, including the authoring-only Vale source | Source and authority |
| 1 | A locally validated causal `CompiledStory` contract with profiles, route diversity, optional beats, knowledge, and failure-forward guarantees | Causal contract and profiles |
| 2 | An explicit, credential-safe OpenAI transport and offline compiler command that produces an unreviewed candidate | OpenAI transport and candidate orchestration |
| 3 | A bounded backwards-planning, critic, and repair pipeline that either accepts a fully validated candidate or returns diagnostics | Compilation, critics, and repair |
| 4 | Reviewed cross-genre fixtures, beginning with Vale, promoted only from candidate artifacts | Reviewed artifact corpus |
| 5 | A V2-only reviewed-artifact loader, hosted evaluation, and SHA-bound promotion evidence | V2 bootstrap and promotion |

### Work package — Source and authority (Phase 0)

- [ ] Inventory every current V2 authoring and hosted-bootstrap consumer of
  `CompiledStory`, and confirm no retired V1 blueprint/package surface is a
  dependency.
- [ ] Add a concise authority note identifying raw outlines and reviewed causal
  artifacts as immutable inputs and `RuntimeState` as the sole mutable truth.
- [ ] Record the current Vale defects as failing authoring cases: absent west
  gallery, prose-only upper gallery/long hall, unreachable evidence locations,
  and a solution graph that cannot be proven through the playable map.
- [ ] Add a source-selection inventory covering every outline in
  `data/story_outlines.yaml`: stable ID, declared genre, tone/variant fields,
  and content hash. Treat the file as immutable compiler input, never runtime
  state.
- [ ] Create the new `authoring_only` Vale raw-outline entry. Its source ID is
  the provenance ID for the rebuild; do not claim that the existing compiled
  fixture or V1 blueprint is its raw outline.
- [ ] Extend outline schema/selection tests so the compiler can select an
  `authoring_only` outline by exact ID, while normal runtime template selection
  excludes it.
- [ ] Decide and document the reviewed-artifact location and versioning policy
  before generating any paid candidate.

**Exit criteria:** no runtime consumer silently starts loading a candidate, and
any selected source outline can be resolved deterministically by ID. Vale has a
distinct, reviewable raw source rather than an implied or reconstructed one.

### Work package — OpenAI transport and candidate orchestration (Phase 2; tests first)

- [ ] Add `OpenAIBlueprintTransport` at the authoring boundary, implementing
  the existing `BlueprintCompilerTransport.generate(prompt, *, json_object)`
  Protocol.
- [ ] Add a typed, constructor-injected configuration object containing API
  key, selected model, optional base URL, and finite request timeout. Read
  `OPENAI_API_KEY` only from the CLI/factory boundary; fail with a typed,
  non-secret configuration error when it or the model is absent.
- [ ] Use the OpenAI Responses API with provider JSON-object mode when
  `json_object=True`; return normalized text/object output to the existing
  parser. Do not send a deep provider-side schema—the local V2 contract is
  authoritative.
- [ ] Normalize supported response envelopes and surface transport, refusal,
  empty-output, malformed-output, and JSON-mode-rejected cases as typed
  compiler errors. Let `BlueprintCompiler` own the single retry without JSON
  mode; do not add hidden adapter retries.
- [ ] Extend provenance with provider name, configured model, response/request
  identifier when available, prompt version, source hash, and local validation
  results. Never store credentials or raw headers.
- [ ] Extend `storygame-blueprint` with a first-party
  `--provider openai` selection and `--model`; retain
  `--transport-factory` solely as a mutually exclusive test/custom seam.
- [ ] Keep `--outline-id` as the required source selector. Resolve it through
  the existing outline loader, reject missing IDs and genre mismatches before
  any network request, and write the selected ID plus SHA-256 source hash into
  candidate provenance.
- [ ] Document the explicit environment setup and one-shot candidate command;
  add a non-CI live smoke command that is skipped without credentials.

**Tests:** mocked Responses success, plain/structured output normalization,
JSON-mode rejection then one non-JSON retry, malformed output exhaustion,
missing key/model, timeout, refusal, provenance redaction, CLI argument
conflicts, valid compilation setup for every selected outline fixture, unknown
outline ID, declared-genre mismatch, changed-source hash, and proof that no
test performs a paid request.

**Exit criteria:** with an injected fake OpenAI client, a valid V2 causal
candidate follows the exact two-request maximum; no key or secret appears in
an artifact or failure message.

### Work package — Causal contract and profiles (Phase 1; tests first)

- [ ] Add V2 contract types for concrete locations, connected routes, causal
  events, timeline constraints, evidence opportunities, party knowledge,
  failure-forward declarations, and beat/revelation gates. Give every
  cross-reference a stable ID.
- [ ] Model required outcomes separately from optional/substitutable beats.
  Each optional beat declares whether it is an alternative satisfier,
  complication, or relationship/world-development opportunity; validation
  rejects an optional beat that silently becomes the sole route to a required
  ending.
- [ ] Make profiles data-driven for required terminal and causal roles,
  minimum independent proof routes, allowed opportunity types, and required
  Freytag gates. Keep role labels in profile data, not shared engine branches.
- [ ] Add validators for graph cycles, impossible timelines, unknown actors,
  locations, evidence, holders, and truths; incompatible custody; unreachable
  required locations; routes whose prerequisites cannot be satisfied; and
  premature protected knowledge. Require each pivotal revelation to have two
  genuinely distinct routes unless its profile explicitly permits one.
- [ ] Add a `CausalCompletenessCritic` alongside `RouteFairnessCritic`. It
  proves each terminal truth has a backwards chain through declared evidence
  or testimony to reachable opportunities, then forward into a valid end
  state.
- [ ] Add a `FreytagProgressionCritic` that validates ordered gates,
  prerequisite revelations, pressure changes, and at least one viable
  alternative route where the profile requires one.

**Tests:** valid and invalid fixtures for mystery, fantasy, sci-fi, and
relationship; each missing causal role; cyclic cause; invalid time order;
missing/isolated location; inaccessible clue; invalid custody; knowledge leak;
single-route proof where two are required; optional-only ending route;
failure-forward path that dead-ends a required ending; and a Freytag gate that
opens before its prerequisites.

**Exit criteria:** no prose scan is needed to establish map validity: all
navigation, clue, participant, and progression dependencies are structured and
locally validated.

### Work package — Compilation, critics, and repair (Phase 3)

- [ ] Use a staged V2 instruction: establish
  terminal truth; enumerate causal event/timeline; work backward to evidence,
  testimony, and opportunities; bind them to concrete reachable locations;
  then assign revelation gates and Freytag beats.
- [ ] Require the candidate to emit multiple independent realization routes
  for every profile-required revelation and to distinguish proof from mere
  suspicion. It must classify each beat as required, optional/substitutable,
  or an alternative satisfier, and declare bounded failure-forward guidance
  without prescribing a player action.
- [ ] Pass the complete profile and source-outline hash to the model; verify
  the source ID/hash locally after parsing. Compile against the selected
  outline's profile; do not use a Vale-specific prompt or fallback.
- [ ] Keep the existing one optional critic/repair pass. Repair receives only
  structured diagnostics; it cannot change source provenance, weaken a
  profile, or remove failed obligations.
- [ ] Persist diagnostics explaining exactly which causal, route, map, or
  Freytag invariant rejected a candidate.

**Tests:** prompt snapshot/contract assertions; a transport payload that has
all mystery labels but lacks a logical proof chain; repair that fixes a single
reachable-route issue; repair exhaustion; and profile-driven non-mystery
backward planning without shared named-genre conditionals.

**Exit criteria:** a candidate either passes all local causal/map/progression
checks or is an explicitly non-playable artifact with actionable diagnostics.

### Work package — Reviewed artifact corpus (Phase 4)

- [ ] Prepare one reviewed raw Vale outline that states the terminal solution
  and intended public/protected boundaries without treating old compiled prose
  as authority. Add it as the Phase 0 `authoring_only` outline entry, then
  select it through the same `--outline-id` compiler path used by every other
  outline.
- [ ] Run the explicit OpenAI compiler command to write a new candidate;
  preserve the prompt version, source hash, model identifier, and critic
  reports.
- [ ] Review the candidate against a concrete Vale checklist: mansion foyer,
  study/library, west gallery crime scene, appropriate private/service routes,
  all material NPCs, evidence custody, murder timeline, means, motive,
  opportunity, concealment, exoneration, and at least two fair proof paths.
- [ ] Reject rather than hand-edit a logically broken candidate. Correct the
  raw source/profile/contract and regenerate a new candidate version.
- [ ] Once accepted, promote the reviewed V2 artifact as a new immutable
  `CompiledStory` fixture. Do not retain prose that advertises locations or
  opportunities absent from its validated graph.
- [ ] Repeat the same reviewed-candidate process for fantasy, sci-fi, and
  relationship fixtures. Each profile must demonstrate its own terminal roles,
  protected knowledge, route-diversity rule, optional beats, and
  failure-forward path; no fixture receives a special runtime branch.

**Tests:** generated-candidate schema/provenance validation; Vale-specific
authoring fixtures for each causal role and concrete location; reachability
from the opening; two independent solution routes; no early solution leak;
and regression coverage that keeps all shared gameplay tests genre-agnostic.

**Exit criteria:** the mansion's described destinations, graph nodes, exits,
NPC placement, clue custody, causal solution, and Freytag gates agree in one
reviewed artifact.

### Work package — V2 bootstrap and promotion (Phase 5)

- [ ] Add one reviewed-artifact loader that bootstraps a V2 `RuntimeState` from
  the causal `CompiledStory`. It must not revive world packages, facts, route
  proposals, or a deterministic incident selector.
- [ ] Pass only the bounded V2 runtime context—current world state, active
  beats, recent events, summary, protections, and pacing directives—to the
  turn model. Optional routes and failure-forward guidance remain authoring
  constraints, not a second runtime mutation authority.
- [ ] Enforce soft convergence at the runtime boundary: satisfy required
  outcomes only through the reviewed artifact's declared realization routes,
  unlock its declared follow-on opportunities after commit, and never steer
  toward a preferred scene or fabricate/relocate canonical evidence.
- [ ] Treat phase directives as pressure controls, not location or action
  mandates. Render scenes only as temporary projections of the accepted
  dramatic situation, and commit each declared failure-forward consequence as
  a bounded state change rather than retrying an expected action.
- [ ] Add generic authoring/playability evaluation: every required opportunity
  is reachable from the opening under declared prerequisites; every terminal
  truth has a causal proof chain; every protected truth has a release gate;
  pivotal revelations meet their profile's route-diversity requirement; and
  optional beats cannot be the sole path to an ending.
- [ ] Run the complete test suite, authoring-quality suite, cross-genre V2
  compiler/runtime evaluation, staged hosted-demo E2E, and the SHA-bound
  promotion gate. Review the generated candidate and its staging evidence
  before production promotion.

**Exit criteria:** the hosted Vale session runs only through V2 `RuntimeState`,
has a coherent playable mansion investigation, and passes the same generic
causality, reachability, knowledge, route-diversity, and progression checks
required of every future genre.

## Completion checklist

- [ ] OpenAI adapter is explicit, credential-safe, mocked in tests, and never
  invoked by gameplay or CI.
- [ ] V2 contracts express concrete topology, party knowledge, failure-forward
  guidance, required outcomes, optional/substitutable beats, and backwards
  causal/Freytag progression graphs.
- [ ] Local validators and critics reject incomplete, unreachable, leaking,
  temporally impossible, single-route, or optional-only-ending stories.
- [ ] Vale is regenerated as a reviewed candidate, not manually patched from
  the defective template.
- [ ] A reviewed V2 artifact bootstraps `RuntimeState` and passes generic V2
  runtime, staging, and promotion evaluation.
- [ ] Documentation explains the paid/offline workflow, artifact review, and
  provider configuration without exposing credentials.
- [ ] The offline compiler command and tests demonstrate that every selected
  outline in `data/story_outlines.yaml` can enter the same compiler pipeline
  using its own declared profile; Vale is only the first reviewed rebuild.
