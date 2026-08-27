# Testing runbook

## Phase 1 knowledge-catalog migration and Scene 1A timeline

**Purpose:** Verify the declarative catalog covers every Continuity Initiative
fact and executable realization, rejects malformed ownership/visibility, and
keeps the Scene 1A opening and unrecovered warning distinct.

**Setup / seed:**

- Python 3.12 dependencies installed with `uv sync --group dev`.
- Run from the repository root; pytest temporary files belong under `/tmp`.

**Safe actions:**

- The tests load the checked-in package and copy it into pytest temporary
  directories before corrupting fixtures.

**Destructive or external actions:**

- None for the deterministic suite. The optional browser command creates a
  disposable staging session and may make billed model calls.

**Steps:**

1. Run the focused package and Phase 1 persistence tests while editing the
   catalog, loader, or save compatibility.
2. Run the full suite after formatting.
3. After the implementation revision is deployed to staging, run the opt-in
   browser timeline probe; retain its redacted artifact.

**Verify:**

```bash
TMPDIR=/tmp uv run pytest -q
source .env && cd frontend && E2E_KNOWLEDGE_TIMELINE=1 npm run test:e2e -- --grep @knowledge-timeline
```

Expected: deterministic tests prove that opening entry knowledge is committed,
the warning is absent until its source is selected, and malformed catalogs fail
closed. The staged probe records each turn and rejects early warning/JANUS,
unearned patrol tape, and generic repeated follow-up narration.

**Cleanup:** Delete ignored `artifacts/e2e-knowledge-timeline.{json,md}` when
the evidence is no longer needed.

**Notes:** The browser probe is intentionally not run against an undeployed
local schema change. Record its observed revision and outcome here after the
staging run; this regression contract carries through Phases 2–5.

Last verified locally: 2026-08-27 — `uv run ruff check --fix .`, `uv run ruff
format .`, and `TMPDIR=/tmp uv run pytest -q` passed with 89 tests and 90.86%
coverage. The staged browser command remains pending deployment of this
revision; do not treat local schema evidence as a staging result.

## Declarative knowledge package loading

**Purpose:** Verify the Phase 0 knowledge catalog, safe scene frames, immutable
indexes, and fail-closed source/effect validation without changing provider
context behavior.

**Setup / seed:**

- Python 3.12 dependencies installed with `uv sync --group dev`.
- Run from the repository root; use `/tmp` for pytest temporary files.

**Safe actions:**

- Tests copy the Continuity Initiative package into pytest temporary paths.

**Destructive or external actions:**

- None.

**Steps:**

1. Run the full Python suite after editing knowledge models, loader validation,
   or `knowledge.yaml`.
2. Apply Ruff autofix and formatting, then rerun the full suite.

**Verify:**

```bash
TMPDIR=/tmp uv run pytest -q
```

Expected: all tests pass with repository coverage at or above 90%.

**Cleanup:** None; pytest temporary files are under `/tmp`.

**Notes:** A focused `tests/test_markdown_story_package.py` run passed all 16
tests on 2026-08-27 but exited nonzero solely because the global 90% coverage
gate measured 31.67%; use the full suite for a passing verification.

After merged SHA `fb49aea9a7bcae79c20c53bb6f13f7fc72b647b4` completed the
staging deployment, the opt-in browser gate passed: `source .env && cd
frontend && E2E_KNOWLEDGE_TIMELINE=1 npm run test:e2e -- --grep
@knowledge-timeline` ran one Chromium test successfully in 10.3 seconds on
2026-08-27. It wrote ignored local evidence to
`artifacts/e2e-knowledge-timeline.{json,md}`. This remote run creates a staging
session and may make billed model calls; retain the artifacts while evaluating
the phase and delete them when no longer needed. Chrome DevTools MCP was not
available in the verification session, so Playwright supplied the browser
evidence.

## Route-backed continuity-initiative progression

