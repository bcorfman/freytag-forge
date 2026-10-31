"""FastAPI product surface for the validated Markdown scene runtime."""

from __future__ import annotations

import hmac
import logging
from collections import deque
from collections.abc import Callable
from os import getenv
from pathlib import Path
from threading import Lock
from time import monotonic
from uuid import uuid4

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel, ConfigDict, Field, model_validator

from storygame.runtime.capture import WorldCapture, build_capture_provider
from storygame.runtime.cloudflare import CloudflareTurnProvider, NarrationProviderError
from storygame.runtime.contracts import ResolvedTurnProposal, RuntimeContractError, contract_error_summary
from storygame.runtime.engine import ClarificationTurn, RuntimeEngine
from storygame.runtime.item_facts import ItemFactsProvider
from storygame.runtime.jev import JevClient
from storygame.runtime.knowledge_audit import build_knowledge_audit
from storygame.runtime.observation_verifier import ObservationVerifier
from storygame.runtime.persistence import RuntimeSaveError, RuntimeStateSqliteStore
from storygame.runtime.scripted_provider import ScriptedTurnProvider
from storygame.runtime.state import RuntimeState, RuntimeStateError
from storygame.runtime.validation import REJECTED_TURN_MESSAGE, ProposalValidationError, rejection_message
from storygame.runtime.world_model import display_name, world_for
from storygame.story_package.loader import StoryPackageError, load_story_package

logger = logging.getLogger(__name__)
OBSERVATION_ENFORCE_ENV = "FREYTAG_OBSERVATION_ENFORCE"
OBSERVATION_SCENE_STATE_ENV = "FREYTAG_OBSERVATION_SCENE_STATE"
OPENING_CHECK_ENV = "FREYTAG_OPENING_CHECK"


class _Request(BaseModel):
    model_config = ConfigDict(extra="forbid")


class SessionRequest(_Request):
    story_id: str = Field(min_length=1)


class TurnRequest(_Request):
    session_id: str = Field(min_length=1)
    player_input: str | None = Field(default=None, min_length=1, max_length=12000)
    command: str | None = Field(default=None, min_length=1, max_length=12000)
    clarifies: str | None = Field(default=None, min_length=1, max_length=12000)
    clarification_round: int = Field(default=0, ge=0, le=2)
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
    world = world_for(state.package, state.facts)
    scene = next(scene for scene in state.package.scenes if scene.metadata.scene_id == state.current_scene_id)
    protagonist_id = state.package.world.protagonist_id
    things = {}
    for entity_id in world.entity_ids():
        holder_id = world.holder(entity_id)
        if entity_id not in scene.metadata.item_ids and holder_id != protagonist_id:
            continue
        if world.is_hidden(entity_id):
            continue
        parent_id = world.parent(entity_id)
        things[display_name(state.package, state.facts, world, entity_id)] = {
            "place": display_name(state.package, state.facts, world, parent_id) if parent_id else None,
            "held_by": display_name(state.package, state.facts, world, holder_id) if holder_id else None,
        }
    summary = {
        "story_id": state.package.story_id,
        "scene_id": state.current_scene_id,
        "phase": state.phase,
        "pending_game_break": state.has_pending_break,
        "story_complete": state.story_complete,
        "fired_storylet_ids": sorted(event_id for event_id in state.fired_event_ids if event_id.startswith("SL-")),
        "fired_pacing_event_ids": sorted(
            event.id for event in state.package.pacing.events if event.id in state.fired_event_ids
        ),
        "story_elapsed_seconds": int(elapsed[-1].value) if elapsed and elapsed[-1].value else 0,
        "turn_index": state.turn_index,
        "turns_since_scene_entry": state.turn_index - state.scene_entered_at_turn,
        "things": dict(sorted(things.items())),
    }
    if state.story_complete and state.package.pacing.ending is not None:
        summary["ending_marker"] = state.package.pacing.ending.marker
    return summary


