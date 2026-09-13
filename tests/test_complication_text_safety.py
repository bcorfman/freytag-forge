"""Every pacing realization survives narration safety on its firing turn."""

from __future__ import annotations

from pathlib import Path

import pytest

from storygame.runtime.engine import RuntimeEngine
from storygame.runtime.facts import Fact
from storygame.runtime.state import RuntimeState
from storygame.story_package.loader import load_story_package

PACKAGE = load_story_package(Path("data/stories/continuity-initiative"))
REALIZATIONS = tuple((event, realization) for event in PACKAGE.pacing.events for realization in event.realizations)
REALIZATION_IDS = tuple(
    f"{event.id}-{index}" for event in PACKAGE.pacing.events for index, _realization in enumerate(event.realizations)
)


@pytest.mark.parametrize(
    ("event", "realization"),
    REALIZATIONS,
    ids=REALIZATION_IDS,
)
def test_complication_text_is_accepted_on_event_firing_turn(event, realization) -> None:
    scene = next(item for item in PACKAGE.scenes if item.metadata.scene_id == event.scene_id)
    first_scene_id = PACKAGE.scenes[0].metadata.scene_id
    if event.scene_id == first_scene_id:
        state = RuntimeState.bootstrap(PACKAGE)
    else:
        state = RuntimeState(
            package=PACKAGE,
            current_scene_id=event.scene_id,
            phase=scene.metadata.freytag_phase,
        )

    for guard in realization.when:
        state.facts.assert_fact(Fact(predicate=guard.fact_id, subject="story", value=str(guard.equals).lower()))
    state.turn_index = state.scene_entered_at_turn + event.at_turn - 1

    engine = RuntimeEngine(
        state,
        lambda _input: {"segments": [{"kind": "narration", "text": realization.text}]},
    )

    proposal = engine.turn("Wait and watch the room.")

    assert proposal.segments[0].text == realization.text