**Purpose:** Verify that the revised five-file story package loads with executable storylet routes, activates only eligible scene-local guidance, and rejects durable effects that are not route-authorized.

**Setup / seed:**

- Python 3.12 dependencies installed with `uv sync --group dev`.
- Run from the repository root with `/tmp` as pytest's temporary directory.

**Safe actions:**

- Tests use copied package fixtures and local SQLite temporary files only.

**Destructive or external actions:**

- None.

**Steps:**

1. Run the Markdown-package, context, and progression tests after changing the story package or route validator.
2. Run the full suite before handoff because the coverage gate is repository-wide.

**Verify:**

```bash
TMPDIR=/tmp uv run pytest -q
```

Expected: all tests pass with the project coverage gate at or above 90%.

**Cleanup:** None; pytest temporary files are under `/tmp`.

**Notes:** Durable LLM effects must be submitted as an active `SL-*` event with a route realization ID and the exact reviewed operations. `entry_text` is an opening seed, not the full scene prose.

Last verified: 2026-08-26 — `TMPDIR=/tmp uv run pytest -q` completed with 58 passing tests and 90.17% coverage; Ruff autofix and formatting also passed.

## Frontend structured-turn rendering unit tests

**Purpose:** Verify that the browser renderer preserves accepted structured
narration, speech, and action blocks, while retaining the legacy `lines`
fallback for non-interaction turns.

**Setup / seed:**

- Node.js and the frontend dependencies installed with `npm ci` or `npm install`
  from `frontend/`.
- No network, credentials, seed data, or deployed service required.

**Safe actions:**

- Running the Node unit tests is read-only apart from normal local test caches.

**Destructive or external actions:**

- None.

**Steps:**

1. Change into `frontend/`.
2. Run the focused unit-test command.

**Verify:**

```bash
cd frontend && npm test
```

Expected: Node reports three passing `turn_rendering` tests and exits with code
0.

Last verified: 2026-08-26 — 3 passing tests, exit code 0.

**Cleanup:** None.

**Notes:** This is a renderer-only smoke test. It does not call FastAPI,
Cloudflare, or Workers AI.

## Full Markdown scene-runtime suite

**Purpose:** Verify package loading, context scoping, fact-backed progression,
game-break persistence, FastAPI behavior, Cloudflare transport contracts, and
concept-level scene-roleplay checks.

**Setup / seed:**

- Python 3.12 dependencies installed with `uv sync --group dev`.
- Use `/tmp` for pytest temporary files in this WSL environment.

**Safe actions:**

- The suite uses temporary SQLite files and local package fixtures only.

**Destructive or external actions:**

- None. Do not set Cloudflare credentials for this suite; its transport tests
  use injected responses.

**Steps:**

1. Run the full Python suite from the repository root.

**Verify:**

```bash
TMPDIR=/tmp uv run pytest -q
```

Expected: all tests pass and the project-wide coverage gate remains at or above
90%.

Last verified: 2026-08-26 — 53 passed, 91.04% coverage.

**Cleanup:** None; pytest temporary files are under `/tmp`.

**Notes:** A focused pytest invocation can exit nonzero solely because the
global 90% coverage gate applies. Use the full suite for a passing coverage
verification.

## Frontend production build

**Purpose:** Verify that the Vite bundle builds from the current React/browser
source and package lock.

**Setup / seed:**

- Node.js and frontend dependencies installed from `frontend/`.

**Safe actions:**

- Produces a local ignored `frontend/dist/` build artifact.

**Destructive or external actions:**

- The build overwrites local `frontend/dist/`; do not treat that directory as
  hand-authored source.

**Steps:**

1. Change into `frontend/`.
2. Build the bundle.

**Verify:**

```bash
cd frontend && npm run build
```

Expected: Vite reports a successful build and writes `dist/index.html` plus
hashed assets.

Last verified: 2026-08-26 — build completed successfully.

