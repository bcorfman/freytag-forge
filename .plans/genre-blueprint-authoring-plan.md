# Genre-blueprint authoring plan

## Decision

Freytag Forge will compile a raw outline into a versioned, immutable,
genre-aware **Story Blueprint** before a session starts. A blueprint records the
canonical causal structure of one story and the multiple player-facing routes
through which its required truths can be discovered. It is authoring input, not
runtime state.

At session bootstrap, validated blueprint declarations are realized as canonical
facts. During play, a small, fast runtime model receives only an
observer-scoped slice of those facts and proposes bounded intent, effects,
dialogue, and available clue/incident realizations. Existing deterministic
policy validates and commits every change. Narration remains a projection of
committed facts.

This plan extends the current fact-authoritative runtime; it does **not** adopt
the incompatible, fact-free V2 cutover described in `gpt-refactor.md`.

## Goals

- Turn every supported outline in `data/story_outlines.yaml` into a testable,
  genre-aware causal plan rather than asking the runtime model to invent canon.
- Keep the engine story- and genre-agnostic. Genre behavior belongs in validated
  profiles and blueprint data, never in named runtime branches.
- Preserve freeform play: player routes remain open; required revelations use
  soft convergence through several valid discoveries.
- Make pivotal progression evidence- or realization-backed, rather than merely
  accepting a model-supplied beat-completion label.
- Keep normal runtime turns within the existing one-request plus one bounded
  recovery budget.

## Non-goals

- A universal simulation language or unrestricted runtime rule engine.
- A single “solution” shape for every genre.
- Live LLM compilation on an ordinary player turn.
- Replacing facts with blueprint/package mutation authority.
- Retrofitting every historical outline before the contract and one vertical
  slice are proven.

## Target model

```text
story_outlines.yaml + genre profile
        │
        ▼
offline authoring LLM (large/capable; opt-in and budgeted)
        │
        ▼
StoryBlueprint (immutable JSON/YAML artifact)
        │
        ├── local schema + genre validation
        ├── causality/revelation-path evaluation + bounded repair
        └── checked-in compiled fixture
        │
        ▼
bootstrap realization
        │
        ▼
canonical facts ──► scoped runtime context ──► small/fast turn model
        ▲                                              │
        └──── policy validation + atomic fact commit ◄─┘
```

The generic portion has `canonical_truths`, `revelations`, `required_beats`,
`optional_beats`, `realization_routes`, `protected_facts`,
`opposition_clocks`, `failure_forward`, and `end_states`. A declared genre
profile defines the additional causal fields and validation rules. For example,
mystery requires a crime solution; romance requires relationship wounds,
agency-preserving choices, and viable relationship outcomes.

### Dramatic hierarchy

Blueprints represent the four authoring levels from `gpt-proposal.md`:

```text
dramatic phase
  → required beat / required outcome
    → optional or substitutable beat
      → concrete incident or realization route
```

- **Dramatic phases** control pressure, revelation scale, opposition response,
  and the kinds of incidents currently available.
- **Required beats** name the destination facts that must become true for a
  coherent central story. They must not prescribe a scene or player action.
- **Optional/substitutable beats** provide authored complications, alliances,
  reversals, relationship changes, and texture. They may fulfill a narrative
  function through several alternatives, or be omitted without invalidating the
  ending.
- **Concrete incidents/routes** are runtime-selectable factual realizations:
  clues, testimony, an ambush, a failed intrusion, a changing location, or
  another bounded consequence. They satisfy a required or optional beat only
  when their declared conditions are met.

Profiles use the preferred eight-region vocabulary—exposition, disruption,
rising action, midpoint reversal, crisis, climax, falling action, and
resolution—to guide authoring and pacing. It is not a rigid universal count:
a profile may merge regions when justified by the genre or source outline. The
validator checks phase ordering and the required turning-point semantics, not a
fixed number of major beats. Seven to nine major beats is an authoring
guideline, not a schema requirement.

## Phases

### Phase 0 — Reconcile boundaries and establish baselines

**Goal:** make the source of truth and the gap measurable before adding schema.

1. [x] Document the relationship among raw outlines, `WorldPackage`, legacy
   `StoryPackage`, `CompiledStory`, Story Blueprint, facts, and saved artifacts.
   State explicitly that only facts are mutable during a session.
2. [x] Audit the Vale Mansion fixture and record its current causal omissions:
   perpetrator, motive, means, opportunity, method, timeline, concealment,
   exonerating evidence, proof threshold, and alternate clue routes.
3. [x] Add an authoring-quality test tier separate from runtime safety tests.
   It must cover every supported genre fixture and report collection totals only
   as information.
