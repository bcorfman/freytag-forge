# ruff: noqa: E501
"""Independent check for round 7: within-scene order and prompt parity of the compiled default story.

Run from a worktree root with PYTHONPATH set (no uv). Exit 0 only when, for every scene,
(1) storylets, storylet routes, deliveries, pacing events and knowledge claims keep the legacy
within-scene order, and (2) `bench prompt` for every scene entry and every beat is byte-identical
between the compiled default package and the frozen legacy package. Never calls a model.
"""

from __future__ import annotations

import os
import re
import subprocess
import sys
from pathlib import Path

from storygame.story_package import load_story_package
from storygame.story_package.loader import load_legacy_story_package

LEGACY = Path("tests/fixtures/parity/continuity-initiative/legacy")
DEFAULT = Path("data/stories/continuity-initiative")


def scene_of(item: object) -> str | None:
    for field in ("scene_id",):
        if hasattr(item, field):
            return getattr(item, field)
    return None


def sequences(package) -> dict[str, list[tuple[str, str]]]:
    knowledge = [
        (k.id, sorted(k.available_in_scenes)[0] if k.available_in_scenes else "") for k in package.knowledge.knowledge
    ]
    return {
        "storylets": [(s.id, s.scene_id) for s in package.storylets],
        "routes": [(s.id, s.scene_id) for s in package.storylet_routes.storylets],
        "deliveries": [(getattr(d, "fact_id", None) or getattr(d, "id", ""), d.scene_id) for d in package.deliveries],
        "pacing": [(e.id, getattr(e, "scene_id", "")) for e in package.pacing.events],
        "knowledge": knowledge,
    }


def within_scene(pairs: list[tuple[str, str]]) -> dict[str, list[str]]:
    grouped: dict[str, list[str]] = {}
    for item_id, scene in pairs:
        grouped.setdefault(scene, []).append(item_id)
    return grouped


def prompt(package: Path, scene: str, beat: str | None) -> str:
    command = [sys.executable, "-m", "bench", "prompt", "--scene", scene, "--text", "--package", str(package)]
    if beat:
        command += ["--beat", beat]
    done = subprocess.run(command, capture_output=True, text=True, timeout=300, env=os.environ)
    return done.stdout if done.returncode == 0 else f"EXIT {done.returncode}: {done.stderr.strip().splitlines()[-1:]}"


def beats(package: Path, scene: str) -> list[str]:
    done = subprocess.run(
        [sys.executable, "-m", "bench", "prompt", "--scene", scene, "--list-beats", "--package", str(package)],
        capture_output=True,
        text=True,
        timeout=300,
        env=os.environ,
    )
    return sorted(set(re.findall(rf"^\s*({re.escape(scene)}\.\d+)", done.stdout, flags=re.M)))


def main() -> int:
    old = sequences(load_legacy_story_package(LEGACY))
    new = sequences(load_story_package(DEFAULT))
    failures: list[str] = []
    for name in old:
        left, right = within_scene(old[name]), within_scene(new[name])
        for scene in sorted(set(left) | set(right)):
            if left.get(scene) != right.get(scene):
                failures.append(f"ORDER {name} scene {scene}: legacy {left.get(scene)} != compiled {right.get(scene)}")
    scenes = ["1A", "1B", "1C", "2A", "2B", "2C", "3A", "3B", "3C"]
    checked = 0
    for scene in scenes:
        for beat in [None, *beats(LEGACY, scene)]:
            checked += 1
            a, b = prompt(LEGACY, scene, beat), prompt(DEFAULT, scene, beat)
            if a != b:
                failures.append(f"PROMPT {scene} beat {beat}: legacy and compiled prompts differ")
    print(f"checked order for {len(old)} collections and {checked} prompts; failures: {len(failures)}")
    for line in failures[:40]:
        print(line)
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
