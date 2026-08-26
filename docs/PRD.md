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

- `SceneContextBuilder` sends the provider only the current scene contract,
  local public entities, safe relevant facts, active storylets/events, and an
  unambiguous named entity’s concise public history. It excludes protected and
  speaker-private knowledge; ambiguous names add no entity state.
- The provider returns one strict, normalized `TurnProposal`: narration plus
  optional typed fact operations, scene transition, story events, or a
  game-break warning. The prompt carries that JSON schema rather than a story
  dump.
- The runtime clones, validates, and atomically commits accepted proposals.
  Invalid JSON, operations, events, and transitions leave canonical facts
  unchanged. `RuntimeState` keeps the current scene/phase, active/fired events,
  facts, and any pending decision.
- A warning blocks normal turns across restarts. `proceed` clears it;
  `return_to_scene` restores the exact pre-action snapshot. SQLite saves are
  versioned, integrity-checked, and bound to the selected package.

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

Facts—not prose or provider output—determine future play. Shared runtime never
branches on story, character, genre, or premise; provider output fails closed;
and packages, saves, and derived artifacts remain separate immutable inputs or
projections.

## Developer workflow

```bash
uv sync --group dev
TMPDIR=/tmp uv run pytest -q
uv run ruff check --fix .
uv run ruff format .
```
