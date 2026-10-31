# Worker source check and hosted failure diagnosis

Part of [the testing runbook](../testing-runbook.md).

## 10. Cloudflare Worker source check

**Purpose:** Check the Worker source against the adapter's request and
typed-error contract. `worker/src/index.js` is the source; this check does not
deploy anything.

```bash
node --check worker/src/index.js
```

**Pass:** no output, exit 0. Confirm the Worker accepts `system`, `user`,
`max_tokens`, and optional `response_format`, and that every error returns a
JSON `code` plus `X-Narration-Error-Code`, `X-Trace-ID`, and `X-Worker-Revision`.

**Cost:** A direct Worker request spends neurons. Use a small prompt with no
real player or protected story data, and never print
`CLOUDFLARE_WORKER_URL` or `CLOUDFLARE_WORKER_TOKEN`.

## 11. Diagnosing hosted failures

| Symptom | Meaning | Response |
| --- | --- | --- |
| 429, header `X-Narration-Error-Code: AI_QUOTA_EXCEEDED`, body `narration service is at capacity` | Workers AI daily quota spent | Stop until 00:00 UTC |
| 429, header `X-Narration-Error-Code: AI_DAILY_BUDGET_EXCEEDED` | The $5 daily model budget is spent | Stop until 00:00 UTC |
| 429, body `{"detail": "rate limit exceeded"}` | App limiters (`FREYTAG_RATE_LIMIT_PER_MINUTE` turns per session per minute; `FREYTAG_SESSIONS_PER_IP_PER_DAY` new sessions per IP per day) | Slow down and retry |
| 409 `uncited_knowledge`, `narration_known_term_leak`, `ineligible_selection` | Narration safety or selection rejected the turn before commit; no state changed | The player receives a fixed recovery line while the rejection code remains in the header and the raw reason is logged at WARNING; knowledge-guard rejection retries once within the two-request turn budget, while other 409 causes are not retried. |
| 403, plain text `error code: 1010`, no Worker headers | Cloudflare Browser Integrity Check rejected the client | Keep the adapter's browser `User-Agent`; do not disable the check |
| Single 503, or a browser CORS/`Failed to fetch` error | Worker or API briefly unavailable, or an unhandled API error whose 500 carried no CORS header | Typed 503 service failures retain their diagnostic response, while an unexpected engine error returns the fixed recovery line and logs a traceback at ERROR; read the staging service log before rerunning once and checking `/api/v1/version`. |
| 502 with `X-Narration-Error-Code` | Typed Worker failure | Classify by that code; `UNKNOWN` means an untyped upstream failure |
| Aborted `@llm-canon` | Infrastructure noise or a real stall | Apply section 7's counting rules before reading anything into it |

See [the hosted canon judge](hosted-probes.md#7-hosted-canon-judge-llm-canon) for section 7's counting rules.
