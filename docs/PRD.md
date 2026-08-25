# Freytag Forge V2 product reference

> V2 cutover complete. The hosted `storygame.web_demo` adapter is the sole
> player-facing application surface and `RuntimeState` is the only mutable
> runtime authority. The retained `data/` directory is immutable authored
> input, not runtime state.

> The LLM-first runtime has a pinned historical rollback record, a testable
> root/`/dev/` channel contract, and isolated delivery channels. Trusted `main`
> CI deploys to `/dev/` and Railway staging; production is a manual promotion
> of a previously staged immutable SHA. See the
> [release baseline](release-baseline.md),
> [acceptance matrix](v2-acceptance-matrix.md), and
> [causal-spatial projection plan](../.plans/causal-spatial-runtime-projection.md).

## Product Intent
Freytag Forge is a deterministic narrative-engine platform for interactive fiction. It aims to blend strong IF usability with modern, testable narration controls and reproducible evaluation.
Current runtime generation is package-driven.

## Opening and cast continuity

Opening orientation is a typed authoring projection, not freeform runtime
truth. `StoryOutline` normalizes protagonist context, opening companions,
public briefing, arrival context, scene purpose, and first available actions.
The compiler emits `CompiledStory.opening` as `OpeningMetadata`; each
`OpeningContact` carries identity, role, relationship, opening location,
public knowledge, and item custody. Local validation requires contacts to be
declared in the cast and present at the initial location, and rejects protected
revelation summaries in public opening text.

Bootstrap copies the accepted opening declarations into the runtime's opening
fact projection before any player-facing output. The hosted session response
projects the same typed metadata, and the frontend renders it without issuing
an automatic `look` turn. Ordinary turns remain proposal-first and the
opening projection cannot mutate state or bypass commit validation. Existing
reviewed causal artifacts remain loadable: the compiler supplies safe generic
defaults when legacy opening metadata is absent.

## V2 capability baseline

The engine is V2-only. The following behavioral requirements define the
cross-genre runtime baseline; they do not depend on a retained V1 migration
ledger or historical implementation artifacts.

The presentation target is progressive description. A newly entered room or
newly encountered item may receive a full authored description with atmosphere,
layout, visible details, and actionable context. Ordinary movement back into a
known room should be concise and should mention only changed or newly relevant
details. An explicit `LOOK` request may expand the room description again. Item
inspection follows the same rule. Observation/discovery markers are fact-backed
state; prose is a projection and may not create facts.

For a normalized movement affordance, the turn prompt carries an explicit
post-commit destination rendering context while the commit remains subject to
the shared validation path. The narrator must describe that destination rather
than the origin. Opening orientation is provided only on the initial turn;
later turns must address the player's current action and cannot reuse opening
prose unless the player explicitly asks to look.

The player-facing opening renders only the scene, player context, and public
situation; authoring metadata such as arrival context and scene purpose is not
repeated as prose.

The NPC target is continuity, not decorative text. A declared NPC must remain
addressable only when present, answer as that NPC from permitted knowledge, and
retain interaction history, relationship state, and bounded stance changes.
Repeated questions may make an NPC impatient or less helpful, like a person,
but this is a generic validated interaction policy rather than a named-character
branch. Historical examples such as Daria inform the interaction shape only;
they are not V2 content. Current story packages provide their own NPCs.

Progression should be conversation-led and exploration-rich for every outline.
A question, earned trust, contradiction, follow-up, or purposeful investigation
of a place can unlock a declared lead or change the active objective. Searching
rooms and inspecting items remain valid player choices, but the experience must
not collapse into collecting interchangeable object text or solving detached
puzzles by rote. Objects and puzzles are optional authored supports;
conversation disclosures, exploration consequences, and relationship effects
are proposal-first, locally validated, and committed as facts before the
resulting lead or prose is shown.

These capabilities apply across mystery, fantasy, sci-fi, and relationship
stories. Opening metadata, room/item declarations, NPC roles, knowledge, and
presentation detail are authored inputs; accepted visibility, discovery,
dialogue effects, and relationship changes are committed to `RuntimeState`
facts before rendering.

