"""Focused tests for the story new command."""

from __future__ import annotations

import shutil
from pathlib import Path

from storygame.story_cli import main
from storygame.story_source import check_source_tree
from storygame.story_source.yamlio import load_document

SOURCE = Path(__file__).resolve().parents[2] / "data" / "stories" / "continuity-initiative" / "source"


def copy_source(tmp_path: Path) -> Path:
    root = tmp_path / "source"
    shutil.copytree(SOURCE, root)
    return root


def assert_fmt_clean(root: Path, monkeypatch) -> None:
    monkeypatch.chdir(root)
    assert main(["fmt", "--check"]) == 0
    assert check_source_tree(root) == []


def test_new_fact_writes_fact_and_keeps_tree_valid(tmp_path: Path, monkeypatch, capsys) -> None:
    root = copy_source(tmp_path)
    monkeypatch.chdir(root)

    assert main(["new", "fact", "1A", "new_clue_fact", "--purpose", "A newly authored clue."]) == 0

    document = load_document(root / "scenes" / "1A.yaml")
    assert document["facts"]["new_clue_fact"] == {"purpose": "A newly authored clue."}
    assert "scenes/1A.yaml" in capsys.readouterr().out
    assert_fmt_clean(root, monkeypatch)


def test_new_beat_writes_unguarded_default_say(tmp_path: Path, monkeypatch) -> None:
    root = copy_source(tmp_path)
    monkeypatch.chdir(root)

    assert main(["new", "beat", "1A", "new_pacing_event", "--say", "A new pacing line."]) == 0

    beats = load_document(root / "scenes" / "1A.yaml")["beats"]
    assert beats[-1] == {
        "id": "new_pacing_event",
        "at_turn": 0,
        "sets": {"michelle_abduction_suspicion": False},
        "say": "A new pacing line.",
    }
    assert_fmt_clean(root, monkeypatch)


def test_new_claim_adds_claim_and_match_entry_for_realization_only_variant(tmp_path: Path, monkeypatch) -> None:
    root = copy_source(tmp_path)
    scene_path = root / "scenes" / "3C.yaml"
    document = load_document(scene_path)
    reveal = next(item for item in document["reveals"] if "claim_id" not in item["variants"]["r1"])
    reveal_id = reveal["id"]
    variant_key = next(key for key, value in reveal["variants"].items() if "claim_id" not in value)
    monkeypatch.chdir(root)

    assert (
        main(["new", "claim", "3C", reveal_id, variant_key, "new_resolution_claim", "--says", "A new public fact."])
        == 0
    )

    updated = load_document(scene_path)
    variant = next(item for item in updated["reveals"] if item["id"] == reveal_id)["variants"][variant_key]
    assert variant["claim_id"] == "new_resolution_claim"
    assert variant["realization_id"]
    assert variant["says"] == "A new public fact."
    match = load_document(root / "scenes" / "3C.match.yaml")
    assert match["claims"]["new_resolution_claim"]["aliases"] == ["A new public fact."]
    assert_fmt_clean(root, monkeypatch)


def test_new_duplicate_id_refuses_without_changing_files(tmp_path: Path, monkeypatch, capsys) -> None:
    root = copy_source(tmp_path)
    path = root / "scenes" / "1A.yaml"
    before = path.read_bytes()
    monkeypatch.chdir(root)

    assert main(["new", "fact", "1A", "memory_card_recovered", "--purpose", "No change."]) == 1
    assert path.read_bytes() == before
    assert "id already used" in capsys.readouterr().err


def test_new_unknown_scene_returns_two(tmp_path: Path, monkeypatch) -> None:
    root = copy_source(tmp_path)
    monkeypatch.chdir(root)

    assert main(["new", "fact", "9Z", "new_fact", "--purpose", "No scene."]) == 2


def test_new_missing_required_flag_returns_two(tmp_path: Path, monkeypatch) -> None:
    root = copy_source(tmp_path)
    monkeypatch.chdir(root)

    assert main(["new", "fact", "1A", "new_fact"]) == 2
