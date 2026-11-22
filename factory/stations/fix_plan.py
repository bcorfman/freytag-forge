"""Build and lint deterministic plans for the two supported story fixes."""

from __future__ import annotations

import argparse
import json
import re
import sys
from collections.abc import Mapping
from pathlib import Path
from typing import Any

from factory.checks.gap_delta import DEFAULT_ROOT
from storygame.story_package.loader import load_story_package
from storygame.story_package.models import StoryPackage
from storygame.story_source.lookup import _source_tree, story_text

PLAN_VERSION = 1
_KINDS = frozenset({"add_pacing_beat", "set_text"})
_BEAT_ID = re.compile(r"^[a-z][a-z0-9_]*_(?P<scene>[1-9][a-z])$")
_TODO = re.compile(r"\bTODO\b", re.IGNORECASE)
_ID_CHAR = r"A-Za-z0-9_"


def _value(item: object, name: str, default: object = None) -> object:
    if isinstance(item, Mapping):
        return item.get(name, default)
    return getattr(item, name, default)


def _scene_ids(package: StoryPackage) -> set[str]:
    return {
        scene_id
        for scene in getattr(package, "scenes", ())
        if isinstance(scene_id := _value(_value(scene, "metadata"), "scene_id"), str)
    }


def _ticket_scene(ticket_payload: Mapping[str, Any]) -> str | None:
    if "scene" in ticket_payload:
        scene = ticket_payload.get("scene")
        return scene if isinstance(scene, str) else None
    turns = ticket_payload.get("failing_turns")
    if isinstance(turns, list):
        for packet in turns:
            scene = _value(packet, "scene")
            if isinstance(scene, str):
                return scene
    return None


def _declared_facts(package: StoryPackage) -> set[str]:
    world = getattr(package, "world", None)
    facts = _value(world, "facts")
    if isinstance(facts, (tuple, list, set, frozenset)):
        return {fact_id for fact_id in facts if isinstance(fact_id, str)}
    catalog = getattr(package, "knowledge", None)
    definitions = _value(catalog, "facts", ())
    return {fact_id for fact in definitions if isinstance(fact_id := _value(fact, "id"), str)}


def _window(package: StoryPackage, scene: str) -> object | None:
    pacing = getattr(package, "pacing", None)
    for candidate in _value(pacing, "scenes", ()) or ():
        if _value(candidate, "scene_id") == scene:
            return candidate
    return None


def _window_turn(window: object | None, names: tuple[str, ...], fallback: int = 0) -> int:
    for name in names:
        value = _value(window, name)
        if isinstance(value, int) and not isinstance(value, bool):
            return value
    return fallback


def _window_numbers(package: StoryPackage, scene: str) -> tuple[int, int, int]:
    window = _window(package, scene)
    minimum = _window_turn(window, ("min_turns", "min"))
    nudge = _window_turn(window, ("nudge_after_turns", "nudge"))
    handoff = _window_turn(window, ("handoff_after_turns", "handoff"))
    if not handoff:
        handoff = _window_turn(window, ("latest_turn", "latest"))
    return minimum, nudge, handoff


def _model_dump(value: object) -> object:
    dumper = getattr(value, "model_dump", None)
    if callable(dumper):
        return dumper(mode="json")
    if isinstance(value, Mapping):
        return {str(key): _model_dump(item) for key, item in value.items()}
    if isinstance(value, (tuple, list)):
        return [_model_dump(item) for item in value]
    return value


def _predicate_map(predicates: object) -> dict[str, object]:
    result: dict[str, object] = {}
    for predicate in predicates or ():
        fact_id = _value(predicate, "fact_id")
        if isinstance(fact_id, str):
            result[fact_id] = _value(predicate, "equals")
    return {key: result[key] for key in sorted(result)}


def _json_safe(value: object) -> object:
    if value is None or isinstance(value, (str, int, float, bool)):
        return value
    dumper = getattr(value, "model_dump", None)
    if callable(dumper):
        return _json_safe(dumper(mode="json"))
    if isinstance(value, Mapping):
        return {str(key): _json_safe(item) for key, item in value.items()}
    if isinstance(value, (tuple, list)):
        return [_json_safe(item) for item in value]
    return str(value)


def _whole_word(text: str, identifier: str) -> bool:
    pattern = rf"(?<![{_ID_CHAR}]){re.escape(identifier)}(?![{_ID_CHAR}])"
    return re.search(pattern, text) is not None


