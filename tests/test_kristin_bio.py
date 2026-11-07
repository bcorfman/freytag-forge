from __future__ import annotations

from pathlib import Path

import pytest

from storygame.runtime.item_facts import ItemFactsProvider
from storygame.runtime.state import RuntimeState
from storygame.runtime.world_model import apply_scene_placements
from storygame.story_package.loader import load_story_package

PACKAGE = load_story_package(Path("data/stories/continuity-initiative"))
SCENES = ("1A", "1B", "1C", "2A", "2B", "2C", "3A", "3B", "3C")


def _prompt(package, scene_id: str) -> tuple[str, str]:
    scene = next(scene for scene in package.scenes if scene.metadata.scene_id == scene_id)
    state = RuntimeState.bootstrap(package)
    state.current_scene_id = scene_id
    state.phase = scene.metadata.freytag_phase
    state._assert_scene_entry_fact(scene_id)
    apply_scene_placements(package, state.facts, scene_id)
    provider = ItemFactsProvider(
        worker_url="https://worker.example/turn",
        token="",
        state=state,
        item_facts={},
        mode="single_call",
        seed_from_package=True,
        held_by=True,
    )
    provider.prepare_turn("Look around.")
    prompt = provider.assemble_turn_prompt("Look around.")
    return prompt["system"], provider._section_user_prompt(prompt["context"])


def test_kristin_bio_names_no_goal() -> None:
    """A goal changes by scene; the scene's own pressure line carries it."""

    bio = next(npc.narrator_bio for npc in PACKAGE.world.npcs if npc.id == "kristin")
    assert "wants" not in bio


@pytest.mark.parametrize("scene_id", SCENES)
def test_every_scene_prompt_carries_its_own_goal_for_kristin(scene_id: str) -> None:
    _, user = _prompt(PACKAGE, scene_id)
    assert "What presses on Kristin now: " in user
