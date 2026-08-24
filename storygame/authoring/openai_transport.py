"""Credential-safe OpenAI Responses transport for offline blueprint authoring."""

from __future__ import annotations

import json
import os
import time
from collections.abc import Mapping
from typing import Protocol
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from storygame.authoring.compiler import CompilationError
from storygame.authoring.model_tiers import resolve_compiler_model

_SAFE_RATE_LIMIT_HEADERS = (
    ("x-request-id", "request_id"),
    ("x-ratelimit-limit-requests", "limit_requests"),
    ("x-ratelimit-remaining-requests", "remaining_requests"),
    ("x-ratelimit-reset-requests", "reset_requests"),
    ("x-ratelimit-limit-tokens", "limit_tokens"),
    ("x-ratelimit-remaining-tokens", "remaining_tokens"),
    ("x-ratelimit-reset-tokens", "reset_tokens"),
    ("x-ratelimit-limit-project-tokens", "limit_project_tokens"),
    ("x-ratelimit-remaining-project-tokens", "remaining_project_tokens"),
    ("x-ratelimit-reset-project-tokens", "reset_project_tokens"),
)


class OpenAIResponsesClient(Protocol):
    def create_response(self, **kwargs: object) -> object: ...

    def retrieve_response(self, response_id: str, *, timeout_seconds: float) -> object: ...


class OpenAICompilerConfig:
    """Explicit live-authoring configuration; credentials never leave this boundary."""

    def __init__(
        self,
        *,
        api_key: str,
        model: str,
        reasoning_effort: str = "high",
        base_url: str = "https://api.openai.com/v1",
        timeout_seconds: float = 600,
        background: bool = False,
    ) -> None:
        if not api_key.strip():
            raise CompilationError("OPENAI_API_KEY_REQUIRED", "OPENAI_API_KEY is required for live compilation")
        if not model.strip():
            raise CompilationError("OPENAI_MODEL_REQUIRED", "an explicit OpenAI model is required")
        if timeout_seconds <= 0:
            raise CompilationError("OPENAI_TIMEOUT_INVALID", "request timeout must be positive")
        self.api_key = api_key
        self.model = model
        self.reasoning_effort = reasoning_effort
        self.base_url = base_url.rstrip("/")
        self.timeout_seconds = timeout_seconds
        self.background = background

    @classmethod
    def from_environment(
        cls,
        *,
        quality_tier: str | None = None,
        debug: bool = False,
        base_url: str | None = None,
        timeout_seconds: float | None = None,
        background: bool | None = None,
    ) -> OpenAICompilerConfig:
        api_key = os.getenv("OPENAI_API_KEY", "")
        selected_model, reasoning_effort = resolve_compiler_model(quality_tier, debug=debug)
        selected_base_url = base_url or os.getenv("OPENAI_BASE_URL", "https://api.openai.com/v1")
        return cls(
            api_key=api_key,
            model=selected_model,
            reasoning_effort=reasoning_effort,
            base_url=selected_base_url,
            timeout_seconds=timeout_seconds if timeout_seconds is not None else 600,
            background=background if background is not None else True,
        )


class _UrllibOpenAIResponsesClient:
    def __init__(self, config: OpenAICompilerConfig) -> None:
        self._config = config

    def create_response(self, **kwargs: object) -> object:
        payload = dict(kwargs)
        timeout_seconds = payload.pop("timeout_seconds", self._config.timeout_seconds)
        timeout = float(timeout_seconds) if isinstance(timeout_seconds, int | float) else self._config.timeout_seconds
        request = Request(
            f"{self._config.base_url}/responses",
            data=json.dumps(payload).encode("utf-8"),
            headers={
                "Authorization": f"Bearer {self._config.api_key}",
                "Content-Type": "application/json",
            },
            method="POST",
        )
        with urlopen(request, timeout=timeout) as response:  # noqa: S310 - explicit configured endpoint
            return json.loads(response.read().decode("utf-8"))

    def retrieve_response(self, response_id: str, *, timeout_seconds: float) -> object:
        request = Request(
            f"{self._config.base_url}/responses/{response_id}",
            headers={"Authorization": f"Bearer {self._config.api_key}"},
            method="GET",
        )
        with urlopen(request, timeout=timeout_seconds) as response:  # noqa: S310 - explicit configured endpoint
            return json.loads(response.read().decode("utf-8"))


def _mapping(value: object) -> Mapping[str, object] | None:
    return value if isinstance(value, Mapping) else None


def _strip_fence(value: str) -> str:
    text = value.strip()
    if text.startswith("```") and text.endswith("```"):
        return text.split("\n", 1)[1].rsplit("\n", 1)[0].strip()
    return text