def _text_ids(package: StoryPackage) -> set[str]:
    identifiers = _declared_facts(package)
    indexes = getattr(package, "knowledge_indexes", None)
    by_id = _value(indexes, "by_id", {})
    if isinstance(by_id, Mapping):
        identifiers.update(str(identifier) for identifier in by_id)
    for collection in (
        getattr(package, "storylets", ()),
        _value(getattr(package, "storylet_routes", None), "storylets", ()),
    ):
        identifiers.update(
            str(identifier) for item in collection or () if isinstance(identifier := _value(item, "id"), str)
        )
    return identifiers


def _text_problem(text: object, package: StoryPackage) -> bool:
    if not isinstance(text, str) or not text.strip() or not 20 <= len(text) <= 600:
        return True
    if "{" in text or "}" in text or _TODO.search(text):
        return True
    return any(
        _whole_word(text, identifier) for identifier in sorted(_text_ids(package), key=lambda item: (-len(item), item))
    )


def _shape_problems(plan: object) -> list[str]:
    if not isinstance(plan, dict):
        return ["plan.shape plan must be an object"]
    required = {"version", "ticket_id", "scene", "kind", "reason", "evidence_keys"}
    if not required.issubset(plan) or set(plan) - required - {"beat", "set_text"}:
        return ["plan.shape required keys or extra top-level keys are invalid"]
    if (
        plan.get("version") != PLAN_VERSION
        or not isinstance(plan.get("version"), int)
        or isinstance(plan.get("version"), bool)
    ):
        return ["plan.shape version must be 1"]
    if any(not isinstance(plan.get(key), str) for key in ("ticket_id", "scene", "kind", "reason")):
        return ["plan.shape scalar fields have invalid types"]
    evidence = plan.get("evidence_keys")
    if not isinstance(evidence, list) or any(not isinstance(item, str) for item in evidence):
        return ["plan.shape evidence_keys must be a list of strings"]
    kind = plan.get("kind")
    if kind not in _KINDS:
        return []
    expected = {"beat"} if kind == "add_pacing_beat" else {"set_text"}
    if set(plan) != required | expected:
        return ["plan.shape exactly the sub-object for kind is required"]
    subplan = plan.get(next(iter(expected)))
    if not isinstance(subplan, dict):
        return ["plan.shape fix sub-object must be an object"]
    if kind == "add_pacing_beat":
        fields = {"id", "at_turn", "text", "verbatim", "trailing", "when", "sets"}
        if set(subplan) != fields:
            return ["plan.shape beat fields are invalid"]
        if (
            not isinstance(subplan.get("id"), str)
            or not isinstance(subplan.get("at_turn"), int)
            or isinstance(subplan.get("at_turn"), bool)
        ):
            return ["plan.shape beat scalar fields have invalid types"]
        if not isinstance(subplan.get("text"), str) or any(
            not isinstance(subplan.get(key), bool) for key in ("verbatim", "trailing")
        ):
            return ["plan.shape beat text and flags have invalid types"]
        for name in ("when", "sets"):
            mapping = subplan.get(name)
            if not isinstance(mapping, dict) or any(
                not isinstance(key, str) or not isinstance(value, bool) for key, value in mapping.items()
            ):
                return [f"plan.shape beat {name} must map strings to booleans"]
    else:
        if set(subplan) != {"address", "text"} or any(
            not isinstance(subplan.get(key), str) for key in ("address", "text")
        ):
            return ["plan.shape set_text fields have invalid types"]
    return []


def _exit_fact_ids(package: StoryPackage, scene: str) -> set[str]:
    transitions = _value(getattr(package, "pacing", None), "transitions", ())
    result: set[str] = set()
    for transition in transitions or ():
        if _value(transition, "source_scene_id") != scene:
            continue
        result.update(
            fact_id
            for predicate in (_value(transition, "triggers", ()) or ())
            if isinstance(fact_id := _value(predicate, "fact_id"), str)
        )
        result.update(
            dependency
            for dependency in (_value(transition, "required_dependencies", ()) or ())
            if isinstance(dependency, str)
        )
    return result


