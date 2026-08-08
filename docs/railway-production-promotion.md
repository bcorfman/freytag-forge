# Railway production promotion

Railway production is promoted by the `tests` workflow; it is never deployed
merely because a commit was pushed. The `deploy-production` job waits for the
cutover contracts, fast feedback, and required coverage jobs for the exact
`main` SHA. It checks out that SHA, uploads it with the Railway CLI, and labels
the deployment `github-sha=<SHA>`.

The workflow polls Railway's deployment list for that label (or Railway's
reported commit SHA), rejects an ambiguous match, waits for `SUCCESS`, and
checks `<public-api-url>/api/v1/health`. `hosted-demo-e2e` then exercises the
deployed API from `https://bcorfman.github.io`. Only a passing E2E result
publishes the `production-promotion` commit status as `success`; all other
outcomes publish it as `failure`.

The workflow serializes the complete deployment and E2E journey for `main` in
the `production-promotion-refs/heads/main` concurrency group. It never cancels an in-progress
promotion. Job summaries and the `railway-deployment-<SHA>` and
`hosted-demo-e2e-<SHA>` artifacts retain the deployment id/URL, API URL, SHA,
health result, and E2E result.

## One-time production setup

These are operator-owned settings and cannot be established by a repository
workflow:

1. Disable Railway GitHub-push auto-deploy for the production service. The
   workflow's explicit CLI upload must be its only deployment trigger.
2. Use GitHub's protected `freytag-forge / production` environment. Restrict it to `main`
   and the intended maintainers, and add a least-privilege Railway project
   token as its `RAILWAY_TOKEN` secret.
3. Set these variables in `freytag-forge / production`:

   | Variable | Value |
   | --- | --- |
   | `RAILWAY_PROJECT_ID` | Railway project identifier |
   | `RAILWAY_SERVICE_ID` | Production web-demo service identifier |
   | `RAILWAY_PRODUCTION_ENVIRONMENT_ID` | Railway production environment identifier |
   | `RAILWAY_PUBLIC_API_URL` | Public API base URL, without a required trailing slash |
   | `RAILWAY_KNOWN_GOOD_DEPLOYMENT_ID` | Most recently verified deployment id, used as the rollback target in release evidence |

4. Update `RAILWAY_KNOWN_GOOD_DEPLOYMENT_ID` after every green promotion. If an
   E2E failure requires immediate recovery, roll back to that recorded
   deployment in Railway, then investigate the retained failed deployment
   rather than treating it as promoted.

The Railway service must preserve the health endpoint configured in
[`railway.toml`](../railway.toml): `GET /api/v1/health` returns
`{"status":"ok"}`. The deployment identity contract is its id, public API
URL, final Railway status, and either its Railway-reported commit SHA or the
CLI deployment message `github-sha=<GitHub SHA>`.

## Diagnostic E2E

`Hosted demo post-deploy E2E` remains manually dispatchable for diagnosis. Its
result is not a promotion record and cannot trigger a deployment. Supply a
target API URL and deployed SHA when investigating a failed release.
