"""Real prompt-size budgets for every scene, so richer scenes cannot silently bloat what the models read.

Measured 2026-11-02 at scene start with the network stubbed: the narrator prompt (system plus user) is 4.0 to
4.4k characters in every scene and the item-matching prompt is 1.9 to 2.9k. The matching prompt lists every thing in
the scene, so it grows as a scene gets richer; the narrator sees a THINGS line only for things the matcher resolved
from the command, so its worst case is its turn-start size plus the whole scene's THINGS lines.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from storygame.runtime.item_facts import ItemFactsProvider
from storygame.runtime.state import RuntimeState
from storygame.runtime.world_model import apply_scene_placements
from storygame.story_package.loader import load_story_package

PACKAGE = load_story_package(Path("data/stories/continuity-initiative"))
NARRATION_CHARACTERS = 5000
MATCH_CHARACTERS = 3500
NARRATION_WORST_CASE_CHARACTERS = 6500
MATCH_THING_LINES = 30


def _prompts(scene_id: str) -> tuple[int, int, int, int]:
    scene = next(scene for scene in PACKAGE.scenes if scene.metadata.scene_id == scene_id)
    state = RuntimeState.bootstrap(PACKAGE)
    state.current_scene_id = scene_id
    state.phase = scene.metadata.freytag_phase
    state._assert_scene_entry_fact(scene_id)
    apply_scene_placements(PACKAGE, state.facts, scene_id)
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
    narration = len(prompt["system"]) + len(provider._section_user_prompt(prompt["context"]))
    match = provider.last_prompt
    things_block = match["user"].split("THINGS:")[1].split("NEW NAMES:")[0]
    return narration, len(match["system"]) + len(match["user"]), things_block.count("\n- "), len(things_block)


@pytest.mark.parametrize("scene_id", [scene.metadata.scene_id for scene in PACKAGE.scenes])
def test_every_scene_stays_inside_the_prompt_budgets(scene_id: str) -> None:
    narration, match, thing_lines, things_characters = _prompts(scene_id)
    assert narration <= NARRATION_CHARACTERS, f"narrator prompt is {narration} characters"
    assert match <= MATCH_CHARACTERS, f"matching prompt is {match} characters"
    assert thing_lines <= MATCH_THING_LINES, f"matching prompt lists {thing_lines} things"
    # Worst case: the matcher resolves every listed thing, so the narrator also sees each THINGS line.
    assert narration + things_characters <= NARRATION_WORST_CASE_CHARACTERS