def lint_plan(plan: dict, ticket_payload: dict, package: StoryPackage) -> list[str]:
    """Return deterministic rule-labelled problems for one proposed fix plan."""

    shape = _shape_problems(plan)
    if shape:
        return shape
    if plan["kind"] not in _KINDS:
        return ["plan.kind kind is not supported"]

    problems: list[str] = []
    ticket_scene = _ticket_scene(ticket_payload)
    if plan["scene"] not in _scene_ids(package) or ticket_scene is None or plan["scene"] != ticket_scene:
        problems.append("plan.scene scene must exist and equal the ticket scene")

    packets = ticket_payload.get("failing_turns")
    packets = packets if isinstance(packets, list) else []
    packet_keys = {_value(packet, "key") for packet in packets}
    evidence = plan["evidence_keys"]
    if not evidence or any(key not in packet_keys for key in evidence):
        problems.append("plan.evidence evidence_keys must name failing-turn packets")

    if not plan["reason"].strip() or len(plan["reason"]) > 400:
        problems.append("plan.reason reason must be non-blank and at most 400 characters")

    if plan["kind"] == "add_pacing_beat":
        beat = plan["beat"]
        expected_suffix = plan["scene"].lower()
        if not _BEAT_ID.fullmatch(beat["id"]) or not beat["id"].endswith(f"_{expected_suffix}"):
            problems.append("plan.beat_id beat id must use the scene suffix and safe identifier form")
        elif any(
            _value(event, "id") == beat["id"] for event in _value(getattr(package, "pacing", None), "events", ()) or ()
        ):
            problems.append("plan.beat_id beat id already exists")

        _, _, handoff = _window_numbers(package, plan["scene"])
        if plan["beat"]["at_turn"] < 1 or not handoff or plan["beat"]["at_turn"] >= handoff:
            problems.append("plan.beat_turn at_turn must be before the scene handoff")

        facts = _declared_facts(package)
        if (set(beat["when"]) | set(beat["sets"])) - facts:
            problems.append("plan.facts beat predicates must name declared story facts")
        if set(beat["sets"]) & _exit_fact_ids(package, plan["scene"]):
            problems.append("plan.exit_trigger beat may not set an exit trigger or dependency")
        if _text_problem(beat["text"], package):
            problems.append("plan.text beat text violates the bounded authored-text rules")
    else:
        address = plan["set_text"]["address"]
        current: str | None = None
        if not address.endswith(".text"):
            problems.append("plan.address address must resolve to a .text field")
        else:
            try:
                current = story_text(address, package=package)
            except (KeyError, TypeError, ValueError):
                problems.append("plan.address address does not resolve")
        if _text_problem(plan["set_text"]["text"], package):
            problems.append("plan.text replacement text violates the bounded authored-text rules")
        if current is not None and current == plan["set_text"]["text"]:
            problems.append("plan.unchanged replacement text must differ from the current text")
    return problems


def _source_path(package: StoryPackage, candidate_id: str) -> str | None:
    try:
        tree = _source_tree(package)
    except (OSError, RuntimeError):
        return None
    if tree is None:
        return None

    def contains_claim(value: object) -> bool:
        if isinstance(value, Mapping):
            return value.get("claim_id") == candidate_id or any(contains_claim(item) for item in value.values())
        if isinstance(value, (list, tuple)):
            return any(contains_claim(item) for item in value)
        return False

    for relative, document in sorted(tree.files.items()):
        if contains_claim(document):
            return str(tree.root / relative)
    return None


def _candidate_ids(ticket_payload: Mapping[str, Any]) -> list[str]:
    identifiers: set[str] = set()
    turns = ticket_payload.get("failing_turns")
    for packet in turns if isinstance(turns, list) else ():
        offered = _value(packet, "candidates_offered", ())
        if isinstance(offered, (list, tuple)):
            identifiers.update(item for item in offered if isinstance(item, str))
    return sorted(identifiers)


def _candidate_evidence(package: StoryPackage, candidate_id: str) -> dict[str, object] | None:
    indexes = getattr(package, "knowledge_indexes", None)
    definitions = _value(indexes, "by_id", {})
    candidate = definitions.get(candidate_id) if isinstance(definitions, Mapping) else None
    if candidate is None:
        return None
    text = _value(candidate, "delivery_text", "")
    if not isinstance(text, str):
        text = ""
    return {
        "earn_when": _json_safe(_value(candidate, "earn_when")),
        "requires": _json_safe(_model_dump(_value(candidate, "requires", ()))),
        "text": text[:400],
        "source": _source_path(package, candidate_id),
    }


def _bound_evidence(packet: dict[str, object], limit: int = 12_000) -> dict[str, object]:
    def size() -> int:
        return len(json.dumps(packet, ensure_ascii=False, sort_keys=True, separators=(",", ":")))

    for key in ("failing_turns", "beats", "exits"):
        values = packet[key]
        while size() > limit and isinstance(values, list) and values:
            values.pop()
    candidates = packet["candidates"]
    while size() > limit and isinstance(candidates, dict) and candidates:
        candidates.pop(sorted(candidates)[-1])
    return packet


