# Freytag Forge

Deterministic interactive fiction engine with Freytag pacing, canonical turn artifacts, and a multi-critic coherence gate.

## Why this exists

- Playable CLI + web story engine with deterministic seeds.
- Narrative quality control that is testable and reproducible.
- Canonical state artifacts that are traceable and tamper-checked.

## Get started in 60 seconds

```bash
uv sync
uv run python -m storygame --seed 123
```

At the prompt:

```text
look
save checkpoint
load checkpoint
quit
```

## Core features

- Deterministic engine:
- world evolution is seed-driven and replayable.
- Coherence gate (`storygame.llm.coherence`):
- 3 critics (`continuity`, `causality`, `dialogue_fit`) + 1 deterministic judge.
- weighted rubric: `0.4/0.4/0.2`, threshold `>=80`, critical floors on continuity and causality.
- bounded critique loop (`max_rounds=10`).
- deterministic pre-judge validators:
- `entity_reachability`
- `inventory_location_consistency`
- `committed_state_contradiction`
- `beat_transition_legality`
- invalid candidates are revised without consuming critique-round budget.
- Canonical turn artifacts per save slot:
- `story_artifacts/<slot>/StoryState.json` (`schema_version=2`)
- `story_artifacts/<slot>/STORY.md`
- `StoryState.json` includes trace metadata (`raw_command`, `action_kind`, `beat_type`, `template_key`, accepted `judge_decision`) and `story_markdown_sha256`.
- artifact pair integrity is checked before overwrite; tampered `STORY.md` causes persistence failure.

## Run modes

- CLI:

```bash
uv run python -m storygame --seed 123
```

- Replay + transcript:

```bash
uv run python -m storygame --seed 123 --replay runs/demo_commands.txt --transcript runs/demo_transcript.txt
```

- Web app:

```bash
uv run uvicorn storygame.web:app --reload
```

Open `http://127.0.0.1:8000`.

## Narrator backends

- `--narrator mock` (deterministic default for testing)
- `--narrator none` (engine-only output)
- `--narrator openai` (`OPENAI_API_KEY` required)
- `--narrator ollama` (`OLLAMA_BASE_URL` / `OLLAMA_MODEL`)

Engine state never depends on LLM output.

## Contributing

1. Install dev tooling:
```bash
uv sync --group dev
uv run pre-commit install
uv run pre-commit run --all-files
```

## CLI Options

- `--seed`: deterministic world, beat, and event selection.
- `--replay <path>`: run command list from file.
- `--debug`: print turn/phase/tension/beat diagnostics and context keys.
- `--transcript <path>`: write transcript lines.
- `--narrator mock|none|openai|ollama`: narrator mode.
  - `openai`: calls `api.openai.com` with API key.
  - `ollama`: calls local Ollama server (`OLLAMA_BASE_URL`).
- `--save-db <path>`: path to SQLite save/resume database.
- `--autosave-slot <slot>`: write snapshot to slot after each turn.

## LLM Adapter

`storygame.llm.adapters.Narrator` is the integration boundary:

- `MockNarrator`: deterministic test narrator.
- `SilentNarrator`: disables narration.
- `OpenAIAdapter`: reads from environment:
  - `OPENAI_API_KEY` (required for `--narrator openai`)
  - `OPENAI_MODEL` (default `gpt-4o-mini`)
  - `OPENAI_TIMEOUT` (default `10.0`)
  - `OPENAI_BASE_URL` (optional override for API endpoint)
  - `OPENAI_TEMPERATURE` (default `0.2`, lower drift)
  - `OPENAI_MAX_TOKENS` (default `512`)
- `OllamaAdapter`: reads from environment:
  - `OLLAMA_MODEL` (default `llama3.2`)
  - `OLLAMA_TIMEOUT` (default `180.0`)
  - `OLLAMA_BASE_URL` (default `http://localhost:11434/api/chat`)
  - `OLLAMA_TEMPERATURE` (default `0.2`, lower drift)
  - `OLLAMA_MAX_TOKENS` (default `512`)

Engine state never depends on LLM output. Narrators receive a constrained context slice built by `storygame.llm.context.build_narration_context`.
That context now includes canonical NPC identity/pronoun facts so narration can keep details stable across turns.

## Coherence Gate

Turn narration now runs through a deterministic multi-critic coherence gate (`storygame.llm.coherence`) before output:

- Three critique agents run every round: `continuity`, `causality`, and `dialogue_fit`.
- Each critique report returns all rubric dimensions (`continuity`, `causality`, `dialogue_fit`) and feedback text.
- A single deterministic judge aggregates critic outputs with fixed weights:
- `continuity=0.4`, `causality=0.4`, `dialogue_fit=0.2`.
- Acceptance rule is fixed:
- total score `>= 80`, plus critical floors `continuity >= 70` and `causality >= 70`.
- Critique loop is bounded to `max_rounds=10` and emits a deterministic `JudgeDecision` including critic IDs and rubric component scores.
- Hard turn budgets are enforced:
- max critique rounds, token spend per role (`narrator`, `critics`), and wall-clock timeout.
- If a budget is exhausted before acceptance, the gate hard-fails with a deterministic reason code:
- `BUDGET_MAX_CRITIQUE_ROUNDS`, `BUDGET_NARRATOR_TOKENS`, `BUDGET_CRITIC_TOKENS`, or `BUDGET_WALL_CLOCK_TIMEOUT`.
- Coherence telemetry is emitted per turn with:
- critique rounds used, per-role token spend, elapsed milliseconds, and hard-fail reason.
- Hard-fail recovery uses a constrained reversal branch for retryable failures:
- deterministic reversal seed and machine-readable delta with `preserved`, `modified`, and `discarded`.
- preserved fields include committed room/action/goal and visible state anchors.
- replan retry runs through the same critique/judge pipeline with bounded reversal rounds.
- Debug mode prints a judge summary line with status, score, threshold, round, critic IDs, components, and decision ID.
- Agent I/O contracts are enforced in `storygame.llm.contracts`:
- `AgentProposal`, `StoryPatch`, `CritiqueReport`, `JudgeDecision`, and `RevisionDirective` have explicit parsers/adapters with `extra=forbid`.
- natural-language fields (`rationale`, `feedback`, revision instruction) are length-bounded.
- malformed payloads are rejected with deterministic contract error codes (for example: `CONTRACT_INVALID_CRITIQUE_REPORT`) rather than silently falling through.

## Running Ollama locally

Start Ollama and keep it alive in one terminal:

```bash
ollama serve
```

In another terminal, ensure a model is pulled first:

```bash
ollama pull llama3.2
```
2. Run checks before opening a PR:
```bash
uv run pytest -q
uv run ruff check .
```
3. Keep changes deterministic and covered:
- add tests for behavior changes
- keep save/replay behavior seed-stable
- update this README when behavior or contracts change

## Helpful commands

```bash
make install
make test
make lint
make run-cli
make run-web
```
