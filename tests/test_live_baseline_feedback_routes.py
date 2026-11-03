from __future__ import annotations

import importlib.util
import json
import os
import subprocess
from pathlib import Path

import pytest

from storygame.story_package.loader import load_story_package

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts/ringer/transcript_1a/live_baseline.py"
CHECKER = ROOT / "scripts/ringer/transcript_1a/check_live_baseline.py"
PYTHON = ROOT / ".venv/bin/python"
PACKAGE_ROOT = ROOT / "data/stories/continuity-initiative"

FEEDBACK_ROUTES = {
    "feedback_raw": (
        "open the drawer",
        "feel in the gap",
        "head out to the truck",
        "look for the laptop",
        "get in the truck",
        "plug the memory card into the laptop",
    ),
    "feedback_canonical": (
        "Pull out the drawer.",
        "Feel in the gap beneath the drawer.",
        "Go out to the truck.",
        "Look for my laptop.",
        "Get in the truck.",
        "Plug the memory card into my laptop.",
    ),
    "feedback_counter": (
        "Pull out the drawer.",
        "Feel in the gap beneath the drawer.",
        "Go out to the truck.",
        "Take my laptop.",
        "Get out of the truck.",
        "Examine the truck.",
        "Get in the truck.",
        "Plug the memory card into my laptop.",
        "Drive to the park.",
    ),
}

EXISTING_ROUTES = {
    "reported": (
        "go in the house",
        "feel in the gap",
        "look at the fabric",
        "pull out the drawer",
        "feel under the drawer",
        "go out to the truck",
        "get in",
        "look around",
    ),
    "corrected": (
        "go in the house",
        "pull out the drawer",
        "feel in the gap",
        "look around",
        "wait",
        "wait",
        "go out to the truck",
        "get in",
        "look around",
        "get out of the truck",
        "look around",
        "wait",
    ),
    "witnessed": (
        "go in the house",
        "examine the carved initials",
        "wait",
        "wait",
        "wait",
        "feel under the drawer",
        "say what the card is to the officer",
        "wait",
        "go out to the truck",
        "get in",
        "look around",
    ),
    "movement": (
        "look around",
        "go outside",
        "look around",
        "go out to the truck",
        "look around",
        "get out of the truck",
        "look around",
        "go inside",
        "look around",
        "go out to the truck",
        "go inside",
        "look around",
    ),
    "observe": (
        "inspect the drawer",
        "pull out the drawer",
        "feel under the drawer",
        "feel under the drawer",
        "go outside",
        "inspect the truck",
        "enter the truck",
        "inspect the passenger seat",
        "examine my laptop",
        "get out of the truck",
        "examine the truck",
        "go inside",
        "inspect the drawer",
    ),
    "observe_topup": (
        "inspect the drawer",
        "pull out the drawer",
        "feel under the drawer",
        "feel under the drawer",
        "go outside",
        "inspect the truck",
        "enter the truck",
        "pick up my laptop",
        "inspect the passenger seat",
    ),
    "observe_under_first": (
        "feel under the drawer",
        "feel under the drawer",
        "inspect the drawer",
        "pull out the drawer",
    ),
    "observe_look_inside_under": (
        "inspect the drawer",
        "examine the drawer",
        "search the drawer",
        "check the drawer",
        "look inside the drawer",
        "look under the drawer",
    ),
    "observe_supporters_1a": (
        "inspect the workstation",
        "search the workstation",
        "look under the workstation",
        "examine the workstation chair",
        "check the workstation chair",
        "look under the workstation chair",
    ),
    "observe_park_bench_1b": (
        "inspect the park bench",
        "look under the park bench",
        "search the park bench",
        "check the park bench",
        "look under the park bench",
        "inspect the storm drain",
    ),
    "observe_storm_drain_1b": ("inspect the storm drain",),
    "observe_service_gate_1b": ("inspect the service gate",),
    "observe_back_door_1a": ("inspect the back door",),
    "observe_executive_desk_3b": (
        "inspect the executive desk",
        "search the executive desk",
        "look under the executive desk",
        "examine the executive desk",
        "check the executive desk",
        "look under the executive desk",
    ),
}


def _module():
    module_spec = importlib.util.spec_from_file_location("live_baseline_feedback_routes", SCRIPT)
    module = importlib.util.module_from_spec(module_spec)
    assert module_spec.loader is not None
    module_spec.loader.exec_module(module)
    return module


def test_feedback_routes_and_existing_routes_are_exact() -> None:
    module = _module()

    assert set(module.ROUTES) == set(EXISTING_ROUTES) | set(FEEDBACK_ROUTES)
    for route, inputs in EXISTING_ROUTES.items():
        assert module.ROUTES[route] == inputs
    for route, inputs in FEEDBACK_ROUTES.items():
        assert module.ROUTES[route] == inputs


@pytest.mark.parametrize("route", tuple(FEEDBACK_ROUTES))
def test_feedback_routes_use_normal_1a_start_and_are_not_scene_routes(route: str) -> None:
    module = _module()
    package = load_story_package(PACKAGE_ROOT)

    assert route not in module.NEW_ROUTES
    assert route not in module.ROUTE_START_SCENES
    state, checkpoint_index = module._start_state(package, route)
    assert state.current_scene_id == "1A"
    assert checkpoint_index is None


@pytest.mark.parametrize("route", tuple(FEEDBACK_ROUTES))
def test_feedback_route_dry_run_writes_artifacts_and_passes_checker(tmp_path: Path, monkeypatch, route: str) -> None:
    module = _module()
    output = tmp_path / route
    monkeypatch.setenv("PYTHONPATH", str(ROOT))
    monkeypatch.setenv("TMPDIR", "/tmp")
    monkeypatch.setenv("CLOUDFLARE_WORKER_URL", "https://w.example")

    assert (
        module.main(
            [
                "--route",
                route,
                "--replicates",
                "1",
                "--dry-run",
                "--out",
                str(output),
            ]
        )
        == 0
    )
    assert (output / "rows.json").is_file()
    assert (output / "summary.json").is_file()
    summary = json.loads((output / "summary.json").read_text())
    assert summary["route"] == route
    assert summary["inputs"] == list(FEEDBACK_ROUTES[route])

    env = os.environ.copy()
    env.update(PYTHONPATH=str(ROOT), TMPDIR="/tmp", CLOUDFLARE_WORKER_URL="https://w.example")
    subprocess.run(
        [str(PYTHON), str(CHECKER), str(output), "1", "--mode", "dry"],
        check=True,
        env=env,
    )
