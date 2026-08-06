# Freytag Forge Combined Refactor Plan

## Decision

Use the repository-specific architecture plan as the migration chassis and
delivery sequence. Extend it with the tiered plan's missing world-simulation,
epistemic, NPC, and evaluation capabilities.

The desired result is an interactive-fiction engine that is:

- story-first and LLM-proposal-first for every ordinary player turn;
- deterministic and fact-backed for all canonical world changes;
- rich enough to support consequences, discovery, knowledge, and persistent
  NPC behavior across more than one genre;
- fast enough to use one story-model call on the normal turn path; and
- evaluable with deterministic invariants as well as repeatable play fixtures.

This is an in-place strangler refactor, not a greenfield rewrite. Preserve the
fact store, validated commit boundary, persistence, replay, triggers, typed
contracts, and separate `web` / `web_demo` adapters. Replace only the layers
that leave game semantics in prose, unrestricted fact proposals, parser-era
actions, or fallback metadata.

## Superseded Plan Material Incorporated Here

This plan absorbs the useful parts of the retired `forge.md`, `webui.md`, and
`world_builder.md` plans:

- from **Forge**: typed agent boundaries, deterministic pre-render validators,
  durable traceable artifacts, bounded recovery, debug diagnostics, and
  repeatable evaluation;
- from **Web UI**: separate local and hosted surfaces, Cloudflare-backed hosted
  narration, versioned demo API, static client, CORS/session/quota controls,
  typed fail-closed responses, and deployment observability; and
- from **World Builder**: genre/tone/session inputs, outline/curve selection,
  structured world packages, declarative authoring data, stable/adaptive NPC
  traits, and local replanning that maintains alternate progress paths.

The following assumptions are explicitly rejected: `STORY.md` as canonical
runtime truth; a multi-critic/judge loop on ordinary turns; a big-bang rewrite;
and parser-known-command-first routing. Facts remain canonical, normal turns
remain proposal-first, and critics are authoring/evaluation tools rather than
fast-path turn dependencies.

## Non-Negotiable Product Rules

1. Ordinary turns remain LLM-proposal-first. Parser handling is limited to
   `save`, `load`, `quit`, and `help`; deterministic direction, inventory, and
   item aliases normalize into the shared proposal/commit contract.
2. The player may attempt any story move. The engine validates a bounded
   consequence, asks for clarification when needed, or uses the existing
   confirmation-and-replan path only for irreparable goal breaks. It must not
   substitute a command table for story interpretation.
3. Facts are the sole canonical mutable truth. Object views, `world_package`,
   active-goal strings, and prose are projections or inputs, never competing
   runtime authorities.
4. LLMs propose framing, dialogue, semantic intent, and bounded consequences.
   Deterministic policy validates and commits accepted deltas before final
   narration is displayed.
5. The LLM receives only observer- and speaker-permitted context. Narration
   and dialogue may not establish uncommitted state, leak protected knowledge,
   or replace a directly addressed NPC's reply with a summary.
6. Preserve the different local and hosted-demo credential/backend contracts.
   Shared code belongs below their adapter boundary.
7. `StoryState.json`, `STORY.md`, debug traces, and transcripts are
   integrity-checked, orchestrator-written projections of canonical facts and
   accepted decisions. They never become a second mutation authority.

## Current Foundation and Migration Status

The architecture-plan migration remains the authoritative record for completed
work. Retain its completed phases rather than recreating them:

- validated canonical commits and invariant validation;
- fact-backed scene and dramatic state;
- `TurnProposalV2` and ordinary-turn proposal execution;
- fact-first, validator-first bootstrap/opening behavior.

Before beginning new work, verify those claims with the full test suite and a
short architecture audit. Do not weaken them while extending the engine.

## Authoring, Runtime, and Artifact Boundaries

- Authoring inputs include player-selected genre, optional tone, and session
  length; outline and curve templates select a structured world package.
- Static authoring data may define predicate schemas, rule packs, and NPC role
  defaults. It is validated at package-load time; it cannot authorize arbitrary
  runtime predicate invention or bypass fact policy.
- Runtime state consists exclusively of canonical facts plus deterministic RNG,
  logs, persistence handles, and read-only projections.
- `StoryState.json` and `STORY.md` are emitted only by the orchestrator. Each
  turn records parent linkage, artifact hashes, command/proposal identity,
  accepted decision metadata, and the committed fact delta. Tampering or a
  failed round-trip is rejected and logged.

## Target Turn Model

