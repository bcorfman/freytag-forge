# Freytag Forge product reference

Freytag Forge is a package-driven interactive-fiction engine. Players write
any in-scope move; a story-agnostic runtime validates its consequences before
they become durable facts. `storygame.web_demo` is the only hosted player
surface. Facts are the sole mutable runtime authority.

## Play

- Freeform roleplay reaches the model unchanged. Save/load and an explicit
  pending game-break decision are the only control actions.
- Markdown packages define immutable scenes, entities, transitions, pacing,
  and optional storylets. Prose guides narration but never becomes runtime
  truth by inference.
- The current scene supplies bounded, player-safe context. Protected and
  speaker-private knowledge stays excluded.
- Scenes use declared Freytag phases and pacing to create urgency without
  forcing a menu, route, or player action.

## Runtime contract

Each turn is a strict, provider-normalized `TurnProposal`: narration plus
optional typed fact operations, scene transition, story events, or a game-break
warning. The runtime applies a proposal only to a cloned candidate and commits
it atomically after validation. Invalid JSON, operations, events, or
transitions leave facts unchanged.

`RuntimeState` carries the current scene and phase, active/fired events,
canonical facts, and an optional game-break decision. A warning blocks normal
turns across process restarts. `proceed` clears it; `return_to_scene` restores
the exact pre-action snapshot. SQLite saves are versioned, integrity-checked,
and bound to the selected story package.

## Authoring and hosting

The [Markdown story authoring](markdown-story-authoring.md) guide is the
authoring contract. The loader rejects malformed source, invalid IDs and
predicates, ambiguous priorities, invalid windows, and dependency cycles before
play begins. Immutable package data is never rewritten at runtime.

FastAPI, React, Cloudflare Worker transport, and SQLite remain the deployed
stack. The worker is an untrusted proposal transport; its output is locally
validated. Health, version, CORS, rate limits, and deployment identity remain
adapter responsibilities, not gameplay policy.

## Guardrails

- Facts, not prose or provider output, determine future play.
- Shared runtime behavior never branches on story, character, genre, or premise.
- Provider output fails closed and never renders or mutates invented facts.
- Packages, saves, and derived artifacts have separate immutable/input roles.

## Developer workflow

```bash
uv sync --group dev
TMPDIR=/tmp uv run pytest -q
uv run ruff check --fix .
uv run ruff format .
```
