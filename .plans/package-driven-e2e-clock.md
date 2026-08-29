# Package-driven E2E pacing clock

## Status

Proposed implementation plan for replacing the full-story E2E suite's fixed
120-second turn increment with package-declared timing milestones. This plan
does not change authored Continuity Initiative timing or production runtime
semantics.

## Problem statement

The browser currently receives one `VITE_E2E_TEST_CLOCK_SECONDS` value and adds
that same `test_clock_seconds` delta to every normal turn request. The API
accepts the field only when `FREYTAG_ALLOW_TEST_CLOCK=1`, and
`RuntimeEngine.turn()` advances the canonical `story_elapsed_seconds` fact by
that delta after an accepted proposal.

That scalar worked when the relevant story beats lay on a 120-second grid. The
reviewed package now declares global scene targets and pressure events at
irregular timestamps, including 195, 690, 705, 870, 975, and 1020 seconds. A
single per-turn delta can skip a narrow authored boundary, arrive late in a
scene window, or make a test's clock dependent on how many incidental turns or
game-break resolutions occurred earlier.

The package is already the timing authority. E2E code should name an authored
milestone and calculate the required delta from the last observed canonical
elapsed fact instead of copying package timestamps into another numeric
schedule.

## Goals

1. Let a browser test advance an accepted normal turn toward a named scene
   pacing point or pacing event declared in the selected story package.
2. Use the existing opt-in `test_clock_seconds` request field and its server-side
   validation; do not add another mutation path.
3. Calculate every delta from the most recently returned
   `state.story_elapsed_seconds`, so retries, failed turns, and game-breaks do
   not silently shift later timing.
4. Keep shared Python and browser application code story-agnostic. Story IDs,
   scene IDs, event IDs, and timestamps belong in package data or test intent.
5. Make timing drift fail with a specific diagnostic before paid canon judging
   begins.
6. Preserve the simple scalar clock for focused tests that intentionally need
   only one fixed advance, such as `@timed-events`.

## Non-goals

- Do not round or rescale `data/stories/continuity-initiative/pacing.yaml`.
- Do not infer elapsed time from plot or storylet prose.
- Do not expose package pacing internals through a new production endpoint.
- Do not add story-specific branches to `frontend/src/main.js`, FastAPI, or the
  runtime engine.
- Do not enable `FREYTAG_ALLOW_TEST_CLOCK` in staging or production.
- Do not make the E2E harness a gameplay authority or choose provider effects,
  storylets, transitions, or player actions.
- Do not treat a package-derived expected timestamp as sufficient evidence by
  itself; tests must continue to assert independently expected scenes, events,
  and knowledge boundaries.

## Proposed design

### 1. Parse a narrow pacing projection in Playwright

Add `frontend/e2e/package-clock.js`. It reads the selected package's
`pacing.yaml` directly from the repository and builds an immutable test-only
projection containing:

- `story_id`;
- each scene's `earliest_seconds`, `target_seconds`, and `latest_seconds`;
- each pacing event's ID, scene ID, and `at_seconds`; and
- the declared scene order from the pacing scene list.

Add the maintained `yaml` package as a frontend development dependency and
update `frontend/package-lock.json`. Do not implement a partial YAML parser or
copy timestamps into JavaScript.

The loader must reject, with actionable messages:

- a missing or malformed pacing file;
- duplicate or missing scene/event IDs;
- non-integer or negative timestamps;
- a target outside its scene's earliest/latest window;
- an event outside its declared scene window; and
- a requested story, scene, event, or pacing point that is not declared.

The package loader in Python remains the runtime validation authority. These
checks are defensive E2E diagnostics, not a competing package schema.

### 2. Address milestones semantically

Expose a small API from `package-clock.js`:

```js
const pacing = loadPackagePacing({ storyId: "continuity_initiative" });

pacing.scenePoint("1B", "target");      // resolves from pacing.yaml
pacing.scenePoint("2C", "earliest");
pacing.eventPoint("purge_2c");
```

The returned milestone carries its semantic identity and absolute timestamp,
for example:

```js
{
  kind: "scene_point",
  scene_id: "1B",
  point: "target",
  target_seconds: 195,
}
```

Tests name the intended milestone but never type its numeric timestamp. This
keeps changes to authored timing localized to the package while leaving the
test's narrative expectation reviewable.

### 3. Inject the calculated delta at the Playwright boundary

Extend `frontend/e2e/helpers.js` with a package-clock controller installed
before `startSceneSession(page)`. The controller owns only E2E state:

- the last elapsed value observed in a successful session/turn response;
- one armed post-turn milestone for the next `/api/v1/turn` request; and
- diagnostic history of requested milestone, prior elapsed time, sent delta,
  returned elapsed time, scene, and fired pacing events.

Use Playwright request routing to parse the outgoing JSON body and set:

```text
test_clock_seconds = milestone.target_seconds - last_observed_elapsed_seconds
```

This keeps test-only behavior out of `frontend/src/main.js`. Preserve all other
request fields byte-for-byte and continue the request normally. Do not
intercept session creation, game-break resolution, judging requests, or other
API traffic.