```text
player input
  -> control-plane classification, or one LLM TurnProposalV2
  -> deterministic intent/entity resolution and policy validation
  -> canonical fact commit of direct effects
  -> deterministic consequences, knowledge/perception updates, triggers,
     dramatic policy, and timed events
  -> narration/dialogue rendered from the resulting permitted fact slice
  -> persistence and replay artifact
```

Action policy is a validator and commit authority, not a command router. The
LLM may propose a novel action; policy maps it to a bounded supported effect,
asks for clarification, or records an attempted-but-unsuccessful action. It
must never force normal play through a fixed verb list.

## Phase 0 — Baseline, Contracts, and Evaluation Fixtures

### Work

- [x] Record test, coverage, latency, LLM-call-count, and replay baselines in
  `docs/evaluation-baseline.md`.
- [x] Create deterministic vertical-slice packages for at least:
  - mystery investigation;
  - fantasy/adventure journey;
  - science-fiction technical crisis; and
  - relationship-driven social scene.
- [x] Define transcript-independent failure categories: contradiction, impossible
  action, hidden-information leak, role drift, causal omission, uncommitted
  narration, repetitive scene pressure, and blocked player agency.
- [x] Freeze the model, prompt version, generation settings, and seeds used for
  behavioral evaluation.

### Tests and exit criteria

- [x] The existing suite passes with project coverage at or above 90%.
- [x] Every fixture can initialize, save, load, and replay deterministically.
- [x] Evaluation assertions classify failures from structured artifacts, not only
  subjective transcript review.
- [x] Baseline ordinary-turn LLM-call count and latency are recorded for local and
  hosted-demo surfaces separately.

## Phase 1 — Close the Fact-Authority Migration

### Work

- [x] Audit remaining mutation sites in rules, story bootstrap, CLI, web adapters,
  simulation, and persistence.
- [x] Route each canonical mutation through `ValidatedFactCommitter` (or its
  explicit successor) with a source label and typed operation contract.
- [x] Demote `GameState` objects, `active_goal`, and `world_package` fields to
  read-after-commit projections or bootstrap/presentation data.
- [x] Remove ordinary-path fallback reads from legacy views and package payloads.
  Remaining package reads are authoring compatibility inputs; semantic turn
  execution reads facts.
- [x] Preserve temporary projections only behind explicit adapter Protocols, with
  projection refresh occurring after successful fact commits.
- [x] Preserve deterministic artifact write/read validation and turn-to-turn parent
  hashes while changing artifact payloads to derive from facts alone.

### Tests and exit criteria

- [x] Player/NPC location, item container/custody, active goal, role exclusivity,
  clues, event flags, and scene state have cardinality/invariant tests.
- [x] No ordinary turn begins by rebuilding canonical facts from mutable legacy
  views.
- [x] Save/load and artifact rendering read the same fact-backed state as runtime
  execution.
- [x] Each persisted turn has one valid, tamper-evident `StoryState.json` and a
  regenerated `STORY.md`; both round-trip across process boundaries.

## Phase 2 — Predicate Policies and Bounded Intent Effects

### Work

- Add predicate-family policies for world truth, perception, knowledge,
  relationships, tasks, traces, and dramatic state.
- Specify for each protected predicate: legal commit sources, invariants,
  normalization, and derived-update owner.
- Evolve `TurnProposalV2` so it expresses player intent, references, candidate
  semantic effects, dialogue, narration claims, and beat hints in one typed
  contract.
- Add deterministic intent-effect policies for movement, examination,
  communication, manipulation, transfer, concealment, assistance, opposition,
  and waiting. These are extensible policy families, not parser command names.
- Resolve unique visible shorthand (for example, `take key`) deterministically
  at the boundary; reject ambiguity with a story-appropriate clarification.
- Load declarative core and genre predicate/rule packs through typed authoring
  schemas. Rule precedence and conflicts must resolve deterministically before
  a package can be played.

### Tests and exit criteria

- Unauthorized LLM state deltas are rejected without mutating facts.
- Valid novel phrasings map to the same bounded intent effects as equivalent
  phrasings without relying on a parser route.
- Invalid or impossible attempts preserve truth and yield an LLM-authored,
  fact-consistent outcome when a valid proposal is available.
- No central conditional chain is required to add a policy family.
- Invalid package schemas and rule conflicts fail before session creation, with
  no partial state realization.

## Phase 3 — Perception, Discovery, and Information Boundaries

### Work

- Implement an observer-aware resolver that distinguishes existence, location,
  accessibility, perceptibility, observation, recognition, and interpretation.
