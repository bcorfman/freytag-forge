from __future__ import annotations

from pathlib import Path

import pytest

from storygame.runtime.engine import RuntimeEngine
from storygame.runtime.state import RuntimeState
from storygame.story_package.loader import StoryPackageError, load_story_package

FIXTURE = Path(__file__).parent / "fixtures" / "stories" / "lighthouse-incident"


def _package():
    return load_story_package(FIXTURE)


def _provider(knowledge_id: str | None = None, text: str = "Ada waits."):
    def provide(_player_input: str):
        segment = {"kind": "narration", "text": text}
        payload = {"segments": [segment]}
        if knowledge_id is not None:
            segment["grounding_ids"] = [knowledge_id]
            payload["selected_knowledge_ids"] = [knowledge_id]
        return payload

    return provide


def _true_facts(state: RuntimeState) -> set[str]:
    return {fact.predicate for fact in state.facts.asserted if fact.subject == "story" and fact.value == "true"}


def _reach_lamp_room() -> RuntimeState:
    state = RuntimeState.bootstrap(_package())
    RuntimeEngine(state, _provider("k_find_key", "Ada finds the brass key.")).turn("I find the brass key.")
    assert state.current_scene_id == "1B"
    return state


def test_lighthouse_fixture_loads_with_final_incident_and_ending() -> None:
    package = _package()

    assert [incident.id for incident in package.incidents] == ["tide_window", "lamp_watch"]
    assert package.incidents[1].successor_transition_id is None
    assert package.pacing.ending is not None
    assert package.pacing.ending.scene_id == "1B"


def test_earned_final_incident_outcome_reaches_ending() -> None:
    state = _reach_lamp_room()

    result = RuntimeEngine(state, _provider("k_tend_lamp", "Ada tends the lamp.")).turn("I tend the lamp.")

    assert state.story_complete is True
    assert "lighthouse_complete" in _true_facts(state)
    assert result.segments[-2].text == "The lighthouse burns steadily through the night."
    assert result.segments[-1].text == "Ada's care keeps the beacon ready for dawn."


def test_missed_window_recovery_reaches_ending_without_outcome_fact() -> None:
    state = _reach_lamp_room()
    engine = RuntimeEngine(state, _provider())

    engine.turn("I wait for the lamp hour.")
    facts_after_window = _true_facts(state)
    assert "lamp_window_missed" in facts_after_window
    assert not {"lamp_tended", "lamp_signal_seen"} & facts_after_window

    result = RuntimeEngine(state, _provider("k_recover_lamp", "Ada restores the lamp watch.")).turn(
        "I restore the lamp watch."
    )

    facts = _true_facts(state)
    assert state.story_complete is True
    assert "lighthouse_complete" in facts
    assert "lamp_recovery_complete" in facts
    assert not {"lamp_tended", "lamp_signal_seen"} & facts
    assert result.segments[-1].text == "The lighthouse burns steadily through the night."
    assert all(segment.text != "Ada's care keeps the beacon ready for dawn." for segment in result.segments)


def test_mid_story_incident_without_successor_is_rejected(tmp_path: Path) -> None:
    package = tmp_path / "lighthouse-incident"
    package.mkdir()
    for source in FIXTURE.iterdir():
        if source.is_file():
            (package / source.name).write_bytes(source.read_bytes())
    incidents_path = package / "incidents.yaml"
    incidents = incidents_path.read_text(encoding="utf-8")
    incidents = incidents.replace("  successor_transition_id: t_1a_1b\n", "", 1)
    incidents_path.write_text(incidents, encoding="utf-8")

    with pytest.raises(StoryPackageError, match="tide_window.*ending scene"):
        load_story_package(package)


def test_transition_bridge_text_is_player_visible() -> None:
    state = RuntimeState.bootstrap(_package())

    result = RuntimeEngine(state, _provider("k_find_key", "Ada finds the brass key.")).turn("I find the brass key.")

    assert any(segment.text == "Ada carries the lantern into the lamp room." for segment in result.segments)
