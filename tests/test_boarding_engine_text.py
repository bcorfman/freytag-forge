from __future__ import annotations

import json
from pathlib import Path

import pytest

from storygame.runtime.capture import WorldCapture, build_capture_provider
from storygame.runtime.engine import RuntimeEngine
from storygame.runtime.item_facts import ItemFactsProvider
from storygame.runtime.state import RuntimeState
from storygame.runtime.world_model import world_for
from storygame.story_package.loader import load_story_package
from tests.test_place_scoped_feed import _synthetic_package

ROOT = Path(__file__).parents[1]
PACKAGE = load_story_package(ROOT / "data/stories/continuity-initiative")
BOARDING_STEPS = (
    "Kristin sat down in the driver's seat.",
    "Kristin's laptop sat on the passenger seat.",
)


class _Response:
    def __init__(self, body: object) -> None:
        self.body = json.dumps(body).encode()

    def read(self) -> bytes:
        return self.body

    def __enter__(self) -> _Response:
        return self

    def __exit__(self, *_args: object) -> bool:
        return False


def _provider(state: RuntimeState) -> ItemFactsProvider:
    return ItemFactsProvider(
        worker_url="https://worker.example/turn",
        token="",
        state=state,
        item_facts={},
        mode="single_call",
        seed_from_package=True,
        held_by=True,
    )


def _real_boarding_engine(*, only_boards: bool = True):
    state = RuntimeState.bootstrap(PACKAGE)
    world = world_for(PACKAGE, state.facts)
    assert world.move("kristin", "outside_house").ok
    assert world.move("kristin_laptop", "truck_passenger_seat").ok
    provider = _provider(state)

    capture: WorldCapture | None = None

    def ask(_state, questions):
        is_boarding = capture is not None and capture._command == "Get in."
        return {
            question: {
                "noul": (
                    1.0
                    if is_boarding
                    and (question == "boards_vehicle" or (only_boards and question == "only_boards_vehicle"))
                    else 0.0
                )
            }
            for question in questions
        }

    capture = WorldCapture(provider, ask)
    return state, provider, RuntimeEngine(state, provider, capture=capture)


def _stub_narrator(monkeypatch: pytest.MonkeyPatch, *, allow: list[bool], calls: list[object]) -> None:
    def open_request(request, **_kwargs: object) -> _Response:
        if not allow[0]:
            raise AssertionError("the consumed boarding turn called the narrator")
        calls.append(request)
        return _Response({"segments": [{"kind": "narration", "text": "The truck is quiet."}]})

    monkeypatch.setattr("storygame.runtime.cloudflare.urlopen", open_request)


def test_consumed_boarding_uses_engine_text_and_prints_final_narration(monkeypatch: pytest.MonkeyPatch) -> None:
    state, provider, engine = _real_boarding_engine()
    allow = [False]
    calls: list[object] = []
    _stub_narrator(monkeypatch, allow=allow, calls=calls)

    result = engine.turn("Get in.")

    assert all(step in result.narration for step in BOARDING_STEPS)
    assert world_for(PACKAGE, state.facts).parent("kristin") == "truck_driver_seat"
    assert provider.request_count == 0
    assert provider.last_turn_engine_text is True
    assert provider.last_prompt is None
    capture_after = engine.capture.last_after
    assert capture_after is not None
    assert capture_after["narration_prompt"] is None
    assert calls == []
    print(f"test (a) final narration: {result.narration}")


def test_consumed_boarding_discards_previous_narrator_item_facts(monkeypatch: pytest.MonkeyPatch) -> None:
    state = RuntimeState.bootstrap(PACKAGE)
    world = world_for(PACKAGE, state.facts)
    assert world.move("kristin", "outside_house").ok
    assert world.move("kristin_laptop", "truck_passenger_seat").ok
    provider = build_capture_provider(state)

    def ask(command, questions):
        return {
            question: {
                "noul": (
                    1.0
                    if (command.get("command") == "Get in." and question in {"boards_vehicle", "only_boards_vehicle"})
                    else 0.0
                )
            }
            for question in questions
        }

    engine = RuntimeEngine(
        state,
        provider,
        capture=WorldCapture(provider, ask, fixed_refusal=True, engine_refusal=True),
    )

    def open_request(_request, **_kwargs: object) -> _Response:
        return _Response(
            {
                "segments": [{"kind": "narration", "text": "Quiet."}],
                "item_facts": {"Kristin": {"place": "outside the house"}},
            }
        )

    monkeypatch.setattr("storygame.runtime.cloudflare.urlopen", open_request)
    for _ in range(3):
        engine.turn("Look around.")

    engine.turn("Get in.")

    boarded_world = world_for(PACKAGE, state.facts)
    assert boarded_world.parent("kristin") == "truck_driver_seat"
    assert boarded_world.parent("kristin_laptop") == "truck_passenger_seat"

    engine.turn("Look around.")
    assert world_for(PACKAGE, state.facts).parent("kristin") == "outside_house"


