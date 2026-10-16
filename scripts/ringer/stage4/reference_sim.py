"""Measure the offline Stage 4 reference resolver over recorded journeys."""

from __future__ import annotations

import argparse
import json
from collections import defaultdict
from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from bench.core import advance_state_to_scene
from storygame.runtime.candidate_matcher import _matches_all
from storygame.runtime.reference_resolution import _masked_full_names, _scene_things, resolve_references
from storygame.runtime.state import RuntimeState
from storygame.runtime.world_model import display_name, world_for
from storygame.story_package.loader import load_story_package

PACKAGE = load_story_package(Path("data/stories/continuity-initiative"))


@dataclass(frozen=True)
class AskedCommand:
    scene_id: str
    turn: Any
    command: str
    noun: str
    options: tuple[str, ...]


@dataclass(frozen=True)
class UniqueResolution:
    scene_id: str
    turn: Any
    command: str
    noun: str
    entity_id: str
    entity_name: str


@dataclass(frozen=True)
class EvidenceComparison:
    noun: str
    entity_name: str
    before: tuple[str, ...]
    after: tuple[str, ...]


@dataclass(frozen=True)
class EvidenceChange:
    scene_id: str
    turn: Any
    command: str
    comparisons: tuple[EvidenceComparison, ...]


@dataclass(frozen=True)
class FalseResolution:
    scene_id: str
    turn: Any
    command: str
    noun: str
    resolved_name: str
    other_names: tuple[str, ...]


def _read_journey(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict) or not isinstance(value.get("replicates"), list):
        raise ValueError("journey JSON must contain a replicates list")
    return value


def _scene_states(journey: dict[str, Any]) -> dict[str, RuntimeState]:
    scene_ids = {scene["scene"] for replicate in journey["replicates"] for scene in replicate.get("scenes", [])}
    states: dict[str, RuntimeState] = {}
    for scene_id in sorted(scene_ids):
        state = RuntimeState.bootstrap(PACKAGE)
        advance_state_to_scene(PACKAGE, state, scene_id)
        states[scene_id] = state
    return states


def _scene_reveals(scene_id: str) -> dict[str, tuple[tuple[str, ...], ...]]:
    return {
        item.id: item.action_evidence
        for item in PACKAGE.knowledge.knowledge
        if scene_id in item.available_in_scenes and item.action_evidence
    }


def _matching_reveals(reveals: dict[str, tuple[tuple[str, ...], ...]], command: str) -> tuple[str, ...]:
    return tuple(sorted(reveal_id for reveal_id, evidence in reveals.items() if _matches_all(evidence, command)))


def _entity_names(state: RuntimeState) -> dict[str, str]:
    world = world_for(PACKAGE, state.facts)
    return {
        entity.id: display_name(PACKAGE, state.facts, world, entity.id)
        for entity in (
            *PACKAGE.world.locations,
            *PACKAGE.world.npcs,
            *PACKAGE.world.groups,
            *PACKAGE.world.items,
        )
    }


def _measure(journey: dict[str, Any], states: dict[str, RuntimeState]) -> dict[str, Any]:
    total = 0
    unique_command_count = 0
    per_scene: defaultdict[str, dict[str, int]] = defaultdict(
        lambda: {"commands": 0, "asked": 0, "unique": 0, "untouched": 0}
    )
    asked: list[AskedCommand] = []
    unique: list[UniqueResolution] = []
    evidence_changes: list[EvidenceChange] = []
    false_resolutions: list[FalseResolution] = []

    for replicate in journey["replicates"]:
        for scene in replicate.get("scenes", []):
            scene_id = scene["scene"]
            state = states[scene_id]
            reveals = _scene_reveals(scene_id)
            names = _entity_names(state)
            for turn in scene.get("turns", []):
                if turn.get("rejected"):
                    continue
                command = turn["input"]
                total += 1
                per_scene[scene_id]["commands"] += 1
                result = resolve_references(state, command)
                if result.question is not None:
                    per_scene[scene_id]["asked"] += 1
                    asked.append(
                        AskedCommand(
                            scene_id,
                            turn.get("turn"),
                            command,
                            result.question.noun,
                            tuple(name for _entity_id, name in result.question.options),
                        )
                    )
                    continue

                if not result.resolutions:
                    per_scene[scene_id]["untouched"] += 1
                    continue

                per_scene[scene_id]["unique"] += 1
                unique_command_count += 1
                comparisons: list[EvidenceComparison] = []
                full_name_matches = _masked_full_names(state, command)[1]
                for noun, entity_id in result.resolutions:
                    entity_name = names.get(entity_id)
                    if entity_name is None:
                        world = world_for(PACKAGE, state.facts)
                        entity_name = display_name(PACKAGE, state.facts, world, entity_id)
                    resolution = UniqueResolution(scene_id, turn.get("turn"), command, noun, entity_id, entity_name)
                    unique.append(resolution)

                    other_names = tuple(
                        sorted(names.get(other_id, other_id) for other_id in full_name_matches if other_id != entity_id)
                    )
                    if other_names:
                        false_resolutions.append(
                            FalseResolution(scene_id, turn.get("turn"), command, noun, entity_name, other_names)
                        )

                    before = _matching_reveals(reveals, command)
                    after = _matching_reveals(reveals, f"{command} {entity_name}")
                    if before != after:
                        comparisons.append(EvidenceComparison(noun, entity_name, before, after))

                if comparisons:
                    evidence_changes.append(EvidenceChange(scene_id, turn.get("turn"), command, tuple(comparisons)))

    return {
        "total": total,
        "unique_command_count": unique_command_count,
        "per_scene": dict(per_scene),
        "asked": asked,
        "unique": unique,
        "evidence_changes": evidence_changes,
        "false_resolutions": false_resolutions,
    }


