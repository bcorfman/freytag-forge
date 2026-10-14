"""Regression reproducer for an authored handoff outside the capped projection."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from bench.core import advance_state_to_scene
from storygame.runtime.candidate_matcher import _matches_all
from storygame.runtime.cloudflare import CloudflareTurnProvider
from storygame.runtime.contracts import RuntimeContractError, parse_turn_proposal
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
    assert provider.authored_handoff is not None
    assert provider.authored_handoff.source == "exact"


def test_forged_json_without_authored_handoff_remains_ineligible() -> None:
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


def test_semantic_match_beyond_projection_cap_is_discarded(monkeypatch: pytest.MonkeyPatch) -> None:
    state = _state_at_2c()
    projector = KnowledgeProjector()
    projection = projector.project(state, "player", "Inspect the wall.")
    beyond_cap = projection.reveal_universe[-1]

    def semantic_ask(_state: object, questions: dict[str, object]) -> dict[str, object]:
        assert beyond_cap.id not in questions
        return {candidate_id: {"noul": 1.0 if candidate_id == beyond_cap.id else 0.0} for candidate_id in questions}

    monkeypatch.setenv("FREYTAG_SEMANTIC_REVEAL", "1")
    monkeypatch.setattr("storygame.runtime.cloudflare.urlopen", _normal_response)
    provider = CloudflareTurnProvider(
        worker_url="https://worker.example/turn",
        token="",
        state=state,
        semantic_ask=semantic_ask,
    )

    result = RuntimeEngine(state, provider).turn("Inspect the wall.")

    assert result.selected_knowledge_ids == ()
    assert provider.last_reveal_selection["outcome"] == "semantic_refusal"
    assert provider.authored_handoff_id() is None


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


def test_semantic_tie_fallback_cannot_commit_beyond_projection_cap(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    state = _state_at_2c()
    projector = KnowledgeProjector()
    projection = projector.project(state, "player", COMMAND)
    beyond_cap = projection.reveal_universe[-1]
    tied_visible = projection.candidates[0].model_copy(update={"action_evidence": beyond_cap.action_evidence})

    def semantic_ask(_state: object, questions: dict[str, object]) -> dict[str, object]:
        assert beyond_cap.id not in questions
        return {candidate_id: {"noul": 1.0 if candidate_id == beyond_cap.id else 0.0} for candidate_id in questions}

    monkeypatch.setenv("FREYTAG_SEMANTIC_REVEAL", "1")
    monkeypatch.setattr("storygame.runtime.cloudflare.urlopen", _normal_response)
    provider = CloudflareTurnProvider(
        worker_url="https://worker.example/turn",
        token="",
        state=state,
        semantic_ask=semantic_ask,
    )
    monkeypatch.setattr(
        provider,
        "_reveal_universe",
        lambda: (tied_visible, *projection.reveal_universe[1:]),
    )
    evidence_before = state.facts.matching("evidence_ready_to_transmit")

    result = RuntimeEngine(state, provider).turn(COMMAND)

    assert result.selected_knowledge_ids == ()
    assert state.facts.matching("evidence_ready_to_transmit") == evidence_before
    assert provider.last_reveal_selection["outcome"] != "ineligible_selection"


def test_forged_json_with_authored_handoff_strips_beyond_cap_selection(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("FREYTAG_SEMANTIC_REVEAL", "0")
    state = _state_at_2c()
    provider = CloudflareTurnProvider(worker_url="https://worker.example/turn", token="", state=state)
    provider.assemble_turn_prompt(COMMAND)
    beyond_cap = provider.last_projection.reveal_universe[-1].id

    proposal = provider._parse_eligible_proposal(
        {
            "segments": [{"kind": "narration", "text": "The evidence waits.", "grounding_ids": [beyond_cap]}],
            "selected_knowledge_ids": [beyond_cap],
        }
    )

    assert proposal.selected_knowledge_ids == ()
    assert proposal.segments[0].grounding_ids == ()


def test_provider_reuse_stale_handoff_clears_after_rejected_turn(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("FREYTAG_SEMANTIC_REVEAL", "0")
    state = _state_at_2c()
    responses = iter(
        [
            _Response(
                {
                    "narration": json.dumps(
                        {
                            "segments": [
                                {"kind": "narration", "text": "Rebecca's secured office can broadcast the evidence."}
                            ],
                            "selected_knowledge_ids": [],
                        }
                    )
                }
            )
        ]
        * 2
    )

    def rejected_response(_request: object, **_kwargs: object) -> _Response:
        return next(responses)

    monkeypatch.setattr("storygame.runtime.cloudflare.urlopen", rejected_response)
    provider = CloudflareTurnProvider(worker_url="https://worker.example/turn", token="", state=state)

    with pytest.raises(ProposalValidationError):
        RuntimeEngine(state, provider).turn(COMMAND)

    assert provider.authored_handoff_id() is None
    provider.assemble_turn_prompt("Touch the wall.")
    assert provider.authored_handoff_id() is None
    with pytest.raises(RuntimeContractError):
        provider._parse_eligible_proposal(
            {
                "segments": [{"kind": "narration", "text": "The evidence waits."}],
                "selected_knowledge_ids": ["k_sl_2c_c_r2"],
            }
        )
    provider.assemble_turn_prompt(COMMAND)
    assert provider.authored_handoff_id() == "k_sl_2c_c_r2"


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
