from __future__ import annotations

import importlib.util
import tempfile
from pathlib import Path

import pytest

from storygame.runtime.state import RuntimeState
from storygame.runtime.world_model import world_for
from storygame.story_package.loader import load_story_package

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "ringer" / "environment_narration" / "drain_details_capture.py"
PACKAGE_ROOT = ROOT / "data" / "stories" / "continuity-initiative"


def _module():
    spec = importlib.util.spec_from_file_location("drain_details_capture", SCRIPT)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _arms_by_path():
    captures = _module().capture_arms()
    return {
        path: {
            arm: next(item for item in captures if item["path"] == path and item["arm"] == arm)
            for arm in ("control", "candidate")
        }
        for path in _module().PATHS
    }


@pytest.mark.nightly
def test_candidate_reuses_the_existing_storm_drain_and_adds_no_world_entities() -> None:
    module = _module()
    captures = module.capture_arms()
    control = load_story_package(PACKAGE_ROOT)
    control_ids = {
        entity.id
        for entities in (control.world.locations, control.world.npcs, control.world.groups, control.world.items)
        for entity in entities
    }
    candidate = next(item for item in captures if item["arm"] == "candidate")
    assert candidate["status"] == "captured"

    with tempfile.TemporaryDirectory() as temporary:
        candidate_root = module._candidate_package_root(Path(temporary))
        loaded = load_story_package(candidate_root)
    loaded_ids = {
        entity.id
        for entities in (loaded.world.locations, loaded.world.npcs, loaded.world.groups, loaded.world.items)
        for entity in entities
    }
    assert loaded_ids == control_ids
    assert world_for(loaded, RuntimeState.bootstrap(loaded).facts).resolve("storm drain") == "storm_drain"
    assert world_for(control, RuntimeState.bootstrap(control).facts).resolve("storm drain") == "storm_drain"
    assert set(loaded.knowledge_indexes.by_id) == set(control.knowledge_indexes.by_id)


@pytest.mark.nightly
def test_candidate_changes_only_affected_scene_requests_and_never_scene_1b2_or_other_scene() -> None:
    module = _module()
    by_path = _arms_by_path()
    changed_paths = {path for path, arms in by_path.items() if arms["control"]["diff"]["status"] == "changed"}
    assert changed_paths == set(module.PATHS)
    control_scene = module._capture_scene_prompt(load_story_package(PACKAGE_ROOT), "1A")
    with tempfile.TemporaryDirectory() as temporary:
        candidate_root = module._candidate_package_root(Path(temporary))
        candidate_scene = module._capture_scene_prompt(load_story_package(candidate_root), "1A")
    assert control_scene == candidate_scene
    assert module.CANDIDATE_PHRASE not in control_scene["user"]


@pytest.mark.nightly
def test_candidate_reaches_the_1b_requests_without_future_reveal_leak() -> None:
    module = _module()
    by_path = _arms_by_path()
    for path in module.PATHS:
        control = by_path[path]["control"]
        candidate = by_path[path]["candidate"]
        if control["status"] != "captured":
            assert control["status"] == "not reproducible offline"
            continue
        assert candidate["status"] == "captured"
        candidate_text = "\n".join(request["user"] for request in candidate["requests"])
        assert module.CANDIDATE_PHRASE in candidate_text
        if path in {"opening", "initial_inspect", "retry", "malformed_recovery", "scene_1b2"}:
            assert "transit token" not in candidate_text.casefold()
            assert "handwritten number sequence" not in candidate_text.casefold()
            assert "michelle's photograph" not in candidate_text.casefold()
