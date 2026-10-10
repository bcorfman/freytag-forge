"""Emergency surface gates are scoped only to the scenes that use them."""

from __future__ import annotations

from pathlib import Path

import pytest

from storygame.runtime.engine import RuntimeEngine
from storygame.runtime.state import RuntimeState
from storygame.runtime.validation import ProposalValidationError
from storygame.story_package.loader import load_story_package

PACKAGE = load_story_package(Path("data/stories/continuity-initiative"))
ITEM_ID = "emergency_surface_gates"


def _scene(scene_id: str):
    return next(scene for scene in PACKAGE.scenes if scene.metadata.scene_id == scene_id)


def _narrate(scene_id: str, text: str) -> None:
    scene = _scene(scene_id)
    state = RuntimeState(package=PACKAGE, current_scene_id=scene_id, phase=scene.metadata.freytag_phase)
    state._assert_scene_entry_fact(scene_id)
    payload = {"segments": [{"kind": "narration", "text": text, "grounding_ids": []}]}
    RuntimeEngine(state, lambda _player_input: payload).turn("Inspect the emergency surface gates.")


def test_surface_gates_are_declared_and_placed_only_in_scenes_3a_through_3c() -> None:
    for scene_id in ("3A", "3B", "3C"):
        metadata = _scene(scene_id).metadata
        assert ITEM_ID in metadata.item_ids
        assert metadata.item_placements[ITEM_ID].parent == "facility_escape"

    for scene_id in ("1A", "1B", "1C", "2A", "2B", "2C"):
        metadata = _scene(scene_id).metadata
        assert ITEM_ID not in metadata.item_ids
        assert ITEM_ID not in metadata.item_placements


@pytest.mark.parametrize("scene_id", ["3A", "3B"])
@pytest.mark.parametrize(
    "text",
    [
        "Kristin looks at the emergency surface gates.",
        "The surface gates are shut.",
    ],
)
def test_surface_gates_can_be_narrated_in_scenes_3a_and_3b(scene_id: str, text: str) -> None:
    _narrate(scene_id, text)


def test_surface_gates_are_rejected_in_scene_1a() -> None:
    with pytest.raises(ProposalValidationError) as caught:
        _narrate("1A", "Kristin looks at the emergency surface gates.")

    assert caught.value.code == "narration_known_term_leak"
