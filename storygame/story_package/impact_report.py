"""Render deterministic, read-only dependency reports for a package."""

from __future__ import annotations

import re
from collections.abc import Iterable
from pathlib import Path

from storygame.story_package.dependencies import Consumer, Producer, consumers, producers
from storygame.story_package.loader import load_story_package
from storygame.story_package.models import (
    FactPredicate,
    KnowledgeDefinition,
    PacingEvent,
    StoryletRoute,
    StoryPackage,
    Transition,
)

_TESTS_DEFAULT = Path(__file__).resolve().parents[2] / "tests"
_INTRO = "Generated from the current story files. Read-only; edit the sources, not this page."


def _value(value: object) -> str:
    return str(value).lower()


def _source_location(root: Path, record_id: str, source_file: str | None = None) -> str | None:
    patterns = (
        re.compile(rf"^\s*-\s+id:\s*{re.escape(record_id)}(?:\s|$)"),
        re.compile(rf"^\s*\{{?id:\s*{re.escape(record_id)}(?:\s|[,}}]|$)"),
        re.compile(rf"^\s*{re.escape(record_id)}:\s*(?:#.*)?$"),
    )
    paths = (root / source_file,) if source_file is not None else tuple(root.rglob("*"))
    for path in sorted(item for item in paths if item.is_file()):
        try:
            lines = path.read_text(encoding="utf-8").splitlines()
        except OSError:
            continue
        for line_number, line in enumerate(lines, 1):
            if any(pattern.search(line) for pattern in patterns):
                return f"{path.relative_to(root).as_posix()}:{line_number}"
    return None


def _record_suffix(root: Path, record_id: str, kind: str | None = None) -> str:
    source_files = {
        "fact": "knowledge.yaml",
        "claim": "knowledge.yaml",
        "pacing event": "pacing.yaml",
        "transition": "pacing.yaml",
        "canonical route event": "storylet-routes.yaml",
        "storylet realization": "storylet-routes.yaml",
        "connection consequence": "connections.yaml",
        "guard": "world.yaml",
    }
    location = _source_location(root, record_id, source_files.get(kind) if kind else None)
    return f" [source: {location}]" if location else ""


def _producer_line(root: Path, item: Producer) -> str:
    scene = item.scene_id if item.scene_id is not None else "none"
    return (
        f"- kind: {item.kind}; record: `{item.record_id}`; scene: `{scene}`;"
        f" text: {item.text}{_record_suffix(root, item.record_id, item.kind)}"
    )


def _consumer_line(root: Path, item: Consumer) -> str:
    kind = "guard" if item.kind == "world" and item.text.startswith("guard ") else None
    suffix = _record_suffix(root, item.record_id, kind)
    return f"- kind: {item.kind}; record: `{item.record_id}`; text: {item.text}{suffix}"


def _append_list(lines: list[str], values: Iterable[str]) -> None:
    values = tuple(values)
    lines.extend(values or ("- none",))


def _append_fact_producers(lines: list[str], root: Path, package: StoryPackage, predicate: FactPredicate) -> None:
    lines.append(f"- `{predicate.fact_id}` equals `{_value(predicate.equals)}`")
    found = producers(package, predicate.fact_id, predicate.equals)
    if found:
        lines.extend(f"  {_producer_line(root, item)[2:]}" for item in found)
    else:
        lines.append("  - none")


def _append_fact_consumers(lines: list[str], root: Path, package: StoryPackage, fact_id: str) -> None:
    found = consumers(package, fact_id)
    lines.append(f"- `{fact_id}`")
    if found:
        lines.extend(f"  {_consumer_line(root, item)[2:]}" for item in found)
    else:
        lines.append("  - none")


def _append_tests(lines: list[str], subject: str, tests_dir: Path) -> None:
    token = re.compile(rf"(?<!\w){re.escape(subject)}(?!\w)")
    matches: list[str] = []
    for path in sorted(tests_dir.glob("*.py")):
        try:
            file_lines = path.read_text(encoding="utf-8").splitlines()
        except OSError:
            continue
        file_matches = [
            f"- {tests_dir.name}/{path.name}:{line_number}"
            for line_number, line in enumerate(file_lines, 1)
            if token.search(line)
        ]
        matches.extend(file_matches[:5])
    all_count = 0
    for path in sorted(tests_dir.glob("*.py")):
        try:
            all_count += sum(1 for line in path.read_text(encoding="utf-8").splitlines() if token.search(line))
        except OSError:
            continue
    shown = matches[:20]
    lines.extend(shown or ("- none",))
    remaining = all_count - len(shown)
    if remaining > 0:
        lines.append(f"({remaining} more)")


def _subject_matches(package: StoryPackage, subject: str) -> list[tuple[str, object]]:
    matches: list[tuple[str, object]] = []
    matches.extend(("fact", fact) for fact in package.knowledge.facts if fact.id == subject)
    matches.extend(("claim", claim) for claim in package.knowledge.knowledge if claim.id == subject)
    matches.extend(("pacing event", event) for event in package.pacing.events if event.id == subject)
    matches.extend(("transition", transition) for transition in package.pacing.transitions if transition.id == subject)
    matches.extend(("storylet", storylet) for storylet in package.storylet_routes.storylets if storylet.id == subject)
    return matches


