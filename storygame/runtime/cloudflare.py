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
            "system": "Return only a valid TurnProposal JSON object matching response_schema.",
            "user": json.dumps({"player_input": player_input, "scene_context": context.model_dump(mode="json")}),
            "max_tokens": 1024,
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
        headers = {"Content-Type": "application/json"}
        if self.token:
            headers["Authorization"] = f"Bearer {self.token}"
        request = Request(self.worker_url, data=json.dumps(payload).encode(), headers=headers, method="POST")
        with urlopen(request, timeout=float(getenv("CLOUDFLARE_TIMEOUT", "15"))) as response:  # noqa: S310
            body = json.loads(response.read())
        if isinstance(body, dict) and body.get("status") == "error":
            raise NarrationProviderError(str(body.get("message", "narration service failed")), 502)
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
        code = cls._worker_error_code(error)
        if code in {"AI_QUOTA_EXCEEDED", "AI_CAPACITY_EXCEEDED"}:
            return NarrationProviderError("narration service is at capacity", 429)
        if code == "AI_REQUEST_REJECTED" and 400 <= error.code < 500:
            return NarrationProviderError("narration service rejected the turn", error.code)
        return NarrationProviderError("narration service rejected the turn", 429 if error.code == 429 else 502)
