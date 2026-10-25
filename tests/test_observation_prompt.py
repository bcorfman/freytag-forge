from __future__ import annotations

import importlib.util
import re
import socket
from pathlib import Path

import pytest

from storygame.runtime.capture import WorldCapture, build_capture_provider
from storygame.runtime.cloudflare import CloudflareTurnProvider
from storygame.runtime.observation import ObservationRequest
from storygame.runtime.world_model import world_for
from storygame.story_package.loader import load_story_package

ROOT = Path(__file__).parents[1]
PACKAGE_ROOT = ROOT / "data/stories/continuity-initiative"
PACKAGE = load_story_package(PACKAGE_ROOT)
PROBE_PATH = ROOT / "scripts/ringer/transcript_1a/boarding_probe.py"
PROBE_SPEC = importlib.util.spec_from_file_location("boarding_probe", PROBE_PATH)
assert PROBE_SPEC is not None and PROBE_SPEC.loader is not None
boarding_probe = importlib.util.module_from_spec(PROBE_SPEC)
PROBE_SPEC.loader.exec_module(boarding_probe)


@pytest.fixture(autouse=True)
def no_sockets(monkeypatch: pytest.MonkeyPatch) -> None:
    def fail_socket(*_args: object, **_kwargs: object) -> None:
        raise AssertionError("network access is forbidden in observation prompt tests")

    monkeypatch.setattr(socket, "socket", fail_socket)


def _capture(
    command: str,
    request: ObservationRequest | None,
    *,
    move_laptop_to_kristin: bool = False,
) -> tuple[str, object, object]:
    state = boarding_probe._state_at(PACKAGE, "outside_house")
    with boarding_probe._stub_jev(), boarding_probe._stub_item_facts():
        provider = build_capture_provider(state)
        provider.observation_request = request
        world = world_for(PACKAGE, state.facts)
        if move_laptop_to_kristin:
            assert world.move("kristin_laptop", "kristin").ok

        captured: dict[str, str] = {}

        def dispatch(system: str, user: dict[str, object]) -> dict[str, object]:
            captured["system"] = system
            captured["user"] = provider._section_user_prompt(user)
            return {"segments": [], "selected_knowledge_ids": []}

        provider._dispatch = dispatch
        ask = boarding_probe._boarding_ask
        if request is not None and request.kind == "none":

            def ask(_state, questions):
                return {question: {"noul": 0.0} for question in questions}

        WorldCapture(provider, ask).before_turn(command)
        if request is None:
            CloudflareTurnProvider.__call__(provider, command)
        else:
            provider(command)

    assert "user" in captured
    return captured["user"], provider, world_for(PACKAGE, state.facts)


def test_observation_request_is_off_by_default_byte_for_byte() -> None:
    expected = boarding_probe._control_prompt(PACKAGE, "outside_house", "Go to the truck.")["user"]
    actual, _provider, _world = _capture("Go to the truck.", None)

    assert actual == expected
    assert "- Just before this:" in actual
    assert "THINGS:\n- Kristin. Place: driver's seat." in actual
    assert "Kristin's laptop" not in actual.split("THINGS:", 1)[1].split("CONSTRAINTS:", 1)[0]


def test_observation_request_projects_entering_context_and_calls_narrator() -> None:
    user, provider, _world = _capture(
        "Enter the truck.",
        ObservationRequest("Enter the truck.", "enter", "kristin_truck"),
    )

    assert provider.last_turn_engine_text is False
    assert "- Kristin's laptop. Place: passenger seat." in user
    assert "- Enter the truck." in user
    assert user.count("- Already done:") == 1
    assert "Already done: Kristin sat down in the driver's seat." in user
    assert "- Show these in your reply: Kristin's laptop." in user