## Causal-spatial runtime projection Phase 0

Phase 0 adds a read-only loss characterization at
`storygame.authoring.spatial_audit`. `audit_runtime_projection` bootstraps the
existing reduced `CompiledStory` projection and returns a frozen,
JSON-serializable `RuntimeProjectionAudit`. Its coverage blocks compare
declared IDs with IDs backed by canonical facts for participant placement,
scene subjects, evidence realization, evidence custody, and group encounters.

Each opening suggestion is checked only against current fact-backed target
aliases: a declared character with a `present` fact at the opening location or
a visible declared item with current custody. The serialized
`SuggestedActionAudit` records matched target IDs, target kinds, and an explicit
`supported` flag. Phase 0 does not parse ordinary gameplay, infer placement
from prose or roles, add new runtime fact families, or synthesize a fallback
target.

`storygame-blueprint-audit` includes this projection as a non-gating
`runtime_projection` block in JSON and a **Phase 0 runtime projection** section
in Markdown. Existing compiler checks retain their pass/fail meaning while the
separate `complete` flag records runtime readiness. The current reviewed Vale
artifact measures 7 declared participants and 21 evidence opportunities but
zero projected participant placements, evidence realizations, or custody
facts; all four advertised opening actions lack a current social or inspectable
target. Cross-genre characterization lives in
`tests/test_causal_spatial_projection_phase0.py`.

## Causal compiler Phase 0: symbol-resolution baseline

The offline causal compiler now carries a checked-in Phase 0 characterization
corpus at `tests/fixtures/causal_compiler_phase0.json` and a versioned baseline
at `data/story_blueprints/diagnostics/phase0-baseline.json`. The corpus covers
truth, participant, location, connected-route, causal-event,
evidence-opportunity, realization-route, revelation, required-outcome, and
required-beat namespaces. It includes known references, wrong-namespace
references, ambiguous IDs, and candidates containing multiple reference
failures, with mystery, fantasy, sci-fi, and relationship coverage.

Phase 0 is intentionally characterization-only. It does not add a runtime
authority, mutate an artifact, or call a provider. The current compiler
contract is recorded explicitly: syntax errors precede binding errors;
`UNKNOWN_REFERENCE` remains the compatibility code for an unbound reference;
`AMBIGUOUS_REFERENCE` is reserved for the symbol-resolution migration; and
independent bindable failures are reported in deterministic source-collection
and field-declaration order. A rejected candidate keeps the existing bounded
repair behavior: one initial request plus one repair request, never more than
two inference requests.

The baseline is evidence for the Phase 1 registry and bound-IR work. It is not
a promotion artifact and cannot become runtime input. Future diagnostic-code
changes must update the compatibility record and the characterization tests in
the same change.

## Offline storylet compiler Phase 0: dramatic characterization baseline

The offline storylet compiler has a separate, non-runtime Phase 0 corpus at
`tests/fixtures/storylet_compiler_phase0.json`, a measured baseline at
`data/story_blueprints/diagnostics/storylet-compiler-phase0-baseline.json`, and
an author-owned Vale Mansion source Brief at
`data/story_briefs/vale_mansion_storylet.yaml`. The Brief is selected only for
future offline authoring work; the existing reviewed `vale_mansion_rebuild`
fixture remains immutable runtime input.

The corpus establishes the Phase 1 vocabulary across mystery, fantasy, sci-fi,
and relationship stories: multiple eligible dramatic situations, a free-form
action outside those situations, protected knowledge, a failure-forward
alternative, and a fact-shaped completion marker that will later prevent
repetition. It also records measurable acceptance criteria: applicable required
beats need two distinct advancement paths; completion must support distinct
route families; protected facts must stay out of player-visible context; a
completed storylet must become ineligible; and normal turns must retain the
one-request path with at most one bounded recovery request.

