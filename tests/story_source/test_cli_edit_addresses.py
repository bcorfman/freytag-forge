"""Gap tests for the story source editing commands."""

from __future__ import annotations

import json
import shutil
from pathlib import Path

import pytest

from storygame.story_cli import main
from storygame.story_cmds.cmd_set import _find_record
from storygame.story_source.yamlio import dumps_document, load_document

SOURCE = Path(__file__).resolve().parents[2] / "data/stories/continuity-initiative/source"


def copy_source(tmp_path: Path) -> Path:
    root = tmp_path / "source"
    shutil.copytree(SOURCE, root)
    return root


@pytest.mark.parametrize(
    ("address", "value", "relative_path"),
    [
        ("scene:1A.title", "Edited scene", "scenes/1A.yaml"),
        ("fact:michelle_abduction_suspicion.purpose", "Edited purpose", "scenes/1A.yaml"),
        (
            "delivery:continuity_initiative_known.must_convey[0]",
            "[Michelle's memory card]",
            "scenes/1A.match.yaml",
        ),
        ("claim:k_sl_1a_a_r1.aliases[0]", "edited alias", "scenes/1A.match.yaml"),
        ("entity:memory_card.name", "Edited card", "catalog.yaml"),
        ("beat:kristin_steadies_1a.say[0].text", "Edited beat", "scenes/1A.yaml"),
        ("bridge:bridge_1a_actionable_lead.when[0]", "continuity_initiative_known", "scenes/1A.yaml"),
        ("exit:t_1a_1b.bridge", "Edited exit", "scenes/1A.yaml"),
        ("reveal:sl_1a_a.title", "Edited reveal", "scenes/1A.yaml"),
        ("variant:sl_1a_a/r1.intent", "Edited variant", "scenes/1A.yaml"),
        ("outcome:i_2a_real_leak/inspection_convincing.advantages[0]", "supervisor_convinced", "scenes/2A.yaml"),
        ("ending:final.when.evacuation_complete", "true", "scenes/3C.yaml"),
    ],
)
def test_set_resolves_each_supported_record_address(tmp_path, monkeypatch, address, value, relative_path) -> None:
    root = copy_source(tmp_path)
    monkeypatch.chdir(root)

    assert main(["set", address, value]) == 0
    assert value.strip("[]").encode() in (root / relative_path).read_bytes()


def test_set_resolves_match_delivery_special_case_and_inherited_claim_field(tmp_path, monkeypatch) -> None:
    root = copy_source(tmp_path)
    match_path = root / "scenes/1A.match.yaml"
    match = load_document(match_path)
    match["shared"] = {"common": {"aliases": ["shared alias"]}}
    match["claims"]["k_sl_1a_a_r1"].pop("aliases")
    match["claims"]["k_sl_1a_a_r1"]["use"] = "common"
    match_path.write_text(dumps_document(match), encoding="utf-8")
    monkeypatch.chdir(root)

    assert main(["set", "delivery:continuity_initiative_known.must_convey[0]", "[Michelle's memory card]"]) == 0
    assert main(["set", "claim:k_sl_1a_a_r1.aliases[0]", "edited shared alias"]) == 0
    updated = load_document(match_path)
    assert updated["deliveries"]["continuity_initiative_known"]["must_convey"][0] == ["Michelle's memory card"]
    assert updated["shared"]["common"]["aliases"] == ["edited shared alias"]


@pytest.mark.parametrize(
    ("argv", "message"),
    [
        (["set", "scene:1A.title"], "missing value for address: scene:1A.title"),
        (["set", "scene:1A.title", "x", "--add", "y"], "set accepts a replacement or --add/--drop, not both"),
        (["set", "fact:scene_1a_entry_known.purpose", "x"], "generated entry facts cannot be edited"),
        (["set", "not-an-address", "x"], "unknown address or missing field: not-an-address"),
        (["set", "scene:1A.title", "["], "invalid YAML value for scene:1A.title"),
    ],
)
def test_set_reports_argument_and_lookup_refusals(tmp_path, monkeypatch, capsys, argv, message) -> None:
    root = copy_source(tmp_path)
    monkeypatch.chdir(root)

    assert main(argv) == (
        2
        if "missing value" in message
        or "not-an-address" in message
        or "invalid YAML" in message
        or "not both" in message
        else 1
    )
    assert message in capsys.readouterr().err


