"""Every authored cue must survive narration safety at its scene nudge."""

from __future__ import annotations

from pathlib import Path

import pytest

from storygame.runtime.engine import RuntimeEngine
from storygame.runtime.state import RuntimeState
from storygame.story_package.loader import load_story_package
from storygame.story_package.models import FactDelivery

PACKAGE = load_story_package(Path("data/stories/continuity-initiative"))
CUE_DELIVERIES = tuple(delivery for delivery in PACKAGE.deliveries if delivery.cue_text is not None)


@pytest.mark.parametrize(
    "delivery",
    CUE_DELIVERIES,
    ids=lambda delivery: f"{delivery.scene_id}-{delivery.fact_id}",
)
def test_cue_text_is_accepted_at_its_scene_nudge(delivery: FactDelivery) -> None:
    scene = next(item for item in PACKAGE.scenes if item.metadata.scene_id == delivery.scene_id)
    window = next(item for item in PACKAGE.pacing.scenes if item.scene_id == delivery.scene_id)
    if scene.metadata.scene_id == PACKAGE.scenes[0].metadata.scene_id:
        state = RuntimeState.bootstrap(PACKAGE)
    else:
        state = RuntimeState(
            package=PACKAGE,
            current_scene_id=scene.metadata.scene_id,
            phase=scene.metadata.freytag_phase,
        )
    state.turn_index = window.nudge_after_turns - 1
    cue_text = delivery.cue_text
    assert cue_text is not None

    engine = RuntimeEngine(
        state,
        lambda _input: {"segments": [{"kind": "narration", "text": cue_text}]},
    )

    proposal = engine.turn("Look around carefully.")

    assert proposal.segments[0].text == cue_text
    assert state.turn_index == window.nudge_after_turns
