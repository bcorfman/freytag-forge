# Testing runbook

How to verify freytag-forge: which command checks which boundary, what it
costs, what passing looks like, and how to clean up. This is an operating
manual, not a results log.

**Keeping this file short.** Edit an existing entry in place when a procedure
changes; add an entry only for a new verification boundary. Never append dated
observations, test counts, coverage figures, phase evidence, or diagnosis
narratives. Those belong in the plan, PR, commit message, or `bench/results/`.
Earlier history is in git.

Related: [test-suite guide](test-suite-performance-guide.md) (markers, tiers,
CI jobs) and [`bench/README.md`](../bench/README.md) (bench flags, ledger,
variations).

## Conventions for every command

- Run from the repository root. Pytest needs `TMPDIR=/tmp` (WSL); use
  `uv run python`, never bare `python`.
- The 90% coverage floor is repository-wide. A focused pytest run can pass
  every assertion and still exit nonzero on coverage; add `--no-cov` or
  `-o addopts=''` for focused work, and use the full suite as the coverage
  check of record.
- Never pin collection counts in tests or in this file.
- Hosted checks run against staging only, never a local API. Staging deploys
  only from `main`.

## 1. Local deterministic suite

**Purpose:** The authoritative gate for runtime, package, transport, API, and
persistence behavior. Free; no network.

```bash
TMPDIR=/tmp uv run pytest -q                                  # full suite + coverage
TMPDIR=/tmp uv run pytest -q --no-cov -m "(unit or component) and not authoring_quality"  # CI fast feedback
TMPDIR=/tmp uv run pytest -q --no-cov -m authoring_quality    # package authoring checks
TMPDIR=/tmp uv run pytest -q --cov -n 2 --tier-report=/tmp/test-suite-health.json  # CI required gate
uv run ruff check --fix . && uv run ruff format .
cd frontend && npm test && npm run build
```

**Pass:** all tests pass and total coverage is at or above 90%; Ruff reports no
remaining issues; `npm test` passes and Vite writes `frontend/dist/`.

**Cleanup:** None. `frontend/dist/` is generated; delete it freely.

**Notes:** CI (`.github/workflows/test.yml`) runs static checks, fast feedback,
and the required gate, then deploys the tested SHA to staging and reruns
`tests/test_web_demo.py tests/test_cloudflare_transport.py` against the
adapter contract. `frozen-runtime-regression.yml` runs
`tests/test_markdown_story_package.py` weekly.

## 2. Focused checks by boundary

Use while editing; finish with section 1.

| Boundary | Tests |
| --- | --- |
| Package loading and lints (`must_convey`, `delivery_text`, narration term traps, custody, placements) | `tests/test_markdown_story_package.py` |
| Knowledge projection, save/load stability, leakage matrix | `tests/test_knowledge_projection.py tests/test_knowledge_leakage_matrix.py` |
| Narration safety and reveal conveyance | `tests/test_narration_safety.py tests/test_must_convey.py` |
| Authored reveal handoff (matcher, composition, prompt exclusion) | `tests/test_candidate_matcher.py tests/test_cloudflare_transport.py` |
| Pacing windows, handoff fallback, full canonical journeys | `tests/test_scene_relative_pacing.py tests/test_pacing_handoff.py tests/test_canon_journey.py` |
| API payloads and player-visible segments | `tests/test_web_demo.py` |
| Bench harness and ledger | `tests/test_bench.py` |

```bash
TMPDIR=/tmp uv run pytest -q --no-cov <tests from the table>
```

**Pass:** assertions pass. Coverage exit status is irrelevant here.

## 3. Prompt inspection (free)

**Purpose:** See exactly what the narrator receives, without a model call.

```bash
uv run python -m bench prompt --scene 1A --text
uv run python -m bench prompt --scene 1A --beat 1A.2 --text --player-input "Search under the drawer in her workstation."
uv run python -m bench describe --variation bench/variations/authored-handoff-phase1.json --json
```

**Pass:** the prompt contains only material the scene has made available. For
an authored-handoff turn it contains no candidate ID, candidate statement,
`delivery_text`, `must_convey`, or grounding instruction.

