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


def test_every_declared_pacing_event_lands_inside_its_scene_window() -> None:
    windows = {window.scene_id: window for window in PACKAGE.pacing.scenes}

    assert all(event.at_turn <= windows[event.scene_id].handoff_after_turns for event in PACKAGE.pacing.events)


def test_scene_windows_and_storylet_targets_leave_room_for_every_beat() -> None:
    expected_windows = {
        "1A": (2, 4, 5),
        "1B": (2, 3, 4),
        "1C": (2, 3, 4),
        "2A": (2, 3, 4),
        "2B": (2, 3, 4),
        "2C": (2, 3, 4),
        "3A": (3, 4, 5),
        "3B": (4, 4, 5),
        "3C": (2, 4, 5),
    }
    windows = {window.scene_id: window for window in PACKAGE.pacing.scenes}

    assert {
        scene_id: (window.min_turns, window.nudge_after_turns, window.handoff_after_turns)
        for scene_id, window in windows.items()
    } == expected_windows
    assert sum(window.handoff_after_turns for window in windows.values()) * 45 == PACKAGE.pacing.budget_seconds
    for scene_id, window in windows.items():
        storylets = [storylet for storylet in PACKAGE.storylet_routes.storylets if storylet.scene_id == scene_id]
        targets = [storylet.target_turn for storylet in storylets]
        assert targets == sorted(set(targets))
        assert all(
            storylet.earliest_turn <= storylet.target_turn <= window.handoff_after_turns for storylet in storylets
        )


def test_every_scene_has_at_least_as_many_turns_as_it_has_beats() -> None:
    """A scene with fewer turns than beats cannot cover them, whatever the narrator does.

    This shipped once: 36 authored beats against a 30-turn budget, six scenes
    short, and 3C given two turns for four beats. The handoff then dumped the
    undelivered beats as flat exposition and a player reported it. The hosted
    judge had been complaining in every scene, but its prose is stochastic and
    the cause was misread as narration quality for three rounds. The property is
    static, so it belongs here rather than in an LLM's opinion.
    """

    windows = {window.scene_id: window for window in PACKAGE.pacing.scenes}
    short = {
        scene.metadata.scene_id: (len(scene.beats), windows[scene.metadata.scene_id].handoff_after_turns)
        for scene in PACKAGE.scenes
        if windows[scene.metadata.scene_id].handoff_after_turns < len(scene.beats)
    }
    assert not short, f"scenes with fewer turns than beats (beats, turns): {short}"


def test_storylet_activation_uses_scene_relative_turns_after_a_late_clock() -> None:
    state = RuntimeState.bootstrap(PACKAGE)
    state.facts.assert_fact(Fact(predicate="story_elapsed_seconds", subject="story", value="600"))
    engine = RuntimeEngine(state, _quiet_turn)

    engine._activate_pacing()  # noqa: SLF001 - exercise the pacing boundary directly.
    assert "SL-1A-B" not in state.active_event_ids

    state.turn_index = 2
    engine._activate_pacing()  # noqa: SLF001 - the second scene-relative turn opens the storylet.
    assert "SL-1A-B" in state.active_event_ids


def test_storylet_activation_earns_forward_after_an_earlier_same_scene_beat() -> None:
    state = RuntimeState.bootstrap(PACKAGE)
    state.fired_event_ids.add("SL-1A-A")
    engine = RuntimeEngine(state, _quiet_turn)

    engine._activate_pacing()  # noqa: SLF001 - exercise the pacing boundary directly.

    assert "SL-1A-B" in state.active_event_ids


def test_earned_forward_activation_never_crosses_scene_boundaries() -> None:
    state = RuntimeState.bootstrap(PACKAGE)
    state.fired_event_ids.update({"SL-1A-A", "SL-1A-B", "SL-1A-C", "SL-1A-D"})
    engine = RuntimeEngine(state, _quiet_turn)

    engine._activate_pacing()  # noqa: SLF001 - exercise the pacing boundary directly.

    assert not any(event_id.startswith("SL-1B-") for event_id in state.active_event_ids)


def test_loader_rejects_out_of_order_scene_turn_allocation(tmp_path: Path) -> None:
    root = tmp_path / "package"
    shutil.copytree(Path("data/stories/continuity-initiative"), root)
    source = root / "pacing.yaml"
    old = "min_turns: 2\n  nudge_after_turns: 4"
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
