# LLM-first runtime refactor plan

## Decision record

This plan deliberately replaces the current fact-backed, predicate-policy runtime
with a smaller LLM-first runtime. It supersedes the conflicting runtime claims in
the README, PRD, fact-authority documentation, evaluation baseline, and
contributor rules as part of the migration. It does not retain a compatibility
layer for facts, semantic actions, deterministic consequences, triggers,
perception, or deterministic beat selection.

The retained product is the hosted demo. `storygame.web`, the CLI, and their
local/deployment parity machinery are retired. The only public application
adapter after cutover is the current hosted-demo surface, rebuilt over the new
runtime.

The release topology follows PhaserForge's channel-promotion model, with the
URLs requested for this project:

```text
successful main CI
        |
        +--> staging: Pages /dev/ + Railway staging API (new candidate)

manual promotion of the tested SHA
        |
        +--> production: Pages / + Railway production API (user-facing)
```

During the migration, production continues to run the last promoted legacy
revision while `main` and `/dev/` run the new runtime. This is deployment-level
versioning, not two runtime implementations in the same revision. The legacy
runtime is deleted from `main` once staging can operate independently; its
already-deployed, immutable production revision remains until the first V2
promotion.

## Target architecture

### Runtime boundary

```text
player input
  -> RuntimeContextBuilder
  -> TurnModel.play_turn
  -> TurnResult parser and minimal validator
  -> RuntimeState commit
  -> event log, summary, persistence, response
```

The normal path makes one structured-output model request. One repair/fallback
request may be made only when the first response cannot be decoded or validated;
both requests share one recovery budget. A failure returns a typed error and
does not persist a partial turn.

`RuntimeState` is the sole mutable runtime authority. It contains:

```text
compiled_story
world
beat_runtime
turn_index
recent_events
story_summary
```

It replaces `GameState.world_facts` and its compatibility projections. Saves,
transcripts, and display artifacts are projections of `RuntimeState`; none may
be a mutation authority.

### Offline authoring boundary

The outline and genre profile compile into a validated `CompiledStory`:

```text
premise, central question, characters, initial world state,
required and optional beats, ending conditions, revelation protections
```

Each beat declares its Freytag phase, prerequisites, completion tags,
protections, satisfier/failure-forward guidance, unlocks, and pacing targets.
Natural-language guidance instructs the model; it is not an executable rule
language. The compiler and its contract are story-agnostic and must validate
every outline genre represented in `data/story_outlines.yaml`.

### Minimal validation boundary

The validator accepts typed `set`, `add`, and `remove` updates to approved,
schema-defined state paths. It enforces only:

- schema correctness and known entity/path references;
- cardinality for uniquely held objects and explicit alive/dead transitions;
- protected revelations in player-visible narration and updates;
- monotonic required-beat completion, prerequisite order, and ending order;
- atomicity: all accepted updates commit together or none do.

It intentionally does not prove arbitrary causal rules, choose incidents,
derive player intent, run predicates, or interpret narration as state changes.

### Pacing boundary

`PacingController` calculates a `PaceDirective` for active beats from per-beat
turns active, turns without material progress, and the compiled pacing targets.
Its only modes are `open`, `nudge`, `advance`, `escalate`, and
`force_consequence`. The LLM chooses the concrete incident and must not dictate
the player's action. A `BeatUpdate` reports progress with supporting evidence;
completion occurs only when the update sets a declared completion tag and the
beat's prerequisites are complete.

### Hosted deployment boundary

There are two isolated channels, not two variants of one database:

| Concern | Staging | Production |
| --- | --- | --- |
| Pages URL | `/freytag-forge/dev/` | `/freytag-forge/` |
| API | dedicated Railway staging origin | dedicated Railway production origin |
| database/files | disposable staging SQLite volume | independent production SQLite volume |
| sessions | staging namespace/cookie configuration | production namespace/cookie configuration |
| deployment | automatic after passing `main` CI | manual, SHA-pinned promotion |

The Pages artifact always contains both `index.html` at its root and `dev/`.
An automatic staging deployment builds `dev/` from the passing `main` SHA and
preserves the currently published root artifact. A production promotion builds
the root from the selected tested SHA and preserves the currently published
`dev/` artifact. This prevents a Pages publish from replacing the opposite
channel. The browser bundle embeds its channel's API base URL at build time.

## Non-goals

- No `runtime_v1`/`runtime_v2` feature flag or permanent compatibility path.
- No CLI or local `storygame.web` deployment surface after cutover.
- No Neo4j, GraphRAG, Mem0, vector store, generic rule engine, condition DSL,
  multi-agent runtime director, or deterministic incident selector.
- No migration of live V1 saves into V2. Existing production sessions remain
  available only on the deployed legacy production revision until promotion;
  V2 starts new sessions.