def test_observation_request_uses_current_holder_not_stale_place() -> None:
    user, _provider, _world = _capture(
        "Enter the truck.",
        ObservationRequest("Enter the truck.", "enter", "kristin_truck"),
        move_laptop_to_kristin=True,
    )

    assert "- Kristin's laptop. Held by:" in user
    assert "Kristin's laptop. Place: passenger seat." not in user


def test_observation_request_never_exposes_hidden_story_item() -> None:
    user, _provider, _world = _capture(
        "Enter the truck.",
        ObservationRequest("Enter the truck.", "enter", "kristin_truck"),
    )

    assert "Michelle's memory card" not in user
    assert "memory_card" not in user


def test_non_observation_action_adds_no_projection_lines() -> None:
    user, _provider, _world = _capture(
        "Approach the truck.",
        ObservationRequest("Approach the truck.", "none", "kristin_truck"),
    )

    assert "Kristin's laptop" not in user
    assert "Show these in your reply:" not in user


def test_observation_prompt_is_deterministic() -> None:
    request = ObservationRequest("Enter the truck.", "enter", "kristin_truck")

    first, _provider, _world = _capture("Enter the truck.", request)
    second, _provider, _world = _capture("Enter the truck.", request)

    assert first == second


def test_observation_added_lines_do_not_contain_entity_ids() -> None:
    user, _provider, world = _capture(
        "Enter the truck.",
        ObservationRequest("Enter the truck.", "enter", "kristin_truck"),
    )
    added_lines = [
        line for line in user.splitlines() if "Kristin's laptop" in line or "Show these in your reply:" in line
    ]

    for entity_id in world.entity_ids():
        assert all(re.search(rf"(?<!\w){re.escape(entity_id)}(?!\w)", line) is None for line in added_lines)


def test_observation_request_excludes_boarding_notice_from_completed_actions() -> None:
    user, _provider, _world = _capture(
        "Enter the truck.",
        ObservationRequest("Enter the truck.", "enter", "kristin_truck"),
    )

    assert "- Already done: Kristin sat down in the driver's seat." in user
    assert (
        "Already done: Kristin sat down in the driver's seat. Kristin's laptop sat on the passenger seat." not in user
    )
    assert "- Kristin's laptop. Place: passenger seat." in user


def test_default_prompt_keeps_boarding_notice_in_completed_actions() -> None:
    user, _provider, _world = _capture("Enter the truck.", None)

    assert (
        "- Just before this: Kristin sat down in the driver's seat. Kristin's laptop sat on the passenger seat." in user
    )


