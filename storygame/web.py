from __future__ import annotations

from dataclasses import dataclass
from os import getenv
from pathlib import Path
from random import Random
from uuid import uuid4

from fastapi import FastAPI, HTTPException
from fastapi.responses import HTMLResponse
from pydantic import BaseModel

from storygame.cli import _build_narrator, run_turn
from storygame.engine.state import GameState
from storygame.engine.world import build_default_state
from storygame.llm.adapters import Narrator
from storygame.persistence.savegame_sqlite import SqliteSaveStore
from storygame.plot.freytag import get_phase


@dataclass
class _SessionState:
    state: GameState
    rng: Random


class _ScopedSaveStore:
    def __init__(self, store: SqliteSaveStore, scope: str) -> None:
        self._store = store
        self._scope = scope

    def _slot(self, slot: str) -> str:
        return f"{self._scope}:{slot}"

    def save_run(
        self,
        slot: str,
        state: GameState,
        rng: Random,
        raw_command: str = "save",
        action_kind: str = "save",
        beat_type: str | None = None,
        template_key: str | None = None,
        transcript: list[str] | None = None,
        judge_decision: dict[str, str] | None = None,
    ) -> None:
        self._store.save_run(
            self._slot(slot),
            state,
            rng,
            raw_command=raw_command,
            action_kind=action_kind,
            beat_type=beat_type,
            template_key=template_key,
            transcript=transcript,
            judge_decision=judge_decision,
        )

    def load_run(self, slot: str) -> tuple[GameState, Random]:
        return self._store.load_run(self._slot(slot))


class TurnRequest(BaseModel):
    command: str
    run_id: str | None = None
    seed: int = 123
    debug: bool = False


class StateSnapshot(BaseModel):
    run_id: str
    location: str
    room_name: str
    inventory: list[str]
    objective: str
    phase: str
    progress: float
    tension: float
    turn_index: int


class TurnResponse(BaseModel):
    run_id: str
    command: str
    action_raw: str
    beat: str
    continued: bool
    lines: list[str]
    state: StateSnapshot


def create_app(
    save_db_path: str | Path | None = None,
    default_seed: int = 123,
    narrator_mode: str | None = None,
) -> FastAPI:
    app = FastAPI(title="Freytag Forge", version="0.1.0")

    save_db = Path("runs/storygame_web_saves.sqlite") if save_db_path is None else Path(save_db_path)
    store = SqliteSaveStore(save_db, check_same_thread=False)
    sessions: dict[str, _SessionState] = {}
    resolved_narrator_mode = _resolve_narrator_mode(narrator_mode)
    narrator: Narrator = _build_narrator(resolved_narrator_mode)

    @app.get("/", response_class=HTMLResponse)
    async def index() -> str:
        return _WEB_UI_HTML

    @app.post("/turn", response_model=TurnResponse)
    def submit_turn(payload: TurnRequest) -> TurnResponse:
        run_id = payload.run_id
        if run_id is not None and run_id in sessions:
            session = sessions[run_id]
        elif run_id is None:
            run_id = uuid4().hex
            session = _SessionState(build_default_state(seed=payload.seed), Random(payload.seed))
            sessions[run_id] = session
        else:
            raise HTTPException(status_code=404, detail=f"Unknown run_id '{run_id}'.")

        scoped_store = _ScopedSaveStore(store, run_id)
        next_state, lines, action_raw, beat_type, continued = run_turn(
            session.state,
            payload.command,
            session.rng,
            narrator,
            debug=payload.debug,
            save_store=scoped_store,
            memory_slot=run_id,
        )

        room = next_state.world.rooms[next_state.player.location]
        sessions[run_id].state = next_state
        response_state = StateSnapshot(
            run_id=run_id,
            location=next_state.player.location,
            room_name=room.name,
            inventory=list(next_state.player.inventory),
            objective=next_state.active_goal,
            phase=str(get_phase(next_state.progress)),
            progress=next_state.progress,
            tension=next_state.tension,
            turn_index=next_state.turn_index,
        )
        return TurnResponse(
            run_id=run_id,
            command=payload.command,
            action_raw=action_raw,
            beat=beat_type,
            continued=continued,
            lines=list(lines),
            state=response_state,
        )

    @app.on_event("shutdown")
    def _close_store() -> None:
        store.close()

    return app


def _resolve_narrator_mode(requested_mode: str | None = None) -> str:
    if requested_mode is not None:
        requested_mode = requested_mode.strip().lower()
        if requested_mode:
            return requested_mode

    explicit = getenv("FREYTAG_NARRATOR")
    if explicit:
        explicit = explicit.strip().lower()
        if explicit in {"mock", "none", "openai", "ollama"}:
            return explicit

    if getenv("OPENAI_API_KEY"):
        return "openai"

    if getenv("OLLAMA_BASE_URL") or getenv("OLLAMA_MODEL"):
        return "ollama"

    return "mock"


app = create_app()