4. [x] Define success measures: compilation pass rate, genre-validator failure
   rate, number of independent routes per pivotal revelation, premature-leak
   rate, clue-route completion rate, fail-forward coverage, normal-turn model
   calls, and p95 latency.

**Exit criteria:** [x] the data-authority map and a failing Vale causality test
describe the intended first vertical slice without changing gameplay.

### Phase 1 — Define the generic blueprint contract (tests first)

**Goal:** create the immutable authoring contract shared by all genres.

1. [x] Write contract tests before implementation for IDs, immutable parsing,
   references, cycles, protected facts, revelation ordering, route reachability,
   ending viability, and cross-genre fixture loading.
2. [x] Add `storygame.authoring.blueprint_contracts` with typed models for:
   - `StoryBlueprint`, identity/version/source-outline provenance, premise, and
     central question;
   - `CanonicalTruth` and `ProtectedFact`;
   - `Revelation`, prerequisite truths, completion conditions, protected facts,
     unlocks, and required/optional status;
   - `RealizationRoute`, containing a route role, one or more declarative
     satisfiers, availability constraints, and a bounded failure-forward result;
   - `DramaticBeat`, classified as required or optional/substitutable, with
     phase/role/question, required outcome or narrative function, revelation
     dependencies, pressure change, and pacing;
   - `OppositionClock`, opportunity decay, and `EndState`.
3. [x] Require every optional/substitutable beat to state whether it is an
   alternative satisfier for a required outcome, a complication, or a
   relationship/world-development opportunity. The validator must reject an
   optional beat that silently becomes the only route to a required ending.
4. [x] Keep executable effects small and reuse existing typed fact predicates and
   consequences. Blueprint prose is guidance; it cannot mutate state directly.
5. [x] Provide a format migration path from the current `CompiledStory` fixture:
   retain its public API temporarily, then load it as a reduced blueprint until
   all consumers migrate. Do not duplicate causal truth in both formats.

**Exit criteria:** [x] the generic contract rejects malformed graphs and validates a
minimal fixture for mystery, fantasy, sci-fi, and relationship genres.

### Phase 2 — Add declarative genre profiles and validators

**Goal:** encode genre-specific causality without genre-specific runtime code.

1. [x] Add versioned profiles under `data/genre_profiles/`, beginning with mystery,
   fantasy, sci-fi, and relationship. Profiles declare required causal roles,
   allowed revelation roles, ending requirements, and generic policy mappings.
2. [x] Implement an injected `GenreBlueprintValidator` protocol and a registry that
   resolves a profile by declared genre; no `if genre == ...` branches in engine
   code.
3. [x] Define the profile's accepted phase ordering and turning-point semantics.
   Profiles may merge the preferred eight Freytag regions but must still
   identify the disruption, reversal (when applicable), crisis, climax, and
   resolution functions needed by their story form.
4. [x] The mystery profile must require exactly one canonical crime solution with:
   victim, perpetrator, motive, means, opportunity, method, time window,
   concealment, and at least one evidence-backed route to identify/exonerate
   each decisive party. It must reject circular proof, clue placement that is
   inaccessible before its revelation, and a climax unsupported by required
   discoveries.
5. [x] Other profiles must use their own semantic requirements, e.g. a sci-fi
   failure cause/constraints/remedies/trade-off; fantasy rule/source/cost; and
   relationship wounds/needs/choice/outcomes. They share the generic contract
   but do not inherit mystery fields.
6. [x] Add validator fixtures that demonstrate both valid and invalid instances for
   every supported genre.

**Exit criteria:** [x] adding a new genre is data plus a validator adapter and tests;
the engine need not learn the genre’s names or causal fields.

### Phase 3 — Build the offline compilation and evaluation workflow

**Goal:** use a capable LLM before play, with deterministic acceptance.

1. [x] Extend the existing offline authoring compiler with a `BlueprintCompiler`
   transport. It takes one raw outline and a selected genre profile, returns the
   typed blueprint JSON, and never runs during normal gameplay.
2. [x] Prompt the compiler to plan backward from each genre’s terminal truth and to
   produce phase → required beat → optional/substitutable beat → incident/route
   structures, multiple player routes, protected facts, pressure responses, and
   failure-forward options. Request provider JSON-object mode; parse and
   validate locally using the existing bounded authoring-recovery conventions.
3. [x] Run existing offline continuity/causality/dialogue critics against the entire
   blueprint and its opening facts. Add a specialist check for route fairness:
   every required revelation has at least two genuinely distinct paths unless a
   declared genre profile explicitly permits otherwise.
4. [x] Permit one bounded repair pass. Preserve compiler prompt/version, model
   metadata, validation diagnostics, critic results, and source-outline hash in
   the artifact provenance.