**Cleanup:** Remove `frontend/dist/` only when a clean local workspace is
needed; it is regenerated by the command.

**Notes:** This does not call the deployed FastAPI service.

## Manual Chromium scene-runtime E2E categories

**Purpose:** Exercise the real frontend and Cloudflare-backed scene API by
category: smoke, spine, storylets, NPC knowledge, world-state follow-up, and
safety.

**Setup / seed:**

- Run `npx playwright install chromium` once from `frontend/`.
- From the repository root, load `.env` before changing into `frontend/`; it
  exports `E2E_API_BASE_URL` and `E2E_DEPLOYMENT_CHANNEL` for the staging
  deployment. There is no `frontend/.env` (only an example file).
- Set `E2E_API_BASE_URL` to a deployed FastAPI service that reports
  `runtime: "scene-v1"` from `/api/v1/version`.
- Set `E2E_DEPLOYMENT_CHANNEL` to the matching deployment channel.

**Safe actions:**

- `--list` validates E2E discovery without opening a browser or calling the
  deployed API.

**Destructive or external actions:**

- A real E2E run creates remote sessions and makes billed Cloudflare AI calls.
  Use only the intended environment and review ignored `artifacts/e2e-*.{json,md}`.

**Steps:**

1. Confirm the API version reports `scene-v1`.
2. Run all E2E tests or select one category with `--grep @<tag>`.

If Playwright's automatic Vite startup stalls, start Vite separately from the
repository root after loading `.env`; pass the corresponding public Vite
variables explicitly, then run Playwright in a second terminal:

```bash
source .env
cd frontend
VITE_API_BASE_URL="$E2E_API_BASE_URL" VITE_DEPLOYMENT_CHANNEL="$E2E_DEPLOYMENT_CHANNEL" npm run dev -- --host 127.0.0.1 --port 4173
```

The Vite server must be restarted after changing these variables. A manually
started server without them renders `VITE_API_BASE_URL is not configured.`

**Verify:**

```bash
source .env && cd frontend && npm run test:e2e -- --grep @spine
```

Expected: Chromium completes the selected category and writes an
`artifacts/e2e-spine.{json,md}` evaluation report. The `@smoke` category also
writes `artifacts/e2e-smoke-loaded.png` as loaded-page visual evidence.

Last verified safely: 2026-08-26 — Playwright discovered six tagged tests using
`E2E_API_BASE_URL=http://127.0.0.1:9999 npx playwright test --list`; no live
target was configured before the root `.env` was loaded.

**Cleanup:** Delete ignored `artifacts/e2e-*.json`, `artifacts/e2e-*.md`, and
Playwright trace artifacts when they are no longer needed.

**Notes:** The production service observed on 2026-08-26 reported `runtime:
"v2"` and rejected scene-runtime `player_input` requests. It is not a valid
target until the scene-v1 FastAPI deployment is promoted. On 2026-08-26,
running from `frontend/` before sourcing the root `.env` failed before browser
launch because `E2E_API_BASE_URL` was unset; source from the repository root.
After sourcing it, the staging version endpoint reported `api: "v1"`,
`runtime: "scene-v1"`, and `channel: "staging"`, but the focused `@smoke`
run failed: session creation and the opening rendered, then the submitted turn
returned `{}` and the UI showed `narration service rejected the turn`. Evidence:
`artifacts/e2e-smoke.json`, `artifacts/e2e-smoke-loaded.png`, and the retained
Playwright trace. A direct reproduction returned Railway HTTP 502 with the
same safe detail; the deployed API does not expose the Worker error code or
headers needed to classify the cause.

The source adapter now retries exactly once without `response_format` when the
Worker returns its documented `AI_JSON_MODE_REJECTED` code, while preserving
fail-closed behavior for all other Worker errors. `TMPDIR=/tmp uv run pytest
-q` passed on 2026-08-26 (55 passed, 90.69% coverage). The JSON-mode fallback
was deployed to staging, but did not resolve the failure. A manually configured
Vite server confirmed the frontend environment fix on 2026-08-26; staging then
failed in 767 ms with the original empty turn payload.