The baseline exercises the current reviewed fixtures and records deterministic
runtime-context token estimates, one provider request for each successful normal
turn, a two-turn material-progress rate, active-beat persistence without a
declared completion tag, and short narrative observations. The observations are
diagnostics, not golden prose assertions. This phase adds no Storylet contract,
selector, provider call, mutable quality store, or runtime authority; facts
remain the sole canonical mutable truth.

## Offline storylet compiler Phase 1: immutable contracts

`story-blueprint-v2` now optionally carries a `dramatic_spine`, named
fact-template `consequences`, and immutable `storylets`. A storylet binds to a
required beat, truth/participant/location/pressure availability, route family,
bounded realization modes, declared consequences, fact-backed
activation/completion/abort markers, and explicit failure-forward targets.
These are reviewed authoring data—not runtime authority or executable effects.

The shared symbol registry binds every new reference and rejects wrong
namespaces. Local validation rejects unsatisfiable availability, undeclared or
conflicting fact effects, protected availability facts, invalid completion
markers, and failure-forward cycles. Versioned genre profiles hold generic
storylet variety, pressure-span, and alternate-progression minima; shared code
does not inspect genre names. Candidate audits now project coverage by beat,
purpose, realization mode, route family, and failure-forward chain.

Genre-blueprint authoring has completed its offline-only Phases 1–2 contract
and profile-validation layer.
Raw outlines, `WorldPackage`, legacy `StoryPackage`, `CompiledStory`, and the
immutable Story Blueprint are authoring inputs or projections; canonical facts
are the only mutable truth during a session. `StoryBlueprint` locally validates
generic causal references, protected-fact release order, revelation graphs,
route reachability, optional beat intent, and viable endings for all supported
genres. Versioned, injected genre profiles add semantic causal roles, allowed
revelation/evidence routes, phase and turning-point requirements, and ending
requirements for mystery, fantasy, sci-fi, and relationship stories; no shared
runtime code branches on these genre names. It does not yet alter runtime
bootstrap or gameplay. A one-way reduced
projection keeps the public `CompiledStory` fixture API available while future
consumers migrate. See [genre-blueprint authoring](genre-blueprint-authoring.md).

## Offline storylet compiler Phase 2: candidate generation and review

The explicitly gated offline compiler requests one complete
`story-blueprint-v2` JSON object: it first plans causal truths, locations,
revelations, and viable endings, then produces the dramatic spine, named
consequence templates, and bounded storylet pool. Source creative direction
and hard constraints are included verbatim as authoring context, while local
typed validation remains the authority; provider JSON-object mode is syntax
assistance, not a provider-side schema.

The existing one-request-plus-one-recovery limit applies to malformed envelopes,
JSON-mode fallback, validation repair, and transient transport errors together.
Repair receives the candidate and a namespace ledger including storylets and
consequences. It may add declarations called for by diagnostics, but the
structural-diff policy rejects unrelated rewrites of accepted causal content.

Before a candidate can be accepted, deterministic critics report stable,
independent diagnostics for storylet coverage and diversity, pressure-envelope
fit, participant continuity, protected-knowledge safety, and failure-forward
viability, alongside causal completeness, route fairness, and Freytag
progression. Candidate audit and promotion rerun these checks. Human approval
now explicitly covers dramatic questions, participant agency, repeated-content
risk, consequence quality, and distinct progression paths, in addition to the
existing causal review checklist. Generated storylets remain non-playable until
the whole artifact validates and an editor promotes it; this phase makes no
runtime change.

## Offline storylet compiler Phase 3: runtime narrative package and selector

An approved `reviewed-story-blueprint-v2` enters runtime through an immutable
`RuntimeNarrativeProjection`. The compatibility projection still carries the
existing `CompiledStory` for legacy consumers, while its read-only
`RuntimeNarrativePackage` preserves the reviewed candidate SHA-256 and source
ID/hash alongside the dramatic spine, storylets, consequence templates, and
protected-truth set.
`RuntimeState` holds that package only as authored input; facts remain the sole
mutable session authority and snapshots bind only the compiled-story identity.