## Phased implementation

### Phase 0 — Establish the cutover and channel baseline

**Goal:** make the intended deletion and deployment topology measurable before
any runtime changes.

1. [x] Record the current production commit SHA, Railway deployment ID, Pages
   deployment ID, API origin, and rollback instructions in a release-baseline
   document.
2. [x] Add a small staged/production acceptance matrix for the four existing genre
   fixtures: opening, freeform turn, malformed-model failure, persistence
   round-trip, protected revelation, and session isolation.
3. [x] Define migration success measures: structured-output success rate, one-call
   rate, repair rate, typed-error rate, p95 turn latency, premature-revelation
   rate, continuity violations, completion rate, and user-facing session
   failures. Capture the existing measurements as comparison-only evidence;
   do not preserve deterministic replay as a V2 requirement.
4. [x] Add deployment-contract tests that assert root and `/dev/` use different API
   origins and never share a session/database configuration.
5. [x] Update the test tier map so deleted-surface tests are not silently retained
   as coverage padding.

**Exit criteria:** [x] An immutable V1 production rollback target and an explicit
V2 acceptance scorecard exist; all baseline checks pass.

### Phase 1 — Install staged and production delivery channels

**Goal:** expose a safe `/dev/` environment before moving user traffic.

1. [x] Replace the current main-to-production deployment sequence with two channel
   workflows:
   - after CI succeeds for a trusted `main` push, deploy that exact SHA to the
     `freytag-forge / staging` GitHub environment and `/dev/`;
   - provide a `workflow_dispatch` promotion requiring a full immutable SHA;
     reject branch names, a SHA not previously staged successfully, and a
     source revision that differs from the checked-out revision.
2. [x] Configure separate Railway staging and production environments/services,
   public URLs, volumes, API credentials, session signing secrets, allowed
   CORS origins, model credentials, and known-good deployment IDs. Do not copy
   production saves or secrets into staging.
3. [x] Update `railway.toml` and deployment workflows so both channels launch only
   `storygame.web_demo:app`. Ensure health/version responses identify the
   deployed SHA and `staging` or `production` channel.
4. [x] Rework the Pages workflow to build `frontend/dist/dev` for staging and the
   root bundle for production. Validate the artifact shape, preserve the
   untouched channel by retrieving the published Pages artifact, and fail
   closed if it cannot preserve a valid opposite-channel index.
5. [x] Build separate frontend API base URLs into each channel and show a persistent
   non-production badge at `/dev/`. Add an E2E check that the root bundle has no
   staging API URL and `/dev/` has no production API URL.
6. [x] Make the manual production workflow perform health and browser E2E checks
   against the root production URL before recording promotion success. Keep the
   existing legacy production deployment as rollback until V2 promotion passes.

**Exit criteria:** [x] A passing `main` SHA reaches only `/dev/` and staging;
production root remains unchanged. A manually selected test SHA can be promoted
and rolled back without changing `/dev/`.

### Phase 2 — Define and validate V2 authoring contracts

**Goal:** replace the runtime package/fact contract without touching the live
production deployment.

1. [x] Add `storygame.authoring.contracts` for `CompiledStory`, `Character`,
   `Beat`, `BeatPacing`, `CompletionTag`, and protected revelations.
2. [x] Add `storygame.authoring.compiler` and prompts that transform an outline and
   genre profile into `CompiledStory`. Reuse provider adapters only at the
   transport boundary; do not reuse runtime fact/proposal contracts.
3. [x] Define local compiler validation: stable IDs, referenced prerequisites and
   unlocks, acyclic prerequisite graph, at least one crisis/climax/resolution,
   a climax that depends on preceding required work, a resolution that answers
   the central question, valid completion tags, valid protections, and valid
   pacing thresholds.
4. [x] Add cross-genre fixtures for mystery, fantasy, sci-fi, and relationship
   stories. Test valid compilation plus each invalid condition independently.
5. [x] Create versioned, checked-in compiled-story fixtures for deterministic tests;
   live compiler-model evaluation remains opt-in and budgeted.
6. [x] Update authoring docs to identify compiled stories as immutable session input
   and remove obsolete package claims only after Phase 4 has adopted the new
   bootstrap path.

**Exit criteria:** [x] Every supported genre has a valid compiled fixture and all
compiler validation failures are local, descriptive, and non-story-specific.

### Phase 3 — Build the standalone minimal runtime

**Goal:** create the replacement engine with no dependency on V1 world facts,
policies, rules, plot selection, or parser execution.

1. [x] Add `storygame.runtime.state` with typed `RuntimeState`, `WorldState`,
   `BeatRuntime`, events, and summary structures. Bootstrap it from one
   `CompiledStory` into an explicit initial state.