def _collisions(states: dict[str, RuntimeState]) -> dict[str, dict[str, tuple[tuple[str, str], ...]]]:
    result: dict[str, dict[str, tuple[tuple[str, str], ...]]] = {}
    for scene_id, state in states.items():
        names = _entity_names(state)
        by_head: defaultdict[str, set[str]] = defaultdict(set)
        for thing in _scene_things(state):
            for head in thing.heads:
                by_head[head].add(thing.entity_id)
        result[scene_id] = {
            head: tuple(sorted((entity_id, names.get(entity_id, entity_id)) for entity_id in entity_ids))
            for head, entity_ids in sorted(by_head.items())
            if len(entity_ids) >= 2
        }
    return result


def _code(value: Any) -> str:
    text = str(value).replace("`", "'")
    return f"`{text}`"


def _rate(count: int, total: int) -> str:
    return f"{(count * 100 / total) if total else 0.0:.2f}"


def _report(measurement: dict[str, Any], collisions: dict[str, dict[str, tuple[tuple[str, str], ...]]]) -> str:
    total = measurement["total"]
    per_scene = measurement["per_scene"]
    asked: list[AskedCommand] = measurement["asked"]
    unique: list[UniqueResolution] = measurement["unique"]
    unique_command_count = measurement["unique_command_count"]
    evidence_changes: list[EvidenceChange] = measurement["evidence_changes"]
    false_resolutions: list[FalseResolution] = measurement["false_resolutions"]
    lines = [
        "# Stage 4 reference resolver measurement",
        "",
        "## commands measured",
        "",
        f"- Total non-rejected commands: **{total}**.",
    ]
    for scene_id in sorted(per_scene):
        counts = per_scene[scene_id]
        lines.append(
            f"- {_code(scene_id)}: {counts['commands']} commands; "
            f"{counts['asked']} asked, {counts['unique']} unique, {counts['untouched']} untouched."
        )

    lines.extend(["", "## asked", "", f"- Count: **{len(asked)}** ({_rate(len(asked), total)} per 100 commands)."])
    if asked:
        for item in asked:
            options = ", ".join(_code(option) for option in item.options)
            lines.append(
                f"- [{item.scene_id}, turn {item.turn}] {_code(item.command)} — noun "
                f"{_code(item.noun)}; options: {options}."
            )
    else:
        lines.append("- None.")

    lines.extend(
        [
            "",
            "## unique",
            "",
            f"- Count: **{unique_command_count}** commands ({len(unique)} resolutions).",
        ]
    )
    if unique:
        for scene_id in sorted({item.scene_id for item in unique}):
            lines.append(f"### {scene_id}")
            for item in unique:
                if item.scene_id == scene_id:
                    lines.append(
                        f"- [turn {item.turn}] {_code(item.command)} — {_code(item.noun)} -> "
                        f"{_code(item.entity_name)} ({_code(item.entity_id)})."
                    )
    else:
        lines.append("- None.")

    lines.extend(
        [
            "",
            "## evidence would change",
            "",
            f"- Hypothetical changed-command count: **{len(evidence_changes)}**.",
            "- This appends the resolved display name only for measurement; the engine does not do this today.",
        ]
    )
    if evidence_changes:
        for item in evidence_changes:
            for comparison in item.comparisons:
                lines.append(
                    f"- [{item.scene_id}, turn {item.turn}] {_code(item.command)} + {_code(comparison.entity_name)} "
                    f"({_code(comparison.noun)}): {list(comparison.before)} -> {list(comparison.after)}."
                )
    else:
        lines.append("- None.")

    lines.extend(["", "## scenes with a collision", ""])
    for scene_id in sorted(collisions):
        scene_collisions = collisions[scene_id]
        if not scene_collisions:
            lines.append(f"- {_code(scene_id)}: none.")
            continue
        lines.append(f"- {_code(scene_id)}:")
        for head, entities in scene_collisions.items():
            rendered = ", ".join(f"{_code(name)} ({_code(entity_id)})" for entity_id, name in entities)
            lines.append(f"  - {_code(head)}: {rendered}.")

    if false_resolutions:
        risks = "; ".join(
            f"{item.scene_id} turn {item.turn} {_code(item.command)} resolves {_code(item.resolved_name)} "
            f"from {_code(item.noun)} while also naming {', '.join(_code(name) for name in item.other_names)}"
            for item in false_resolutions
        )
        risk_text = f"Potential false-resolution flags: {risks}."
    else:
        risk_text = "No potential false-resolution flags were visible from commands that also named another entity."
    if total:
        burden = f"{len(asked)} of {total} commands asked for clarification ({_rate(len(asked), total)} per 100)."
    else:
        burden = "No non-rejected commands were available, so clarification burden is 0.00 per 100 commands."
    evidence_recommendation = (
        "The nonzero hypothetical effect makes this worth building and testing as a real feature."
        if evidence_changes
        else "The zero hypothetical effect does not justify building this as a feature from this journey alone."
    )
    lines.extend(
        [
            "",
            "## summary",
            "",
            f"{burden} The unique-resolution false-resolution risk is limited to the following observable flags: "
            f"{risk_text} The evidence hypothetical changed {len(evidence_changes)} commands; "
            f"{evidence_recommendation} It remains hypothetical: the engine does not do this today.",
        ]
    )
    return "\n".join(lines)


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("journey", type=Path)
    args = parser.parse_args(argv)
    journey = _read_journey(args.journey)
    states = _scene_states(journey)
    measurement = _measure(journey, states)
    print(_report(measurement, _collisions(states)))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
