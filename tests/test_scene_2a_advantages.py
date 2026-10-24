from pathlib import Path

from storygame.runtime.engine import RuntimeEngine
from storygame.runtime.facts import Fact
from storygame.runtime.state import RuntimeState
from storygame.story_package.loader import load_story_package
from storygame.story_package.models import scene_entry_texts
from tests.test_game_path_journeys import play

PACKAGE = load_story_package(Path("data/stories/continuity-initiative"))
BASE_2A_FACTS = ("false_identities_ready", "facility_perimeter_reached")


def _state_2a(*advantage_facts: str) -> RuntimeState:
    state = RuntimeState.bootstrap(PACKAGE)
    state.current_scene_id = "2A"
    state.phase = next(scene.metadata.freytag_phase for scene in PACKAGE.scenes if scene.metadata.scene_id == "2A")
    state._assert_scene_entry_fact("2A")
    state.active_event_ids.add("SL-2A-C")
    for fact_id in (*BASE_2A_FACTS, *advantage_facts):
        state.facts.assert_fact(Fact(predicate=fact_id, subject="story", value="true"))
    return state


def _eligible_confrontations(state: RuntimeState, command: str) -> set[str]:
    projection = RuntimeEngine(state, lambda _command: {}).projector.project(state, "player", command)
    return {
        candidate.id for candidate in projection.reveal_universe if candidate.id in {"k_sl_2a_c_r3", "k_sl_2a_c_r4"}
    }


def test_processing_numbers_variant_requires_the_copied_numbers() -> None:
    command = "Use the copied prisoner numbers to explain the cooling-water inspection to the supervisor."

    assert "k_sl_2a_c_r3" in _eligible_confrontations(_state_2a("processing_numbers_copied"), command)
    assert "k_sl_2a_c_r3" not in _eligible_confrontations(_state_2a(), command)


def test_service_route_variant_requires_known_service_access() -> None:
    command = "Use the known service route to explain the inspection approach to the supervisor."

    assert "k_sl_2a_c_r4" in _eligible_confrontations(_state_2a("service_level_access_known"), command)
    assert "k_sl_2a_c_r4" not in _eligible_confrontations(_state_2a(), command)


def test_both_advantages_make_both_confrontation_variants_available() -> None:
    state = _state_2a("processing_numbers_copied", "service_level_access_known")

    assert _eligible_confrontations(
        state, "Use the copied prisoner numbers to explain the cooling-water inspection to the supervisor."
    ) == {
        "k_sl_2a_c_r3",
        "k_sl_2a_c_r4",
    }
    assert _eligible_confrontations(
        state, "Use the known service route to explain the inspection approach to the supervisor."
    ) == {
        "k_sl_2a_c_r3",
        "k_sl_2a_c_r4",
    }


def test_2a_completes_without_either_carried_advantage() -> None:
    state = _state_2a()
    selected = True

    def provider(_command: str) -> dict[str, object]:
        nonlocal selected
        if selected:
            selected = False
            knowledge = PACKAGE.knowledge_indexes.by_id["k_sl_2a_c_r1"]
            return {
                "segments": [{"kind": "narration", "text": knowledge.delivery_text, "grounding_ids": [knowledge.id]}],
                "selected_knowledge_ids": [knowledge.id],
            }
        return {"segments": [{"kind": "narration", "text": "The inspection continues."}]}

    engine = RuntimeEngine(state, provider)
    engine._activate_pacing()
    for _ in range(7):
        engine.turn("Explain the cooling-water inspection to the supervisor.")

    assert state.current_scene_id == "2B"


def test_carried_advantages_persist_into_2b() -> None:
    numbers_journey = play(("k_sl_1c_c_copy_numbers", "k_sl_2a_c_r3"))
    route_journey = play(("k_sl_1c_c_secure_route", "k_sl_2a_c_r4"))

    assert numbers_journey.state.current_scene_id == "3C"
    assert route_journey.state.current_scene_id == "3C"
    for journey, fact_id in (
        (numbers_journey, "processing_numbers_copied"),
        (route_journey, "service_level_access_known"),
    ):
        assert "2B" in journey.scenes
        assert Fact(predicate=fact_id, subject="story", value="true") in journey.state.facts.asserted


def test_2a_entry_variants_follow_each_real_journey_advantage() -> None:
    numbers = play(("k_sl_1c_c_copy_numbers", "k_sl_2a_c_r3"))
    route = play(("k_sl_1c_c_secure_route", "k_sl_2a_c_r4"))
    assert numbers.entry_texts[-1].startswith("Kristin still has the copied prisoner numbers.")
    assert route.entry_texts[-1].startswith("Kristin and Brandon know the service approach.")


def test_2a_entry_includes_both_variants_in_declaration_order() -> None:
    state = _state_2a("processing_numbers_copied", "service_level_access_known")
    metadata = next(scene.metadata for scene in PACKAGE.scenes if scene.metadata.scene_id == "2A")
    texts = scene_entry_texts(metadata, {fact.predicate for fact in state.facts.asserted})
    assert texts[1:] == (
        "Kristin still has the copied prisoner numbers. She needs a way into the facility.",
        "Kristin and Brandon know the service approach. Their proof is weaker, but it may still get them inside.",
    )


def test_2a_entry_is_base_only_when_neither_advantage_is_true() -> None:
    state = _state_2a()
    metadata = next(scene.metadata for scene in PACKAGE.scenes if scene.metadata.scene_id == "2A")
    assert tuple(scene_entry_texts(metadata, {fact.predicate for fact in state.facts.asserted})) == (
        metadata.entry_text,
    )
