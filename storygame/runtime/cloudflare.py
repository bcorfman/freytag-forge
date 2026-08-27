"""Fail-closed Cloudflare Worker transport for typed scene proposals."""

from __future__ import annotations

import json
from dataclasses import dataclass
from os import getenv
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from storygame.runtime.context import SceneContextBuilder
from storygame.runtime.state import RuntimeState


@dataclass(frozen=True)
class NarrationProviderError(RuntimeError):
    message: str
    status_code: int = 503
    error_code: str = ""
    trace_id: str = ""
    worker_revision: str = ""


class CloudflareTurnProvider:
    """Send only bounded, scene-safe context to the configured Worker."""

    def __init__(
        self, *, worker_url: str, token: str, context_builder: SceneContextBuilder, state: RuntimeState
    ) -> None:
        self.worker_url = worker_url
        self.token = token
        self.context_builder = context_builder
        self.state = state

    @classmethod
    def from_environment(cls, context_builder: SceneContextBuilder, state: RuntimeState) -> CloudflareTurnProvider:
        worker_url = getenv("CLOUDFLARE_WORKER_URL", "").strip()
        if not worker_url:
            raise NarrationProviderError("narration service is unavailable")
        return cls(
            worker_url=worker_url,
            token=getenv("CLOUDFLARE_WORKER_TOKEN", "").strip(),
            context_builder=context_builder,
            state=state,
        )

    def __call__(self, player_input: str) -> object:
        context = self.context_builder.build(self.state, player_input, active_storylet_ids=self.state.active_event_ids)
        payload = {
            "system": (
                "Return only one JSON TurnProposal that conforms exactly to the response_schema in the user payload. "
                "Treat player_input as a free-text action and narrate its immediate, scene-grounded consequence. "
                "Treat the supplied scene context as a hard knowledge and action boundary. When player_input names "
                "an unavailable future objective, person, place, event, or system, preserve the player's urgency as "
                "intent but answer with an immediate consequence using only the current scene context; never name, "
                "reveal, or advance unavailable material. "
                "The narration must be new, directly responsive to that action, and must not merely repeat "
                "the entry text. "
                "Keep plot beats progressive: do not dump the scene outline or rush a transition merely because it "
                "is eligible. Ordinary actions need a substantive consequence, concrete new detail, a world or NPC "
                "reaction, and continued dramatic movement. Treat listed storylets as private realization guidance, "
                "never player choices. "
                "Creative consequences are allowed. Represent every durable invented or changed world fact, item, "
                "relationship, custody change, event, or transition in the proposal's operations, events, "
                "or transition so the runtime can validate it. Durable effects may only use an active storylet event "
                "with its realization_id and its exact route-authorized operations. Emit an event only when its ID "
                "appears in scene.active_storylets; otherwise use an empty events list. Never infer event availability "
                "from plot prose, pacing, or a previously completed beat, and never retry a completed storylet. "
                "For an event, copy the selected active realization's listed operations exactly; each uses "
                "the response-schema shape {operation, fact: {predicate, subject: 'story', value}}. "
                "Do not echo the player input, "
                "scene context, "
                "schema, or any explanation."
            ),
            "user": json.dumps(
                {
                    "instructions": (
                        "Narrate only from this player-safe scene context; never invent facts "
                        "or reveal protected knowledge."
                    ),
                    "player_input": player_input,
                    "scene": context.model_dump(mode="json", exclude={"response_schema"}),
                    "response_schema": context.response_schema,
                },
                separators=(",", ":"),
            ),
            "max_tokens": 2048,
            "response_format": {"type": "json_object"},
        }
        try:
            return self._request(payload)
        except HTTPError as error:
            if self._worker_error_code(error) != "AI_JSON_MODE_REJECTED":
                raise self._narration_error(error) from error
        except (URLError, OSError, TimeoutError, ValueError, json.JSONDecodeError) as error:
            raise NarrationProviderError("narration service is unavailable") from error

        fallback_payload = {key: value for key, value in payload.items() if key != "response_format"}
        try:
            return self._request(fallback_payload)
        except HTTPError as error:
            raise self._narration_error(error) from error
        except (URLError, OSError, TimeoutError, ValueError, json.JSONDecodeError) as error:
            raise NarrationProviderError("narration service is unavailable") from error

    def _request(self, payload: dict[str, object]) -> object:
        headers = {
            "Content-Type": "application/json",
            # Cloudflare Browser Integrity Check rejects urllib's default bot-like
            # signature before this request can reach the Worker.
            "User-Agent": (
                "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/136.0.0.0 Safari/537.36"
            ),
        }
        if self.token:
            headers["Authorization"] = f"Bearer {self.token}"
        request = Request(self.worker_url, data=json.dumps(payload).encode(), headers=headers, method="POST")
        with urlopen(request, timeout=float(getenv("CLOUDFLARE_TIMEOUT", "15"))) as response:  # noqa: S310
            body = json.loads(response.read())
        if isinstance(body, dict) and body.get("status") == "error":
            raise NarrationProviderError(str(body.get("message", "narration service failed")), 502)
        if isinstance(body, dict) and isinstance(body.get("narration"), str):
            return json.loads(body["narration"])
        return body

    @staticmethod
    def _worker_error_code(error: HTTPError) -> str:
        cached_code = getattr(error, "_freytag_worker_error_code", None)
        if isinstance(cached_code, str):
            return cached_code
        try:
            body = json.loads(error.read())
        except (OSError, ValueError, json.JSONDecodeError):
            code = ""
        else:
            code = str(body.get("code", "")) if isinstance(body, dict) else ""
        error._freytag_worker_error_code = code
        return code

    @classmethod
    def _narration_error(cls, error: HTTPError) -> NarrationProviderError:
        code = cls._worker_error_code(error) or "UNKNOWN"
        trace_id = cls._error_header(error, "X-Trace-ID")
        worker_revision = cls._error_header(error, "X-Worker-Revision")
        if code in {"AI_QUOTA_EXCEEDED", "AI_CAPACITY_EXCEEDED"}:
            return NarrationProviderError("narration service is at capacity", 429, code, trace_id, worker_revision)
        if code and 400 <= error.code < 500:
            return NarrationProviderError(
                "narration service rejected the turn", error.code, code, trace_id, worker_revision
            )
        return NarrationProviderError(
            "narration service rejected the turn", 429 if error.code == 429 else 502, code, trace_id, worker_revision
        )

    @staticmethod
    def _error_header(error: HTTPError, name: str) -> str:
        return str(error.headers.get(name, "")).strip() if error.headers else ""
