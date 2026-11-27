# Code review recommendations

Date: 2026-11-27

Status: Merged to `main` and staged (2026-11-27). Not promoted to production;
the rollback drill has not been run.

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

## Owner decisions (2026-11-27)

- Lint: exclude `.plans/` and `scripts/ringer/` from Ruff entirely.
- Approval: the owner's per-PR merge word; risk tiers are advisory. The owner
  accepts, promotes and owns rollback. The factory keeps its narrow right to
  merge its own gated repair-ticket PRs.
- Architecture: move the direct `World.schema` reads into `World` methods now.
- Rollback: write the procedure; the owner runs the drill later.
- Rollback gate: a SHA with any successful `production-promotion` status skips
  the nightly coverage requirement.

## Corrections to the review above

- `.plans/code-reviews.txt` does not exist in the repository.
- All lint violations were in `.plans/` and `scripts/ringer/`.
- The `main` ruleset only blocks deletion and non-fast-forward pushes. There is
  one collaborator, so a required approval would block every merge. The Railway
  GitHub environments have no protection rules. Settings were not changed.
- No workflow ran hosted E2E, and the diagnostic E2E workflow the guide named
  does not exist.
- Each Pages deploy deleted the other channel's `deployment.json`; the live
  root file returned 404.
- Live production (`62d23f5c`) has no successful nightly run, so the promotion
  workflow would have refused to restore it.

## Results

| Rec | Branch (stacked in this order) | Delivered |
| --- | --- | --- |
| 1 | `review-rec1-lint` | Full Ruff check and format check in CI |
| 2 | `review-rec2-checklist` | `REVIEW.md`, PR template |
| 3 | `review-rec3-risk-tiers` | Policy file, classifier, advisory "review risk" workflow |
| 4 | `review-rec4-arch-checks` | Six declared-only `World` methods; boundary tests |
| 5 | `review-rec5-release` | Evidence v2, previous-version record, production Pages check, Pages metadata fix, rollback gate and procedure, corrected guide |
| 6 | `review-rec6-outcomes` | Weekly outcomes report, ownership section, runbook entries |

Code was written by Ringer Luna workers (run `code-review-recs`). Review of
patches that had passed their checks found classifier defects (tier order,
paths with spaces, interpreter) and report defects (revert count, fresh-review
order, backwards comparison, import failure, API volume); all were fixed.

Verification, on the final combined tree: full suite 5291 passed, 27 skipped;
`worldkeeper` 152 passed. After that run one workflow line changed (the weekly
report now uses a 7-day window). Each branch tip passes Ruff, its new tests and
the quick-suite and shard-manifest tests without `PYTHONPATH`; only the final
tree ran the full suite. `defect-design`, `goal-tracking`, `prompt-probe`,
`strategy-goals` and `synthetic-struct-2a-g` each merge cleanly with the last
branch and pass Ruff and the boundary tests. A live read-only 7-day outcomes report ran in about three
minutes using 225 REST requests (42 merged PRs, none with a review).

## Merge and staging

PRs #838 to #843 were merged in order with merge commits, each after its own
`tests` run passed on its head commit. `main` is `0b9534b1`, identical in
content to the last branch. GitHub cancelled the superseded `main` runs for the
second to fifth merges; the first and last passed. On `0b9534b1`:

- Staging deploy and `staging-deployment` status succeeded.
- The evidence artifact is `scene-staging-evidence-v2`, result `success`, with
  both deployed identity checks and the local adapter tests passing.
- `/dev/deployment.json` reports `0b9534b1`.
- "review risk" passed on PRs #840 to #843.
- "review outcomes", dispatched once (run 46059918146), succeeded with the
  workflow token.

## Not verified

- The promotion workflow changes have not run: nightly exemption, previous
  version record and production Pages check. The rollback drill has not run.
- The Pages preservation fix has only been simulated for a valid file:
  production's root `deployment.json` is still missing, so there was nothing to
  preserve.
- The scheduled (not dispatched) report run, and staging evidence on a failed
  deploy.
- The weakened-assertion flag has false positives (for example, skip calls
  inside test strings).

## PR description notes

- Rec 4: one edge changes behavior. In the narrator's THINGS text, an entity
  created during play used to raise `KeyError` in the opening check; it is now
  treated as not an opening.
- Rec 5: production promotion can now fail if the published root
  `deployment.json` does not match within about five minutes or more.
  `scene-staging-evaluation` now also runs when the staging deploy fails.

## Remaining

- `coverage-nightly` is failing: the last six runs failed, and the latest
  (on `1e00fc29`) reported 89% against the 90% floor. A SHA that has not been
  in production cannot be promoted until it has a passing run. This predates
  these changes.
- Production's root `deployment.json` stays missing until the next promotion.
- Run the rollback drill (see the promotion guide). It needs a second proven
  release, so it depends on a promotion first.

## Resume here

Nothing is in progress. Next: fix nightly coverage, promote when ready, then
run the rollback drill.
