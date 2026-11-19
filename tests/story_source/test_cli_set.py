"""Tests for the authored-source ``story set`` command."""

from __future__ import annotations

import shutil
from pathlib import Path

from storygame.story_cli import main

SOURCE = Path(__file__).resolve().parents[2] / "data/stories/continuity-initiative/source"


def _copy_source(tmp_path: Path) -> Path:
    root = tmp_path / "source"
    shutil.copytree(SOURCE, root)
    return root


def test_set_scene_situation_preserves_neighbour_comment(tmp_path: Path, monkeypatch, capsys) -> None:
    root = _copy_source(tmp_path)
    scene = root / "scenes/1A.yaml"
    text = scene.read_text(encoding="utf-8")
    scene.write_text(text.replace("\npressure:", "\n# keep this comment\npressure:", 1), encoding="utf-8")
    monkeypatch.chdir(root)

    assert main(["set", "scene:1A.situation", "A changed situation"]) == 0
    assert "# keep this comment" in scene.read_text(encoding="utf-8")
    assert "situation: A changed situation" in scene.read_text(encoding="utf-8")
    assert "--- scenes/1A.yaml" in capsys.readouterr().out
    assert main(["fmt", "--check"]) == 0


def test_set_claim_matcher_add_drop_restores_bytes(tmp_path: Path, monkeypatch) -> None:
    root = _copy_source(tmp_path)
    match = root / "scenes/1A.match.yaml"
    original = match.read_bytes()
    monkeypatch.chdir(root)

    assert main(["set", "claim:k_sl_1a_b_r0.action_evidence[0]", "--add", "probe"]) == 0
    assert main(["set", "claim:k_sl_1a_b_r0.action_evidence[0]", "--drop", "probe"]) == 0
    assert match.read_bytes() == original
    assert main(["fmt", "--check"]) == 0


def test_set_claim_text_and_refuse_frozen_id(tmp_path: Path, monkeypatch, capsys) -> None:
    root = _copy_source(tmp_path)
    monkeypatch.chdir(root)

    value = (
        "Kristin finds Michelle's memory card taped beneath the drawer. "
        "The memory card is taped beneath the KMS drawer, Michelle."
    )
    assert main(["set", "claim:k_sl_1a_b_r0.text", repr(value)]) == 0
    assert main(["set", "claim:k_sl_1a_b_r0.claim_id", "other"]) == 1
    assert "frozen" in capsys.readouterr().err


def test_set_failed_check_restores_bytes(tmp_path: Path, monkeypatch, capsys) -> None:
    root = _copy_source(tmp_path)
    scene = root / "scenes/1A.yaml"
    original = scene.read_bytes()
    monkeypatch.chdir(root)

    assert main(["set", "scene:1A.turns.min", "0"]) == 1
    assert scene.read_bytes() == original
    assert capsys.readouterr().err


def test_set_unknown_address_returns_two(tmp_path: Path, monkeypatch, capsys) -> None:
    root = _copy_source(tmp_path)
    monkeypatch.chdir(root)

    assert main(["set", "claim:not_a_claim.text", "value"]) == 2
    assert "unknown address" in capsys.readouterr().err