- Add canonical predicates and rules for concealment, exposure, environmental
  conditions, traces, portals, sensory propagation, and discovery.
- Build model context from the current observer's permitted slice only.
- Add a speaker-specific context slice for NPC dialogue; global case truth
  must not be implicitly available to the speaker.
- Allow evidence to move, be contaminated, be lost, be transformed, and be
  reinterpreted through validated facts.

### Tests and exit criteria

- Hidden information is absent from player and unrelated-NPC prompts, rather
  than merely discouraged in instructions.
- Rain/lighting/trace and similar environmental facts persist coherently across
  adjacent rooms and perception modes.
- Discovery, custody, and room placement cannot form contradictory states.
- Required clues or equivalent paths remain reachable in every fixture.

## Phase 4 — Consequence and Affordance Engine

### Work

- Add a deterministic post-direct-effect consequence pass before triggers and
  final dramatic policy.
- Represent reusable causal rules for material/environmental properties,
  access paths, character condition, social stance, and information exposure.
- Keep universal rules separate from story-package rule data. Authoring models
  may propose rule packs offline, but executable rules require schemas,
  validation, and tests.
- Generate affordance context from currently legal state; do not rely on
  hard-coded story regexes or model memory of prior prose.

### Tests and exit criteria

- Direct actions produce persistent, logically connected downstream facts.
- Physical, social, investigative, and technical fixtures each exercise the
  same consequence machinery.
- Consequences are deterministic, independently testable, and do not require
  prose extraction to become canonical.

## Phase 5 — Knowledge, NPC Roles, and Delegated Work

### Work

- Model what each important character knows, believes, suspects, conceals, and
  may infer.
- Create fact-backed NPC role contracts: goals, capabilities, limitations,
  initiative policy, relationship, advisory style, and permitted autonomous
  behavior.
- Express stable identity traits separately from bounded adaptive traits. The
  latter may change only through declared policy and retain a small typed
  presentation projection for narration stability.
- Add a deterministic task/commitment lifecycle for offers, acceptance,
  progress, results, failure, cancellation, and consequences.
- Validate NPC actions by knowledge, role, location, resources, obligations,
  visibility, and current scene/dynamic state.
- Keep dialogue LLM-authored from the addressed NPC's context and reject
  parroting, wrong-speaker, off-scene, or role-violating proposals.

### Tests and exit criteria

- NPCs do not disclose facts they cannot know or perform work they cannot
  plausibly do.
- Directly addressing a visible NPC returns that NPC's in-character reply.
- Delegation is distinct from dialogue, hints, and autonomous activity and is
  durable across save/load.
- At least a companion, rival, adviser, medic, and navigator role are proven
  through shared machinery across fixtures.

## Phase 6 — Fact-Driven Freytag Policy

### Work

- Complete the existing fact-backed dramatic-state migration with a
  deterministic `BeatPolicy`.
- Use phase, beat role, scene pressure, obstacle mode, active conflict,
  reveal opportunity/budget, and NPC scene goals as policy inputs.
- Move reveal scheduling and timed progression from `simulation.py` fallback
  chains to fact-driven services.
- Let validated player consequences alter pressure, available reveals, and
  NPC stance within phase legality; do not prescribe player choices.
- Retire progress/tension as commit authorities after they are derived metrics.

### Tests and exit criteria

- Beat phase and role measurably alter legal escalation, reveal timing, scene
  framing, and consequence classes.
- Deterministic policy avoids random/repetitive beat selection while retaining
  varied player approaches.
- Major goal-breaking actions follow explicit confirmation, state disruption,
  replan, and then official response to the original prompt.
- Local replans preserve the curve constraints and current player agency while
  adding or reopening valid evidence/progression paths where necessary.

## Phase 7 — Post-Commit Rendering and Hot-Path Cleanup

### Work

- Render narration and NPC dialogue only from committed facts plus permitted
  framing; structured claims must cover any visible state change.
- Keep opening/bootstrap as structured fact proposal -> validation -> commit ->
  prose validation. Accepted prose never repairs truth after display.
- Reduce the normal path to one LLM call and allow at most one bounded
  revision call for contract-invalid or deterministically repairable output.
- Remove normal-turn critic/extractor/editor passes, obsolete parser-era
  fallbacks, and stale compatibility branches when covered by tests.
- Split surface plumbing into gateway, orchestration, rendering, and
  persistence responsibilities where this makes call flow clearer.
