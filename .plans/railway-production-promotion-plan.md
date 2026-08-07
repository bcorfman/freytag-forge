# Railway production promotion plan

## Outcome

Production is a promotion, not a side effect of pushing a commit. A commit may
reach Railway only after the required checks for that exact `main` commit have
passed; the deployment is accepted only after the hosted-demo E2E journey has
passed against it.

```text
pull request checks pass
        -> merge to main
        -> required main CI passes for the merged SHA
        -> GitHub Actions deploys that SHA to Railway
        -> Railway reports the deployment healthy
        -> hosted-demo E2E runs against the deployed API
        -> production promotion is recorded green
```

The current GitHub Pages client remains static hosting. This plan gates the
Railway API it calls; it does not make Railway responsible for GitHub Pages.

## Prerequisites and decisions

- [ ] Disable Railway's GitHub-push auto-deploy for the production service.
  Otherwise it can race the required checks and this gate is cosmetic.
- [ ] Create a GitHub `production` Environment, protected to the intended
  deployment branch (`main`) and maintainers. Use its audit trail for every
  production promotion.
- [ ] Store a least-privilege Railway token as the protected
  `RAILWAY_TOKEN` environment secret. Store non-secret project, service, and
  production-environment identifiers as GitHub variables (or environment
  secrets if local policy requires).
- [ ] Decide and document Railway's successful-deployment signal: deployment
  id, committed SHA, public API URL, and health status. The orchestrator must
  be able to poll it rather than assuming that submitting a deployment worked.
- [ ] Keep a known-good Railway deployment id available for rollback. A failed
  E2E must never silently count as a successful promotion.

## Implementation

### 1. Make CI the promotion authority

- [ ] Keep the existing required pull-request checks in branch protection.
- [ ] In the workflow that runs on `push` to `main`, add a `deploy-production`
  job with `needs` covering every required merge-validation job (including the
  required coverage gate). Do not use a separate concurrent `push` workflow
  for deployment.
- [ ] Scope that job to `main`, `if: success()`, and `environment: production`.
  Set a repository-wide production concurrency group with
  `cancel-in-progress: false`, so an older in-flight deployment cannot be
  superseded halfway through its verification.
- [ ] Check out and deploy the triggering immutable SHA, not a branch name
  resolved later. Record the SHA in the deployment summary and status.

### 2. Trigger and verify Railway

- [ ] Replace Railway's automatic GitHub deploy with an explicit Railway API
  (or supported Railway CLI) deployment from `deploy-production`.
- [ ] Poll the resulting deployment until Railway reports success, failure, or
  a bounded timeout. Fail the GitHub job on failure or timeout and include the
  Railway deployment URL/id in the summary.
- [ ] Verify the reported deployment SHA is the GitHub Actions triggering SHA.
  If Railway cannot expose that identity, attach it as deployment metadata and
  reject any ambiguous result.
- [ ] Call `GET /api/v1/health` on the deployed public API before declaring the
  deployment ready.

### 3. Make E2E part of promotion completion

- [ ] Run `tests/test_hosted_demo_e2e.py` as a `hosted-demo-e2e` job that
  `needs: deploy-production`; pass the API URL returned by the verified Railway
  deployment and `https://bcorfman.github.io` as the browser origin.
- [ ] Preserve the existing manual-dispatch E2E workflow for diagnosis, but do
  not use it as the normal production gate. The normal gate must be chained by
  `needs`, not depend on a best-effort repository-dispatch event.
- [ ] Publish the E2E output and its tested API URL/SHA as workflow artifacts
  or job summary. This provides a compact release record for continuity,
  save/load, opening-cleanliness, CORS, and narration failures.
- [ ] Mark the production deployment successful only when the E2E job passes.
  On E2E failure, surface a failed deployment status and retain the failed
  Railway deployment for diagnosis; roll back using the recorded known-good
  deployment when service policy requires immediate recovery.

### 4. Test the gate itself

- [ ] Exercise a deliberately failing required CI check on a non-production
  branch and confirm no Railway deployment request is made.
- [ ] Exercise a Railway deployment failure and confirm hosted E2E does not
  start.
- [ ] Exercise a hosted-E2E failure and confirm the workflow is red, its
  deployment/SHA evidence is retained, and no green promotion status is
  published.
- [ ] Exercise one successful promotion and verify all records name the same
  commit SHA: merge, CI, Railway deployment, health check, and E2E.

## Acceptance criteria

- [ ] Railway receives no production deployment request before every required
  CI job for the exact `main` SHA is green.
- [ ] A Railway success alone is insufficient: the hosted-demo E2E journey must
  pass before the production promotion is green.
- [ ] Failed checks, failed deployments, and failed E2E runs leave actionable
  links, the tested SHA, and a recoverable rollback target.
- [ ] The manual hosted E2E remains available for investigation without being
  mistaken for the release gate.
