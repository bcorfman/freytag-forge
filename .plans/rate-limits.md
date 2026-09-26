# Rate limits and a daily model budget: plan

Status (2026-09-26): tasks 1 and 2 are built on branch `rate-limits` (4ae3780,
5af72ef), which is not yet merged. The Worker with the budget is deployed
(revision 08bbb897): with the token, a request narrates, which needs a budget
reservation to succeed; without it, the request gets 401. Next: merge, deploy the API to
Railway, set `FREYTAG_TRUST_PROXY_HEADER=1` there, and run the per-IP check
below. Then the follow-up. Every code change is a Ringer task on GPT-5.6 Luna,
as in the other plans.

## Why

No outsider may use the game's Cloudflare models for their own purposes or run
up the bill, and no single player may drive up calls. The world-model plan's
W12 adds a Jev call during play, which raised the question. A read of the
current guards found these gaps:

1. `POST /api/v1/session` has no limit, and each session runs the opening
   narration, which is one 8b call. A script can loop on it.
2. The only limit is 60 requests a minute per client IP, on `POST
   /api/v1/turn` only (`storygame/web_demo.py`, `require_rate_limit`). A
   person needs far fewer, and one turn can make several model calls (a
   retry, a match call, the W12 Jev question).
3. Railway starts uvicorn without `--forwarded-allow-ips` (`railway.toml`).
   uvicorn then trusts forwarding headers only from 127.0.0.1, so
   `request.client.host` is probably Railway's proxy for every player. If so,
   the "per IP" limit is one bucket shared by all players. Not yet confirmed
   against live traffic.
4. Per-IP limits never cap the bill: rotating IPs gets fresh buckets, and the
   in-memory counts reset on every restart.
5. Cloudflare sets no spending ceiling. The account is on Workers Paid
   (Brandon, 2026-09-26). On that plan, Workers AI usage beyond the free
   10,000 neurons a day is billed at $0.011 per 1,000 neurons with no daily
   or monthly cap. Only the Free plan stops at 10,000 neurons. Workers
   requests, CPU time and Durable Objects are billed past their included
   amounts in the same way (Cloudflare pricing pages, checked 2026-09-26).
   Cloudflare's per-account rate limit on text generation, 300 requests a
   minute at most, bounds the rate of calls but not the bill: at about
   $0.0004 a turn, that rate costs on the order of $170 a day.
6. The narration Worker (`.plans/cloudflare.js`) checks its bearer token only
   `if (env.DEMO_SHARED_TOKEN)`. The secret is set in production (Brandon,
   2026-09-26), but the code fails open if it is ever missing.

## Decisions (Brandon, 2026-09-26)

- **Per session:** at most 10 turns a minute, keyed on the server-minted
  `session_id`.
- **Per IP:** at most 20 new sessions a day.
- **Daily budget:** $5 a day of model spend across all players, enforced in
  the Worker.

## Design

### The API (Railway)

- The turn limit is keyed on `session_id`, not on the IP.
- `POST /api/v1/session` gets the per-IP limit of 20 a day.
- The client IP is the rightmost `X-Forwarded-For` entry, and only when
  `FREYTAG_TRUST_PROXY_HEADER=1`, which is set on Railway. Railway's own
  docs say nothing about client IP headers (checked 2026-09-26). In
  Railway's forum, a Railway staff member said the rightmost entry is the
  trustworthy one, because the edge appends the address it saw; anything to
  its left can be forged. `X-Real-IP` was rejected: staff reported it is set
  to the CDN's address when traffic passes through Railway's CDN.
- **Check after deploy.** If the rightmost entry turns out to be a proxy's
  address, every player shares one bucket, and 20 sessions a day stops the
  demo for everyone. After deploying to staging, send 21 session requests
  from one machine without the token and expect the 21st to get 429. Then
  create a session from another network, such as a phone off Wi-Fi, and
  expect 200.
- Both limits return 429 with a plain message. The existing
  `FREYTAG_RATE_LIMIT_PER_MINUTE` setting becomes the per-session turn limit
  (default 10), and a new `FREYTAG_SESSIONS_PER_IP_PER_DAY` holds the session
  limit (default 20). A value of 0 still turns a limit off, for local and unit
  test use.
- Counts stay in memory. A restart resets them. That is acceptable because
  the Worker's budget is the hard cap.

### The E2E exemption (Brandon, 2026-09-26)

A local E2E run makes many sessions from one IP and would pass 20 in a day.
Requests that carry the existing test-clock token are exempt from both API
limits.

- **Where it applies.** Only where `FREYTAG_ALLOW_TEST_CLOCK=1` and
  `FREYTAG_TEST_CLOCK_TOKEN` is set, which is staging only (runbook section
  8). Production sets neither, so no request there is ever exempt.
- **The check.** The token comes from the `X-Freytag-Test-Clock-Token`
  header and is compared with `hmac.compare_digest`, as
  `_test_clock_seconds` does. Put that comparison in one helper that both
  paths call. A wrong token is not exempt and counts like any request; it is
  not refused with 403 by the limiter, because the limiter should not become
  a way to probe the token.
- **Exempt from the API limits only.** Exempt requests still go through
  the Worker's $5 budget. A leaked token can bypass the per-session and
  per-IP limits on staging, but it cannot raise the bill past the cap. If
  staging and production share one Worker, an E2E run spends from the same
  daily budget as players.
- **The harness must send the token; today it sends nothing.** Commit
  c6309d2 (2026-08-30) removed the browser's test-clock injection, and
  nothing in `frontend/` sends the token now. The E2E harness needs to add
  the header to its `/api/v1/session` and `/api/v1/turn` requests, read from
  an environment variable and scoped with a Playwright route to the API's
  URL only, so the token never reaches another host. Never write the token
  value into a file.
