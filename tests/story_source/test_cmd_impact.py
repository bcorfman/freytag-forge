from __future__ import annotations

import hashlib
import json
import shutil
from pathlib import Path

from storygame.story_cli import main
from storygame.story_package.impact_report import render_impact_report
from tests.story_source.helpers import compiled_story_copy

SOURCE = Path(__file__).resolve().parents[2] / "data" / "stories" / "continuity-initiative" / "source"
FACT = "kristin_marked_by_patrol"
CLAIM = "k_sl_1a_b_r0w"


def _source_copy(tmp_path: Path) -> Path:
    root = tmp_path / "source"
    shutil.copytree(SOURCE, root)
    return root


def _hashes(root: Path) -> dict[Path, str]:
    return {
        path.relative_to(root): hashlib.sha256(path.read_bytes()).hexdigest()
        for path in root.rglob("*")
        if path.is_file()
    }


def test_fact_impact_matches_existing_report(tmp_path: Path, monkeypatch, capsys) -> None:
    root = _source_copy(tmp_path)
    expected_root = compiled_story_copy(tmp_path / "expected")
    monkeypatch.chdir(root)

    assert main(["impact", f"fact:{FACT}"]) == 0

    assert capsys.readouterr().out == render_impact_report(expected_root, FACT)


def test_claim_impact_matches_existing_report(tmp_path: Path, monkeypatch, capsys) -> None:
    root = _source_copy(tmp_path)
    expected_root = compiled_story_copy(tmp_path / "expected")
    monkeypatch.chdir(root)

    assert main(["impact", f"claim:{CLAIM}.text"]) == 0

    assert capsys.readouterr().out == render_impact_report(expected_root, CLAIM)


def test_unknown_impact_address_returns_two(tmp_path: Path, monkeypatch, capsys) -> None:
    root = _source_copy(tmp_path)
    monkeypatch.chdir(root)

    assert main(["impact", "fact:not_a_fact"]) == 2

    assert capsys.readouterr().err == "unknown address: fact:not_a_fact\n"


def test_json_impact_shape_and_read_only_behavior(tmp_path: Path, monkeypatch, capsys) -> None:
    root = _source_copy(tmp_path)
    before = _hashes(root)
    monkeypatch.chdir(root)

    assert main(["impact", "claim:" + CLAIM + ".says", "--json"]) == 0

    output = json.loads(capsys.readouterr().out)
    assert output["address"] == "claim:" + CLAIM + ".says"
    assert output["subject"] == CLAIM
    assert output["report"].startswith("# Impact report: " + CLAIM)
    assert _hashes(root) == before
