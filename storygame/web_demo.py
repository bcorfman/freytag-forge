"""FastAPI product surface for the validated Markdown scene runtime."""

from __future__ import annotations

import hmac
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
from storygame.runtime.contracts import ResolvedTurnProposal, RuntimeContractError, contract_error_summary
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
    test_clock_seconds: int | None = Field(default=None, ge=0, le=3600)
    test_clock_token: str | None = None

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
        "fired_pacing_event_ids": sorted(
            event.id for event in state.package.pacing.events if event.id in state.fired_event_ids
        ),
        "story_elapsed_seconds": int(elapsed[-1].value) if elapsed and elapsed[-1].value else 0,
        "turn_index": state.turn_index,
        "turns_since_scene_entry": state.turn_index - state.scene_entered_at_turn,
    }


def _turn_payload(
    state: RuntimeState, proposal: ResolvedTurnProposal | str, game_break: object | None = None
) -> dict[str, object]:
    """Keep structured segments primary while retaining migration-era lines."""
    if isinstance(proposal, str):
        narration = proposal
        segments = [{"kind": "narration", "text": narration}]
    else:
        narration = proposal.narration
        segments = [item.model_dump(mode="json") for item in proposal.segments] or [
            {"kind": "narration", "text": narration}
        ]
    return {
        "segments": segments,
        "lines": [narration],
        "game_break": game_break,
        "delivery": state.last_turn_delivery.model_dump(mode="json"),
        "state": _state_summary(state),
    }


def _narration_http_error(error: NarrationProviderError) -> HTTPException:
    """Surface the worker's safe diagnostic headers without leaking provider prose."""

    headers = {"X-Narration-Error-Code": error.error_code} if error.error_code else {}
    if error.trace_id:
        headers["X-Trace-ID"] = error.trace_id
    if error.worker_revision:
        headers["X-Worker-Revision"] = error.worker_revision
    return HTTPException(status_code=error.status_code, detail=error.message, headers=headers)


def _contract_error_detail(error: RuntimeContractError) -> str:
    """Expose only schema paths/types; never provider prose or rejected values."""
    summary = contract_error_summary(error)
    return f"provider response violates the turn contract ({summary})" if summary else str(error)


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
    rate_limit = int(getenv("FREYTAG_RATE_LIMIT_PER_MINUTE", "60"))
    request_times: dict[str, deque[float]] = {}
    request_times_lock = Lock()
    app = FastAPI(title="Freytag Forge", version="3")
    allowed_headers = ["Content-Type", "Authorization"]
    if getenv("FREYTAG_ALLOW_TEST_CLOCK", "") == "1":
        allowed_headers.append("X-Freytag-Test-Clock-Seconds")
        allowed_headers.append("X-Freytag-Test-Clock-Token")
    app.add_middleware(
        CORSMiddleware,
        allow_origins=[item for item in getenv("FREYTAG_CORS_ORIGINS", "*").split(",") if item],
        allow_credentials=False,
        allow_methods=["GET", "POST"],
        allow_headers=allowed_headers,
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
        return CloudflareTurnProvider.from_environment(state)

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
        state = RuntimeState.bootstrap(package)
        try:
            opening = RuntimeEngine(state, provider_for(state)).opening()
        except NarrationProviderError as error:
            raise _narration_http_error(error) from error
        except RuntimeContractError as error:
            raise HTTPException(status_code=422, detail=_contract_error_detail(error)) from error
        session_id = uuid4().hex
        store.save(session_id, state)
        scene = package.scenes[0].metadata
        return {
            "session_id": session_id,
            "state": _state_summary(state),
            "opening": {
                "scene_id": scene.scene_id,
                "phase": scene.freytag_phase,
                "text": opening.narration,
                "segments": [item.model_dump(mode="json") for item in opening.segments],
            },
        }

    @app.post("/api/v1/turn")
    def turn(body: TurnRequest, request: Request) -> dict[str, object]:
        require_rate_limit(request)
        state = load_state(body.session_id)
        try:
            test_clock = _test_clock_seconds(body, request)
            proposal = RuntimeEngine(state, provider_for(state)).turn(body.input_text, clock_seconds=test_clock)
        except NarrationProviderError as error:
            raise _narration_http_error(error) from error
        except RuntimeContractError as error:
            raise HTTPException(status_code=422, detail=_contract_error_detail(error)) from error
        except RuntimeStateError as error:
            raise HTTPException(status_code=409, detail=str(error)) from error
        store.save(body.session_id, state)
        warning = proposal.game_break.model_dump(mode="json") if proposal.game_break else None
        return _turn_payload(state, proposal, warning)

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


def _test_clock_seconds(body: TurnRequest, request: Request) -> int | None:
    """Allow deterministic pacing in a locally opted-in E2E server only."""

    if getenv("FREYTAG_ALLOW_TEST_CLOCK", "") != "1":
        return None
    value = body.test_clock_seconds
    if value is None:
        value = request.headers.get("X-Freytag-Test-Clock-Seconds")
    if value is None:
        return None
    configured_secret = getenv("FREYTAG_TEST_CLOCK_TOKEN", "")
    if not configured_secret:
        raise HTTPException(status_code=503, detail="test clock is enabled but no shared secret is configured")
    supplied_secret = body.test_clock_token
    if supplied_secret is None:
        supplied_secret = request.headers.get("X-Freytag-Test-Clock-Token")
    if supplied_secret is None:
        supplied_secret = ""
    if not hmac.compare_digest(supplied_secret.encode("utf-8"), configured_secret.encode("utf-8")):
        raise HTTPException(status_code=403, detail="test clock token is invalid")
    try:
        seconds = int(value)
    except ValueError as error:
        raise HTTPException(status_code=422, detail="test clock must be an integer number of seconds") from error
    if not 0 <= seconds <= 3600:
        raise HTTPException(status_code=422, detail="test clock must be between 0 and 3600 seconds")
    return seconds


app = create_demo_app()