`StoryletSelector` is constructor-injected with the package and `FactStore`.
It makes no provider request and no writes. It returns at most three eligible
opportunities, deterministically ranking active-beat compatibility, required
and absent known truths, present participants, current location, pressure band,
failure-forward urgency, recent-use facts, priority, then stable ID. Bootstrap
seeds explicit false-valued storylet active/completed/aborted/discovered and
recent-use facts; later phases may change those facts only through validated
commit policies.

The prompt context includes the active dramatic situation and only the small
eligible set's ID, purpose, question, realization modes, and consequence IDs.
It filters non-player knowledge and protected facts. An empty eligible set is
ordinary freeform play: it supplies no invented objective and forces no
transition.

Phase 3 adds the offline-only blueprint compilation and review workflow.
`BlueprintCompiler` requests provider JSON-object mode through an explicit
transport option, retries at most once without that option, locally validates
the complete generic/profile contract and source-outline provenance, then runs
injected whole-blueprint critics and the route-fairness specialist. One bounded
repair may be revalidated and re-reviewed. The resulting candidate envelope
records prompt/version, model metadata, source hash, diagnostics, reviews, and
repair status; it is not a runtime input or mutable authority. The
`storygame-blueprint` command is explicitly live-opt-in and never overwrites a
reviewed fixture.

Phase 4 adds an editor-reviewed Vale Mansion vertical slice at
`data/story_blueprints/v1/vale_mansion_case.yaml`. The offline artifact
declares the complete solution, initial party knowledge, bounded timeline,
evidence custody, location classes, alternate routes, and protected release
order. Its acceptance contracts prove two evidence-backed solution paths and
reject early unsupported completion. It remains an immutable authoring input;
Phase 5 realizes it into a fact-backed progression map at V2 bootstrap. A
turn can propose only a declared `route_id` with optional `evidence_ids`; local
progression policy validates current route availability and revelation/evidence
conditions before atomically committing facts. Bare completion tags are
rejected for blueprint-backed sessions, and the prompt receives only
observer-earned facts and legal route metadata.

Grounded-turn-contract Phases 0–4 have audited the V1 and V2
proposal/rendering boundaries, recorded the adapter-wide provider-call and
in-process latency baseline, and closed the generic material-staging path.
Ordinary V1 freeform turns carry typed `staging_claims`, checked only against
candidate facts after validated effects. Story packages declare fact-backed
environment transitions, bounded dramatic consequence classes, route blocks,
and evidence recoveries; validation rejects an unwinnable fully blocked route.
The planner receives only observer-scoped claim/effect choices, distinguishes
atmosphere from material staging, and renderers receive prose only after the
atomic commit accepts it. The same contract is exercised by mystery, fantasy,
sci-fi, and relationship sessions without a runtime genre branch. Accepted
planner turns project locally generated request IDs, retries, latency,
rejection codes, and outcome into committed event metadata, integrity-checked
save traces, and hosted-demo response headers; exhausted failures stay
uncommitted. These behaviors remain covered by the typed runtime and adapter
regression suite.

## Offline storylet compiler Phase 4: proposal, validation, and commit

`TurnResult` may carry one optional, typed `storylet_realization`: a reviewed
storylet ID, one of its declared realization modes, authorized consequence IDs,
and declared completion or abort evidence. The field is strict at the untrusted
JSON boundary and cannot carry runtime paths or arbitrary fact mutations.

The clone-first runtime policy rechecks the selector's current fact snapshot,
participant/location availability, mode, consequence authorization, outcome
evidence, and failure-forward declaration before it writes anything. Accepted
consequence templates become `knows(player, truth)` fact operations, while
selection, completion, abort, discovery, and recent-use markers are canonical
facts. An aborted storylet records its declared alternatives as discovered;
the renderer receives narration only after that atomic candidate succeeds.

Unselected freeform turns retain the ordinary proposal/commit contract. The
engine's pacing update recognizes committed storylet completion or abort facts,
not a model-supplied dramatic tag. The shared save projection persists these
facts with its usual integrity check, and `storygame.web_demo` remains a thin
consumer of the unchanged runtime response.

## Offline storylet compiler Phase 5: deterministic simulation