The staging revision was subsequently verified to match the JSON-mode fallback
source SHA, yet the same 502 remained. This confirms a different typed Worker
failure. The next source revision returns its safe Worker code in the
`X-Narration-Error-Code` response header; after deploying it, repeat the direct
session/turn probe and use that header to correct the Worker portal setting or
upstream AI condition. `TMPDIR=/tmp uv run pytest -q` then passed with 56 tests
and 90.83% coverage.

The deployment dashboard can be newer than the API's reported SHA because that
endpoint reads an environment value. The next diagnostic revision always emits
`X-Narration-Error-Code: UNKNOWN` for an untyped Worker HTTP failure and
forwards `X-Trace-ID` and `X-Worker-Revision` when the Worker supplies them.
This distinguishes an active adapter with a nonconforming Worker/upstream error
from an older deployed adapter. `TMPDIR=/tmp uv run pytest -q` passed with 57
tests and 91.11% coverage.

The confirmed cause is Cloudflare edge error 1010, not a Worker or Workers AI
error: the real 4,419-byte scene-context request sent by Python `urllib`
received HTTP 403, plain text `error code: 1010`, and no Worker headers before
the Worker executed. A small request using the same credentials succeeded,
including with `response_format`. Cloudflare documents 1010 as Browser
Integrity Check rejecting a client signature. The adapter now sends a standard
browser `User-Agent`; the same real scene-context call then succeeded directly
against the configured Worker. Do not disable Browser Integrity Check or alter
Worker credentials for this failure. A focused transport run has 7 passing
tests but intentionally exits nonzero under the repository's whole-project
coverage gate; use the full suite below for the passing coverage result.

## LLM scene-canon E2E acceptance

**Purpose:** Judge each reached scene’s narration against its scene-local plot, storylet guidance/routes, pacing, and world canon.

**Setup / seed:**

- A working scene-v1 API target plus `OPENAI_API_KEY` for the independent judge.
- The test reads the five story sources locally and sends only the current scene’s canon to the judge.

**Safe actions:**

- Creates a remote game session and makes model/judge calls; it does not alter package sources or a deployed configuration.

**Destructive or external actions:**

- Billed external model calls. Run deliberately against the intended environment.

**Steps:**

1. Configure `E2E_API_BASE_URL`, `E2E_DEPLOYMENT_CHANNEL`, and `OPENAI_API_KEY`.
2. Run the opt-in full-spine acceptance category.

**Verify:**

```bash
source .env && cd frontend && npm run test:e2e -- --grep @llm-canon
```

Expected: every reached scene receives a passing verdict for canon consistency, scene locality, progressive revelation, richness, and protected-knowledge safety; `artifacts/e2e-llm-canon.{json,md}` records the evidence.

**Cleanup:** Remove generated ignored E2E artifacts if they are no longer useful.

**Notes:** This is intentionally separate from deterministic state assertions. It skips when `OPENAI_API_KEY` or `E2E_TEST_CLOCK_SECONDS` is absent. Start the local API with `FREYTAG_ALLOW_TEST_CLOCK=1`, then use `E2E_TEST_CLOCK_SECONDS=120`; Vite adds this value to the ordinary JSON turn body, avoiding a CORS preflight. Each turn is bounded to 30 seconds (override with `E2E_TURN_TIMEOUT_MS`) and partial progress is written to `artifacts/e2e-llm-canon-progress.{json,md}`.

Last verified: 2026-08-27 — after staging reported runtime `scene-v1` for the merged SHA, `source .env && cd frontend && npm run test:e2e -- --grep @llm-canon` completed all eight turns and reached the independent judge. The judge failed scene `1A`: narration leaked JANUS and broader system purpose, rushed into later-scene beats, and did not consistently respond to the player action from the Thomas home. Treat this as a scene-context/prompt safety defect, not a transport or fact-validation failure. Preserve freeform LLM-proposed new facts; canonical package facts remain route-authorized, and repeated identical canonical assertions are no-ops.

