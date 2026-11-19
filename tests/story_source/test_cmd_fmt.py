"""Tests for the story-source formatter command."""

from __future__ import annotations

import json
import shutil
from pathlib import Path

import yaml

from storygame.story_cli import main

SOURCE_ROOT = Path(__file__).resolve().parents[2] / "data" / "stories" / "continuity-initiative" / "source"


def _copy_source(tmp_path: Path) -> Path:
    root = tmp_path / "source"
    shutil.copytree(SOURCE_ROOT, root)
    return root


def _make_noncanonical(path: Path) -> tuple[str, object]:
    before = path.read_text(encoding="utf-8")
    values = yaml.safe_load(before)
    lines = before.replace("schema: 1\n", "schema: 1\n# inserted comment\n", 1).splitlines(keepends=True)
    in_participants = False
    for index, line in enumerate(lines):
        if line == "participants:\n":
            in_participants = True
        elif in_participants and line.startswith("- "):
            lines[index] = f"  {line}"
        elif in_participants:
            in_participants = False
    path.write_text("".join(lines), encoding="utf-8")
    return before, values


def test_check_on_canonical_copy_is_quiet(tmp_path: Path, monkeypatch, capsys) -> None:
    root = _copy_source(tmp_path)
    monkeypatch.chdir(root)

    assert main(["fmt", "--check"]) == 0
    assert capsys.readouterr().out == ""


def test_check_reports_noncanonical_file_without_writing(tmp_path: Path, monkeypatch, capsys) -> None:
    root = _copy_source(tmp_path)
    path = root / "scenes" / "1A.yaml"
    _make_noncanonical(path)
    noncanonical = path.read_text(encoding="utf-8")
    monkeypatch.chdir(root)

    assert main(["fmt", "--check"]) == 1
    output = capsys.readouterr().out
    assert "scenes/1A.yaml" in output
    assert path.read_text(encoding="utf-8") == noncanonical


def test_fmt_rewrites_only_changed_file_and_preserves_values(tmp_path: Path, monkeypatch, capsys) -> None:
    root = _copy_source(tmp_path)
    path = root / "scenes" / "1A.yaml"
    before, values = _make_noncanonical(path)
    before_files = {
        item.relative_to(root).as_posix(): item.read_text(encoding="utf-8") for item in root.rglob("*.yaml")
    }
    monkeypatch.chdir(root)

    assert main(["fmt"]) == 0
    assert "reformatted scenes/1A.yaml" in capsys.readouterr().out
    assert path.read_text(encoding="utf-8") != before
    assert "# inserted comment" in path.read_text(encoding="utf-8")
    assert yaml.safe_load(path.read_text(encoding="utf-8")) == values
    assert {
        item.relative_to(root).as_posix(): item.read_text(encoding="utf-8")
        for item in root.rglob("*.yaml")
        if item.relative_to(root).as_posix() != "scenes/1A.yaml"
    } == {key: value for key, value in before_files.items() if key != "scenes/1A.yaml"}
    assert main(["fmt", "--check"]) == 0
    assert capsys.readouterr().out == ""


def test_scene_filter_and_unknown_scene(tmp_path: Path, monkeypatch, capsys) -> None:
    root = _copy_source(tmp_path)
    _make_noncanonical(root / "scenes" / "1A.yaml")
    before_files = {
        item.relative_to(root).as_posix(): item.read_text(encoding="utf-8") for item in root.rglob("*.yaml")
    }
    monkeypatch.chdir(root)

    assert main(["fmt", "1A"]) == 0
    assert "scenes/1A.yaml" in capsys.readouterr().out
    assert {
        item.relative_to(root).as_posix(): item.read_text(encoding="utf-8")
        for item in root.rglob("*.yaml")
        if item.relative_to(root).as_posix() != "scenes/1A.yaml"
    } == {key: value for key, value in before_files.items() if key != "scenes/1A.yaml"}
    assert main(["fmt", "NOPE"]) == 2
    assert "unknown scene id: NOPE" in capsys.readouterr().err


def test_json_reports_checked_and_changed_paths(tmp_path: Path, monkeypatch, capsys) -> None:
    root = _copy_source(tmp_path)
    _make_noncanonical(root / "scenes" / "1A.yaml")
    monkeypatch.chdir(root)

    assert main(["fmt", "--check", "--json"]) == 1
    result = json.loads(capsys.readouterr().out)

    assert result["checked"] == len(list(root.rglob("*.yaml")))
    assert result["changed"] == ["scenes/1A.yaml"]