5. [x] Add a CLI/tooling command to compile one selected outline into a checked-in
   candidate fixture. It must require explicit opt-in for live model use and
   never overwrite a reviewed fixture automatically.

**Exit criteria:** [x] a raw mystery outline can produce a reviewable candidate
blueprint and an invalid model result cannot become a playable package.

### Phase 4 — Author the Vale Mansion vertical slice backwards

**Goal:** prove the contract with the demo without contaminating shared runtime.

1. Create `data/story_blueprints/v1/vale_mansion_case.yaml`, generated then
   editor-reviewed. Declare the complete crime solution, all parties’ knowledge,
   a minute-level or bounded-window timeline, and evidence/concealment facts.
2. Define a reveal ladder: death is suspicious; the payment trail matters;
   groundskeeper accusation is unsound; the true perpetrator’s means/motive/
   opportunity are established; the case outcome is decided.
3. Give every pivotal revelation at least two distinct routes—physical trace,
   document, testimony, observed behavior, or consequence-created trace—and
   state their availability, custody, and failure-forward behavior.
4. Replace the linear, generic map-only path with declarative location classes
   and routes that can realize the same evidence in several appropriate places.
   Preserve canonical truth: alternate delivery may not change who killed Emma
   or what evidence proves it.
5. Write acceptance tests from player perspective: solve through each route,
   miss/contaminate a clue, accuse the groundskeeper early, pursue an unrelated
   action, and verify that the player can neither receive protected truth nor
   complete the accusation/exposure beats without supporting facts.

**Exit criteria:** Vale Mansion is fairly solvable through more than one route,
and its final answer follows committed evidence rather than narration or a bare
completion tag.

### Phase 5 — Realize blueprints into facts and enforce progression

**Goal:** join authoring causality to the existing fact-backed runtime.

1. Add a bootstrap adapter that realizes a validated blueprint into the existing
   canonical fact store: truths, evidence, availability/custody, knowledge,
   scene state, clocks, beat state, and protected revelation boundaries.
2. Extend shared proposal/commit contracts with a stable `route_id` and optional
   `evidence_ids`; validate them against currently available blueprint-derived
   facts. The model may propose a route, but cannot invent one.
3. Replace V2 bare completion-tag acceptance with a generic
   `ProgressionValidator`: a beat completes only after declared revelation and
   evidence/realization conditions are true. Maintain monotonic prerequisites
   and atomic rollback on rejection.
4. Extend incidents and consequences to select from blueprint-declared routes
   using current location, observer knowledge, custody, relationships, pressure,
   and clocks. A failed route commits its declared bounded consequence before
   narration and exposes an altered viable route.
5. Build runtime prompt context exclusively from observer-scoped facts and
   currently legal routes; do not expose canonical solution fields unless the
   player has earned their relevant facts.
6. Preserve one normal provider request and the shared two-request recovery
   cap. Add timing and request-count tests around blueprint-aware turns.

**Exit criteria:** a bounded runtime model can flexibly realize an authored route
without becoming the authority for story truth or progression.

### Phase 6 — Expand fixtures and migrate deployment safely

**Goal:** prove generality before making blueprints the default demo input.

1. Produce reviewed blueprints for at least fantasy, sci-fi, and relationship
   fixtures drawn from the outline corpus. Each must exercise different genre
   validators and non-mystery terminal structures.
2. Add cross-genre regression suites for valid alternative routes, protected
   knowledge, failure-forward transitions, pressure clocks, impossible route
   rejection, persistence/replay, and model-recovery exhaustion.
3. Run offline package evaluation plus scripted-player playability evaluation;
   record route coverage and causal-validator results alongside quality scores.
4. Roll out the Vale blueprint through the existing staging channel, complete
   the acceptance matrix, observe the defined quality/latency measures, then
   make it the hosted demo’s default only after manual promotion.
5. Deprecate reduced `CompiledStory` fixture fields only after all package,
   bootstrap, runtime, persistence, and hosted tests consume blueprints. Keep a
   documented, deterministic migration for checked-in fixtures—not for mutable
   player saves unless separately approved.

**Exit criteria:** the demo runs on the Vale blueprint in production and all
supported genre fixtures demonstrate the same generic authoring/runtime
contract.

## Sequencing rules

- Tests precede each phase’s implementation; use `TMPDIR=/tmp uv run pytest -q`
  for full verification and focused `--no-cov` tests during iteration.
- Keep modules near the project size guidance; split contracts, validators,
  compiler, realization, and evaluation at their architectural seams.
- Update `docs/compiled-story-authoring.md`, `docs/fact-authority.md`, and the
  PRD only when a phase’s implementation is complete, so documentation does
  not claim unbuilt causality guarantees.
- Do not make raw `story_outlines.yaml` a runtime input. It is source material
  for offline compilation and evaluation only.
