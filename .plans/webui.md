## Freytag Forge Web Demo Plan (Cloudflare + Railway) While Preserving Local Interface

### Product Intent
Ship a public, low-friction demo that anyone can try without supplying API keys, while preserving the current local developer/player experience.

### Non-Negotiables
1. Keep the existing local interfaces intact:
   - `storygame.web` (`/` + `/turn`) remains the default local web UX.
   - CLI and replay flows remain unchanged.
2. Hosted demo users do not need their own OpenAI/Ollama tokens.
3. Deterministic world/state boundaries remain server-authoritative.
4. Hosted spend and abuse are bounded with explicit guardrails.

---

## Current State (As Implemented)
- Web runtime is a single FastAPI app in `storygame/web.py`.
- API shape today:
  - `GET /` serves embedded HTML/JS web UI.
  - `POST /turn` drives game turns using `run_id` session continuity.
- Turn routing is planner-first for gameplay intents, with deterministic state/event tracking.
- Narrator backends today are OpenAI/Ollama adapters.

---

## Target Architecture

### A) Preserve Existing Local Interface (No Breaking Changes)
- Keep `storygame.web:create_app()` behavior and payload contracts unchanged.
- Keep current embedded web UI for local/dev use.
- Keep current env resolution (`FREYTAG_NARRATOR`, OpenAI/Ollama vars) for local runs.

### B) Add Hosted Demo Surface (Railway + Cloudflare)
Add a separate deploy-oriented app module (for example `storygame/web_demo.py`) that:
- uses the same core game loop (`run_turn`) and deterministic state model,
- exposes a stable hosted API for a static frontend,
- injects a Cloudflare-backed narrator path so demo users do not bring keys.

Recommended hosted API (versioned):
- `POST /api/v1/session`
  - creates a server session and returns `session_id` + seed + expiry metadata.
- `POST /api/v1/turn`
  - accepts `session_id`, `command`, optional `debug` and returns turn payload.
- `GET /api/v1/health`
  - liveness/readiness endpoint for Railway and smoke tests.

Rationale:
- avoids changing existing local `/turn` contract,
- supports static frontend hosting cleanly,
- isolates demo-specific rate/quota behavior from local mode.

---

## Narration and Adapter Strategy

### Cloudflare-backed demo narrator
- Add `CloudflareWorkersAIAdapter` implementing existing `Narrator` protocol.
- Hosted demo uses this adapter by dependency injection in the demo app.
- Keep OpenAI/Ollama adapters for local/dev and advanced usage.

### Output-editor behavior in demo
- Do not couple demo correctness to OpenAI/Ollama-only editor modes.
- Use either:
  - a deterministic pass-through editor for demo mode, or
  - a Cloudflare-capable output editor adapter if implemented.

---

## Session, Persistence, and Determinism

### Session model
- In-memory active session map with TTL expiration (demo app).
- Optional SQLite-backed recovery for session continuity across process restarts.

### Save/load in hosted demo
- Keep command-level save/load semantics available unless product decides to hide them in demo UX.
- If hidden in UI, backend should still support deterministic slot behavior per session scope.

### Deterministic guarantees
- Engine remains sole authority for state mutation.
- LLM outputs stay proposal/narration scoped; deterministic policies validate and commit bounded state updates.

---

## Abuse and Spend Guardrails (Demo App)

### Required controls
- Per-IP short-window rate limiting.
- Per-IP/day turn cap.
- Per-session turn cap and inactivity expiry.
- Request timeout/token ceilings for narrator calls.

### Failure policy
- Default hosted policy: fail-closed on hard quota/rate limits with user-readable status.
- Distinguish:
  - `rate_limited`
  - `quota_exhausted`
  - `service_unavailable`

---

## Frontend Strategy

### Hosted demo frontend
- Static frontend (GitHub Pages acceptable) calling Railway demo API.
- Minimal UX:
  - bootstrap session,
  - submit turns,
  - render transcript and state panel (inventory/objective/phase/tension/progress),
  - clear handling for quota/rate-limit/service errors.

### Local frontend
- Keep existing embedded UI in `storygame.web` unchanged for dev and deeper exploration.

---

## Deployment Topology

### Local/dev
- `uv run uvicorn storygame.web:app --reload`

### Hosted demo
- Railway service running demo app entrypoint (for example `storygame.web_demo:app`).
- Cloudflare Worker endpoint used by `CloudflareWorkersAIAdapter`.
- Optional GitHub Pages for static demo frontend.

---

## Environment Variables (Proposed)

### Shared/local (existing)
- `FREYTAG_NARRATOR`
- `OPENAI_API_KEY`, `OPENAI_MODEL`, `OPENAI_TIMEOUT`, etc.
- `OLLAMA_BASE_URL`, `OLLAMA_MODEL`, `OLLAMA_TIMEOUT`, etc.

### Hosted demo (new)
- `DEMO_MODE=true`
- `CORS_ALLOW_ORIGINS`
- `CLOUDFLARE_WORKER_URL`
- `CLOUDFLARE_WORKER_TOKEN` (or equivalent auth)
- `SESSION_TTL_SECONDS`
- `SESSION_TURN_CAP`
- `IP_RATE_LIMIT_PER_MIN`
- `IP_DAILY_TURN_CAP`
- `NARRATOR_TIMEOUT_MS`

---

## Rollout Plan

### Phase 1: Demo backend skeleton
- Create `web_demo.py` with `session`, `turn`, `health` endpoints.
- Reuse current state/session/run-turn plumbing.
- Add API tests for lifecycle and error envelopes.

### Phase 2: Cloudflare adapter
- Implement `CloudflareWorkersAIAdapter` + tests (success, timeout, 429, 5xx retry policy).
- Wire into demo app via constructor injection.

### Phase 3: Guardrails
- Add rate limiting, session TTL/turn caps, and typed error mapping.
- Add integration tests for cap/rate/quota behavior.

### Phase 4: Static demo frontend
- Build static client against `/api/v1/*`.
- Add smoke tests against deployed Railway URL.

### Phase 5: Launch checklist
- CORS locked to demo origin(s).
- Health checks configured.
- Observability for request/turn/quota metrics.

---

## Test Plan

### Backend
- Session create/continue/expire flows.
- Turn parity with current run loop semantics.
- Error mapping for rate/quota/upstream failures.

### Adapter
- Cloudflare success path.
- timeout and retry behavior.
- 429 normalization (`quota_exhausted`).

### Frontend
- session bootstrap and first-turn rendering.
- disabled input on quota exhaustion.
- distinct banners for rate-limit vs service outage.

---

## Open Decisions
1. Should hosted demo expose save/load in UI or keep it power-user only?
2. Should demo output editor be pass-through or Cloudflare-backed critique rewrite?
3. Should the hosted API return `run_id` to align with existing web contract, or keep `session_id` for explicit versioned API separation?
