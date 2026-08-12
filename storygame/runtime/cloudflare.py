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
            "max_tokens": 1024,
        }
        if json_object:
            payload["response_format"] = {"type": "json_object"}
        headers = {"Content-Type": "application/json", "User-Agent": "FreytagForge/2"}
        if self.token:
            headers["Authorization"] = f"Bearer {self.token}"
        request = urllib.request.Request(self.url, data=json.dumps(payload).encode(), method="POST", headers=headers)
        try:
            with urllib.request.urlopen(request, timeout=self.timeout) as response:
                return _normalize_turn_envelope(json.loads(response.read().decode()))
        except urllib.error.HTTPError as exc:
            detail = exc.read().decode(errors="replace") if exc.fp else str(exc)
            if json_object and _json_mode_rejected(detail):
                raise JsonModeRejected(detail) from exc
            raise RuntimeError(f"Cloudflare AI agent request failed: {exc.code} {detail[:800]}") from exc
        except (urllib.error.URLError, json.JSONDecodeError) as exc:
            raise RuntimeError("Cloudflare AI agent request failed") from exc


def _normalize_turn_envelope(response: object) -> object:
    """Remove only known Cloudflare transport metadata before local validation."""
    if not isinstance(response, dict) or "narration" not in response:
        return response
    turn = {
        key: value
        for key, value in response.items()
        if key not in {"model", "trace_id", "upstream_request_id", "worker_revision"}
    }
    narration = turn.get("narration")
    if isinstance(narration, str):
        try:
            nested = json.loads(narration)
        except json.JSONDecodeError:
            return turn
        if isinstance(nested, dict):
            return nested
    return turn


def _json_mode_rejected(detail: str) -> bool:
    try:
        payload = json.loads(detail)
    except json.JSONDecodeError:
        payload = {}
    if isinstance(payload, dict) and payload.get("code") == "AI_JSON_MODE_REJECTED":
        return True
    normalized = detail.casefold()
    return any(marker in normalized for marker in ("json mode", "json schema", "response_format", "couldn't be met"))


_SYSTEM_PROMPT = (
    "Return one JSON object only, with no markdown. Author an open-ended interactive-fiction turn from the supplied "
    "state. Do not dictate the player's action or reveal protected information before its release tags. The exact "
    "shape is {\"narration\":string,\"operations\":array,\"beat_updates\":array,\"material_progress\":boolean,"
    "\"summary_delta\":string|null}. operations must be an array of {\"kind\":\"set|add|remove\","
    "\"path\":string,\"value\":any}; never use an object keyed by path. beat_updates must be an array of "
    "{\"beat_id\":string,\"completion_tags\":array of strings,\"evidence\":string}; never include id, phase, "
    "or summary. Use [] for operations or beat_updates when none apply, and a boolean—not an object—for "
    "material_progress. Narration may describe only committed effects."
)