@pytest.mark.parametrize(
    ("option", "item", "message"),
    [
        ("--add", "michelle abduction suspicion", "value already present at claim:k_sl_1a_a_r1.aliases"),
        ("--drop", "does-not-exist", "value not present at claim:k_sl_1a_a_r1.aliases"),
        ("--add", "x", "--add and --drop require a list field"),
    ],
)
def test_set_add_drop_edge_cases_are_precise_and_non_mutating(
    tmp_path, monkeypatch, capsys, option, item, message
) -> None:
    root = copy_source(tmp_path)
    path = root / "scenes/1A.match.yaml"
    before = path.read_bytes()
    monkeypatch.chdir(root)
    address = "claim:k_sl_1a_a_r1.aliases" if item != "x" else "scene:1A.situation"

    assert main(["set", address, option, item]) == 1
    assert message in capsys.readouterr().err
    assert path.read_bytes() == before


def test_set_json_reports_changed_file_and_diff(tmp_path, monkeypatch, capsys) -> None:
    root = copy_source(tmp_path)
    monkeypatch.chdir(root)

    assert main(["--json", "set", "scene:1A.title", "JSON title"]) == 0
    result = json.loads(capsys.readouterr().out)
    assert result["changed"] == ["scenes/1A.yaml"]
    assert "JSON title" in result["diff"]


def test_set_failed_source_check_restores_every_changed_byte(tmp_path, monkeypatch, capsys) -> None:
    root = copy_source(tmp_path)
    scene = root / "scenes/1A.yaml"
    original = scene.read_bytes()
    monkeypatch.chdir(root)

    assert main(["set", "scene:1A.turns.min", "0"]) == 1
    assert scene.read_bytes() == original
    assert capsys.readouterr().err


@pytest.mark.parametrize(
    ("kind", "identifier", "relative_path", "record_path"),
    [
        ("claim", "k_scene_1a_entry", "scenes/1A.yaml", [("entry_claims", 0)]),
        (
            "claim",
            "k_sl_2b_d_route_effects",
            "scenes/2B.yaml",
            [("reveals", 3), ("variants", None), ("r1", None), ("extra_claims", 0)],
        ),
        (
            "claim",
            "k_bridge_2b_archive_crisis",
            "scenes/2B.yaml",
            [("bridge", 0), ("claim", None)],
        ),
        ("reveal", "sl_1a_a", "scenes/1A.yaml", [("reveals", 0)]),
        (
            "outcome",
            "i_2a_real_leak/inspection_convincing",
            "scenes/2A.yaml",
            [("reveals", 1), ("variants", None), ("r5", None), ("outcome", None)],
        ),
        ("ending", "final", "scenes/3C.yaml", [("ending", None)]),
    ],
)
def test_find_record_returns_real_storage_for_each_uncovered_record_branch(
    tmp_path: Path, kind, identifier, relative_path, record_path
) -> None:
    root = copy_source(tmp_path)
    path, _, actual_record_path = _find_record(root, kind, identifier, f"{kind}:{identifier}.field")
    assert path.relative_to(root).as_posix() == relative_path
    assert actual_record_path == record_path