2. [x] Add `storygame.runtime.contracts` for `TurnResult`, typed state operations,
   events, beat progress, and optional summary delta. Require JSON-object mode
   through an explicit adapter option and normalize all supported provider
   response envelopes before local parsing.
3. [x] Add `storygame.runtime.pacing.PacingController`; write direct unit tests for
   all directive transitions, productive turns resetting stagnation, and
   hard-limit behavior that preserves player agency.
4. [x] Add `storygame.runtime.context.RuntimeContextBuilder`, passing only current
   structured state, rolling event window, summary, active beats, protections,
   and pace directives. Keep input sizes bounded and record prompt version and
   token estimates in traces.
5. [x] Add `storygame.runtime.validation` and atomic commit logic. Validate a cloned
   state before replacing the stored state. Never update state from narration.
6. [x] Add `storygame.runtime.engine.RuntimeEngine.turn`. It performs context build,
   one model call, at most one shared-budget recovery, parse/validate/commit,
   event append, summary update, and response construction. A failed recovery
   returns a typed fail-closed error and leaves the prior state intact.
7. [x] Test schema rejection, unknown IDs/paths, unique-custody conflicts,
   protected leaks, invalid beat ordering, malformed JSON, structured/fenced
   envelopes, JSON-mode rejection, recovery exhaustion, atomic rollback, and
   one-call happy-path behavior.

**Exit criteria:** [x] V2 can run all four compiled fixtures in-process with a stub
model; all valid turns commit only through `RuntimeState`, and invalid turns
leave it byte-for-byte unchanged.

### Phase 4 — Replace hosted-demo orchestration and persistence

**Goal:** make the hosted-demo adapter the only runnable product surface.

1. [x] Refactor `storygame.web_demo` to construct `RuntimeEngine` via explicit
dependencies and expose only the session/opening/turn/health/version endpoints
needed by the frontend. Keep current quota, CORS, typed upstream-failure, and
request-ID behavior where it is independent of V1.
2. [x] Replace V1 SQLite serialization with a versioned `RuntimeState` snapshot,
event log, compiled-story identifier/content hash, and rolling summary. Verify
integrity on load. Reject V1 save schemas with a clear `unsupported_save_version`
error rather than attempting a lossy migration.
3. [x] Make every hosted session start from a compiled-story fixture/package and
persist only V2 runtime state. Enforce staging/production database and session
namespace separation at construction and in deployment configuration.
4. [x] Adapt the frontend to the retained response contract, display the returned
turn index and location from V2 state, and make its base-path handling work at
both `/` and `/dev/`. Add a visible `/dev/` banner.
5. [x] Retire `storygame.web`, CLI entry points, local-web commands, web-surface
parity code, and their tests. Remove their packaging/README references rather
than leaving dead adapters.
6. [x] Add hosted-demo API and browser tests for session creation, freeform turns,
save/load, errors, quota behavior, CORS, `/dev/` base paths, production root
base paths, and isolated channel state.

**Exit criteria:** [ ] staging serves a complete V2 browser session at `/dev/` with
no import or runtime dependency on the retired local/CLI surfaces.

### Phase 5 — Evaluate V2 on staging and tune authoring/pacing

**Goal:** establish that the simplified engine is safe and materially useful
before it replaces the existing production runtime.

**Testing labels:** **[Automated]** is reproducible in CI or a staging runner;
**[User testing]** needs human play, qualitative review, or an approval decision.

1. **[Automated]** Run the four genre fixtures and scripted player styles against staging with
fixed model/version/prompt settings. Include investigate, travel, social,
avoidant, adversarial, repeated-failure, and unexpected-action scripts.
   **[User testing]** Play at least one unscripted session in each genre to
   confirm the scripted coverage has not made the experience feel constrained.
2. **[Automated]** Evaluate protected revelations, state continuity, entity/custody validity,
beat order, completion, player agency, one-call/repair rates, latency, and
typed fail-closed errors; record the evidence alongside the exact deployed SHA.
   **[User testing]** Sample model-authored output for narrative flow, agency,
   clarity, and cross-genre fit; record the reviewer and findings with that SHA.
3. **[Automated]** Validate every proposed compiler pacing, `PacingController`,
or prompt change with a new compiled-fixture version and the full regression suite.
   **[User testing]** Tune compiler pacing defaults, `PacingController` thresholds, and runtime
prompt guidance using a new compiled-fixture version for each accepted change.
Do not add deterministic incidents or story/genre-specific runtime branches to
repair an evaluation failure.
4. **[Automated]** Require a staging soak window with fresh sessions, persistence reloads, and
browser E2E runs. Verify the staged API's channel/version endpoint matches the
candidate SHA displayed in Pages build metadata.
   **[User testing]** During the soak, manually exercise `/dev/` in a browser,
   including a new session, freeform turn, save/load, and error presentation.
