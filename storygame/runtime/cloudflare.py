"""Cloudflare AI-agent transport for the V2 turn contract."""

from __future__ import annotations

import json
import os
import urllib.error
import urllib.request
from typing import Any

from storygame.runtime.context import RuntimeContext
from storygame.runtime.engine import JsonModeRejected


class CloudflareTurnModel:
    def __init__(self, *, url: str | None = None, token: str | None = None, timeout: float | None = None) -> None:
        self.url = url or os.getenv("CLOUDFLARE_WORKER_URL", "")
        self.token = token if token is not None else os.getenv("CLOUDFLARE_WORKER_TOKEN", "")
        self.timeout = timeout if timeout is not None else float(os.getenv("CLOUDFLARE_TIMEOUT", "10"))
        if not self.url:
            raise ValueError("CLOUDFLARE_WORKER_URL is required for the Cloudflare V2 turn model")

    def play_turn(self, context: RuntimeContext, *, json_object: bool) -> object:
        payload: dict[str, Any] = {
            "system": _SYSTEM_PROMPT,
            "user": json.dumps(context.payload, separators=(",", ":"), default=list),
            "response_format": {"type": "json_object"} if json_object else None,
        }
        headers = {"Content-Type": "application/json", "User-Agent": "FreytagForge/2"}
        if self.token:
            headers["Authorization"] = f"Bearer {self.token}"
        request = urllib.request.Request(self.url, data=json.dumps(payload).encode(), method="POST", headers=headers)
        try:
            with urllib.request.urlopen(request, timeout=self.timeout) as response:
                return _normalize_turn_envelope(json.loads(response.read().decode()))
        except urllib.error.HTTPError as exc:
            detail = exc.read().decode(errors="replace") if exc.fp else str(exc)
            if json_object and exc.code == 400:
                raise JsonModeRejected(detail) from exc
            raise RuntimeError(f"Cloudflare AI agent request failed: {exc.code}") from exc
        except (urllib.error.URLError, json.JSONDecodeError) as exc:
            raise RuntimeError("Cloudflare AI agent request failed") from exc


def _normalize_turn_envelope(response: object) -> object:
    """Remove only known Cloudflare transport metadata before local validation."""
    if not isinstance(response, dict) or "narration" not in response:
        return response
    return {key: value for key, value in response.items() if key not in {"model", "trace_id", "worker_revision"}}


_SYSTEM_PROMPT = (
    "Return JSON only. Author an open-ended interactive-fiction turn from the supplied state. "
    "Do not dictate the player's action. Do not reveal protected information before its listed release tags. "
    "Output narration, operations (set/add/remove only on supplied schema paths), beat_updates, optional "
    "summary_delta, and material_progress. Narration may describe only committed effects."
)
