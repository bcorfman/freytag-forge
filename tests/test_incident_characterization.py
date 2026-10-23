from __future__ import annotations

import shutil
from pathlib import Path

import pytest
import yaml

from storygame.runtime.engine import RuntimeEngine
from storygame.runtime.facts import Fact
from storygame.runtime.reveal_eligibility import explain_reveal
from storygame.runtime.state import RuntimeState
from storygame.runtime.validation import ProposalValidationError
from storygame.story_package.loader import StoryPackageError, load_story_package

PACKAGE_ROOT = Path("data/stories/continuity-initiative")
PACKAGE = load_story_package(PACKAGE_ROOT)


def _scene_1c_state() -> RuntimeState:
    state = RuntimeState.bootstrap(PACKAGE)
    state.current_scene_id = "1C"
    state.phase = next(scene.metadata.freytag_phase for scene in PACKAGE.scenes if scene.metadata.scene_id == "1C")
    state._assert_scene_entry_fact("1C")
    return state


def _fact(state: RuntimeState, fact_id: str) -> None:
    state.facts.assert_fact(Fact(predicate=fact_id, subject="story", value="true"))


def _turn(text: str, selected: str | None = None) -> dict[str, object]:
    segment: dict[str, object] = {"kind": "narration", "text": text}
    if selected:
        segment["grounding_ids"] = [selected]
    return {"segments": [segment], "selected_knowledge_ids": [selected] if selected else []}


def _knowledge(knowledge_id: str):
    return PACKAGE.knowledge_indexes.by_id[knowledge_id]


def test_1c_realizations_are_exclusive_once_the_storylet_fires() -> None:
    for first, other in (
        ("k_sl_1c_a_r1", "k_sl_1c_a_r2"),
        ("k_sl_1c_a_r2", "k_sl_1c_a_r1"),
    ):
        state = _scene_1c_state()
        state.active_event_ids.add("SL-1C-A")

        def provider(_input: str, knowledge_id: str = first) -> dict[str, object]:
            return _turn(_knowledge(knowledge_id).delivery_text, knowledge_id)

        engine = RuntimeEngine(state, provider)
        engine.turn("Inspect the terminal for signs of activity.")

        assert "SL-1C-A" in state.fired_event_ids
        expected = "storylet_spent" if first.endswith("r1") else "already_established"
        assert explain_reveal(state, "player", _knowledge(other)).reason == expected


def test_1c_earned_reveal_and_forced_handoff_pin_delivery_cost_behavior() -> None:
    earned = _scene_1c_state()
    _fact(earned, "facility_proof")
    earned.active_event_ids.add("SL-1C-B")
    RuntimeEngine(earned, lambda _: _turn(_knowledge("k_sl_1c_b_r1").delivery_text, "k_sl_1c_b_r1")).turn(
        "Read the identification numbers on the uniforms below."
    )
    earned_cost = earned.facts.matching("evidence_gap_processing_numbers", subject="story")

    forced = _scene_1c_state()
    _fact(forced, "facility_proof")
    forced.staged_handoff_fact_ids = ("captives_confirmed_alive",)
    RuntimeEngine(forced, lambda _: {"segments": [{"kind": "narration", "text": "The view is brief."}]}).turn(
        "Search the processing line."
    )
    forced_cost = forced.facts.matching("evidence_gap_processing_numbers", subject="story")

    assert bool(earned_cost) is False
    assert bool(forced_cost) is True


def test_1c_min_turns_floor_delays_bridge_transition_until_turn_seven() -> None:
    state = _scene_1c_state()
    for fact_id in ("facility_proof", "captives_confirmed_alive", "national_detention_network_known"):
        _fact(state, fact_id)
    engine = RuntimeEngine(state, lambda _: {"segments": [{"kind": "narration", "text": "The terminal is quiet."}]})

    for _ in range(6):
        result = engine.turn("Wait and watch the terminal.")
        assert state.current_scene_id == "1C"
        assert state.turn_index - state.scene_entered_at_turn < 7
        assert result.segments
    result = engine.turn("Wait and watch the terminal.")
    assert state.current_scene_id == "2A"
    assert state.turn_index - state.scene_entered_at_turn == 0
    assert result.segments[0].text == "The terminal is quiet."
    assert result.segments[1].text.startswith("The observation shaft showed them living captives")


def test_loader_rejects_pacing_event_beyond_scene_min_turns(tmp_path: Path) -> None:
    root = tmp_path / "continuity-initiative"
    shutil.copytree(PACKAGE_ROOT, root)
    pacing_path = root / "pacing.yaml"
    pacing = yaml.safe_load(pacing_path.read_text(encoding="utf-8"))
    event = next(item for item in pacing["events"] if item["id"] == "security_1c")
    event["at_turn"] = 8
    pacing_path.write_text(yaml.safe_dump(pacing, sort_keys=False), encoding="utf-8")

    with pytest.raises(StoryPackageError, match="security_1c.*min_turns floor 7"):
        load_story_package(root)


def test_rejected_turn_restores_security_pacing_then_accepted_turn_fires_it() -> None:
    state = _scene_1c_state()
    state.turn_index = 2
    before = state.snapshot()

    def rejected(_input: str) -> dict[str, object]:
        return {"segments": [{"kind": "narration", "text": "Rebecca is in the room."}]}

    with pytest.raises(ProposalValidationError):
        RuntimeEngine(state, rejected).turn("Wait and watch the terminal.")
    assert state.snapshot() == before
    assert "security_1c" not in state.fired_event_ids

    accepted = RuntimeEngine(state, lambda _: {"segments": [{"kind": "narration", "text": "The terminal is quiet."}]})
    result = accepted.turn("Wait and watch the terminal.")
    assert "security_1c" in state.fired_event_ids
    assert Fact(predicate="terminal_security_escalating", subject="story", value="true") in state.facts.asserted
    assert state.last_turn_delivery.complication_text == "Security is escalating around the terminal."
    assert all("Security is escalating" not in segment.text for segment in result.segments)


def test_clarification_turn_does_not_advance_pacing() -> None:
    pytest.skip("No short, stable 1C command in today's reference resolver produces ClarificationTurn.")


def test_1c_missed_window_deadline_backstop_forces_2a_with_unearned_facts() -> None:
    state = _scene_1c_state()
    engine = RuntimeEngine(state, lambda _: {"segments": [{"kind": "narration", "text": "The terminal is quiet."}]})
    results = [engine.turn("Wait and watch the terminal.") for _ in range(10)]

    assert state.facts.matching("terminal_security_escalating", subject="story")
    assert state.facts.matching("terminal_sweep_closing", subject="story")
    assert not state.facts.matching("facility_infiltration_needed", subject="story")
    assert state.current_scene_id == "1C"
    assert state.turn_index == 10
    assert results[-1].segments

    deadline = engine.turn("Wait and watch the terminal.")
    assert state.turn_index == 11
    assert state.current_scene_id == "2A"
    assert state.facts.matching("facility_infiltration_needed", subject="story")
    assert deadline.segments
