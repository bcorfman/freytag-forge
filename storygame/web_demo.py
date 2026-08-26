"""FastAPI product surface for the validated Markdown scene runtime."""

from __future__ import annotations

from collections import deque
from collections.abc import Callable
from os import getenv
from pathlib import Path
from threading import Lock
from time import monotonic
from uuid import uuid4

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, ConfigDict, Field, model_validator

from storygame.runtime.cloudflare import CloudflareTurnProvider, NarrationProviderError
from storygame.runtime.context import SceneContextBuilder
from storygame.runtime.engine import RuntimeEngine
from storygame.runtime.persistence import RuntimeSaveError, RuntimeStateSqliteStore
from storygame.runtime.state import RuntimeState, RuntimeStateError
from storygame.story_package.loader import StoryPackageError, load_story_package


class _Request(BaseModel):
    model_config = ConfigDict(extra="forbid")


class SessionRequest(_Request):
    story_id: str = Field(min_length=1)


class TurnRequest(_Request):
    session_id: str = Field(min_length=1)
    player_input: str | None = Field(default=None, min_length=1, max_length=12000)
    command: str | None = Field(default=None, min_length=1, max_length=12000)

    @model_validator(mode="after")
    def has_one_player_input(self) -> TurnRequest:
        if self.player_input is None and self.command is None:
            raise ValueError("player_input or command is required")
        if self.player_input is not None and self.command is not None:
            raise ValueError("provide only player_input or command")
        return self

    @property
    def input_text(self) -> str:
        return self.player_input or self.command or ""


class BreakResolutionRequest(_Request):
    session_id: str = Field(min_length=1)
    warning_id: str = Field(min_length=1)
    decision: str = Field(pattern="^(proceed|return_to_scene)$")


def _deployment_sha() -> str:
    """Return the immutable deploy identity supplied by Railway or CI."""
    return getenv("FREYTAG_DEPLOYMENT_SHA", "").strip() or getenv("RAILWAY_GIT_COMMIT_SHA", "").strip() or "unknown"


def _default_package_root() -> Path:
    return Path(__file__).resolve().parents[1] / "data" / "stories" / "continuity-initiative"


def _state_summary(state: RuntimeState) -> dict[str, object]:
    elapsed = state.facts.matching("story_elapsed_seconds", "story")
    return {
        "story_id": state.package.story_id,
        "scene_id": state.current_scene_id,
        "phase": state.phase,
        "pending_game_break": state.has_pending_break,
        "fired_storylet_ids": sorted(event_id for event_id in state.fired_event_ids if event_id.startswith("SL-")),
        "story_elapsed_seconds": int(elapsed[-1].value) if elapsed and elapsed[-1].value else 0,
    }


def _turn_payload(state: RuntimeState, narration: str, game_break: object | None = None) -> dict[str, object]:
    """Keep structured segments primary while retaining migration-era lines."""
    return {
        "segments": [{"kind": "narration", "text": narration}],
        "lines": [narration],
        "game_break": game_break,
        "state": _state_summary(state),
    }


