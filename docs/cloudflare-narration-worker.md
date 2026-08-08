# Cloudflare narration-worker contract

The hosted demo expects its Cloudflare Worker to proxy Workers AI failures as
structured JSON. The Worker must not turn every upstream failure into `503`.

## Required environment values

| Worker variable | Purpose |
| --- | --- |
| `CF_ACCOUNT_ID` | Cloudflare account that owns the Workers AI request |
| `CF_API_TOKEN` | Token with Workers AI permissions |
| `CF_AI_MODEL` | Optional model override; otherwise use the deployed default |
| `DEMO_SHARED_TOKEN` | Optional bearer token shared with Railway |

Railway must use the matching Worker URL and `CLOUDFLARE_WORKER_TOKEN`.

## Response contract

Success responses are JSON with a non-empty `narration` string, `model`, and
`trace_id`.

Failure responses are JSON with `status: "error"`, a stable `code`, a safe
`message`, and `trace_id`. When available, they also include
`upstream_status`, `upstream_code`, and `upstream_request_id`.

The important codes are:

- `AI_QUOTA_EXCEEDED`: HTTP 429; do not retry automatically.
- `AI_CAPACITY_EXCEEDED`: HTTP 429; retry only with a bounded policy and honor
  `Retry-After`.
- `AI_REQUEST_REJECTED`: preserve the upstream 4xx status.
- `AI_UPSTREAM_ERROR`: use a gateway/server failure for upstream 5xx responses.
- `AI_NETWORK_ERROR`, `AI_BAD_RESPONSE`, and `AI_EMPTY_RESPONSE`: Worker or
  upstream protocol failures.

The Worker should catch failed `fetch()` calls and return a deliberate 5xx
response. Cloudflare documents that an uncaught Worker exception produces a
runtime error response rather than the application’s JSON contract.

## Promotion checks

After deploying the Worker and Railway service, verify:

1. `GET /api/v1/health` returns 200.
2. A normal hosted `look` turn returns 200 and a non-empty narration.
3. A Worker quota response reaches the API as 429 / `quota_exhausted`.
4. A Worker capacity response reaches the API as 429 / `rate_limited`.
5. The response includes `X-Request-ID`, `X-Narration-Error-Code`, and, when
   supplied by the Worker, `X-Trace-ID`.
6. The production hosted E2E test passes after the deployment is healthy.