def _turn_payload(
    state: RuntimeState,
    proposal: ResolvedTurnProposal | str,
    game_break: object | None = None,
    prompt: dict[str, str] | None = None,
) -> dict[str, object]:
    """Keep structured segments primary while retaining migration-era lines."""
    if game_break is not None:
        # The candidate is validated but not canon until the player chooses to
        # proceed. Never put its prose in the warning response.
        narration = ""
        segments: list[dict[str, object]] = []
    elif isinstance(proposal, str):
        narration = proposal
        segments = [{"kind": "narration", "text": narration}]
    else:
        narration = proposal.narration
        segments = [item.model_dump(mode="json") for item in proposal.segments] or [
            {"kind": "narration", "text": narration}
        ]
    delivery = state.last_turn_delivery.model_dump(mode="json")
    if not any(delivery[key] for key in ("capture_steps", "capture_issues", "capture_unplaced")):
        for key in ("capture_steps", "capture_issues", "capture_unplaced"):
            delivery.pop(key, None)
    payload = {
        "segments": segments,
        "lines": [narration] if narration else [],
        "game_break": game_break,
        "delivery": delivery,
        "state": _state_summary(state),
        "story_complete": state.story_complete,
    }
    if state.story_complete and state.package.pacing.ending is not None:
        payload["ending_marker"] = state.package.pacing.ending.marker
    if prompt is not None:
        payload["prompt"] = prompt
    return payload


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


def _test_clock_token_matches(supplied_secret: str) -> bool:
    configured_secret = getenv("FREYTAG_TEST_CLOCK_TOKEN", "")
    if getenv("FREYTAG_ALLOW_TEST_CLOCK", "") != "1" or not configured_secret:
        return False
    return hmac.compare_digest(supplied_secret.encode("utf-8"), configured_secret.encode("utf-8"))


def _client_ip(request: Request) -> str:
    if getenv("FREYTAG_TRUST_PROXY_HEADER", "") == "1":
        forwarded = request.headers.get("X-Forwarded-For")
        if forwarded is not None:
            return forwarded.rsplit(",", 1)[-1].strip()
    return request.client.host if request.client else "unknown"


