"""Replay recoverable Scene 3A commands against HEAD and the worktree package."""

from __future__ import annotations

import json
import re
import subprocess
import sys
import tempfile
from collections.abc import Iterator
from pathlib import Path
from typing import Any

REPO = Path(__file__).resolve().parents[3]
PACKAGE_RELATIVE = Path("data/stories/continuity-initiative")
PACKAGE_FILES = (
    "handoffs.yaml",
    "knowledge.yaml",
    "pacing.yaml",
    "plot.md",
    "storylet-routes.yaml",
    "storylets.md",
    "world.yaml",
)


def _json_values(path: Path) -> Iterator[Any]:
    text = path.read_text(encoding="utf-8")
    for match in re.finditer(r"```(?:json)?\s*\n(.*?)```", text, re.DOTALL | re.IGNORECASE):
        try:
            yield json.loads(match.group(1))
        except json.JSONDecodeError:
            continue


def _scene_runs(value: Any) -> Iterator[tuple[str, int, list[dict[str, Any]]]]:
    if isinstance(value, dict):
        if value.get("scene") == "3A" and isinstance(value.get("turns"), list):
            replicate = int(value.get("replicate", 0))
            turns = [turn for turn in value["turns"] if isinstance(turn, dict) and "input" in turn]
            yield ("record", replicate, turns)
        for child in value.values():
            yield from _scene_runs(child)
    elif isinstance(value, list):
        for child in value:
            yield from _scene_runs(child)


def _corpus_paths() -> Iterator[Path]:
    for root in (REPO / "artifacts", REPO / "bench"):
        if root.exists():
            yield from root.rglob("*.md")
            yield from root.rglob("*.json")
    external = Path.home() / "dev/ringer-work/affordance-live-all"
    if external.exists():
        yield from external.glob("*.md")


def _recorded_runs() -> Iterator[tuple[Path, int, list[dict[str, Any]]]]:
    seen: set[tuple[Path, int, tuple[str, ...]]] = set()
    for path in _corpus_paths():
        for _, replicate, turns in _scene_runs_from_path(path):
            key = (path, replicate, tuple(str(turn["input"]) for turn in turns))
            if key not in seen:
                seen.add(key)
                yield path, replicate, turns


def _scene_runs_from_path(path: Path) -> Iterator[tuple[str, int, list[dict[str, Any]]]]:
    for value in _json_values(path):
        yield from _scene_runs(value)


def _old_package(root: Path) -> Path:
    package = root / PACKAGE_RELATIVE
    package.mkdir(parents=True)
    for filename in PACKAGE_FILES:
        source = f"{PACKAGE_RELATIVE.as_posix()}/{filename}"
        content = subprocess.check_output(["git", "show", f"HEAD:{source}"], cwd=REPO)
        (package / filename).write_bytes(content)
    return package


def _state(package: Any) -> Any:
    from storygame.runtime.state import RuntimeState

    state = RuntimeState(package=package, current_scene_id="3A", phase="crisis")
    state._assert_scene_entry_fact("3A")
    return state


def _result(engine: Any, command: str) -> str | None:
    from storygame.runtime.candidate_matcher import ActionEvidenceCandidate, uniquely_matched_candidate

    candidates = engine.projector.project(engine.state, "player", command).candidates
    evidence = tuple(
        ActionEvidenceCandidate(id=candidate.id, required_groups=candidate.action_evidence) for candidate in candidates
    )
    matched = uniquely_matched_candidate(command, evidence)
    return matched.id if matched is not None else None


def _apply_recorded_reveals(package: Any, state: Any, turn: dict[str, Any]) -> None:
    from storygame.runtime.facts import Fact
    from storygame.runtime.world_model import world_for

    for knowledge_id in turn.get("grounding_ids", ()):
        knowledge = package.knowledge_indexes.by_id.get(knowledge_id)
        if knowledge is None:
            continue
        for effect in knowledge.establishes:
            if effect.op == "assert" and effect.value is True:
                state.facts.assert_fact(Fact(predicate=effect.fact_id, subject="story", value="true"))
        if knowledge.source.storylet_id:
            state.fired_event_ids.add(knowledge.source.storylet_id)
    world_for(package, state.facts)


def _replay(package: Any, turns: list[dict[str, Any]]) -> list[tuple[int, str, str | None]]:
    from storygame.runtime.engine import RuntimeEngine

    state = _state(package)
    engine = RuntimeEngine(state, lambda _command: {"segments": []})
    results = []
    for turn in turns:
        turn_number = int(turn.get("turn", len(results) + 1))
        state.turn_index = turn_number
        engine._activate_pacing()  # noqa: SLF001 - replay the real authored activation path.
        command = str(turn["input"])
        results.append((turn_number, command, _result(engine, command)))
        _apply_recorded_reveals(package, state, turn)
    return results


def main() -> int:
    sys.path.insert(0, str(REPO))
    from storygame.story_package.loader import load_story_package

    current_package = load_story_package(REPO / PACKAGE_RELATIVE)
    runs = list(_recorded_runs())
    if not runs:
        print("No readable Scene 3A command corpus was found.")
        return 0

    with tempfile.TemporaryDirectory(prefix="3a-records-corpus-") as temporary:
        old_package = load_story_package(_old_package(Path(temporary)))
        changes: list[tuple[Path, int, int, str, str | None, str | None]] = []
        for path, replicate, turns in runs:
            before = _replay(old_package, turns)
            after = _replay(current_package, turns)
            for old, new in zip(before, after, strict=True):
                if old[2] != new[2]:
                    changes.append((path, replicate, new[0], new[1], old[2], new[2]))

    print("Corpus commands whose matcher result changed:")
    if not changes:
        print("  none")
    for path, replicate, turn, command, before, after in changes:
        print(f"  {path}:{replicate}:turn {turn}: {command!r}: {before!r} -> {after!r}")
    print(f"Changed commands: {len(changes)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