On 2026-08-27, the same command again reached the judge but failed at scene `1A`. Its eight recorded turns remained in `1A` while accepting future-scene player requests, including a dead drop, facility entry, JANUS, a purge clock, and a relay. The source prompt now states that the scene object is exhaustive and that player input cannot authorize future names, places, objectives, or plot beats; deploy that revision before treating the live acceptance check as resolved.

## Deterministic E2E pacing clock

**Purpose:** Trigger declared pacing pressure in browser tests without waiting for wall-clock time.

**Setup / seed:**

- Start only a local/API test server with `FREYTAG_ALLOW_TEST_CLOCK=1`.
- Start Vite with `E2E_TEST_CLOCK_SECONDS=120`; this adds `test_clock_seconds` to JSON turn requests.

**Safe actions:**

- The test-clock body field is ignored unless the API process explicitly opted in.

**Destructive or external actions:**

- None; do not enable this environment variable on a deployed API.

**Steps:**

1. Start the opted-in local API and Vite test server.
2. Run the tagged Playwright test.

**Verify:**

```bash
cd frontend && E2E_TEST_CLOCK_SECONDS=120 npm run test:e2e -- --grep @timed-events
```

Expected: the turn response reports `pressure_1a` in `fired_pacing_event_ids` without a two-minute wait.

**Cleanup:** Unset `FREYTAG_ALLOW_TEST_CLOCK` after local testing.

**Notes:** The application accepts `test_clock_seconds` only with explicit server-side opt-in and bounds it to 0–3600 seconds. The legacy header remains supported for non-browser harnesses.

## Story Feed root page — local Playwright QA

**Purpose:** Verify the root Story Feed UI's loading, loaded, and service-error
states; its command form's valid, blank, and long-input behavior; and its
desktop/mobile layout without creating a remote session.

**Setup / seed:**

- Node dependencies installed in `frontend/`; Chromium installed with
  `npx playwright install chromium`.
- The test intercepts the service identity, session, and turn requests with
  local fixtures. It does not need a test account, seed data, or a deployed API.

**Safe actions:**

- Starts a local Vite server and writes ignored screenshot evidence under
  `artifacts/`. No external API call or state change occurs.

**Destructive or external actions:**

- None. The command overwrites its generated local evidence files.

**Steps:**

1. Run the focused `@page-qa` Playwright test from `frontend/`.
2. Review the loading, loaded desktop, loaded mobile, and error screenshots.

**Verify:**

```bash
cd frontend && E2E_API_BASE_URL=http://127.0.0.1:9999 npm run test:e2e -- --grep @page-qa
```

Expected: one passing Chromium test; screenshots at
`artifacts/e2e-page-qa-{loading-1440,loaded-1440,loaded-375,error-375}.png`.

Last verified: 2026-08-26 — one Chromium test passed in 3.5 seconds using
`E2E_API_BASE_URL=http://127.0.0.1:9999 E2E_DEPLOYMENT_CHANNEL=production
npm run test:e2e -- --grep @page-qa --timeout=60000` from `frontend/`.

**Cleanup:** Keep the ignored evidence while it is useful; remove only the
generated `artifacts/e2e-page-qa-*.png` files when no longer needed.

**Notes:** The page has no user-auth UI boundary; authentication/authorization
must be verified against the deployed service separately. The responsive form
switches to a single column at 720px. Blank input is ignored client-side;
long input is passed through to the service contract without a client limit.

## Story Feed staging browser audit

**Purpose:** Audit the deployed Story Feed page with Chrome DevTools evidence
at desktop, tablet, and mobile sizes, including console, network, and cold-load
performance signals.

**Setup / seed:**

