# Freytag-Driven LLM Text Adventure (Python) — Implementation Plan

This repo builds a deterministic text-adventure engine with:
- **Structured world engine** (rules + state + event log)
- **Freytag plot manager** (phase/tension/beat control)
- **LLM narrator** (prose only; never mutates state)

Later stages add:
- **SQLite save/resume**
- **Vector memory**
- **Web UI**

## Non-negotiable design rules (prevents the 3 common failures)

1. **LLM never mutates game state**
   - Engine is the only authority for state changes.
   - LLM output is *narration only* (plus optional *suggestions* that must be validated by the engine).

2. **LLM sees a “relevant slice” of state**
   - Provide only: current location facts, inventory, active goals, last N events, current Freytag phase/tension/beat, constraints.
   - Never dump the whole database into the prompt.

3. **Deterministic spine**
   - Plot manager selects beats/events deterministically (seeded).
   - Engine applies events deterministically.
   - LLM decorates the chosen beat/event with prose.

---

## Milestones and deliverables

### Milestone 0 — Repo scaffolding + CI (Day 0)
**Goal:** A runnable CLI skeleton with tests and CI.

- [x] Create `pyproject.toml`
  - Dependencies (MVP): `pytest`, `pytest-cov`, `ruff`
  - Optional: `mypy`
- [x] Create package layout:
        storygame/
        init.py
        cli.py
        engine/
        plot/
        llm/
        tests/
        .github/workflows/test.yml
- [x] Add `ruff` config and `pytest` config
- [x] Add GitHub Actions workflow: lint + tests
- [x] Add `make` (or just documented commands)
- [x] `python -m storygame` (or `storygame` console script)
- [x] `pytest -q`
- [x] `ruff check .`

**Acceptance criteria**
- [x] `pytest` passes in CI
- [x] `python -m storygame` runs and starts the game loop

---

### Milestone 1 — Deterministic world engine (Day 1–2)
**Goal:** Playable tiny game with no LLM involved.

#### 1.1 Core data model (engine/state.py)
- [x] Define dataclasses (or pydantic, but keep MVP simple):
- [x] `GameState`
- [x] `PlayerState` (location, inventory, flags, stats)
- [x] `WorldState` (rooms, items, NPCs, connections)
- [x] `EventLog` (list of `Event`)
- [x] Define `Event` schema:
  - fields: `type`, `entities`, `tags`, `delta_progress`, `delta_tension`, `message_key?`, `turn_index`, `timestamp?`

#### 1.2 Parser (engine/parser.py)
- [x] Minimal action AST:
- [x] `LOOK`
- [x] `MOVE(destination|direction)`
- [x] `TAKE(item)`
- [x] `TALK(npc)`
- [x] `USE(item, target?)`
- [x] `HELP`, `INVENTORY`
- [x] Implement `parse_command(str) -> Action`

#### 1.3 Rules + state transition (engine/rules.py)
- [x] Implement pure-ish transition:
- [x] `apply_action(state: GameState, action: Action, rng: Random) -> (GameState, list[Event])`
- [x] Validate actions:
- [x] cannot move through locked exits
- [x] cannot take missing item
- [x] cannot talk to missing NPC

#### 1.4 Minimal world content (engine/world.py)
- [x] Define a tiny world (4–6 rooms) + some items + one NPC
- [x] Ensure there is a simple objective that can progress the story

#### 1.5 CLI loop (cli.py)
- [x] Display current room description (engine-generated for now)
- [x] Read player input
- [x] Parse -> apply_action -> print result (basic text)
- [x] Print debug info when `--debug`:
- [x] turn, location, progress, tension, last event types

#### Tests
- [x] `test_parser.py`
- [x] `test_world_rules.py` (move/take/invalid action behavior)
- [x] `test_reproducibility.py` (same seed + same command list => same event log/state)

**Acceptance criteria**
- [x] Can complete a tiny objective via CLI without LLM
- [x] Deterministic replay using seed

---

### Milestone 2 — Freytag plot manager + deterministic beat/event selection (Day 3–4)
**Goal:** The game reliably follows an arc: exposition → rising → climax → falling → resolution.

#### 2.1 Freytag phase mapping (plot/freytag.py)
- [x] Define phases based on progress:
- exposition: `<0.2`
- rising_action: `0.2–0.6`
- climax: `0.6–0.8`
- falling_action: `0.8–0.95`
- resolution: `>=0.95`
- [x] Provide `get_phase(progress) -> Phase`

#### 2.2 Tension model (plot/tension.py)
- [x] Track tension in `[0..1]`
- [x] Target tension bands per phase
- [x] Update tension based on events (`delta_tension`) and smoothing

#### 2.3 Beat manager (plot/beat_manager.py)
- [x] Define beat types per phase (examples):
- exposition: `hook`, `inciting_incident`, `goal_reveal`
- rising: `complication`, `revelation`, `escalation`, `setback`
- climax: `confrontation`, `irreversible_choice`
- falling: `consequence`, `escape`, `unraveling`
- resolution: `closure`, `epilogue`
- [x] Deterministic beat selection:
  inputs: phase, tension, recent beats/events, rng seed
- [x] output: `Beat(type, tags, required_entities?)`

