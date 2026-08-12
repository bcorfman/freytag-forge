# Freytag Forge

## Write anything. Keep the story true.

Freytag Forge is a hosted interactive-fiction engine. Each browser session
starts from an immutable, validated `CompiledStory`; a model authors open-ended
turns and proposes typed effects; local V2 validation atomically commits only
legal changes to `RuntimeState`.

The hosted demo is the only runnable product surface. It is deployed at `/` in
production and `/dev/` in staging; `/dev/` displays a persistent non-production
badge. The frontend uses a relative build base so both locations work.

```text
player input -> bounded V2 context -> structured TurnResult
             -> validation + clone-first commit -> response and snapshot
```

One model request is normal. At most one shared recovery request handles a
JSON-mode rejection, malformed response, or validation failure. If recovery is
exhausted, no state changes and the API returns a typed failure.

## Runtime and saves

`RuntimeState` is the only mutable session truth: world, beat runtime, turn
index, recent events, and rolling summary. Saves contain a versioned V2
snapshot, event log, compiled-story content hash, and integrity hash.
Unsupported legacy snapshots are deliberately rejected as
`unsupported_save_version` rather than migrated lossily.

Staging and production are isolated by Railway service/volume/secrets/origin
and session namespace. A successful `main` deploy reaches only staging and
Pages `/dev/`; promoting production requires a tested immutable SHA.

Before a SHA is eligible for promotion, staging automatically runs all four
compiled-story fixtures through seven freeform player styles and stores a
SHA-bound scorecard. A maintainer then performs the four-genre browser review
and explicitly approves or rejects that SHA. See
[Phase 5 staging evaluation](docs/phase-5-staging-evaluation.md).

The source tree contains only this V2 runtime. Production promotion is an
operator action because it changes live traffic; use the exact checklist in
[production promotion](docs/railway-production-promotion.md) and record the
result in [the promotion record](docs/production-promotion-record.md).

## Development

- `uv sync` installs dependencies.
- `make run` runs the hosted adapter locally at `http://127.0.0.1:8000`.
- `TMPDIR=/tmp uv run pytest -q` runs the required full suite.
- `uv run ruff check .` checks lint rules.

The API provides `POST /api/v1/session` and `POST /api/v1/turn`, plus health
and version endpoints. In a turn, `save` and `load` are the retained
control-plane commands; all other input is freeform story play.

## References

- [Product requirements](docs/PRD.md)
- [V2 compiled-story authoring](docs/compiled-story-authoring.md)
- [LLM-first migration plan](.plans/gpt-refactor.md)
- [V2 acceptance matrix](docs/v2-acceptance-matrix.md)
- [Release baseline](docs/release-baseline.md)
