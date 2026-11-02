from __future__ import annotations

from pathlib import Path

import pytest

from storygame.runtime.capture import WorldCapture, build_capture_provider
from storygame.runtime.engine import RuntimeEngine
from storygame.runtime.state import RuntimeState
from storygame.runtime.world_model import world_for
from storygame.story_package.loader import load_story_package
from tests.test_place_scoped_feed import _synthetic_package

ROOT = Path(__file__).parents[1]
PACKAGE = load_story_package(ROOT / "data/stories/continuity-initiative")


@pytest.fixture(autouse=True)
def offline_worker(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("CLOUDFLARE_WORKER_URL", "https://w.example")


def _scripted_jev(
    _state: object,
    questions: dict[str, object],
    *,
    board: bool,
    only_board: bool,
) -> dict[str, dict[str, float]]:
    state = _state if isinstance(_state, dict) else {}
    command = str(state.get("command", "")).lower()
    answers: dict[str, dict[str, float]] = {}
    for key in questions:
        if key == "boards_vehicle":
            yes = board and any(vehicle in command for vehicle in ("truck", "skiff"))
        elif key == "only_boards_vehicle":
            yes = only_board and any(vehicle in command for vehicle in ("truck", "skiff"))
        elif key == "searches_underneath":
            yes = "gap" in command
        elif key == "opens_container":
            yes = "open" in command and "drawer" in command
        else:
            yes = False
        answers[key] = {"noul": 1.0 if yes else 0.0}
    return answers


def _product_replay(
    *,
    board: bool,
    only_board: bool,
    force_narrator_for: tuple[str, ...] = (),
) -> tuple[RuntimeEngine, list[dict[str, str]]]:
    state = RuntimeState.bootstrap(PACKAGE)
    provider = build_capture_provider(state)
    provider.semantic_ask = lambda state, questions: _scripted_jev(state, questions, board=board, only_board=only_board)
    provider._request_item_facts = lambda _payload: {"refers": [], "same_as": {}}
    captured: list[dict[str, str]] = []

    def dispatch(system: str, user: dict[str, object]) -> dict[str, object]:
        captured.append({"system": system, "user": provider._section_user_prompt(user)})
        return {"segments": [{"kind": "narration", "text": "Offline probe narration."}], "selected_knowledge_ids": []}

    provider._dispatch = dispatch

    class ReplayCapture(WorldCapture):
        def before_turn(self, command: str) -> dict[str, object]:
            record = super().before_turn(command)
            if command in force_narrator_for:
                self.provider.command_consumed = False
            return record

    capture = ReplayCapture(
        provider,
        lambda state, questions: _scripted_jev(state, questions, board=board, only_board=only_board),
    )
    return RuntimeEngine(state, provider, capture=capture), captured


def _boarding_prompt(command: str, *, board: bool = True) -> str:
    engine, captured = _product_replay(
        board=board,
        only_board=True,
        force_narrator_for=(command,) if board else (),
    )
    for route_command in ("open the drawer", "feel in the gap", command):
        engine.turn(route_command)
    assert captured
    return captured[-1]["user"]


def _synthetic_package_with_vehicle_item(*, item_inside: bool):
    package = _synthetic_package()
    scene = package.scenes[0]
    placements = dict(scene.metadata.item_placements)
    placements["lamp"] = placements["lamp"].model_copy(update={"parent": "car" if item_inside else "room"})
    scene = scene.model_copy(update={"metadata": scene.metadata.model_copy(update={"item_placements": placements})})
    items = tuple(
        item.model_copy(
            update=(
                {"name": "a green skiff"}
                if item.id == "car"
                else {"name": "helm seat"}
                if item.id == "driver_seat"
                else {"name": "brass lantern"}
                if item.id == "lamp"
                else {}
            )
        )
        for item in package.world.items
    )
    return package.model_copy(update={"scenes": (scene,), "world": package.world.model_copy(update={"items": items})})


def _synthetic_boarding_prompt(*, item_inside: bool) -> str:
    package = _synthetic_package_with_vehicle_item(item_inside=item_inside)
    state = RuntimeState.bootstrap(package)
    world = world_for(package, state.facts)
    assert world.move("hero", "yard").ok
    assert world.move("held_key", "room").ok
    provider = build_capture_provider(state)
    provider.semantic_ask = lambda state, questions: _scripted_jev(state, questions, board=True, only_board=False)
    provider._request_item_facts = lambda _payload: {"refers": [], "same_as": {}}
    captured: list[str] = []

    def dispatch(_system: str, user: dict[str, object]) -> dict[str, object]:
        captured.append(provider._section_user_prompt(user))
        return {"segments": [{"kind": "narration", "text": "Offline probe narration."}], "selected_knowledge_ids": []}

    provider._dispatch = dispatch

    class ReplayCapture(WorldCapture):
        def before_turn(self, command: str) -> dict[str, object]:
            record = super().before_turn(command)
            self.provider.command_consumed = False
            return record

    engine = RuntimeEngine(
        state,
        provider,
        capture=ReplayCapture(
            provider,
            lambda state, questions: _scripted_jev(state, questions, board=True, only_board=False),
        ),
    )
    engine.turn("enter the green skiff")
    assert captured
    return captured[-1]


def _direct_prompt(state: RuntimeState, command: str) -> str:
    provider = build_capture_provider(state)
    provider._request_item_facts = lambda _payload: {"refers": [], "same_as": {}}
    provider._selected_names = list(provider.item_facts)
    return provider._section_user_prompt(provider.assemble_turn_prompt(command)["context"])


def test_committed_head_out_route_has_reach_fact_and_no_raw_player_command() -> None:
    user = _boarding_prompt("head out to the truck")
    where = "- Kristin is in the driver's seat of Kristin's truck, outside the house."
    reach = "- Kristin can reach anything inside Kristin's truck from the driver's seat."
    assert f"SCENE:\n{where}\n{reach}" in user
    assert "Already done:" in user
    assert "Kristin. Place: driver's seat." in user
    assert "- head out to the truck" not in user.split("PLAYER:", 1)[1]


def test_committed_go_to_route_has_reach_fact_and_no_raw_player_command() -> None:
    user = _boarding_prompt("go to the truck")
    assert (
        "SCENE:\n- Kristin is in the driver's seat of Kristin's truck, outside the house.\n"
        "- Kristin can reach anything inside Kristin's truck from the driver's seat."
    ) in user
    assert "- go to the truck" not in user.split("PLAYER:", 1)[1]


def test_unboarded_turn_keeps_raw_command_without_boarding_facts() -> None:
    user = _boarding_prompt("go to the truck", board=False)
    player = user.split("PLAYER:", 1)[1]
    assert "- go to the truck" in player
    assert "Already done:" not in user
    assert "can reach anything inside" not in user


def test_already_aboard_turn_keeps_raw_command_line() -> None:
    engine, captured = _product_replay(
        board=True,
        only_board=True,
        force_narrator_for=("head out to the truck",),
    )
    engine.turn("open the drawer")
    engine.turn("feel in the gap")
    engine.turn("head out to the truck")
    engine.turn("get in the truck")

    assert captured
    user = captured[-1]["user"]
    assert "- get in the truck" in user.split("PLAYER:", 1)[1]
    assert "Already done:" not in user


def test_synthetic_vehicle_names_build_reach_fact_and_drop_boarding_command() -> None:
    user = _synthetic_boarding_prompt(item_inside=True)
    assert (
        "SCENE:\n- Ari is in the helm seat of a green skiff, the yard.\n"
        "- Ari can reach anything inside a green skiff from the helm seat."
    ) in user
    assert "- enter the green skiff" not in user.split("PLAYER:", 1)[1]


def test_vehicle_with_nothing_inside_has_no_reach_fact() -> None:
    user = _synthetic_boarding_prompt(item_inside=False)
    assert "can reach anything inside" not in user


def test_unseated_protagonist_has_no_reach_fact() -> None:
    state = RuntimeState.bootstrap(PACKAGE)
    assert world_for(PACKAGE, state.facts).move("kristin", "outside_house").ok
    user = _direct_prompt(state, "look around")
    assert "can reach anything inside" not in user
