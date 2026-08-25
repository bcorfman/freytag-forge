# Freytag Forge V2 product reference

Freytag Forge is a package-driven interactive-fiction engine: players may try
any in-scope move, while deterministic policy makes every accepted consequence
grounded, persistent, and replayable. `storygame.web_demo` is the only hosted
player surface. `RuntimeState.facts` is the only mutable runtime authority;
`data/`, reviewed packages, prose, traces, and transcripts are immutable input
or derived projections.

Detailed authoring, staging, and acceptance procedures live in
[compiled-story authoring](compiled-story-authoring.md),
[genre-blueprint authoring](genre-blueprint-authoring.md),
[the causal-spatial plan](../.plans/causal-spatial-runtime-projection.md), and
[the V2 acceptance matrix](v2-acceptance-matrix.md).

## Product experience

The engine supports mystery, fantasy, sci-fi, and relationship stories through
one fact-backed runtime—never through story- or genre-specific branches.

- Players use ordinary language. Only `save`, `load`, `quit`, and `help` are
  control commands; unambiguous movement and visible-item affordances are
  normalized through the same proposal/commit boundary.
- New rooms and items may be richly described; known spaces stay concise unless
  the player explicitly looks again. Prose cannot create observation,
  discovery, location, custody, or relationship truth.
- Opening orientation is typed public metadata, rendered once without an
  automatic model turn. It contains the scene, player context, public briefing,
  contacts, and first available actions—not protected authoring material.
- Present NPCs, declared groups, visible items, and inspectable scene subjects
  are the only current social or investigative targets. NPCs retain permitted
  knowledge, voice, relationship, stance, and interaction continuity.
- Conversation, inspection, and consequence unlock opportunities; they never
  become a fixed action menu or forced path.

## Authoring and reviewed packages

The offline compiler produces a validated `story-blueprint-v2`: causal truth,
space, cast, evidence, dramatic progression, and optional social interaction
declarations. Those declarations include public placement, NPC performance,
movement, scene subjects, group/party context, and interaction frames.

The compiler plans causal and spatial continuity before dramatic opportunities.
Local contracts and critics reject unknown references, impossible routes,
incompatible custody, absent group members, protected-public leaks,
unsatisfiable storylets, invalid interaction frames, and failure-forward
cycles. Genre profiles inject generic minima; shared runtime code does not
inspect genre names. Candidate generation allows one request plus one shared
repair/recovery request, then requires review and promotion before play.

`RuntimeNarrativeProjection` keeps the legacy-compatible `CompiledStory` beside
a frozen reviewed package. Both are inputs; neither is a mutation authority.

Offline conversation evaluation drives semantic player policies through
isolated real engine sessions. An independent model judges each accepted,
structured transcript against its authored performance context and returns a
typed rubric with turn/segment citations. Local checks validate citations,
grounding, and thresholds; they do not score prose by keywords. This evidence
and human review gate promotion only—the ordinary runtime never calls an
evaluation critic or accepts an evaluator-directed route.

## Facts, bootstrap, and context

Bootstrap copies reviewed declarations into canonical facts: player and NPC
location/presence, public presentation and availability, inspectable scene
subjects, evidence location/custody/discovery, group membership, party
knowledge, goals, tasks, clues, relationships, pressure, and explicit storylet
and interaction lifecycle markers. `WorldState` remains a compatibility view
updated only by a validated candidate.

`RuntimeContextBuilder` exposes only the current player-safe projection:
visible facts and targets, eligible storylets, recent events, pacing, and legal
progression. It excludes off-scene/unavailable targets and protected or
speaker-private knowledge. A keyed private slice gives each present NPC its
performance profile, known truths, motive, relationship, stance, and recent
interaction state. An active interaction frame and its continuation obligations
precede other eligible storylets without disabling freeform play.

Movement plans stay immutable. Any location or availability change must be a
typed, validated fact operation; package data is never rewritten at runtime.

## Turn contract and progression

