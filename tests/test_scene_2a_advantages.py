from pathlib import Path

from storygame.runtime.candidate_matcher import uniquely_matched_authored_handoff
from storygame.runtime.engine import RuntimeEngine
from storygame.runtime.facts import Fact
from storygame.runtime.knowledge import RevealCandidate
from storygame.runtime.state import RuntimeState
from storygame.story_package.loader import load_story_package
from storygame.story_package.models import scene_entry_texts

PACKAGE = load_story_package(Path("data/stories/continuity-initiative"))
BASE_2A_FACTS: tuple[str, ...] = ()
SCENE_2A_CANDIDATES = tuple(
    RevealCandidate(
        id=item.id,
        statement=item.statement,
        earn_when=item.earn_when,
        must_convey=item.must_convey,
        action_evidence=item.action_evidence,
        delivery_text=item.delivery_text,
    )
    for item in PACKAGE.knowledge.knowledge
    if "2A" in item.available_in_scenes and item.action_evidence
)


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
    del state
    handoff = uniquely_matched_authored_handoff(command, SCENE_2A_CANDIDATES)
    return {handoff.candidate.id} if handoff is not None else set()


def test_convincing_diagnosis_selects_the_new_inspection_outcome() -> None:
    command = "Diagnose the real cooling-water pressure fault and explain the ventilation problem to the supervisor."

    assert _eligible_confrontations(_state_2a(), command) == {"k_sl_2a_c_r5"}


def test_vague_diagnosis_selects_the_under_watch_inspection_outcome() -> None:
    command = "Give the supervisor a vague, overlong explanation of the cooling and ventilation fault."

    assert _eligible_confrontations(_state_2a(), command) == {"k_sl_2a_c_r6"}


def test_inspection_outcomes_are_distinct() -> None:
    state = _state_2a()

    assert _eligible_confrontations(
        state, "Diagnose the real cooling-water pressure fault and explain the ventilation problem to the supervisor."
    ) == {"k_sl_2a_c_r5"}
    assert _eligible_confrontations(
        state, "Give the supervisor a vague, overlong explanation of the cooling and ventilation fault."
    ) == {"k_sl_2a_c_r6"}


def test_2a_completes_without_either_carried_advantage() -> None:
    state = _state_2a()
    engine = RuntimeEngine(state, lambda _command: {"segments": [{"kind": "narration", "text": "We wait."}]})

    for _ in range(5):
        engine.turn("Wait and watch the shift supervisor.")

    assert state.current_scene_id == "2A"
    assert Fact(predicate="inspection_window_missed", subject="story", value="true") in state.facts.asserted
    assert Fact(predicate="restricted_corridor_access", subject="story", value="true") not in state.facts.asserted
    assert Fact(predicate="cover_suspected", subject="story", value="true") not in state.facts.asserted
    engine.turn("Continue waiting.")
    assert Fact(predicate="supervisor_escorting", subject="story", value="true") in state.facts.asserted


def test_2a_entry_includes_both_variants_in_declaration_order() -> None:
    state = _state_2a("processing_numbers_copied", "service_level_access_known")
    metadata = next(scene.metadata for scene in PACKAGE.scenes if scene.metadata.scene_id == "2A")
    texts = scene_entry_texts(metadata, {fact.predicate for fact in state.facts.asserted})
    assert texts[1:] == (
        "Kristin still has the copied prisoner numbers. The codes on the supervisor's work orders look like the same "
        "system.",
        "Brandon knows the service approach. If they get past this man, he can take them around the second checkpoint.",
    )


def test_2a_entry_is_base_only_when_neither_advantage_is_true() -> None:
    state = _state_2a()
    metadata = next(scene.metadata for scene in PACKAGE.scenes if scene.metadata.scene_id == "2A")
    assert tuple(scene_entry_texts(metadata, {fact.predicate for fact in state.facts.asserted})) == (
        metadata.entry_text,
    )