`storygame.authoring.storylet_simulation` is an authoring-only harness for a
reviewed `RuntimeNarrativeProjection`. It invokes the existing read-only
`StoryletSelector` and clone-first `validate_and_commit` policy directly; it
does not call a provider, render prose, or gain an alternate mutation path.
Six generic legal play styles—goal-focused, exploratory, social, avoidant,
aggressive, and chaotic—start from independent runtime states.

The versioned `storylet-simulation-v1` report records ending reachability, dead
ends, revelation order, storylet reuse, selection diversity, pressure
trajectories, blocked-action rate, distinct climax paths, and protected-
revelation violations. Reports must end in `.simulation.json`, are immutable
once written, and are non-runtime evidence: they can inform source Brief,
compiler-contract, and editorial changes but can never become a playable
package or state authority. The cross-genre regression exercises the same
generic harness for mystery, fantasy, sci-fi, and relationship profile labels.

## Fact authority, inventory, clues, and documents

`storygame.runtime.facts` provides the minimal canonical fact layer beneath
`RuntimeState`. A frozen `Fact` is an assertable or retractable predicate with
typed subject, object, and optional value; `FactStore` owns the mutable set and
provides deterministic matching and JSON serialization. Supported policy
families cover identity, role, location, presence, custody, possession,
knowledge/unknown boundaries, discovered clues and leads, active goals/tasks,
scene objectives, relationships, NPC availability, item affordances, and flags.

Bootstrap derives these facts from compiled-story opening metadata, item
definitions, and the initial world declaration. `world.items`, inventory,
flags, location, and discovery attributes remain compatibility projections;
they are synchronized only while a cloned candidate passes
`validate_and_commit`.

Fact writes use the typed `StateOperation` boundary with `facts: add/remove`
operations. Custody is cardinality-one per item, and a transfer to the player
is legal only when the current holder is in the scene. Unknown items,
unsupported fact families, malformed facts, and unavailable items fail closed
without changing the prior state. The same fact set is serialized in the
versioned integrity-checked SQLite snapshot and restored on load.

Readable documents are declared through `ItemDefinition` and
`ReadableDocument`. A `DocumentDisclosure` names the document, addressed
speaker, and one declared fact. Runtime validation requires the speaker to be
present, permitted for that document/fact, and to know the fact; the player's
knowledge fact is committed before the response is rendered. Already-known
facts, wrong speakers, unavailable speakers, and non-readable items are
rejected. No package lookup or narration text can create a clue or disclosure.

## Dialogue and freeform action parity

`DialogueProposal` is the typed runtime boundary for NPC speech. It carries an
addressed `target_id`, matching `speaker_id`, a bounded list of permitted fact
ids, player-visible dialogue, and bounded `StateOperation` effects. Validation
requires the target to be present in the current scene and explicitly named or
otherwise unambiguously addressed by the player. The speaker must match the
target and possess every permitted fact. Prompt parroting and narrator-style
speaker substitution are rejected with typed fail-closed errors.

Dialogue effects are applied to a cloned candidate through the same atomic
fact/compatibility-view commit path as ordinary turns. Only after that commit
does the engine project the NPC's dialogue as the response. Protected
revelations are checked against both narration and dialogue, so spoken prose
cannot become an alternate knowledge authority.

Ordinary freeform play remains model-interpreted. The runtime only normalizes
unambiguous declared movement and visible-item affordances such as inspect and
take; those normalized intents still become bounded state operations and pass
local validation. It does not replace story interpretation with a fixed action
table. Ambiguous or unavailable targets/items remain model proposals and are
validated or rejected at the same boundary. The normal turn still permits one
provider request plus one bounded recovery request.

## Goals, dramatic state, and progression

`CompiledStory` carries generic progression metadata: `goals`, `tasks`,
`clues`, `scene_purpose`, `dramatic_question`, `initial_pressure`,
`relationships`, `timed_events`, and `endings`. These are immutable reviewed
authoring inputs. Cross-reference validation rejects tasks without a declared
goal, endings with unknown beats, and duplicate timed-event IDs.