5. **[Automated]** Define and verify the first-promotion gate: no critical validator or
revelation failures, no unresolved channel-isolation failures, all required
hosted checks green, and scorecard metrics acceptable relative to Phase 0.
   **[User testing]** Review the scorecard and staging evidence, then explicitly
   approve or reject the candidate SHA for production promotion.

**Implementation note (2026-08-11):** [x] The SHA-bound V2 staging evaluator,
workflow artifact, automated promotion gate, seven style scripts, and human
review procedure are implemented in
[`docs/phase-5-staging-evaluation.md`](../docs/phase-5-staging-evaluation.md).
The five Phase 5 run/approval items and the exit criterion remain unchecked
until a deployed staging candidate produces evidence and receives a human
approval; implementation tests are not staging evidence.

**Exit criteria:** **[Automated]** a documented candidate SHA has passed the
promotion gate on the isolated staging channel; **[User testing]** that SHA has
an explicit human approval for production promotion.

### Phase 6 — Promote V2 and remove V1

**Goal:** switch user traffic to V2 exactly once, then delete obsolete code.

1. [ ] **[User testing / operator]** Invoke the manual promotion workflow using the successful staging SHA. The
workflow verifies that SHA's staging evidence, checks it out exactly, deploys
the production Railway service, builds the root Pages bundle from it, preserves
`/dev/`, and runs health plus browser E2E at the root URL.
2. [ ] **[User testing / operator]** Record the production deployment ID, Pages deployment ID, SHA, model/prompt
revision, and known-good rollback target. If any verification fails, retain the
old production artifact/API and report the failed promotion without altering
the staged channel.
3. [x] **[Automated]** Delete V1 engine
modules and data: fact store/committers/predicate policies, semantic actions,
consequences, triggers/incidents, perception/epistemic inference, deterministic
beat policy/dramatic compatibility layers, V1 proposal contracts, V1 package
runtime realization, CLI/local web adapters, and obsolete tests/fixtures.
4. [ ] **[User testing / operator]** Remove V1 deployment code and temporary legacy rollback documentation after
the replacement production revision is itself recorded as the known-good target.
5. [x] **[Automated]** Update README, PRD, fact-authority, offline-authoring, evaluation, deployment,
and test-suite documentation to describe the V2 state contract, hosted-only
surface, `/dev/` staging, and SHA-pinned production promotion. Delete documents
whose only purpose was the retired architecture.
6. [ ] **[Automated locally; User testing / CI for deployed channels]** Run lint, the complete test suite with the required temporary-directory
setting, browser E2E for both channels, and the full compiler/runtime
cross-genre evaluation. Maintain at least 90% project coverage after deleted
tests and code are removed.

**Implementation note (2026-08-11):** [x] The V1 source/data/test execution
path is removed from `main`, with a regression guard in
`tests/test_v2_cutover.py`; V2-only CI and documentation are updated. Production
promotion, the observation window, deployment identifiers, root and `/dev/`
browser E2E, and the final known-good rollback record require the operator and
remain unchecked.

**Exit criteria:** [ ] root production and `/dev/` both run the one V2 runtime;
there is no V1 execution path in `main`, and documentation, tests, and CI all
describe one hosted product with two isolated delivery channels.

## Required implementation sequence

Tests precede each production change: contract tests before contracts, unit
tests before runtime modules, API/browser tests before adapter and frontend
cutover, deployment workflow tests before deployment changes, then documentation
after the accepted implementation. Each phase is independently deployable to
staging and has a rollback boundary; no phase requires a flag day.

## Risks and explicit responses

| Risk | Response |
| --- | --- |
| Pages deployments overwrite the entire site | Build both root and `dev/` in one artifact; preserve and validate the untouched channel before publishing. |
| `main` deletes V1 before V2 is approved | Keep V1 only in the immutable deployed production revision, not as a current-code compatibility path; promotion is manual and SHA-pinned. |
| Staging corrupts or exposes production sessions | Separate Railway services/volumes/secrets/origins, channel-scoped sessions, and automated isolation tests. |
| Model output mutates invalid state | Typed output, minimal local validation, clone-then-commit atomicity, one shared recovery budget, and typed fail-closed errors. |
| Simplification leaks a protected revelation | Send protections in the context, validate narration and updates locally, and block the whole turn on a violation. |
| Pace limits railroad the player | Directives describe pressure but prohibit player-action dictation; evaluation includes avoidance and unexpected actions. |
| V2 regresses quality | Do not promote until a single staged SHA passes cross-genre, persistence, isolation, performance, and qualitative scorecard gates. |
