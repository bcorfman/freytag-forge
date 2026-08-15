# Genre-blueprint authoring test plan

## Purpose and scope

This plan verifies the complete authoring-to-runtime path described in
`genre-blueprint-authoring-plan.md`: raw outlines become reviewed immutable
blueprints; a blueprint realizes into facts; and a player may reach an ending
through authored alternatives without an LLM becoming the authority for canon
or progression.

Tests are deliberately split by what has a deterministic oracle. Automated
tests prove contracts, safety, factual continuity, and transport limits. User
tests assess clarity, dramatic pacing, fairness as experienced by a player, and
genre fit—questions for which matching an expected string is not a valid proxy.

## Test levels and ownership

| Level | What it proves | Execution | Owner |
| --- | --- | --- | --- |
| Unit | Typed contracts, profile validators, route legality, and progression policy | Every pull request | Engineering |
| Component | Compiler recovery, fact realization, observer context, and provider envelopes | Every pull request | Engineering |
| Runtime E2E | A structured model proposal travels from context through validation, atomic commit, and rendered response | Every pull request | Engineering |
| Hosted E2E | The deployed API/browser path creates a session, plays, saves, loads, and preserves channel identity | Staging deployment | CI/operator |
| Human user test | Agency, intelligibility, clue fairness, pacing, and genre satisfaction | Before promotion | Named reviewer |

Do not convert subjective human outcomes into brittle text assertions. Record
them with the candidate SHA, blueprint version, model/prompt revision, genre,
and transcript URL instead.

## Automated coverage matrix

| Plan phase | Required automated proof | Existing or required test location |
| --- | --- | --- |
| 0: boundaries/baseline | Facts remain the only mutable authority; authoring-quality fixtures collect independently | `test_authoring_quality_baseline.py`, `test_fact_runtime.py` |
| 1: generic contract | Parsing immutability, IDs, references, cycles, protected release order, route reachability, endings, and optional-beat purpose | `test_blueprint_contracts.py` |
| 2: genre profiles | Valid and invalid mystery, fantasy, sci-fi, and relationship causality; no runtime named-genre branch | `test_genre_blueprint_validators.py` |
| 3: offline compiler | JSON mode and one fallback, malformed/schema failure, provenance, fairness critic, one repair, and no overwrite | `test_blueprint_compiler.py`, `test_blueprint_cli.py` |
| 4: Vale vertical slice | Two route families per pivotal revelation, premature accusation rejection, unrelated action, and fail-forward declarations | `test_vale_mansion_blueprint.py` |
| 5: fact realization | Canon fact map, observer scoping, route/evidence validation, atomic rollback, and failure-forward commit | `test_blueprint_runtime.py` |
| 5: runtime E2E | Turn model → scoped prompt → typed result → `ProgressionValidator` → event/facts; one-call success and bounded two-call rejection recovery | `test_blueprint_runtime_e2e.py` |
| 6: deployment | Each genre fixture over public staging, state continuity, save/load, model-call cap, latency, protected leakage, and channel/SHA identity | `staging_evaluation.py`, `test_hosted_demo_e2e.py` |

## Automated E2E scenarios

The following tests are implemented in `tests/test_blueprint_runtime_e2e.py`.
They are integration-tier E2E tests for the in-process V2 boundary; they use an
injected deterministic model so their oracle is stable and they run in pull
request CI.

1. **Declared-route happy path.** Bootstrap the Vale blueprint with the V2
   bridge fixture. Submit `review_case_file` through `RuntimeEngine`. Assert one
   model request, committed `suspicious_death`, and a prompt that excludes the
   protected perpetrator identity.
2. **Failed-route path.** Submit `inspect_gallery_staging` with
   `route_failed=true`. Assert its declared failure-forward truth commits before
   the turn returns and a subsequent payment-trail route becomes legal.
3. **Invented-route rejection.** Submit an undeclared route on both permitted
   requests. Assert typed recovery exhaustion after exactly two calls and an
   unchanged blueprint fact map.

When Phase 6 makes blueprints the hosted default, extend the live staging E2E
rather than duplicating API tests. For each supported genre it must additionally
assert that a route-bearing turn is accepted only when its route is in the
server-provided legal-route context, and that save/load preserves facts, route
history, clocks, and completed revelations.

Run local deterministic E2E coverage with:

```text
TMPDIR=/tmp uv run pytest tests/test_blueprint_runtime_e2e.py -q --no-cov
```

Run the full gate with:

```text
TMPDIR=/tmp uv run pytest -q
```

## User test protocol

Run this protocol against the staging candidate after the automated staging
evaluation succeeds and before promotion. Use a fresh session for each path;
do not give the reviewer the solution, route IDs, or canonical truth summaries.

| Scenario | Reviewer action | Record | Acceptance decision |
| --- | --- | --- | --- |
| Orientation | Play the opening for 5–10 minutes without a guide | What feels actionable, confusing, prematurely revealed, or absent | Reviewer can state an immediate goal and at least two plausible next actions |
| Alternate investigation | Independently solve Vale once through physical evidence and once through document/testimony | Route taken, dead ends, inferred theory, and moment of proof | Each path feels causally sufficient; neither reads as a hidden required command |
| Failure-forward | Miss, contaminate, or abandon a promising clue | Whether the consequence is legible and what new opportunity is perceived | Setback changes the situation but preserves an understandable viable path |
| Agency probe | Accuse the groundskeeper early, pursue a social/unrelated action, and refuse a suggested lead | Whether the game acknowledges intent without inventing facts or railroading | The player may attempt the action; consequences are coherent and do not leak protected truth |
| Dramatic pacing | Continue through the midpoint, crisis, and climax | Notes on pressure, repetition, urgency, and resolution payoff | The reviewer judges escalation and resolution satisfying for the declared genre |
| Cross-genre fit | Play one short unscripted session in fantasy, sci-fi, and relationship fixtures | Genre expectations met/missed and any mystery-shaped behavior | Each genre feels distinct without new shared-runtime special cases |
| Accessibility and trust | Use browser controls, make one harmless invalid move, save, load, and read an error | Confusing wording, accessibility barriers, unsafe/raw error text | Controls and failures are comprehensible; save/load preserves the player’s understood situation |

The reviewer records **approve**, **approve with follow-up**, or **reject**. A
rejection requires a transcript excerpt, reproduction steps, and classification:
clarity, fairness, agency, pacing, genre fit, accessibility, or integrity. An
integrity finding (leaked protected truth, fabricated canonical fact, impossible
route accepted, or lost save state) blocks promotion and receives a deterministic
regression test before a new candidate is reviewed.

## Exit evidence

For a Phase-6 promotion candidate, attach:

- passing full-suite and staging-evaluation artifacts;
- route coverage by revelation and genre, including failure-forward paths;
- request-count and p95-latency report;
- protected-truth leak count and typed failure count;
- the completed user-test record with reviewer, SHA, transcript links, and
  decision; and
- any accepted-risk follow-ups with owner and due date.
