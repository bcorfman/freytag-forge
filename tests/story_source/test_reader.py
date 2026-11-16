from __future__ import annotations

from pathlib import Path

from tests.story_source.helpers import copy_fixture, require_story_source


def test_mini_ok_reads_exactly_the_fixture_files(tmp_path: Path) -> None:
    story_source = require_story_source()
    root = copy_fixture("mini_ok", tmp_path)

    tree, diagnostics = story_source.read_source_tree(root)

    assert diagnostics == []
    assert list(tree.files) == [
        "catalog.yaml",
        "scenes/1A.match.yaml",
        "scenes/1A.yaml",
        "scenes/2C.match.yaml",
        "scenes/2C.yaml",
        "story.yaml",
    ]


def test_duplicate_key_is_reported_with_lines(tmp_path: Path) -> None:
    story_source = require_story_source()
    root = copy_fixture("mini_ok", tmp_path)
    scene = root / "scenes/1A.yaml"
    original = scene.read_text(encoding="utf-8")
    needle = (
        "        intent: Kristin searches beneath the KMS drawer, finds Michelle's hidden "
        "memory card, and keeps it with her."
    )
    scene.write_text(original.replace(needle, needle + "\n        intent: duplicate intent"), encoding="utf-8")
    duplicate_line = scene.read_text(encoding="utf-8").splitlines().index("        intent: duplicate intent") + 1

    _, diagnostics = story_source.read_source_tree(root)

    assert len(diagnostics) == 1
    diagnostic = diagnostics[0]
    assert diagnostic.name == "L1.duplicate_key"
    assert diagnostic.file and diagnostic.address and diagnostic.field
    assert "intent" in diagnostic.message
    assert "line" in diagnostic.message
    assert str(duplicate_line) in diagnostic.message


def test_yaml_syntax_error_is_a_diagnostic(tmp_path: Path) -> None:
    story_source = require_story_source()
    root = tmp_path / "source"
    root.mkdir()
    (root / "broken.yaml").write_text("schema: [\n", encoding="utf-8")

    tree, diagnostics = story_source.read_source_tree(root)

    assert tree.files == {"broken.yaml": None}
    assert [diagnostic.name for diagnostic in diagnostics] == ["L1.syntax"]


def test_line_of_returns_the_line_of_a_known_key(tmp_path: Path) -> None:
    story_source = require_story_source()
    root = copy_fixture("mini_ok", tmp_path)
    tree, diagnostics = story_source.read_source_tree(root)

    assert diagnostics == []
    assert tree.line_of("scenes/1A.yaml", ("scene",)) == 2


def test_reading_is_deterministic(tmp_path: Path) -> None:
    story_source = require_story_source()
    root = copy_fixture("mini_ok", tmp_path)

    first_tree, first_diagnostics = story_source.read_source_tree(root)
    second_tree, second_diagnostics = story_source.read_source_tree(root)

    assert first_tree.files == second_tree.files
    assert first_diagnostics == second_diagnostics
    assert first_tree.line_of("scenes/1A.yaml", ("scene",)) == second_tree.line_of("scenes/1A.yaml", ("scene",))
