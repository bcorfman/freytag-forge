from __future__ import annotations

import importlib.util
from pathlib import Path

import pytest

from storygame.runtime.capture import WorldCapture, build_capture_provider
from storygame.runtime.cloudflare import CloudflareTurnProvider
from storygame.runtime.observation import ObservationRequest, build_observation_context
from storygame.runtime.seating import board_vehicle
from storygame.runtime.world_model import world_for
from storygame.story_package.loader import load_story_package
from tests.test_boarding import _synthetic_vehicle_world

ROOT = Path(__file__).parents[1]
PACKAGE = load_story_package(ROOT / "data/stories/continuity-initiative")
PROBE_PATH = ROOT / "scripts/ringer/transcript_1a/boarding_probe.py"
PROBE_SPEC = importlib.util.spec_from_file_location("observation_mode_boarding_probe", PROBE_PATH)
assert PROBE_SPEC is not None and PROBE_SPEC.loader is not None
boarding_probe = importlib.util.module_from_spec(PROBE_SPEC)
PROBE_SPEC.loader.exec_module(boarding_probe)


@pytest.fixture(autouse=True)
def fake_worker_url(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("CLOUDFLARE_WORKER_URL", "https://w.example")


def _state_at(place_id: str, *, already_aboard: bool = False):
    state = boarding_probe._state_at(PACKAGE, place_id)
    if already_aboard:
        assert world_for(PACKAGE, state.facts).move("kristin", "truck_driver_seat").ok
    return state


def _run(
    monkeypatch: pytest.MonkeyPatch,
    command: str,
    *,
    place_id: str = "outside_house",
    match_refers: tuple[str, ...] = (),
    answers: dict[str, bool | None] | None = None,
    observe_automatically: bool = True,
    already_aboard: bool = False,
    hand_set_request: ObservationRequest | None = None,
):
    answers = answers or {}
    monkeypatch.setattr(
        CloudflareTurnProvider,
        "_request_item_facts",
        lambda _self, _payload: {"refers": list(match_refers), "same_as": {}},
    )
    state = _state_at(place_id, already_aboard=already_aboard)
    provider = build_capture_provider(state)
    provider.observe_automatically = observe_automatically
    provider.observation_request = hand_set_request
    captured: dict[str, str] = {}

    def dispatch(_system: str, user: dict[str, object]) -> dict[str, object]:
        captured["user"] = provider._section_user_prompt(user)
        return {"segments": [], "selected_knowledge_ids": []}

    provider._dispatch = dispatch

    def ask(_state: object, questions: dict[str, object]) -> dict[str, dict[str, float]]:
        return {
            key: {"noul": 1.0 if answers.get(key, False) else 0.0} for key in questions if answers.get(key) is not None
        }

    record = WorldCapture(provider, ask).before_turn(command)
    provider(command)
    assert "user" in captured
    return record, captured["user"], provider


def test_boarding_turn_sets_enter_request_and_calls_narrator(monkeypatch: pytest.MonkeyPatch) -> None:
    record, user, provider = _run(
        monkeypatch,
        "Enter the truck.",
        answers={"boards_vehicle": True, "only_boards_vehicle": True},
    )

    assert record["boarding_command_consumed"] is True
    assert provider.observation_request == ObservationRequest("Enter the truck.", "enter", "kristin_truck")
    assert provider.last_turn_engine_text is False
    assert "- Kristin's laptop. Place: passenger seat." in user
    assert "- Already done: Kristin sat down in the driver's seat." in user
    assert "Kristin's laptop sat on the passenger seat." not in user.split("Already done:", 1)[1]


def test_already_aboard_turn_is_narrated_without_engine_step(monkeypatch: pytest.MonkeyPatch) -> None:
    record, user, provider = _run(
        monkeypatch,
        "Get in the truck.",
        answers={"boards_vehicle": True, "only_boards_vehicle": True},
        already_aboard=True,
    )

    assert record["boarding_command_consumed"] is False
    assert provider.observation_request == ObservationRequest("Get in the truck.", "enter", "kristin_truck")
    assert provider.last_turn_engine_text is False
    assert "is already in the" not in user
    assert "Just before this:" not in user
    assert "Already done:" not in user


@pytest.mark.parametrize(
    ("answer", "kind"),
    ((True, "open"), (None, "look")),
)
def test_container_observation_kind_uses_open_question(
    monkeypatch: pytest.MonkeyPatch, answer: bool | None, kind: str
) -> None:
    _record, _user, provider = _run(
        monkeypatch,
        "Open the drawer.",
        place_id="kitchen",
        match_refers=("drawer",),
        answers={"opens_container": answer},
    )

    assert provider.observation_request == ObservationRequest("Open the drawer.", kind, "michelle_drawer")


def test_character_only_match_keeps_default_prompt(monkeypatch: pytest.MonkeyPatch) -> None:
    _record, automatic_user, automatic_provider = _run(
        monkeypatch,
        "Talk to Kristin.",
        match_refers=("Kristin",),
    )
    _record, legacy_user, legacy_provider = _run(
        monkeypatch,
        "Talk to Kristin.",
        match_refers=("Kristin",),
        observe_automatically=False,
    )

    assert automatic_provider.observation_request is None
    assert automatic_user == legacy_user
    assert legacy_provider.observation_request is None


def test_observation_request_is_cleared_before_each_turn(monkeypatch: pytest.MonkeyPatch) -> None:
    state = _state_at("outside_house")
    provider = build_capture_provider(state)
    provider.observe_automatically = True
    replies = iter(({"refers": ["Kristin's laptop"], "same_as": {}}, {"refers": ["Kristin"], "same_as": {}}))
    monkeypatch.setattr(CloudflareTurnProvider, "_request_item_facts", lambda _self, _payload: next(replies))

    def ask(_state, questions):
        return {key: {"noul": 0.0} for key in questions}

    capture = WorldCapture(provider, ask)
    capture.before_turn("Examine my laptop.")
    assert provider.observation_request == ObservationRequest("Examine my laptop.", "look", "kristin_laptop")

    capture.before_turn("Talk to Kristin.")
    assert provider.observation_request is None


def test_manual_request_survives_when_automatic_observation_is_off(monkeypatch: pytest.MonkeyPatch) -> None:
    request = ObservationRequest("Examine my laptop.", "look", "kristin_laptop")
    _record, _user, provider = _run(
        monkeypatch,
        "Talk to Kristin.",
        match_refers=("Kristin",),
        observe_automatically=False,
        hand_set_request=request,
    )

    assert provider.observation_request == request


def test_synthetic_vehicle_and_observation_use_their_own_names() -> None:
    package, world = _synthetic_vehicle_world()
    result = board_vehicle(world, package, "Get into the boat 0.", lambda *_: True)
    assert result.vehicle_id == "boat_0"

    context = build_observation_context(
        world,
        "player",
        ObservationRequest("Inspect the boat 0.", "look", "boat_0"),
        completed_actions=result.steps[:1],
    )
    assert "rope 0" in context.required
