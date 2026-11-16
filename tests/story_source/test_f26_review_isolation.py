from __future__ import annotations

import json
from copy import deepcopy
from dataclasses import asdict, is_dataclass
from pathlib import Path

import yaml

from tests.story_source.helpers import copy_fixture, load_tree, patch_source, require_story_source

MARKER = "F26_REVIEW_ONLY_NOTE_7F4A91"
_BRIDGE = {
    "id": "review_isolation_bridge",
    "when": ["purge_window_missed", "purge_recovery_ready"],
    "commits": {"purge_window_missed": True},
    "note": MARKER,
}


def _add_bridge_in_contract_order(root: Path) -> None:
    path = root / "scenes/2C.yaml"
    scene = load_tree(root)["scenes/2C.yaml"]
    ordered: dict[str, object] = {}
    for key, value in scene.items():
        ordered[key] = value
        if key == "reveals":
            ordered["bridge"] = [deepcopy(_BRIDGE)]
    with path.open("w", encoding="utf-8") as stream:
        yaml.safe_dump(ordered, stream, sort_keys=False, width=10_000, allow_unicode=True)


def _add_notes(root: Path) -> None:
    patch_source(root, "scenes/2C.yaml", "beats[0].note", MARKER)
    _add_bridge_in_contract_order(root)


def _package_dump(package: object) -> object:
    if hasattr(package, "model_dump"):
        return package.model_dump(mode="json", by_alias=True)
    if is_dataclass(package):
        return asdict(package)
    return package


def test_fixture_adds_only_the_beat_and_bridge_notes(tmp_path: Path) -> None:
    root = copy_fixture("mini_ok", tmp_path)
    baseline = load_tree(root)
    expected = deepcopy(baseline)
    expected_scene = expected["scenes/2C.yaml"]
    expected_scene["beats"][0]["note"] = MARKER
    expected_scene["bridge"] = [deepcopy(_BRIDGE)]

    _add_notes(root)
    mutated = load_tree(root)
    assert mutated == expected
    assert mutated != baseline

    containing_files = [
        path.relative_to(root).as_posix()
        for path in root.rglob("*")
        if path.is_file() and MARKER in path.read_text(encoding="utf-8")
    ]
    assert containing_files == ["scenes/2C.yaml"]
    assert sum(path.read_text(encoding="utf-8").count(MARKER) for path in root.rglob("*") if path.is_file()) == 2


def test_reader_only_notes_stay_out_of_package_and_narrator_material(tmp_path: Path) -> None:
    story_source = require_story_source()
    clean_root = copy_fixture("mini_ok", tmp_path / "clean")
    assert story_source.check_source_tree(clean_root) == []

    root = copy_fixture("mini_ok", tmp_path / "mutated")
    _add_notes(root)
    assert story_source.check_source_tree(root) == []
    package = story_source.compile_source_tree(root)
    dumped = json.dumps(_package_dump(package), ensure_ascii=False, default=str)
    assert MARKER not in dumped
