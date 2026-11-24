"""Focused tests for the story new command."""

from __future__ import annotations

import shutil
from pathlib import Path

from factory.stations.wiring import beat_position_error
from storygame.story_cli import main
from storygame.story_source import check_source_tree
from storygame.story_source.compiler import compile_source_tree
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


def test_new_beat_at_turn_inserts_in_the_middle(tmp_path: Path, monkeypatch) -> None:
    root = copy_source(tmp_path)
    monkeypatch.chdir(root)

    assert main(["new", "beat", "1A", "inserted_middle", "--say", "A middle pacing line.", "--at-turn", "9"]) == 0

    beats = load_document(root / "scenes" / "1A.yaml")["beats"]
    ids = [beat["id"] for beat in beats]
    assert ids.index("inserted_middle") + 1 == ids.index("patrol_leaves_1a")
    assert beats[ids.index("inserted_middle")]["at_turn"] == 9
    assert ids[ids.index("inserted_middle") - 1] == "reyes_rams_drawer_1a"
    assert_fmt_clean(root, monkeypatch)


def test_new_beat_at_turn_inserts_at_the_end(tmp_path: Path, monkeypatch) -> None:
    root = copy_source(tmp_path)
    monkeypatch.chdir(root)

    assert main(["new", "beat", "1A", "inserted_end", "--say", "A final pacing line.", "--at-turn", "13"]) == 0

    beats = load_document(root / "scenes" / "1A.yaml")["beats"]
    assert beats[-1]["id"] == "inserted_end"
    assert beats[-1]["at_turn"] == 13
    assert_fmt_clean(root, monkeypatch)


def test_new_beat_at_turn_goes_after_equal_turns(tmp_path: Path, monkeypatch) -> None:
    root = copy_source(tmp_path)
    monkeypatch.chdir(root)

    assert main(["new", "beat", "1A", "inserted_tie", "--say", "A tied pacing line.", "--at-turn", "7"]) == 0

    beats = load_document(root / "scenes" / "1A.yaml")["beats"]
    ids = [beat["id"] for beat in beats]
    assert ids[ids.index("inserted_tie") - 1] == "officer_presses_1a"
    assert ids[ids.index("inserted_tie") + 1] == "reyes_rams_drawer_1a"
    assert_fmt_clean(root, monkeypatch)


def test_new_beat_at_turn_passes_compiled_position_for_every_story_scene(tmp_path: Path, monkeypatch) -> None:
    story = load_document(SOURCE / "story.yaml")
    scene_ids = story["scenes"]
    for scene_id in scene_ids:
        root = tmp_path / str(scene_id)
        shutil.copytree(SOURCE, root)
        original = load_document(root / "scenes" / f"{scene_id}.yaml")
        turns = sorted({beat["at_turn"] for beat in original["beats"]})
        monkeypatch.chdir(root)
        beat_ids = []
        for index, at_turn in enumerate(turns):
            beat_id = f"position_probe_{str(scene_id).lower()}_{index}"
            assert (
                main(
                    [
                        "new",
                        "beat",
                        str(scene_id),
                        beat_id,
                        "--say",
                        "A position probe.",
                        "--at-turn",
                        str(at_turn),
                    ]
                )
                == 0
            )
            beat_ids.append(beat_id)
        package = compile_source_tree(root)
        for beat_id in beat_ids:
            assert beat_position_error(package.pacing.events, beat_id, str(scene_id)) is None


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
