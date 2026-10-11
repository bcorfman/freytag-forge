"""Evidence gaps paid by forced handoffs and selected by 3C pacing."""

from __future__ import annotations

from itertools import product
from pathlib import Path

import pytest

from storygame.runtime.engine import RuntimeEngine
from storygame.runtime.facts import Fact
from storygame.runtime.reveal_eligibility import explain_reveal
from storygame.runtime.state import RuntimeState
from storygame.story_package.loader import load_story_package
from storygame.story_package.models import FactPredicate, PacingEvent, PacingRealization

PACKAGE = load_story_package(Path("data/stories/continuity-initiative"))

GAPS = (
    "evidence_gap_processing_numbers",
    "evidence_gap_development_record",
    "evidence_gap_marked_site_list",
)
FORCED_DELIVERIES = (
    ("1C", "captives_confirmed_alive", "evidence_gap_processing_numbers"),
    ("2B", "brandon_janus_role_known", "evidence_gap_development_record"),
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


@pytest.mark.parametrize(("scene_id", "delivery_id", "gap_id"), FORCED_DELIVERIES)
def test_forced_delivery_asserts_gap_when_narration_already_conveys_delivery(
    scene_id: str, delivery_id: str, gap_id: str
) -> None:
    state = _state(scene_id)
    state.staged_handoff_fact_ids = (delivery_id,)
    delivery = next(item for item in PACKAGE.deliveries if item.fact_id == delivery_id)
    narration = ". ".join(group[0] for group in delivery.must_convey)
    engine = RuntimeEngine(state, lambda _input: {"segments": [{"kind": "narration", "text": narration}]})

    engine.turn("Search the room.")

    assert _asserted(state, gap_id)


def test_spent_3c_events_do_not_repeat_their_payoff() -> None:
    state = _state("3C", turn_index=3)
    state.facts.assert_fact(Fact(predicate=GAPS[0], subject="story", value="true"))
    engine = RuntimeEngine(state, lambda _input: {"segments": [{"kind": "narration", "text": "Keep moving."}]})
    collapse = next(event for event in PACKAGE.pacing.events if event.id == "collapse_3c")
    routes = next(event for event in PACKAGE.pacing.events if event.id == "routes_collapse_3c")

    engine.turn("Keep moving toward the stairs.")
    first_collapse = state.last_turn_delivery.complication_text
    state.turn_index = 4
    engine.turn("Keep moving toward the gate.")

    assert "collapse_3c" in state.fired_event_ids
    assert state.last_turn_delivery.complication_text not in {realization.text for realization in collapse.realizations}
    state.turn_index = 9
    engine.turn("Help the captives toward the gate.")
    first_routes = state.last_turn_delivery.complication_text
    state.turn_index = 10
    engine.turn("Help the captives toward the surface.")

    assert "routes_collapse_3c" in state.fired_event_ids
    assert state.last_turn_delivery.complication_text not in {realization.text for realization in routes.realizations}
    assert first_collapse is not None
    assert first_routes is not None


def test_3c_pacing_collision_spends_event_without_retrying_gap_line() -> None:
    competing = PacingEvent(
        id="competing_3c_complication",
        scene_id="3C",
        at_turn=4,
        effects=(FactPredicate(fact_id="competing_3c_pressure", equals=True),),
        realizations=(PacingRealization(text="The competing complication takes the foreground."),),
    )
    package = PACKAGE.model_copy(
        update={"pacing": PACKAGE.pacing.model_copy(update={"events": (competing, *PACKAGE.pacing.events)})}
    )
    state = RuntimeState(package=package, current_scene_id="3C", phase="resolution", turn_index=3)
    state.facts.assert_fact(Fact(predicate=GAPS[0], subject="story", value="true"))
    engine = RuntimeEngine(state, lambda _input: {"segments": [{"kind": "narration", "text": "Keep moving."}]})
    collapse = next(event for event in package.pacing.events if event.id == "collapse_3c")

    engine.turn("Keep moving toward the stairs.")
    assert state.last_turn_delivery.complication_text == competing.realizations[0].text
    assert "collapse_3c" in state.fired_event_ids
    assert collapse.realizations[0].text not in state.last_turn_delivery.complication_text

    state.turn_index = 4
    engine.turn("Keep moving toward the gate.")
    assert state.last_turn_delivery.complication_text is None
    assert "collapse_3c" in state.fired_event_ids


def _resolution_reachability(gap_ids: tuple[str, ...]) -> tuple[object, ...]:
    state = _state("3C")
    for fact_id in ("broadcast_started", "brandon_confession_available", "detention_locations_secured", *gap_ids):
        state.facts.assert_fact(Fact(predicate=fact_id, subject="story", value="true"))
    engine = RuntimeEngine(state, lambda _input: {"segments": [{"kind": "narration", "text": "Watch."}]})
    engine._activate_pacing()  # noqa: SLF001 - inspect deterministic eligibility.
    true_facts = {fact.predicate for fact in state.facts.asserted if fact.value == "true"}
    canonical = tuple(
        event.id
        for event in (*PACKAGE.storylet_routes.bridge_events, *PACKAGE.storylet_routes.resolution_events)
        if event.scene_id == "3C"
        and event.activation.is_satisfied(true_facts)
        and event.id not in state.fired_event_ids
    )
    reveal_ids = tuple(candidate.id for candidate in engine.projector.project(state, "player", "").candidates)
    reveal_reasons = tuple(
        (item.id, explain_reveal(state, "player", item).eligible)
        for item in PACKAGE.knowledge.knowledge
        if item.available_in_scenes and "3C" in item.available_in_scenes
    )
    return tuple(sorted(state.active_event_ids)), canonical, reveal_ids, reveal_reasons


@pytest.mark.parametrize("gap_ids", product((False, True), repeat=3))
def test_all_gap_combinations_preserve_3c_reachability(gap_ids: tuple[bool, bool, bool]) -> None:
    selected = tuple(fact_id for fact_id, present in zip(GAPS, gap_ids, strict=True) if present)

    assert _resolution_reachability(selected) == _resolution_reachability(())


def test_all_gaps_still_reach_resolution_complete_at_the_resolution_deadline() -> None:
    state = _state("3C", turn_index=13)
    for fact_id in ("broadcast_started", "brandon_confession_available", "detention_locations_secured", *GAPS):
        state.facts.assert_fact(Fact(predicate=fact_id, subject="story", value="true"))

    engine = RuntimeEngine(state, lambda _input: {"segments": [{"kind": "narration", "text": "Get everyone out."}]})
    engine.turn("Get everyone to the surface.")

    assert _asserted(state, "resolution_complete")


def test_gap_fact_ids_are_not_used_by_progression_or_reveal_gates() -> None:
    dumped = PACKAGE.model_dump()
    occurrences: list[tuple[tuple[str, ...], str]] = []

    def walk(value: object, path: tuple[str, ...] = ()) -> None:
        if isinstance(value, dict):
            for key, child in value.items():
                walk(child, (*path, str(key)))
        elif isinstance(value, list):
            for index, child in enumerate(value):
                walk(child, (*path, str(index)))
        elif value in GAPS:
            occurrences.append((path, value))

    walk(dumped)

    def allowed(path: tuple[str, ...]) -> bool:
        if path[:2] in {("world", "facts"), ("knowledge", "facts")}:
            return True
        if path[:1] == ("deliveries",) and "costs" in path:
            return True
        if path[:1] == ("pacing",) and "realizations" in path and "when" in path:
            return True
        return "new_fact_ids" in path

    assert all(allowed(path) for path, _fact_id in occurrences), occurrences


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


@pytest.mark.parametrize("gap_ids", product((False, True), repeat=3))
def test_3c_pacing_prioritizes_records_over_check_for_all_gap_combinations(
    gap_ids: tuple[bool, bool, bool],
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
    expected_routes = routes.realizations[0].text if gap_ids[2] else routes.realizations[-1].text

    assert collapse_text == expected_collapse
    assert routes_text == expected_routes


def test_3c_no_gaps_keep_original_default_texts() -> None:
    collapse = next(event for event in PACKAGE.pacing.events if event.id == "collapse_3c")
    routes = next(event for event in PACKAGE.pacing.events if event.id == "routes_collapse_3c")

    assert collapse.realizations[-1].text == (
        "Water seeps under the outer doors. Charles's emergency deluge is becoming real."
    )
    assert (
        routes.realizations[-1].text
        == "Rising water is closing routes through the facility. The remaining routes are narrowing fast."
    )
