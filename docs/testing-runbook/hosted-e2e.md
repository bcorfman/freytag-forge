# Staged deployment and hosted E2E

Part of [the testing runbook](../testing-runbook.md).

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

- `E2E_TURN_TIMEOUT_MS` defaults to 30 000. A narration turn that spends its
  one recovery makes two model calls; an item-facts match can add up to two
  separate calls, so use 90 000 for any multi-turn category.
- In `@spine` telemetry, `fallback_turns` counts turns where the player read
  authored fallback prose instead of responsive narration. Watch it when
  changing `must_convey` groups.
- `@spine` and `@storylets` do not assert full storylet, branch, or ending
  coverage. Do not claim that coverage from them.
- A single HTTP 503 or a browser CORS error ends a run: rerun once before
  investigating. See section 11 for other failures.
  See [diagnosing hosted failures](worker-and-failures.md#11-diagnosing-hosted-failures).

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
