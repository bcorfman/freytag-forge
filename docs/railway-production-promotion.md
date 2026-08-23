# Railway staging and production promotion

> V2 cutover: deployments launch only `storygame.web_demo:app`. No V1 runtime or saves are part of the hosted service; immutable authored material under `data/` is retained for V2.

Phase 1 uses two isolated Railway channels. A successful trusted `main` CI run
uploads its exact SHA to staging and publishes the browser bundle under `/dev/`.
It cannot deploy production. Production is promoted only through the manual
`Promote staged SHA to production` workflow, which selects the newest successful
staging SHA on `main` when its optional SHA input is blank. A supplied full SHA
must have a successful `staging-deployment` status. Both deployments launch
`storygame.web_demo:app` from [`railway.toml`](../railway.toml).

The health endpoint returns `status`, `runtime`, `channel`, and `sha`; the
version endpoint returns `api`, `runtime`, `channel`, and `sha`. The workflows
reject a deployment unless both endpoints identify the expected V2 runtime,
channel, and immutable revision.

The channel workflows serialize deployments and never cancel a running
promotion. The staging workflow records the `staging-deployment` commit status
only after its Railway health identity passes and the `/dev/` Pages artifact
has been published. The production workflow waits for its root Pages publish
before it runs the browser E2E.

## One-time Railway and GitHub setup

These are operator-owned settings and cannot be established by a repository
workflow:

1. In Railway, create a separate **staging environment** (or an entirely
   separate staging service if your Railway plan requires it). Do not duplicate
   the production volume. Give staging a new, disposable volume for its runtime
   snapshots.
   Use a distinct public domain, such as
   `https://freytag-forge-staging.up.railway.app`.
2. Set the staging service environment variables: `FREYTAG_DEPLOYMENT_CHANNEL=staging`,
   its own model/API credentials. The hosted adapter allows the Pages origin
   `https://bcorfman.github.io`. Railway sets `RAILWAY_GIT_COMMIT_SHA` for CLI
   deployments. Never copy production saves or secrets into staging. The GitHub workflow writes
   `FREYTAG_DEPLOYMENT_SHA` with `--skip-deploys` immediately before its bounded
   CLI upload; do not configure that value manually. Deployments use Railway's
   CI mode rather than detached mode, then independently verify both identity
   endpoints.
3. Keep production in a separate Railway environment/service, with its existing
   production volume and `FREYTAG_DEPLOYMENT_CHANNEL=production`. Set
   only production model/API credentials there. Disable Railway GitHub-push
   auto-deploy for
   both channels: the workflows' explicit CLI uploads must be their only
   deployment trigger.
4. In GitHub, create protected environments `freytag-forge / staging` and
   `freytag-forge / production`. Restrict production to intended maintainers.
   Put a least-privilege `RAILWAY_TOKEN` secret in each environment. The token
   must be able to deploy only the intended Railway project/service.
5. Set these variables in `freytag-forge / staging`:

   | Variable | Value |
   | --- | --- |
   | `RAILWAY_PROJECT_ID` | Railway project identifier |
   | `RAILWAY_SERVICE_ID` | Staging web-demo service identifier |
   | `RAILWAY_STAGING_ENVIRONMENT_ID` | Railway staging environment identifier |
   | `RAILWAY_PUBLIC_API_URL` | Staging public API base URL |

6. Set these variables in `freytag-forge / production`:

   | Variable | Value |
   | --- | --- |
   | `RAILWAY_PROJECT_ID` | Railway project identifier |
   | `RAILWAY_SERVICE_ID` | Production web-demo service identifier |
   | `RAILWAY_PRODUCTION_ENVIRONMENT_ID` | Railway production environment identifier |
   | `RAILWAY_PUBLIC_API_URL` | Public API base URL, without a required trailing slash |
7. Set GitHub repository variables `VITE_STAGING_API_BASE_URL` and
   `VITE_PRODUCTION_API_BASE_URL` to the matching distinct public origins.
   The Pages workflow embeds these values at build time and fails if either
   channel bundle contains the other channel's origin.
 
The Railway service must preserve the health endpoint configured in
[`railway.toml`](../railway.toml). The deployment identity contract is its
public API URL, API/runtime version, channel, and immutable SHA.

## First staging deployment

1. Complete the settings above, then merge this change to `main`.
2. Confirm the `tests` run succeeds; `Deploy staging` should run automatically.
3. The staging workflow verifies both API identity endpoints, publishes the
   Pages bundle under `https://bcorfman.github.io/freytag-forge/dev/`, runs the
   live API/Pages/session smoke test, and then runs the cross-genre staging
   evaluation. It records `staging-deployment` only if those gates pass.
4. To promote, dispatch `Promote staged SHA to production` with its SHA field
   blank to select the newest successful staging deployment on `main`, then
   approve the protected production environment. Supply a full SHA only to
   promote an older staged candidate. Before uploading, the workflow prints
   Railway deployment IDs/statuses and fails closed unless it identifies a
   successful, active, or idle-sleeping known-good deployment. This is a
   preflight record, not an automatic rollback.
5. Production deployment verifies both API identity endpoints, publishes the
   root Pages bundle, then runs the live API/Pages/session smoke test. Only
   after those steps does it publish the `production-promotion` commit status.

## Diagnostic E2E

`Hosted demo post-deploy E2E` remains manually dispatchable for diagnosis. Its
result is not a promotion record and cannot trigger a deployment. Supply the
deployed API URL and exact deployed commit SHA; it checks the matching Pages
`deployment.json`, API identity, session creation, and one accepted turn.
