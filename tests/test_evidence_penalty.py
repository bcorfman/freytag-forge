"""Evidence gaps paid by forced handoffs and selected by 3C pacing."""

from __future__ import annotations

from itertools import product
from pathlib import Path

import pytest

from storygame.runtime.engine import RuntimeEngine
from storygame.runtime.facts import Fact
from storygame.runtime.state import RuntimeState
from storygame.story_package.loader import load_story_package

PACKAGE = load_story_package(Path("data/stories/continuity-initiative"))

GAPS = (
    "evidence_gap_processing_numbers",
    "evidence_gap_development_record",
    "evidence_gap_copy_check",
    "evidence_gap_marked_site_list",
)
FORCED_DELIVERIES = (
    ("1C", "captives_confirmed_alive", "evidence_gap_processing_numbers"),
    ("2B", "brandon_janus_role_known", "evidence_gap_development_record"),
    ("2C", "evidence_ready_to_transmit", "evidence_gap_copy_check"),
    ("3B", "detention_locations_secured", "evidence_gap_marked_site_list"),
)
EARNED_DELIVERIES = (
    ("1C", "captives_confirmed_alive", "facility_proof", "k_sl_1c_b_r1"),
    ("2B", "brandon_janus_role_known", "janus_evidence", "k_sl_2b_b_r1"),
    ("2C", "evidence_ready_to_transmit", "janus_evidence", "k_sl_2c_c_r1"),
    ("3B", "detention_locations_secured", "human_security_control", "k_sl_3b_b_r1"),
)


def _state(scene_id: str, *, turn_index: int = 0) -> RuntimeState:
    scene = next(scene for scene in PACKAGE.scenes if scene.metadata.scene_id == scene_id)
    return RuntimeState(
        package=PACKAGE,
        current_scene_id=scene_id,
        phase=scene.metadata.freytag_phase,
        turn_index=turn_index,
    )


def _asserted(state: RuntimeState, fact_id: str) -> bool:
    return Fact(predicate=fact_id, subject="story", value="true") in state.facts.asserted


@pytest.mark.parametrize(("scene_id", "delivery_id", "gap_id"), FORCED_DELIVERIES)
def test_forced_delivery_asserts_its_evidence_gap(scene_id: str, delivery_id: str, gap_id: str) -> None:
    state = _state(scene_id)
    state.staged_handoff_fact_ids = (delivery_id,)
    engine = RuntimeEngine(state, lambda _input: {"segments": [{"kind": "narration", "text": "Wait."}]})

    engine.turn("Search the room.")

    assert _asserted(state, gap_id)
    assert sum(_asserted(state, other) for other in GAPS) == 1


@pytest.mark.parametrize(("scene_id", "delivery_id", "prerequisite", "knowledge_id"), EARNED_DELIVERIES)
def test_earned_delivery_leaves_its_evidence_gap_unset(
    scene_id: str, delivery_id: str, prerequisite: str, knowledge_id: str
) -> None:
    state = _state(scene_id)
    state.facts.assert_fact(Fact(predicate=prerequisite, subject="story", value="true"))
    if scene_id == "3B":
        state.facts.assert_fact(Fact(predicate="rebecca_office_reached", subject="story", value="true"))
    delivery_text = PACKAGE.knowledge_indexes.by_id[knowledge_id].delivery_text
    engine = RuntimeEngine(
        state,
        lambda _input: {
            "segments": [{"kind": "narration", "text": delivery_text}],
            "selected_knowledge_ids": [knowledge_id],
        },
    )

    engine.turn("Search the room.")

    assert _asserted(state, delivery_id)
    assert not any(_asserted(state, gap_id) for gap_id in GAPS)


def _pacing_texts(gap_ids: tuple[str, ...]) -> tuple[str | None, str | None]:
    state = _state("3C", turn_index=3)
    for gap_id in gap_ids:
        state.facts.assert_fact(Fact(predicate=gap_id, subject="story", value="true"))
    engine = RuntimeEngine(state, lambda _input: {"segments": [{"kind": "narration", "text": "Keep moving."}]})

    engine.turn("Keep moving toward the stairs.")
    collapse_text = state.last_turn_delivery.complication_text
    state.turn_index = 9
    engine.turn("Help the captives toward the gate.")
    return collapse_text, state.last_turn_delivery.complication_text


@pytest.mark.parametrize("gap_ids", product((False, True), repeat=4))
def test_3c_pacing_prioritizes_records_over_check_for_all_gap_combinations(
    gap_ids: tuple[bool, bool, bool, bool],
) -> None:
    selected = tuple(fact_id for fact_id, present in zip(GAPS, gap_ids, strict=True) if present)
    collapse_text, routes_text = _pacing_texts(selected)
    collapse = next(event for event in PACKAGE.pacing.events if event.id == "collapse_3c")
    routes = next(event for event in PACKAGE.pacing.events if event.id == "routes_collapse_3c")
    expected_collapse = (
        collapse.realizations[0].text
        if gap_ids[0]
        else collapse.realizations[1].text
        if gap_ids[1]
        else collapse.realizations[-1].text
    )
    expected_routes = (
        routes.realizations[0].text
        if gap_ids[3]
        else routes.realizations[1].text
        if gap_ids[2]
        else routes.realizations[-1].text
    )

    assert collapse_text == expected_collapse
    assert routes_text == expected_routes


def test_3c_no_gaps_keep_original_default_texts() -> None:
    collapse = next(event for event in PACKAGE.pacing.events if event.id == "collapse_3c")
    routes = next(event for event in PACKAGE.pacing.events if event.id == "routes_collapse_3c")

    assert collapse.realizations[-1].text == (
        "Water seeps under the outer doors. Charles's emergency deluge is becoming real."
    )
    assert routes.realizations[-1].text == (
        "Rising water closes a maintenance passage behind the fleeing captives. "
        "The remaining routes are narrowing fast."
    )
