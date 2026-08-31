from __future__ import annotations

import shutil
from pathlib import Path

import pytest

from storygame.runtime.engine import RuntimeEngine
from storygame.runtime.facts import Fact
from storygame.runtime.state import RuntimeState
from storygame.story_package import StoryPackageError, load_story_package

PACKAGE = load_story_package(Path("data/stories/continuity-initiative"))


def _quiet_turn(_input: str) -> dict[str, object]:
    return {"segments": [{"kind": "narration", "text": "The investigation continues."}]}


def test_turn_index_keeps_counting_and_scene_entry_resets_relative_turns() -> None:
    state = RuntimeState.bootstrap(PACKAGE)
    state.facts.assert_fact(Fact(predicate="michelle_lead_actionable", subject="story", value="true"))
    state.facts.assert_fact(Fact(predicate="patrol_return_pressure", subject="story", value="true"))
    engine = RuntimeEngine(state, _quiet_turn)

    engine.turn("I investigate.")
    assert state.turn_index == 1
    assert state.current_scene_id == "1A"
    assert state.turn_index - state.scene_entered_at_turn == 1

    engine.turn("I leave when the lead is ready.")
    assert state.turn_index == 2
    assert state.current_scene_id == "1B"
    assert state.scene_entered_at_turn == 2
    assert state.turn_index - state.scene_entered_at_turn == 0

    engine.turn("I keep moving.")
    assert state.turn_index == 3
    assert state.turn_index - state.scene_entered_at_turn == 1


def test_min_turns_floor_blocks_a_committed_trigger_until_source_turns_are_played() -> None:
    state = RuntimeState.bootstrap(PACKAGE)
    state.facts.assert_fact(Fact(predicate="michelle_lead_actionable", subject="story", value="true"))
    state.facts.assert_fact(Fact(predicate="patrol_return_pressure", subject="story", value="true"))
    engine = RuntimeEngine(state, _quiet_turn)

    engine.turn("I rush toward the exit.", clock_seconds=3600)
    assert state.current_scene_id == "1A"

    engine.turn("I take the lead and go.", clock_seconds=0)
    assert state.current_scene_id == "1B"


def test_each_scene_entry_starts_with_a_full_relative_turn_allowance() -> None:
    state = RuntimeState.bootstrap(PACKAGE)
    engine = RuntimeEngine(state, _quiet_turn)

    for transition in PACKAGE.pacing.transitions:
        window = next(item for item in PACKAGE.pacing.scenes if item.scene_id == transition.source_scene_id)
        for _ in range(window.min_turns):
            engine.turn("I take another careful turn.")
        if state.current_scene_id != transition.target_scene_id:
            for trigger in transition.triggers:
                state.facts.assert_fact(
                    Fact(predicate=trigger.fact_id, subject="story", value=str(trigger.equals).lower())
                )
            engine.turn("I follow the opening.")
        assert state.current_scene_id == transition.target_scene_id
        assert state.turn_index == state.scene_entered_at_turn


def test_every_declared_pacing_event_lands_by_its_scene_floor() -> None:
    windows = {window.scene_id: window for window in PACKAGE.pacing.scenes}

    assert all(event.at_turn <= windows[event.scene_id].min_turns for event in PACKAGE.pacing.events)


def test_storylet_activation_uses_scene_relative_turns_after_a_late_clock() -> None:
    state = RuntimeState.bootstrap(PACKAGE)
    state.facts.assert_fact(Fact(predicate="story_elapsed_seconds", subject="story", value="600"))
    engine = RuntimeEngine(state, _quiet_turn)

    engine._activate_pacing()  # noqa: SLF001 - exercise the pacing boundary directly.
    assert "SL-1A-B" not in state.active_event_ids

    state.turn_index = 2
    engine._activate_pacing()  # noqa: SLF001 - the second scene-relative turn opens the storylet.
    assert "SL-1A-B" in state.active_event_ids


def test_loader_rejects_out_of_order_scene_turn_allocation(tmp_path: Path) -> None:
    root = tmp_path / "package"
    shutil.copytree(Path("data/stories/continuity-initiative"), root)
    source = root / "pacing.yaml"
    old = "min_turns: 2\n  nudge_after_turns: 2"
    new = "min_turns: 3\n  nudge_after_turns: 2"
    source.write_text(source.read_text().replace(old, new, 1))

    with pytest.raises(StoryPackageError, match="turn allocations must be ordered"):
        load_story_package(root)


def test_loader_rejects_handoff_sum_over_budget(tmp_path: Path) -> None:
    root = tmp_path / "package"
    shutil.copytree(Path("data/stories/continuity-initiative"), root)
    source = root / "pacing.yaml"
    source.write_text(source.read_text().replace("budget_seconds: 1800", "budget_seconds: 1799", 1))

    with pytest.raises(StoryPackageError, match="handoff sum.*budget_seconds"):
        load_story_package(root)
