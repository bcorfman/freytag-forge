# Freytag Forge

Freytag Forge is a story-first detective RPG in your terminal/browser: you type what you do, the world reacts, and the narrative stays coherent across turns with deterministic state tracking under the hood.

## A Quick Taste
```text
Outside The Mansion
Broad stone steps rise to a carved oak door framed by weathered columns.
A torn ledger page lies half-caught in a crack between the stones near the bottom step.
Daria Stone is nearby, watching your next move.

>PICK UP THE LEDGER PAGE
Clue noted: Half-burned ledger page with initials that match the victim's diary.

>DARIA, WHAT DO YOU MAKE OF THIS?
Daria says: "The initials aren't random. Start with whoever had access to the archives tonight."
```

## Quick Start
### 1) Prereqs
- Python 3.12+
- [uv](https://docs.astral.sh/uv/)

### 2) Install deps
```bash
make install
```

### 3) Configure narrator backend
OpenAI:
```bash
export OPENAI_API_KEY="your_api_key"
export OPENAI_MODEL="gpt-4o-mini"  # optional
```

Ollama:
```bash
ollama serve
ollama pull llama3.2
export OLLAMA_MODEL="llama3.2"  # optional
export OLLAMA_BASE_URL="http://localhost:11434/api/chat"  # optional
```

### 4) Run
```bash
make run
```
Then open `http://127.0.0.1:8000`.

## Usage Commands
Core gameplay commands:
- `look`, `go <direction>`, `take <item>`, `talk <npc>`, `use <item> on <target>`, `inventory`

Meta commands:
- `save <slot>`, `load <slot>`, `quit`

Replay + transcript:
```bash
uv run python -m storygame --seed 123 --replay runs/commands.txt --transcript runs/session.txt
```

Run tests:
```bash
make test
```

## Architecture (Focused Summary)
- Planner-first turn routing: ordinary gameplay is interpreted through the LLM/freeform proposal path first, with parser handling kept to control-plane commands and resilience fallback.
- Deterministic commit authority: the engine owns canonical fact-backed state for locations, inventory, flags, goals, discovered leads/clues, relationships, timed events, and reveal state.
- LLM-authored story layer: bootstrap/opening prose, turn narration, and NPC dialogue are authored by LLMs but must stay grounded in deterministic facts.
- Single bootstrap contract: startup prefers one LLM bootstrap bundle that defines protagonist identity, assistant/contact plan, goals, villains, clue placement, reveal schedule, timed events, and opening paragraphs; accepted outputs are persisted back into runtime facts.
- Replan boundary: light confirmed disruptions adapt NPC behavior and story pressure around the current goal, while only player-confirmed major disruptions may rewrite core goals.
- Canonical persistence: SQLite save snapshots plus `StoryState.json` / `STORY.md` artifact history preserve the fact-backed story state and trace linkage across turns.

For full architecture and design details, see [docs/PRD.md](docs/PRD.md).
