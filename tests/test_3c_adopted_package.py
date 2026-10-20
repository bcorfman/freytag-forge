from __future__ import annotations

import hashlib
from pathlib import Path

import yaml

from bench.core import load_variation, package_and_state
from storygame.story_package.loader import load_story_package

ROOT = Path(__file__).parents[1]
SHIPPED_ROOT = ROOT / "data/stories/continuity-initiative"
FROZEN_ROOT = ROOT / "tests/fixtures/continuity_initiative_pre_3c_adoption"
VARIATION = ROOT / "bench/variations/stage7-3c-pump-need.json"

SHIPPED_ENTRY_TEXT = (
    "entry_text: \"The broadcast chamber lights are steady. Brandon's relay is open. "
    "Michelle's evidence package is ready to send. Water is entering the outer access level.\\n\\n\""
)
SHIPPED_B_R1_DELIVERY = (
    'delivery_text: "Kristin takes the Portable data case from Rebecca. Michelle sends its prisoner locations '
    'to independent networks. The drainage pumps need power. Water rises around the drainage pump controls."'
)
SHIPPED_PLOT_SHA256 = "47dd7e2ae9b3ff41ca06b1ea005e4e8b9b64156865d16c4195788402a01d69ed"
SHIPPED_KNOWLEDGE_SHA256 = "9417f345c1d0bb4ebef22262118f682f2d404cb88b1b25609063af26d67e4486"


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _package_files(root: Path) -> set[str]:
    return {
        path.relative_to(root).as_posix() for path in root.rglob("*") if path.is_file() and path.name != "README.txt"
    }


def _line_differences(left: Path, right: Path) -> list[tuple[int, str, str]]:
    left_lines = left.read_text(encoding="utf-8").splitlines(keepends=True)
    right_lines = right.read_text(encoding="utf-8").splitlines(keepends=True)
    return [
        (line_number, old, new)
        for line_number, (old, new) in enumerate(zip(left_lines, right_lines, strict=True), 1)
        if old != new
    ]


def test_frozen_pump_application_reproduces_the_shipped_package() -> None:
    variation = load_variation(VARIATION)
    package_and_state(variation, "3C")
    materialized = Path(variation["_package_path"])

    old_entry = (
        "entry_text: \"The broadcast chamber lights steadied as Brandon's relay held open. Outside, Charles's "
        "emergency deluge was filling the outer access level and forcing water toward the maintenance routes; "
        'inside, the evidence was ready to leave for good.\\n\\n"'
    )
    old_delivery = (
        'delivery_text: "Kristin stops Rebecca from fleeing with the data case. Michelle sends its prisoner '
        'locations to independent networks. Water rises around the drainage pump controls."'
    )
    assert (FROZEN_ROOT / "plot.md").read_text(encoding="utf-8").count(old_entry) == 1
    assert (FROZEN_ROOT / "knowledge.yaml").read_text(encoding="utf-8").count(old_delivery) == 1

    for filename in ("plot.md", "knowledge.yaml"):
        assert _sha256(materialized / filename) == _sha256(SHIPPED_ROOT / filename)
    assert _sha256(materialized / "plot.md") == SHIPPED_PLOT_SHA256
    assert _sha256(materialized / "knowledge.yaml") == SHIPPED_KNOWLEDGE_SHA256

    assert _package_files(FROZEN_ROOT) == _package_files(SHIPPED_ROOT)
    for filename in _package_files(FROZEN_ROOT) - {"plot.md", "knowledge.yaml"}:
        assert (FROZEN_ROOT / filename).read_bytes() == (SHIPPED_ROOT / filename).read_bytes()
    assert _line_differences(FROZEN_ROOT / "plot.md", SHIPPED_ROOT / "plot.md") == [
        (831, old_entry + "\n", SHIPPED_ENTRY_TEXT + "\n")
    ]
    assert _line_differences(FROZEN_ROOT / "knowledge.yaml", SHIPPED_ROOT / "knowledge.yaml") == [
        (2513, "  " + old_delivery + "\n", "  " + SHIPPED_B_R1_DELIVERY + "\n")
    ]


def test_shipped_package_loads_and_b_r1_establishes_neither_c_fact() -> None:
    package = load_story_package(SHIPPED_ROOT)
    scene_3c = next(scene for scene in package.scenes if scene.metadata.scene_id == "3C")
    assert scene_3c.metadata.entry_text == yaml.safe_load(SHIPPED_ENTRY_TEXT.removeprefix("entry_text: "))

    b_r1 = package.knowledge_indexes.by_id["k_sl_3c_b_r1"]
    assert b_r1.delivery_text == yaml.safe_load(SHIPPED_B_R1_DELIVERY.removeprefix("delivery_text: "))
    c_fact_ids = {
        effect.fact_id
        for c_id in ("k_sl_3c_c_r1", "k_sl_3c_c_r2")
        for effect in package.knowledge_indexes.by_id[c_id].establishes
    }
    assert c_fact_ids.isdisjoint({effect.fact_id for effect in b_r1.establishes})