def _extract_output(response: object) -> tuple[object, str | None]:
    payload = _mapping(response)
    if payload is None:
        return response, None
    identifier = payload.get("id")
    response_id = identifier if isinstance(identifier, str) else None
    if payload.get("refusal"):
        raise CompilationError("OPENAI_REFUSAL", "OpenAI refused the blueprint request")
    if "output_text" in payload:
        return payload["output_text"], response_id
    result = _mapping(payload.get("result"))
    if result is not None and "response" in result:
        return result["response"], response_id
    choices = payload.get("choices")
    if isinstance(choices, list) and choices:
        choice = _mapping(choices[0])
        message = _mapping(choice.get("message")) if choice is not None else None
        if message is not None and "content" in message:
            return message["content"], response_id
    output = payload.get("output")
    if isinstance(output, list):
        for item in output:
            output_item = _mapping(item)
            content = output_item.get("content") if output_item is not None else None
            if isinstance(content, list):
                for part in content:
                    mapped_part = _mapping(part)
                    if mapped_part and mapped_part.get("type") == "output_text" and "text" in mapped_part:
                        return mapped_part["text"], response_id
    return payload, response_id


def _rate_limit_detail(error: HTTPError) -> str:
    """Return only documented, non-secret diagnostics from a 429 response."""

    details = [f"{label}={value}" for header, label in _SAFE_RATE_LIMIT_HEADERS if (value := error.headers.get(header))]
    suffix = f" ({'; '.join(details)})" if details else ""
    return f"OpenAI request was rate limited (status 429){suffix}"


class OpenAIBlueprintTransport:
    """A first-party, injected-client adapter over the OpenAI Responses API."""

    def __init__(self, config: OpenAICompilerConfig, client: OpenAIResponsesClient | None = None) -> None:
        self._config = config
        self._client = client or _UrllibOpenAIResponsesClient(config)
        self.last_request_id: str | None = None

    def generate(self, prompt: str, *, json_object: bool) -> str | Mapping[str, object]:
        request: dict[str, object] = {
            "model": self._config.model,
            "input": prompt,
            "reasoning": {"effort": self._config.reasoning_effort},
            "timeout_seconds": self._config.timeout_seconds,
        }
        if json_object:
            request["text"] = {"format": {"type": "json_object"}}
        if self._config.background:
            request["background"] = True
        try:
            response = self._client.create_response(**request)
            if self._config.background:
                response = self._await_background_response(response)
        except TimeoutError as exc:
            raise CompilationError("OPENAI_TIMEOUT", "OpenAI request timed out") from exc
        except HTTPError as exc:
            if json_object and exc.code == 400:
                raise CompilationError("OPENAI_JSON_MODE_REJECTED", "OpenAI rejected JSON-object mode") from exc
            if exc.code == 429:
                raise CompilationError("OPENAI_RATE_LIMIT", _rate_limit_detail(exc)) from exc
            raise CompilationError("OPENAI_TRANSPORT_ERROR", f"OpenAI request failed with status {exc.code}") from exc
        except URLError as exc:
            raise CompilationError("OPENAI_TRANSPORT_ERROR", "OpenAI request could not be completed") from exc
        except Exception as exc:
            if json_object and getattr(exc, "status_code", None) == 400 and "json" in str(exc).casefold():
                raise CompilationError("OPENAI_JSON_MODE_REJECTED", "OpenAI rejected JSON-object mode") from exc
            raise CompilationError("OPENAI_TRANSPORT_ERROR", "OpenAI request could not be completed") from exc
        output, self.last_request_id = _extract_output(response)
        if isinstance(output, str):
            normalized = _strip_fence(output)
            if not normalized:
                raise CompilationError("OPENAI_EMPTY_OUTPUT", "OpenAI returned no blueprint output")
            try:
                parsed = json.loads(normalized)
            except json.JSONDecodeError:
                return normalized
            return parsed if isinstance(parsed, Mapping) else normalized
        if isinstance(output, Mapping):
            return output
        raise CompilationError("OPENAI_MALFORMED_OUTPUT", "OpenAI returned an unsupported response envelope")

    def _await_background_response(self, initial_response: object) -> object:
        response = initial_response
        deadline = time.monotonic() + self._config.timeout_seconds
        while True:
            payload = _mapping(response)
            if payload is None:
                raise CompilationError("OPENAI_MALFORMED_OUTPUT", "OpenAI returned an unsupported response envelope")
            status = payload.get("status")
            if status == "completed":
                return response
            if status in {"failed", "cancelled", "incomplete"}:
                raise CompilationError("OPENAI_BACKGROUND_FAILED", "OpenAI background request did not complete")
            response_id = payload.get("id")
            if not isinstance(response_id, str) or not response_id:
                raise CompilationError("OPENAI_MALFORMED_OUTPUT", "OpenAI background response did not include an ID")
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                raise CompilationError("OPENAI_TIMEOUT", "OpenAI request timed out")
            time.sleep(min(1, remaining))
            response = self._client.retrieve_response(response_id, timeout_seconds=remaining)