def test_find_record_finds_match_only_delivery_after_scene_fact_is_removed(tmp_path: Path) -> None:
    root = copy_source(tmp_path)
    scene = root / "scenes/1B.yaml"
    document = load_document(scene)
    document["facts"].pop("park_pursuit_resolved", None)
    scene.write_text(dumps_document(document), encoding="utf-8")

    path, _, record_path = _find_record(root, "delivery", "park_pursuit_resolved", "delivery:park_pursuit_resolved")
    assert path.relative_to(root).as_posix() == "scenes/1B.match.yaml"
    assert record_path == [("deliveries", None), ("park_pursuit_resolved", None)]


@pytest.mark.parametrize("mutation", ["remove_match", "remove_claim", "remove_field"])
def test_set_claim_matcher_lookup_refusals_are_exact_and_non_mutating(tmp_path, monkeypatch, capsys, mutation) -> None:
    root = copy_source(tmp_path)
    match_path = root / "scenes/1A.match.yaml"
    source_path = root / "scenes/1A.yaml"
    if mutation == "remove_match":
        match_path.unlink()
    else:
        match = load_document(match_path)
        if mutation == "remove_claim":
            match["claims"].pop("k_sl_1a_a_r1")
        else:
            match["claims"]["k_sl_1a_a_r1"].pop("aliases")
        match_path.write_text(dumps_document(match), encoding="utf-8")
    before = {path: path.read_bytes() for path in root.rglob("*.yaml")}
    monkeypatch.chdir(root)

    assert main(["set", "claim:k_sl_1a_a_r1.aliases[0]", "replacement"]) == 2
    assert capsys.readouterr().err == ("unknown address or missing field: claim:k_sl_1a_a_r1.aliases[0]\n")
    assert {path: path.read_bytes() for path in root.rglob("*.yaml")} == before
    assert source_path.exists()


@pytest.mark.parametrize(
    ("argv", "message", "code"),
    [
        (["rename", "bad", "new_id"], "invalid rename address or id", 2),
        (["rename", "fact:not_present", "new_id"], "unknown address: fact:not_present", 2),
        (
            ["rename", "fact:alarm_log_read", "new_id", "--retire", "obsolete"],
            "--retire is only valid for a frozen id",
            1,
        ),
    ],
)
def test_rename_run_reports_invalid_requests(tmp_path, monkeypatch, capsys, argv, message, code) -> None:
    root = copy_source(tmp_path)
    monkeypatch.chdir(root)

    assert main(argv) == code
    assert message in capsys.readouterr().err


def test_rename_json_reports_all_changed_files(tmp_path, monkeypatch, capsys) -> None:
    root = copy_source(tmp_path)
    monkeypatch.chdir(root)

    assert main(["--json", "rename", "fact:alarm_log_read", "alarm_log_reviewed"]) == 0
    result = json.loads(capsys.readouterr().out)
    assert "scenes/" in " ".join(result["changed"])
    assert "alarm_log_reviewed" in result["diff"]
    assert isinstance(result["tests"], list)


def test_rename_prints_problems_and_restores_tree(tmp_path, monkeypatch, capsys) -> None:
    root = copy_source(tmp_path)
    bad = root / "scenes/1A.yaml"
    document = load_document(bad)
    document["facts"]["bad_fact"] = {}
    bad.write_text(dumps_document(document), encoding="utf-8")
    before = {path: path.read_bytes() for path in root.rglob("*.yaml")}
    monkeypatch.chdir(root)

    assert main(["rename", "fact:alarm_log_read", "alarm_log_reviewed"]) == 1
    assert "bad_fact" in capsys.readouterr().err
    assert {path: path.read_bytes() for path in root.rglob("*.yaml")} == before


def test_new_rejected_check_restores_tree(tmp_path, monkeypatch, capsys) -> None:
    root = copy_source(tmp_path)
    scene = root / "scenes/1A.yaml"
    before = scene.read_bytes()
    monkeypatch.chdir(root)

    assert main(["new", "fact", "1A", "invalid_new_fact", "--purpose", ""]) == 1
    assert scene.read_bytes() == before
    assert capsys.readouterr().err
