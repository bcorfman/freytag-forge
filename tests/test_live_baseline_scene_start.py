from __future__ import annotations

import importlib.util
import json
from pathlib import Path

import pytest

from storygame.runtime.world_model import world_for
from storygame.story_package.loader import load_story_package

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts/ringer/transcript_1a/live_baseline.py"
PACKAGE_ROOT = ROOT / "data/stories/continuity-initiative"


def _module():
    module_spec = importlib.util.spec_from_file_location("live_baseline_scene_start", SCRIPT)
    module = importlib.util.module_from_spec(module_spec)
    assert module_spec.loader is not None
    module_spec.loader.exec_module(module)
    return module


def _fact_set(facts) -> set[str]:
    return {json.dumps(fact.model_dump(mode="json"), sort_keys=True) for fact in facts.asserted}


def test_new_route_command_lists_are_pinned() -> None:
    module = _module()

    assert module.ROUTES["observe_supporters_1a"] == (
        "inspect the workstation",
        "search the workstation",
        "look under the workstation",
        "examine the workstation chair",
        "check the workstation chair",
        "look under the workstation chair",
    )
    assert module.ROUTES["observe_park_bench_1b"] == (
        "inspect the park bench",
        "look under the park bench",
        "search the park bench",
        "check the park bench",
        "look under the park bench",
        "inspect the storm drain",
    )
    assert module.ROUTES["observe_executive_desk_3b"] == (
        "inspect the executive desk",
        "search the executive desk",
        "look under the executive desk",
        "examine the executive desk",
        "check the executive desk",
        "look under the executive desk",
    )


@pytest.mark.parametrize(
    ("route", "scene_id", "thing_id"),
    [
        ("observe_park_bench_1b", "1B", "park_bench"),
        ("observe_executive_desk_3b", "3B", "rebecca_desk"),
    ],
)
def test_scene_route_restores_entry_checkpoint_and_placements(route: str, scene_id: str, thing_id: str) -> None:
    module = _module()
    package = load_story_package(PACKAGE_ROOT)

    state, checkpoint_index = module._start_state(package, route)
    assert checkpoint_index is not None
    checkpoint = next(
        checkpoint
        for checkpoint in __import__("tests.journey_prefix", fromlist=["_default_walk"])._default_walk().checkpoints
        if checkpoint.snapshot.current_scene_id == scene_id
    )
    scene = next(scene for scene in package.scenes if scene.metadata.scene_id == scene_id)
    expected_parent = scene.metadata.item_placements[thing_id].parent

    assert state.current_scene_id == scene_id
    assert state.phase == scene.metadata.freytag_phase
    assert state.facts.matching(f"scene_{scene_id.lower()}_entry_known")
    assert _fact_set(state.facts) == _fact_set(checkpoint.snapshot.facts)
    assert world_for(package, state.facts).parent(thing_id) == expected_parent


def test_park_bench_entry_world_structure_records_under_clues_and_checkpoint() -> None:
    module = _module()
    package = load_story_package(PACKAGE_ROOT)
    state, checkpoint_index = module._start_state(package, "observe_park_bench_1b")
    structure = module._world_structure(state)
    walk = __import__("tests.journey_prefix", fromlist=["_default_walk"])._default_walk()

    assert checkpoint_index == next(
        index for index, checkpoint in enumerate(walk.checkpoints) if checkpoint.snapshot.current_scene_id == "1B"
    )
    for entity_id in ("transit_card", "number_sequence", "michelle_photograph"):
        assert structure[entity_id]["parent"] == "park_bench"
        assert structure[entity_id]["relation"] == "under"
        assert structure[entity_id]["hidden"] is False


def test_start_checkpoint_index_is_the_first_checkpoint_in_each_scene() -> None:
    module = _module()
    package = load_story_package(PACKAGE_ROOT)
    walk = __import__("tests.journey_prefix", fromlist=["_default_walk"])._default_walk()

    for route, scene_id in module.ROUTE_START_SCENES.items():
        state, checkpoint_index = module._start_state(package, route)
        assert checkpoint_index == next(
            index
            for index, checkpoint in enumerate(walk.checkpoints)
            if checkpoint.snapshot.current_scene_id == scene_id
        )
        assert state.current_scene_id == scene_id


def test_missing_tracked_thing_is_recorded_as_none() -> None:
    module = _module()
    package = load_story_package(PACKAGE_ROOT)
    state, _checkpoint_index = module._start_state(package, "observe_park_bench_1b")
    module.TRACKED = (*module.TRACKED, "thing_missing_from_story")

    places = module._places(state)

    assert places["thing_missing_from_story"] is None


def test_legacy_route_opening_shape_is_unchanged(tmp_path: Path) -> None:
    module = _module()
    output = tmp_path / "legacy"

    assert (
        module.main(
            [
                "--dry-run",
                "--route",
                "observe_look_inside_under",
                "--replicates",
                "1",
                "--turns",
                "1",
                "--out",
                str(output),
            ]
        )
        == 0
    )
    rows = json.loads((output / "rows.json").read_text())

    assert set(rows[0]["opening"]) == {"narration", "places", "prompts", "provider_responses"}
    assert "start_scene" not in rows[0]["opening"]
    assert "start_checkpoint_index" not in rows[0]["opening"]


@pytest.mark.parametrize("route", ["observe_supporters_1a", "observe_park_bench_1b", "observe_executive_desk_3b"])
def test_new_routes_support_dry_run_call_count_shape(tmp_path: Path, route: str) -> None:
    module = _module()
    output = tmp_path / route

    assert (
        module.main(
            [
                "--dry-run",
                "--route",
                route,
                "--replicates",
                "1",
                "--out",
                str(output),
            ]
        )
        == 0
    )
    summary = json.loads((output / "summary.json").read_text())
    rows = json.loads((output / "rows.json").read_text())

    assert {"calls_made", "max_calls", "real_calls", "stopped_reason"} <= set(summary)
    assert summary["real_calls"] == 0
    assert rows[0]["opening"]["start_scene"] in {"1A", "1B", "3B"}


def test_unreachable_scene_start_fails_before_replicate_calls() -> None:
    module = _module()
    package = load_story_package(PACKAGE_ROOT)
    module.ROUTE_START_SCENES["unreachable"] = "never_reached"

    with pytest.raises(RuntimeError) as raised:
        module._start_state(package, "unreachable")

    assert "never_reached" in str(raised.value)
