from __future__ import annotations

from pathlib import Path

import pytest

from storygame.personas import _ScriptedProvider
from storygame.runtime.engine import RuntimeEngine
from storygame.runtime.state import RuntimeState
from storygame.story_package.loader import load_story_package

PACKAGE = load_story_package(Path("data/stories/continuity-initiative"))


@pytest.mark.parametrize(
    "scene_id",
    [
        *[scene.metadata.scene_id for scene in PACKAGE.scenes if scene.metadata.scene_id != "3C"],
        pytest.param("3C", marks=pytest.mark.xfail(strict=True, reason="neutral stalling has no bounded exit in 3C")),
    ],
)
def test_neutral_staller_leaves_each_scene_by_handoff_plus_three(scene_id: str) -> None:
    state = RuntimeState.bootstrap(PACKAGE)
    state.current_scene_id = scene_id
    state.phase = next(scene.metadata.freytag_phase for scene in PACKAGE.scenes if scene.metadata.scene_id == scene_id)
    state._assert_scene_entry_fact(scene_id)
    provider = _ScriptedProvider(PACKAGE, state)
    engine = RuntimeEngine(state, provider)
    window = next(item for item in PACKAGE.pacing.scenes if item.scene_id == scene_id)
    bound = window.handoff_after_turns + 3

    for _ in range(bound):
        provider.selected = ()
        engine.turn("Inspect the nearest concrete feature for a safe route.")
        if state.current_scene_id != scene_id or state.story_complete:
            break

    assert state.current_scene_id != scene_id or state.story_complete
