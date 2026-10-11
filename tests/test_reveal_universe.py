"""Hermetic checks for the uncapped reveal matching universe."""

from __future__ import annotations

from types import SimpleNamespace

import pytest

from storygame.runtime.cloudflare import CloudflareTurnProvider
from storygame.runtime.engine import RuntimeEngine
from tests.test_design_review_fixtures import _assert_story_facts, _scene_state


def _state():
    state = _scene_state("1A")
    _assert_story_facts(state, "memory_card_recovered", "michelle_warning_known")
    state.turn_index = 4
    RuntimeEngine(
        state, lambda _input: {"segments": [{"kind": "narration", "text": "The room is quiet."}]}
    )._activate_pacing()
    return state


def _provider(state, ask=None):
    return CloudflareTurnProvider(worker_url="", token="", state=state, semantic_ask=ask)


def test_fifth_eligible_reveal_gets_authored_handoff(monkeypatch):
    monkeypatch.setenv("FREYTAG_SEMANTIC_REVEAL", "0")
    provider = _provider(_state())

    provider.assemble_turn_prompt("Inspect the reflective tape.")

    assert provider.authored_handoff is not None
    assert provider.authored_handoff.candidate.id == "k_sl_1a_c_r2"
    assert provider.last_reveal_selection["outcome"] == "exact_match"


def test_narrator_projection_stays_capped_and_ordered():
    state = _state()
    provider = _provider(state)
    provider.assemble_turn_prompt("Describe the workstation.")
    projection = provider.last_projection
    assert projection is not None
    assert tuple(candidate.id for candidate in projection.candidates) == tuple(
        candidate.id for candidate in projection.reveal_universe[:4]
    )
    assert provider.prompt_candidate_ids == ()


@pytest.mark.parametrize(
    ("ask", "calls", "expected"),
    [
        (lambda _state, _questions: {}, 0, "semantic_refusal"),
        (lambda _state, _questions: (_ for _ in ()).throw(RuntimeError("provider")), 0, "provider_error"),
    ],
)
def test_semantic_telemetry_outcomes(ask, calls, expected):
    provider = _provider(_state(), ask)
    provider.semantic_fallback_calls = calls
    provider.assemble_turn_prompt("Tell me what is important.")
    assert provider.last_reveal_selection["outcome"] == expected


def test_exact_tie_telemetry():
    state = _state()
    provider = _provider(state)
    original = provider.projector.project(state, "player", "Inspect the reflective tape.")
    tied = original.reveal_universe + (original.reveal_universe[-1].model_copy(update={"id": "tied"}),)
    provider.projector = SimpleNamespace(
        project=lambda *_args: original.model_copy(update={"reveal_universe": tied, "candidates": tied[:4]})
    )
    provider.assemble_turn_prompt("Inspect the reflective tape.")
    assert provider.last_reveal_selection["outcome"] == "exact_tie"


def test_no_eligible_action_and_budget_exhausted_telemetry(monkeypatch):
    monkeypatch.setenv("FREYTAG_SEMANTIC_REVEAL", "0")
    provider = _provider(_state())
    projection = provider.projector.project(provider.state, "player", "Search the workstation.")
    empty = projection.model_copy(update={"candidates": (), "reveal_universe": ()})
    provider.projector = SimpleNamespace(project=lambda *_args: empty)
    provider.assemble_turn_prompt("Tell me what is important.")
    assert provider.last_reveal_selection["outcome"] == "no_eligible_action"

    monkeypatch.delenv("FREYTAG_SEMANTIC_REVEAL")
    provider = _provider(_state(), lambda *_args: {})
    provider.semantic_fallback_calls = 40
    provider.assemble_turn_prompt("Tell me what is important.")
    assert provider.last_reveal_selection["outcome"] == "budget_exhausted"


def test_request_reconstruction_is_stable(monkeypatch):
    monkeypatch.setenv("FREYTAG_SEMANTIC_REVEAL", "0")
    provider = _provider(_state())
    first = provider.assemble_turn_prompt("Inspect the workstation.")
    first_selection = provider.last_reveal_selection.copy()
    second = provider.assemble_turn_prompt("Inspect the workstation.")
    assert second == first
    assert provider.last_reveal_selection == first_selection
