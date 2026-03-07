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

## Web UI

Serve the FastAPI app:

```bash
uv run uvicorn storygame.web:app --reload
```

Open [http://127.0.0.1:8000](http://127.0.0.1:8000) and interact with the same engine used by the CLI.

The web client uses:
- `POST /turn` with `{ "command": "...", "run_id": "...", "seed": 123, "debug": false }`.
- `run_id` can be omitted to create a fresh run.
- `save <slot>` and `load <slot>` are handled by the same backend and persist through a shared SQLite save store.

### Web narrator selection

Web narrator is selected automatically:

- `FREYTAG_NARRATOR=openai` explicitly enables OpenAI.
- `FREYTAG_NARRATOR=ollama` explicitly enables Ollama.
- `FREYTAG_NARRATOR=mock` / `FREYTAG_NARRATOR=none` for deterministic/non-LM mode.
- Otherwise, the presence of `OPENAI_API_KEY` enables OpenAI.
- Otherwise, `OLLAMA_BASE_URL` or `OLLAMA_MODEL` enables Ollama.
- Otherwise it falls back to `mock`.

To force a mode, set `FREYTAG_NARRATOR` before starting:

```bash
FREYTAG_NARRATOR=openai uv run uvicorn storygame.web:app --reload
```


## Save and Resume

Save and resume are now available with a local SQLite save file.

Save to a slot:

```bash
python -m storygame --seed 123 --save-db runs/storygame_saves.sqlite
```

Then at the prompt:

```text
> save checkpoint
```

Resume from a slot:

```text
> load checkpoint
```

You can also provide a replay command file and database:

```bash
python -m storygame --seed 123 --replay runs/demo_commands.txt --save-db runs/storygame_saves.sqlite
```

Optional auto-save on each turn:

```bash
python -m storygame --seed 123 --save-db runs/storygame_saves.sqlite --autosave-slot autosave
```

### Canonical Story Artifacts

Each save slot writes a canonical artifact pair in `story_artifacts/<slot>/`:

- `StoryState.json`: authoritative structured state (`schema_version=2`).
- `STORY.md`: narrative workspace rendered from `StoryState.json`.

Artifact guarantees:

- `StoryState.json` includes deterministic trace metadata:
- `raw_command`, `action_kind`, `beat_type`, `template_key`, and an accepted `judge_decision`.
- `StoryState.json` includes `story_markdown_sha256` for the exact `STORY.md` snapshot.
- Writes are orchestrator-only through the save-store persistence path.
- Before each write, existing artifacts are integrity-checked. If `STORY.md` was externally edited, persistence fails with an integrity error.
- Canonical JSON rendering is deterministic (`sort_keys` + stable formatting), and round-trips reproduce byte-stable output.

## Test and Lint

```bash
uv run pytest -q
uv run ruff check .
```

To keep style checks automatic, install and run pre-commit:

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

## Running Ollama locally

Start Ollama and keep it alive in one terminal:

```bash
ollama serve
```

In another terminal, ensure a model is pulled first:

```bash
ollama pull llama3.2
```

Then run:

```bash
python -m storygame --seed 123 --narrator ollama
```

If `localhost` fails for Python but works in your browser, point the adapter explicitly at IPv4:

```bash
OLLAMA_BASE_URL=http://127.0.0.1:11434 uv run python -m storygame --seed 123 --narrator ollama
```

If Ollama is not available, gameplay continues with a fallback narrator error line and the engine will stay deterministic.

## Recent Changes

- Story coherence overhaul for the forge scenario:
  - The first playable turn now includes an explicit briefing with backstory and stakes (who framed your mentor, what was stolen, and why exposing the conspiracy matters).
  - Plot events now describe a forged resonance transmitter, not a magically ringing broken bell.
  - Removed nonsensical "memory trap" language in favor of concrete physical complications.
  - Room output now includes a directional `Signal:` hint so navigation follows audible logic.
  - NPC `talk` output is now knowledge-bounded by role/source (`rumor`, `archive record`, `maintenance record`, `witness account`) and gives actionable next leads.
  - Added meaningful item interactions (for example: `use glass lens on sea map`) that set flags and advance progress.
  - Added item role typing (`junk`, `tool`, `clue`, `evidence`) to reduce inventory/room clutter and keep prompts focused on actionable objects.
  - Added a turn-level `Caseboard` with known facts, open questions, and active leads to keep the mystery legible.
- Added canonical NPC continuity facts in narrator context and prompts:
  - NPC identity and pronouns are now always present in the LLM context slice.
  - This reduces drift like "oracle changed gender between turns."
- Improved local narrator reliability:
  - `OllamaAdapter` now attempts compatible endpoint variants (`/api/chat` and `/api/generate`).
  - Endpoint diagnostics are surfaced in narration failure lines.
  - Narrator failures no longer mutate state and do not stop turn progression.
- Tuned narration defaults for consistency:
  - Default temperature lowered to `0.2` for both OpenAI and Ollama adapters.
  - Default token cap raised to `512`.
  - Default Ollama timeout raised to `180s` for slower local generations.
