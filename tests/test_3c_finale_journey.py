"""The finite 3C incident completes every authored evacuation branch."""

from pathlib import Path

from storygame.runtime.engine import RuntimeEngine
from storygame.runtime.facts import Fact
from storygame.runtime.state import RuntimeState
from storygame.story_package.loader import load_story_package

PACKAGE = load_story_package(Path("data/stories/continuity-initiative"))
ENTRY_FACTS = (
    "broadcast_started",
    "brandon_confession_available",
    "detention_locations_secured",
)
OUTCOME_FACTS = {"barrier_held", "captives_out_costly", "lower_levels_lost"}


def _state() -> RuntimeState:
    state = RuntimeState(package=PACKAGE, current_scene_id="3C", phase="resolution")
    state._assert_scene_entry_fact("3C")
    for fact_id in ENTRY_FACTS:
        state.facts.assert_fact(Fact(predicate=fact_id, subject="story", value="true"))
    return state


def _provider(knowledge_id: str | None = None):
    knowledge = PACKAGE.knowledge_indexes.by_id[knowledge_id] if knowledge_id else None

    def provide(_player_input: str):
        if knowledge is None:
            return {"segments": [{"kind": "narration", "text": "Kristin checks the rising water."}]}
        return {
            "segments": [
                {
                    "kind": "narration",
                    "text": knowledge.delivery_text or knowledge.statement,
                    "grounding_ids": [knowledge_id],
                }
            ],
            "selected_knowledge_ids": [knowledge_id],
        }

    return provide


def _texts(result) -> list[str]:
    return [segment.text for segment in result.segments]


def _start_at_evacuation(state: RuntimeState) -> RuntimeEngine:
    engine = RuntimeEngine(state, _provider("k_sl_3c_a_r1"))
    engine._activate_pacing()  # noqa: SLF001 - stage the first real 3C cue.
    engine.turn("Send the evidence package.")
    engine.provider = _provider("k_sl_3c_b_r1")
    engine.turn("Take the Portable data case from Rebecca.")
    engine._activate_pacing()  # noqa: SLF001 - expose the incident's evacuation handoff.
    return engine


def test_3c_finale_journey_completes_clean_costly_and_missed_recovery() -> None:
    cases = (
        ("k_sl_3c_c_r1", "Restore the pumps.", "The lower levels stand, and every cart came through."),
        (
            "k_sl_3c_c_r2",
            "Give up the lower levels.",
            "The lower levels went under. Everyone who reached the surface lived.",
        ),
    )
    for knowledge_id, command, variant in cases:
        state = _state()
        engine = _start_at_evacuation(state)
        engine.provider = _provider(knowledge_id)
        result = engine.turn(command)
        facts = {fact.predicate for fact in state.facts.asserted if fact.value == "true"}
        assert state.story_complete is True
        assert variant in _texts(result)
        assert "evacuation_complete" in facts

    state = _state()
    engine = _start_at_evacuation(state)
    engine.provider = _provider()
    while state.turn_index < 10:
        engine.turn("Inspect the drainage pump controls.")
    facts = {fact.predicate for fact in state.facts.asserted if fact.value == "true"}
    assert "evacuation_window_missed" in facts
    assert "evacuation_surge_building" in facts

    engine.provider = _provider("k_sl_3c_h_r1")
    result = engine.turn("Let the surge carry the captives through the gates.")
    facts = {fact.predicate for fact in state.facts.asserted if fact.value == "true"}
    assert state.story_complete is True
    assert "The surge, not a plan, carried the captives out. No one yet knows how many." in _texts(result)
    assert "evacuation_complete" in facts
    assert "surge_forced_evacuation" in facts
    assert not OUTCOME_FACTS & facts
