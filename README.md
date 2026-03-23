# Freytag Forge

Freytag Forge is a story-first detective RPG in your terminal/browser: you type what you do, the world reacts, and the narrative stays coherent across turns with deterministic fact-backed state under the hood.

## A Quick Taste
```text
Outside The Mansion
Broad stone steps rise to a carved oak door framed by weathered columns.
Daria Stone waits just inside the foyer windows, watching your next move.
Rain slicks the stone and leaves the brass door handle cold under your hand.

>LOOK THROUGH THE FOYER WINDOW
The foyer beyond the glass is lit in amber bands. Daria lifts the case file a little, signaling that the first useful lead is already inside.

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
Ordinary gameplay:
- Natural-language inputs are the default path.
- Deterministic aliases like `look`, `go <direction>`, `take <item>`, `talk <npc>`, `use <item> on <target>`, and `inventory` are normalized into the same proposal/commit runtime instead of using a separate parser-authored experience.
- Directional shortcuts like `n`, `s`, `e`, `w`, `u`, `d` resolve to canonical movement.

Meta commands:
- `save <slot>`, `load <slot>`, `quit`, `help`

Replay + transcript:
```bash
uv run python -m storygame --seed 123 --replay runs/commands.txt --transcript runs/session.txt
```

Run tests:
```bash
make test
```

## Architecture (Focused Summary)
- Proposal-first turn routing: ordinary gameplay now runs through a shared `TurnProposal` contract, including parser-normalized deterministic actions like movement, look, take, use, and inventory. Parser handling is retained only for control-plane commands.
- Deterministic commit authority: the engine owns canonical fact-backed state for locations, inventory, flags, goals, discovered leads/clues, relationships, timed events, reveal state, and scene/dramatic state.
- LLM-authored story layer: bootstrap/opening prose, turn narration, and NPC dialogue are authored by LLMs but must stay grounded in deterministic facts.
- Scene + dramatic facts: current scene framing, dramatic question, player approach, beat phase/role, and pressure are fact-backed so narration and NPC behavior read from committed story state.
- Single bootstrap contract: startup prefers one LLM bootstrap bundle that defines protagonist identity, assistant/contact plan, goals, villains, clue placement, reveal schedule, timed events, and opening paragraphs; facts commit first, then opening prose is validated against those facts and fails closed on mismatch.
- Bootstrap objective guardrail: assistant/contact objectives are normalized away from suspect-style questioning language before opening validation so hosted demo openings stay playable when the upstream model phrases the first move poorly.
- Replan boundary: light confirmed disruptions adapt NPC behavior and story pressure around the current goal, while only player-confirmed major disruptions may rewrite core goals.
- Canonical persistence: SQLite save snapshots plus `StoryState.json` / `STORY.md` artifact history preserve the fact-backed story state and trace linkage across turns.

For full architecture and design details, see [docs/PRD.md](docs/PRD.md).
