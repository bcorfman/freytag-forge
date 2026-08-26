# Cloudflare turn-model contract

The hosted API uses a Cloudflare Worker as its turn-model transport. The Worker
must return structured scene-runtime responses on both success and failure; it must not
turn every upstream failure into a generic `503`.

## Configuration

| Worker | Railway | Purpose |
| --- | --- | --- |
| `CF_ACCOUNT_ID`, `CF_API_TOKEN` | — | Workers AI credentials |
| `CF_AI_MODEL` | — | Optional Worker model override |
| `DEMO_SHARED_TOKEN` | `CLOUDFLARE_WORKER_TOKEN` | Optional shared bearer token |
| — | `CLOUDFLARE_WORKER_URL` | Worker URL |
| — | `CLOUDFLARE_TIMEOUT` | Bounded request timeout |

Without `CLOUDFLARE_WORKER_URL`, openings still work and freeform turns fail
closed as `service_unavailable`. Configure `CF_VERSION_METADATA` through
`version_metadata` in `wrangler.jsonc`; return its version ID as
`X-Worker-Revision` on every response.

## HTTP contract

Success is a valid `TurnProposal` JSON object: non-empty `narration`, optional
typed fact `operations`, one scene `transition`, optional story `events`, and
an optional `game_break` warning. The API validates it before a fact changes.
Put trace, model, upstream request, and Worker-revision metadata in headers—not
in the result object. Forward the adapter's bounded `max_tokens` value to
Workers AI.

Failures use `{ "status": "error", "code", "message", "trace_id" }`, with
safe optional upstream fields. Preserve these classifications:

| Worker code | API behavior |
| --- | --- |
| `AI_QUOTA_EXCEEDED` | 429; no automatic retry |
| `AI_CAPACITY_EXCEEDED` | 429; bounded retry only, honoring `Retry-After` |
| `AI_REQUEST_REJECTED` | Preserve upstream 4xx |
| `AI_UPSTREAM_ERROR` | Gateway/server failure for upstream 5xx |
| `AI_JSON_MODE_REJECTED` | Typed 502; permits the one JSON-mode fallback |
| `AI_NETWORK_ERROR`, `AI_BAD_RESPONSE`, `AI_EMPTY_RESPONSE` | Deliberate typed 5xx |

Catch failed `fetch()` calls and return this contract. Include `X-Request-ID`
and `X-Narration-Error-Code`; add trace and Worker revision headers when known.

## JSON mode and verification

The Railway client requests `response_format: {"type":"json_object"}` only
when its typed adapter selects `json_object`; the Worker forwards it unchanged.
Local parsing and contract validation remain authoritative. On
`AI_JSON_MODE_REJECTED`, the client may retry once without `response_format`
while retaining its JSON-only instruction. That retry consumes the turn's only
recovery request; every later failure is fail-closed.

After deployment, verify health, one ordinary hosted turn, quota/capacity error
mapping, required response headers, and hosted E2E. Use
`npx wrangler deployments list --name <worker> --json` and
`npx wrangler versions list --name <worker> --json` only to diagnose the active
Worker revision.
