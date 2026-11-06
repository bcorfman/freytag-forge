from __future__ import annotations

import re
from pathlib import Path

import yaml

from storygame.audit import _markdown, audit_package

# The stolen-radio pairs are a real authored-versus-world mismatch awaiting an
# author decision; the rest are to be reviewed.
KNOWN_UNBOUND = frozenset(
    {
        ("k_sl_1a_a_r1", "michelle_phone"),
        ("k_sl_1a_a_r1", "workstation_chair"),
        ("k_sl_1a_c_r1", "lake_photograph"),
        ("k_sl_1a_g_r1", "michelle_reading_glasses"),
        ("k_sl_1a_g_r1", "michelle_tea_mug"),
        ("k_sl_1a_g_r1", "manuscript_pages"),
        ("k_sl_1c_c_secure_route", "transit_card"),
        ("k_sl_3a_c_r1", "stolen_radio"),
        ("k_sl_3a_c_r2", "stolen_radio"),
        ("k_sl_3c_a_r1", "portable_archive"),
        ("k_sl_3c_a_r2", "portable_archive"),
    }
)


def _package(
    tmp_path: Path,
    *,
    item_ids: list[str] | None = None,
    knowledge: list[dict] | None = None,
    items: list[dict] | None = None,
    fact_effects: dict | None = None,
    extra_scene: bool = False,
) -> Path:
    root = tmp_path / "package"
    root.mkdir()
    listed = ", ".join(["lantern"] if item_ids is None else item_ids)
    plot = (
        "## Scene 1A — House\n---\n"
        f"scene_id: 1A\nitem_ids: [{listed}]\n"
        "---\n### Scene 1A.1 — Delivery\n**Details:** a quiet room\n"
    )
    if extra_scene:
        plot += "## Scene 1B — Park\n---\nscene_id: 1B\nitem_ids: [lantern]\n---\n"
    root.joinpath("plot.md").write_text(plot, encoding="utf-8")
    world = {
        "protagonist_id": "ada",
        "npcs": [{"id": "ada", "name": "Ada", "aliases": []}],
        "locations": [],
        "items": items or [{"id": "lantern", "name": "brass lantern", "aliases": []}],
    }
    if fact_effects is not None:
        world["fact_effects"] = fact_effects
    files = {
        "knowledge.yaml": {"knowledge": knowledge or [], "scene_frames": []},
        "world.yaml": world,
        "pacing.yaml": {"scenes": []},
        "storylet-routes.yaml": {"storylets": []},
        "storylets.md": "",
    }
    for name, value in files.items():
        root.joinpath(name).write_text(yaml.safe_dump(value), encoding="utf-8")
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


def _unbound(root: Path) -> list[dict]:
    return [item for item in audit_package(root)["findings"] if item["check"] == "delivery_names_unbound_item"]


def test_delivery_naming_character_and_movable_item_is_reported(tmp_path: Path) -> None:
    findings = _unbound(_package(tmp_path, knowledge=[_entry()]))
    assert len(findings) == 1
    assert "k_delivery" in findings[0]["detail"]
    assert "brass lantern" in findings[0]["detail"]
    assert "Ada" in findings[0]["detail"]


def test_item_in_entity_ids_is_bound(tmp_path: Path) -> None:
    entry = _entry()
    entry["entity_ids"] = ["lantern"]
    assert _unbound(_package(tmp_path, knowledge=[entry])) == []


def test_asserted_fact_effect_move_binds_item(tmp_path: Path) -> None:
    entry = _entry()
    entry["establishes"] = [{"op": "assert", "fact_id": "lantern_moved"}]
    root = _package(tmp_path, knowledge=[entry], fact_effects={"lantern_moved": [{"move": "lantern"}]})
    assert _unbound(root) == []


def test_fixed_item_is_ignored(tmp_path: Path) -> None:
    item = {"id": "lantern", "name": "brass lantern", "fixed": True}
    assert _unbound(_package(tmp_path, knowledge=[_entry()], items=[item])) == []


def test_item_without_character_is_not_a_transfer_candidate(tmp_path: Path) -> None:
    assert _unbound(_package(tmp_path, knowledge=[_entry("The brass lantern is on the table")])) == []


def test_item_in_another_scene_is_not_a_candidate(tmp_path: Path) -> None:
    root = _package(tmp_path, item_ids=[], knowledge=[_entry()], extra_scene=True)
    assert _unbound(root) == []


def test_delivery_variant_text_is_checked(tmp_path: Path) -> None:
    entry = _entry("The delivery is ready")
    entry["delivery_variants"] = [{"requires": ["alternate"], "text": "Ada hands over the brass lantern"}]
    findings = _unbound(_package(tmp_path, knowledge=[entry]))
    assert len(findings) == 1


def test_markdown_report_includes_the_check(tmp_path: Path) -> None:
    root = _package(tmp_path, knowledge=[_entry()])
    markdown = _markdown(audit_package(root))
    assert "**delivery_names_unbound_item**" in markdown


def test_real_package_finding_set_is_explicitly_pinned() -> None:
    root = Path("data/stories/continuity-initiative")
    report = audit_package(root)
    world = yaml.safe_load(root.joinpath("world.yaml").read_text(encoding="utf-8"))
    item_ids_by_name = {item["name"]: item["id"] for item in world["items"]}
    pattern = re.compile(r"Delivery of '([^']+)' names the (.+?) with (.+?) but ")
    actual = set()
    for finding in report["findings"]:
        if finding["check"] != "delivery_names_unbound_item":
            continue
        match = pattern.search(finding["detail"])
        assert match, finding
        actual.add((match.group(1), item_ids_by_name[match.group(2)]))
    assert actual == KNOWN_UNBOUND, f"new={sorted(actual - KNOWN_UNBOUND)} missing={sorted(KNOWN_UNBOUND - actual)}"
