# Railway staging and production promotion

Only `storygame.web_demo:app` is deployed. Staging and production are isolated:
trusted `main` deploys the tested SHA to Railway staging and Pages `/dev/`;
**Promote staged SHA to production** manually deploys a SHA with a successful
`staging-deployment` status to production and root Pages.

The API health and version endpoints must report the expected V2 runtime,
channel, and immutable SHA. Pages publishes matching `deployment.json` metadata.
Workflows fail closed on an identity mismatch and serialize deployments without
cancelling an active promotion.

## One-time setup

1. Create separate Railway staging and production environments/services with
   separate volumes, domains, credentials, and model access. Never copy
   production saves or secrets to staging.
2. Set `FREYTAG_DEPLOYMENT_CHANNEL=staging` or `production` in the matching
   service. Disable Railway GitHub-push auto-deploy: workflow CLI uploads are
   the deployment trigger.
3. Create protected GitHub environments `freytag-forge / staging` and
   `freytag-forge / production`; give each a least-privilege `RAILWAY_TOKEN`.
4. Configure per-channel `RAILWAY_PROJECT_ID`, `RAILWAY_SERVICE_ID`,
   `RAILWAY_*_ENVIRONMENT_ID`, and `RAILWAY_PUBLIC_API_URL` variables. The
   workflow writes `FREYTAG_DEPLOYMENT_SHA`; do not set it manually.
5. Configure `VITE_STAGING_API_BASE_URL` and `VITE_PRODUCTION_API_BASE_URL`.
   The Pages workflow rejects a bundle containing the other channel's origin.

## Release flow

1. Merge to `main`; required tests then deploy staging, verify API and Pages
   identity, run hosted E2E and staging evaluation, and publish
   `staging-deployment` only on success.
2. Review the staged `/dev/` experience and dispatch the protected production
   workflow. Blank SHA chooses the newest successful staged commit; a supplied
   full SHA must already have the successful status.
3. Production verifies API identity, publishes root Pages, runs hosted E2E, and
   records `production-promotion` only after all gates pass.

`Hosted demo post-deploy E2E` is diagnostic only. Supply its deployed API URL
and exact SHA; it verifies Pages metadata, API identity, session creation, and
one accepted turn. It cannot deploy or promote.