#### 2.4 Event library (engine/events.py)
- [x] Create small library of event templates keyed by tags
- [x] `select_event(beat, state, rng) -> EventTemplate`
- [x] `apply_event_template(state, template, rng) -> (state, events)`
- [x] Ensure events are **facts** (engine side), not prose

#### Tests
- [x] `test_plot_freytag.py` (phase transitions)
- [x] `test_event_selection.py` (beat→event tag matching and determinism)
- [x] Regression test: a scripted command list triggers a climax event near 0.7–0.8 progress

**Acceptance criteria**
- [x] A typical playthrough hits a climax beat before resolution
- [x] Deterministic beat/event selection given seed + commands

---

### Milestone 3 — LLM narrator integration (Day 5)
**Goal:** LLM writes prose based on engine truth + chosen beat, without breaking rules.

#### 3.1 LLM interface (llm/adapters.py)
- [x] Define `Narrator` protocol:
- [x] `generate(context: NarrationContext) -> str`
- [x] Implement at least one adapter:
- [x] `MockNarrator` (for tests)
- [x] `OpenAIAdapter`
- [x] `OllamaAdapter` (local endpoint support)
- [x] Add config via env vars (do not hardcode secrets)

#### 3.2 Context builder (llm/context.py)
- [x] Build a **state slice**:
- [x] current room facts (name, visible items, exits, NPCs)
- [x] canonical NPC identity facts (name + pronouns + identity summary) to reduce narrative drift
- [x] inventory summary
- [x] active goal/objective
- [x] last N events (N=5) summarized structurally
- [x] Freytag phase + tension + selected beat type
- [x] hard constraints (see prompts)
- [x] Enforce context budget:
- [x] truncate lists
- [x] keep summaries short

#### 3.3 Prompt templates (llm/prompts.py)
- [x] System constraints:
- [x] do not invent items/locations/NPCs
- [x] do not change state
- [x] narration must be consistent with provided facts
- [x] User message includes context slice + player action + chosen beat
- [x] User prompt includes canonical NPC identity/pronoun facts for continuity across turns

#### 3.4 Engine integration (cli.py / engine loop)
- [x] After action + plot selection:
- [x] call narrator to render scene text
- [x] print narration
- [x] Debug mode prints:
- [x] phase, tension, beat, selected event types
- [x] context slice keys (not full prompt)
- [x] Add narrator mode switch in CLI (`--narrator mock|none|openai`) and require `OPENAI_API_KEY` for OpenAI mode.
- [x] Add CLI support for local narration via `--narrator ollama` and `OLLAMA_*` env config.

#### Tests
- [x] `test_llm_context.py` (context includes required keys, respects size limit)
- [x] `test_prompt_snapshots.py` (golden prompt formatting using MockNarrator)
- [x] Ensure the engine does not parse LLM output for state changes (MVP)

**Acceptance criteria**
- [x] Game is still deterministic in state evolution
- [x] LLM narration reflects beat/phase without inventing facts (as much as models allow)

---

### Milestone 4 — MVP hardening + regression corpus (Day 6–7)
**Goal:** Debuggable, repeatable, demo-worthy.

- [x] Add transcript logging to `runs/` (gitignored)
- [x] Add “golden runs” regression inputs:
  - [x] store command lists (and seed)
  - [x] assert final state hash and key event sequence
- [x] Add `--seed` CLI option and `--replay <commands.txt>`
- [x] Expand content modestly:
  - [x] 8–12 rooms
  - [x] ~20 items total
  - [x] 8–12 event templates
  - [x] at least 2 climax events

**Acceptance criteria**
- [x] 10–15 minute playthrough yields full Freytag arc
- [x] Replays reproduce state timeline

---

## Later stages (planned, not MVP)

### Stage 5 — Save/Resume with SQLite
**Key rule:** persist structured state + event log + seed, not just transcript text.

- [x] `persistence/savegame_sqlite.py`
- [x] tables: runs, turns, state_snapshots, events, transcript_lines
- [x] CLI: `save <slot>`, `load <slot>`
- [x] Auto-save per turn optional

**Acceptance criteria**
- [x] Can stop and resume exactly from same state and seed
- [x] Replayed continuation stays deterministic

### Stage 6 — Vector memory (constrained)
**Key rule:** memory is “soft context” only; engine state remains truth.

- [x] Store summaries of:
- long-term NPC relationship notes
- lore discovered
- prior important events
- [x] Retrieve only when relevant (room/NPC/goal tags)
- [x] Never allow retrieved text to override engine facts

**Exit criteria**
- [x] Retrieval improves continuity without introducing contradictions

### Stage 7 — Web UI
- [ ] FastAPI backend endpoint:
- POST `/turn` {command, run_id}
- [ ] Minimal frontend:
- transcript panel
- input box
- inventory/objective panel
- phase/tension indicator
- debug toggle

**Acceptance criteria**
- [ ] Same engine used by CLI and web
- [ ] Save/load works through web UI

---

## Definition of Done (MVP)
- [x] Deterministic engine (seeded) with reproducible replays
- [x] Event library drives state changes (facts)
- [x] LLM narrates only (no state mutation)
- [x] Tests + CI green
- [x] Freytag plot manager controls pacing and beat selection
- [x] Basic documentation:
- how to run
- how to set seed
- how to replay
- how to plug in LLM adapter
