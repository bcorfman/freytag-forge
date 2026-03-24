from __future__ import annotations

import logging
from datetime import UTC, datetime, timedelta
from os import getenv
from pathlib import Path
from random import Random
from typing import Callable, Literal
from uuid import uuid4

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel

from storygame.cli import _build_narrator
from storygame.engine.freeform import LlmFreeformProposalAdapter
from storygame.engine.state import GameState
from storygame.engine.world import build_default_state
from storygame.llm.adapters import CloudflareWorkersAIAdapter, Narrator
from storygame.llm.output_editor import OutputEditor, build_output_editor
from storygame.llm.story_agents.agents import DefaultNarratorOpeningAgent
from storygame.llm.story_director import StoryDirector
from storygame.persistence.savegame_sqlite import SqliteSaveStore
from storygame.web_runtime import (
    ScopedSaveStore,
    bootstrap_failure_debug_payload,
    build_bootstrap_response_payload,
    build_turn_response_payload,
    execute_turn,
    is_bootstrap_command,
)

_LOGGER = logging.getLogger(__name__)
def _utc_now() -> datetime:
    return datetime.now(UTC)


class _DemoSession:
    def __init__(self, state: GameState, rng: Random, expires_at: datetime) -> None:
        self.state = state
        self.rng = rng
        self.expires_at = expires_at
        self.turns_used = 0

class SessionCreateRequest(BaseModel):
    seed: int | None = None
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


class SessionCreateResponse(BaseModel):
    session_id: str
    seed: int
    expires_at: str


class TurnRequest(BaseModel):
    session_id: str
    command: str
    debug: bool = False


class StateSnapshot(BaseModel):
    session_id: str
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
    status: Literal["ok"] = "ok"
    session_id: str
    command: str
    action_raw: str
    beat: str
    continued: bool
    lines: list[str]
    state: StateSnapshot


class HealthResponse(BaseModel):
    status: Literal["ok"] = "ok"


class ErrorResponse(BaseModel):
    status: Literal["rate_limited", "quota_exhausted", "service_unavailable", "error"]
    detail: str


