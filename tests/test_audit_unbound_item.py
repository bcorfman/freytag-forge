from __future__ import annotations

import shutil
from pathlib import Path

from storygame.audit import _markdown, delivery_names_unbound_item
from storygame.story_package.loader import load_story_package
from tests.story_source.helpers import DELETE, copy_fixture, load_compiled_copy, patch_source

# Pairs awaiting review. The 3A stolen-radio pairs were resolved by the fact_effects
# move on detention_uprising_started; the rest may be real missing effects or benign.
KNOWN_UNBOUND = frozenset(
    {
        ("k_sl_1a_a_r1", "michelle_phone"),
        ("k_sl_1a_a_r1", "workstation_chair"),
        ("k_sl_1a_c_r1", "lake_photograph"),
        ("k_sl_1a_g_r1", "michelle_reading_glasses"),
        ("k_sl_1a_g_r1", "michelle_tea_mug"),
        ("k_sl_1a_g_r1", "manuscript_pages"),
        ("k_sl_1c_c_secure_route", "transit_card"),
        ("k_sl_3c_a_r1", "portable_archive"),
        ("k_sl_3c_a_r2", "portable_archive"),
    }
)
SCENE_ITEM_OVERRIDES: dict[Path, list[str]] = {}


def _package(
    tmp_path: Path,
    *,
    item_ids: list[str] | None = None,
    knowledge: list[dict] | None = None,
    items: list[dict] | None = None,
    fact_effects: dict | None = None,
    extra_scene: bool = False,
) -> Path:
    root = copy_fixture("mini_ok", tmp_path)
    source = root / "source"
    source.mkdir()
    for path in tuple(root.glob("*.yaml")):
        shutil.move(str(path), source / path.name)
    shutil.move(str(root / "scenes"), source / "scenes")
    root.joinpath("ownership.yaml").write_text(
        "schema: 1\ncatalog: compiled\nscenes:\n  1A: compiled\n  2C: compiled\n", encoding="utf-8"
    )
    entry = (knowledge or [_entry()])[0]
    patch_source(root, "source/catalog.yaml", "characters.kristin.name", "Ada")
    patch_source(root, "source/catalog.yaml", "characters.kristin.aliases", ["Ada"])
    patch_source(root, "source/catalog.yaml", "items.memory_card.name", "brass lantern")
    patch_source(root, "source/catalog.yaml", "items.memory_card.aliases", [])
    patch_source(root, "source/catalog.yaml", "items.memory_card.fixed", (items or [{}])[0].get("fixed", False))
    SCENE_ITEM_OVERRIDES[root] = [
        "memory_card" if item_id == "lantern" else item_id
        for item_id in (["lantern"] if item_ids is None else item_ids)
    ]
    patch_source(root, "source/scenes/1A.yaml", "reveals[find_card].variants.quiet.claim_id", "k_delivery")
    patch_source(root, "source/scenes/1A.yaml", "reveals[find_card].variants.quiet.says", "The delivery happened.")
    patch_source(root, "source/scenes/1A.yaml", "reveals[find_card].variants.quiet.text", entry["delivery_text"])
    patch_source(
        root, "source/scenes/1A.yaml", "reveals[find_card].variants.quiet.entities", entry.get("entity_ids", [])
    )
    patch_source(
        root,
        "source/scenes/1A.yaml",
        "reveals[find_card].variants.quiet.relevance",
        {"entity_ids": [], "priority": 0},
    )
    patch_source(
        root,
        "source/scenes/1A.yaml",
        "reveals[find_card].variants.quiet.commits",
        {
            "michelle_abduction_suspicion": True,
            **{effect["fact_id"]: True for effect in entry.get("establishes", [])},
        },
    )
    patch_source(
        root,
        "source/scenes/1A.yaml",
        "reveals[find_card].variants.quiet.text_when",
        entry.get("delivery_variants", []),
    )
    patch_source(root, "source/scenes/1A.match.yaml", "claims.k_sl_1a_b_r0", DELETE)
    patch_source(
        root,
        "source/scenes/1A.match.yaml",
        "claims.k_delivery",
        {
            "aliases": ["delivery"],
            "action_evidence": [["hand", "hands"], ["lantern"]],
            "must_convey": [["the"]],
        },
    )
    if fact_effects:
        for fact_id, effects in fact_effects.items():
            patch_source(
                root,
                "source/scenes/1A.yaml",
                f"facts.{fact_id}",
                {
                    "purpose": f"The fact {fact_id} is true.",
                    "on_assert": [{**effect, "parent": "kristin"} for effect in effects],
                },
            )
    load_compiled_copy(root)
    return root


