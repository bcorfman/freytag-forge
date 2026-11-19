from __future__ import annotations

from pathlib import Path

import pytest

from storygame.story_source import check_source_tree
from storygame.story_source.diagnostics import SourceError
from tests.story_source.helpers import DELETE, compiled_story_copy, load_compiled_copy, patch_source


def _diagnostics(root: Path, code: str):
    return [diagnostic for diagnostic in check_source_tree(root / "source") if diagnostic.name == code]


def test_axis_pole_check_rejects_unavailable_value(tmp_path: Path) -> None:
    root = compiled_story_copy(tmp_path)
    patch_source(root, "source/catalog.yaml", "items.workstation_chair.unavailable", "gone")

    diagnostics = _diagnostics(root, "L2.axis_pole")
    assert any("item 'workstation_chair' unavailable is not a pole" in item.message for item in diagnostics)
    with pytest.raises(SourceError, match="item 'workstation_chair' unavailable is not a pole"):
        load_compiled_copy(root)


def test_seat_lines_check_rejects_missing_enter_line(tmp_path: Path) -> None:
    root = compiled_story_copy(tmp_path)
    patch_source(root, "source/catalog.yaml", "items.workstation_chair.enter_text", DELETE)

    diagnostics = _diagnostics(root, "L2.seat_lines")
    assert any("item 'workstation_chair' seat_for requires enter_text" in item.message for item in diagnostics)
    with pytest.raises(SourceError, match="enter_text"):
        load_compiled_copy(root)


def test_blank_description_check_rejects_whitespace(tmp_path: Path) -> None:
    root = compiled_story_copy(tmp_path)
    patch_source(root, "source/catalog.yaml", "places.outside_house.description", "  ")

    diagnostics = _diagnostics(root, "L2.blank_description")
    assert any(
        "location 'outside_house' description must be a non-blank string" in item.message for item in diagnostics
    )
    with pytest.raises(SourceError, match="description must be a non-blank string"):
        load_compiled_copy(root)


def test_scoped_alias_check_rejects_declared_name_collision(tmp_path: Path) -> None:
    root = compiled_story_copy(tmp_path)
    patch_source(root, "source/catalog.yaml", "groups.corridor_guards.scoped_aliases", ["Kristin"])

    diagnostics = _diagnostics(root, "L2.scoped_alias_collision")
    assert any("scoped alias 'Kristin'" in item.message for item in diagnostics)
    assert any("declared entity name or alias" in item.message for item in diagnostics)
    with pytest.raises(SourceError, match="scoped alias 'Kristin'.*declared entity name or alias"):
        load_compiled_copy(root)


def test_world_catalog_checks_are_quiet_for_default_story(tmp_path: Path) -> None:
    root = compiled_story_copy(tmp_path)

    assert _diagnostics(root, "L2.axis_pole") == []
    assert _diagnostics(root, "L2.seat_lines") == []
    assert _diagnostics(root, "L2.blank_description") == []
    assert _diagnostics(root, "L2.scoped_alias_collision") == []
