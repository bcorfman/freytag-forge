"""Regression reproducer for an authored handoff outside the capped projection."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from bench.core import advance_state_to_scene
from storygame.runtime.cloudflare import CloudflareTurnProvider
from storygame.runtime.engine import RuntimeEngine
from storygame.runtime.knowledge import KnowledgeProjector
from storygame.runtime.state import RuntimeState
from storygame.story_package.loader import load_story_package

PACKAGE = load_story_package(Path("data/stories/continuity-initiative"))
COMMAND = "Send the evidence."


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


def _normal_response(_request: object, **_kwargs: object) -> _Response:
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


@pytest.mark.nightly
def test_semantic_match_inside_projection_cap_still_commits(monkeypatch: pytest.MonkeyPatch) -> None:
    state = _state_at_2c()
    target = KnowledgeProjector().project(state, "player", "Inspect the wall.").candidates[-1]

    def semantic_ask(_state: object, questions: dict[str, object]) -> dict[str, object]:
        assert target.id in questions
        return {candidate_id: {"noul": 1.0 if candidate_id == target.id else 0.0} for candidate_id in questions}

    monkeypatch.setenv("FREYTAG_SEMANTIC_REVEAL", "1")
    monkeypatch.setattr("storygame.runtime.cloudflare.urlopen", _normal_response)
    provider = CloudflareTurnProvider(
        worker_url="https://worker.example/turn",
        token="",
        state=state,
        semantic_ask=semantic_ask,
    )

    result = RuntimeEngine(state, provider).turn("Inspect the wall.")

    assert result.selected_knowledge_ids == (target.id,)
    assert provider.last_reveal_selection["outcome"] == "semantic_match"
    assert provider.authored_handoff is not None
    assert provider.authored_handoff.source == "semantic"
