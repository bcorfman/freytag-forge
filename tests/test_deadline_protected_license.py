"""Deadline handoffs license protected terms in their authored fallback text."""

from __future__ import annotations

import json
from copy import deepcopy
from pathlib import Path

import pytest

from storygame.runtime.contracts import NarrationSegment, ResolvedTurnProposal
from storygame.runtime.engine import RuntimeEngine
from storygame.runtime.knowledge import KnowledgeProjector
from storygame.runtime.narration_safety import NarrationSafetyValidator
from storygame.runtime.state import RuntimeState
from storygame.runtime.validation import ProposalValidationError
from storygame.story_package.loader import load_story_package
from storygame.story_package.models import FactDelivery

PACKAGE = load_story_package(Path("data/stories/continuity-initiative"))


class _Response:
    def __init__(self, payload: object) -> None:
        self.payload = json.dumps(payload).encode()

    def __enter__(self) -> _Response:
        return self

    def __exit__(self, *_args: object) -> None:
        return None

    def read(self) -> bytes:
        return self.payload


def _windows() -> dict[str, int]:
    return {window.scene_id: window.handoff_after_turns for window in PACKAGE.pacing.scenes}


def _drive_to_scene(engine: RuntimeEngine, state: RuntimeState, target: str) -> dict[str, int]:
    windows = _windows()
    exits: dict[str, int] = {}
    max_turns = sum(windows.values())

    for _ in range(max_turns):
        if state.current_scene_id == target:
            return exits
        source_scene = state.current_scene_id
        turn_in_scene = state.turn_index - state.scene_entered_at_turn + 1
        assert turn_in_scene <= windows[source_scene]
        engine.turn("Wait and watch the room.")
        if state.current_scene_id != source_scene:
            exits[source_scene] = turn_in_scene

    pytest.fail(f"did not reach {target}; stopped in {state.current_scene_id}")


def test_staged_fallback_licenses_only_protected_terms_it_contains() -> None:
    delivery = FactDelivery(
        fact_id="synthetic_handoff",
        scene_id="1A",
        source_kind="observation",
        must_convey=(("JANUS archive",), ("archive opens",)),
        fallback_text="The JANUS archive opens.",
    )
    package = PACKAGE.model_copy(update={"deliveries": (*PACKAGE.deliveries, delivery)})
    state = RuntimeState.bootstrap(package)
    state.staged_handoff_fact_ids = ("synthetic_handoff",)
    candidate_state = deepcopy(state)
    validator = NarrationSafetyValidator()

    validator.validate(
        state,
        candidate_state,
        ResolvedTurnProposal(segments=(NarrationSegment(kind="narration", text="The JANUS archive opens."),)),
        KnowledgeProjector(),
        "Search the kitchen.",
    )

    with pytest.raises(ProposalValidationError) as caught:
        validator.validate(
            state,
            candidate_state,
            ResolvedTurnProposal(
                segments=(
                    NarrationSegment(kind="narration", text="The JANUS archive opens. The selection system waits."),
                )
            ),
            KnowledgeProjector(),
            "Search the kitchen.",
        )

    assert caught.value.code == "protected_narration_leak"
    assert "selection system" in str(caught.value)
