"""Full engine coverage for the 2C evidence-cost authored handoff."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from bench.core import advance_state_to_scene
from storygame.runtime.cloudflare import CloudflareTurnProvider
from storygame.runtime.engine import RuntimeEngine
from storygame.runtime.facts import Fact
from storygame.runtime.state import RuntimeState
from storygame.story_package.loader import load_story_package

PACKAGE = load_story_package(Path("data/stories/continuity-initiative"))


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


COMMAND = "Assess the cost of transmitting our evidence right now to the people still held here."


def _provider(state, monkeypatch: pytest.MonkeyPatch) -> CloudflareTurnProvider:
    def open_request(_request: object, **_kwargs: object) -> _Response:
        return _Response(
            {
                "narration": json.dumps(
                    {
                        "segments": [{"kind": "narration", "text": "Brandon weighs the cost."}],
                        "selected_knowledge_ids": [],
                    }
                )
            }
        )

    monkeypatch.setattr("storygame.runtime.cloudflare.urlopen", open_request)
    return CloudflareTurnProvider(worker_url="https://worker.example/turn", token="", state=state)


def test_assess_cost_engine_turn_earns_and_commits_established_reveal(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("FREYTAG_SEMANTIC_REVEAL", "0")
    state = _state_at_2c()
    assert not state.facts.matching("evidence_ready_to_transmit")
    provider = _provider(state, monkeypatch)

    result = RuntimeEngine(state, provider).turn(COMMAND)

    assert result.selected_knowledge_ids == ("k_sl_2c_c_r2",)
    assert result.events[0].knowledge_ids == ("k_sl_2c_c_r2",)
    assert state.facts.matching("evidence_ready_to_transmit")
    assert "ineligible_selection" not in str(provider.last_reveal_selection)


def test_assess_cost_engine_turn_when_reveal_is_already_established(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("FREYTAG_SEMANTIC_REVEAL", "0")
    state = _state_at_2c()
    state.facts.assert_fact(Fact(predicate="evidence_ready_to_transmit", subject="story", value="true"))
    provider = _provider(state, monkeypatch)

    result = RuntimeEngine(state, provider).turn(COMMAND)

    assert result.narration
    assert result.selected_knowledge_ids in ((), ("k_sl_2c_c_r2",))
    assert "ineligible_selection" not in str(provider.last_reveal_selection)
