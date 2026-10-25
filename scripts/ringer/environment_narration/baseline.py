"""Freeze offline evidence of the current environment-narration behavior."""

from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import os
import re
import subprocess
import sys
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path
from types import ModuleType, SimpleNamespace
from typing import Any

ROOT = Path(__file__).resolve().parents[3]
PACKAGE_ROOT = ROOT / "data/stories/continuity-initiative"
WORKER_SOURCE = ROOT / "worker/src/index.js"
HISTORICAL_ARTIFACT_PATHS: tuple[Path, ...] = (
    ROOT / "bench/results/boarding-probe-live/probe.json",
    ROOT / "bench/results/open-probe-live/probe.json",
    ROOT / ".plans/1a-transcript-continuity/baseline-live-narrations.json",
    ROOT / ".plans/1a-transcript-continuity/boarding-probe-prereg.md",
)
HISTORICAL_GIT_OBJECT = "5ea0119955c62b84699a8dc7878a4af770b55a7e:.plans/world-model.md"
LAPTOP = "Kristin's laptop"
LAPTOP_PLACE = "passenger seat"

CASE_SPECS = (
    {
        "id": "boarding_go_to_truck",
        "place": "outside_house",
        "command": "Go to the truck.",
        "boards": True,
        "only_boards": True,
    },
    {
        "id": "boarding_get_in",
        "place": "outside_house",
        "command": "Get in.",
        "boards": True,
        "only_boards": True,
    },
    {
        "id": "boarding_enter_truck",
        "place": "outside_house",
        "command": "Enter the truck.",
        "boards": True,
        "only_boards": True,
    },
    {
        "id": "boarding_from_kitchen",
        "place": "kitchen",
        "command": "Go out to the truck.",
        "boards": True,
        "only_boards": True,
    },
    {
        "id": "already_seated",
        "place": "outside_house",
        "command": "Get in the truck.",
        "boards": True,
        "only_boards": True,
    },
    {
        "id": "compound_enter_and_inspect",
        "place": "outside_house",
        "command": "Enter the truck and inspect my laptop.",
        "boards": True,
        "only_boards": False,
    },
    {
        "id": "approach_truck",
        "place": "outside_house",
        "command": "Approach the truck.",
        "boards": False,
        "only_boards": False,
    },
    {
        "id": "look_around_outside",
        "place": "outside_house",
        "command": "Look around.",
        "boards": False,
        "only_boards": False,
    },
)


