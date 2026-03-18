from __future__ import annotations

from dataclasses import dataclass
from os import getenv
from pathlib import Path
from random import Random
from typing import Literal
from uuid import uuid4

from fastapi import FastAPI, HTTPException
from fastapi.responses import HTMLResponse
from pydantic import BaseModel

from storygame.cli import _build_narrator
from storygame.engine.state import GameState
from storygame.engine.world import build_default_state
from storygame.llm.adapters import Narrator
from storygame.llm.output_editor import OutputEditor, build_output_editor
from storygame.llm.story_director import StoryDirector
from storygame.persistence.savegame_sqlite import SqliteSaveStore
from storygame.web_runtime import (
    ScopedSaveStore,
    build_bootstrap_response_payload,
    build_turn_response_payload,
    execute_turn,
    is_bootstrap_command,
)


@dataclass
class _SessionState:
    state: GameState
    rng: Random

class TurnRequest(BaseModel):
    command: str
    run_id: str | None = None
    seed: int = 123
    genre: Literal[
        "sci-fi",
        "mystery",
        "romance",
        "adventure",
        "action",
        "suspense",
        "drama",
        "fantasy",
        "horror",
        "thriller",
    ] = "mystery"
    session_length: Literal["short", "medium", "long"] = "medium"
    tone: Literal["neutral", "dark", "light", "romantic", "tense", "mysterious", "epic"] = "neutral"
    debug: bool = False


class StateSnapshot(BaseModel):
    run_id: str
    location: str
    room_name: str
    inventory: list[str]
    genre: str
    tone: str
    session_length: str
    plot_curve_id: str
    story_outline_id: str
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
    narrator: Narrator | None = None,
    output_editor: OutputEditor | None = None,
    story_director: StoryDirector | None = None,
) -> FastAPI:
    app = FastAPI(title="Freytag Forge", version="0.1.0")

    save_db = Path("runs/storygame_web_saves.sqlite") if save_db_path is None else Path(save_db_path)
    store = SqliteSaveStore(save_db, check_same_thread=False)
    sessions: dict[str, _SessionState] = {}
    resolved_narrator_mode = _resolve_narrator_mode(narrator_mode)
    active_narrator: Narrator = _build_narrator(resolved_narrator_mode) if narrator is None else narrator
    active_output_editor = build_output_editor(resolved_narrator_mode) if output_editor is None else output_editor
    active_story_director = (
        StoryDirector(resolved_narrator_mode, active_output_editor) if story_director is None else story_director
    )

    @app.get("/", response_class=HTMLResponse)
    async def index() -> str:
        return _WEB_UI_HTML

    @app.post("/turn", response_model=TurnResponse)
    def submit_turn(payload: TurnRequest) -> TurnResponse:
        run_id = payload.run_id
        session_started = False
        if run_id is not None and run_id in sessions:
            session = sessions[run_id]
        elif run_id is None:
            run_id = uuid4().hex
            session = _SessionState(
                build_default_state(
                    seed=payload.seed,
                    genre=payload.genre,
                    session_length=payload.session_length,
                    tone=payload.tone,
                ),
                Random(payload.seed),
            )
            sessions[run_id] = session
            session_started = True
        else:
            raise HTTPException(status_code=404, detail=f"Unknown run_id '{run_id}'.")

        start_state = session.state
        bootstrap_only = session_started and is_bootstrap_command(payload.command)
        if bootstrap_only:
            return TurnResponse.model_validate(
                build_bootstrap_response_payload(
                    start_state,
                    payload.command,
                    "run_id",
                    run_id,
                    active_story_director,
                )
            )

        scoped_store = ScopedSaveStore(store, run_id)
        result = execute_turn(
            start_state,
            payload.command,
            session.rng,
            active_narrator,
            narrator_mode=resolved_narrator_mode,
            debug=payload.debug,
            save_store=scoped_store,
            memory_slot=run_id,
            output_editor=active_output_editor,
            story_director=active_story_director,
        )

        sessions[run_id].state = result.next_state
        return TurnResponse.model_validate(
            build_turn_response_payload(
                result.next_state,
                payload.command,
                result.action_raw,
                result.beat,
                result.continued,
                result.lines,
                "run_id",
                run_id,
            )
        )

    @app.on_event("shutdown")
    def _close_store() -> None:
        store.close()

    return app


def _resolve_narrator_mode(requested_mode: str | None = None) -> str:
    if requested_mode is not None:
        requested_mode = requested_mode.strip().lower()
        if requested_mode in {"openai", "ollama"}:
            return requested_mode
        if requested_mode:
            raise ValueError("Narrator mode must be 'openai' or 'ollama'.")

    explicit = getenv("FREYTAG_NARRATOR")
    if explicit:
        explicit = explicit.strip().lower()
        if explicit in {"openai", "ollama"}:
            return explicit

    if getenv("OPENAI_API_KEY"):
        return "openai"

    if getenv("OLLAMA_BASE_URL") or getenv("OLLAMA_MODEL"):
        return "ollama"

    return "openai"


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
        startNewGame();
      });

      async function startNewGame() {
        localStorage.removeItem("freytag-run-id");
        runId = null;
        runIdLabel.textContent = "none";
        transcript.textContent = "";
        inventory.textContent = "(empty)";
        objective.textContent = "-";
        phase.textContent = "-";
        tension.textContent = "-";
        progress.textContent = "-";
        await turn("look");
      }

      async function bootstrap() {
        if (runId) {
          runIdLabel.textContent = runId;
        } else {
          await startNewGame();
        }
      }

      bootstrap();
    </script>
  </body>
</html>
"""