Before sending, fail locally when:

- no successful session state has established the current elapsed time;
- the target is earlier than the observed elapsed time;
- another target is already armed;
- the computed delta is outside the API's existing 0-3600 bound; or
- scalar and package-driven clock modes are both enabled.

After receiving a successful normal-turn response, observe the returned state
rather than assuming the requested delta was committed. An ordinary accepted
turn without a game-break must report the requested target exactly. A response
with `pending_game_break` must report its actual unchanged time, leave later
calculations anchored to that observed value, and record that the requested
milestone was not reached. The calling test must explicitly retry, choose a
different milestone, or fail; the controller must not silently consume time.

The milestone is a **post-turn target**, matching current engine ordering:
proposal validation/commit occurs first, pacing advances second, and pacing
activation runs afterward. An event reached at the end of turn N is therefore
canonical in turn N's returned state and available as provider context on turn
N+1. Document and unit-test this ordering.

### 4. Keep opt-in modes explicit and separate

Retain `E2E_TEST_CLOCK_SECONDS` and `VITE_E2E_TEST_CLOCK_SECONDS` for the
single-purpose `@timed-events` check. Introduce `E2E_PACKAGE_CLOCK=1` only as a
Playwright-side opt-in for package-driven tests.

Rules:

- package-clock tests skip unless `E2E_PACKAGE_CLOCK=1`;
- the API must still be started separately with
  `FREYTAG_ALLOW_TEST_CLOCK=1`;
- `E2E_PACKAGE_CLOCK` is not forwarded to Vite and does not affect application
  bundles;
- `E2E_PACKAGE_CLOCK` and `E2E_TEST_CLOCK_SECONDS` are mutually exclusive for
  the same test run; and
- neither setting weakens the API's server-side opt-in or numeric bounds.

Do not add an automatic probe that attempts to discover whether a remote API
allows test-clock mutation. A rejected request should fail normally, and the
runbook must continue to prohibit enabling the server flag on deployed APIs.

## E2E migration

### LLM scene-canon journey

Update `frontend/e2e/scene-runtime.spec.js` so `@llm-canon`:

1. loads the Continuity Initiative pacing projection;
2. installs one package-clock controller before session creation;
3. names the intended package milestone alongside each reviewed free-text
   action;
4. submits the action with that milestone armed;
5. records the requested milestone and observed timing in
   `e2e-llm-canon-progress` evidence;
6. asserts the expected scene, elapsed timestamp, and relevant fired event IDs
   at each boundary; and
7. runs the paid judge only after the deterministic timing/progression checks
   pass.

Represent journey steps as semantic test data, for example:

```js
{
  input: "...reviewed free-text action...",
  clock: { sceneId: "2C", point: "target" },
  expectedSceneId: "2C",
  expectedEventIds: ["purge_2c"],
}
```

The concrete action/milestone pairing must be reviewed against the finalized
story journey during implementation. Do not preserve the current eight-action
array merely to minimize diff size if it cannot legally exercise all nine
scenes. Timing control may accelerate waiting, but it must not substitute for
the route facts required by a legal transition.

Keep scene and event assertions explicit even though timestamps come from the
package. This prevents the test from becoming tautological: a malformed or
semantically wrong package should not pass simply because the harness parsed
the same wrong value.

### Focused timed-event test

Keep `@timed-events` on `E2E_TEST_CLOCK_SECONDS=120`. It verifies the API/UI
scalar plumbing and `pressure_1a` activation independently of the new planner.
This gives coverage for both supported E2E clock paths without making the
one-turn smoke test load package data.

### Other E2E categories

Do not automatically enable package pacing for `@smoke`, `@storylets`, `@npc`,
`@world-state`, or `@safety`. Adopt semantic milestones in another category
only when that category has an explicit timing assertion. This limits test
clock influence and preserves ordinary-turn coverage using provider-supplied
bounded narrative time.

## Implementation sequence

### Phase 1: Package clock model and unit tests

1. Add `yaml` to `frontend/devDependencies` and update the lockfile.
2. Add failing unit tests in `frontend/e2e/package-clock.test.js` for loading
   the real package, resolving irregular scene/event milestones, malformed
   fixtures, unknown IDs, and invalid timing relationships.
3. Implement `frontend/e2e/package-clock.js` until those tests pass.
4. Expand the frontend `npm test` glob so all `frontend/e2e/*.test.js` unit
   tests are collected rather than listing only `roleplay-judge.test.js`.

### Phase 2: Request controller and deterministic tests

1. Add unit-testable delta calculation and state observation without requiring
   a browser.
2. Cover zero deltas, forward deltas, backward targets, the 3600-second bound,
   duplicate arming, missing initial state, malformed response state, exact
   post-turn confirmation, and pending-game-break non-advancement.
3. Add the narrow Playwright route integration in `helpers.js`.
4. Verify the interceptor changes only `/api/v1/turn` JSON and preserves the
   session ID and player input.

### Phase 3: Canon E2E migration

1. Replace the scalar-clock skip in `@llm-canon` with the explicit
   `E2E_PACKAGE_CLOCK` gate.