def _entry(text: str = "Ada hands over the brass lantern") -> dict:
    return {
        "id": "k_delivery",
        "statement": "The delivery happened.",
        "delivery_text": text,
        "entity_ids": [],
        "available_in_scenes": ["1A"],
        "establishes": [],
    }


def _report(root: Path) -> dict:
    package = load_story_package(root)
    knowledge = package.knowledge.model_dump()
    world = package.world.model_dump()
    world["fact_effects"] = {fact_id: list(effects) for fact_id, effects in world["fact_effects"].items()}
    world["protagonist"] = next(npc for npc in world["npcs"] if npc["id"] == package.protagonist_id)
    scenes = {
        scene.metadata.scene_id: (
            f"---\nitem_ids: [{', '.join(SCENE_ITEM_OVERRIDES.get(root, scene.metadata.item_ids))}]\n---"
        )
        for scene in package.scenes
    }
    findings = delivery_names_unbound_item(knowledge, world, scenes)
    return {"findings": findings, "scenes": {scene_id: [] for scene_id in scenes}}


def _unbound(root: Path) -> list[dict]:
    return _report(root)["findings"]


def test_delivery_naming_character_and_movable_item_is_reported(tmp_path: Path) -> None:
    findings = _unbound(_package(tmp_path, knowledge=[_entry()]))
    assert len(findings) == 1
    assert "k_delivery" in findings[0]["detail"]
    assert "brass lantern" in findings[0]["detail"]
    assert "Ada" in findings[0]["detail"]


def test_item_in_entity_ids_is_bound(tmp_path: Path) -> None:
    entry = _entry()
    entry["entity_ids"] = ["memory_card"]
    assert _unbound(_package(tmp_path, knowledge=[entry])) == []


def test_asserted_fact_effect_move_binds_item(tmp_path: Path) -> None:
    entry = _entry()
    entry["establishes"] = [{"op": "assert", "fact_id": "lantern_moved"}]
    root = _package(tmp_path, knowledge=[entry], fact_effects={"lantern_moved": [{"move": "memory_card"}]})
    assert _unbound(root) == []


def test_fixed_item_is_ignored(tmp_path: Path) -> None:
    item = {"id": "memory_card", "name": "brass lantern", "fixed": True}
    assert _unbound(_package(tmp_path, knowledge=[_entry()], items=[item])) == []


def test_item_without_character_is_not_a_transfer_candidate(tmp_path: Path) -> None:
    assert _unbound(_package(tmp_path, knowledge=[_entry("The brass lantern is on the table")])) == []


def test_item_in_another_scene_is_not_a_candidate(tmp_path: Path) -> None:
    root = _package(tmp_path, item_ids=[], knowledge=[_entry()], extra_scene=True)
    assert _unbound(root) == []


def test_delivery_variant_text_is_checked(tmp_path: Path) -> None:
    entry = _entry("The delivery is ready")
    entry["delivery_variants"] = [{"when": ["patrol_in_house"], "text": "Ada hands over the brass lantern"}]
    findings = _unbound(_package(tmp_path, knowledge=[entry]))
    assert len(findings) == 1


def test_markdown_report_includes_the_check(tmp_path: Path) -> None:
    root = _package(tmp_path, knowledge=[_entry()])
    markdown = _markdown(_report(root))
    assert "**delivery_names_unbound_item**" in markdown


def test_real_package_finding_set_is_explicitly_pinned() -> None:
    root = Path("data/stories/continuity-initiative")
    package = load_story_package(root)
    report = _report(root)
    item_ids_by_name = {item.name: item.id for item in package.world.items}
    actual = set()
    for finding in report["findings"]:
        detail = finding["detail"]
        start = detail.index("Delivery of '") + len("Delivery of '")
        delivery_id, remainder = detail[start:].split("' names the ", 1)
        item_name = remainder.split(" with ", 1)[0]
        actual.add((delivery_id, item_ids_by_name[item_name]))
    assert actual == KNOWN_UNBOUND, f"new={sorted(actual - KNOWN_UNBOUND)} missing={sorted(KNOWN_UNBOUND - actual)}"
