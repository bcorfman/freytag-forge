# Railway staging and production promotion

Only `storygame.web_demo:app` is deployed. It serves `/api/v1/health`,
`/api/v1/version`, `/api/v1/session`, `/api/v1/turn` and `/api/v1/game-break`.
Staging and production are isolated: trusted `main` deploys the tested SHA to
Railway staging and Pages `/dev/`; **Promote staged SHA to production** is
dispatched by hand and deploys to production and root Pages. Deployments are
serialized and do not cancel an active promotion.

The workflow files are the authority:
[`test.yml`](../.github/workflows/test.yml),
[`promote-production.yml`](../.github/workflows/promote-production.yml) and
[`deploy-frontend-pages.yml`](../.github/workflows/deploy-frontend-pages.yml).

## One-time setup

1. Create separate Railway staging and production environments/services with
   separate volumes, domains, credentials, and model access. Never copy
   production saves or secrets to staging.
2. Set `FREYTAG_DEPLOYMENT_CHANNEL=staging` or `production` in the matching
   service. Disable Railway GitHub-push auto-deploy: workflow CLI uploads are
   the deployment trigger.
3. Create the GitHub environments `freytag-forge / staging` and
   `freytag-forge / production`; give each a least-privilege `RAILWAY_TOKEN`.
   The workflows name these environments but do not rely on protection rules.
   Check the repository settings before assuming an environment gates anything.
4. Configure per-channel `RAILWAY_PROJECT_ID`, `RAILWAY_SERVICE_ID`,
   `RAILWAY_*_ENVIRONMENT_ID`, and `RAILWAY_PUBLIC_API_URL` variables. The
   workflow writes `FREYTAG_DEPLOYMENT_SHA`; do not set it manually.
5. Configure `VITE_STAGING_API_BASE_URL` and `VITE_PRODUCTION_API_BASE_URL`.
   The Pages workflow rejects a bundle containing the other channel's origin.

## What staging verifies

A merge to `main` runs the static checks and test shards, then deploys the SHA.

| Check | Runs against | What it shows |
| --- | --- | --- |
| `api-identity` | Deployed staging API | Health and version report the staging channel, scene runtime and this SHA |
| `pages-identity` | Published Pages `/dev/deployment.json` | The frontend reports the staging channel and this SHA |
| `adapter-contract` | The CI runner only | `tests/test_web_demo.py` and `tests/test_cloudflare_transport.py` pass for this checkout; it does not call the deployed service |

The `staging-evaluation-<sha>` artifact records each check's outcome and an
overall `result`. It is written when the deploy fails too. The
`staging-deployment` commit status is `success` only when the deploy and
evaluation jobs both succeed.

**No workflow runs hosted gameplay E2E.** A green `staging-deployment` status
says nothing about gameplay on the deployed service. Hosted E2E is a separate,
billed, manual step: see
[staged deployment and hosted E2E](testing-runbook/hosted-e2e.md).

## Promotion

1. Review the staged `/dev/` experience, then dispatch the promotion workflow.
   A blank SHA picks the newest successfully staged commit.
2. The SHA must have a successful `staging-deployment` status. A SHA that has
   never been in production also needs a successful `coverage-nightly` run on
   that exact SHA; dispatching `coverage-nightly` on `main` covers `main`'s
   head. A SHA with any successful `production-promotion` status in its history
   skips the nightly requirement, so a previous release can be restored.
3. Before changing anything, the run summary records a Railway deployment ID,
   the live API SHA, the live frontend SHA and, when the API SHA is a usable
   target, the rollback command.
4. Production verifies API identity, publishes root Pages and verifies the root
   `deployment.json`. Only then does it record a successful
   `production-promotion` status.

Publishing one Pages channel keeps the other channel's files, including its
`deployment.json` when the published copy is valid.

## Rollback

Roll back by promoting the previous production SHA. This redeploys the API and
builds the matching frontend through the same path as any release. The person
who owns rollback is named in the
[agent workflow guide](agent-workflow-guide.md#ownership).

1. Find the target. In the summary of the bad promotion run, take **Previous
   live production API SHA** and its printed command. If it says `unknown`, or
   the record says it is not a rollback target, pick the newest earlier commit
   with a successful `production-promotion` status:
   `gh api "repos/{owner}/{repo}/commits/<sha>/statuses"`.
   Never leave the SHA blank: that promotes the newest staged commit.
2. Run it:

   ```bash
   gh workflow run promote-production.yml --ref main -f sha=<previous 40-character SHA>
   gh run list --workflow promote-production.yml --limit 1
   gh run watch <run-id> --exit-status
   ```

3. Confirm both halves report the target SHA: `GET /api/v1/version` on the
   production API, and `deployment.json` at the root of the Pages site. Then
   open the site, start a session and take one turn.
4. Record the bad SHA, the restored SHA and both run links in the plan or PR.

What can stop or limit it:

- **No eligible Railway deployment.** The workflow stops before changing
  anything unless one of the last 100 production deployments is `SUCCESS`,
  `ACTIVE` or `SLEEPING`. If it stops here, restore the API from the Railway
  dashboard using the deployment ID in an earlier promotion summary, then
  publish the matching frontend:
  `gh workflow run deploy-frontend-pages.yml --ref main -f channel=production -f sha=<sha>`.
  Verify as in step 3. This path records no `production-promotion` status.
- **The workflow comes from `main`.** The code is the old SHA; the steps that
  deploy it are the current ones.
- **Saved sessions are not rolled back.** A save whose story or save-format
  version does not match is refused, not converted. Sessions kept outside a
  persistent volume (the default is under `/tmp`) do not survive a redeploy.
- **Settings are not rolled back.** Railway and GitHub variables, and the
  Cloudflare Worker, keep their current values and versions.

### Drill

**This procedure has not been exercised.** Treat rollback as unproven until a
drill has run: promote an earlier proven SHA, verify it as in step 3, promote
the current SHA again and verify that too. A drill changes live production, so
the owner chooses when to run it. When it passes, replace this paragraph with
the run links.
