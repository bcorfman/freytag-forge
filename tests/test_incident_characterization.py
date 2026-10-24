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
        ("k_sl_1c_c_copy_numbers", "k_sl_1c_c_secure_route"),
        ("k_sl_1c_c_secure_route", "k_sl_1c_c_copy_numbers"),
    ):
        state = _scene_1c_state()
        state.active_event_ids.add("SL-1C-C")
        _fact(state, "facility_proof")
        _fact(state, "captives_confirmed_alive")

        def provider(_input: str, knowledge_id: str = first) -> dict[str, object]:
            return _turn(_knowledge(knowledge_id).delivery_text, knowledge_id)

        engine = RuntimeEngine(state, provider)
        command = (
            "Copy the prisoner numbers." if first.endswith("copy_numbers") else "Ask Brandon about the transfer route."
        )
        engine.turn(command)

        assert "SL-1C-C" in state.fired_event_ids
        expected = "storylet_spent"
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
    assert bool(forced_cost) is False


def test_1c_incident_outcome_bypasses_min_turns_floor() -> None:
    state = _scene_1c_state()
    for fact_id in ("facility_proof", "captives_confirmed_alive"):
        _fact(state, fact_id)
    engine = RuntimeEngine(
        state,
        lambda _: _turn(
            "Kristin copies the prisoner numbers and matches them to missing-person records.",
            "k_sl_1c_c_copy_numbers",
        ),
    )
    result = engine.turn("Copy the prisoner numbers.")
    assert state.current_scene_id == "2A"
    assert state.turn_index - state.scene_entered_at_turn == 0
    assert result.segments[1].text == "Kristin and Brandon withdraw from the terminal to prepare a way inside."


def test_loader_rejects_pacing_event_beyond_scene_min_turns(tmp_path: Path) -> None:
    root = tmp_path / "continuity-initiative"
    shutil.copytree(PACKAGE_ROOT, root)
    pacing_path = root / "pacing.yaml"
    pacing = yaml.safe_load(pacing_path.read_text(encoding="utf-8"))
    event = next(item for item in pacing["events"] if item["id"] == "transfer_window_1c")
    event["at_turn"] = 8
    pacing_path.write_text(yaml.safe_dump(pacing, sort_keys=False), encoding="utf-8")

    with pytest.raises(StoryPackageError, match="transfer_window_1c.*min_turns floor 7"):
        load_story_package(root)


def test_rejected_turn_restores_security_pacing_then_accepted_turn_fires_it() -> None:
    state = _scene_1c_state()
    state.turn_index = 4
    before = state.snapshot()

    def rejected(_input: str) -> dict[str, object]:
        return {"segments": [{"kind": "narration", "text": "Rebecca is in the room."}]}

    with pytest.raises(ProposalValidationError):
        RuntimeEngine(state, rejected).turn("Wait and watch the terminal.")
    assert state.snapshot() == before
    assert "transfer_window_1c" not in state.fired_event_ids

    accepted = RuntimeEngine(state, lambda _: {"segments": [{"kind": "narration", "text": "The terminal is quiet."}]})
    result = accepted.turn("Wait and watch the terminal.")
    assert "transfer_window_1c" in state.fired_event_ids
    assert Fact(predicate="transfer_window_missed", subject="story", value="true") in state.facts.asserted
    assert state.last_turn_delivery.complication_text == (
        'The view down the observation shaft goes dark. Brandon says, "That chance is gone. '
        "We can still try the service entrance. Follow me through it if you want to try. "
        'We will have to risk the sweep."'
    )
    assert all("transfer line goes dark" not in segment.text for segment in result.segments)


def test_clarification_turn_does_not_advance_pacing() -> None:
    pytest.skip("No short, stable 1C command in today's reference resolver produces ClarificationTurn.")


def test_1c_missed_window_stays_open_past_deadline_without_unearned_facts() -> None:
    state = _scene_1c_state()
    engine = RuntimeEngine(state, lambda _: {"segments": [{"kind": "narration", "text": "The terminal is quiet."}]})
    results = [engine.turn("Wait and watch the terminal.") for _ in range(10)]

    assert state.facts.matching("transfer_window_missed", subject="story")
    assert not state.facts.matching("facility_infiltration_needed", subject="story")
    assert state.current_scene_id == "1C"
    assert state.turn_index == 10
    assert results[-1].segments

    assert state.turn_index == 10
    assert state.current_scene_id == "1C"
    assert not state.facts.matching("facility_infiltration_needed", subject="story")
    assert results[-1].segments
