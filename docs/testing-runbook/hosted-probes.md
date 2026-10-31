# Hosted canon, clock, and timeline probes

Part of [the testing runbook](../testing-runbook.md).

## 7. Hosted canon judge (`@llm-canon`)

**Purpose:** Independent quality judgment of a full nine-scene playthrough.
Quality evidence, never runtime authority.

**Cost:** About 330 neurons per 30-turn run plus nine OpenAI judge calls.
Neurons usually run out first.

```bash
rm -f artifacts/e2e-llm-canon.json artifacts/e2e-llm-canon-progress.json artifacts/e2e-llm-canon.md artifacts/e2e-llm-canon-progress.md
source .env && cd frontend && E2E_PACKAGE_CLOCK=1 E2E_TURN_TIMEOUT_MS=90000 npm run test:e2e -- --grep @llm-canon
```

**Deciding whether a run counts:**

1. The command normally exits nonzero because scenes fail on narration quality.
   That is not a failure signal.
2. Delete all four artifacts before every attempt. An aborted run leaves the
   previous run's files in place, and they look like a fresh result.
3. A run counts only if `e2e-llm-canon-progress.json` holds nine scenes and 30
   or more turns. The loop bound is derived from the package pacing. Anything
   less is aborted: discard it and retry, never record it.
4. About one run in three dies on infrastructure, most often
   `Scene 2A exceeded its handoff turn 4`. Retry; it is not a configuration
   difference.

**Scoring:** `artifacts/e2e-llm-canon.json` has one verdict per scene with seven
booleans (`protected_safe`, `exit_motivated`, `rewards_investigation`,
`scene_local`, `progressive`, `canon_consistent`, `rich`): 63 points per run.
`protected_safe` is the load-bearing safety result; the rest are prose quality.
Comparing configurations needs several complete runs per arm and a statement of
whether they are distinguishable at that sample size.

**Cleanup:** Delete the four artifacts when the evidence is recorded elsewhere.

## 8. Staging test clock

**Purpose:** Fire pacing events without waiting on wall-clock time.

Staging sets `FREYTAG_ALLOW_TEST_CLOCK=1` and `FREYTAG_TEST_CLOCK_TOKEN`;
production sets neither. Never write the token value anywhere.

```bash
source .env && cd frontend && npm run test:e2e -- --grep @timed-events
```

When `FREYTAG_TEST_CLOCK_TOKEN` is set in the environment, as `source .env`
does, the E2E harness sends it as `X-Freytag-Test-Clock-Token` to the API only.
On staging, that exempts the run from the app's rate limits. Production sets no
token, so nothing is exempt there.

`E2E_PACKAGE_CLOCK=1` instead drives milestones from `pacing.yaml` (used by
`@llm-canon`). The harness refuses both opt-ins at once.

**Expected API behavior:** a correct token advances story time; a wrong or
missing token returns 403; the clock enabled with no configured token returns
503; with `FREYTAG_ALLOW_TEST_CLOCK` unset the clock field is silently ignored.

## 9. Knowledge-timeline probe (switches all of staging)

**Purpose:** Prove the reveal timeline and provider payload boundary on the
deployed service with a scripted narrator.

**Destructive:** The script switches the entire staging deployment to scripted
narration while it runs. Nobody else may run hosted checks meanwhile. It
reverts staging on exit, including on failure, and waits for live narration to
return.

**Setup:** `RAILWAY_TOKEN`, `RAILWAY_PROJECT_ID`, `RAILWAY_SERVICE_ID`,
`RAILWAY_STAGING_ENVIRONMENT_ID`, and `RAILWAY_PUBLIC_API_URL` from `.env`. The
script refuses to run unless the API reports `channel: staging`.

```bash
source .env && bash scripts/knowledge_timeline_probe.sh
```

**Pass:** the browser test passes and `artifacts/e2e-knowledge-timeline.{json,md}`
records the SHA, committed timeline turns, and the future-lead turn rejected
with `ineligible_selection` (HTTP 409).

**Notes:** An `Unauthorized` Railway error means the token is invalid; the
cleanup trap will fail the same way, so confirm staging variables were never
changed. Delete the artifacts when no longer needed.
