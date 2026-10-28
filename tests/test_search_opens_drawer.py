from __future__ import annotations

import pytest

from storygame.runtime.capture import WorldCapture, build_capture_provider
from storygame.runtime.cloudflare import CloudflareTurnProvider
from storygame.runtime.item_facts import ItemFactsProvider
from storygame.runtime.observation import ObservationRequest
from storygame.runtime.state import RuntimeState
from storygame.runtime.world_model import world_for
from tests.test_drawer_gap_nudge import CARD_FIND, NUDGE, _card_find_state, _gap_state, _handoff
from tests.test_observation_preview import _synthetic_package


@pytest.fixture(autouse=True)
def fake_worker_url(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("CLOUDFLARE_WORKER_URL", "https://w.example")


def _real_capture(
    monkeypatch: pytest.MonkeyPatch,
    state,
    command: str,
    answers: dict[str, bool | None],
):
    monkeypatch.setattr(
        CloudflareTurnProvider,
        "_request_item_facts",
        lambda _self, _payload: {"refers": ["drawer"], "same_as": {}},
    )
    provider = build_capture_provider(state)
    calls: list[str] = []

    def ask(_state: object, questions: dict[str, object]) -> dict[str, dict[str, float]]:
        calls.extend(key for key in questions if key in {"searches_underneath", "opens_container"})
        return {key: {"noul": 1.0 if answers[key] else 0.0} for key in questions if answers.get(key) is not None}

    record = WorldCapture(provider, ask).before_turn(command)
    return provider, record, calls


def test_search_drawer_opens_it_and_keeps_gap_nudge(monkeypatch: pytest.MonkeyPatch) -> None:
    command = "Search the drawer."
    state = _gap_state()
    provider, record, calls = _real_capture(
        monkeypatch,
        state,
        command,
        {"searches_underneath": False, "opens_container": True},
    )
    world = world_for(state.package, state.facts)

    assert calls == ["searches_underneath", "opens_container"]
    assert provider.observation_request == ObservationRequest(command, "open", "michelle_drawer")
    assert world.axis_values("michelle_drawer").get("open") == "open"
    assert record["engine_opened"] is True
    context = provider._observation_context()
    assert context is not None
    assert set(("binder clips", "pens", "spare batteries", "stapler")) <= set(context.required)
    handoff = _handoff(state, command)
    assert handoff is not None
    assert handoff.candidate.id == NUDGE


def test_search_under_drawer_stays_closed_and_finds_card(monkeypatch: pytest.MonkeyPatch) -> None:
    command = "Search under the drawer."
    state = _card_find_state()
    provider, record, calls = _real_capture(monkeypatch, state, command, {"searches_underneath": True})
    world = world_for(state.package, state.facts)

    assert calls == ["searches_underneath"]
    assert "opens_container" not in calls
    assert provider.observation_request == ObservationRequest(command, "under", "michelle_drawer")
    assert world.axis_values("michelle_drawer").get("open") == "closed"
    assert record["engine_opened"] is False
    handoff = _handoff(state, command)
    assert handoff is not None
    assert handoff.candidate.id == CARD_FIND
    assert handoff.candidate.id != NUDGE


def test_inspect_drawer_stays_a_closed_look(monkeypatch: pytest.MonkeyPatch) -> None:
    command = "Inspect the drawer."
    state = _gap_state()
    provider, record, calls = _real_capture(
        monkeypatch,
        state,
        command,
        {"searches_underneath": False, "opens_container": False},
    )
    world = world_for(state.package, state.facts)

    assert calls == ["searches_underneath", "opens_container"]
    assert provider.observation_request == ObservationRequest(command, "look", "michelle_drawer")
    assert world.axis_values("michelle_drawer").get("open") == "closed"
    assert record["engine_opened"] is False


def test_unanswered_container_questions_keep_a_closed_look(monkeypatch: pytest.MonkeyPatch) -> None:
    command = "Inspect the drawer."
    state = _gap_state()
    provider, record, calls = _real_capture(
        monkeypatch,
        state,
        command,
        {"searches_underneath": None, "opens_container": None},
    )
    world = world_for(state.package, state.facts)

    assert calls == ["searches_underneath", "opens_container"]
    assert provider.observation_request == ObservationRequest(command, "look", "michelle_drawer")
    assert world.axis_values("michelle_drawer").get("open") == "closed"
    assert record["engine_opened"] is False


def test_open_drawer_still_uses_the_engine_open_step(monkeypatch: pytest.MonkeyPatch) -> None:
    command = "Open the drawer."
    state = _gap_state()
    provider, record, calls = _real_capture(
        monkeypatch,
        state,
        command,
        {"searches_underneath": False, "opens_container": True},
    )
    world = world_for(state.package, state.facts)

    assert calls == ["searches_underneath", "opens_container"]
    assert provider.observation_request == ObservationRequest(command, "open", "michelle_drawer")
    assert world.axis_values("michelle_drawer").get("open") == "open"
    assert record["engine_opened"] is True


def _synthetic_container_capture(
    monkeypatch: pytest.MonkeyPatch,
    command: str,
    answers: dict[str, bool | None],
):
    package = _synthetic_package()
    items = list(package.world.items)
    items[0] = items[0].model_copy(update={"kind": "container", "openable": True, "open": False})
    package = package.model_copy(update={"world": package.world.model_copy(update={"items": items})})
    state = RuntimeState.bootstrap(package)
    provider = ItemFactsProvider(
        worker_url="",
        token="",
        state=state,
        item_facts={},
        mode="single_call",
        seed_from_package=True,
        held_by=True,
    )
    monkeypatch.setattr(
        CloudflareTurnProvider,
        "_request_item_facts",
        lambda _self, _payload: {"refers": ["survey tray"], "same_as": {}},
    )
    calls: list[str] = []

    def ask(_state: object, questions: dict[str, object]) -> dict[str, dict[str, float]]:
        calls.extend(key for key in questions if key in {"searches_underneath", "opens_container"})
        return {key: {"noul": 1.0 if answers[key] else 0.0} for key in questions if answers.get(key) is not None}

    record = WorldCapture(provider, ask).before_turn(command)
    return state, provider, record, calls


@pytest.mark.parametrize(
    ("answers", "expected_kind", "expected_open", "expected_engine_opened"),
    (
        ({"searches_underneath": True, "opens_container": True}, "under", "closed", False),
        ({"searches_underneath": False, "opens_container": True}, "open", "open", True),
    ),
)
def test_synthetic_openable_container_obeys_under_first(
    monkeypatch: pytest.MonkeyPatch,
    answers: dict[str, bool | None],
    expected_kind: str,
    expected_open: str,
    expected_engine_opened: bool,
) -> None:
    command = "Search under the survey tray."
    state, provider, record, calls = _synthetic_container_capture(monkeypatch, command, answers)
    world = world_for(state.package, state.facts)

    if answers["searches_underneath"]:
        assert calls == ["searches_underneath"]
    else:
        assert calls == ["searches_underneath", "opens_container"]
    assert provider.observation_request == ObservationRequest(command, expected_kind, "tray")
    assert world.axis_values("tray").get("open") == expected_open
    assert record["engine_opened"] is expected_engine_opened
