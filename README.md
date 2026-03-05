# FreytagForge

Deterministic text adventure engine with Freytag pacing and narration adapters.

## Quickstart

Install dependencies:

```bash
uv sync
```

Run interactive mode:

```bash
python -m storygame --seed 123
```

Run without narration (engine-only text):

```bash
python -m storygame --seed 123 --narrator none
```

## Replay

Replay scripted commands:

```bash
python -m storygame --seed 123 --replay runs/demo_commands.txt
```

Write replay transcript:

```bash
python -m storygame --seed 123 --replay runs/demo_commands.txt --transcript runs/demo_transcript.txt
```

## Test and Lint

```bash
uv run pytest -q
uv run ruff check .
```

## CLI Options

- `--seed`: deterministic world, beat, and event selection.
- `--replay <path>`: run command list from file.
- `--debug`: print turn/phase/tension/beat diagnostics and context keys.
- `--transcript <path>`: write transcript lines.
- `--narrator mock|none`: narrator mode.

## LLM Adapter

`storygame.llm.adapters.Narrator` is the integration boundary:

- `MockNarrator`: deterministic test narrator.
- `SilentNarrator`: disables narration.
- `OpenAIAdapter`: reads `OPENAI_API_KEY`, `OPENAI_MODEL`, and `OPENAI_TIMEOUT` from environment.

Engine state never depends on LLM output. Narrators receive a constrained context slice built by `storygame.llm.context.build_narration_context`.
