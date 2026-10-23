"""Regression coverage for committed authored reveal IDs in turn delivery."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from bench.core import advance_state_to_scene
from storygame.runtime.cloudflare import CloudflareTurnProvider
from storygame.runtime.state import RuntimeState, TurnDelivery
from storygame.story_package.loader import load_story_package

PACKAGE = load_story_package(Path("data/stories/continuity-initiative"))
COMMAND = "Assess the cost of transmitting our evidence right now to the people still held here."


class _Response:
    def __init__(self, body: object) -> None:
        self.body = json.dumps(body).encode()

    def __enter__(self) -> _Response:
        return self

    def __exit__(self, *_args: object) -> None:
        return None

    def read(self) -> bytes:
        return self.body


def _state_at_2c() -> RuntimeState:
    state = RuntimeState.bootstrap(PACKAGE)
    advance_state_to_scene(PACKAGE, state, "2C")
    state.turn_index = 48
    state.scene_entered_at_turn = 47
    state.delivered_cue_ids = ("evidence_ready_to_transmit",)
    return state


def _provider(state: RuntimeState, monkeypatch: pytest.MonkeyPatch, text: str = "Brandon weighs the cost."):
    def open_request(_request: object, **_kwargs: object) -> _Response:
        return _Response(
            {"narration": json.dumps({"segments": [{"kind": "narration", "text": text}], "selected_knowledge_ids": []})}
        )

    monkeypatch.setenv("FREYTAG_SEMANTIC_REVEAL", "0")
    monkeypatch.setattr("storygame.runtime.cloudflare.urlopen", open_request)
    return CloudflareTurnProvider(worker_url="https://worker.example/turn", token="", state=state)


def test_old_turn_delivery_without_field_loads() -> None:
    delivery = TurnDelivery.model_validate({})

    assert delivery.revealed_knowledge_ids == ()