**Notes:** Player inputs in scripts and examples are imperative commands
("Search the kitchen."), never first person. See `AGENTS.md`.

## 4. Live narration bench (billed)

**Purpose:** Measure prompt, package, or runtime changes against the real
Cloudflare narrator without deploying. Quality and integration evidence only;
section 1 remains authoritative.

**Cost:** Workers AI neurons (about 11 per narration request; 10,000 free per
day, reset at 00:00 UTC) plus one OpenAI judge call per judged scene. Every run
appends to the tracked, append-only `bench/results/ledger.jsonl`.

**Run:** Live runs go through Ringer, because a sandboxed worker cannot reach
the network or write `bench/results/`:

```bash
cd /home/bcorfman/dev/ringer && ./ringer.py run /home/bcorfman/dev/freytag-forge/bench/manifests/phase7-live-bench.json
```

The underlying command shape, for writing a new manifest:

```bash
uv run python -m bench run --variation bench/variations/authored-handoff-phase1.json \
  --scene 1A --replicates 4 --script candidate-selection-repro --out /tmp/bench-1a --confirm
uv run python -m bench compare <baseline-variation> <candidate-variation>
uv run python -m bench.candidate_selection_report --in /tmp/bench-1a/all-turn-records.json \
  --out-json /tmp/bench-1a/report.json --out-md /tmp/bench-1a/report.md
```

**Pass / interpretation:**

- Read `summary.json`: `failed_replicates` and the verbatim `failure_reason`
  strings distinguish a failed run from one that never executed.
- `all-turn-records.json` keeps every turn, including failed replicates.
  `authored_handoff_candidate_id` is bench-only telemetry; a non-null value on
  an action that should not earn a reveal is a false positive.
- `model_selected_knowledge_ids` empty with `selected_knowledge_ids` non-empty
  means the runtime, not the model, owned the reveal.
- Use at least four replicates. Within-variation variance is as large as most
  between-variation gaps; `bench compare` reports whether arms are
  distinguishable. Never report a one- or two-point difference as real.
- Bench scenes start from a bare arrival state (only the entry fact committed),
  so a mid-story scene can fail safety checks a real playthrough would not.

**Stop conditions:** HTTP 429 with `X-Narration-Error-Code: AI_QUOTA_EXCEEDED`
is the daily quota; stop. `{"detail":"rate limit exceeded"}` is the app limiter
and is retried automatically.

**Cleanup:** Outputs under `/tmp` are disposable. Never rewrite or delete
ledger lines.

## 5. Staged deployment gate

**Purpose:** Get a change onto staging so hosted checks test the real SHA.

1. Merge the implementation PR to `main`.
2. Poll the `tests` workflow until its staging deployment succeeds.
3. Confirm `GET /api/v1/version` on staging reports that exact SHA,
   `runtime: "scene-v1"`, and `channel: "staging"`. A green `/api/v1/health`
   alone proves nothing about the revision.
4. Run the hosted checks below. If only documentation changes afterwards, do
   not redeploy or rerun them.

## 6. Hosted E2E categories (billed)

**Purpose:** Exercise the deployed frontend, FastAPI service, and Cloudflare
Worker end to end.

**Setup:** `npx playwright install chromium` once in `frontend/`. Source the
root `.env` before changing directory (there is no `frontend/.env`); it sets
`E2E_API_BASE_URL` and `E2E_DEPLOYMENT_CHANNEL`.

```bash
source .env && cd frontend && npm run test:e2e -- --grep @smoke
source .env && cd frontend && npm run test:e2e -- --grep "@safety|@npc"
source .env && cd frontend && E2E_TURN_TIMEOUT_MS=90000 npm run test:e2e -- --grep @spine
```

| Tag | Checks | Extra cost or setup |
| --- | --- | --- |
| `@smoke` | Session, opening, one turn; writes `artifacts/e2e-smoke-loaded.png` | Narration calls |
| `@spine` | Scripted traversal toward 3C; delivery telemetry in `artifacts/e2e-spine.json` | Long run; use the 90 s timeout |
| `@storylets`, `@npc`, `@world-state`, `@safety` | Category policies | Narration calls |
| `@llm-judge` | Two free-text turns judged for responsiveness | `OPENAI_API_KEY`; `E2E_JUDGE_MODEL` defaults to `gpt-5.6-luna` |
| `@timed-events` | Pressure event fires via the test clock | See section 8 |
| `@knowledge-timeline` | Reveal timeline and payload IDs | See section 9 |
| `@llm-canon` | Nine-scene canon judge | See section 7 |
| `@page-qa` | UI states and layout with intercepted requests | None; runs locally, see below |