def _append_fact_report(lines: list[str], root: Path, package: StoryPackage, fact_id: str) -> None:
    lines.extend(["## Set by", ""])
    _append_list(lines, (_producer_line(root, item) for item in producers(package, fact_id)))
    lines.extend(["", "## Read by", ""])
    _append_list(lines, (_consumer_line(root, item) for item in consumers(package, fact_id)))
    lines.extend(["", "## Claims", "", "### Establishes", ""])
    establishing = [
        claim.id
        for claim in package.knowledge.knowledge
        if any(effect.fact_id == fact_id for effect in claim.establishes)
    ]
    _append_list(lines, (f"- `{claim_id}`" + _record_suffix(root, claim_id, "claim") for claim_id in establishing))
    lines.extend(["", "### Requires", ""])
    requiring = [
        claim.id
        for claim in package.knowledge.knowledge
        if any(requirement.fact_id == fact_id for requirement in claim.requires)
    ]
    _append_list(lines, (f"- `{claim_id}`" + _record_suffix(root, claim_id, "claim") for claim_id in requiring))


def _append_claim_report(lines: list[str], root: Path, package: StoryPackage, claim: KnowledgeDefinition) -> None:
    lines.extend(["## Requires", ""])
    if claim.requires:
        for requirement in claim.requires:
            _append_fact_producers(lines, root, package, requirement)
    else:
        lines.append("- none")
    lines.extend(["", "## Establishes", ""])
    if claim.establishes:
        for effect in claim.establishes:
            _append_fact_consumers(lines, root, package, effect.fact_id)
    else:
        lines.append("- none")
    lines.extend(["", "## Source", ""])
    source = claim.source
    source_parts = [f"kind: {source.kind}"]
    if source.storylet_id:
        source_parts.append(f"storylet: `{source.storylet_id}`")
    if source.realization_id:
        source_parts.append(f"realization: `{source.realization_id}`")
    if source.canonical_event_id:
        source_parts.append(f"event: `{source.canonical_event_id}`")
    lines.append("- " + "; ".join(source_parts) + _record_suffix(root, claim.id, "claim"))


def _append_record_report(
    lines: list[str], root: Path, package: StoryPackage, item: PacingEvent | Transition | StoryletRoute
) -> None:
    reads: list[tuple[str, FactPredicate]] = []
    sets: list[tuple[str, str, object]] = []
    if isinstance(item, PacingEvent):
        reads.extend(("when", predicate) for predicate in item.when)
        reads.extend(
            ("realization when", predicate) for realization in item.realizations for predicate in realization.when
        )
        sets.extend(("effect", effect.fact_id, effect.equals) for effect in item.effects)
    elif isinstance(item, Transition):
        reads.extend(("trigger", predicate) for predicate in item.triggers)
    else:
        reads.extend(("activation condition", predicate) for predicate in item.activation_conditions)
        for realization in item.realizations:
            sets.extend(
                (f"realization {realization.id}", operation.fact_id, operation.value)
                for operation in realization.operations
                if operation.op == "assert"
            )
    lines.extend(["## Reads", ""])
    if reads:
        for label, predicate in reads:
            lines.append(f"- {label}: `{predicate.fact_id}` equals `{_value(predicate.equals)}`")
            found = producers(package, predicate.fact_id, predicate.equals)
            if found:
                lines.extend(f"  {_producer_line(root, producer)[2:]}" for producer in found)
            else:
                lines.append("  - none")
    else:
        lines.append("- none")
    lines.extend(["", "## Sets", ""])
    if sets:
        for label, fact_id, value in sets:
            lines.append(f"- {label}: `{fact_id}` equals `{_value(value)}`")
            found = consumers(package, fact_id)
            if found:
                lines.extend(f"  {_consumer_line(root, consumer)[2:]}" for consumer in found)
            else:
                lines.append("  - none")
    else:
        lines.append("- none")


def render_impact_report(root: Path, subject: str, *, tests_dir: Path | None = None) -> str:
    """Render one package record's fact dependencies and textual test matches."""

    package = load_story_package(root)
    matches = _subject_matches(package, subject)
    if not matches:
        raise ValueError(f"unknown subject '{subject}'")
    kinds = [kind for kind, _ in matches]
    if len(kinds) > 1:
        raise ValueError(f"ambiguous subject '{subject}': {', '.join(kinds)}")

    lines = [f"# Impact report: {subject}", "", _INTRO, ""]
    kind, item = matches[0]
    if kind == "fact":
        _append_fact_report(lines, root, package, item.id)
    elif kind == "claim":
        _append_claim_report(lines, root, package, item)
    else:
        _append_record_report(lines, root, package, item)
    lines.extend(["", "## Tests that name it (textual id matches; not proof of coverage)", ""])
    _append_tests(lines, subject, tests_dir or _TESTS_DEFAULT)
    return "\n".join(lines) + "\n"
