"""The hosted-only HTTP adapter for the V2 runtime."""

from __future__ import annotations

import logging
from collections.abc import Callable
from datetime import UTC, datetime, timedelta
from os import getenv
from pathlib import Path
from typing import Literal
from uuid import uuid4

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel

from storygame.authoring.compiler import load_compiled_story_fixture
from storygame.persistence.runtime_state_sqlite import RuntimeSaveError, RuntimeStateSqliteStore
from storygame.runtime.cloudflare import CloudflareTurnModel
from storygame.runtime.context import RuntimeContext
from storygame.runtime.engine import RuntimeEngine, TurnModel
from storygame.runtime.state import RuntimeState, bootstrap_runtime_state

_LOGGER = logging.getLogger(__name__)


class _UnavailableTurnModel:
    def play_turn(self, context: RuntimeContext, *, json_object: bool) -> object:
        raise RuntimeError("No hosted V2 turn-model adapter is configured.")


class _DemoSession:
    def __init__(self, engine: RuntimeEngine, expires_at: datetime) -> None:
        self.engine = engine
        self.expires_at = expires_at
        self.turns_used = 0


class SessionCreateRequest(BaseModel):
    genre: Literal["mystery", "fantasy", "sci-fi", "relationship", "romance"] = "mystery"


class SessionCreateResponse(BaseModel):
    session_id: str
    compiled_story_id: str
    expires_at: str


class TurnRequest(BaseModel):
    session_id: str
    command: str


class StateSnapshot(BaseModel):
    location: str
    turn_index: int
    active_beats: list[str]


class TurnResponse(BaseModel):
    status: Literal["ok"] = "ok"
    session_id: str
    lines: list[str]
    state: StateSnapshot
    model_calls: int = 0


class HealthResponse(BaseModel):
    status: Literal["ok"] = "ok"
    channel: str
    sha: str


class ErrorResponse(BaseModel):
    status: Literal["rate_limited", "quota_exhausted", "service_unavailable", "unsupported_save_version", "error"]
    detail: str


