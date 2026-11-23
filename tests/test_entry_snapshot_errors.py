from __future__ import annotations

import json
import shutil
from pathlib import Path

import pytest

import storygame.runtime.entry_snapshots as snapshots_module
from storygame.runtime.entry_snapshots import (
    EntrySnapshotError,
    build_entry_snapshot,
    carry_in_report,
    check_entry_snapshots,
    load_entry_snapshot,
    main,
    state_from_snapshot,
)
from storygame.story_package.loader import load_story_package

ROOT = Path(__file__).parents[1]
STORY_ROOT = ROOT / "data" / "stories" / "continuity-initiative"
PACKAGE = load_story_package(STORY_ROOT)


def _copy_story(tmp_path: Path) -> Path:
    destination = tmp_path / "continuity-initiative"
    shutil.copytree(STORY_ROOT, destination)
    return destination


def _snapshot(root: Path, scene_id: str = "1A") -> tuple[object, dict[str, object]]:
    package = load_story_package(root)
    path = root / "entry" / f"{scene_id}.json"
    value = json.loads(path.read_text(encoding="utf-8"))
    return package, value


def _write_snapshot(root: Path, scene_id: str, value: object) -> None:
    (root / "entry" / f"{scene_id}.json").write_text(
        json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )


def _patch_expected_entries(monkeypatch: pytest.MonkeyPatch, root: Path) -> None:
    """Keep check-path tests focused on their defect instead of replaying the route each time."""
    package = load_story_package(root)
    entries = []
    for scene in package.scenes:
        snapshot = json.loads((root / "entry" / f"{scene.metadata.scene_id}.json").read_text(encoding="utf-8"))
        path = snapshot["path"]
        entries.append(
            (
                state_from_snapshot(package, snapshot, root),
                {"turns": path["turns"], "storylets": path["storylets_delivered"]},
            )
        )
    monkeypatch.setattr(snapshots_module, "_canonical_entries", lambda _package: entries)


def test_build_rejects_unknown_scene_id() -> None:
    # build_entry_snapshot: _scene's unknown scene-id validation branch.
    with pytest.raises(EntrySnapshotError, match="scene nowhere is not in package continuity_initiative"):
        build_entry_snapshot(PACKAGE, STORY_ROOT, "nowhere")


def test_load_rejects_missing_truncated_invalid_json_and_wrong_top_level(tmp_path: Path) -> None:
    # load_entry_snapshot: OSError/JSONDecodeError and non-object validation branches.
    root = _copy_story(tmp_path)
    path = root / "entry" / "1A.json"
    for contents, message in (
        (None, "cannot load entry snapshot"),
        ("not json", "cannot load entry snapshot"),
        ("[]", "must be a JSON object"),
    ):
        if contents is None:
            path.unlink()
        else:
            path.write_text(contents, encoding="utf-8")
        with pytest.raises(EntrySnapshotError, match=message):
            load_entry_snapshot(root, "1A")
        shutil.copy2(STORY_ROOT / "entry" / "1A.json", path)


def test_state_from_snapshot_rejects_bad_header_and_shapes(tmp_path: Path) -> None:
    # state_from_snapshot: schema, story, scene, fingerprint, list, and mapping validation branches.
    root = _copy_story(tmp_path)
    package, original = _snapshot(root)
    for field, value, message in (
        ("schema", 2, "unknown entry snapshot schema"),
        ("story_id", "other_story", "story_id does not match"),
        ("scene_id", 42, "scene_id is missing"),
        ("source_fingerprint", "tampered", "source_fingerprint does not match"),
        ("story_facts", {}, "story_facts must be a list"),
        ("runtime", [], "snapshot runtime must be an object"),
        ("world", [], "snapshot world must be an object"),
    ):
        snapshot = json.loads(json.dumps(original))
        snapshot[field] = value
        with pytest.raises(EntrySnapshotError, match=message):
            state_from_snapshot(package, snapshot, root)


def test_state_from_snapshot_rejects_non_mapping_snapshot() -> None:
    # state_from_snapshot: direct non-dict snapshot validation branch.
    with pytest.raises(EntrySnapshotError, match="entry snapshot must be an object"):
        state_from_snapshot(PACKAGE, [], STORY_ROOT)  # type: ignore[arg-type]


def test_state_from_snapshot_rejects_runtime_scene_mismatch(tmp_path: Path) -> None:
    # state_from_snapshot: runtime current_scene_id mismatch branch.
    root = _copy_story(tmp_path)
    package, snapshot = _snapshot(root)
    snapshot["scene_id"] = "1B"
    with pytest.raises(EntrySnapshotError, match="scene_id does not match runtime"):
        state_from_snapshot(package, snapshot, root)


def test_state_from_snapshot_rejects_unknown_story_predicate(tmp_path: Path) -> None:
    # state_from_snapshot: invalid story Fact validation branch.
    root = _copy_story(tmp_path)
    package, snapshot = _snapshot(root)
    snapshot["story_facts"].append({"predicate": "wk_unknown", "subject": "story", "object": None, "value": "true"})  # type: ignore[index]
    with pytest.raises(EntrySnapshotError, match="story_facts may not contain worldkeeper facts"):
        state_from_snapshot(package, snapshot, root)


def test_state_from_snapshot_rejects_malformed_story_fact_row(tmp_path: Path) -> None:
    # state_from_snapshot: Fact.model_validate ValueError branch for a malformed row.
    root = _copy_story(tmp_path)
    package, snapshot = _snapshot(root)
    snapshot["story_facts"].append({"predicate": "broken"})  # type: ignore[index]
    with pytest.raises(EntrySnapshotError, match="invalid story fact"):
        state_from_snapshot(package, snapshot, root)