**Pass:** the test passes and writes `artifacts/e2e-<category>.{json,md}`.

**Interpretation:**

- `E2E_TURN_TIMEOUT_MS` defaults to 30 000. A turn that spends its one recovery
  makes two model calls, so use 90 000 for any multi-turn category.
- In `@spine` telemetry, `fallback_turns` counts turns where the player read
  authored fallback prose instead of responsive narration. Watch it when
  changing `must_convey` groups.
- `@spine` and `@storylets` do not assert full storylet, branch, or ending
  coverage. Do not claim that coverage from them.
- A single HTTP 503 or a browser CORS error ends a run: rerun once before
  investigating. See section 11 for other failures.

**Local UI check (free):**

```bash
cd frontend && E2E_API_BASE_URL=http://127.0.0.1:9999 npm run test:e2e -- --grep @page-qa
```

Writes `artifacts/e2e-page-qa-*.png` for loading, desktop, mobile, and error
states.

**If Vite fails to start under Playwright:** start it yourself, then run
Playwright in a second terminal:

```bash
source .env && cd frontend && VITE_API_BASE_URL="$E2E_API_BASE_URL" VITE_DEPLOYMENT_CHANNEL="$E2E_DEPLOYMENT_CHANNEL" npm run dev -- --host 127.0.0.1 --port 4173
```

Without those variables the page shows `VITE_API_BASE_URL is not configured.`

**Cleanup:** Delete ignored `artifacts/e2e-*` and `frontend/test-results/` when
no longer needed. Remote sessions are disposable.

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
   or more turns. Anything less is aborted: discard it and retry, never record
   it.
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
source .env && cd frontend && E2E_TEST_CLOCK_SECONDS=120 npm run test:e2e -- --grep @timed-events
```

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

## 10. Cloudflare Worker source check

**Purpose:** Check the portal copy of the Worker against the adapter's request
and typed-error contract. `.plans/cloudflare.js` is that copy; editing it does
not deploy anything.

```bash
node --check .plans/cloudflare.js
```

**Pass:** no output, exit 0. Confirm the Worker accepts `system`, `user`,
`max_tokens`, and optional `response_format`, and that every error returns a
JSON `code` plus `X-Narration-Error-Code`, `X-Trace-ID`, and
`X-Worker-Revision`.

**Cost:** A direct Worker request spends neurons. Use a small prompt with no
real player or protected story data, and never print
`CLOUDFLARE_WORKER_URL` or `CLOUDFLARE_WORKER_TOKEN`.

## 11. Diagnosing hosted failures

| Symptom | Meaning | Response |
| --- | --- | --- |
| 429, header `X-Narration-Error-Code: AI_QUOTA_EXCEEDED`, body `narration service is at capacity` | Workers AI daily quota spent | Stop until 00:00 UTC |
| 429, body `{"detail": "rate limit exceeded"}` | App limiter (`FREYTAG_RATE_LIMIT_PER_MINUTE`) | Slow down and retry |
| 409 `uncited_knowledge`, `narration_known_term_leak`, `ineligible_selection` | Narration safety or selection rejected the turn before commit; no state changed | A real finding. The turn is lost, not retried. Reproduce locally with `bench` before spending more hosted runs |
| 403, plain text `error code: 1010`, no Worker headers | Cloudflare Browser Integrity Check rejected the client | Keep the adapter's browser `User-Agent`; do not disable the check |
| Single 503, or a browser CORS/`Failed to fetch` error | Worker or API briefly unavailable | Rerun once; check `/api/v1/version` before changing CORS |
| 502 with `X-Narration-Error-Code` | Typed Worker failure | Classify by that code; `UNKNOWN` means an untyped upstream failure |
| Aborted `@llm-canon` | Infrastructure noise or a real stall | Apply section 7's counting rules before reading anything into it |
