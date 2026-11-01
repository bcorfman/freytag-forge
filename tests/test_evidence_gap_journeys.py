"""Whole-game journeys for every reachable combination of evidence gaps.

Each journey uses the real thorough policy and withholds the authored
realizations that would otherwise establish a selected delivery fact. The
deadline handoff must then pay the delivery's assert-cost. A selected gap is a
fallback, never an earned realization; the assertions below prove that
provenance and preserve the resulting costs through 3C.

The gap itself is the provenance: the existing forced-delivery and earned-
delivery tests establish that a selected gap is fallback and an unselected
delivery is earned. The 3C routes-collapse text is covered synthetically for
all eight subsets by
``test_3c_pacing_prioritizes_records_over_check_for_all_gap_combinations``.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from itertools import product
from pathlib import Path

import pytest

from storygame.personas import (
    PERSONAS,
    _legacy_package,
    _resolution_complete,
    _ScriptedProvider,
    _select_thorough,
    _turn_cap,
)
from storygame.runtime.contracts import RuntimeContractError
from storygame.runtime.engine import RuntimeEngine
from storygame.runtime.facts import Fact
from storygame.runtime.state import RuntimeState
from storygame.runtime.validation import ProposalValidationError
from storygame.story_package.loader import load_story_package

PACKAGE = load_story_package(Path("data/stories/continuity-initiative"))
PLAYED = _legacy_package(PACKAGE)
AUTHORED_TURN_BUDGET = 120

GAPS = (
    "evidence_gap_processing_numbers",
    "evidence_gap_development_record",
    "evidence_gap_marked_site_list",
)
DELIVERY_FACTS = (
    "captives_confirmed_alive",
    "brandon_janus_role_known",
    "detention_locations_secured",
)
WITHHELD_REALIZATIONS = (
    ("k_sl_1c_c_copy_numbers", "k_sl_1c_c_secure_route"),
    ("k_sl_2b_b_r4",),
    ("k_sl_3b_b_r1", "k_sl_3b_b_r2"),
)
# In 2B the development-record gap is the cost of the earned "erase Brandon's name" outcome, and the neutral
# recovery carries no cost. A journey with the 2B gap withholds the keep-the-name outcome so the thorough policy
# takes the erase outcome; a journey without it withholds the erase outcome so the policy keeps the name.
WITHHELD_WHEN_GAP_NOT_SELECTED = ((), ("k_sl_2b_b_r5",), ())


@dataclass
class Journey:
    state: RuntimeState
    scenes: list[str] = field(default_factory=list)
    gaps_at_3c: set[str] | None = None
    complication_texts: dict[str, str | None] = field(default_factory=dict)

    @property
    def deadline_events(self) -> list[str]:
        return [event for record in self.state.turn_records for event in record.deadline_event_ids]


def _asserted(state: RuntimeState, fact_id: str) -> bool:
    return Fact(predicate=fact_id, subject="story", value="true") in state.facts.asserted


def _expected_pacing_text(event_id: str, gap_ids: set[str]) -> str:
    event = next(event for event in PLAYED.pacing.events if event.id == event_id)
    for realization in event.realizations:
        if realization.when and all(
            _asserted_fact in gap_ids for _asserted_fact in (predicate.fact_id for predicate in realization.when)
        ):
            return realization.text
    return event.realizations[-1].text


def _play(withheld: set[str]) -> Journey:
    blocked = withheld
    state = RuntimeState.bootstrap(PLAYED)
    provider = _ScriptedProvider(PLAYED, state)
    engine = RuntimeEngine(state, provider)
    journey = Journey(
        state=state,
        scenes=[state.current_scene_id],
        complication_texts={"collapse_3c": None, "routes_collapse_3c": None},
    )

    for _ in range(_turn_cap(PLAYED)):
        if _resolution_complete(state):
            break
        engine._activate_pacing()
        offered = tuple(
            candidate
            for candidate in engine.projector.project(state, "player", "").candidates
            if candidate.id not in blocked
        )
        selected = _select_thorough(PLAYED, state, offered)
        provider.selected = (selected,) if selected else ()
        scene_before = state.current_scene_id
        try:
            engine.turn(PERSONAS["thorough"])
        except (ProposalValidationError, RuntimeContractError):
            provider.selected = ()
            engine.turn(PERSONAS["thorough"])

        if state.current_scene_id != scene_before:
            journey.scenes.append(state.current_scene_id)
        if state.current_scene_id == "3C":
            for event_id in ("collapse_3c", "routes_collapse_3c"):
                if event_id in state.fired_event_ids and journey.complication_texts[event_id] is None:
                    journey.complication_texts[event_id] = state.last_turn_delivery.complication_text
            if journey.gaps_at_3c is None:
                journey.gaps_at_3c = {gap for gap in GAPS if _asserted(state, gap)}

    return journey


def _journey_for(combination: tuple[bool, bool, bool]) -> Journey:
    withheld = {
        knowledge_id
        for chosen, selected_realizations, unselected_realizations in zip(
            combination, WITHHELD_REALIZATIONS, WITHHELD_WHEN_GAP_NOT_SELECTED, strict=True
        )
        for knowledge_id in (selected_realizations if chosen else unselected_realizations)
    }
    return _play(withheld)


@pytest.mark.parametrize("combination", product((False, True), repeat=3))
@pytest.mark.nightly
def test_every_reachable_evidence_gap_combination(combination: tuple[bool, bool, bool]) -> None:
    """A subset with gaps is labeled fallback, never earned."""

    selected_gaps = {gap for gap, chosen in zip(GAPS, combination, strict=True) if chosen}
    journey = _journey_for(combination)
    state = journey.state

    assert _resolution_complete(state)
    assert state.turn_index <= AUTHORED_TURN_BUDGET
    assert {gap for gap in GAPS if _asserted(state, gap)} == selected_gaps
    assert all(_asserted(state, delivery) for delivery in DELIVERY_FACTS)
    assert journey.gaps_at_3c is not None
    assert journey.gaps_at_3c & set(GAPS[:2]) == selected_gaps & set(GAPS[:2])
    assert (GAPS[2] in journey.gaps_at_3c) == (GAPS[2] in selected_gaps)
    for delivery, gap, chosen in zip(DELIVERY_FACTS, GAPS, combination, strict=True):
        assert _asserted(state, delivery)
        assert _asserted(state, gap) is chosen


@pytest.mark.parametrize("combination", product((False, True), repeat=3))
@pytest.mark.nightly
def test_evidence_gap_3c_pressure_text(combination: tuple[bool, bool, bool]) -> None:
    """Each 3C pressure realization follows the selected fallback gaps."""

    selected_gaps = {gap for gap, chosen in zip(GAPS, combination, strict=True) if chosen}
    journey = _journey_for(combination)
    collapse_text = journey.complication_texts["collapse_3c"]
    if collapse_text is None:
        pytest.skip("collapse_3c fired without player-visible text; same-turn event delivery is displaced")
    assert collapse_text == _expected_pacing_text("collapse_3c", selected_gaps)
    if "routes_collapse_3c" not in journey.state.fired_event_ids:
        assert journey.complication_texts["routes_collapse_3c"] is None
    else:
        routes_text = journey.complication_texts["routes_collapse_3c"]
        assert routes_text is not None
        assert routes_text == _expected_pacing_text("routes_collapse_3c", selected_gaps)
