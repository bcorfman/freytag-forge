"""Every authored cue and escalation pointer must survive narration safety.

A pointer that safety rejects would reject every turn from the nudge on, because a
rejected turn leaves the pointer staged. The loader does not check this, so this
test is the gate for shipped text.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from storygame.runtime.engine import RuntimeEngine
from storygame.runtime.facts import Fact
from storygame.runtime.state import RuntimeState
from storygame.runtime.validation import ProposalValidationError
from storygame.story_package.loader import load_story_package
from storygame.story_package.models import FactDelivery

PACKAGE = load_story_package(Path("data/stories/continuity-initiative"))
CUE_DELIVERIES = tuple(delivery for delivery in PACKAGE.deliveries if delivery.cue_text is not None)
POINTERS = tuple(
    [(delivery, 1, delivery.cue_text) for delivery in CUE_DELIVERIES]
    + [(delivery, 2, delivery.escalation_text) for delivery in PACKAGE.deliveries if delivery.escalation_text]
)


@pytest.mark.parametrize(
    ("delivery", "stage", "cue_text"),
    POINTERS,
    ids=lambda value: f"{value.scene_id}-{value.fact_id}" if isinstance(value, FactDelivery) else None,
)
def test_cue_text_is_accepted_on_the_first_scene_turn(delivery: FactDelivery, stage: int, cue_text: str) -> None:
    scene = next(item for item in PACKAGE.scenes if item.metadata.scene_id == delivery.scene_id)
    if scene.metadata.scene_id == PACKAGE.scenes[0].metadata.scene_id:
        state = RuntimeState.bootstrap(PACKAGE)
    else:
        state = RuntimeState(
            package=PACKAGE,
            current_scene_id=scene.metadata.scene_id,
            phase=scene.metadata.freytag_phase,
        )
        state._assert_scene_entry_fact(scene.metadata.scene_id)  # noqa: SLF001 - model the first turn in this scene.
    for knowledge in PACKAGE.knowledge.knowledge:
        if knowledge.available_in_scenes and scene.metadata.scene_id not in knowledge.available_in_scenes:
            continue
        if not any(effect.fact_id == delivery.fact_id and effect.op == "assert" for effect in knowledge.establishes):
            continue
        for requirement in knowledge.requires:
            state.facts.assert_fact(Fact(predicate=requirement.fact_id, subject="story", value="true"))
    state.staged_cue_fact_id = delivery.fact_id
    state.staged_cue_stage = stage
    if stage == 2:
        state.delivered_cue_ids = (delivery.fact_id,)
    state.turn_index = 0

    engine = RuntimeEngine(
        state,
        lambda _input: {"segments": [{"kind": "narration", "text": cue_text}]},
    )

    proposal = engine.turn("Look around carefully.")

    assert proposal.segments[-1].text == cue_text
    scene_cue_ids = {item.fact_id for item in CUE_DELIVERIES if item.scene_id == delivery.scene_id}
    assert not state.delivered_cue_ids or state.delivered_cue_ids[0] in scene_cue_ids
    assert state.staged_cue_fact_id is None
    assert state.turn_index == 1


def test_unsafe_escalation_text_is_rejected_by_narration_safety() -> None:
    """The gate above has teeth: a pointer naming a later secret fails safety."""

    delivery = CUE_DELIVERIES[0]
    secret = "Phase Two"
    state = RuntimeState.bootstrap(PACKAGE)
    state.staged_cue_fact_id = delivery.fact_id
    state.staged_cue_stage = 2
    state.delivered_cue_ids = (delivery.fact_id,)
    text = f"The workstation hints at {secret}."
    engine = RuntimeEngine(state, lambda _input: {"segments": [{"kind": "narration", "text": text}]})

    with pytest.raises(ProposalValidationError) as caught:
        engine.turn("Look around carefully.")

    assert caught.value.code == "protected_narration_leak"
