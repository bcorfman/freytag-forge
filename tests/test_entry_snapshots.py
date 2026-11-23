from __future__ import annotations

import json
import shutil
import subprocess
import sys
from pathlib import Path
from types import SimpleNamespace

import pytest

import storygame.runtime.entry_snapshots as snapshots_module
from storygame.runtime.entry_seed import advance_state_to_scene
from storygame.runtime.entry_snapshots import (
    EntrySnapshotError,
    carry_in_report,
    check_entry_snapshots,
    load_entry_snapshot,
    main,
    state_from_snapshot,
    write_entry_snapshots,
)
from storygame.runtime.state import RuntimeState
from storygame.runtime.world_model import world_for
from storygame.story_package.loader import load_story_package

ROOT = Path(__file__).parents[1]
STORY_ROOT = ROOT / "data" / "stories" / "continuity-initiative"
PACKAGE = load_story_package(STORY_ROOT)
SCENE_IDS = tuple(scene.metadata.scene_id for scene in PACKAGE.scenes)


def _copy_story(tmp_path: Path) -> Path:
    destination = tmp_path / "continuity-initiative"
    shutil.copytree(STORY_ROOT, destination)
    return destination


def _snapshots(root: Path) -> dict[str, dict[str, object]]:
    return {scene_id: load_entry_snapshot(root, scene_id) for scene_id in SCENE_IDS}


def test_committed_snapshots_are_clean_and_list_optional_chains(capsys) -> None:
    assert check_entry_snapshots(STORY_ROOT) == []

    report = carry_in_report(PACKAGE, _snapshots(STORY_ROOT).values())
    optional_chains = [
        row for row in report if row["consumer_kind"] == "gate" and not row["consumer_required"] and not row["supplied"]
    ]
    assert len(optional_chains) == 6
    assert all(row["consumer_required"] is False for row in optional_chains)
    assert all(row["supplied"] is False for row in optional_chains)

    assert main(["check", "--story-root", str(STORY_ROOT)]) == 0
    assert "optional chains not reachable from canonical entry" in capsys.readouterr().out


def test_entry_snapshot_runtime_does_not_import_http_layer() -> None:
    result = subprocess.run(
        [
            sys.executable,
            "-c",
            "import sys; import storygame.runtime.entry_snapshots; print('storygame.web_demo' in sys.modules)",
        ],
        cwd=ROOT,
        env={"PYTHONPATH": f"{ROOT}:{ROOT / 'packages' / 'worldkeeper' / 'src'}"},
        capture_output=True,
        text=True,
        check=True,
    )

    assert result.stdout.strip() == "False"


def test_regenerating_snapshots_twice_is_byte_identical(tmp_path: Path) -> None:
    root = _copy_story(tmp_path)

    paths = write_entry_snapshots(root)
    first = {path.name: path.read_bytes() for path in paths}
    write_entry_snapshots(root)

    assert first == {path.name: path.read_bytes() for path in paths}


def test_loader_package_is_identical_with_or_without_entry_directory(tmp_path: Path) -> None:
    with_entries = _copy_story(tmp_path)
    without_entries = tmp_path / "without-entry"
    shutil.copytree(STORY_ROOT, without_entries, ignore=shutil.ignore_patterns("entry"))

    assert load_story_package(with_entries) == load_story_package(without_entries)


def test_state_from_snapshot_matches_canonical_path_facts_and_world() -> None:
    state = RuntimeState.bootstrap(PACKAGE)
    for scene_id in SCENE_IDS:
        if scene_id != SCENE_IDS[0]:
            advance_state_to_scene(PACKAGE, state, scene_id, persona="canonical")
        snapshot = load_entry_snapshot(STORY_ROOT, scene_id)
        restored = state_from_snapshot(PACKAGE, snapshot)
        assert restored.facts == state.facts
        assert world_for(PACKAGE, restored.facts).export_state() == world_for(PACKAGE, state.facts).export_state()
        world = world_for(PACKAGE, restored.facts)
        assert world.entry_problems(PACKAGE.world.protagonist_id, world.area(PACKAGE.world.protagonist_id)) == ()