- **Runbook.** Section 8 of `docs/testing-runbook.md` still shows
  `E2E_TEST_CLOCK_SECONDS=120`, which nothing reads since c6309d2. Brandon
  (2026-09-26): it applies to nothing, so it must not come back. Remove it
  from the entry's command and edit the entry in place to describe the token
  as the E2E rate-limit exemption. The new harness code must not read it.
  The runbook line is its only remaining mention; `.env` does not set it.

### The Worker (Cloudflare)

- **The budget is counted in dollars.** Each model has an input and an
  output price per million tokens, held in the Worker's config. Before a
  call, the Worker reserves that call's worst case: the estimated input plus
  its `max_tokens` of output. After the call, it settles the reservation to
  the reported `usage`. Reserving first means parallel calls cannot push the
  day past $5.
- **The counter** is a Durable Object keyed by the UTC date, so it survives
  restarts and is shared by every Worker instance. Cloudflare's rate-limiting
  binding counts requests, not dollars, so it does not fit.
- **Refusal.** Once the day's reservations and spend reach $5, every model
  route returns the error contract with a new code,
  `AI_DAILY_BUDGET_EXCEEDED`. The API maps it to 429 with no retry, like
  `AI_QUOTA_EXCEEDED`. The game stops for everyone until 00:00 UTC.
- **Fail closed.** If the counter cannot be read or updated, the call is
  refused. A missing `DEMO_SHARED_TOKEN` refuses every request instead of
  skipping the check.
- The 10,000 free neurons a day are ignored, which keeps the count on the
  safe side.
- The counter's own cost is negligible: two Durable Object requests per
  model call, against 1 million included a month on Workers Paid.
- The $5 is model spend only. The plan's $5-a-month base fee and any
  Workers request or CPU overage are separate and not counted.
- The W12 Jev route (world-model plan, task E) goes through the same budget.

### Prices

- Workers AI charges $0.011 per 1,000 neurons (Cloudflare pricing page,
  checked 2026-09-26).
- The page lists `@cf/meta/llama-3.1-8b-instruct-fp8-fast` at $0.045 per
  million input tokens and $0.384 per million output tokens. It does not list
  `@cf/meta/llama-3.1-8b-instruct-fast`, which the Worker uses, or
  `typesafe/jev`. Find both prices before building. Until they are known,
  set each missing price to the most expensive listed model the Worker could
  plausibly be switched to, so any error is on the safe side.
- Rough scale, for sizing only: a turn of about 4,000 input and 500 output
  tokens on the fp8-fast prices costs about $0.0004, so $5 is on the order
  of 10,000 turns a day.

## Tasks

- **Task 1: API limits.** The per-session turn limit, the per-IP session
  limit, and the client IP from the trusted proxy header. Unit tests cover:
  the 11th turn in a minute refused and a later one allowed; two sessions
  keeping separate counts; the 21st session from one IP refused; a forged
  header ignored when the proxy is not trusted; a limit of 0 turning a
  limit off; a request with the right token exempt from both limits with the
  test clock enabled; the same request not exempt with the test clock
  disabled; and a wrong token counted like any request, not refused with
  403. The E2E harness sends the token header to the API only, and the
  runbook's section 8 is edited in place.
- **Task 2: the Worker budget.** The Durable Object counter, reserve and
  settle, the new error code in the Worker and in the API's error mapping,
  and fail-closed token and counter checks. Tests cover: a call refused once
  the budget is spent; parallel reservations not overshooting; a refused call
  when the counter fails; every request refused with no token; and the count
  resetting at the next UTC date. `docs/cloudflare-narration-worker.md` gains
  the new code and config.

## Follow-up: remove the HTTP test clock (Brandon, 2026-09-26)

Commit c6309d2 found that a story-clock value no longer advances anything
that matters, because pacing counts turns since scene entry. The API still
accepts one, so remove it from the HTTP surface. Run this after task 1,
which moves the token check into the shared helper this follow-up keeps.

- Remove from `storygame/web_demo.py`: the `test_clock_seconds` field on
  `TurnRequest`; the `X-Freytag-Test-Clock-Seconds` header and its CORS
  entry; `_test_clock_seconds`; and passing `clock_seconds` from the turn
  route. The turn route then calls `engine.turn(body.input_text)`.
- Keep `FREYTAG_ALLOW_TEST_CLOCK`, `FREYTAG_TEST_CLOCK_TOKEN`, the
  `X-Freytag-Test-Clock-Token` header and its CORS entry, and the token
  helper. The E2E exemption uses all of them. Whether to rename them away
  from "clock" is not part of this follow-up.
- Keep `RuntimeEngine.turn(..., clock_seconds=...)`. It still advances
  `story_elapsed_seconds`, and the canon-journey and pacing tests use it
  in-process. Only the HTTP route stops passing it.
- Tests in `tests/test_web_demo.py` that exercise the seconds field or
  header are removed or rewritten against the token exemption. A request
  that still sends `test_clock_seconds` gets the ordinary validation answer
  for an unknown field, whatever `TurnRequest` does with extra fields today.
- Runbook section 8 loses the seconds field and the expected-behaviour lines
  about advancing story time. It keeps the token.

## Open questions

None. The deployed Worker is `.plans/cloudflare.js` with
`.plans/wrangler.jsonc`, and Brandon deploys it with `wrangler` (2026-09-26).
Task 2 adds the Durable Object binding and its migration to
`wrangler.jsonc`. The worker cannot deploy; Brandon runs `wrangler deploy`
after review, and the budget is checked against the deployed Worker before
task 2 is called done.