Bootstrap realizes the declarations into `RuntimeState.facts`: goals and task
status, clue declarations, relationship assertions, scene purpose, dramatic
question, and scene pressure. The context builder projects declarations beside
current fact-backed pressure so the model can frame choices without gaining a
mutation authority. Beat order and pacing remain advisory projections over
facts, not a competing progression store.

At the atomic commit boundary, due timed events assert their declared facts,
record an `event_fired` fact, and apply bounded pressure changes. Each event
fires once, and all event effects are discarded with the candidate if the turn
is rejected. Ending declarations describe valid and failure-forward outcomes;
they do not force a player action or fabricate completion.

The Phase 4 contract is exercised across mystery, fantasy, sci-fi, and
relationship fixtures with the same runtime policy families and no genre branch.

## Persistence, artifacts, and replay

Runtime snapshots use the `runtime-state-v3` schema. The SQLite adapter stores
the compiled-story identity and hash beside a canonical JSON snapshot and its
SHA-256. The snapshot carries its own schema marker; unsupported versions,
invalid JSON, malformed payloads, story mismatches, and hash failures are
typed `RuntimeSaveError` failures before any state is rehydrated. A snapshot is
therefore a restart input, never a competing authority.

`storygame.persistence.story_state` provides the artifact projection boundary.
`artifact_bundle(state)` derives `StoryState.json`, `STORY.md`, `trace.json`,
and `transcript.json` from the current facts and accepted `RuntimeEvent`
decisions. It does not load a projection to reconstruct state. The JSON state
projection includes the fact set, accepted decisions, turn index, and a
compiled-story identity; the Markdown summary is a presentation projection;
trace and transcript data retain deterministic decision and narration evidence.

Every projection is covered by a versioned `manifest.json` containing stable
SHA-256 hashes. `verify_artifact_manifest` rejects missing or changed files,
and `verify_replay_signature` rejects replay evidence whose accepted decisions
have changed. `write_artifacts` uses temporary files followed by replacement,
so an orchestrator can regenerate a complete artifact directory after a
restart. The optional hosted-adapter `artifact_root` writes one projection
directory per session after bootstrap and each accepted turn; runtime requests
never consult those files for decisions.

Phase 5 regression coverage proves fact and event projection parity, artifact
corruption rejection, deterministic manifests, replay signatures, and the
existing hosted process-restart/load path. The runtime remains the sole
mutable authority; artifacts are integrity-checked evidence and projections.

## Hosted adapter and release parity

`storygame.web_demo` is the only player-facing application surface. The
authoring CLI remains offline-only, and no V1 runtime or rollback route is
reachable from the hosted adapter. The hosted contract is deliberately small:
`GET /api/v1/health` reports `status`, `runtime`, `channel`, and immutable
`sha`; `GET /api/v1/version` reports `api: v1` plus the same runtime/channel/SHA
identity; `POST /api/v1/session`, `POST /api/v1/session/load`, and
`POST /api/v1/turn` carry the typed session, state, narration, and fail-closed
runtime responses.

The static Pages client checks the version contract before opening a session,
uses the channel-specific API origin, and shows a non-production badge only for
staging/development bundles. The API and Pages bundles are independently
stamped with the same tested SHA; staging rejects identity mismatches before
publishing its deployment status. Production is a manual, protected-environment
promotion of a successful staged SHA, with isolated Railway namespaces and a
post-promotion hosted smoke test. The root Pages channel is production and
`/dev/` is staging; deployment assembly preserves the opposite channel rather
than replacing it.

Phase 6 release evidence is operational rather than a new runtime authority:
the staging evaluation artifact, deployment status, Pages `deployment.json`,
health/version responses, and production promotion record document the release
without becoming inputs to gameplay.

## Goals
- Deliver a playable hosted web IF experience.
- Keep world-state progression deterministic and replayable.
- Let LLMs drive ordinary in-scope story progression, NPC dialogue, and turn framing inside deterministic safety rails.
- Improve narration quality via bounded, reproducible coherence workflows.
- Persist canonical artifacts with traceability and integrity enforcement.
- Enforce explicit typed contracts at agent boundaries.

