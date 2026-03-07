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