def test_state_from_snapshot_rejects_unknown_world_predicate_or_entity(tmp_path: Path) -> None:
    # state_from_snapshot: world import unknown predicate/entity validation branch.
    root = _copy_story(tmp_path)
    package, original = _snapshot(root)
    for field, value in (("predicate", "wk_unknown"), ("subject", "unknown_entity")):
        snapshot = json.loads(json.dumps(original))
        row = dict(snapshot["world"]["facts"][0])
        row[field] = value
        snapshot["world"]["facts"].append(row)
        with pytest.raises(EntrySnapshotError, match="invalid world state"):
            state_from_snapshot(package, snapshot, root)


def test_check_reports_missing_invalid_fingerprint_and_scene_story_mismatches(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    # check_entry_snapshots: missing file, load failure, stale fingerprint, and metadata mismatch branches.
    root = _copy_story(tmp_path)
    _patch_expected_entries(monkeypatch, root)
    (root / "entry" / "1A.json").unlink()
    (root / "entry" / "1B.json").write_text("{", encoding="utf-8")
    snapshot = json.loads((root / "entry" / "1C.json").read_text(encoding="utf-8"))
    snapshot["source_fingerprint"] = "stale"
    snapshot["story_id"] = "wrong"
    snapshot["scene_id"] = "wrong-scene"
    _write_snapshot(root, "1C", snapshot)
    problems = check_entry_snapshots(root)
    assert any(problem.startswith("missing entry snapshot:") and problem.endswith("1A.json") for problem in problems)
    assert any("cannot load entry snapshot" in problem for problem in problems)
    assert "stale fingerprint for scene 1C" in problems
    assert "snapshot story_id mismatch for scene 1C" in problems
    assert "snapshot scene_id mismatch for scene 1C" in problems


def test_check_reports_every_drift_line_kind(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    # _drift_lines via check_entry_snapshots: world added/removed/changed, story added/removed, runtime/path drift.
    root = _copy_story(tmp_path)
    _patch_expected_entries(monkeypatch, root)
    snapshot = json.loads((root / "entry" / "1A.json").read_text(encoding="utf-8"))
    facts = snapshot["world"]["facts"]
    facts.pop()
    facts[0]["value"] = "changed"
    facts.append({"predicate": "wk_axis", "subject": "new_entity", "object": "new", "value": "new"})
    snapshot["story_facts"].pop()
    snapshot["story_facts"].append({"predicate": "added_fact", "subject": "story", "object": None, "value": "true"})
    snapshot["runtime"]["turn_index"] = 99
    snapshot["path"]["turns"] = 99
    _write_snapshot(root, "1A", snapshot)
    problems = check_entry_snapshots(root)
    assert "DRIFT in scene 1A" in problems
    assert any(line.startswith("world added:") and "new_entity" in line for line in problems)
    assert any(line.startswith("world removed:") for line in problems)
    assert any(line.startswith("world changed:") and "from" in line and "to" in line for line in problems)
    assert any(line.startswith("story fact removed:") for line in problems)
    assert any(line.startswith("story fact added:") and "added_fact" in line for line in problems)
    assert "runtime fields differ" in problems
    assert "path metadata differs" in problems


def test_check_summarizes_unreadable_world_and_cuts_long_drift(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    # _drift_lines: diff exception fallback and the 40-line truncation branch.
    root = _copy_story(tmp_path)
    _patch_expected_entries(monkeypatch, root)
    snapshot = json.loads((root / "entry" / "1A.json").read_text(encoding="utf-8"))
    snapshot["world"] = []
    snapshot["story_facts"] = [
        {"predicate": f"extra_{index}", "subject": "story", "object": None, "value": "true"} for index in range(50)
    ]
    _write_snapshot(root, "1A", snapshot)
    problems = check_entry_snapshots(root)
    assert "world state differs and could not be summarized" in problems
    assert any(line.endswith("more drift lines cut") for line in problems)


def test_carry_in_report_rejects_non_mapping_or_iterable_input() -> None:
    # carry_in_report/_snapshot_map: invalid snapshot collection shape branch.
    with pytest.raises(EntrySnapshotError, match="snapshots must be a scene mapping or iterable"):
        carry_in_report(PACKAGE, 123)


def test_main_check_drift_prints_lines_and_returns_nonzero(
    tmp_path: Path, capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch
) -> None:
    # main: check command's drift printing and non-zero return branch.
    root = _copy_story(tmp_path)
    _patch_expected_entries(monkeypatch, root)
    snapshot = json.loads((root / "entry" / "1A.json").read_text(encoding="utf-8"))
    snapshot["path"]["turns"] = 7
    _write_snapshot(root, "1A", snapshot)
    (root / "entry" / "1B.json").write_text("not json", encoding="utf-8")
    assert main(["check", "--story-root", str(root)]) == 1
    output = capsys.readouterr().out
    assert "DRIFT in scene 1A" in output
    assert "cannot load entry snapshot" in output


def test_main_write_and_missing_story_root(capsys: pytest.CaptureFixture[str], tmp_path: Path) -> None:
    # main: write command and loader failure for a missing story root.
    root = _copy_story(tmp_path)
    assert main(["write", "--story-root", str(root)]) == 0
    assert "1A.json" in capsys.readouterr().out
    with pytest.raises((FileNotFoundError, ValueError), match="story|source|not found|No such file"):
        main(["write", "--story-root", str(tmp_path / "missing")])


def test_main_rejects_unknown_command() -> None:
    # main: argparse unknown-command error path.
    with pytest.raises(SystemExit, match="2"):
        main(["unknown"])
