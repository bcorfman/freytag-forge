"""Deterministic provider for explicitly configured non-production deployments."""

from __future__ import annotations

import json
from os import getenv
from pathlib import Path

from storygame.runtime.cloudflare import NarrationProviderError
from storygame.runtime.state import RuntimeState


class ScriptedTurnProvider:
    """Return the configured opening and the persisted session turn's payload."""

    def __init__(self, state: RuntimeState, script_path: str) -> None:
        try:
            payload = json.loads(Path(script_path).read_text())
        except (OSError, json.JSONDecodeError) as error:
            raise NarrationProviderError(
                "scripted narration is unavailable", 503, "SCRIPTED_CONFIGURATION_ERROR"
            ) from error
        if not isinstance(payload, dict) or not isinstance(payload.get("turns"), list) or "opening" not in payload:
            raise NarrationProviderError("scripted narration is unavailable", 503, "SCRIPTED_CONFIGURATION_ERROR")
        self.state = state
        self.opening_payload = payload["opening"]
        self.turn_payloads = payload["turns"]

    @classmethod
    def from_environment(cls, state: RuntimeState) -> ScriptedTurnProvider:
        script_path = getenv("FREYTAG_SCRIPTED_TURNS", "").strip()
        if not script_path:
            raise NarrationProviderError("scripted narration is unavailable", 503, "SCRIPTED_CONFIGURATION_ERROR")
        return cls(state, script_path)

    def opening(self) -> object:
        return self.opening_payload

    def __call__(self, _player_input: str) -> object:
        turn_number = self.state.turn_index
        if turn_number < 1 or turn_number > len(self.turn_payloads):
            raise NarrationProviderError("scripted narration is unavailable", 503, "SCRIPTED_EXHAUSTED")
        return self.turn_payloads[turn_number - 1]