def create_demo_app(
    save_db_path: str | Path | None = None,
    default_seed: int = 123,
    narrator_mode: str | None = None,
    narrator: Narrator | None = None,
    output_editor: OutputEditor | None = None,
    story_director: StoryDirector | None = None,
    session_ttl_seconds: int = 30 * 60,
    session_turn_cap: int = 30,
    ip_rate_limit_per_min: int = 20,
    ip_daily_turn_cap: int = 300,
    cors_allow_origins: tuple[str, ...] | None = None,
    now_fn: Callable[[], datetime] | None = None,
) -> FastAPI:
    app = FastAPI(title="Freytag Forge Demo API", version="0.1.0")
    now = _utc_now if now_fn is None else now_fn
    save_db = Path("runs/storygame_web_demo_saves.sqlite") if save_db_path is None else Path(save_db_path)
    store = SqliteSaveStore(save_db, check_same_thread=False)
    sessions: dict[str, _DemoSession] = {}
    ip_window_hits: dict[str, list[datetime]] = {}
    ip_daily_hits: dict[tuple[str, str], int] = {}

    resolved_narrator_mode = _resolve_narrator_mode(narrator_mode)
    active_narrator: Narrator = (
        _build_demo_narrator(resolved_narrator_mode)
        if narrator is None
        else narrator
    )
    active_output_editor = build_output_editor(resolved_narrator_mode) if output_editor is None else output_editor
    story_director_mode = "cloudflare" if getenv("CLOUDFLARE_WORKER_URL", "").strip() else resolved_narrator_mode
    active_freeform_adapter = LlmFreeformProposalAdapter(mode=story_director_mode)
    use_fast_story_director_opening = story_director is None
    allow_story_director_bootstrap = story_director_mode != "cloudflare"
    active_story_director = (
        StoryDirector(story_director_mode, active_output_editor) if story_director is None else story_director
    )
    active_narrator_opening_agent = DefaultNarratorOpeningAgent(story_director_mode)
    resolved_cors_allow_origins = _resolve_demo_cors_allow_origins(cors_allow_origins)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=list(resolved_cors_allow_origins),
        allow_methods=["*"],
        allow_headers=["*"],
    )

    def _expiry(now_at: datetime) -> datetime:
        return now_at + timedelta(seconds=session_ttl_seconds)

    def _touch(session: _DemoSession) -> None:
        session.expires_at = _expiry(now())

    def _error_response(status_code: int, status: str, detail: str) -> JSONResponse:
        return JSONResponse(
            status_code=status_code,
            content={"status": status, "detail": detail},
        )

    def _enforce_ip_limits(ip: str, current_time: datetime) -> JSONResponse | None:
        if ip_rate_limit_per_min > 0:
            threshold = current_time - timedelta(seconds=60)
            recent_hits = [value for value in ip_window_hits.get(ip, []) if value > threshold]
            if len(recent_hits) >= ip_rate_limit_per_min:
                return _error_response(
                    429,
                    "rate_limited",
                    "Rate limit exceeded for this IP. Please retry shortly.",
                )
            recent_hits.append(current_time)
            ip_window_hits[ip] = recent_hits

        if ip_daily_turn_cap > 0:
            day = current_time.date().isoformat()
            key = (ip, day)
            current_count = ip_daily_hits.get(key, 0)
            if current_count >= ip_daily_turn_cap:
                return _error_response(
                    429,
                    "rate_limited",
                    "Daily cap reached for this IP. Please retry tomorrow.",
                )
            ip_daily_hits[key] = current_count + 1
        return None

    def _narrator_fail_closed(lines: list[str]) -> JSONResponse | None:
        for line in lines:
            lowered = line.lower()
            if "ai_quota_exceeded" in lowered:
                _LOGGER.warning("Narrator quota exhausted: %s", line)
                return _error_response(
                    429,
                    "quota_exhausted",
                    "Narration quota exhausted for the hosted demo. Please retry later.",
                )
            if "[narrator failed:" in lowered:
                _LOGGER.warning("Narrator failed: %s", line)
                return _error_response(
                    503,
                    "service_unavailable",
                    "Narration service is temporarily unavailable.",
                )
        return None

    def _resolve_session(session_id: str) -> _DemoSession:
        session = sessions.get(session_id)
        if session is None:
            raise HTTPException(status_code=404, detail=f"Unknown or expired session_id '{session_id}'.")
        if session.expires_at <= now():
            sessions.pop(session_id, None)
            raise HTTPException(status_code=404, detail=f"Unknown or expired session_id '{session_id}'.")
        return session

    @app.get("/api/v1/health", response_model=HealthResponse)
    def health() -> HealthResponse:
        return HealthResponse()

    @app.post("/api/v1/session", response_model=SessionCreateResponse)
    def create_session(payload: SessionCreateRequest) -> SessionCreateResponse:
        session_seed = default_seed if payload.seed is None else payload.seed
        session_id = uuid4().hex
        created_at = now()
        session = _DemoSession(
            state=build_default_state(
                seed=session_seed,
                genre=payload.genre,
                session_length=payload.session_length,
                tone=payload.tone,
            ),
            rng=Random(session_seed),
            expires_at=_expiry(created_at),
        )
        sessions[session_id] = session
        return SessionCreateResponse(
            session_id=session_id,
            seed=session_seed,
            expires_at=session.expires_at.isoformat(),
        )

    @app.post("/api/v1/turn", response_model=TurnResponse | ErrorResponse)
    def submit_turn(payload: TurnRequest, request: Request) -> TurnResponse | JSONResponse:
        session = _resolve_session(payload.session_id)
        current_time = now()
        client_host = request.client.host if request.client is not None else "unknown"
        ip_limit_error = _enforce_ip_limits(client_host, current_time)
        if ip_limit_error is not None:
            return ip_limit_error
        if session_turn_cap > 0 and session.turns_used >= session_turn_cap:
            return _error_response(
                429,
                "quota_exhausted",
                "Session turn cap reached for this demo session.",
            )
        start_state = session.state
        bootstrap_only = session.turns_used == 0 and is_bootstrap_command(payload.command)
        if bootstrap_only:
            try:
                payload_body = build_bootstrap_response_payload(
                    start_state,
                    payload.command,
                    "session_id",
                    payload.session_id,
                    active_story_director,
                    active_narrator,
                    active_output_editor,
                    use_fast_story_director_opening=use_fast_story_director_opening,
                    allow_story_director_bootstrap=allow_story_director_bootstrap,
                    narrator_opening_agent=active_narrator_opening_agent,
                )
            except RuntimeError as exc:
                _LOGGER.warning(
                    "Bootstrap opening unavailable: %s | debug=%s",
                    str(exc),
                    bootstrap_failure_debug_payload(
                        start_state,
                        payload.command,
                        "session_id",
                        payload.session_id,
                    ),
                )
                return _error_response(
                    503,
                    "service_unavailable",
                    "Narration service is temporarily unavailable.",
                )
            payload_body["status"] = "ok"
            return TurnResponse.model_validate(payload_body)
        scoped_store = ScopedSaveStore(store, payload.session_id)
        result = execute_turn(
            session.state,
            payload.command,
            session.rng,
            active_narrator,
            active_freeform_adapter,
            narrator_mode=resolved_narrator_mode,
            debug=payload.debug,
            save_store=scoped_store,
            memory_slot=payload.session_id,
            output_editor=active_output_editor,
            story_director=active_story_director,
        )
        narrator_error = _narrator_fail_closed(result.lines)
        if narrator_error is not None:
            return narrator_error
        session.state = result.next_state
        session.turns_used += 1
        _touch(session)

        payload_body = build_turn_response_payload(
            result.next_state,
            payload.command,
            result.action_raw,
            result.beat,
            result.continued,
            result.lines,
            "session_id",
            payload.session_id,
        )
        payload_body["status"] = "ok"
        return TurnResponse.model_validate(payload_body)

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


def _resolve_demo_cors_allow_origins(configured_origins: tuple[str, ...] | None = None) -> tuple[str, ...]:
    if configured_origins is not None:
        cleaned = tuple(origin.strip() for origin in configured_origins if origin.strip())
        return cleaned or ("*",)

    raw = getenv("DEMO_CORS_ALLOW_ORIGINS", "").strip()
    if not raw:
        return ("*",)
    cleaned = tuple(origin.strip() for origin in raw.split(",") if origin.strip())
    return cleaned or ("*",)


def _build_demo_narrator(resolved_narrator_mode: str) -> Narrator:
    if getenv("CLOUDFLARE_WORKER_URL", "").strip():
        return CloudflareWorkersAIAdapter()
    return _build_narrator(resolved_narrator_mode)


app = create_demo_app()
