"""Fixes found by the 2C probe: the monitor light echo, the commitment-turn prompt size and the undeclared guards."""

from __future__ import annotations

import re
from pathlib import Path

from storygame.runtime.item_facts import ItemFactsProvider
from storygame.runtime.state import RuntimeState
from storygame.runtime.validation import unconveyed_terms
from storygame.runtime.world_model import apply_scene_placements
from storygame.story_package.loader import load_story_package

LIVE_PACKAGE = Path("data/stories/continuity-initiative")
FROZEN_PACKAGE = Path("bench/frozen/continuity-pre-richer-2c")
PACKAGE = load_story_package(LIVE_PACKAGE)
FROZEN = load_story_package(FROZEN_PACKAGE)


def _collapse(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip()


def _entries() -> dict:
    return {entry.id: entry for entry in PACKAGE.knowledge.knowledge}


def _scene(package, scene_id: str = "2C"):
    return next(scene for scene in package.scenes if scene.metadata.scene_id == scene_id)


def test_the_monitor_light_delivery_says_only_what_is_new() -> None:
    entry = _entries()["k_sl_2c_h_r1"]
    assert _collapse(entry.delivery_text) == "Whatever goes out will be seen."
    assert [list(group) for group in entry.must_convey] == [["seen"]]
    assert unconveyed_terms(entry.must_convey, entry.delivery_text) == ()


def test_what_the_new_things_show_lives_in_their_placement_text() -> None:
    placements = _scene(PACKAGE).metadata.item_placements
    light = placements["monitor_light"].text.casefold()
    assert "amber" in light and "one outbound channel" in light
    assert "brandon" in placements["corridor_camera"].text.casefold()
    assert placements["cart_tags"].text


def test_the_new_things_add_nothing_to_the_scene_details() -> None:
    live = [list(beat.details) for beat in _scene(PACKAGE).beats.values()]
    frozen = [list(beat.details) for beat in _scene(FROZEN).beats.values()]
    assert live == frozen


def test_the_matched_ticket_sentence_is_short() -> None:
    entries = _entries()
    for entry_id in ("k_sl_2c_d_r3", "k_sl_2c_d_r4"):
        entry = entries[entry_id]
        variant = next(item for item in entry.delivery_variants if "ticket_header_matched" in item.requires)
        text = _collapse(variant.text).casefold()
        assert len(_collapse(variant.text)) - len(_collapse(entry.delivery_text)) <= 60, entry_id
        assert "maintenance ticket" in text and "sensor fault" in text and "archive" in text, entry_id
        assert "ticket header" not in text, entry_id


def test_the_corridor_guards_are_a_declared_group_in_2c() -> None:
    groups = {group.id: group for group in PACKAGE.world.groups}
    assert "corridor_guards" in groups
    assert groups["corridor_guards"].name == "corridor guards"
    assert groups["corridor_guards"].scoped_aliases == ("guards", "guard")
    placement = _scene(PACKAGE).metadata.character_placements["corridor_guards"]
    assert placement.parent == "purge_chamber" and placement.text
    assert "corridor_guards" not in {item.id for item in FROZEN.world.items}


def test_the_matching_prompt_lists_the_corridor_guards() -> None:
    scene = _scene(PACKAGE)
    state = RuntimeState.bootstrap(PACKAGE)
    state.current_scene_id = "2C"
    state.phase = scene.metadata.freytag_phase
    state._assert_scene_entry_fact("2C")
    apply_scene_placements(PACKAGE, state.facts, "2C")
    provider = ItemFactsProvider(
        worker_url="https://worker.example/turn",
        token="",
        state=state,
        item_facts={},
        mode="single_call",
        seed_from_package=True,
        held_by=True,
    )
    provider.prepare_turn("Tell Rebecca nothing.")
    provider.assemble_turn_prompt("Tell Rebecca nothing.")
    things = provider.last_prompt["user"].split("THINGS:")[1].split("NEW NAMES:")[0]
    assert "corridor guards" in things