- Preserve hosted-demo fail-closed behavior and backend differences.
- Preserve the local `GET /` + `POST /turn` interface and the hosted demo's
  `GET /api/v1/health`, `POST /api/v1/session`, and `POST /api/v1/turn`
  contract. The static client remains a separate consumer of the versioned API.
- Keep hosted guardrails: CORS allowlisting, session TTL, session turn cap,
  per-IP short-window and daily limits, request timeouts/token ceilings, and
  distinct `rate_limited`, `quota_exhausted`, and `service_unavailable`
  responses.

### Tests and exit criteria

- Ordinary turns make one LLM call on the fast path and two at most on
  recovery; tests assert this.
- Narration cannot introduce an item, location, relationship, or revelation
  without a matching accepted commit.
- Local and hosted surfaces retain their valid deployment differences while
  sharing parity-tested contracts below the adapter boundary.
- Total story-agent latency is under ten seconds per normal turn at the chosen
  deployment target.
- API lifecycle, adapter retries/timeouts, quota/error envelopes, static-client
  bootstrap, and deployment health checks have automated coverage. Telemetry
  records turn latency, model-call count, retries, quota events, and failures
  without exposing internals to players.

## Phase 8 — Story Construction and Playability Evaluation

### Work

- Use an offline frontier-model pipeline to generate structured story packages
  containing characters, motivations, world rules, secrets, revelations,
  causal assumptions, role contracts, beat plans, and ending conditions.
- Validate packages deterministically for reachability, clue/revelation paths,
  character availability, causality, and ending viability before play.
- Run frontier critique only at authoring/evaluation/replan boundaries, not as
  ordinary-turn scaffolding.
- Run specialist continuity, causality, and dialogue-fit critiques in parallel
  during offline evaluation; use one deterministic judge only to aggregate a
  versioned weighted rubric with critical-dimension floors.
- Bound evaluation/replan recovery by explicit round, token, and wall-clock
  budgets. If a recovery candidate is required, record preserved, modified, and
  discarded fact categories and revalidate it end-to-end.
- Run scripted exploratory, goal-focused, social, adversarial, avoidant, and
  chaotic players against every fixture; make failures regression artifacts.

### Tests and exit criteria

- Every fixture reaches at least one valid ending under multiple play styles.
- Required information has more than one plausible acquisition path where the
  story design calls for resilience.
- Frontier critique finds no unresolved critical causal, motivational, or
  fairness defect before a package is accepted.
- Local-model evaluations report direct-validity, repair rate, contradiction,
  leakage, role drift, latency, and token usage.
- Deterministic invalid-turn fixtures have complete rejection coverage, and
  fixed-seed artifact/transcript checks remain stable outside permitted
  nondeterministic display metadata.

## Phase 9 — Cutover, Simplification, and Decision Gates

### Work

- Make the new runtime default only after the fixture/evaluation gate passes.
- Delete superseded freeform, semantic-action, narration-extraction, and
  parser-authoring paths rather than retaining permanent wrappers.
- Document fact policies, proposal contracts, adapter boundaries, latency
  budgets, story-package schema, and authoring/model-tier policy.
- Add CI enforcement for tests, branch coverage, linting, deterministic
  fixtures, selected behavioral-evaluation reports, API smoke tests, and
  artifact-integrity checks.

### Decision gates

Evaluate after Phases 4, 5, and 7. Continue only when:

- mechanisms work across at least two genres without story-specific engine
  branches;
- tests become more deterministic and understandable;
- legacy code is being removed rather than accumulated behind adapters;
- accepted model output is validated rather than trusted; and
- agency, coherence, and latency all improve against the Phase 0 baseline.

Consider a focused subsystem rewrite only if the same gate fails repeatedly
because the existing fact/commit boundaries cannot express the required rules.

### Final exit criteria

- One canonical runtime supports CLI, local web, and hosted demo adapters.
- Project-wide coverage remains at or above 90%.
- Canonical mutations, persistence, and replay are fact-authoritative.
- Ordinary play remains proposal-first, responsive, and not command-parser
  shaped.
- The genre-diverse fixtures demonstrate fair discovery, causal persistence,
  stable NPCs, meaningful player agency, and coherent endings.

## Delivery Order

Implement in this order: Phase 0, audit remaining Phase 1 work, Phases 2–5,
Phase 6, Phase 7, then Phases 8–9. This preserves the architecture plan's
completed safety work, establishes the world rules that make play fun before
polishing dramatic pacing, and defers latency/cutover work until the final turn
contract is stable.
