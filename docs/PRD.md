# Freytag Forge PRD

## Product

Freytag Forge is a hosted, LLM-first interactive-fiction experience. The only
product adapter is `storygame.web_demo`; it serves the browser client at the
Pages root in production and `/dev/` in staging. CLI and local-web adapters are
retired.

The immutable input to each session is a versioned `CompiledStory`. The sole
mutable authority is `RuntimeState`: world, beat runtime, turn index, recent
events, and rolling summary. Prose, saves, and browser responses are
projections of that state, never mutation authorities.

## Turn contract

```text
browser input -> RuntimeContextBuilder -> TurnModel -> local validation
              -> atomic RuntimeState commit -> snapshot/event response
```

Normal play makes one JSON-object request. A malformed response, local contract
failure, or JSON-mode rejection can use one shared recovery request; exhausted
recovery returns a typed fail-closed error and preserves the prior state.

The validator permits only schema-defined `set`, `add`, and `remove` updates.
It protects revelation text, unique item custody, required beat ordering, and
atomicity. Pacing directives can pressure a scene but cannot dictate a player
action.

## Hosted API

- `GET /api/v1/health` and `GET /api/v1/version` return deployment channel and SHA.
- `POST /api/v1/session` starts a session from a compiled-story fixture.
- `POST /api/v1/turn` returns the opening, executes freeform play, or handles
  the control-plane `save` and `load` commands.

All endpoints retain configured CORS, request IDs, session TTLs, per-IP limits,
and per-session caps. Hosted model/configuration failures are client-safe
`service_unavailable` responses.

## Persistence and channel isolation

The hosted store writes `runtime-state-v2` snapshots under a required session
namespace. Each record includes the compiled-story ID/content hash and a
snapshot SHA-256; loading verifies all three. Unsupported legacy save schemas
return `unsupported_save_version`; there is no lossy migration.

Staging and production have separate Railway services, volumes, secrets,
origins, API URLs, and session namespaces. Passing `main` deploys only staging
and Pages `/dev/`; production promotion is manual and SHA-pinned. Pages builds
use a relative base path, so the same frontend works at both `/` and `/dev/`.

## Staging evaluation and promotion

Before a SHA may be promoted, staging runs the four compiled genres through
investigate, travel, social, avoidant, adversarial, repeated-failure, and
unexpected-action scripts. The SHA-bound evidence records one-call and repair
rates, latency, typed failures, revelation and continuity violations,
completion, and user-facing session failures. The gate fails on a staging/SHA
mismatch, incomplete coverage, typed failure, revelation leak, or continuity
failure. A maintainer must then review unscripted browser play in every genre
and explicitly approve the same SHA; this approval is required before the
manual production workflow.

## Quality gates

Required checks cover compiled-story validation across mystery, fantasy,
sci-fi, and relationship fixtures; runtime atomicity and recovery; hosted
session/opening/freeform/save/load/error/quota/CORS behavior; and root/`/dev/`
channel isolation. Project coverage remains at least 90%.
