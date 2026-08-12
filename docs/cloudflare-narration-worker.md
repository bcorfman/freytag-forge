# Cloudflare V2 turn-model contract

The hosted demo uses a Cloudflare endpoint as its V2 turn-model transport. The
endpoint must proxy Workers AI failures as structured JSON and must not turn
every upstream failure into `503`.

## Required environment values

| Worker variable | Purpose |
| --- | --- |
| `CF_ACCOUNT_ID` | Cloudflare account that owns the Workers AI request |
| `CF_API_TOKEN` | Token with Workers AI permissions |
| `CF_AI_MODEL` | Optional model override; otherwise use the deployed default |
| `DEMO_SHARED_TOKEN` | Optional bearer token shared with Railway |

Configure each Railway channel with the matching values below. The token is
optional only when the Worker does not require bearer authentication.

| Railway variable | Value |
| --- | --- |
| `CLOUDFLARE_WORKER_URL` | Public URL of the V2 turn-model Worker |
| `CLOUDFLARE_WORKER_TOKEN` | `DEMO_SHARED_TOKEN`, when configured |
| `CLOUDFLARE_TIMEOUT` | Optional bounded request timeout, in seconds |

If `CLOUDFLARE_WORKER_URL` is absent, the hosted API intentionally serves
openings but rejects freeform model turns with `service_unavailable`.

Configure Cloudflare's native version metadata binding in `wrangler.jsonc`:

```jsonc
{
  "version_metadata": {
    "binding": "CF_VERSION_METADATA"
  }
}
```

The Worker should obtain the version ID at request time and add it to both
successful and error responses:

```js
const workerRevision = env.CF_VERSION_METADATA.id;

return json(
  {
    narration,
    operations,
    beat_updates,
    summary_delta,
    material_progress,
  },
  200,
  { "X-Worker-Revision": workerRevision },
);
```

Apply the same header to `errorJson` responses. This reports the version that
actually handled the request, including during gradual deployments.

## Response contract

Success responses are a V2 `TurnResult` JSON object: non-empty `narration`,
optional `operations`, `beat_updates`, `summary_delta`, and
`material_progress`. Do not put Worker metadata inside that object. Send model,
trace, and Worker revision metadata in response headers instead. The adapter
also strips the known legacy `model`, `trace_id`, and `worker_revision` envelope
keys before local V2 validation, but that compatibility normalization is not a
substitute for updating the Worker contract.

Failure responses are JSON with `status: "error"`, a stable `code`, a safe
`message`, and `trace_id`. When available, they also include
`upstream_status`, `upstream_code`, and `upstream_request_id`.

The important codes are:

- `AI_QUOTA_EXCEEDED`: HTTP 429; do not retry automatically.
- `AI_CAPACITY_EXCEEDED`: HTTP 429; retry only with a bounded policy and honor
  `Retry-After`.
- `AI_REQUEST_REJECTED`: preserve the upstream 4xx status.
- `AI_UPSTREAM_ERROR`: use a gateway/server failure for upstream 5xx responses.
- `AI_JSON_MODE_REJECTED`: Workers AI rejected or could not satisfy the requested
  JSON response format. This is a typed 502 so the client can make its one
  JSON-mode fallback without relying on error-message matching.
- `AI_NETWORK_ERROR`, `AI_BAD_RESPONSE`, and `AI_EMPTY_RESPONSE`: Worker or
  upstream protocol failures.

The Worker should catch failed `fetch()` calls and return a deliberate 5xx
response. Cloudflare documents that an uncaught Worker exception produces a
runtime error response rather than the application’s JSON contract.

The Worker must forward the adapter’s bounded `max_tokens` request value to the
Workers AI request. Otherwise the model may use a smaller default and truncate
opening narration before the final paragraph.

## Structured-output and recovery contract

Structured story-agent requests declare their required response shape through a
typed adapter option. When that option is `json_object`, the Railway client
sends `response_format: {"type": "json_object"}` and the Worker forwards it
unchanged to Workers AI. The option is transport metadata; it must not be
inferred from prompt wording.

The client always performs local JSON parsing and typed-contract validation;
JSON mode only requests syntactic JSON. If the Worker returns
`AI_JSON_MODE_REJECTED`, the client may make exactly one fallback request
without `response_format`, while retaining the JSON-only prompt instruction.
This fallback consumes the ordinary turn's only recovery request. A subsequent
timeout, malformed response, contract error, or upstream failure must fail
closed rather than starting another retry sequence.

Workers AI can report that JSON-mode failure in either a non-2xx response or a
successful HTTP envelope with `success: false`. Classify both forms as
`AI_JSON_MODE_REJECTED`; otherwise the Railway client cannot safely select the
required fallback.

## Promotion checks

After deploying the Worker and Railway service, verify:

1. `GET /api/v1/health` returns 200.
2. A normal hosted freeform turn returns 200, a non-empty narration, and a V2
   state update response (the opening `look` does not contact the turn model).
3. A Worker quota response reaches the API as 429 / `quota_exhausted`.
4. A Worker capacity response reaches the API as 429 / `rate_limited`.
5. The response includes `X-Request-ID`, `X-Narration-Error-Code`, and, when
   supplied by the Worker, `X-Trace-ID` and `X-Worker-Revision`.
6. The production hosted E2E test passes after the deployment is healthy.

## Verifying the version

After deployment, verify the active Cloudflare deployment and its version with
`npx wrangler deployments list --name <worker-name> --json` and
`npx wrangler versions list --name <worker-name> --json`. These commands are
diagnostic only; Railway does not need Cloudflare API credentials or a copied
version ID.
