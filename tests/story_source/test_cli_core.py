"""Focused coverage for the story CLI's built command surface."""

from __future__ import annotations

from pathlib import Path

from storygame.story_cli import main
from storygame.story_package import loader
from storygame.story_source.compiler import compile_source_tree
from tests.story_source.helpers import copy_fixture


def test_show_prints_authored_claim_text(tmp_path: Path, monkeypatch, capsys) -> None:
    root = copy_fixture("mini_ok", tmp_path)
    monkeypatch.chdir(root)

    assert main(["show", "claim:k_sl_1a_b_r0.text"]) == 0

    assert "Her laptop is still out in her truck." in capsys.readouterr().out


def test_show_unknown_address_returns_two(tmp_path: Path, monkeypatch, capsys) -> None:
    root = copy_fixture("mini_ok", tmp_path)
    monkeypatch.chdir(root)

    assert main(["show", "claim:not_a_claim.text"]) == 2

    assert "unknown address" in capsys.readouterr().err


def test_parity_can_compare_a_compiled_package_to_itself(tmp_path: Path, monkeypatch, capsys) -> None:
    root = copy_fixture("mini_ok", tmp_path)
    package = compile_source_tree(root)
    monkeypatch.setattr(loader, "load_story_package", lambda _root: package)
    monkeypatch.chdir(root)

    assert main(["parity", "1A"]) == 0

    assert '"pass": true' in capsys.readouterr().out


def test_missing_source_root_returns_two(tmp_path: Path, monkeypatch, capsys) -> None:
    monkeypatch.chdir(tmp_path)

    assert main(["parity", "1A"]) == 2

    assert "source root not found" in capsys.readouterr().err
