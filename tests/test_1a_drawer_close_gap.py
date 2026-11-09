from __future__ import annotations

import json
from pathlib import Path

import pytest
import yaml

from storygame.runtime.candidate_matcher import uniquely_matched_authored_handoff
from storygame.runtime.cloudflare import CloudflareTurnProvider
from storygame.runtime.engine import RuntimeEngine
from storygame.runtime.facts import Fact
from storygame.runtime.knowledge import KnowledgeProjector
from storygame.runtime.state import RuntimeState
from storygame.runtime.world_model import world_for
from storygame.story_package.loader import load_story_package
from tests.test_observation_mode import _state_at

PACKAGE_ROOT = Path("data/stories/continuity-initiative")
PACKAGE = load_story_package(PACKAGE_ROOT)
OPEN_IDS = ("k_sl_1a_f_r1",)  # k_sl_1a_b_r0w is the witnessed card recovery, not an open-drawer reply
OPEN_TEXT = "The drawer slides out. It holds a stapler, spare batteries, pens, and binder clips."
CLOSE_ID = "k_sl_1a_f_r3"
CLOSE_TEXT = (
    "Kristin slides the drawer shut. It rides high in its frame. A thin gap beneath its lower edge is wide enough "
    "for Kristin's fingers."
)
GAP_FACT = "drawer_gap_pointed_out"
OPENED_FACT = "drawer_opened"
CARD_FACT = "memory_card_recovered"
STORYLET = "SL-1A-F"
CARD_FIND = "k_sl_1a_b_r0"
RAM_EVENT = "reyes_rams_drawer_1a"
RAM_TEXT = (
    "Reyes tugs at the workstation drawer. It sticks. Frustrated, he rams it back into place with the heel of his "
    "hand, and it sits high in its frame. A thin gap shows beneath its lower edge, wide enough for Kristin's fingers. "
    "Reyes never looks down. Only Kristin sees it."
)
BARE_DRAWER_COMMANDS = (
    "Inspect the drawer.",
    "Examine the drawer.",
    "Search the drawer.",
    "Check the drawer.",
    "Look at the drawer.",
    "Study the drawer.",
    "Examine the carved initials.",
    "Examine my initials.",
)
COMMANDS = (
    "Turn on the phone.",
    "Unlock the phone.",
    "Type in the password.",
    "Type the password into Michelle's phone.",
    "Turn off the phone.",
    "Greet the officer.",
    "Ask the officer where Dr. McGehee is.",
)


def _handoff(state: RuntimeState, command: str):
    projection = KnowledgeProjector().project(state, "player", command)
    return uniquely_matched_authored_handoff(command, projection.reveal_universe)


def _gap_state() -> RuntimeState:
    state = _state_at("kitchen")
    state.active_event_ids.add(STORYLET)
    return state


def _set_fact(state: RuntimeState, predicate: str, value: bool) -> None:
    state.facts.assert_fact(Fact(predicate=predicate, subject="story", value=str(value).lower()))


def _true_fact_ids(knowledge_id: str) -> set[str]:
    knowledge = next(item for item in PACKAGE.knowledge.knowledge if item.id == knowledge_id)
    return {operation.fact_id for operation in knowledge.establishes}


def test_opening_the_drawer_shows_contents_and_no_gap() -> None:
    entries = {item.id: item for item in PACKAGE.knowledge.knowledge}
    for knowledge_id in OPEN_IDS:
        entry = entries[knowledge_id]
        assert entry.delivery_text == OPEN_TEXT
        assert "gap" not in entry.delivery_text.lower()
        assert "lower edge" not in entry.delivery_text.lower()
        assert OPENED_FACT in _true_fact_ids(knowledge_id)
        assert GAP_FACT not in _true_fact_ids(knowledge_id)


@pytest.mark.parametrize("command", ("Close the drawer.", "Shut the drawer.", "Push the drawer closed."))
def test_closing_the_drawer_after_opening_finds_the_gap(command: str) -> None:
    state = _gap_state()
    _set_fact(state, OPENED_FACT, True)
    _set_fact(state, CARD_FACT, False)
    handoff = _handoff(state, command)
    assert handoff is not None
    assert handoff.candidate.id == CLOSE_ID
    assert handoff.delivery_text == CLOSE_TEXT
    assert _true_fact_ids(CLOSE_ID) == {GAP_FACT}


def test_closing_without_opening_finds_nothing() -> None:
    state = _gap_state()
    _set_fact(state, OPENED_FACT, False)
    assert any(item.id == CLOSE_ID for item in PACKAGE.knowledge.knowledge)
    handoff = _handoff(state, "Close the drawer.")
    candidate_ids = {
        candidate.id for candidate in KnowledgeProjector().project(state, "player", "Close the drawer.").candidates
    }
    assert handoff is None or handoff.candidate.id != CLOSE_ID
    assert CLOSE_ID not in candidate_ids


def test_closing_after_the_card_is_recovered_finds_nothing_control() -> None:
    state = _gap_state()
    _set_fact(state, OPENED_FACT, True)
    _set_fact(state, CARD_FACT, True)
    handoff = _handoff(state, "Close the drawer.")
    assert handoff is None or handoff.candidate.id != CLOSE_ID


