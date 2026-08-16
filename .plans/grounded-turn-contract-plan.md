# Grounded turn-contract plan

## Decision

Adopt a hybrid turn contract:

> Facts remain the sole authority for consequential world state. The LLM may
> freely author intent, dialogue, event framing, and atmosphere, but every
> material state assertion in its narration must be represented by a typed
> claim that agrees with the facts after the proposed effects commit.

This replaces prose keyword policing with validation of structured claims. It
does not make narration templated, nor does it require every incidental image
or emotional observation to become a fact.

## Problem

The current freeform proposal combines LLM-authored prose with a typed action
proposal. Effects are validated and committed, but the prose can still claim a
different item location, weather state, access condition, or visible event.
The case-file-on-the-steps regression demonstrated that correct canonical
custody alone does not prevent a contradictory player-facing projection.

The current phrase-based custody guard is a short-term safety net only. It is
not a scalable solution and must be removed once the structured contract and
its evaluation coverage are in place.

## Goals

- Preserve one normal provider call and the shared two-request recovery budget.
- Keep ordinary play LLM-proposal-first and permit freeform player attempts.
- Let the LLM invent concrete Freytag incidents while deterministic policy
  constrains only their consequence class and canonical effects.
- Validate material narration claims against post-commit facts without
  story-, genre-, item-, or phrase-specific runtime branches.
- Keep physical placement, knowledge, access, weather, clocks, and dramatic
  pressure declarative and fact-backed when they affect play.
- Cover every supported package with deterministic contract tests and selected
  hosted staging scripts.

## Non-goals

- Parsing arbitrary prose to reconstruct world state.
- A second LLM critic on the normal turn path.
- Tracking incidental description such as a warm breeze, a nervous pause, or
  metaphorical language when it has no durable gameplay consequence.
- Pre-authoring every possible complication or using a fixed event table.
- Replacing the existing fact committer, observer slices, or policy registry.

## Target turn shape

```text
observer-scoped facts + legal dramatic permissions
                    │
                    ▼
LLM JSON proposal: intent, dialogue/narration, bounded effects, staging claims
                    │
                    ▼
local typed parsing → effect-policy validation → candidate post-state
                    │                                  │
                    └──── staging claims match ───────┘
                    │
                    ▼
atomic fact commit → accepted prose as a projection of that committed state
```

### Material staging claim

Add a locally validated `staging_claims` collection to the turn proposal. A
claim names an existing canonical relation, not a new ad-hoc prose category.
Initial relation families are:

- `custody`: item held by actor, or item located in a room;
- `environment`: declared weather/light/exposure state at a location;
- `access`: route/item/NPC availability or block state;
- `event`: a committed timed or dramatic event visible in the current scene.

The claim is checked against the candidate post-effect facts. For example,
`case_file held_by daria_stone` is valid only while that holding fact remains
true. To describe the file on the steps, the proposal must include a legal
custody/location effect and a matching post-commit staging claim.

The model is instructed to list every material physical or environmental state
it explicitly stages. This is an auditable structured-output contract, not an
attempt to infer every English statement after the fact. Cross-genre adversarial
evaluations measure omissions and trigger the existing one-retry repair path.

## Dramatic creativity model

Freytag policy permits a consequence class, not a prewritten incident. At a
rising-action opportunity, a package/policy may allow a `complication` with a
bounded pressure increase, an access change, a clock advance, or a declared
revelation opportunity. The LLM supplies the concrete realization: a burst
pipe, a witness recantation, an arrival, a failed entry, or another grounded
event. It may not consume a protected reveal, dead-end all viable routes, or
silently change custody/weather/access outside its legal effects.

Consequential weather follows the same pattern. A package declares legal
environment transitions and their conditions; the LLM proposes one only when
the current policy permits it. Incidental atmospheric prose remains untracked
unless it claims a change with gameplay consequences.

## Phases

### Phase 0 — Baseline and boundary audit

1. [x] Document every proposal/rendering entry point: CLI, `storygame.web`,
   `storygame.web_demo`, freeform adapter, opening agents, and Story Director.
2. [x] Add failing deterministic tests for contradictory material prose in each
   relation family, using an injected provider response and asserting no facts
   commit on rejection.
3. [x] Record current normal-turn provider-call counts and latency baseline.
4. [x] Classify existing checks as structural fact validation, temporary prose
   guard, or presentation-only validation.

**Exit criteria:** [x] the gap is measured across all deployment adapters and no
implementation decision depends on mystery-specific examples. See the
[Phase 0 baseline](../docs/grounded-turn-contract-baseline.md).

