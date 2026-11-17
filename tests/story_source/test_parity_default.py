"""Parity gate: the converted default story must compile to the legacy package."""

from pathlib import Path

from storygame.story_package.loader import load_story_package
from storygame.story_source import compile_source_tree
from storygame.story_source.convert import write_source_tree
from storygame.story_source.parity import check_parity

PACKAGE_ROOT = Path("data/stories/continuity-initiative")


def test_converted_default_story_has_no_unreviewed_parity_differences(tmp_path: Path) -> None:
    """Every field of the compiled package equals the legacy package, with no review file."""

    legacy = load_story_package(PACKAGE_ROOT)
    write_source_tree(legacy, tmp_path)
    report = check_parity(legacy, compile_source_tree(tmp_path))
    open_differences = [d for d in report["differences"] if not d["reviewed"] and d["class"] not in _AUTO]
    lines = [f"{d['scene']} {d['path']} [{d['class']}]" for d in open_differences[:25]]
    assert report["summary"]["unreviewed"] == 0, f"{len(open_differences)} open differences:\n" + "\n".join(lines)


_AUTO = {"op_order", "condition_order", "collection_order"}
