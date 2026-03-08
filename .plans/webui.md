## Freytag Forge Demo Architecture: GitHub Pages + Railway Backend + Cloudflare Workers AI

### Summary
Deploy a production-shaped public demo with predictable spend by keeping Python server-side and the browser static:
1. **GitHub Pages** serves a static HTML/CSS/JS frontend.
2. **Railway (Hobby)** runs the existing FastAPI + Python game engine backend.
3. **Cloudflare Workers AI** provides narration inference with fail-closed quota behavior.

This keeps implementation close to current repo architecture while reducing browser/runtime complexity and preserving server-side controls.

### Implementation Changes
- **Backend API surface (FastAPI on Railway)**
  - Split web UI concerns from API concerns:
    - Keep existing local `storygame.web` for dev convenience.
    - Add dedicated API module for hosted demo endpoints:
      - `POST /api/v1/session` creates session + seed.
      - `POST /api/v1/turn` accepts `session_id`, `command`, `debug` and returns turn payload.
      - `GET /api/v1/health` for deploy and uptime checks.
  - Maintain in-memory active session cache plus bounded persistence (SQLite) for restart resilience.
  - Add explicit dependency-injected narrator adapter that calls Cloudflare endpoint (no OpenAI key path in hosted demo).

- **Narrator integration (Railway -> Cloudflare)**
  - Add `CloudflareWorkersAIAdapter` implementing existing `Narrator` protocol.
  - Request shape to Worker:
    - `system`, `user`, `trace_id`, `session_id`.
  - Adapter enforces strict timeouts, request retries for transient 5xx only, and typed error mapping.
  - Hard-fail on quota errors (`429 AI_QUOTA_EXCEEDED`) with user-visible status message.

- **Abuse and spend guardrails (server-side)**
  - Per-IP rate limit (short window) and per-IP daily turn cap.
  - Per-session turn cap (default 30) and inactivity expiry (default 30 minutes).
  - Narration request ceilings:
    - max tokens, max timeout, max retries.
  - Optional mode toggle after quota exhaustion:
    - default `fail_closed` for hosted demo.
    - configurable `mock_fallback` for private deployments.

- **Frontend (GitHub Pages static app)**
  - Build simple JS client matching zorkdemo style:
    - session bootstrap via `/api/v1/session`.
    - turn submission via `/api/v1/turn`.
    - transcript + inventory/objective/phase panels.
  - Add clear non-technical error UX states:
    - `rate_limited`, `quota_exhausted`, `service_unavailable`.
  - On `quota_exhausted`, disable submit and display daily reset guidance.

- **Deployment and CI/CD**
  - Add GitHub Pages workflow:
    - build static frontend artifact and deploy on push to `main`.
  - Add Railway deploy workflow (optional if using Railway auto-deploy).
  - Add Worker deploy workflow using Wrangler.
  - Wire environment variables:
    - Railway: `CORS_ALLOW_ORIGINS`, `CLOUDFLARE_WORKER_URL`, `SESSION_TURN_CAP`, `IP_DAILY_TURN_CAP`, `TURN_TIMEOUT_MS`.
    - Worker: AI binding/model config and allowed origin list.

### Public Interfaces
- **Backend API (new hosted surface)**
  - `POST /api/v1/session`
    - Request: `{ "seed": int? }`
    - Response: `{ "session_id": str, "seed": int, "expires_at": iso8601 }`
  - `POST /api/v1/turn`
    - Request: `{ "session_id": str, "command": str, "debug": bool? }`
    - Response: `{ "session_id": str, "command": str, "action_raw": str, "beat": str, "continued": bool, "lines": [str], "state": {...}, "status": "ok"|"quota_exhausted"|"rate_limited"|"error" }`
  - `GET /api/v1/health`
    - Response: `{ "status": "ok" }`

- **Cloudflare Worker API**
  - `POST /api/narrate`
    - Request: `{ "system": str, "user": str, "trace_id": str, "session_id": str }`
    - Success `200`: `{ "narration": str, "model": str, "trace_id": str }`
    - Quota `429`: `{ "code": "AI_QUOTA_EXCEEDED", "message": str, "trace_id": str }`

### Test Plan
- **Backend behavior tests**
  - Session lifecycle: create, valid turn, expired session handling.
  - Turn API parity: `/api/v1/turn` returns same story-state semantics as existing `run_turn` flow.
  - Error mapping:
    - Cloudflare `429` -> API status `quota_exhausted`.
    - backend rate-limit -> API status `rate_limited`.

- **Adapter tests**
  - Cloudflare adapter success parsing.
  - timeout/retry policy behavior.
  - quota and upstream error normalization.

- **Frontend integration tests**
  - Initial session bootstrap and first turn render.
  - quota-exhausted UX disables input.
  - rate-limit and transient-error banners are distinct.

- **Deployment checks**
  - `GET /api/v1/health` used by Railway health checks.
  - CORS allows Pages origin only.

### Assumptions and Defaults
- Railway plan is **Hobby ($5/mo credits)** and acceptable for backend hosting.
- Hosted demo model provider is **Cloudflare Workers AI** only.
- Default production policy is **fail-closed** on AI quota exhaustion.
- Frontend remains static and does not store secrets.
- Existing CLI and local web mode continue to work unchanged for development.
