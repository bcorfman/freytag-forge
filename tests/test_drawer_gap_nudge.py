from __future__ import annotations

from pathlib import Path

import pytest

from storygame.runtime.candidate_matcher import uniquely_matched_authored_handoff
from storygame.runtime.facts import Fact
from storygame.runtime.knowledge import KnowledgeProjector
from storygame.story_package.loader import load_story_package
from tests.test_observation_mode import _state_at

PACKAGE = load_story_package(Path("data/stories/continuity-initiative"))
NUDGE = "k_sl_1a_f_r2"
CARD_FIND = "k_sl_1a_b_r0"
CARD_FIND_PATROL = "k_sl_1a_b_r0w"
OPEN_DRAWER = "k_sl_1a_f_r1"
GAP_STORYLET = "SL-1A-F"
GAP_FACT = "drawer_gap_pointed_out"
CARD_FACT = "memory_card_recovered"
NUDGE_TEXT = (
    "The drawer rides high in its frame. A thin gap beneath its lower edge is wide enough for Kristin's fingers."
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

UNDER_COMMANDS = tuple(
    f"{verb} {underword} the drawer."
    for verb in ("Examine", "Inspect", "Search", "Check", "Look", "Feel", "Study")
    for underword in ("under", "beneath", "underneath", "below")
)


def _handoff(state, command: str):
    projection = KnowledgeProjector().project(state, "player", command)
    return uniquely_matched_authored_handoff(command, projection.reveal_universe)


def _gap_state():
    state = _state_at("kitchen")
    state.active_event_ids.add(GAP_STORYLET)
    return state


def _fact_is_true(state, predicate: str) -> bool:
    return any(fact.predicate == predicate and fact.value == "true" for fact in state.facts.asserted)


def _state_after_gap_deliveries(delivery_count: int):
    state = _gap_state()
    for _ in range(delivery_count):
        state.facts.assert_fact(Fact(predicate=GAP_FACT, subject="story", value="true"))
        state.fired_event_ids.add(GAP_STORYLET)
    return state


def _card_find_state():
    state = _gap_state()
    assert not _fact_is_true(state, "patrol_in_house")
    state.active_event_ids.add("SL-1A-E")
    return state


@pytest.mark.parametrize("command", BARE_DRAWER_COMMANDS)
def test_bare_drawer_commands_pick_the_gap_nudge(command: str) -> None:
    state = _gap_state()

    assert not _fact_is_true(state, CARD_FACT)
    handoff = _handoff(state, command)

    assert handoff is not None
    assert handoff.candidate.id == NUDGE
    assert handoff.delivery_text == NUDGE_TEXT


@pytest.mark.parametrize("delivery_count", (1, 3))
@pytest.mark.parametrize("command", BARE_DRAWER_COMMANDS)
def test_gap_nudge_stays_eligible_after_delivery_and_storylet_spending(delivery_count: int, command: str) -> None:
    state = _state_after_gap_deliveries(delivery_count)
    handoff = _handoff(state, command)

    assert handoff is not None
    assert handoff.candidate.id == NUDGE
    assert handoff.delivery_text == NUDGE_TEXT


@pytest.mark.parametrize("command", UNDER_COMMANDS)
def test_under_forms_pick_the_card_find_and_never_the_gap_nudge(command: str) -> None:
    handoff = _handoff(_card_find_state(), command)

    assert handoff is not None
    assert handoff.candidate.id == CARD_FIND
    assert handoff.candidate.id != CARD_FIND_PATROL
    assert handoff.candidate.id != NUDGE


@pytest.mark.parametrize("command", ("Open the drawer.", "Pull out the drawer."))
def test_opening_commands_do_not_pick_the_gap_nudge(command: str) -> None:
    state = _state_at("kitchen")
    state.active_event_ids.add(GAP_STORYLET)
    handoff = _handoff(state, command)

    assert handoff is None or handoff.candidate.id == OPEN_DRAWER
    assert handoff is None or handoff.candidate.id != NUDGE


def test_unrelated_command_picks_neither_drawer_reveal() -> None:
    handoff = _handoff(_gap_state(), "Inspect the truck.")

    assert handoff is None or handoff.candidate.id not in {NUDGE, CARD_FIND, CARD_FIND_PATROL}


@pytest.mark.parametrize(
    "command",
    ("Look inside the drawer.", "Search inside the drawer.", "Examine inside the drawer."),
)
def test_inside_forms_never_pick_the_card_find(command: str) -> None:
    state = _gap_state()
    handoff = _handoff(state, command)
    picked_id = handoff.candidate.id if handoff is not None else None

    assert picked_id in {NUDGE, None}, {command: picked_id}
    assert picked_id != CARD_FIND
    assert picked_id != CARD_FIND_PATROL


def test_bare_drawer_commands_stop_picking_the_nudge_after_card_recovery() -> None:
    state = _gap_state()
    state.facts.assert_fact(Fact(predicate=CARD_FACT, subject="story", value="true"))

    for command in BARE_DRAWER_COMMANDS:
        handoff = _handoff(state, command)
        assert handoff is None or handoff.candidate.id != NUDGE


def test_real_package_repeatable_flag_is_only_on_the_gap_nudge() -> None:
    assert PACKAGE.knowledge_indexes.by_id[NUDGE].repeatable is True
    assert all(item.repeatable is False for item in PACKAGE.knowledge.knowledge if item.id != NUDGE)


def test_pull_out_drawer_open_reveal_is_eligible_once() -> None:
    state = _state_at("kitchen")
    state.active_event_ids.add(GAP_STORYLET)

    first = _handoff(state, "Pull out the drawer.")
    assert first is not None
    assert first.candidate.id == OPEN_DRAWER

    state.facts.assert_fact(Fact(predicate=GAP_FACT, subject="story", value="true"))
    state.fired_event_ids.add(GAP_STORYLET)

    assert _handoff(state, "Pull out the drawer.") is None