`RuntimeEngine.turn` builds bounded context, calls an injected `TurnModel`,
locally parses a strict `TurnResult`, validates a cloned state, and replaces the
live state only after the entire candidate succeeds. Provider JSON-object mode
is transport metadata, not inferred from prompt text. A rejected JSON-mode
request may retry once without that option; malformed responses, transport
errors, and validation failures share that same recovery budget. Exhaustion
returns a typed fail-closed error and leaves state unchanged.

`StateOperation` supports only declared paths and fact families. Validation
enforces custody cardinality, visible transfers, protected-revelation
boundaries, beat order, route/storylet eligibility, and declared consequences.
Timed events and storylet effects commit on the cloned candidate before
narration renders. Facts, not narration or provider JSON, determine the next
turn.

`InteractionProposal` is the sole interaction boundary for named co-present
responders, groups, visible items, and scene subjects. It validates identity,
addressees, voice, knowledge, membership, protected text, and declared
discoveries before its atomic effects and lifecycle facts commit. The accepted
turn then projects ordered speech and expressive/material action segments with
public names and addressees. `TurnResponse.segments` is the hosted rendering
contract; `lines` is its deterministic compatibility projection. Narration is
retained beside interaction segments, and transcripts, traces, artifacts, and
saves preserve the same accepted structure. `DialogueProposal` remains a
legacy compatibility path.

Goals, tasks, clues, relationships, scene purpose, pressure, timed events, and
endings are reviewed declarations projected into facts. Pacing advises urgency
but never prescribes a player action. Storylets provide eligible dramatic
situations with declared realization modes, consequences, lifecycle markers,
and failure-forward alternatives; an empty eligible set is ordinary freeform
play.

## Persistence, artifacts, and hosting

`RuntimeStateSqliteStore` saves integrity-checked, versioned snapshots bound to
the compiled-story identity. Invalid schema, malformed data, hash failure, or a
story mismatch raises typed `RuntimeSaveError` before rehydration. Loading
restores facts and reconnects the immutable reviewed package.

`artifact_bundle` derives `StoryState.json`, `STORY.md`, `trace.json`, and
`transcript.json` from accepted facts and events. Manifest hashes and replay
signatures detect corruption; projections never reconstruct or mutate runtime
truth.

The hosted adapter exposes health, version, session, load, and turn endpoints.
It owns HTTP translation, session limits, CORS, rate limits, reviewed-fixture
selection, and optional artifact writes; it does not own a second turn policy.
The frontend validates the API identity before opening a session.

Trusted `main` deploys to Railway staging and Pages `/dev/`; production is a
manual promotion of an already staged immutable SHA. Root Pages is production.
Deployment evidence, acceptance records, and rollback data document releases
without becoming gameplay input.

## Operating the project

### Environment

- Offline compiler: `OPENAI_API_KEY`; live compilation also requires
  `FREYTAG_ENABLE_LIVE_COMPILER=1` and `--live`. `OPENAI_BASE_URL` is optional.
- Hosted turn model: `CLOUDFLARE_WORKER_URL`, optional
  `CLOUDFLARE_WORKER_TOKEN`, and `CLOUDFLARE_TIMEOUT`. See the
  [Cloudflare turn-model contract](cloudflare-narration-worker.md).
- Hosted deployment: `FREYTAG_DEPLOYMENT_CHANNEL`,
  `FREYTAG_DEPLOYMENT_SHA`, `DEMO_CORS_ALLOW_ORIGINS`, session/rate-limit
  settings, and channel-specific Vite API origins.

### Developer workflow

```bash
uv sync --group dev
TMPDIR=/tmp uv run pytest -q
uv run ruff check --fix .
uv run ruff format .
```

CI enforces the full suite, branch coverage of at least 90%, and quality-tier
collection checks. Test totals are informational rather than fixed gates.

## Non-negotiable guardrails

- Facts are the sole mutable runtime truth.
- Every provider response is untrusted and locally validated before commit.
- Ordinary turns use at most one request plus one shared recovery request.
- Shared behavior never branches on a story, character, genre, or premise.
- Opening, movement, dialogue, storylets, persistence, and hosted projections
  must agree with committed facts.
- Generated and reviewed artifacts are immutable inputs. Fix authoring sources
  or compiler contracts, regenerate, and promote; never hand-edit a projection.