def create_demo_app(
    save_db_path: str | Path | None = None,
    *,
    turn_model: TurnModel | None = None,
    session_ttl_seconds: int = 30 * 60,
    session_turn_cap: int = 30,
    ip_rate_limit_per_min: int = 20,
    ip_daily_turn_cap: int = 300,
    cors_allow_origins: tuple[str, ...] | None = None,
    now_fn: Callable[[], datetime] | None = None,
    channel: str | None = None,
    session_namespace: str | None = None,
    evaluation_token: str | None = None,
) -> FastAPI:
    """Build the only supported application surface from explicit V2 dependencies."""
    resolved_channel = channel or getenv("FREYTAG_DEPLOYMENT_CHANNEL", "development").strip() or "development"
    namespace = session_namespace or getenv("FREYTAG_SESSION_NAMESPACE", resolved_channel).strip()
    if not namespace:
        raise ValueError("FREYTAG_SESSION_NAMESPACE must identify the deployment channel")
    app = FastAPI(title="Freytag Forge Demo API", version="2.0.0")
    now = now_fn or (lambda: datetime.now(UTC))
    store = RuntimeStateSqliteStore(
        save_db_path or Path("runs/storygame_runtime_v2.sqlite"), namespace=namespace, check_same_thread=False
    )
    sessions: dict[str, _DemoSession] = {}
    ip_window_hits: dict[str, list[datetime]] = {}
    ip_daily_hits: dict[tuple[str, str], int] = {}
    model = turn_model or _configured_turn_model()
    configured_evaluation_token = evaluation_token or getenv("FREYTAG_STAGING_EVALUATION_TOKEN", "").strip()
    origins = cors_allow_origins or _resolve_cors_origins()
    app.add_middleware(
        CORSMiddleware,
        allow_origins=list(origins),
        allow_methods=["*"],
        allow_headers=["*"],
        expose_headers=["X-Request-ID"],
    )

    @app.middleware("http")
    async def attach_request_id(request: Request, call_next):
        response = await call_next(request)
        response.headers.setdefault("X-Request-ID", request.headers.get("X-Request-ID", uuid4().hex))
        return response

    def response_state(state: RuntimeState) -> StateSnapshot:
        return StateSnapshot(
            location=state.world.location,
            turn_index=state.turn_index,
            active_beats=[beat.id for beat in state.active_beats],
        )

    def error(status_code: int, status: str, detail: str, request_id: str = "") -> JSONResponse:
        headers = {"X-Request-ID": request_id} if request_id else None
        return JSONResponse(status_code=status_code, content={"status": status, "detail": detail}, headers=headers)

    def session_for(session_id: str) -> _DemoSession:
        session = sessions.get(session_id)
        if session is None or session.expires_at <= now():
            sessions.pop(session_id, None)
            raise HTTPException(404, f"Unknown or expired session_id '{session_id}'.")
        return session

    def within_limits(ip: str, at: datetime) -> str | None:
        window = [hit for hit in ip_window_hits.get(ip, []) if hit > at - timedelta(minutes=1)]
        if ip_rate_limit_per_min > 0 and len(window) >= ip_rate_limit_per_min:
            return "Rate limit exceeded for this IP. Please retry shortly."
        window.append(at)
        ip_window_hits[ip] = window
        daily_key = (ip, at.date().isoformat())
        if ip_daily_turn_cap > 0 and ip_daily_hits.get(daily_key, 0) >= ip_daily_turn_cap:
            return "Daily cap reached for this IP. Please retry tomorrow."
        ip_daily_hits[daily_key] = ip_daily_hits.get(daily_key, 0) + 1
        return None

    def is_staging_evaluation(request: Request) -> bool:
        return (
            resolved_channel == "staging"
            and bool(configured_evaluation_token)
            and request.headers.get("X-Freytag-Evaluation-Token") == configured_evaluation_token
        )

    @app.get("/api/v1/health", response_model=HealthResponse)
    @app.get("/api/v1/version", response_model=HealthResponse)
    def health() -> HealthResponse:
        return HealthResponse(
            channel=resolved_channel, sha=getenv("FREYTAG_DEPLOYMENT_SHA", "unknown").strip() or "unknown"
        )

    @app.post("/api/v1/session", response_model=SessionCreateResponse)
    def create_session(payload: SessionCreateRequest) -> SessionCreateResponse:
        fixture = "relationship" if payload.genre == "romance" else payload.genre
        story = load_compiled_story_fixture(fixture)
        session_id = uuid4().hex
        session = _DemoSession(
            RuntimeEngine(bootstrap_runtime_state(story), model), now() + timedelta(seconds=session_ttl_seconds)
        )
        sessions[session_id] = session
        store.save(session_id, session.engine.state)
        return SessionCreateResponse(
            session_id=session_id, compiled_story_id=story.id, expires_at=session.expires_at.isoformat()
        )

    @app.post("/api/v1/turn", response_model=TurnResponse | ErrorResponse)
    def turn(payload: TurnRequest, request: Request) -> TurnResponse | JSONResponse:
        request_id = uuid4().hex
        session = session_for(payload.session_id)
        limited = (
            None
            if is_staging_evaluation(request)
            else within_limits(request.client.host if request.client else "unknown", now())
        )
        if limited:
            return error(429, "rate_limited", limited, request_id)
        command = payload.command.strip()
        if command.lower() == "save":
            store.save(payload.session_id, session.engine.state)
            return TurnResponse(
                session_id=payload.session_id, lines=["Story saved."], state=response_state(session.engine.state)
            )
        if command.lower() == "load":
            try:
                session.engine.state = store.load(payload.session_id, session.engine.state.compiled_story)
            except RuntimeSaveError as exc:
                return error(409, exc.code, str(exc), request_id)
            return TurnResponse(
                session_id=payload.session_id, lines=["Story loaded."], state=response_state(session.engine.state)
            )
        if session_turn_cap > 0 and session.turns_used >= session_turn_cap:
            return error(429, "quota_exhausted", "Session turn cap reached for this demo session.", request_id)
        if session.engine.state.turn_index == 0 and command.lower() in {"look", "start"}:
            opening = _opening(session.engine.state)
            return TurnResponse(
                session_id=payload.session_id, lines=[opening], state=response_state(session.engine.state)
            )
        result = session.engine.turn(command)
        if not result.ok:
            detail = result.error.message if result.error else "The story service is unavailable."
            _LOGGER.warning(
                "V2 turn failed: request_id=%s session_id=%s detail=%s cause=%s",
                request_id,
                payload.session_id,
                detail,
                result.error.__cause__ if result.error else None,
            )
            return error(
                503,
                "service_unavailable",
                "The story service is temporarily unavailable. Please retry shortly.",
                request_id,
            )
        session.turns_used += 1
        session.expires_at = now() + timedelta(seconds=session_ttl_seconds)
        store.save(payload.session_id, session.engine.state)
        return TurnResponse(
            session_id=payload.session_id,
            lines=[result.narration],
            state=response_state(session.engine.state),
            model_calls=result.model_calls,
        )

    @app.on_event("shutdown")
    def close_store() -> None:
        store.close()

    return app


def _opening(state: RuntimeState) -> str:
    character = state.compiled_story.characters[0]
    return (
        f"{state.compiled_story.title}. You are {character.name}, {character.description} "
        f"{state.compiled_story.premise}"
    )


def _resolve_cors_origins() -> tuple[str, ...]:
    configured = getenv("DEMO_CORS_ALLOW_ORIGINS", "*")
    return tuple(value.strip() for value in configured.split(",") if value.strip()) or ("*",)


def _configured_turn_model() -> TurnModel:
    if not getenv("CLOUDFLARE_WORKER_URL", "").strip():
        return _UnavailableTurnModel()
    return CloudflareTurnModel()


app = create_demo_app()