## Project Layout
```text
.
├── storygame/
│   ├── authoring/
│   ├── persistence/
│   ├── runtime/
│   └── web_demo.py
├── frontend/
├── tests/
├── .plans/
├── .github/workflows/
├── runs/
├── Makefile
├── pyproject.toml
└── README.md
```

## Tool Stack
- Language/runtime: Python 3.12
- Package/runtime tooling: `uv`
- Web/API: FastAPI + Uvicorn
- Testing: pytest + pytest-cov
- Linting/format rules: Ruff
- Persistence: SQLite runtime snapshots plus integrity-checked artifact projections

## Architecture Overview

### V2 standalone runtime

`storygame.runtime` is independent of V1 facts, predicate policies, parser
execution, plot selection, and packages. A compiled story bootstraps one
`RuntimeState` containing world state, per-beat runtime data, turn index,
recent events, and rolling summary. It is the sole mutable authority.

Each `RuntimeEngine.turn` builds a bounded context from that state, calls an
injected turn model in explicit JSON-object mode, locally parses a `TurnResult`,
validates a cloned state, then atomically replaces the state only on success.
JSON-mode rejection, malformed output, schema failure, and model errors share
one recovery budget: at most two inference requests. Failed recovery returns a
typed error and retains the prior state unchanged. Narration is never an input
to mutation.

The minimal validator permits only schema-defined set/add/remove operations,
enforces unique item custody, protected-revelation boundaries, monotonic beat
completion and prerequisite order. `PacingController` supplies advisory
`open`, `nudge`, `advance`, `escalate`, and `force_consequence` directives;
even the hard limit does not prescribe the player action. Runtime events carry
the prompt version and token estimate for traces.

### Runtime boundaries

- `storygame.authoring` owns immutable source selection, blueprint contracts,
  provider normalization, local validation, candidate review/promotion, audits,
  and deterministic simulations. Authoring artifacts never mutate a session.
- `storygame.runtime` owns `RuntimeState`, canonical `FactStore`,
  untrusted `TurnResult` parsing, context construction, pacing, proposal
  validation, and atomic turn commit.
- `storygame.persistence` owns the versioned SQLite snapshot and
  integrity-checked artifact projections. Projections never reconstruct truth
  except through the explicit snapshot restore boundary.
- `storygame.web_demo` is the hosted adapter. It selects reviewed fixtures,
  constructs sessions, maps typed runtime failures to HTTP responses, and may
  write artifacts after accepted state changes.

Dependencies cross those boundaries through typed models or injected
transports. The hosted adapter does not gain a second turn policy, and the
offline compiler does not become a runtime dependency.

### Turn lifecycle

`RuntimeEngine.turn` builds observer-scoped context, recognizes only
unambiguous movement or visible-item affordances, and still expresses those
affordances through typed `StateOperation` values. The injected `TurnModel`
receives an explicit `json_object` option. `TurnResult.from_provider`
normalizes supported envelopes and validates the local contract.

`validate_and_commit` applies a proposal to a cloned state. It enforces
allowed paths and fact families, custody cardinality, visible transfer,
addressed-speaker presence and identity, permitted knowledge, protected
revelations, beat order, storylet eligibility, and declared consequence
effects. Only a fully valid candidate replaces `RuntimeEngine.state`.
Narration or dialogue is rendered after that commit.

A normal turn makes one inference request. JSON-mode rejection, malformed
output, validation failure, and transport failure share one recovery request;
exhaustion returns `RUNTIME_RECOVERY_EXHAUSTED` and leaves state unchanged.

### Fact and context projection

`bootstrap_runtime_state` seeds the player location, declared opening
contacts, public roles and knowledge, item custody/affordances, goals, tasks,
clues, relationships, pressure, and reviewed storylet markers into
`RuntimeState.facts`. Compatibility views in `WorldState` are projections
updated only at the validated commit boundary.