- The global `chrome-devtools` MCP server must be configured with a usable local
  Chromium executable.
- The page creates a staging session during initialization; no player turn is
  submitted for this audit.

**Safe actions:**

- Navigate and inspect the staging page, capture screenshots/traces, and read
  console/network activity. The normal page initialization creates a remote
  staging session.

**Destructive or external actions:**

- Does not deploy or alter story state, but does call the staging session API.

**Steps:**

1. Open the staging page with Chrome DevTools MCP.
2. Capture full-page screenshots at 1440px, 768px, and 375px widths.
3. Inspect console errors, document/style/script/fetch requests, and collect a
   cold-load trace.

**Verify:**

Expected: no console errors or failed requests; LCP under 2.5 s and CLS under
0.1. INP requires a user interaction and is not available from this load-only
trace.

Last verified: 2026-08-26 — screenshots saved as
`artifacts/browser-qa-staging-{desktop,tablet,mobile}.png`; console had no
errors; all ten observed document, asset, version, and session requests were
200/304. The cold-load trace recorded LCP 130 ms and CLS 0.01 in
`artifacts/browser-qa-staging-trace.json.gz`.

**Cleanup:** Keep ignored `artifacts/browser-qa-staging-*` evidence while it is
useful; remove it when the audit record is no longer needed.

**Notes:** Lighthouse initially failed only `meta-description` (SEO score 91),
because `frontend/index.html` had no description meta tag. The local source now
defines it. On 2026-08-26, `cd frontend && npm run build` passed and a local
Chrome DevTools check of the built page returned the description text. Local
Lighthouse no longer flagged `meta-description`; its remaining independent
failures were `robots-txt` and `llms-txt`. The staging result remains pending a
frontend deployment, so do not mark the live SEO finding resolved yet.

## Cloudflare narration Worker source audit

**Purpose:** Check the portal-exported Worker against the Railway adapter's
request and typed-error contract without changing the deployed Worker.

**Setup / seed:** `.plans/cloudflare.js` is a portal copy. Source the root
`.env`, which supplies `CLOUDFLARE_WORKER_URL` and
`CLOUDFLARE_WORKER_TOKEN`; never print either value.

**Safe actions:** Static inspection and JavaScript syntax validation only.

**Destructive or external actions:** A direct Worker request invokes Workers
AI. Use a bounded prompt and do not send real player or protected story data.

**Steps:**

1. Confirm the Worker accepts the adapter's `system`, `user`, `max_tokens`,
   and optional `response_format` fields.
2. Confirm every Worker failure includes the JSON `code` and diagnostic
   headers required by the contract.

**Verify:**

```bash
node --check .plans/cloudflare.js
```

Expected: no output and exit status 0. Last verified 2026-08-26: passed. The
portal copy accepts the adapter payload and returns typed JSON error bodies,
but `errorJson()` omits the contract-required
`X-Narration-Error-Code: <code>` header. This reduces diagnosis fidelity; it
does not by itself explain a generic 502 because the Railway adapter also
parses the JSON error body. Add that header before the next Worker portal
upload. A direct unauthenticated request to the configured Worker endpoint
returned HTTP 401 with JSON code `UNAUTHORIZED`, `X-Trace-ID`, and
`X-Worker-Revision`, confirming that the public endpoint reaches this Worker.
With the credentials sourced locally, small ordinary and `response_format`
requests both returned HTTP 200. The production-size scene-context request was
initially blocked at the Cloudflare edge with HTTP 403 / error 1010 because
Python urllib's default user agent triggered Browser Integrity Check; the same
request passed after the adapter supplied its browser user agent.

## Hosted free-text roleplay quality evaluation

**Purpose:** Verify that a real player action receives a responsive, progressive
roleplay narration rather than a repeated opening, while allowing creative
consequences that the runtime validates through proposed state effects.