@pytest.mark.parametrize("command", BARE_DRAWER_COMMANDS)
def test_bare_examine_gives_no_gap_before_the_drawer_is_closed(command: str) -> None:
    before = _gap_state()
    _set_fact(before, GAP_FACT, False)
    handoff = _handoff(before, command)
    assert handoff is None or handoff.candidate.id != "k_sl_1a_f_r2"
    after = _gap_state()
    _set_fact(after, GAP_FACT, True)
    handoff = _handoff(after, command)
    assert handoff is not None
    assert handoff.candidate.id == "k_sl_1a_f_r2"


@pytest.mark.parametrize("command", ("Search under the drawer.", "Feel beneath the drawer."))
def test_searching_under_the_drawer_still_finds_the_card_control(command: str) -> None:
    state = _gap_state()
    state.active_event_ids.add("SL-1A-E")
    _set_fact(state, OPENED_FACT, False)
    handoff = _handoff(state, command)
    assert handoff is not None
    assert handoff.candidate.id == CARD_FIND


def test_drawer_opened_is_declared_everywhere_and_the_storylet_has_three_realizations() -> None:
    routes = yaml.safe_load((PACKAGE_ROOT / "storylet-routes.yaml").read_text(encoding="utf-8"))
    route_by_id = {route["id"]: route for route in routes["storylets"]}
    assert OPENED_FACT in {fact.id for fact in PACKAGE.knowledge.facts}
    assert OPENED_FACT in set(PACKAGE.world.facts)
    assert OPENED_FACT in {fact["id"] for fact in routes["new_fact_ids"]}
    assert [option["id"] for option in route_by_id[STORYLET]["realization_options"]] == [
        "SL-1A-F-R1",
        "SL-1A-F-R2",
        "SL-1A-F-R3",
    ]


def test_reyes_rams_the_drawer_event_is_declared() -> None:
    event = next(event for event in PACKAGE.pacing.events if event.id == RAM_EVENT)
    assert event.scene_id == "1A"
    assert event.trailing is True
    assert event.at_turn == 8
    assert {(condition.fact_id, condition.equals) for condition in event.when} == {
        ("patrol_in_house", True),
        (GAP_FACT, False),
        (CARD_FACT, False),
    }
    assert [(effect.fact_id, effect.equals) for effect in event.effects] == [(GAP_FACT, True)]
    assert len(event.realizations) == 1
    assert event.realizations[0].verbatim is True
    assert event.realizations[0].text == RAM_TEXT
    assert "card" not in event.realizations[0].text.casefold()


class _Response:
    def __init__(self, payload: object) -> None:
        self.payload = payload

    def __enter__(self) -> _Response:
        return self

    def __exit__(self, *_args: object) -> None:
        return None

    def read(self) -> bytes:
        return json.dumps(self.payload).encode()


def _run_scene_1a(monkeypatch: pytest.MonkeyPatch, *, turns: int, gap_found: bool = False):
    state = RuntimeState.bootstrap(PACKAGE)
    if gap_found:
        _set_fact(state, GAP_FACT, True)
    observations: list[str] = []

    def open_request(_request, **_kwargs: object) -> _Response:
        observations.append(world_for(PACKAGE, state.facts).parent("patrol_officer"))
        return _Response({"narration": '{"segments":[{"kind":"narration","text":"The house remains quiet."}]}'})

    monkeypatch.setattr("storygame.runtime.cloudflare.urlopen", open_request)
    engine = RuntimeEngine(
        state,
        CloudflareTurnProvider(worker_url="https://worker.example/turn", token="", state=state),
    )
    engine.narration_validator.validate = lambda *_args, **_kwargs: None
    engine.opening()
    proposals = [engine.turn(command, clock_seconds=1) for command in (*COMMANDS, "Wait and observe.")[:turns]]
    return state, observations, proposals


def _texts(proposal: object) -> tuple[str, ...]:
    return tuple(segment.text for segment in proposal.segments)


def test_reyes_rams_the_drawer_when_nobody_found_the_gap(monkeypatch: pytest.MonkeyPatch) -> None:
    state, observations, proposals = _run_scene_1a(monkeypatch, turns=8)
    assert RAM_EVENT in state.fired_event_ids
    assert Fact(predicate=GAP_FACT, subject="story", value="true") in state.facts.asserted
    assert _texts(proposals[-1])[-1] == RAM_TEXT
    assert _texts(proposals[-1]).count(RAM_TEXT) == 1
    assert observations[-1] == "kitchen"


def test_reyes_does_not_ram_the_drawer_after_the_gap_is_found_control(monkeypatch: pytest.MonkeyPatch) -> None:
    state, _observations, proposals = _run_scene_1a(monkeypatch, turns=8, gap_found=True)
    assert RAM_EVENT not in state.fired_event_ids
    assert all(RAM_TEXT not in _texts(proposal) for proposal in proposals)


@pytest.mark.parametrize("turns", (5, 6, 7))
def test_reyes_does_not_ram_the_drawer_before_turn_8_control(monkeypatch: pytest.MonkeyPatch, turns: int) -> None:
    state, _observations, _proposals = _run_scene_1a(monkeypatch, turns=turns)
    assert RAM_EVENT not in state.fired_event_ids


def test_scene_1a_budget_pins_are_untouched_control() -> None:
    budget = json.loads((Path(__file__).parent / "fixtures/deep_turn_budget.json").read_text(encoding="utf-8"))
    scene = budget["scenes"]["1A"]
    assert scene["narration_chars"] == 5485
    assert scene["narration_chars_all_alternates"] == 5597