`RuntimeContextBuilder` exposes the current location, visible world
projection, player-visible facts, recent events, pacing directives, legal
progression routes, and at most three eligible storylets. Protected truth
summaries remain filtered until their release facts are committed.

The current causal-blueprint bridge deliberately does not yet project general
participant placements, scene subjects, evidence realization/custody, or group
encounters. The Phase 0 spatial audit measures that loss; later phases must add
declarative contracts rather than a runtime inference fallback.

### Persistence and artifacts

`RuntimeStateSqliteStore` writes and restores versioned, hash-checked runtime
snapshots bound to the compiled-story identity. Invalid schema versions,
malformed payloads, story mismatches, and hash failures raise
`RuntimeSaveError` before state is returned.

`artifact_bundle` derives `StoryState.json`, `STORY.md`, `trace.json`,
and `transcript.json` from accepted facts and events. `manifest.json`
contains stable SHA-256 hashes; replay signatures bind accepted decisions.
`write_artifacts` is orchestrator-owned, and runtime policy never reads these
files as a mutation authority.

### Hosted API

`storygame.web_demo:create_demo_app` serves:

- `GET /api/v1/health`
- `GET /api/v1/version`
- `POST /api/v1/session`
- `POST /api/v1/session/load`
- `POST /api/v1/turn`

Sessions have explicit TTL and turn limits. Save slots are session-scoped.
CORS, per-IP rate limits, and deployment channel/SHA identity are adapter
concerns. Missing provider configuration and exhausted model failures fail
closed with typed client responses.

The static `frontend/` client verifies the deployed API identity and uses the
channel-specific origin. Root Pages is production; `/dev/` is staging.

## Environment Variables

### Offline authoring

- `OPENAI_API_KEY` is required only for a live compiler request.
- `FREYTAG_ENABLE_LIVE_COMPILER=1` and `--live` are both required.
- `--quality-tier preferred|minimum` selects the reviewed compiler model;
  `--debug` selects the non-promotable low-cost path.
- `OPENAI_BASE_URL` optionally selects a compatible Responses endpoint.

### Hosted turn model

- `CLOUDFLARE_WORKER_URL`
- `CLOUDFLARE_WORKER_TOKEN` (optional when the Worker is unauthenticated)
- `CLOUDFLARE_TIMEOUT`

The Worker contract and structured-output recovery details live in
[Cloudflare V2 turn-model contract](cloudflare-narration-worker.md).

### Hosted service and frontend

- `FREYTAG_DEPLOYMENT_CHANNEL`
- `FREYTAG_DEPLOYMENT_SHA` (written by deployment automation)
- `DEMO_CORS_ALLOW_ORIGINS`
- `SESSION_TTL_SECONDS`
- `SESSION_TURN_CAP`
- `IP_RATE_LIMIT_PER_MIN`
- `IP_DAILY_TURN_CAP`
- `VITE_STAGING_API_BASE_URL` and `VITE_PRODUCTION_API_BASE_URL` in the
  corresponding deployment environments

## Developer Workflow

```bash
uv sync --group dev
uv run pre-commit install
TMPDIR=/tmp uv run pytest -q
uv run ruff check --fix .
uv run ruff format .
```

The required CI coverage job runs the full suite with two workers, branch
coverage, a 90% project floor, and a machine-readable health report. Fast
feedback and cutover-contract jobs are additional gates, not substitutes for
the coverage run. Collection totals remain informational.

## Implementation Guardrails

- Facts are the sole mutable runtime truth.
- Ordinary gameplay remains model-proposal-first; only explicit control input
  and unambiguous declared affordances may normalize locally.
- Every provider response is untrusted and locally typed before commit.
- A normal turn has one request plus at most one shared recovery request.
- No shared runtime behavior may branch on a story ID, character, genre, or
  mystery premise.
- Opening, movement, dialogue, storylet, persistence, and hosted projections
  must agree with committed facts.
- Generated candidate and reviewed artifacts are immutable inputs. Correct
  authoring sources or compiler contracts, then regenerate; never hand-edit an
  artifact projection.