def test_synthetic_consumed_boarding_discards_previous_narrator_item_facts(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    package = _synthetic_boarding_package()
    state = RuntimeState.bootstrap(package)
    world = world_for(package, state.facts)
    assert world.move("hero", "yard").ok
    provider = build_capture_provider(state)

    def ask(command, questions):
        return {
            question: {
                "noul": (
                    1.0
                    if (command.get("command") == "Get in." and question in {"boards_vehicle", "only_boards_vehicle"})
                    else 0.0
                )
            }
            for question in questions
        }

    engine = RuntimeEngine(
        state,
        provider,
        capture=WorldCapture(provider, ask, fixed_refusal=True, engine_refusal=True),
    )

    def open_request(_request, **_kwargs: object) -> _Response:
        return _Response(
            {
                "segments": [{"kind": "narration", "text": "Quiet."}],
                "item_facts": {"Ari": {"place": "yard"}},
            }
        )

    monkeypatch.setattr("storygame.runtime.cloudflare.urlopen", open_request)
    for _ in range(3):
        engine.turn("Look around.")

    engine.turn("Get in.")

    assert world_for(package, state.facts).parent("hero") == "driver_seat"


def test_following_turn_calls_narrator_without_repeating_boarding_notice(monkeypatch: pytest.MonkeyPatch) -> None:
    _state, provider, engine = _real_boarding_engine()
    allow = [False]
    calls: list[object] = []
    _stub_narrator(monkeypatch, allow=allow, calls=calls)

    first = engine.turn("Get in.")
    allow[0] = True
    second = engine.turn("Look around.")

    assert all(step in first.narration for step in BOARDING_STEPS)
    assert second.narration.startswith("The truck is quiet.")
    assert BOARDING_STEPS[1] not in second.narration
    assert provider.last_turn_engine_text is False
    assert len(calls) == 2


def test_boarding_with_another_action_still_calls_narrator(monkeypatch: pytest.MonkeyPatch) -> None:
    _state, provider, engine = _real_boarding_engine(only_boards=False)
    allow = [True]
    calls: list[object] = []
    _stub_narrator(monkeypatch, allow=allow, calls=calls)

    result = engine.turn("Drive the truck.")

    assert result.narration.startswith("The truck is quiet.")
    assert provider.last_turn_engine_text is False
    assert len(calls) == 2


def _synthetic_boarding_package():
    package = _synthetic_package()
    scene = package.scenes[0]
    placements = dict(scene.metadata.item_placements)
    placements["lamp"] = placements["lamp"].model_copy(update={"parent": "car"})
    metadata = scene.metadata.model_copy(update={"item_placements": placements})
    scene = scene.model_copy(update={"metadata": metadata})
    items = tuple(
        item.model_copy(
            update=(
                {"enter_text": "Ari settles into the blue car."}
                if item.id == "driver_seat"
                else {"notice_text": "A brass key rests on the rear bench."}
                if item.id == "lamp"
                else {}
            )
        )
        for item in package.world.items
    )
    return package.model_copy(update={"scenes": (scene,), "world": package.world.model_copy(update={"items": items})})


def test_synthetic_story_uses_its_vehicle_and_item_text_without_narrator(monkeypatch: pytest.MonkeyPatch) -> None:
    package = _synthetic_boarding_package()
    state = RuntimeState.bootstrap(package)
    assert world_for(package, state.facts).move("hero", "yard").ok
    provider = _provider(state)
    engine = RuntimeEngine(
        state,
        provider,
        capture=WorldCapture(provider, lambda _state, questions: {question: {"noul": 1.0} for question in questions}),
    )
    monkeypatch.setattr(
        "storygame.runtime.cloudflare.urlopen",
        lambda *_args, **_kwargs: pytest.fail("the synthetic consumed boarding turn called the narrator"),
    )

    result = engine.turn("Get in.")

    assert "Ari settles into the blue car." in result.narration
    assert "A brass key rests on the rear bench." in result.narration
    assert world_for(package, state.facts).parent("hero") == "driver_seat"
    assert provider.request_count == 0


def test_boarded_snapshot_round_trip_preserves_following_turn(monkeypatch: pytest.MonkeyPatch) -> None:
    state, provider, engine = _real_boarding_engine()
    allow = [False]
    calls: list[object] = []
    _stub_narrator(monkeypatch, allow=allow, calls=calls)
    engine.turn("Get in.")
    snapshot = state.snapshot()

    restored = RuntimeState.bootstrap(PACKAGE)
    restored.restore_snapshot(snapshot)
    restored_provider = _provider(restored)
    restored_capture: WorldCapture | None = None

    def restored_ask(_state, questions):
        is_boarding = restored_capture is not None and restored_capture._command == "Get in."
        return {
            question: {"noul": 1.0 if is_boarding and question in {"boards_vehicle", "only_boards_vehicle"} else 0.0}
            for question in questions
        }

    restored_capture = WorldCapture(restored_provider, restored_ask)
    restored_engine = RuntimeEngine(
        restored,
        restored_provider,
        capture=restored_capture,
    )
    allow[0] = True

    original_result = engine.turn("Look around.")
    restored_result = restored_engine.turn("Look around.")

    assert original_result.narration == restored_result.narration
    assert world_for(PACKAGE, restored.facts).parent("kristin") == "truck_driver_seat"
    assert restored_provider.last_turn_engine_text is False
    assert len(calls) == 4


def test_staged_cue_is_withheld_from_engine_text_out_of_reach(monkeypatch: pytest.MonkeyPatch) -> None:
    state, provider, engine = _real_boarding_engine()
    delivery = next(item for item in PACKAGE.deliveries if item.fact_id == "continuity_initiative_known")
    state.staged_cue_fact_id = delivery.fact_id
    state.staged_cue_stage = 1
    monkeypatch.setattr(
        "storygame.runtime.cloudflare.urlopen",
        lambda *_args, **_kwargs: pytest.fail("the staged consumed boarding turn called the narrator"),
    )

    result = engine.turn("Get in.")

    assert all(step in result.narration for step in BOARDING_STEPS)
    assert delivery.cue_text not in result.narration
    assert state.staged_cue_fact_id == delivery.fact_id
