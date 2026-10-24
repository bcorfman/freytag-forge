from __future__ import annotations

from pathlib import Path

import pytest

from storygame.runtime.engine import RuntimeEngine
from storygame.runtime.facts import Fact
from storygame.runtime.state import RuntimeState
from storygame.story_package.loader import load_story_package

REAL_PACKAGE_ROOT = Path("data/stories/continuity-initiative")
LIGHTHOUSE_PACKAGE_ROOT = Path(__file__).parent / "fixtures" / "stories" / "lighthouse-incident"


def _provider(_player_input: str) -> dict[str, object]:
    return {"segments": [{"kind": "narration", "text": "The player waits and observes."}]}


def _true_facts(state: RuntimeState) -> set[str]:
    return {fact.predicate for fact in state.facts.asserted if fact.subject == "story" and fact.value == "true"}


def _real_incident_state() -> RuntimeState:
    state = RuntimeState.bootstrap(load_story_package(REAL_PACKAGE_ROOT))
    state.current_scene_id = "1C"
    state.phase = next(
        scene.metadata.freytag_phase for scene in state.package.scenes if scene.metadata.scene_id == "1C"
    )
    state._assert_scene_entry_fact("1C")
    state.active_event_ids.update({"SL-1C-A", "SL-1C-B", "SL-1C-C"})
    return state


def _fixture_incident_state() -> RuntimeState:
    return RuntimeState.bootstrap(load_story_package(LIGHTHOUSE_PACKAGE_ROOT))


@pytest.mark.parametrize("state_factory", [_real_incident_state, _fixture_incident_state])
def test_unresolved_incident_never_stages_or_delivers_advantages(state_factory) -> None:
    state = state_factory()
    incident = next(item for item in state.package.incidents if item.scene_id == state.current_scene_id)
    window = next(item for item in state.package.pacing.scenes if item.scene_id == state.current_scene_id)
    engine = RuntimeEngine(state, _provider)
    advantage_ids = {fact_id for outcome in incident.outcomes for fact_id in outcome.advantages}
    fallback_by_fact = {delivery.fact_id: delivery.fallback_text for delivery in state.package.deliveries}
    responses = []

    for turn in range(window.handoff_after_turns + 1):
        responses.append(engine.turn(f"Wait and observe turn {turn}."))
        assert state.staged_handoff_fact_ids == ()

    response_text = " ".join(segment.text for response in responses for segment in response.segments)
    assert not any(
        fallback_by_fact[fact_id] in response_text for fact_id in advantage_ids if fact_id in fallback_by_fact
    )
    assert not advantage_ids & _true_facts(state)
    assert state.current_scene_id == incident.scene_id


def test_ordinary_real_package_scene_still_stages_handoff() -> None:
    package = load_story_package(REAL_PACKAGE_ROOT)
    state = RuntimeState.bootstrap(package)
    state.current_scene_id = "1B"
    state.phase = next(scene.metadata.freytag_phase for scene in package.scenes if scene.metadata.scene_id == "1B")
    state._assert_scene_entry_fact("1B")
    window = next(item for item in package.pacing.scenes if item.scene_id == "1B")
    state.turn_index = window.handoff_after_turns

    RuntimeEngine(state, _provider)._activate_pacing()

    assert state.staged_handoff_fact_ids


@pytest.mark.parametrize("state_factory", [_real_incident_state, _fixture_incident_state])
def test_resolved_incident_keeps_handoff_staging_behavior(state_factory) -> None:
    state = state_factory()
    incident = next(item for item in state.package.incidents if item.scene_id == state.current_scene_id)
    advantage_id = incident.outcomes[0].advantages[0]
    state.facts.assert_fact(Fact(predicate=advantage_id, subject="story", value="true"))
    window = next(item for item in state.package.pacing.scenes if item.scene_id == state.current_scene_id)
    state.turn_index = window.handoff_after_turns

    RuntimeEngine(state, _provider)._activate_pacing()

    assert state.staged_handoff_fact_ids