def create_demo_app(
    *,
    channel: str | None = None,
    package_roots: tuple[Path, ...] | None = None,
    store_path: Path | None = None,
    provider_factory: Callable[[RuntimeState], Callable[[str], object]] | None = None,
    clock: Callable[[], float] | None = None,
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
    turn_rate_limit = int(getenv("FREYTAG_RATE_LIMIT_PER_MINUTE", "10"))
    session_rate_limit = int(getenv("FREYTAG_SESSIONS_PER_IP_PER_DAY", "20"))
    turn_times: dict[str, deque[float]] = {}
    session_times: dict[str, deque[float]] = {}
    request_times_lock = Lock()
    now = clock or monotonic
    app = FastAPI(title="Freytag Forge", version="3")
    allowed_headers = ["Content-Type", "Authorization"]
    allowed_headers.append("X-Freytag-Test-Clock-Token")
    if getenv("FREYTAG_ALLOW_TEST_CLOCK", "") == "1":
        allowed_headers.append("X-Freytag-Test-Clock-Seconds")

    @app.middleware("http")
    async def handle_unexpected_errors(request: Request, call_next):
        try:
            return await call_next(request)
        except Exception:
            logging.getLogger(__name__).exception("Unhandled exception while serving %s", request.url.path)
            return JSONResponse({"detail": "internal server error"}, status_code=500)

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
        if getenv("FREYTAG_TURN_PROVIDER", "") == "scripted":
            if resolved_channel == "production":
                raise NarrationProviderError("narration service is unavailable", 503, "SCRIPTED_PROVIDER_FORBIDDEN")
            return ScriptedTurnProvider.from_environment(state)
        if getenv("FREYTAG_WORLD_CAPTURE", "") == "1":
            return build_capture_provider(state)
        return CloudflareTurnProvider.from_environment(state)

    def engine_for(state: RuntimeState, provider=None) -> RuntimeEngine:
        provider = provider if provider is not None else provider_for(state)
        capture = None
        if getenv("FREYTAG_WORLD_CAPTURE", "") == "1" and getenv("FREYTAG_TURN_PROVIDER", "") != "scripted":
            capture_provider = provider if isinstance(provider, ItemFactsProvider) else build_capture_provider(state)
            capture_ask = JevClient.from_environment().ask
            provider.semantic_ask = capture_ask
            capture_provider.semantic_ask = capture_ask
            enabled = getenv("FREYTAG_FIXED_REFUSAL", "") != "0"
            capture = WorldCapture(capture_provider, capture_ask, fixed_refusal=enabled, engine_refusal=enabled)
            if getenv(OBSERVATION_ENFORCE_ENV, "") == "1":
                capture.enforcing_verifier = ObservationVerifier(
                    capture_ask,
                    scene_state=getenv(OBSERVATION_SCENE_STATE_ENV, "") == "1",
                    opening_check=getenv(OPENING_CHECK_ENV, "") == "1",
                )
        return RuntimeEngine(state, provider, capture=capture)

    def require_turn_rate_limit(body: TurnRequest, request: Request) -> None:
        if turn_rate_limit <= 0 or _test_clock_token_matches(request.headers.get("X-Freytag-Test-Clock-Token", "")):
            return
        current = now()
        with request_times_lock:
            times = turn_times.setdefault(body.session_id, deque())
            while times and times[0] <= current - 60:
                times.popleft()
            if len(times) >= turn_rate_limit:
                raise HTTPException(status_code=429, detail="rate limit exceeded")
            times.append(current)

    def require_session_rate_limit(request: Request) -> None:
        if session_rate_limit <= 0 or _test_clock_token_matches(request.headers.get("X-Freytag-Test-Clock-Token", "")):
            return
        current = now()
        client = _client_ip(request)
        with request_times_lock:
            times = session_times.setdefault(client, deque())
            while times and times[0] <= current - 86400:
                times.popleft()
            if len(times) >= session_rate_limit:
                raise HTTPException(status_code=429, detail="rate limit exceeded")
            times.append(current)

    @app.get("/api/v1/health")
    def health() -> dict[str, str]:
        return {"status": "ok", "runtime": "scene-v1", "channel": resolved_channel, "sha": _deployment_sha()}

    @app.get("/api/v1/version")
    def version() -> dict[str, str]:
        return {"api": "v1", "runtime": "scene-v1", "channel": resolved_channel, "sha": _deployment_sha()}

    @app.post("/api/v1/session")
    def create_session(body: SessionRequest, request: Request) -> dict[str, object]:
        require_session_rate_limit(request)
        package = packages.get(body.story_id)
        if package is None:
            raise HTTPException(status_code=404, detail="story does not exist")
        state = RuntimeState.bootstrap(package)
        try:
            provider = provider_for(state)
            opening = engine_for(state, provider).opening()
        except NarrationProviderError as error:
            raise _narration_http_error(error) from error
        except RuntimeContractError as error:
            raise HTTPException(status_code=422, detail=_contract_error_detail(error)) from error
        except ProposalValidationError as error:
            headers = {"X-Freytag-Rejection-Code": error.code} if error.code else {}
            raise HTTPException(status_code=409, detail=str(error), headers=headers) from error
        session_id = uuid4().hex
        store.save(session_id, state)
        scene = package.scenes[0].metadata
        payload = {
            "session_id": session_id,
            "state": _state_summary(state),
            "opening": {
                "scene_id": scene.scene_id,
                "phase": scene.freytag_phase,
                "text": opening.narration,
                "segments": [item.model_dump(mode="json") for item in opening.segments],
            },
        }
        if getenv("FREYTAG_EXPOSE_PROMPT", "") == "1":
            prompt = getattr(provider, "last_prompt", None)
            if prompt is not None:
                payload["prompt"] = prompt
        return payload

    @app.post("/api/v1/turn")
    def turn(body: TurnRequest, request: Request) -> dict[str, object]:
        state = load_state(body.session_id)
        require_turn_rate_limit(body, request)
        fact_keys_before = {
            fact.predicate
            for fact in state.facts.asserted
            if not fact.predicate.startswith("wk_") and fact.predicate != "world_effects_applied"
        }
        engine: RuntimeEngine | None = None
        try:
            provider = None if state.story_complete else provider_for(state)
            test_clock = _test_clock_seconds(body, request)
            engine = RuntimeEngine(state, lambda _command: {}) if provider is None else engine_for(state, provider)
            clarification_args = (
                {"clarifies": body.clarifies, "clarification_round": body.clarification_round}
                if body.clarifies is not None
                else {}
            )
            proposal = engine.turn(body.input_text, clock_seconds=test_clock, **clarification_args)
        except NarrationProviderError as error:
            http_error = _narration_http_error(error)
            if getenv("FREYTAG_EXPOSE_PROMPT", "") == "1":
                return JSONResponse(
                    status_code=http_error.status_code,
                    content={
                        "detail": http_error.detail,
                        "attempt_bundle": engine.last_attempt.model_dump(mode="json"),
                    },
                    headers=http_error.headers,
                )
            raise http_error from error
        except RuntimeContractError as error:
            raw_detail = _contract_error_detail(error)
            logger.warning("turn rejected [runtime_contract_error]: %s", str(error))
            if getenv("FREYTAG_EXPOSE_PROMPT", "") == "1":
                return JSONResponse(
                    status_code=422,
                    content={
                        "detail": raw_detail,
                        "attempt_bundle": engine.last_attempt.model_dump(mode="json"),
                    },
                )
            # Keep engine diagnostics in server logs; the player only needs a safe recovery line.
            raise HTTPException(status_code=422, detail=REJECTED_TURN_MESSAGE) from error
        except ProposalValidationError as error:
            headers = {"X-Freytag-Rejection-Code": error.code} if error.code else {}
            raw_detail = str(error)
            logger.warning("turn rejected [%s]: %s", error.code or "unknown", raw_detail)
            if getenv("FREYTAG_EXPOSE_PROMPT", "") == "1":
                return JSONResponse(
                    status_code=409,
                    content={
                        "detail": raw_detail,
                        "attempt_bundle": engine.last_attempt.model_dump(mode="json"),
                    },
                    headers=headers,
                )
            raise HTTPException(
                status_code=409,
                detail=rejection_message(error.code, error.term, body.input_text),
                headers=headers,
            ) from error
        except RuntimeStateError as error:
            raw_detail = str(error)
            logger.warning("turn rejected [runtime_state_error]: %s", raw_detail)
            if getenv("FREYTAG_EXPOSE_PROMPT", "") == "1":
                return JSONResponse(
                    status_code=409,
                    content={
                        "detail": raw_detail,
                        "attempt_bundle": (
                            engine.last_attempt.model_dump(mode="json")
                            if engine is not None and engine.last_attempt is not None
                            else None
                        ),
                    },
                )
            raise HTTPException(status_code=409, detail=REJECTED_TURN_MESSAGE) from error
        except HTTPException:
            raise
        except Exception as error:
            logger.exception("Unhandled engine error during turn: %s", error)
            if getenv("FREYTAG_EXPOSE_PROMPT", "") == "1":
                return JSONResponse(
                    status_code=500,
                    content={
                        "detail": str(error),
                        "attempt_bundle": (
                            engine.last_attempt.model_dump(mode="json")
                            if engine is not None and engine.last_attempt is not None
                            else None
                        ),
                    },
                )
            raise HTTPException(status_code=500, detail=REJECTED_TURN_MESSAGE) from error
        if isinstance(proposal, ClarificationTurn):
            payload = _turn_payload(state, proposal)
            payload["clarification"] = {
                "original_command": proposal.clarification.original_command,
                "noun": proposal.clarification.noun,
                "options": [{"id": entity_id, "name": name} for entity_id, name in proposal.clarification.options],
                "round": proposal.clarification.round,
            }
            return payload
        store.save(body.session_id, state)
        warning = proposal.game_break.model_dump(mode="json") if proposal.game_break else None
        expose_prompt = getenv("FREYTAG_EXPOSE_PROMPT", "") == "1"
        prompt = getattr(provider, "last_prompt", None) if expose_prompt else None
        payload = _turn_payload(state, proposal, warning, prompt)
        if expose_prompt:
            payload["attempt_bundle"] = engine.last_attempt.model_dump(mode="json") if engine.last_attempt else None
        if prompt is not None:
            semantic_match = getattr(provider, "last_semantic_match", None)
            if semantic_match is not None:
                payload["semantic_match"] = semantic_match
        if getenv("FREYTAG_EXPOSE_KNOWLEDGE_AUDIT", "") == "1":
            payload["knowledge_audit"] = build_knowledge_audit(engine, proposal, fact_keys_before)
        return payload

    @app.post("/api/v1/game-break")
    def resolve_game_break(body: BreakResolutionRequest) -> dict[str, object]:
        state = load_state(body.session_id)
        if not state.pending_break or state.pending_break.warning_id != body.warning_id:
            raise HTTPException(status_code=409, detail="game-break warning does not match this session")
        try:
            resolved = engine_for(state).resolve_break(body.decision)
        except RuntimeStateError as error:
            raise HTTPException(status_code=409, detail=str(error)) from error
        store.save(body.session_id, state)
        if body.decision == "proceed" and resolved is not None:
            return _turn_payload(state, resolved)
        return _turn_payload(state, "You return to the scene before that consequence.")

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
    supplied_secret = body.test_clock_token
    if supplied_secret is None:
        supplied_secret = request.headers.get("X-Freytag-Test-Clock-Token")
    if supplied_secret is None:
        supplied_secret = ""
    if not getenv("FREYTAG_TEST_CLOCK_TOKEN", ""):
        raise HTTPException(status_code=503, detail="test clock is enabled but no shared secret is configured")
    if not _test_clock_token_matches(supplied_secret):
        raise HTTPException(status_code=403, detail="test clock token is invalid")
    try:
        seconds = int(value)
    except ValueError as error:
        raise HTTPException(status_code=422, detail="test clock must be an integer number of seconds") from error
    if not 0 <= seconds <= 3600:
        raise HTTPException(status_code=422, detail="test clock must be between 0 and 3600 seconds")
    return seconds


app = create_demo_app()
