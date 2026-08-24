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


def _first_beat() -> tuple[str, str]:
    beat = load_compiled_story_fixture("mystery").beats[0]
    return beat.id, beat.completion_tags[0].id


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
    assert "searched_square" in engine.state.world.flags
    assert model.calls == [True]
    assert engine.state.recent_events[-1].prompt_version == "runtime-v2-turn-v2"
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
        _turn(narration=load_compiled_story_fixture("mystery").protected_revelations[0].summary),
        _turn(beat_updates=[{"beat_id": "not_active", "completion_tags": ["not_active"]}]),
    ],
)
def test_invalid_turns_are_atomic(result: dict[str, object]) -> None:
    engine = RuntimeEngine(_state(), StubModel([result]))
    before = runtime_state_bytes(engine.state)
    response = engine.turn("Try something.")
    assert not response.ok
    assert runtime_state_bytes(engine.state) == before


def test_valid_beat_completion_requires_order_and_commits_monotonically() -> None:
    beat_id, completion_tag = _first_beat()
    engine = RuntimeEngine(
        _state(),
        StubModel([_turn(beat_updates=[{"beat_id": beat_id, "completion_tags": [completion_tag]}])]),
    )
    assert engine.turn("Follow the trail.").ok
    assert engine.state.beat_runtime[beat_id].completed_tags == {completion_tag}
    assert load_compiled_story_fixture("mystery").beats[1].id in {beat.id for beat in engine.state.active_beats}


def test_validated_set_replaces_the_flags_collection() -> None:
    engine = RuntimeEngine(
        _state(),
        StubModel([_turn(operations=[{"kind": "set", "path": "world.flags", "value": ["searched_square"]}])]),
    )
    assert engine.turn("Search the square.").ok
    assert engine.state.world.flags == {"searched_square"}


def test_unknown_completion_tag_still_fails_with_the_declared_tags() -> None:
    beat_id, completion_tag = _first_beat()
    engine = RuntimeEngine(
        _state(),
        StubModel(
            [
                _turn(beat_updates=[{"beat_id": beat_id, "completion_tags": ["invented"]}]),
                _turn(beat_updates=[{"beat_id": beat_id, "completion_tags": ["invented"]}]),
            ]
        ),
    )
    response = engine.turn("Search the square.")
    assert response.error is not None
    assert completion_tag in str(response.error.__cause__)


def test_malformed_response_and_recovery_exhaustion_fail_closed() -> None:
    engine = RuntimeEngine(_state(), StubModel(["not JSON", "still not JSON"]))
    before = runtime_state_bytes(engine.state)
    response = engine.turn("Look around.")
    assert response.error is not None and response.error.code == "RUNTIME_RECOVERY_EXHAUSTED"
    assert runtime_state_bytes(engine.state) == before
    assert len(engine.model.calls) == 2


def test_recovery_call_receives_bounded_local_validation_feedback() -> None:
    class RepairAwareModel:
        def __init__(self) -> None:
            self.contexts: list[object] = []

        def play_turn(self, context: object, *, json_object: bool) -> object:
            self.contexts.append(context)
            if json_object:
                return {"narration": "Broken.", "operations": {"add": "invalid"}}
            return _turn()

    model = RepairAwareModel()
    assert RuntimeEngine(_state(), model).turn("Search the square.").ok
    recovery = model.contexts[1]
    assert recovery.payload["recovery_instruction"].startswith("Your previous response failed local validation:")
    assert len(recovery.payload["recovery_instruction"]) <= 900


def test_json_mode_rejection_uses_one_plain_json_recovery() -> None:
    engine = RuntimeEngine(_state(), StubModel([JsonModeRejected(), json.dumps(_turn())]))
    assert engine.turn("Look around.").ok
    assert engine.model.calls == [True, False]


def test_runtime_failure_is_typed() -> None:
    failure = RuntimeFailure("INVALID_TURN", "nope")
    assert failure.code == "INVALID_TURN"


def test_runtime_context_exposes_declared_beat_tags_not_beat_metadata_as_output() -> None:
    context = RuntimeEngine(_state(), StubModel([])).context_builder.build(_state(), "Search the square.")
    beat = context.payload["active_beats"][0]
    beat_id, completion_tag = _first_beat()
    assert beat == {"id": beat_id, "completion_tags": [completion_tag]}
    operations = context.payload["turn_result_contract"]["operations"]
    assert operations == "array of {kind,path,value}; use [] when no state change"
    assert context.payload["turn_result_contract"]["completion_tag_rule"] == (
        "copy only the exact completion_tags listed for the matching active beat; otherwise use []"
    )


def test_runtime_context_exposes_a_public_opening_with_a_first_direction_for_every_genre() -> None:
    for genre in ("mystery", "fantasy", "sci-fi", "relationship"):
        state = bootstrap_runtime_state(load_compiled_story_fixture(genre))
        opening = RuntimeEngine(state, StubModel([])).context_builder.build(state, "look").payload["opening"]

        assert opening["premise"] == state.compiled_story.premise
        assert opening["public_facts"]
        assert opening["current_location"] == state.world.location
        assert opening["available_destinations"] or opening["first_beat"]
        public_opening = {key: value for key, value in opening.items() if key != "protected_boundaries"}
        assert all(protection["summary"] not in str(public_opening) for protection in opening["protected_boundaries"])


def test_declared_destination_aliases_commit_unambiguous_movement() -> None:
    engine = RuntimeEngine(
        _state(),
        StubModel([_turn(operations=[{"kind": "set", "path": "world.location", "value": "foyer"}])]),
    )

    response = engine.turn("go west gallery")

    assert response.ok
    assert engine.state.world.location == "west_gallery"


def test_enter_destination_alias_is_a_deterministic_movement_affordance() -> None:
    engine = RuntimeEngine(_state(), StubModel([_turn(operations=[])]))

    response = engine.turn("enter west gallery")

    assert response.ok
    assert engine.state.world.location == "west_gallery"
