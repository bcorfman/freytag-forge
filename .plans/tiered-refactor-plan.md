# Freytag Forge Tiered Refactor Plan

## Purpose

This plan defines the remaining work for a story-agnostic, fact-backed
interactive-fiction engine. It complements the project architecture rather
than proposing a second runtime.

Canonical truth is committed only by deterministic policy. Packages are
validated authoring inputs, and prose is a post-commit projection. Ordinary
play remains LLM-proposal-first; control-plane commands (`save`, `load`,
`quit`, and `help`) are the only parser-owned inputs.

## Model-Tier Policy

Use the least expensive capable tier at a defined boundary:

* **Deterministic Python** owns canonical facts, policy, validation,
  consequences, persistence, replay, and tests.
* **Ordinary runtime adapters** may propose intent, bounded effects, dialogue,
  and narration. Accepted effects commit before rendering. A normal turn stays
  within the configured request and recovery budget.
* **Frontier models** are offline tools for package authoring, package review,
  difficult repairs, and evaluation-fixture generation. They do not run on an
  ordinary player turn.

No model response establishes canonical truth without local typed validation
and a successful deterministic commit.

## Stage 1 — Baselines, Policy, and Evidence

### Work

- [x] Freeze representative cross-genre fixtures, prompts, adapter/model
  revisions, sampling settings, and seeds.
- [x] Record baseline proposal-validity, direct-acceptance, bounded-repair
  success, hidden-information leakage, role drift, latency, and token use for
  every supported ordinary runtime adapter.
- [x] Classify deterministic failure categories: contradiction, impossible
  action, hidden-information leak, role drift, causal omission, uncommitted
  narration, and exhausted provider recovery.
- [x] Keep characterization coverage for facts, turn execution, prompts, NPC
  dialogue, persistence, replay, and local/hosted adapter parity.

### Exit criteria

- [x] The same frozen fixture produces reproducible facts, artifacts, and
  evaluation results.
- [x] Measurements distinguish informational baselines from release gates.
- [x] Failures are classified from structured evidence rather than transcript
  wording alone.

## Stage 2 — Generic Proposal/Commit Runtime

### Work

- [ ] Maintain typed, extensible policy families for location, perception,
  knowledge, relationships, tasks, traces, dramatic state, and bounded intent
  effects.
- [ ] Route ordinary input through the shared proposal, validation, commit, and
  post-commit rendering contract.
- [ ] Normalize only unambiguous deterministic affordances—visible-item,
  inventory, direction, and exit aliases—into that contract.
- [ ] Retire parser-era routing, plot-specific regexes, demo-specific behavior,
  and compatibility fallbacks as equivalent generic coverage is proven.
- [ ] Fail closed with a typed error when the bounded ordinary-turn recovery
  budget is exhausted; send failures to offline evaluation, not frontier
  inference during play.

### Exit criteria

- [ ] Every accepted state delta passes typed validation and a deterministic
  fact commit.
- [ ] Players may attempt arbitrary story moves; unsupported or ambiguous moves
  preserve truth and receive a bounded outcome or clarification.
- [ ] Deterministic affordances and ordinary freeform input use the same
  proposal/commit contract.
- [ ] No genre or story requires a hard-coded command route.

## Stage 3 — Offline Package Authoring and Playability

### Work

- [ ] Author and validate packages that declare maps, presentation,
  characters, roles, knowledge boundaries, items, custody, discoveries,
  affordances, causal rules, and endings.
- [ ] Use frontier models only offline to propose or repair structured package
  data; deterministic package validation is the acceptance authority.
- [ ] Validate reachability, revelation paths, causal consistency, character
  availability, role contracts, and ending viability across genres.
- [ ] Run exploratory, goal-focused, social, adversarial, avoidant, and chaotic
  scripted players against frozen fixtures.
- [ ] Apply targeted package repairs and revalidate instead of regenerating a
  whole story package.

### Exit criteria

- [ ] Each fixture initializes and plays through the same engine contracts.
- [ ] Required information has resilient, reachable acquisition paths.
- [ ] NPC knowledge, beliefs, limits, delegated work, and autonomous actions
  remain within explicit fact-backed role contracts.
- [ ] Story-specific setup and prose exist only in validated package data.

## Stage 4 — Ordinary-Runtime Quality Evaluation

### Work

- [ ] Compare supported local and hosted ordinary-runtime adapters against the
  same frozen fixtures and deterministic acceptance criteria.
- [ ] Store validation failures and regressions as structured test fixtures.
- [ ] Establish an informational SLO: at least 95% of normal turns validate
  directly or after one bounded repair. Promote it only after stable adapter
  baselines support a release gate.
- [ ] Add a scheduled frozen-model regression suite. It is deterministic by
  default; remote or paid evaluations require explicit configuration and a
  bounded budget.

### Exit criteria

- [ ] Accepted turns have no protected-information leaks or uncommitted state.
- [ ] Proposal validity, repair rate, latency, and token use are reported per
  adapter.
- [ ] Exhausted runtime failures are typed, measurable, and assigned to
  offline authoring or evaluation follow-up.

## Stage 5 — Cutover, Cleanup, and Decision Gates

### Work

- [ ] Make the proposal/commit runtime the only ordinary-turn path for CLI,
  local web, and hosted demo while preserving their separate adapters.
- [ ] Remove superseded parser-era, story-specific, and compatibility paths.
- [ ] Keep deterministic tests, cross-genre evaluation, artifact integrity,
  local/hosted parity, and scheduled evaluation in CI.
- [ ] At each substantial cutover, record evidence for cross-genre behavior,
  fact-commit integrity, compatibility-code reduction, and runtime-quality
  trends before extending the architecture.

### Exit criteria

- [ ] One canonical fact-backed runtime serves every story package and surface.
- [ ] New genres and packages require validated data, not shared runtime
  branches.
- [ ] The ordinary-turn path has bounded latency and recovery, with no frontier
  inference dependency.
- [ ] Compatibility code is being deleted rather than permanently wrapped.

## Salvage Decision Rule

Evaluate the evidence at the end of Stages 2, 3, and 4. Continue only while
generic mechanisms work across genres, facts remain the sole mutable runtime
authority, model proposals remain locally validated, and the compatibility
inventory decreases. Consider a rewrite only if these conditions fail across
multiple reviews and cannot be corrected inside the fact-backed
proposal/commit architecture.
