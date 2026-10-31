"""Capture/check prompt effects; this is not evidence the material will work."""

from __future__ import annotations

import argparse
import importlib.util
import json
import shutil
import sys
import tempfile
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[3]
PACKAGE_ROOT = ROOT / "data" / "stories" / "continuity-initiative"
DETAILS_LINE = "**Details:** ordinary park bench; damaged grounds; service path; checkpoints; emergency patrols"
CANDIDATE_SUFFIX = "; storm drain opening in the damaged grounds"
CANDIDATE_PHRASE = "storm drain opening in the damaged grounds"
PATHS = (
    "opening",
    "initial_inspect",
    "retry",
    "malformed_recovery",
    "post_find_inspect",
    "unrelated_bench",
    "scene_1b2",
    "earned_escape",
)
ESCAPE_COMMAND = "Get out through the storm drains and watch how he opens the secured gate."


def _load_probe() -> Any:
    probe_path = ROOT / "scripts" / "ringer" / "environment_narration" / "hidden_bench_prose_probe.py"
    spec = importlib.util.spec_from_file_location("drain_details_hidden_probe", probe_path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load offline probe from {probe_path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _load_package(root: Path) -> Any:
    from storygame.story_package.loader import load_story_package

    return load_story_package(root)


def _candidate_package_root(destination: Path) -> Path:
    candidate_root = destination / "continuity-initiative-candidate"
    shutil.copytree(PACKAGE_ROOT, candidate_root)
    plot_path = candidate_root / "plot.md"
    plot = plot_path.read_text(encoding="utf-8")
    assert plot.count(DETAILS_LINE) == 1
    plot_path.write_text(plot.replace(DETAILS_LINE, DETAILS_LINE + CANDIDATE_SUFFIX, 1), encoding="utf-8")
    return candidate_root


def _build_state(package: Any, *, recovered: bool = False) -> Any:
    probe = _load_probe()
    state = probe._scene_1b_state(package)
    if recovered:
        from storygame.runtime.facts import Fact
        from storygame.runtime.world_model import apply_world_effects

        state.facts.assert_fact(Fact(predicate="bench_clues_recovered", subject="story", value="true"))
        apply_world_effects(package, state.facts)
    return state


def _force_1b2(package: Any, state: Any, provider: Any) -> None:
    from bench.core import resolve_beat

    selected = resolve_beat(package, "1B", "1B.2")
    provider._forced_beat_anchors.add(selected.anchor)
    storylets = [item.id for item in package.storylets if selected.anchor in item.source_links]
    if not storylets:
        raise RuntimeError("1B.2 has no storylet source")
    state.active_event_ids.update(storylets)


def _fake_response(text: str = "The scene continues.") -> dict[str, object]:
    return {
        "segments": [{"kind": "narration", "text": text}],
        "selected_knowledge_ids": [],
        "item_facts": {},
    }


def _run_engine(
    package: Any,
    command: str | None = None,
    *,
    recovered: bool = False,
    force_1b2: bool = False,
    retry: bool = False,
    malformed: bool = False,
    earned_escape: bool = False,
) -> list[dict[str, str]]:
    from storygame.runtime.cloudflare import CloudflareTurnProvider
    from storygame.runtime.engine import RuntimeEngine
    from storygame.runtime.validation import ProposalValidationError

    probe = _load_probe()
    state = _build_state(package, recovered=recovered)
    provider = probe._world_aware_provider(state)
    if force_1b2:
        _force_1b2(package, state, provider)
    if earned_escape:
        from storygame.runtime.facts import Fact

        state.active_event_ids.add("SL-1B-C")
        for fact_id in ("brandon_identified", "missing_may_be_alive"):
            state.facts.assert_fact(Fact(predicate=fact_id, subject="story", value="true"))

    requests: list[dict[str, str]] = []
    request_count = 0

    def recording_request(_provider: Any, payload: dict[str, object]) -> dict[str, object]:
        nonlocal request_count
        if payload.get("__freytag_request_budget", "narration") == "item_facts":
            return {"refers": [], "same_as": {}}
        requests.append({"system": str(payload["system"]), "user": str(payload["user"])})
        request_count += 1
        if malformed and request_count == 1:
            raise json.JSONDecodeError("offline malformed reply", "{", 0)
        return _fake_response()

    original_request = CloudflareTurnProvider._request
    CloudflareTurnProvider._request = recording_request
    try:
        engine = RuntimeEngine(state, provider)
        if command is None:
            engine.opening()
        else:
            engine.opening()
            requests.clear()
            request_count = 0
            if retry:
                original_validate = engine.narration_validator.validate
                validation_calls = 0

                def reject_once(*args: Any, **kwargs: Any) -> None:
                    nonlocal validation_calls
                    validation_calls += 1
                    if validation_calls == 1:
                        raise ProposalValidationError("offline retry", code="test_guard_retry")
                    original_validate(*args, **kwargs)

                engine.narration_validator.validate = reject_once
            engine.turn(command)
    finally:
        CloudflareTurnProvider._request = original_request
    return requests


def _capture_path(package: Any, path: str) -> dict[str, Any]:
    try:
        if path == "opening":
            requests = _run_engine(package)
        elif path == "initial_inspect":
            requests = _run_engine(package, "Inspect the storm drain.")
        elif path == "retry":
            requests = _run_engine(package, "Inspect the storm drain.", retry=True)
        elif path == "malformed_recovery":
            requests = _run_engine(package, "Inspect the storm drain.", malformed=True)
        elif path == "post_find_inspect":
            requests = _run_engine(package, "Inspect the storm drain.", recovered=True)
        elif path == "unrelated_bench":
            requests = _run_engine(package, "Look under the park bench.")
        elif path == "scene_1b2":
            requests = _run_engine(package, force_1b2=True)
        elif path == "earned_escape":
            requests = _run_engine(package, ESCAPE_COMMAND, recovered=True, earned_escape=True)
        else:
            raise ValueError(f"unknown capture path: {path}")
        return {
            "path": path,
            "status": "captured",
            "requests": requests,
            "error": None,
        }
    except Exception as error:  # noqa: BLE001 - preserve offline evidence per path
        return {
            "path": path,
            "status": "not reproducible offline",
            "requests": [],
            "error": f"{type(error).__name__}: {error}",
        }


def _capture_scene_prompt(package: Any, scene_id: str) -> dict[str, str]:
    from storygame.runtime.cloudflare import CloudflareTurnProvider

    probe = _load_probe()
    from storygame.runtime.state import RuntimeState

    state = RuntimeState.bootstrap(package)
    state.current_scene_id = scene_id
    scene = next(item for item in package.scenes if item.metadata.scene_id == scene_id)
    state.phase = scene.metadata.freytag_phase
    state._assert_scene_entry_fact(scene_id)
    provider = probe._world_aware_provider(state)
    requests: list[dict[str, str]] = []

    def recording_request(_provider: Any, payload: dict[str, object]) -> dict[str, object]:
        if payload.get("__freytag_request_budget", "narration") != "item_facts":
            requests.append({"system": str(payload["system"]), "user": str(payload["user"])})
        return _fake_response()

    original_request = CloudflareTurnProvider._request
    CloudflareTurnProvider._request = recording_request
    try:
        provider.opening()
    finally:
        CloudflareTurnProvider._request = original_request
    return requests[-1]


def _diff(control: dict[str, Any], candidate: dict[str, Any]) -> dict[str, Any]:
    control_requests = control["requests"]
    candidate_requests = candidate["requests"]
    return {
        "status": "identical" if control_requests == candidate_requests else "changed",
        "request_count_control": len(control_requests),
        "request_count_candidate": len(candidate_requests),
        "system_changed": [
            index
            for index, (left, right) in enumerate(zip(control_requests, candidate_requests, strict=False))
            if left["system"] != right["system"]
        ],
        "user_changed": [
            index
            for index, (left, right) in enumerate(zip(control_requests, candidate_requests, strict=False))
            if left["user"] != right["user"]
        ],
    }


def capture_arms() -> list[dict[str, Any]]:
    """Load control and candidate packages and capture all eight paths in each arm."""

    with tempfile.TemporaryDirectory(prefix="t9h-drain-details-") as temporary:
        candidate_root = _candidate_package_root(Path(temporary))
        control_package = _load_package(PACKAGE_ROOT)
        candidate_package = _load_package(candidate_root)
        captures: list[dict[str, Any]] = []
        for arm, package in (("control", control_package), ("candidate", candidate_package)):
            for path in PATHS:
                capture = _capture_path(package, path)
                capture["arm"] = arm
                captures.append(capture)
    by_path = {
        path: {
            arm: next(item for item in captures if item["path"] == path and item["arm"] == arm)
            for arm in ("control", "candidate")
        }
        for path in PATHS
    }
    for path in PATHS:
        control = by_path[path]["control"]
        candidate = by_path[path]["candidate"]
        control["diff"] = _diff(control, candidate)
        candidate["diff"] = control["diff"]
    return captures


def _document(captures: list[dict[str, Any]]) -> dict[str, Any]:
    return {
        "schema": 1,
        "candidate_phrase": CANDIDATE_PHRASE,
        "paths": list(PATHS),
        "captures": captures,
    }


def _print_summary(captures: list[dict[str, Any]]) -> None:
    for path in PATHS:
        control = next(item for item in captures if item["path"] == path and item["arm"] == "control")
        print(
            f"{path}: {control['diff']['status']} "
            f"({control['diff']['user_changed']} user, {control['diff']['system_changed']} system)"
        )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", type=Path, default=Path(tempfile.gettempdir()) / "t9h-drain-details-capture.json")
    args = parser.parse_args(argv)
    try:
        captures = capture_arms()
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(json.dumps(_document(captures), indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
        _print_summary(captures)
        return 0
    except Exception as error:  # noqa: BLE001 - CLI reports a free-check failure
        print(f"capture tool error: {error}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
