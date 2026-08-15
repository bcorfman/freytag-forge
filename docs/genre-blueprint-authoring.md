# Genre-blueprint authoring baseline

Phases 0–3 establish the offline authoring boundary for Story Blueprints. They
do not change gameplay, package realization, or the current V2 runtime.

## Phase-1 generic contract

`storygame.authoring.blueprint_contracts` defines the frozen
`story-blueprint-v1` authoring artifact. A blueprint carries source-outline
provenance, canonical truths, protected facts, revelations, realization routes,
required and optional beats, opposition clocks, and viable end states. Its
local validator rejects duplicate or unknown IDs, revelation cycles,
unreleased protected facts, route-less required revelations, invalid route
references, endings that omit required revelations, and optional beats that
silently become the only satisfier of a required outcome.

Routes provide declarative truth satisfiers, availability constraints, and a
bounded failure-forward result. They are not executable runtime effects. Phase
5 will realize accepted declarations using the existing typed fact predicates
and consequence contracts; no blueprint prose can mutate session state.

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
identification/exoneration routes. Fantasy, sci-fi, and relationship profiles
instead require rule/source/cost, failure/constraint/remedy/trade-off, and
wound/need/choice/outcome structures.

Adding a genre requires a profile, an injected validator adapter where the
declarative adapter is insufficient, and valid/invalid fixtures. It does not
authorize a new runtime branch or make a blueprint mutable.

## Phase-3 compilation and evaluation

`storygame.authoring.blueprint_compiler.BlueprintCompiler` accepts one raw
outline, a selected injected `GenreProfileRegistry`, and a provider transport.
The transport receives an explicit `json_object=True` choice. A JSON-mode
rejection, malformed response, or local schema/profile/provenance failure uses
the single shared fallback request with `json_object=False`; after that the
compiler raises `BLUEPRINT_COMPILATION_EXHAUSTED`. No rejected response is a
playable authoring input.

The compiler plans from the profile terminal truth and asks for phases,
required and optional beats, routes, protections, pressure, and
failure-forward declarations. It validates the selected outline ID and SHA-256
hash against the candidate's source provenance before critique. Injected
continuity, causality, and dialogue critics receive the complete blueprint and
opening facts. `RouteFairnessCritic` additionally requires the profile's
`minimum_routes_per_required_revelation` genuinely distinct route roles for
every required revelation (default: two). One injected repairer may revise a
rejected candidate; the repaired result is fully revalidated and re-reviewed.

`BlueprintCompilation` retains a review record: prompt version, source outline
hash and ID, model metadata, validation diagnostics, critic results, request
count, and whether repair occurred. The `storygame-blueprint` operator command
is deliberately live-only: both `--live` and
`FREYTAG_ENABLE_LIVE_COMPILER=1` are required, a transport factory is injected,
and output must be a new `*.candidate.json` envelope. It never overwrites a
reviewed fixture or makes raw outlines runtime inputs.

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

## Vale Mansion baseline audit

`data/compiled_stories/v1/mystery.json` retains the authored opening, public
briefing, protected revelation, and linear five-beat progression. It does not
yet declare the causal evidence needed to fairly solve the case. The omitted
fields are: perpetrator, motive, means, opportunity, method, bounded timeline,
concealment, exonerating evidence, proof threshold, and multiple independent
routes for each pivotal revelation.

`tests/test_authoring_quality_baseline.py` records this as a strict expected
failure. The test must remain failing until the reviewed Vale Blueprint arrives;
an unexpected pass means the baseline needs to become a normal Phase-4
acceptance contract.

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
| Independent routes | Minimum number of distinct declared realization routes per pivotal revelation. | Vale: 0 declared. |
| Premature-leak rate | Protected-truth leaks before their required facts / protected-truth exposure attempts. | Measure at runtime realization in Phase 5. |
| Clue-route completion rate | Completed declared clue routes / routes made available to scripted play. | Not applicable until Phase 4. |
| Fail-forward coverage | Routes with a declared viable failure-forward result / all routes. | Vale: 0 declared. |
| Normal-turn model calls | Inference requests per ordinary player turn. | Preserve the current cap: one normal request plus at most one shared recovery request. |
| p95 latency | 95th percentile end-to-end ordinary-turn latency. | Preserve the under-ten-second target. |
