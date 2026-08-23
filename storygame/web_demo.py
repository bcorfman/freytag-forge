"""The hosted V2 application adapter; no V1 runtime is reachable here."""

from __future__ import annotations

from dataclasses import dataclass
from os import getenv
from pathlib import Path
from uuid import uuid4

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field

from storygame.authoring.compiler import CompilationError, load_compiled_story_fixture
from storygame.persistence.runtime_state_sqlite import RuntimeSaveError, RuntimeStateSqliteStore
from storygame.persistence.story_state import write_artifacts
from storygame.runtime.cloudflare import CloudflareTurnModel
from storygame.runtime.engine import RuntimeEngine, TurnModel
from storygame.runtime.state import RuntimeState, bootstrap_runtime_state


class SessionCreateRequest(BaseModel):
    genre: str = Field(default="mystery", min_length=1, max_length=80)


class TurnRequest(BaseModel):
    session_id: str = Field(min_length=1, max_length=128)
    command: str = Field(min_length=1, max_length=4000)
    genre: str = Field(default="mystery", min_length=1, max_length=80)


class SessionLoadRequest(BaseModel):
    session_id: str = Field(min_length=1, max_length=128)
    genre: str = Field(default="mystery", min_length=1, max_length=80)


class _UnavailableModel:
    def play_turn(self, context: object, *, json_object: bool) -> object:
        raise RuntimeError("V2 turn model is not configured")


@dataclass
class _Session:
    engine: RuntimeEngine


def _default_model() -> TurnModel:
    try:
        return CloudflareTurnModel()
    except ValueError:
        return _UnavailableModel()


def _state_payload(state: RuntimeState) -> dict[str, object]:
    navigation = state.world.attributes.get("navigation", {})
    routes = navigation.get("routes", []) if isinstance(navigation, dict) else []
    names = navigation.get("names", {}) if isinstance(navigation, dict) else {}
    destinations = [
        names[route["to"]]
        for route in routes
        if isinstance(route, dict)
        and route.get("from") == state.world.location
        and isinstance(route.get("to"), str)
        and isinstance(names, dict)
        and isinstance(names.get(route["to"]), str)
    ]
    return {
        "location": state.world.location,
        "room_name": state.world.location,
        "turn_index": state.turn_index,
        "available_destinations": list(dict.fromkeys(destinations)),
        "opening": (
            state.compiled_story.opening.model_dump(mode="json") if state.compiled_story.opening is not None else None
        ),
    }


def _story_for(genre: str):
    try:
        return load_compiled_story_fixture(genre)
    except CompilationError as exc:
        raise HTTPException(status_code=422, detail=exc.message) from exc


def create_demo_app(
    save_db_path: str | Path | None = None,
    *,
    artifact_root: str | Path | None = None,
    model: TurnModel | None = None,
    channel: str | None = None,
    cors_allow_origins: tuple[str, ...] | None = None,
) -> FastAPI:
    """Build the one public product surface over `RuntimeState` snapshots."""
    resolved_channel = channel or getenv("FREYTAG_DEPLOYMENT_CHANNEL", "unknown").strip() or "unknown"
    namespace = f"runtime-v2:{resolved_channel}"
    store = RuntimeStateSqliteStore(
        save_db_path or Path("runs/storygame_runtime_v2.sqlite"), namespace=namespace, check_same_thread=False
    )
    active_model = _default_model() if model is None else model
    sessions: dict[str, _Session] = {}
    app = FastAPI(title="Freytag Forge", version="2")
    app.add_middleware(
        CORSMiddleware,
        allow_origins=list(cors_allow_origins or ("https://bcorfman.github.io",)),
        allow_methods=["*"],
        allow_headers=["*"],
    )

    @app.get("/api/v1/health")
    def health() -> dict[str, str]:
        return {
            "status": "ok",
            "channel": resolved_channel,
            "sha": (
                getenv("FREYTAG_DEPLOYMENT_SHA", "").strip()
                or getenv("RAILWAY_GIT_COMMIT_SHA", "").strip()
                or "unknown"
            ),
        }

    @app.post("/api/v1/session")
    def create_session(payload: SessionCreateRequest) -> dict[str, object]:
        story = _story_for(payload.genre)
        session_id = uuid4().hex
        state = bootstrap_runtime_state(story)
        store.save(session_id, state)
        if artifact_root is not None:
            write_artifacts(Path(artifact_root) / session_id, state)
        sessions[session_id] = _Session(RuntimeEngine(state, active_model))
        return {"session_id": session_id, "state": _state_payload(state)}

    @app.post("/api/v1/session/load")
    def load_session(payload: SessionLoadRequest) -> dict[str, object]:
        story = _story_for(payload.genre)
        try:
            state = store.load(payload.session_id, story)
        except RuntimeSaveError as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc
        sessions[payload.session_id] = _Session(RuntimeEngine(state, active_model))
        return {"session_id": payload.session_id, "state": _state_payload(state)}

    @app.post("/api/v1/turn")
    def submit_turn(payload: TurnRequest) -> dict[str, object]:
        session = sessions.get(payload.session_id)
        if session is None:
            story = _story_for(payload.genre)
            try:
                state = store.load(payload.session_id, story)
            except RuntimeSaveError as exc:
                raise HTTPException(
                    status_code=404, detail="Unknown session. Start or load a V2 session first."
                ) from exc
            session = _Session(RuntimeEngine(state, active_model))
            sessions[payload.session_id] = session
        result = session.engine.turn(payload.command)
        if not result.ok:
            detail = result.error.message if result.error is not None else "V2 runtime failed."
            return JSONResponse(
                status_code=503,
                content={"status": "runtime_failure", "detail": detail},
                headers={"X-Runtime-Error": result.error.code if result.error else "RUNTIME_FAILURE"},
            )
        store.save(payload.session_id, session.engine.state)
        if artifact_root is not None:
            write_artifacts(Path(artifact_root) / payload.session_id, session.engine.state)
        return {
            "status": "ok",
            "lines": [result.narration],
            "state": _state_payload(session.engine.state),
            "model_calls": result.model_calls,
        }

    @app.on_event("shutdown")
    def close_store() -> None:
        store.close()

    return app


app = create_demo_app()