**Setup / seed:** Source the root `.env` with `E2E_API_BASE_URL`,
`E2E_DEPLOYMENT_CHANNEL`, and `OPENAI_API_KEY`. The optional
`E2E_JUDGE_MODEL` selects the OpenAI judge; it defaults to `gpt-5.4`. Do not
print or commit credentials.

**Safe actions:** The staged test creates a disposable remote session and two
turns. The judge uses the OpenAI Responses API with `store: false` and writes
only its structured verdict and reasons to ignored `artifacts/` evidence.

**Destructive or external actions:** Invokes the staged narration model and two
paid OpenAI judge calls. It does not deploy, change credentials, or mutate
canonical state outside the disposable session.

**Steps:**

1. Start a session and submit two distinct free-text actions.
2. Assert neither narration repeats the opening and that the two narrations
   differ.
3. Ask the OpenAI judge whether each narration responds directly, progresses,
   and remains coherent with the supplied grounding. Creative additions are
   explicitly allowed; story-beat/state-effect validity remains the runtime's
   deterministic responsibility.

**Verify:**

```bash
source .env && cd frontend && npm run test:e2e -- --grep @llm-judge
```

Expected: both OpenAI structured verdicts are `pass` and
`artifacts/e2e-llm-judge.{json,md}` records the narrations plus reasons. This
is an explicit, paid manual evaluation; ordinary `@smoke`, `npm test`, pulls,
pushes, and PR checks do not call OpenAI. Last
verified locally on 2026-08-26: the judge returned `fail` for the known defect
where the opening text was returned verbatim for `Look at the phone`.

**Cleanup:** The generated `artifacts/e2e-llm-judge.*` files are ignored; remove
them when no longer useful. The remote test session is disposable.

**Notes:** As of 2026-08-26, the existing `@spine` E2E only reports whether
its fixed policy reached `3C`; it does not assert it. `@storylets` only checks
that any observed IDs have the `SL-` prefix, so an empty set passes. The
current `pacing.yaml` declares one outgoing transition from each of `1A`
through `3B` and a single terminal `3C`; it has no alternate transition or
ending branches. Do not claim live E2E proof of complete storylet coverage,
branch coverage, or multiple endings until package-declared coverage oracles
and repeated policy runs are implemented.

The loader reads only `data/stories/continuity-initiative/{plot.md,storylets.md,
pacing.yaml,world.yaml}`; `.plans/` copies are not runtime inputs. The loaded
`storylets.md` defines optional scene-local storylets and supplies their prose
sections to the model context, but it does not compile `Effects`, `Completion`,
or `Abort` prose into transition edges. Actual scene branches and endings must
be declared as additional `pacing.yaml` transitions and listed in the source
scene's `transition_ids` frontmatter.

After the adapter change was deployed, two staging `@smoke` retries still
timed out after 120 seconds in `page.waitForResponse()` for `POST
/api/v1/turn`. The page snapshot showed `Failed to fetch` for both the session
feed and submitted action, and no browser-observable turn response arrived.
Restarting the local Vite server did not change that result. Treat this as a
browser/API transport (likely CORS or deployed API reachability) failure, not
as evidence that the Worker user-agent fix is ineffective; the direct
authenticated full-context Worker call succeeded. Evidence is the retained
Playwright trace and error context under
`frontend/test-results/scene-runtime-starts-a-sce-758f8-ts-freeform-narration-smoke-chromium/`.

The direct staging session/turn probe then returned Railway HTTP 500, which
was reproduced locally: the Worker returns a successful envelope containing
JSON text in `narration` plus metadata, but the adapter passed that outer
envelope to strict `TurnProposal` validation. The adapter now unwraps and
parses `narration`, keeps the metadata non-canonical, uses the Worker-supported
2,048-token ceiling after observing a 1,024-token truncated JSON response, and
sends an explicit schema-and-no-echo prompt. A real local Worker plus runtime
turn then succeeded. This revision still needs Railway deployment before
rerunning the staging smoke test.

**Cleanup:** None.