def create_demo_app(
    *,
    channel: str | None = None,
    package_roots: tuple[Path, ...] | None = None,
    store_path: Path | None = None,
    provider_factory: Callable[[RuntimeState], Callable[[str], object]] | None = None,
) -> FastAPI:
    """Build the single hosted surface without introducing gameplay policy."""
    resolved_channel = channel or getenv("FREYTAG_DEPLOYMENT_CHANNEL", "unknown").strip() or "unknown"
    roots = package_roots or (_default_package_root(),)
    try:
        packages = {package.story_id: package for package in (load_story_package(root) for root in roots)}
    except StoryPackageError as error:
        raise RuntimeError("configured story packages are invalid") from error
    if not packages:
        raise RuntimeError("at least one story package is required")
    store = RuntimeStateSqliteStore(store_path or Path(getenv("FREYTAG_SESSION_DB", "/tmp/freytag-forge.sqlite")))
    context_builder = SceneContextBuilder()
    rate_limit = int(getenv("FREYTAG_RATE_LIMIT_PER_MINUTE", "60"))
    request_times: dict[str, deque[float]] = {}
    request_times_lock = Lock()
    app = FastAPI(title="Freytag Forge", version="3")
    app.add_middleware(
        CORSMiddleware,
        allow_origins=[item for item in getenv("FREYTAG_CORS_ORIGINS", "*").split(",") if item],
        allow_credentials=False,
        allow_methods=["GET", "POST"],
        allow_headers=["Content-Type", "Authorization"],
    )

    def load_state(session_id: str) -> RuntimeState:
        for package in packages.values():
            try:
                return store.load(session_id, package)
            except RuntimeSaveError:
                continue
        raise HTTPException(status_code=404, detail="session does not exist")

    def provider_for(state: RuntimeState) -> Callable[[str], object]:
        if provider_factory:
            return provider_factory(state)
        return CloudflareTurnProvider.from_environment(context_builder, state)

    def require_rate_limit(request: Request) -> None:
        if rate_limit <= 0:
            return
        client = request.client.host if request.client else "unknown"
        now = monotonic()
        with request_times_lock:
            times = request_times.setdefault(client, deque())
            while times and times[0] <= now - 60:
                times.popleft()
            if len(times) >= rate_limit:
                raise HTTPException(status_code=429, detail="rate limit exceeded")
            times.append(now)

    @app.get("/api/v1/health")
    def health() -> dict[str, str]:
        return {"status": "ok", "runtime": "scene-v1", "channel": resolved_channel, "sha": _deployment_sha()}

    @app.get("/api/v1/version")
    def version() -> dict[str, str]:
        return {"api": "v1", "runtime": "scene-v1", "channel": resolved_channel, "sha": _deployment_sha()}

    @app.post("/api/v1/session")
    def create_session(body: SessionRequest) -> dict[str, object]:
        package = packages.get(body.story_id)
        if package is None:
            raise HTTPException(status_code=404, detail="story does not exist")
        session_id = uuid4().hex
        state = RuntimeState.bootstrap(package)
        store.save(session_id, state)
        scene = package.scenes[0].metadata
        return {
            "session_id": session_id,
            "state": _state_summary(state),
            "opening": {"scene_id": scene.scene_id, "phase": scene.freytag_phase, "text": scene.entry_text},
        }

    @app.post("/api/v1/turn")
    def turn(body: TurnRequest, request: Request) -> dict[str, object]:
        require_rate_limit(request)
        state = load_state(body.session_id)
        try:
            proposal = RuntimeEngine(state, provider_for(state)).turn(body.input_text)
        except NarrationProviderError as error:
            headers = {"X-Narration-Error-Code": error.error_code} if error.error_code else {}
            if error.trace_id:
                headers["X-Trace-ID"] = error.trace_id
            if error.worker_revision:
                headers["X-Worker-Revision"] = error.worker_revision
            raise HTTPException(status_code=error.status_code, detail=error.message, headers=headers) from error
        except RuntimeStateError as error:
            raise HTTPException(status_code=409, detail=str(error)) from error
        store.save(body.session_id, state)
        warning = proposal.game_break.model_dump(mode="json") if proposal.game_break else None
        return _turn_payload(state, proposal.narration, warning)

    @app.post("/api/v1/game-break")
    def resolve_game_break(body: BreakResolutionRequest) -> dict[str, object]:
        state = load_state(body.session_id)
        if not state.pending_break or state.pending_break.warning_id != body.warning_id:
            raise HTTPException(status_code=409, detail="game-break warning does not match this session")
        try:
            RuntimeEngine(state, provider_for(state)).resolve_break(body.decision)
        except RuntimeStateError as error:
            raise HTTPException(status_code=409, detail=str(error)) from error
        store.save(body.session_id, state)
        narration = "You proceed."
        if body.decision == "return_to_scene":
            narration = "You return to the scene before that consequence."
        return _turn_payload(state, narration)

    return app


app = create_demo_app()
