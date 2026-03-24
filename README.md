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
- Bootstrap objective guardrail: assistant/contact objectives and opening paragraphs are normalized away from suspect-style questioning language before opening validation so hosted demo openings stay playable when the upstream model phrases the first move poorly.
- Web opening path: both web surfaces now use a single bootstrap call plus deterministic validation on the opening critical path, skipping bootstrap critique, remote room-presentation generation, and opening editor passes until after first paint.
- Opening grounding: bootstrap and narrator opening prompts now carry canonical room description, exits, visible NPCs, visible items, and inventory constraints so the first scene stays anchored to deterministic location facts instead of relying on ad hoc post-hoc cleanup.
- Opening contract hygiene: narrator/bootstrap opening paragraphs now drop prompt-shaped field dumps such as `Room name: ... Items: ... Exits: ...` before any player-facing opening is accepted.
- Mystery opening custody: the default mystery start seeds `case_file` to Daria Stone rather than the player, so opening prompts begin from the fact-backed “assistant has the file” world state while `read/review case file` still works through nearby-holder access.
- Mystery arrival staging: the default mystery start also seeds an `arrival_sedan` at `front_steps`, so the car Elias arrived in is present in the fact store, appears in the room block/context, and can naturally anchor opening prose.
- Shared scene grounding: narration and freeform planner prompts now carry richer fact-backed scene, NPC, and visible-item context across ordinary turns as well, including player arrival facts, NPC scene purpose, and item owner/driver/state when relevant.
- Scene-scoped world actions stay proposal-first without being auto-rerouted into nearby NPC conversation; direct NPC reply requirements now apply only when the player actually addresses or questions a visible character.
- Room presentation now reads visible-item custody/state facts generically, so player-owned vehicles and similar scene objects are described consistently across map locations instead of through room-specific hard-coded copy.
- Hosted demo bootstrap now prefers a prose opening path on Cloudflare-backed deployments when the worker cannot satisfy the story-bootstrap JSON contract, keeping the first turn playable without local OpenAI credentials.
- Freeform dialogue facts: accepted targeted NPC replies can commit bounded facts back into the fact store; canonical appearance facts are seeded for mystery contacts, appearance questions are grounded to those facts, and contradictory wardrobe replies now fail closed.
- Replan boundary: light confirmed disruptions adapt NPC behavior and story pressure around the current goal, while only player-confirmed major disruptions may rewrite core goals.
- Canonical persistence: SQLite save snapshots plus `StoryState.json` / `STORY.md` artifact history preserve the fact-backed story state and trace linkage across turns.

For full architecture and design details, see [docs/PRD.md](docs/PRD.md).