def test_tampered_world_fact_is_reported_as_drift_with_entity_id(tmp_path: Path) -> None:
    root = _copy_story(tmp_path)
    path = root / "entry" / "1B.json"
    snapshot = json.loads(path.read_text(encoding="utf-8"))
    snapshot["world"]["facts"].append(
        {"predicate": "wk_hidden", "subject": "memory_card", "object": None, "value": "true"}
    )
    path.write_text(json.dumps(snapshot, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    problems = check_entry_snapshots(root)

    assert any(problem == "DRIFT in scene 1B" for problem in problems)
    assert any("memory_card" in problem for problem in problems)


def test_removed_story_fact_is_reported_as_drift(tmp_path: Path) -> None:
    root = _copy_story(tmp_path)
    path = root / "entry" / "1A.json"
    snapshot = json.loads(path.read_text(encoding="utf-8"))
    snapshot["story_facts"].pop()
    path.write_text(json.dumps(snapshot, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    problems = check_entry_snapshots(root)

    assert any(problem == "DRIFT in scene 1A" for problem in problems)
    assert any("story fact removed" in problem for problem in problems)


def test_source_edit_stales_every_snapshot_and_blocks_resume(tmp_path: Path) -> None:
    root = _copy_story(tmp_path)
    package = load_story_package(root)
    old_snapshot = load_entry_snapshot(root, "1A")
    source = root / "source" / "story.yaml"
    source.write_text(source.read_text(encoding="utf-8") + "\n# source changed\n", encoding="utf-8")
    edited_package = load_story_package(root)

    problems = check_entry_snapshots(root)

    assert sum(problem.startswith("stale fingerprint") for problem in problems) == len(SCENE_IDS)
    with pytest.raises(EntrySnapshotError, match="source_fingerprint"):
        state_from_snapshot(edited_package, old_snapshot)
    assert package.story_id == edited_package.story_id


def test_hidden_held_item_in_snapshot_is_refused(tmp_path: Path) -> None:
    root = _copy_story(tmp_path)
    path = root / "entry" / "1B.json"
    snapshot = json.loads(path.read_text(encoding="utf-8"))
    snapshot["world"]["facts"].append(
        {"predicate": "wk_hidden", "subject": "memory_card", "object": None, "value": "true"}
    )
    with pytest.raises(EntrySnapshotError, match="held item memory_card is hidden"):
        state_from_snapshot(load_story_package(root), snapshot)


def test_carry_in_report_has_shape_and_synthetic_fixture_detects_missing_supply() -> None:
    fixture = load_story_package(ROOT / "tests" / "fixtures" / "stories" / "lighthouse-keeper")
    scenes = {scene.metadata.scene_id for scene in fixture.scenes}
    fake_package = SimpleNamespace(
        world=fixture.world,
        knowledge=fixture.knowledge,
        scenes=fixture.scenes,
        storylet_routes=SimpleNamespace(storylets=()),
    )
    original_producers = snapshots_module.producers
    original_consumers = snapshots_module.consumers
    original_required_storylet_ids = snapshots_module.required_storylet_ids
    fact_id = fixture.world.facts[0]
    snapshots_module.producers = lambda _package, candidate: (
        [SimpleNamespace(kind="storylet realization", scene_id="1A")] if candidate == fact_id else []
    )
    snapshots_module.consumers = lambda _package, candidate: (
        [SimpleNamespace(kind="gate", record_id="next_gate", scene_id="1B")] if candidate == fact_id else []
    )
    snapshots_module.required_storylet_ids = lambda _package: frozenset()
    try:
        report = carry_in_report(
            fake_package,
            {scene_id: {"scene_id": scene_id, "story_facts": []} for scene_id in scenes},
        )
    finally:
        snapshots_module.producers = original_producers
        snapshots_module.consumers = original_consumers
        snapshots_module.required_storylet_ids = original_required_storylet_ids

    assert report == [
        {
            "scene_id": "1B",
            "fact_id": fact_id,
            "consumer_kind": "gate",
            "consumer_id": "next_gate",
            "consumer_required": False,
            "supplied": False,
            "producer_scenes": ["1A"],
        }
    ]


def test_required_synthetic_gate_still_fails_snapshot_check(tmp_path: Path, monkeypatch) -> None:
    root = _copy_story(tmp_path)

    monkeypatch.setattr(
        snapshots_module,
        "carry_in_report",
        lambda _package, _snapshots: [
            {
                "scene_id": "1B",
                "fact_id": "synthetic_fact",
                "consumer_kind": "gate",
                "consumer_id": "required_gate",
                "consumer_required": True,
                "supplied": False,
                "producer_scenes": ["1A"],
            }
        ],
    )

    problems = check_entry_snapshots(root)

    assert problems == ["carry-in gate problem: scene 1B fact synthetic_fact consumer required_gate is not supplied"]


def test_cli_write_succeeds_and_check_is_clean(tmp_path: Path) -> None:
    root = _copy_story(tmp_path)

    assert main(["write", "--story-root", str(root)]) == 0
    assert main(["check", "--story-root", str(root)]) == 0
