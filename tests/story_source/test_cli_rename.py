from __future__ import annotations

import shutil
from pathlib import Path

from storygame.story_cli import main

SOURCE = Path(__file__).resolve().parents[2] / "data" / "stories" / "continuity-initiative" / "source"


def _copy(tmp_path: Path) -> Path:
    root = tmp_path / "source"
    shutil.copytree(SOURCE, root)
    return root


def test_rename_free_fact_rewrites_references_and_keeps_format(tmp_path: Path, monkeypatch, capsys) -> None:
    root = _copy(tmp_path)
    monkeypatch.chdir(root)

    assert main(["rename", "fact:alarm_log_read", "alarm_log_reviewed"]) == 0
    output = capsys.readouterr().out
    assert "scenes/" in output
    assert "alarm_log_reviewed" in output
    assert "  alarm_log_read:" not in "\n".join(path.read_text() for path in root.rglob("*.yaml"))
    assert main(["fmt", "--check"]) == 0


def test_rename_frozen_claim_requires_retirement_and_then_records_it(tmp_path: Path, monkeypatch, capsys) -> None:
    root = _copy(tmp_path)
    monkeypatch.chdir(root)
    before = {path: path.read_bytes() for path in root.rglob("*.yaml")}

    assert main(["rename", "claim:k_sl_1a_b_r0w", "k_sl_1a_b_retired"]) == 1
    capsys.readouterr()
    assert {path: path.read_bytes() for path in root.rglob("*.yaml")} == before

    assert main(["rename", "claim:k_sl_1a_b_r0w", "k_sl_1a_b_retired", "--retire", "obsolete claim"]) == 0
    assert "k_sl_1a_b_retired" in root.joinpath("scenes/1A.yaml").read_text()
    assert "k_sl_1a_b_r0w: obsolete claim" in root.joinpath("story.yaml").read_text()
    assert main(["fmt", "--check"]) == 0
    assert "tests/story_source/test_f25_save_identity.py" in capsys.readouterr().out


def test_rename_refuses_cross_kind_collision_and_existing_new_id(tmp_path: Path, monkeypatch, capsys) -> None:
    root = _copy(tmp_path)
    monkeypatch.chdir(root)
    before = {path: path.read_bytes() for path in root.rglob("*.yaml")}

    assert main(["rename", "fact:audit_window_missed", "audit_window_renamed"]) == 1
    assert "also defined as" in capsys.readouterr().err
    assert {path: path.read_bytes() for path in root.rglob("*.yaml")} == before

    assert main(["rename", "fact:alarm_log_read", "memory_card_recovered"]) == 1
    assert "already exists" in capsys.readouterr().err
    assert {path: path.read_bytes() for path in root.rglob("*.yaml")} == before


def test_rename_refuses_fact_outcome_collision(tmp_path: Path, monkeypatch, capsys) -> None:
    root = _copy(tmp_path)
    monkeypatch.chdir(root)
    before = {path: path.read_bytes() for path in root.rglob("*.yaml")}

    assert main(["rename", "fact:brandon_name_erased", "brandon_name_renamed"]) == 1
    assert "outcome" in capsys.readouterr().err
    assert {path: path.read_bytes() for path in root.rglob("*.yaml")} == before
