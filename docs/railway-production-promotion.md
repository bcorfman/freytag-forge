# Railway staging and production promotion

Phase 1 uses two isolated Railway channels. A successful trusted `main` CI run
uploads its exact SHA to staging and publishes the browser bundle under `/dev/`.
It cannot deploy production. Production is promoted only through the manual
`Promote staged SHA to production` workflow, which selects the newest successful
staging SHA on `main` when its optional SHA input is blank. A supplied full SHA
must have a successful `staging-deployment` status. Both deployments launch
`storygame.web_demo:app` from [`railway.toml`](../railway.toml).

The health endpoint returns `status`, `channel`, and `sha`. The workflows reject
a deployment whose reported channel or immutable revision differs from the
requested target.

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
   the production volume. Give staging a new, disposable volume only if this V1
   build needs persistence, and generate a separate session-signing secret.
   Use a distinct public domain, such as
   `https://freytag-forge-staging.up.railway.app`.
2. Set the staging service environment variables: `FREYTAG_DEPLOYMENT_CHANNEL=staging`,
   `DEMO_CORS_ALLOW_ORIGINS=https://bcorfman.github.io`, its own model/API
   credentials, and staging-only persistence/session credentials. Railway sets
   `RAILWAY_GIT_COMMIT_SHA` for CLI deployments; do not override it. Never copy
   production saves or secrets into staging. The GitHub workflow writes
   `FREYTAG_DEPLOYMENT_SHA` with `--skip-deploys` immediately before its bounded
   CLI upload; do not configure that value manually. Deployments use Railway's
   CI mode rather than detached mode, then independently verify API health.
3. Keep production in a separate Railway environment/service, with its existing
   production volume and `FREYTAG_DEPLOYMENT_CHANNEL=production`. Set
   `DEMO_CORS_ALLOW_ORIGINS=https://bcorfman.github.io` and retain only
   production credentials there. Disable Railway GitHub-push auto-deploy for
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
[`railway.toml`](../railway.toml): `GET /api/v1/health` returns `status`,
`channel`, and `sha`. The deployment identity contract is its public API URL,
channel, and Railway-reported commit SHA.

## First staging deployment

1. Complete the settings above, then merge this change to `main`.
2. Confirm the `tests` run succeeds; `Deploy staging` should run automatically.
3. Verify `https://<staging-origin>/api/v1/health` returns `channel: "staging"`
   and the exact triggering SHA. Verify `/freytag-forge/dev/` shows the persistent
   **Staging — non-production** badge and reaches only the staging API.
4. Keep the recorded V1 production deployment untouched. To promote, dispatch
   `Promote staged SHA to production` with its SHA field blank to select the
   newest successful staging deployment on `main`, then approve the protected
   production environment. Supply a full SHA only to promote an older staged
   candidate. Before uploading, the workflow prints the Railway deployment
   IDs/statuses it can see and fails closed unless it identifies a successful,
   active, or idle-sleeping known-good deployment. This is a preflight record,
   not an automatic rollback. It validates health and the root browser E2E
   before treating the promotion as successful.

## Diagnostic E2E

`Hosted demo post-deploy E2E` remains manually dispatchable for diagnosis. Its
result is not a promotion record and cannot trigger a deployment. Supply a
target API URL and deployed SHA when investigating a failed release.
