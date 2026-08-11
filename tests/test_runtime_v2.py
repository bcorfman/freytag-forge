"""Phase 3 contracts for the standalone V2 runtime."""

from __future__ import annotations

import json

import pytest

from storygame.authoring.compiler import load_compiled_story_fixture
from storygame.runtime.contracts import RuntimeFailure, TurnResult
from storygame.runtime.engine import JsonModeRejected, RuntimeEngine
from storygame.runtime.pacing import PacingController
from storygame.runtime.state import bootstrap_runtime_state, runtime_state_bytes


class StubModel:
    def __init__(self, responses: list[object]) -> None:
        self.responses = responses
        self.calls: list[bool] = []

    def play_turn(self, context: object, *, json_object: bool) -> object:
        self.calls.append(json_object)
        response = self.responses.pop(0)
        if isinstance(response, Exception):
            raise response
        return response


def _state():
    return bootstrap_runtime_state(load_compiled_story_fixture("mystery"))


def _turn(**overrides: object) -> dict[str, object]:
    result: dict[str, object] = {
        "narration": "You examine the square for a reliable lead.",
        "operations": [{"kind": "add", "path": "world.flags", "value": "searched_square"}],
        "beat_updates": [],
        "material_progress": True,
    }
    result.update(overrides)
    return result


def test_runtime_bootstraps_every_compiled_fixture_and_happy_turn_uses_one_call() -> None:
    for genre in ("mystery", "fantasy", "sci-fi", "relationship"):
        state = bootstrap_runtime_state(load_compiled_story_fixture(genre))
        assert state.world.location
        assert state.active_beats
        fixture_engine = RuntimeEngine(state, StubModel([_turn()]))
        assert fixture_engine.turn("Take a meaningful action.").ok

    model = StubModel([_turn()])
    engine = RuntimeEngine(_state(), model)
    response = engine.turn("Search the square.")
    assert response.ok and response.turn_index == 1
    assert engine.state.world.flags == {"searched_square"}
    assert model.calls == [True]
    assert engine.state.recent_events[-1].prompt_version == "runtime-v2-turn-v1"
    assert engine.state.recent_events[-1].prompt_token_estimate > 0


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        ('{"narration":"ok","operations":[],"beat_updates":[]}', "ok"),
        ('```json\n{"narration":"fenced","operations":[],"beat_updates":[]}\n```', "fenced"),
        (
            {"result": {"response": {"narration": "nested", "operations": [], "beat_updates": []}}},
            "nested",
        ),
        (
            {"choices": [{"message": {"content": {"narration": "choice", "operations": [], "beat_updates": []}}}]},
            "choice",
        ),
    ],
)
def test_turn_result_normalizes_provider_envelopes(raw: object, expected: str) -> None:
    assert TurnResult.from_provider(raw).narration == expected


def test_pacing_transitions_reset_on_progress_and_force_consequence_keeps_agency() -> None:
    state = _state()
    pace = PacingController()
    beat = state.active_beats[0]
    directives = [pace.directive(beat, turns_active=turn, stagnant_turns=turn) for turn in (0, 2, 4, 6, 8)]
    assert [directive.mode for directive in directives] == ["open", "nudge", "advance", "escalate", "force_consequence"]
    assert directives[-1].player_action is None
    updated = pace.after_turn(beat, turns_active=8, stagnant_turns=8, material_progress=True)
    assert updated.stagnant_turns == 0


@pytest.mark.parametrize(
    "result",
    [
        _turn(operations=[{"kind": "set", "path": "world.unknown", "value": "no"}]),
        _turn(
            operations=[
                {"kind": "set", "path": "world.items.ledger.holder", "value": "one"},
                {"kind": "set", "path": "world.items.ledger.holder", "value": "two"},
            ]
        ),
        _turn(narration="The disappearance was staged."),
        _turn(beat_updates=[{"beat_id": "public_crisis", "completion_tags": ["accusation_stopped"]}]),
    ],
)
def test_invalid_turns_are_atomic(result: dict[str, object]) -> None:
    engine = RuntimeEngine(_state(), StubModel([result]))
    before = runtime_state_bytes(engine.state)
    response = engine.turn("Try something.")
    assert not response.ok
    assert runtime_state_bytes(engine.state) == before


def test_valid_beat_completion_requires_order_and_commits_monotonically() -> None:
    engine = RuntimeEngine(
        _state(),
        StubModel([_turn(beat_updates=[{"beat_id": "find_evidence", "completion_tags": ["evidence_found"]}])]),
    )
    assert engine.turn("Follow the trail.").ok
    assert engine.state.beat_runtime["find_evidence"].completed_tags == {"evidence_found"}
    assert "public_crisis" in {beat.id for beat in engine.state.active_beats}


def test_malformed_response_and_recovery_exhaustion_fail_closed() -> None:
    engine = RuntimeEngine(_state(), StubModel(["not JSON", "still not JSON"]))
    before = runtime_state_bytes(engine.state)
    response = engine.turn("Look around.")
    assert response.error is not None and response.error.code == "RUNTIME_RECOVERY_EXHAUSTED"
    assert runtime_state_bytes(engine.state) == before
    assert len(engine.model.calls) == 2


def test_json_mode_rejection_uses_one_plain_json_recovery() -> None:
    engine = RuntimeEngine(_state(), StubModel([JsonModeRejected(), json.dumps(_turn())]))
    assert engine.turn("Look around.").ok
    assert engine.model.calls == [True, False]


def test_runtime_failure_is_typed() -> None:
    failure = RuntimeFailure("INVALID_TURN", "nope")
    assert failure.code == "INVALID_TURN"
