# Code review recommendations

Date: 2026-11-27

Status: Proposed; implementation has not started.

Based on [code-reviews.txt](code-reviews.txt) and inspection of the repository's
engineering guidance, configuration, and CI workflows. The article's external
claims were not independently verified. GitHub branch-protection settings were
not inspected.

The project already has a concise AGENTS.md, focused guides, story-source format
checks, snapshot checks, and SHA-bound promotion gates. Build on these controls
with the following six changes.

## 1. Enforce the configured lint rules in CI

[pyproject.toml](../pyproject.toml) enables `E, F, I, B, UP, SIM`, but
[test.yml](../.github/workflows/test.yml) runs only `E9,F63,F7,F82`.

Change the static job to run:

```sh
uv run ruff check .
uv run ruff format --check .
```

Assess existing violations first and separate mechanical cleanup from behavior
changes. This turns existing expectations into enforced checks.

## 2. Add a project-specific review checklist and PR template

Add a root `REVIEW.md` covering these concrete failure modes:

- Rejected turns leave facts changed, including after save/load.
- Narrator inputs expose protected knowledge, future effects, or transcript memory.
- Provider proposals bypass validation before committing facts.
- World-only logic appears outside `packages/worldkeeper`.
- Shared runtime introduces story-specific behavior.
- Story changes omit regenerated entry snapshots.

Add `.github/pull_request_template.md` requiring the linked plan, acceptance
criteria, riskiest change, relevant verification evidence, and remaining
uncertainty. Require review findings to identify a failure scenario and file
location.

Run PR review in a fresh session with the diff, the review instructions, and the
feature plan. Tie the review result to the reviewed commit so subsequent changes
cannot silently inherit it.

## 3. Define risk tiers around the engine's failure modes

Add `.github/review-policy.yml`, with classification and enforcement implemented
separately. A policy file alone does not enforce approvals.

| Tier | Project examples | Proposed treatment |
| --- | --- | --- |
| Low | Explanatory documentation and plan updates | Lightweight review |
| Ordinary | Isolated presentation changes and development tooling | One human approval plus relevant checks |
| High | Fact commits, persistence, knowledge validation, provider boundaries, world semantics, deployment workflows | Explicit invariant evidence, fresh review, and human approval |

Treat story declarations and narrator prompts as behavior changes. Treat tests
that weaken safety assertions as potentially high risk.

Start with human approval across tiers. Reducing review requirements needs
project outcome data first; defer a learned classifier. Inspect actual GitHub
branch-protection settings when implementing enforcement.

## 4. Add architecture checks with actionable errors

Candidate checks:

- Reject imports from `storygame` into `worldkeeper`.
- Reject access to world implementation internals from runtime callers outside
  the designated adapter.
- Extend cross-package regression coverage where runtime behavior could become
  tied to one story.

An actionable failure should explain the repair and link to the rule, for example:

> World-state traversal belongs in a `World` method; add its tests in
> `packages/worldkeeper/tests/`. See runtime-and-authoring-boundaries.md.

Keep the existing story-format and snapshot gates. Choose further checks from
actual repeated review findings; the supplied article does not establish which
mistakes recur most in this project.

## 5. Make release evidence accurate and rollback executable

The [promotion guide](../docs/railway-production-promotion.md) describes hosted
gameplay E2E, while the inspected workflows show adapter tests and
deployment-identity checks.

Update the guide to match the current adapter surface. Expand staging evidence
to record check outcomes and distinguish local adapter verification from deployed
checks. The current JSON is written even on failure and contains no result field.

[promote-production.yml](../.github/workflows/promote-production.yml) records a
previous Railway deployment ID. Extend that into a documented, exercised rollback
procedure covering both the API and matching frontend revision. Recording an ID
alone does not demonstrate recoverability.

## 6. Collect review outcomes before increasing autonomy

Add a reporting script that joins PR and deployment history into a periodic
artifact containing:

- Time from ready-for-review to first review and merge.
- Review rounds and requests for changes.
- Reverts and explicitly linked follow-up fixes.
- Production failures by risk category.

Separate documentation-only changes from executable changes. Measure active
human review time explicitly if desired; elapsed review time is not a substitute.
Treat inferred bug-introducing commits as uncertain labels.

Add a short ownership section to the
[agent workflow guide](../docs/agent-workflow-guide.md): who accepts the change,
who promotes it, and who owns rollback.

## Suggested implementation order

1. Lint enforcement.
2. Review checklist and PR template.
3. Risk classification and fresh-session review.
4. Architecture checks.
5. Release-evidence corrections and rollback.
6. Outcome reporting.

Follow the [testing runbook](../docs/testing-runbook.md) during implementation.
When verification procedures change, update their existing runbook entries in
place. Record implementation results and remaining work in the active plan.

## Resume here

Assess existing Ruff violations and the scope of mechanical cleanup before
implementing recommendation 1. All six recommendations remain proposed.