_WEB_UI_HTML = """<!doctype html>
<html>
  <head>
    <meta charset="utf-8" />
    <title>Freytag Forge Web</title>
    <style>
      :root {
        --bg: #121826;
        --panel: #1d2433;
        --line: #cbd5e1;
        --muted: #94a3b8;
        --accent: #22d3ee;
      }

      body {
        margin: 0;
        font-family: Georgia, "Times New Roman", serif;
        background: radial-gradient(circle at top, #1f2a40, #0b1220 50%, #090e18);
        color: var(--line);
        min-height: 100vh;
      }

      .container {
        max-width: 980px;
        margin: 0 auto;
        padding: 1.5rem;
        display: grid;
        grid-template-columns: 1fr 320px;
        gap: 1rem;
      }

      .panel {
        background: color-mix(in srgb, var(--panel) 95%, #fff 5%);
        border: 1px solid #263045;
        border-radius: 12px;
        padding: 1rem;
        margin-bottom: 1rem;
      }

      .transcript {
        white-space: pre-wrap;
        font-family: Menlo, Consolas, "Courier New", monospace;
        min-height: 340px;
        line-height: 1.35;
        background: #0d1320;
      }

      .controls {
        display: flex;
        gap: 0.75rem;
        margin-top: 0.75rem;
      }

      input {
        flex: 1;
        padding: 0.65rem;
        border: 1px solid #334155;
        border-radius: 8px;
        background: #0f1729;
        color: #dbeafe;
      }

      button {
        border: 0;
        background: var(--accent);
        color: #071224;
        padding: 0.65rem 1rem;
        border-radius: 8px;
        font-weight: 700;
        cursor: pointer;
      }

      .sidebox h2 {
        margin-top: 0;
      }

      .metric {
        margin-bottom: 0.65rem;
      }

      .small {
        color: var(--muted);
        font-size: 0.95rem;
      }
    </style>
  </head>
  <body>
    <div class="container">
      <div>
        <h1>Freytag Forge</h1>
        <p>Web interface for the deterministic CLI + narrator pipeline.</p>
        <div class="panel transcript" id="transcript"></div>
        <div class="controls">
          <input id="command" placeholder="Type command (save/load supported), e.g. look" />
          <button id="submit">Send</button>
          <button id="newGame">New Game</button>
        </div>
        <p class="small">
          <label><input type="checkbox" id="debug" /> Enable debug output</label>
          <span style="margin-left: 1rem;">run_id: <strong id="runIdLabel">none</strong></span>
        </p>
      </div>
      <aside class="sidebox">
        <div class="panel">
          <h2>Inventory</h2>
          <div id="inventory" class="small">-</div>
        </div>
        <div class="panel">
          <h2>Objective</h2>
          <div id="objective" class="small">-</div>
        </div>
        <div class="panel">
          <h2>Phase / Tension</h2>
          <div id="phase" class="metric small">-</div>
          <div id="tension" class="metric small">-</div>
          <div id="progress" class="small">-</div>
        </div>
      </aside>
    </div>
    <script>
      const transcript = document.getElementById("transcript");
      const input = document.getElementById("command");
      const submit = document.getElementById("submit");
      const newGame = document.getElementById("newGame");
      const debugToggle = document.getElementById("debug");
      const runIdLabel = document.getElementById("runIdLabel");
      const inventory = document.getElementById("inventory");
      const objective = document.getElementById("objective");
      const phase = document.getElementById("phase");
      const tension = document.getElementById("tension");
      const progress = document.getElementById("progress");

      let runId = localStorage.getItem("freytag-run-id");

      function appendLine(line) {
        transcript.textContent = `${transcript.textContent}${line}\\n`;
        transcript.scrollTop = transcript.scrollHeight;
      }

      async function turn(command) {
        if (!command.trim()) {
          return;
        }
        const payload = {
          command,
          debug: debugToggle.checked,
        };
        if (runId) {
          payload.run_id = runId;
        }
        const response = await fetch("/turn", {
          method: "POST",
          headers: {"Content-Type": "application/json"},
          body: JSON.stringify(payload),
        });
        const payloadResponse = await response.json();
        if (!response.ok) {
          appendLine(`[error] ${payloadResponse.detail || "request failed"}`);
          return;
        }
        runId = payloadResponse.run_id;
        localStorage.setItem("freytag-run-id", runId);
        runIdLabel.textContent = runId;
        payloadResponse.lines.forEach(appendLine);
        inventory.textContent = payloadResponse.state.inventory.join(", ") || "(empty)";
        objective.textContent = payloadResponse.state.objective;
        phase.textContent = `Phase: ${payloadResponse.state.phase}`;
        tension.textContent = `Tension: ${payloadResponse.state.tension.toFixed(2)}`;
        progress.textContent = `Progress: ${payloadResponse.state.progress.toFixed(2)}`;
        if (!payloadResponse.continued) {
          appendLine("[game ended]");
        }
      }

      submit.addEventListener("click", async () => {
        const command = input.value;
        input.value = "";
        await turn(command);
      });
      input.addEventListener("keydown", async (event) => {
        if (event.key === "Enter") {
          const command = input.value;
          input.value = "";
          await turn(command);
        }
      });

      newGame.addEventListener("click", () => {
        localStorage.removeItem("freytag-run-id");
        runId = null;
        runIdLabel.textContent = "none";
        transcript.textContent = "";
      });

      if (runId) {
        runIdLabel.textContent = runId;
      }

      appendLine("Ready. Save/load are available via commands, e.g. save checkpoint / load checkpoint.");
    </script>
  </body>
</html>
"""