def build_evidence(ticket_payload: dict, package: StoryPackage) -> dict:
    """Build the bounded, JSON-serialisable planner context for a story-data ticket."""

    scene = _ticket_scene(ticket_payload) or ""
    raw_turns = ticket_payload.get("failing_turns")
    turns: list[dict[str, object]] = []
    for packet in raw_turns if isinstance(raw_turns, list) else ():
        player_input = _value(packet, "player_input", "")
        narration = _value(packet, "narration", "")
        offered = _value(packet, "candidates_offered", ())
        turns.append(
            {
                "key": _value(packet, "key", ""),
                "player_input": player_input if isinstance(player_input, str) else "",
                "narration": narration[:500] if isinstance(narration, str) else "",
                "candidates_offered": [item for item in offered if isinstance(item, str)]
                if isinstance(offered, (list, tuple))
                else [],
                "matched_candidate": _value(packet, "matched_candidate"),
                "outcome": _json_safe(_value(packet, "outcome")),
            }
        )

    events = [
        event
        for event in _value(getattr(package, "pacing", None), "events", ()) or ()
        if _value(event, "scene_id") == scene
    ]
    beats = [
        {
            "id": _value(event, "id"),
            "at_turn": _value(event, "at_turn"),
            "when": _predicate_map(_value(event, "when", ())),
            "sets": _predicate_map(_value(event, "effects", ())),
            "trailing": _value(event, "trailing", False),
        }
        for event in sorted(events, key=lambda item: (_value(item, "at_turn", 0), _value(item, "id", "")))
    ]
    transitions = [
        transition
        for transition in _value(getattr(package, "pacing", None), "transitions", ()) or ()
        if _value(transition, "source_scene_id") == scene
    ]
    exits = [
        {
            "id": _value(transition, "id"),
            "triggers": _json_safe(_value(transition, "triggers", ())),
            "to": _value(transition, "target_scene_id"),
        }
        for transition in sorted(transitions, key=lambda item: _value(item, "id", ""))
    ]
    minimum, nudge, handoff = _window_numbers(package, scene)
    evidence: dict[str, object] = {
        "scene": scene,
        "failing_turns": turns,
        "candidates": {
            candidate_id: detail
            for candidate_id in _candidate_ids(ticket_payload)
            if (detail := _candidate_evidence(package, candidate_id)) is not None
        },
        "scene_window": {"min": minimum, "nudge": nudge, "handoff": handoff},
        "beats": beats,
        "exits": exits,
        "fix_menu": [
            {
                "kind": "add_pacing_beat",
                "description": (
                    "Add a player-safe authored pacing beat before handoff; precedents: "
                    "reyes_rams_drawer_" + "1" + "a and supervisor_impatience_" + "2" + "a."
                ),
            },
            {
                "kind": "set_text",
                "description": "Change a reveal handoff sentence through the story CLI at claim:<id>.text.",
            },
        ],
    }
    return _bound_evidence(evidence)


def _read_json(path: Path) -> object:
    with path.open(encoding="utf-8") as handle:
        return json.load(handle)


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="command", required=True)
    evidence = subparsers.add_parser("evidence")
    evidence.add_argument("ticket", type=Path)
    evidence.add_argument("--story", type=Path, default=DEFAULT_ROOT)
    lint = subparsers.add_parser("lint")
    lint.add_argument("plan", type=Path)
    lint.add_argument("--ticket", type=Path, required=True)
    lint.add_argument("--story", type=Path, default=DEFAULT_ROOT)
    return parser


def main(argv: list[str] | None = None) -> int:
    """Run the evidence or plan-lint command."""

    options = _parser().parse_args(argv)
    try:
        if options.command == "evidence":
            ticket = _read_json(options.ticket)
            if not isinstance(ticket, dict):
                raise ValueError("ticket must be a JSON object")
            package = load_story_package(options.story)
            print(json.dumps(build_evidence(ticket, package), ensure_ascii=False, sort_keys=True))
            return 0
        plan = _read_json(options.plan)
        ticket = _read_json(options.ticket)
        if not isinstance(plan, dict) or not isinstance(ticket, dict):
            raise ValueError("plan and ticket must be JSON objects")
        package = load_story_package(options.story)
        problems = lint_plan(plan, ticket, package)
    except (OSError, ValueError, TypeError, json.JSONDecodeError) as error:
        print(str(error), file=sys.stderr)
        return 2
    for problem in problems:
        print(problem)
    return 1 if problems else 0


if __name__ == "__main__":
    raise SystemExit(main())
