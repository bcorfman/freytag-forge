# Genre-blueprint authoring baseline

Phase 0 establishes the authoring boundary for the future Story Blueprint. It
does not change gameplay, package realization, or the current V2 runtime.

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