def _jsonable(value: Any) -> Any:
    if value is None or isinstance(value, (str, int, float, bool)):
        return value
    if isinstance(value, dict):
        return {str(key): _jsonable(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_jsonable(item) for item in value]
    if isinstance(value, set):
        return sorted((_jsonable(item) for item in value), key=lambda item: json.dumps(item, sort_keys=True))
    if hasattr(value, "model_dump"):
        return _jsonable(value.model_dump(mode="json"))
    return repr(value)


def _canonical_json(value: Any) -> bytes:
    return json.dumps(_jsonable(value), ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode()


def _sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def _state_hash(state: Any) -> str:
    facts = {"asserted": [_jsonable(fact) for fact in sorted(state.facts.asserted, key=lambda fact: fact.key)]}
    return _sha256_bytes(_canonical_json(facts))


def _package_hash(package_root: Path) -> str:
    """Hash package paths and bytes using the repository's bench convention."""

    digest = hashlib.sha256()
    files = sorted(path for path in package_root.rglob("*") if path.is_file())
    for path in files:
        relative = path.relative_to(package_root).as_posix().encode()
        content = path.read_bytes()
        digest.update(len(relative).to_bytes(8, "big"))
        digest.update(relative)
        digest.update(len(content).to_bytes(8, "big"))
        digest.update(content)
    return digest.hexdigest()


def parse_worker_default_model(source: str) -> str:
    match = re.search(
        r"const\s+[A-Za-z_$][\w$]*\s*=\s*asString\(env\.CF_AI_MODEL\)\.trim\(\)\s*\|\|\s*([\"'])([^\"']+)\1",
        source,
    )
    if match is None:
        raise RuntimeError("worker source does not contain the default model")
    return match.group(2)


def _worker_default_model(path: Path | None = None) -> str:
    path = WORKER_SOURCE if path is None else path
    return parse_worker_default_model(path.read_text(encoding="utf-8"))


def _git(*args: str, check: bool = True) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["git", *args],
        cwd=ROOT,
        check=check,
        capture_output=True,
        text=True,
    )


def _tracked_scope_dirty() -> bool:
    result = _git("diff", "--name-only", "HEAD", "--", "storygame", "data", "worker", "scripts", "tests")
    return bool(result.stdout.strip())


def _historical_artifacts() -> list[dict[str, object]]:
    artifacts = []
    for raw_path in HISTORICAL_ARTIFACT_PATHS:
        path = Path(raw_path)
        exists = path.is_file()
        artifacts.append(
            {
                "path": str(path.relative_to(ROOT)) if path.is_relative_to(ROOT) else str(path),
                "exists": exists,
                "sha256": _sha256_bytes(path.read_bytes()) if exists else None,
            }
        )
    exists = _git("cat-file", "-e", HISTORICAL_GIT_OBJECT, check=False).returncode == 0
    artifacts.append({"path": HISTORICAL_GIT_OBJECT, "exists": exists})
    return artifacts


def _load_boarding_probe() -> ModuleType:
    path = ROOT / "scripts/ringer/transcript_1a/boarding_probe.py"
    spec = importlib.util.spec_from_file_location("_environment_baseline_boarding_probe", path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"could not load boarding probe from {path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


@contextmanager
def _stubs(ask: Any) -> Iterator[None]:
    from storygame.runtime.cloudflare import CloudflareTurnProvider
    from storygame.runtime.jev import JevClient

    original_jev = JevClient.__dict__["from_environment"]
    original_item_facts = CloudflareTurnProvider._request_item_facts
    JevClient.from_environment = classmethod(  # type: ignore[method-assign]
        lambda cls: SimpleNamespace(ask=ask)
    )
    CloudflareTurnProvider._request_item_facts = lambda self, _payload: {  # type: ignore[method-assign]
        "refers": [],
        "same_as": {},
    }
    try:
        yield
    finally:
        JevClient.from_environment = original_jev
        CloudflareTurnProvider._request_item_facts = original_item_facts


def _section_bounds(lines: list[str], heading: str) -> tuple[int, int]:
    start = next((index for index, line in enumerate(lines) if line == f"{heading}:"), None)
    if start is None:
        raise RuntimeError(f"narrator request has no {heading} section")
    end = len(lines)
    for index in range(start + 1, len(lines)):
        if lines[index].endswith(":") and not lines[index].startswith("-"):
            end = index
            break
    return start, end


def _things_names(user: str) -> list[str]:
    lines = user.splitlines()
    start, end = _section_bounds(lines, "THINGS")
    names = []
    for line in lines[start + 1 : end]:
        if not line.startswith("- "):
            continue
        entry = line[2:]
        names.append(entry.split(".", 1)[0])
    return names


def _just_before_line(user: str) -> str | None:
    for line in user.splitlines():
        stripped = line.lstrip()
        if stripped.startswith("- Just before this:"):
            return stripped[len("- Just before this:") :].strip()
        if stripped.startswith("Just before this:"):
            return stripped[len("Just before this:") :].strip()
    return None


def _displayed_narration(value: Any) -> str | None:
    if not isinstance(value, dict):
        return None
    segments = value.get("segments")
    if not isinstance(segments, list):
        return None
    text = " ".join(
        str(segment["text"])
        for segment in segments
        if isinstance(segment, dict) and segment.get("kind") == "narration" and segment.get("text")
    )
    return text or None


def _expected_observations(case_id: str) -> list[dict[str, object]]:
    if case_id in {"approach_truck", "look_around_outside"}:
        return []
    return [
        {
            "thing": LAPTOP,
            "place": LAPTOP_PLACE,
            "must_be_described": True,
            "source": "plan regression matrix",
        }
    ]


def _capture_case(package: Any, spec: dict[str, object], boarding_probe: ModuleType) -> dict[str, object]:
    from storygame.runtime.capture import WorldCapture, build_capture_provider
    from storygame.runtime.cloudflare import CloudflareTurnProvider

    state = boarding_probe._state_at(package, str(spec["place"]))

    def ask(_state: object, questions: dict[str, object]) -> dict[str, dict[str, float]]:
        return {
            key: {
                "noul": float(
                    spec["boards"]
                    if key == "boards_vehicle"
                    else spec["only_boards"]
                    if key == "only_boards_vehicle"
                    else False
                )
            }
            for key in questions
        }

    with _stubs(ask):
        provider = build_capture_provider(state)
        provider._request_item_facts = lambda _payload: {"refers": [], "same_as": {}}
        captured: dict[str, str] = {}

        def dispatch(system: str, user: dict[str, object]) -> dict[str, object]:
            captured["system"] = system
            captured["user"] = provider._section_user_prompt(user)
            return {"segments": [], "selected_knowledge_ids": []}

        provider._dispatch = dispatch
        if spec["id"] == "already_seated":
            provider._example_player_input = ""
            WorldCapture(provider, ask).before_turn("Enter the truck.")

        state_hash_before = _state_hash(state)
        capture = WorldCapture(provider, ask)
        capture.before_turn(str(spec["command"]))
        state_hash_after = _state_hash(state)
        command_consumed = bool(provider.command_consumed)

        if command_consumed:
            provider._dispatch = lambda _system, _user: (_ for _ in ()).throw(
                AssertionError("engine-text turn dispatched to narrator")
            )
            result = provider(str(spec["command"]))
            engine_text_turn = bool(provider.last_turn_engine_text)
            engine_text = _displayed_narration(result)
            provider._dispatch = dispatch
            CloudflareTurnProvider.__call__(provider, str(spec["command"]))
            source = "bypass_for_capture"
        else:
            result = provider(str(spec["command"]))
            engine_text_turn = bool(provider.last_turn_engine_text)
            engine_text = None
            source = "product"

        if "system" not in captured or "user" not in captured:
            raise RuntimeError(f"provider did not produce a narrator request for {spec['id']!r}")

    user = captured["user"]
    things_names = _things_names(user)
    just_before_line = _just_before_line(user)
    expected = _expected_observations(str(spec["id"]))
    omissions = [entry["thing"] for entry in expected if entry["thing"] not in things_names]
    return {
        "id": spec["id"],
        "place": spec["place"],
        "command": spec["command"],
        "classifier_answers": {"boards": spec["boards"], "only_boards": spec["only_boards"]},
        "state_hash_before": state_hash_before,
        "state_hash_after_implicit": state_hash_after,
        "implicit_steps": list(provider.prior_steps),
        "command_consumed": command_consumed,
        "engine_text_turn": engine_text_turn,
        "engine_text": engine_text,
        "narrator_request": {"system": captured["system"], "user": user, "source": source},
        "things_names": things_names,
        "just_before_line": just_before_line,
        "expected_observations": expected,
        "omissions": omissions,
        "laptop_only_in_background_line": LAPTOP in (just_before_line or "") and LAPTOP not in things_names,
    }


def _build_case_records(package: Any, boarding_probe: ModuleType) -> list[dict[str, object]]:
    return [_capture_case(package, spec, boarding_probe) for spec in CASE_SPECS]


def build_baseline() -> dict[str, object]:
    from storygame.story_package.loader import load_story_package

    os.environ.setdefault("CLOUDFLARE_WORKER_URL", "https://worker.example/turn")
    package = load_story_package(PACKAGE_ROOT)
    boarding_probe = _load_boarding_probe()
    return {
        "schema": 1,
        "source": {
            "git_sha": _git("rev-parse", "HEAD").stdout.strip(),
            "dirty": _tracked_scope_dirty(),
            "package_hash": _package_hash(PACKAGE_ROOT),
            "worker_default_model": _worker_default_model(),
            "model_override_env": os.environ.get("CF_AI_MODEL"),
            "deployed_model_verified": False,
            "network_calls": 0,
        },
        "historical_artifacts": _historical_artifacts(),
        "cases": _build_case_records(package, boarding_probe),
    }


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args(argv)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(build_baseline(), ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
