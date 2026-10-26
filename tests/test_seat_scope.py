from __future__ import annotations

import importlib.util
from pathlib import Path

import pytest

from storygame.runtime.capture import WorldCapture, build_capture_provider
from storygame.runtime.observation import ObservationRequest
from storygame.runtime.world_model import world_for
from storygame.story_package.loader import load_story_package

ROOT = Path(__file__).parents[1]
PACKAGE = load_story_package(ROOT / "data/stories/continuity-initiative")
PROBE_PATH = ROOT / "scripts/ringer/transcript_1a/boarding_probe.py"
PROBE_SPEC = importlib.util.spec_from_file_location("seat_scope_boarding_probe", PROBE_PATH)
assert PROBE_SPEC is not None and PROBE_SPEC.loader is not None
boarding_probe = importlib.util.module_from_spec(PROBE_SPEC)
PROBE_SPEC.loader.exec_module(boarding_probe)

PASSENGER_SEAT = "truck_passenger_seat"
EMPTY_LINE = "- Nothing is left in or under the passenger seat. Searching the passenger seat finds nothing."


@pytest.fixture(autouse=True)
def fake_worker_url(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("CLOUDFLARE_WORKER_URL", "https://w.example")


def _capture_prompt(laptop_parent: str, focus: str) -> str:
    state = boarding_probe._state_at(PACKAGE, "outside_house")
    request = ObservationRequest(f"Look at the {focus}.", "look", focus)
    with boarding_probe._stub_jev(), boarding_probe._stub_item_facts():
        provider = build_capture_provider(state)
        provider.observe_automatically = False
        provider.observation_request = request
        world = world_for(PACKAGE, state.facts)
        assert world.move("kristin_laptop", laptop_parent).ok

        captured: dict[str, str] = {}

        def dispatch(_system: str, user: dict[str, object]) -> dict[str, object]:
            captured["user"] = provider._section_user_prompt(user)
            return {"segments": [], "selected_knowledge_ids": []}

        provider._dispatch = dispatch
        WorldCapture(provider, boarding_probe._boarding_ask).before_turn(request.action)
        provider(request.action)

    assert "user" in captured
    return captured["user"]


def test_only_passenger_seat_is_declared_complete() -> None:
    state = boarding_probe._state_at(PACKAGE, "outside_house")
    world = world_for(PACKAGE, state.facts)

    assert world.contents_complete(PASSENGER_SEAT) is True
    for entity_id in world.entity_ids():
        if entity_id != PASSENGER_SEAT:
            assert world.contents_complete(entity_id) is False


def test_empty_passenger_seat_gets_empty_constraint() -> None:
    user = _capture_prompt("kristin", PASSENGER_SEAT)

    assert user.count(EMPTY_LINE) == 1


def test_passenger_seat_with_laptop_has_required_mention_without_empty_constraint() -> None:
    user = _capture_prompt(PASSENGER_SEAT, PASSENGER_SEAT)

    assert EMPTY_LINE not in user
    assert "- Show these in your reply: Kristin's laptop." in user


@pytest.mark.parametrize("focus", ("truck_driver_seat", "kristin_truck"))
def test_other_truck_scopes_never_get_passenger_seat_empty_constraint(focus: str) -> None:
    user = _capture_prompt("kristin", focus)

    assert EMPTY_LINE not in user
