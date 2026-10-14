"""Regression reproducer for an authored handoff outside the capped projection."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from bench.core import advance_state_to_scene
from storygame.runtime.candidate_matcher import _matches_all
from storygame.runtime.cloudflare import CloudflareTurnProvider
from storygame.runtime.contracts import parse_turn_proposal
from storygame.runtime.engine import RuntimeEngine
from storygame.runtime.knowledge import KnowledgeProjector
from storygame.runtime.state import RuntimeState
from storygame.runtime.validation import ProposalValidationError, SelectedRevealResolver
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


def test_authored_reveal_match_beyond_projection_cap_is_earned(monkeypatch: pytest.MonkeyPatch) -> None:
    """An exact authored match may earn the fifth reveal in the full universe."""

    monkeypatch.setenv("FREYTAG_SEMANTIC_REVEAL", "0")
    state = _state_at_2c()

    r1 = PACKAGE.knowledge_indexes.by_id["k_sl_2c_c_r1"]
    r2 = PACKAGE.knowledge_indexes.by_id["k_sl_2c_c_r2"]
    assert _matches_all(r2.action_evidence, COMMAND)
    assert not _matches_all(r1.action_evidence, COMMAND)
    assert any(effect.fact_id == "evidence_ready_to_transmit" for effect in r2.establishes)

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
    provider = CloudflareTurnProvider(worker_url="https://worker.example/turn", token="", state=state)
    evidence_before = state.facts.matching("evidence_ready_to_transmit")

    result = RuntimeEngine(state, provider).turn(COMMAND)

    assert result.selected_knowledge_ids == (r2.id,)
    assert result.events[0].knowledge_ids == (r2.id,)
    assert state.facts.matching("evidence_ready_to_transmit") != evidence_before
    assert r2.delivery_text in result.narration
    assert any(r2.id in segment.grounding_ids for segment in result.segments)


def test_model_selection_beyond_projection_cap_remains_ineligible() -> None:
    state = _state_at_2c()
    projector = KnowledgeProjector()
    projection = projector.project(state, "player", COMMAND)
    beyond_cap = projection.reveal_universe[-1].id
    assert beyond_cap not in {item.id for item in projection.candidates}

    with pytest.raises(ProposalValidationError) as raised:
        SelectedRevealResolver(PACKAGE).resolve(
            state,
            projection,
            parse_turn_proposal(
                {
                    "segments": [{"kind": "narration", "text": "The evidence waits."}],
                    "selected_knowledge_ids": [beyond_cap],
                }
            ),
            projector,
            COMMAND,
        )

    assert raised.value.code == "ineligible_selection"


def test_handoff_id_outside_reveal_universe_remains_ineligible() -> None:
    state = _state_at_2c()
    projector = KnowledgeProjector()
    projection = projector.project(state, "player", COMMAND)
    outside_universe = "k_sl_1a_a_r1"
    assert outside_universe not in {item.id for item in projection.reveal_universe}

    with pytest.raises(ProposalValidationError) as raised:
        SelectedRevealResolver(PACKAGE).resolve(
            state,
            projection,
            parse_turn_proposal(
                {
                    "segments": [{"kind": "narration", "text": "The evidence waits."}],
                    "selected_knowledge_ids": [outside_universe],
                }
            ),
            projector,
            COMMAND,
            authored_handoff_id=outside_universe,
        )

    assert raised.value.code == "ineligible_selection"
