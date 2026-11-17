"""Parity gate: the converted default story must compile to the legacy package."""

from pathlib import Path

import yaml

from storygame.story_package.loader import load_story_package
from storygame.story_source import compile_source_tree
from storygame.story_source.convert import write_source_tree
from storygame.story_source.parity import check_parity

PACKAGE_ROOT = Path("data/stories/continuity-initiative")
REVIEW_DIR = Path("tests/fixtures/parity/continuity-initiative")
# The contract (section 9, known review entries) allows these reviewed paths and nothing else.
ALLOWED_REVIEWED_PATHS = {"world.facts"}


def _review_entries() -> list[dict]:
    entries: list[dict] = []
    for path in sorted(REVIEW_DIR.glob("*.reviewed.yaml")):
        entries.extend(yaml.safe_load(path.read_text(encoding="utf-8"))["differences"])
    return entries


def test_converted_default_story_has_no_unreviewed_parity_differences(tmp_path: Path) -> None:
    """Every field of the compiled package equals the legacy package, apart from contract-listed reviews."""

    legacy = load_story_package(PACKAGE_ROOT)
    write_source_tree(legacy, tmp_path)
    reviews = _review_entries()
    assert {entry["path"] for entry in reviews} <= ALLOWED_REVIEWED_PATHS
    assert all(entry.get("reason") for entry in reviews)
    report = check_parity(legacy, compile_source_tree(tmp_path), reviews=reviews)
    open_differences = [d for d in report["differences"] if not d["reviewed"]]
    lines = [f"{d['scene']} {d['path']} [{d['class']}]" for d in open_differences[:25]]
    assert report["summary"]["pass"], f"{report['summary']}\n" + "\n".join(lines)
