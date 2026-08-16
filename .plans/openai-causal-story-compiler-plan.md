# OpenAI-backed causal story compiler plan

## Status and decision

**Status:** proposed. No runtime behavior changes are authorized by this plan.

This plan extends the existing offline `BlueprintCompiler`; it does not add a
second compiler or make a model call during ordinary play. It supersedes the
unfinished authoring portions of
[`genre-blueprint-authoring-plan.md`](genre-blueprint-authoring-plan.md): its
completed V1 blueprint contracts remain useful foundations, but the reduced V1
fixture and template-based world builder are not sufficient to rebuild Vale
Mansion coherently.

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
reviewed artifact may be realized into a story package; facts remain the sole
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
                                     reviewed story package realization
                                                    |
                                                    v
                                           fact-backed gameplay
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
  compiler command. The runtime selector rejects it until a reviewed artifact
  is promoted through the normal package workflow.
- Shared engine behavior remains story- and genre-agnostic. Genre-specific
  causal roles belong in versioned profile data; concrete Vale details belong
  only in its source and artifact data.
- A candidate never overwrites a reviewed fixture. It is written only as a
  new `*.candidate.json` artifact with provenance and review results.

## Target authoring contracts

`story-blueprint-v2` will retain the useful V1 concepts—canonical truths,
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
| Freytag progression | Ordered phase/beat graph with revelation gates, pressure change, and alternatives | Routes open at or after their gate, required revelations precede dependent beats, and pacing/progression never regress. |

For mystery, the **profile data** will require roles equivalent to perpetrator,
victim, decisive event, timeline, means, motive, opportunity, concealment, and
proof. Other profiles declare different terminal roles but use the same graph,
location, route, and Freytag validators.

## Implementation phases

### Phase 0 — Freeze the baseline and design V2 migration

- [ ] Inventory every current consumer of `StoryBlueprint`,
  `compiled_story_as_blueprint`, `build_world_package`, and the hosted-demo
  bootstrap path.
- [ ] Add a concise authority/migration note describing V1 as a reduced bridge
  and V2 as the causal source for a rebuilt package.
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

**Exit criteria:** a V2 artifact can coexist with V1 fixtures; no runtime
consumer silently starts loading a candidate, and any selected source outline
can be resolved deterministically by ID. Vale has a distinct, reviewable raw
source rather than an implied or reconstructed one.

### Phase 1 — Add the OpenAI compiler transport (tests first)

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

**Exit criteria:** with an injected fake OpenAI client, a valid V1 blueprint
candidate follows the exact two-request maximum; no key or secret appears in
an artifact or failure message.

### Phase 2 — Define and validate `story-blueprint-v2` (tests first)

- [ ] Add V2 contract types for concrete locations, connected routes, causal
  events, timeline constraints, evidence opportunities, and beat/revelation
  gates. Give every cross-reference a stable ID.
- [ ] Preserve V1 loading during migration. Add an explicit V1-to-V2 migration
  result that is marked incomplete where old data lacks causal or concrete-map
  information; never fabricate missing facts during migration.
- [ ] Make profiles data-driven for required terminal and causal roles,
  minimum independent proof routes, allowed opportunity types, and required
  Freytag gates. Keep role labels in profile data, not shared engine branches.
- [ ] Add validators for graph cycles, impossible timelines, unknown actors,
  locations, evidence, holders, and truths; incompatible custody; unreachable
  required locations; routes whose prerequisites cannot be satisfied; and
  premature protected knowledge.
- [ ] Add a `CausalCompletenessCritic` alongside `RouteFairnessCritic`. It
  proves each terminal truth has a backwards chain through declared evidence
  or testimony to reachable opportunities, then forward into a valid end
  state.
- [ ] Add a `FreytagProgressionCritic` that validates ordered gates,
  prerequisite revelations, pressure changes, and at least one viable
  alternative route where the profile requires one.

**Tests:** valid and invalid fixtures for mystery, fantasy, sci-fi, and
relationship; each missing causal role; cyclic cause; invalid time order;
missing/isolated crime-scene location; inaccessible clue; invalid custody;
knowledge leak; single-route proof where two are required; and a Freytag gate
that opens before its prerequisites.

**Exit criteria:** no prose scan is needed to establish map validity: all
navigation, clue, participant, and progression dependencies are structured and
locally validated.

### Phase 3 — Compile backwards, critique, and repair boundedly

- [ ] Replace the broad V1 prompt with a staged V2 instruction: establish
  terminal truth; enumerate causal event/timeline; work backward to evidence,
  testimony, and opportunities; bind them to concrete reachable locations;
  then assign revelation gates and Freytag beats.
- [ ] Require the candidate to emit multiple independent realization routes
  for every profile-required revelation and to distinguish proof from mere
  suspicion.
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

### Phase 4 — Create the Vale Mansion candidate from source, not patches

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
- [ ] Once accepted, realize the reviewed V2 artifact into a new mystery world
  package and remove the conflicting condensed template topology in the same
  change. Do not retain prose that advertises rooms absent from the graph.

**Tests:** generated-candidate schema/provenance validation; Vale-specific
authoring fixtures for each causal role and concrete location; reachability
from the opening; two independent solution routes; no early solution leak;
and regression coverage that keeps all shared gameplay tests genre-agnostic.

**Exit criteria:** the mansion's described destinations, graph nodes, exits,
NPC placement, clue custody, causal solution, and Freytag gates agree in one
reviewed artifact.

### Phase 5 — Runtime realization, evaluation, and promotion

- [ ] Add a single V2-to-world-package realization adapter. It creates
  fact-backed rooms, paths, locations, custody, knowledge, gates, and
  progression inputs; it does not add mystery logic to the engine.
- [ ] Make `LOOK` render committed visible NPCs, items, and exits, and make an
  unavailable destination fail honestly without narrating uncommitted travel.
- [ ] Add generic navigation/playability evaluation: every opening-visible exit
  changes canonical location; every displayed entity is present; required
  proof routes are reachable; and no accepted narration claims an uncommitted
  location or clue.
- [ ] Run the complete test suite, authoring-quality suite, deterministic
  cross-genre evaluation, staged hosted-demo E2E, and the existing SHA-bound
  promotion gate. Review the generated candidate and its staging evidence
  before production promotion.

**Exit criteria:** the hosted Vale session exposes only committed affordances,
has a coherent playable mansion investigation, and passes the same generic
causality/navigation/progression checks required of every future genre.

## Completion checklist

- [ ] OpenAI adapter is explicit, credential-safe, mocked in tests, and never
  invoked by gameplay or CI.
- [ ] V2 contracts express concrete topology plus backwards causal and
  Freytag progression graphs.
- [ ] Local validators and critics reject incomplete, unreachable, leaking, or
  temporally impossible stories.
- [ ] Vale is regenerated as a reviewed candidate, not manually patched from
  the defective template.
- [ ] A reviewed V2 artifact realizes into facts and passes generic gameplay,
  staging, and promotion evaluation.
- [ ] Documentation explains the paid/offline workflow, artifact review, and
  provider configuration without exposing credentials.
- [ ] The CLI and tests demonstrate that every selected outline in
  `data/story_outlines.yaml` can enter the same compiler pipeline using its
  own declared profile; Vale is only the first reviewed rebuild.