2. Convert the reviewed canon action sequence into semantic journey steps.
3. Add fail-fast scene, elapsed, event, and game-break assertions before each
   judge call.
4. Include package milestone and observed clock history in progress and final
   artifacts.
5. Keep judge inputs scene-local and do not send the new controller's internal
   diagnostics as story canon.

### Phase 4: Documentation and verification

1. Update `docs/testing-runbook.md` in the same implementation change. Split
   the scalar `@timed-events` recipe from the package-driven `@llm-canon`
   recipe, document both opt-ins, exact commands, paid-call boundaries,
   artifacts, expected signals, and cleanup.
2. Update `.env.example` or the repository's existing environment reference if
   it currently documents E2E variables. Do not add real endpoints or secrets.
3. Run formatting/lint and deterministic suites before any external E2E.
4. Run the package-driven browser journey only against an explicitly opted-in
   local API. Do not treat an undeployed local result as staging evidence.
5. Record observed results in the runbook. If later staging verification is
   required, follow the repository rule: merge first, wait for the exact
   main-SHA staging deployment, run E2E against that revision, then commit only
   the observed documentation update.

## Test matrix

| Layer | Case | Expected evidence |
| --- | --- | --- |
| Package parser | Real Continuity Initiative pacing | Resolves 195, 690, 705, 870, 975, and 1020 from YAML, not JS literals |
| Package parser | Unknown scene/event or invalid point | Descriptive failure names the package and requested identifier |
| Clock math | Current 120, target 195 | Sends delta 75 |
| Clock math | Current equals target | Sends zero without moving time backward |
| Clock math | Current exceeds target | Fails locally before the API call |
| Clock observation | Accepted turn reaches target | Returned canonical elapsed equals target and history is recorded |
| Clock observation | Pending game-break | Actual elapsed remains authoritative; no assumed advancement |
| Request routing | Normal turn | Only `test_clock_seconds` is added/replaced in the JSON body |
| Request routing | Session, game-break, judge traffic | Request is untouched |
| Mode safety | Scalar and package modes both set | Test fails before creating a session |
| Browser pacing | `@timed-events` scalar mode | One turn reaches 120 and fires `pressure_1a` |
| Browser canon | Package mode | Reviewed journey reaches each asserted milestone and `3C` before judging |
| Security boundary | API lacks server opt-in | Test-clock field is ignored/rejected according to the existing API contract; harness cannot bypass it |

## Verification commands

Run deterministic checks first:

```bash
cd frontend && npm test
cd frontend && npm run build
TMPDIR=/tmp uv run pytest -q
uv run ruff check --fix .
uv run ruff format .
```

Run the focused scalar clock against an explicitly opted-in local API:

```bash
cd frontend && E2E_TEST_CLOCK_SECONDS=120 npm run test:e2e -- --grep @timed-events
```

Run the package-driven canon journey only after configuring the local API,
browser target, and judge credentials described in the testing runbook:

```bash
cd frontend && E2E_PACKAGE_CLOCK=1 npm run test:e2e -- --grep @llm-canon
```

The last command creates a disposable session and makes billed narration/judge
calls. It is not part of ordinary CI.

## Acceptance criteria

- No full-story E2E test depends on all turns sharing a fixed 120-second delta.
- Numeric scene/event milestones used by the package clock come from
  `pacing.yaml`; test code names semantic IDs and points.
- The existing API field, server opt-in, integer validation, and 0-3600 bound
  remain unchanged.
- Shared application/runtime code contains no Continuity Initiative IDs or
  timing branches.
- Each calculated delta is based on the last elapsed fact actually returned by
  the API, not an assumed turn count.
- Game-breaks and rejected turns cannot silently consume a milestone or shift
  later timing.
- The canon journey asserts legal scene/event progression before paid judging
  and reaches the sole ending scene.
- The scalar `@timed-events` regression remains available and passing.
- Frontend unit/build checks, the full Python suite, Ruff, and the opted-in
  browser checks pass under the documented safety constraints.
- `docs/testing-runbook.md` contains repeatable commands, expected output,
  external-cost warnings, artifacts, and cleanup for both clock modes.

## Risks and mitigations

- **Test mirrors malformed package timing.** Keep semantic scene/event
  expectations and progression assertions independent from parsed timestamps.
- **A route transition does not occur at the planned turn.** Fail on the scene
  assertion; never use clock advancement to force the transition.
- **The provider proposes a game-breaking consequence.** Trust returned state,
  retain the actual elapsed value, and require the test to resolve/retry or
  fail explicitly.
- **Playwright interception hides application behavior.** Retain the scalar
  `@timed-events` test through the real Vite request-body path and unit-test the
  interceptor's narrow mutation.
- **Package changes make a milestone move backward relative to the journey.**
  Reject the target before the request with the prior and requested semantic
  milestone in the error.
- **A test-clock flag reaches a deployed environment.** Keep the server flag
  prohibited in deployment documentation; the Playwright controller provides
  no bypass when the API has not opted in.
- **Paid E2E becomes the first failure signal.** Run package parsing, clock
  math, and deterministic progression checks before invoking the external
  judge, and retain partial progress artifacts.