def test_observation_prompt_without_notice_steps_keeps_only_the_seat_step(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from storygame.runtime import capture as capture_module
    from storygame.runtime.seating import SeatingResult

    original_board_vehicle = capture_module.board_vehicle

    def board_without_notice(*args: object, **kwargs: object) -> SeatingResult:
        result = original_board_vehicle(*args, **kwargs)
        return SeatingResult(result.command, (result.steps[0],), result.asked, result.issues, result.command_consumed)

    monkeypatch.setattr(capture_module, "board_vehicle", board_without_notice)
    user, _provider, _world = _capture(
        "Enter the truck.",
        ObservationRequest("Enter the truck.", "enter", "kristin_truck"),
    )

    assert "- Already done: Kristin sat down in the driver's seat." in user
    assert (
        "- Already done: Kristin sat down in the driver's seat. Kristin's laptop sat on the passenger seat." not in user
    )


def test_seating_result_notice_steps_are_steps_and_default_to_empty() -> None:
    from storygame.runtime.seating import SeatingResult

    notice = "Kristin's laptop sat on the passenger seat."
    result = SeatingResult(
        "Kristin sat down in the driver's seat. " + notice,
        ("Kristin sat down in the driver's seat.", notice),
        True,
        (),
        notice_steps=(notice,),
    )

    assert set(result.notice_steps) <= set(result.steps)
    assert SeatingResult("command", (), False, ()).notice_steps == ()


def _capture_drawer_observation_prompt(
    tmp_path,
    *,
    contents_complete: bool,
    move_card: bool = False,
    keep_item_in_drawer: bool = False,
    request: ObservationRequest | None,
) -> tuple[str, object]:
    import shutil

    import yaml

    from storygame.runtime.capture import WorldCapture, build_capture_provider
    from storygame.runtime.facts import Fact
    from storygame.runtime.world_model import apply_world_effects
    from storygame.story_package.loader import load_story_package

    root = tmp_path / "story"
    shutil.copytree(PACKAGE_ROOT, root)
    world_path = root / "world.yaml"
    world_data = yaml.safe_load(world_path.read_text(encoding="utf-8"))
    drawer = next(item for item in world_data["items"] if item["id"] == "michelle_drawer")
    if contents_complete:
        drawer["contents_complete"] = True
    world_path.write_text(yaml.safe_dump(world_data, sort_keys=False), encoding="utf-8")

    package = load_story_package(root)
    state = boarding_probe._state_at(package, "kitchen")
    with boarding_probe._stub_jev(), boarding_probe._stub_item_facts():
        provider = build_capture_provider(state)
        provider.observation_request = request
        world = world_for(package, state.facts)
        if move_card:
            state.facts.assert_fact(Fact(predicate="memory_card_recovered", subject="story", value="true"))
            apply_world_effects(package, state.facts)
            assert world.parent("memory_card") == "kristin"
        if keep_item_in_drawer:
            assert world.move("michelle_phone", "michelle_drawer").ok

        captured: dict[str, str] = {}

        def dispatch(system: str, user: dict[str, object]) -> dict[str, object]:
            captured["system"] = system
            captured["user"] = provider._section_user_prompt(user)
            return {"segments": [], "selected_knowledge_ids": []}

        provider._dispatch = dispatch
        WorldCapture(provider, boarding_probe._boarding_ask).before_turn("Search beneath the drawer.")
        if request is None:
            CloudflareTurnProvider.__call__(provider, "Search beneath the drawer.")
        else:
            provider("Search beneath the drawer.")

    assert "user" in captured
    return captured["user"], package


def test_complete_empty_drawer_scope_gets_empty_constraint_after_card_is_taken(tmp_path) -> None:
    user, _package = _capture_drawer_observation_prompt(
        tmp_path,
        contents_complete=True,
        move_card=True,
        request=ObservationRequest("Search beneath the drawer.", "look", "michelle_drawer"),
    )

    assert "- Nothing is left in or under the drawer. Searching the drawer finds nothing." in user
    assert "holds nothing else the player can find" not in user
    assert "- Michelle's memory card. Held by: Kristin." in user
    assert "- Michelle's memory card. Place: drawer." not in user


def test_unmarked_empty_drawer_scope_gets_no_empty_constraint(tmp_path) -> None:
    user, _package = _capture_drawer_observation_prompt(
        tmp_path,
        contents_complete=False,
        move_card=True,
        request=ObservationRequest("Search beneath the drawer.", "look", "michelle_drawer"),
    )

    assert "- Nothing is left in or under the drawer. Searching the drawer finds nothing." not in user


def test_complete_drawer_scope_with_known_item_gets_no_empty_constraint(tmp_path) -> None:
    user, _package = _capture_drawer_observation_prompt(
        tmp_path,
        contents_complete=True,
        keep_item_in_drawer=True,
        request=ObservationRequest("Search beneath the drawer.", "look", "michelle_drawer"),
    )

    assert "- Michelle's phone. Place: drawer." in user
    assert "- Nothing is left in or under the drawer. Searching the drawer finds nothing." not in user


def test_complete_drawer_scope_does_not_change_default_prompt(tmp_path) -> None:
    declared_user, declared_package = _capture_drawer_observation_prompt(
        tmp_path,
        contents_complete=True,
        request=None,
    )
    expected = boarding_probe._control_prompt(declared_package, "kitchen", "Search beneath the drawer.")["user"]

    assert declared_user == expected
