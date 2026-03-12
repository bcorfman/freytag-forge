# Freytag Forge PRD

## Product Intent
Freytag Forge is a deterministic narrative-engine platform for interactive fiction. It aims to blend strong IF usability with modern, testable narration controls and reproducible evaluation.

## Goals
- Deliver a playable CLI and web IF experience.
- Keep world-state progression deterministic and replayable.
- Improve narration quality via bounded, reproducible coherence workflows.
- Persist canonical artifacts with traceability and integrity enforcement.
- Enforce explicit typed contracts at agent boundaries.

## Project Layout
```text
.
├── storygame/
│   ├── cli.py
│   ├── web.py
│   ├── engine/
│   ├── llm/
│   ├── persistence/
│   ├── plot/
│   └── memory.py
├── tests/
├── .plans/
├── runs/
├── Makefile
├── pyproject.toml
└── README.md
```

## Tool Stack
- Language/runtime: Python 3.12
- Package/runtime tooling: `uv`
- Web/API: FastAPI + Uvicorn
- Testing: pytest + pytest-cov
- Linting/format rules: Ruff
- Persistence: SQLite (save snapshots + vector memory)

## Architecture Overview
### Core Engine
- `storygame.engine` handles command parsing, world rules, state transitions, and event emission.
- Runtime world truth is fact-based (`at`, `holding`, `path`, `locked`, `flag`, etc.) with legacy object views synchronized for compatibility.
- Plot progression is controlled by Freytag phase/tension modules under `storygame.plot`.
- `storygame.engine.incidents` realizes abstract beats into concrete in-world incidents with deterministic trigger logic.

### Narration + Coherence
- `storygame.llm.adapters` defines narrator integrations (`mock`, `none`, `openai`, `ollama`).
- `storygame.llm.context` constructs constrained narration context.
- `storygame.llm.coherence` runs deterministic multi-critic scoring, judging, budgets, telemetry, and constrained reversal.
- `storygame.llm.contracts` defines and validates strict typed contracts:
  - `AgentProposal`
  - `StoryPatch`
  - `CritiqueReport`
  - `JudgeDecision`
  - `RevisionDirective`

```mermaid
flowchart LR
    C[Player Command] --> N[Narrator Candidate]
    N --> V[Deterministic Validators]
    V -->|pass| R[Critics: continuity/causality/dialogue]
    V -->|fail| D[Revision Directive]
    R --> J[Deterministic Judge]
    J -->|accepted| O[Player-Facing Output]
    J -->|failed| D
    D --> N
    J -->|hard-fail budgets| X[Constrained Reversal Replan]
    X --> N
```

### Persistence + Canonical Artifacts
- `storygame.persistence.savegame_sqlite` stores run snapshots/events/transcripts.
- `storygame.persistence.story_state` emits canonical turn artifacts:
  - `StoryState.json`
  - `STORY.md`
- Artifact integrity is enforced by hash checks and orchestrator-only write constraints.
- Each artifact trace includes `parent_story_state_sha256` to link canonical snapshots across persisted turns.
- Per-turn artifact history is retained under `story_artifacts/<slot>/turns/<turn_index>/`.

## Feature Details
### Beat Realization
- Abstract Freytag beats are realized as concrete incidents (for example: thefts, arrests, urgent clue deliveries).
- Incident triggers are deterministic and may depend on:
  - turn timing (`min_turn`),
  - player location,
  - inventory requirements,
  - recent action-event patterns (for example specific `talk`/`take` activity).
- Incidents are one-shot via explicit per-incident flags and can adjust progress/tension.
- Incident definitions are authored in `storygame/content/incidents.yaml`.
- Trigger schema supports boolean groups (`all`/`any`/`not`), `cooldown_turns`, and ordered event `sequence` matching.
- If no incident matches the current beat context, the engine falls back to generic beat-tagged plot templates.

### World Builder Interfaces
- Predicate and rule packs are YAML-defined:
  - `data/predicates/core.yaml`
  - `data/predicates/genres/<genre>.yaml`
  - `data/rules/core_rules.yaml`
  - `data/rules/genres/<genre>_rules.yaml`
- NPC voice cards are defined in `data/npc_voice_cards.yaml`.
- Runtime contract validators cover:
  - `ActionProposal`
  - `DialogProposal`
  - `StateUpdateEnvelope`
- Non-command input now uses a freeform roleplay path:
  - Known commands are parsed first.
  - Parse failures route to `freeform_roleplay`.
  - Freeform adapters produce `DialogProposal` + `ActionProposal`.
  - Engine policy maps proposals into bounded `StateUpdateEnvelope` fact deltas before commit.

### Output Contract
- Non-debug mode keeps player-facing, diegetic output.
- Turn output is room-first.
- Room output uses plain title + prose layout (no bracketed room labels, no event bullet prefixes).
- Parse failures on non-command input return in-world dialog through freeform roleplay.
- Policy-impossible freeform actions return constrained boundary responses with no state mutation.
- Transcript command echo uses `>COMMAND` format.
- Debug mode includes parseable structured trace via `[debug-json] ...`.

### Coherence Gate
- Critics: `continuity`, `causality`, `dialogue_fit`.
- Judge: deterministic single arbiter with fixed weighted rubric.
- Threshold and critical floors are enforced deterministically.
- Hard limits: rounds, per-role tokens, wall-clock timeout.
- Retryable hard-fails use reversal seeding with preserved/modified/discarded delta reporting.

### Deterministic Validators
- Entity reachability
- Inventory/location consistency
- NPC presence consistency (off-screen NPCs cannot be narrated as present in-room)
- Committed-state contradiction checks
- Beat-transition legality

### Evaluation Harness
- Fixed-seed regression tests for replay stability.
- Output contract tests for debug/non-debug boundaries.
- Contract parser tests for malformed payload rejection.

## CLI and Runtime Modes
- CLI: `uv run python -m storygame --seed 123`
- CLI with story profile: `uv run python -m storygame --seed 123 --genre mystery --session-length medium --tone neutral`
- Replay: `--replay <file> --transcript <file>`
- Web: `uv run uvicorn storygame.web:app --reload`
- Narrator mode: `--narrator mock|none|openai|ollama`

## Environment Variables
### OpenAI adapter
- `OPENAI_API_KEY`
- `OPENAI_MODEL` (default `gpt-4o-mini`)
- `OPENAI_TIMEOUT` (default `10.0`)
- `OPENAI_BASE_URL`
- `OPENAI_TEMPERATURE` (default `0.2`)
- `OPENAI_MAX_TOKENS` (default `512`)

### Ollama adapter
- `OLLAMA_MODEL` (default `llama3.2`)
- `OLLAMA_TIMEOUT` (default `180.0`)
- `OLLAMA_BASE_URL` (default `http://localhost:11434/api/chat`)
- `OLLAMA_TEMPERATURE` (default `0.2`)
- `OLLAMA_MAX_TOKENS` (default `512`)

## Developer Workflow
```bash
uv sync --group dev
uv run pre-commit install
uv run pre-commit run --all-files
uv run python -m pytest -q
uv run python -m ruff check .
```

## Open Product Questions
- Should web mode expose debug JSON traces in UI by default or behind a stricter flag?
- Should transcript format optionally preserve original command casing in addition to `>COMMAND` normalization?
- Should PRD include formal non-goals and release acceptance criteria per milestone?
