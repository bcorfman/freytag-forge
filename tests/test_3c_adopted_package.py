from __future__ import annotations

import re
from pathlib import Path

from storygame.story_package.loader import load_story_package
from tests.story_source.helpers import compiled_story_copy, load_compiled_copy, patch_source

ROOT = Path(__file__).parents[1]
SHIPPED_ROOT = ROOT / "data/stories/continuity-initiative"

SHIPPED_ENTRY_TEXT = (
    "The broadcast chamber lights are steady. Brandon's relay is open. "
    "Michelle's evidence package is ready to send. Water is entering the outer access level.\n\n"
)


def test_frozen_pump_application_reproduces_the_shipped_package(tmp_path: Path) -> None:
    old_entry = (
        "The broadcast chamber lights steadied as Brandon's relay held open. Outside, Charles's "
        "emergency deluge was filling the outer access level and forcing water toward the maintenance routes; "
        "inside, the evidence was ready to leave for good.\n\n"
    )
    old_delivery = "The payload is intentionally different."
    migrated = compiled_story_copy(tmp_path)
    patch_source(migrated / "source", "scenes/3C.yaml", "entry", old_entry)
    patch_source(migrated / "source", "scenes/3C.yaml", "reveals[sl_3c_b].variants.r1.text", old_delivery)
    frozen = load_compiled_copy(migrated)

    frozen_scene = next(scene for scene in frozen.scenes if scene.metadata.scene_id == "3C")
    assert frozen_scene.metadata.entry_text == old_entry
    assert frozen.knowledge_indexes.by_id["k_sl_3c_b_r1"].delivery_text == old_delivery

    shipped = load_story_package(SHIPPED_ROOT)
    shipped_scene = next(scene for scene in shipped.scenes if scene.metadata.scene_id == "3C")
    assert shipped_scene.metadata.entry_text == SHIPPED_ENTRY_TEXT
    assert len(re.split(r"(?<=[.!?])\s+", shipped.knowledge_indexes.by_id["k_sl_3c_b_r1"].delivery_text)) == 4


def test_shipped_package_loads_and_b_r1_establishes_neither_c_fact() -> None:
    package = load_story_package(SHIPPED_ROOT)
    scene_3c = next(scene for scene in package.scenes if scene.metadata.scene_id == "3C")
    assert scene_3c.metadata.entry_text == SHIPPED_ENTRY_TEXT

    b_r1 = package.knowledge_indexes.by_id["k_sl_3c_b_r1"]
    assert len(re.split(r"(?<=[.!?])\s+", b_r1.delivery_text)) == 4
    c_fact_ids = {
        effect.fact_id
        for c_id in ("k_sl_3c_c_r1", "k_sl_3c_c_r2")
        for effect in package.knowledge_indexes.by_id[c_id].establishes
    }
    assert c_fact_ids.isdisjoint({effect.fact_id for effect in b_r1.establishes})


def test_shipped_package_resolves_3c_items_only_in_scene_3c() -> None:
    package = load_story_package(SHIPPED_ROOT)
    scene_3c = next(scene for scene in package.scenes if scene.metadata.scene_id == "3C")
    item_ids = {item.id for item in package.world.items}

    assert {"emergency_speakers", "watertight_barrier"} <= item_ids
    assert {"emergency_speakers", "watertight_barrier"} <= set(scene_3c.metadata.item_ids)
    assert scene_3c.metadata.item_placements["emergency_speakers"].parent == "maintenance_network"
    assert scene_3c.metadata.item_placements["watertight_barrier"].parent == "maintenance_network"
    for scene in package.scenes:
        if scene.metadata.scene_id != "3C":
            assert not {"emergency_speakers", "watertight_barrier"} & set(scene.metadata.item_ids)
            assert not {"emergency_speakers", "watertight_barrier"} & set(scene.metadata.item_placements)