### Phase 1 — Typed contract and candidate-state validator

1. Add typed `staging_claims` to the local turn/action proposal contracts and
   normalize every supported provider envelope into it.
2. Define a small closed vocabulary of generic relation families and IDs;
   reject unknown entities, malformed relations, duplicated contradictory
   claims, and claims outside the observer-visible scene.
3. Add a side-effect-free candidate-state validation path that applies the
   already validated effect envelope to a clone, then checks every staging
   claim against that candidate's facts.
4. Keep all typed-contract parsing and semantic validation local; provider
   JSON-object mode remains syntax assistance only.
5. Ensure claim failures consume the existing recovery request and exhaust as
   `ORDINARY_TURN_RECOVERY_EXHAUSTED` without a commit.

**Exit criteria:** a claim can be validated against post-effect custody,
environment, access, and event facts with no narration text matching.

### Phase 2 — Generic policy/data support

1. Realize `placement_security` and other consequential environmental package
   declarations into canonical facts, while preserving package data as an
   immutable authoring input.
2. Introduce a generic environment-transition policy family: source state,
   target state, declared condition facts, bounded effects, and legal commit
   sources. Do not encode weather names or genres in shared runtime code.
3. Extend existing dramatic-policy output with generic permitted consequence
   classes and budgets; retain the LLM's freedom to choose an incident frame.
4. Validate viability: an access-blocking complication cannot remove all
   required routes; an environment transition cannot destroy/contradict
   protected evidence without a package-declared consequence.
5. Migrate the mystery, fantasy, and at least two additional genre fixtures to
   exercise custody, protected outdoor placement, environment, and access
   paths declaratively.

**Exit criteria:** policy admits creative incidents through generic consequence
classes while facts remain the only mutation authority.

### Phase 3 — Planner and renderer integration

1. Supply the model with concise observer-scoped state plus legal claim/effect
   vocabulary and the currently permitted dramatic consequence classes.
2. Update LLM planner instructions with examples that distinguish atmosphere
   from material staging and require claims for the latter.
3. Validate parsed claims before commit; retry once with the specific local
   contract failure while preserving the total request budget.
4. Render only accepted proposal prose after the atomic commit, retaining the
   current direct-NPC speaker and knowledge protections.
5. Remove the phrase-based held-item custody guard after equivalent contract
   tests pass. Keep package placement validation because it is structural,
   declarative authoring validation rather than prose parsing.

**Exit criteria:** no ordinary turn uses regex/keyword matching to decide
whether material narration agrees with custody, environment, access, or events.

### Phase 4 — Evaluation, persistence, and deployment adapters

1. Build a reusable cross-genre matrix for each relation family:
   valid claim, contradictory claim, valid effect-plus-claim, missing claim,
   unavailable entity, protected knowledge, retry, recovery exhaustion, and
   save/load continuity.
2. Add adversarial deterministic provider fixtures with varied wording to
   demonstrate that validation is relation-based rather than phrase-based.
3. Verify facts/projections survive `StoryState.json`, `STORY.md`, CLI saves,
   web saves, and web-demo saves without claiming uncommitted state.
4. Run hosted staging scripts through both web adapters with independent
   credentials/backends; record request IDs, retry counts, latency, and
   fail-closed results.
5. Remove obsolete tests that only exercise the retired prose matcher, while
   preserving explicit regressions for the original custody failure through
   structured claims.

**Exit criteria:** every adapter has E2E proof that rejected material claims do
not render as accepted turns or mutate state.

### Phase 5 — Rollout and cleanup

1. Gate the new contract behind an explicit deployment configuration during its
   first staging window; do not allow two contracts to mutate one session.
2. Compare staging metrics against Phase 0: provider calls, latency, malformed
   responses, retry exhaustion, contradiction detection, and player-visible
   coherence regressions.
3. Promote only when normal-turn latency remains within the documented target,
   recovery remains bounded, and project coverage is at least 90%.
4. Remove the temporary compatibility path and update authoring/runtime docs.

## Completion criteria

- Material world state in accepted prose has a matching typed claim validated
  against post-commit facts.
- The LLM can realize multiple distinct incidents for the same legal Freytag
  consequence class across genres.
- No normal path uses an additional critic call or unbounded recovery.
- Package validation rejects unprotected outdoor wind-vulnerable placement.
- All persistence and deployment adapters retain fact/prose integrity.
- `TMPDIR=/tmp uv run pytest -q` passes with at least 90% project coverage.
