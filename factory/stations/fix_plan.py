"""Build and lint deterministic plans for the supported story fixes."""

from __future__ import annotations

import argparse
import json
import re
import sys
from collections.abc import Mapping
from pathlib import Path
from typing import Any

from factory.checks.gap_delta import DEFAULT_ROOT
from factory.lessons import lessons_path, render_lessons
from storygame.story_package.dependencies import consumers, producers
from storygame.story_package.loader import load_story_package
from storygame.story_package.models import StoryPackage
from storygame.story_source.lookup import _source_tree, story_text

PLAN_VERSION = 1
EVIDENCE_LIMIT_CHARS = 24_000
_KINDS = frozenset({"add_pacing_beat", "set_text", "edit_claim_evidence", "unsupported"})
_REROUTES = frozenset({"station_code", "story_edit", "adaptive_probe"})
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


def _shape_problems(plan: object, *, legacy: bool = False) -> list[str]:
    del legacy
    if not isinstance(plan, dict):
        return ["plan.shape plan must be an object"]
    required = {"version", "ticket_id", "scene", "kind", "reason", "evidence_keys"}
    if not required.issubset(plan) or set(plan) - required - {"beat", "set_text", "claim_edit", "reroute"}:
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
    if kind == "unsupported":
        if set(plan) != required | {"reroute"}:
            return ["plan.shape unsupported plans require only reroute at the top level"]
        if plan.get("reroute") not in _REROUTES:
            return ["plan.shape unsupported reroute must be a supported reroute value"]
        return []
    expected = (
        {"beat"}
        if kind == "add_pacing_beat"
        else {"claim_edit"}
        if kind == "edit_claim_evidence"
        else {"set_text"}
        if kind == "set_text"
        else set()
    )
    if set(plan) != required | expected:
        return ["plan.shape exactly the sub-object for kind is required"]
    subplan = plan.get(next(iter(expected)))
    if not isinstance(subplan, dict):
        return ["plan.shape fix sub-object must be an object"]
    if kind == "add_pacing_beat":
        fields = {"id", "at_turn", "text", "verbatim", "trailing", "when", "sets"}
        if "test" in subplan:
            fields.add("test")
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
        if "test" in subplan and not isinstance(subplan.get("test"), str):
            return ["plan.shape beat test must be a string"]
    elif kind == "edit_claim_evidence":
        fields = {"claim_id", "group", "phrase"}
        if (
            set(subplan) != fields
            or not isinstance(subplan.get("claim_id"), str)
            or not isinstance(subplan.get("phrase"), str)
        ):
            return ["plan.shape claim_edit fields are invalid"]
        if not isinstance(subplan.get("group"), int) or isinstance(subplan.get("group"), bool):
            return ["plan.shape claim_edit group must be an integer"]
    elif kind == "set_text":
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


def _shared_effect_problems(package: StoryPackage, beat: Mapping[str, Any]) -> list[str]:
    pacing = getattr(package, "pacing", None)
    events = _value(pacing, "events", ()) or ()
    matches: list[tuple[str, int, str]] = []
    for fact_id in sorted(beat["sets"]):
        value = beat["sets"][fact_id]
        for event in events:
            event_turn = _value(event, "at_turn")
            event_id = _value(event, "id")
            if not isinstance(event_turn, int) or isinstance(event_turn, bool) or not isinstance(event_id, str):
                continue
            if any(
                _value(effect, "fact_id") == fact_id and _value(effect, "equals") == value
                for effect in (_value(event, "effects", ()) or ())
            ):
                matches.append((fact_id, event_turn, event_id))

    return [
        f"plan.shared_effect beat sets {fact_id}, which pacing event {event_id} (turn {event_turn}) also sets; "
        "set a fact no other pacing event sets"
        for fact_id, event_turn, event_id in sorted(matches, key=lambda match: (match[0], match[1], match[2]))
    ]


def _writer_preconditions(package: StoryPackage, producer: object) -> list[tuple[str, object]]:
    """Return fact predicates that must hold before a producer can write its fact."""

    kind = _value(producer, "kind")
    record_id = _value(producer, "record_id")
    if kind == "pacing event":
        return [
            (_value(predicate, "fact_id"), _value(predicate, "equals"))
            for event in _value(getattr(package, "pacing", None), "events", ()) or ()
            if _value(event, "id") == record_id
            for predicate in _value(event, "when", ()) or ()
            if isinstance(_value(predicate, "fact_id"), str)
        ]
    if kind == "claim":
        return [
            (_value(predicate, "fact_id"), _value(predicate, "equals"))
            for claim in _value(getattr(package, "knowledge", None), "knowledge", ()) or ()
            if _value(claim, "id") == record_id
            for predicate in _value(claim, "requires", ()) or ()
            if isinstance(_value(predicate, "fact_id"), str)
        ]
    if kind == "storylet realization":
        return [
            (_value(predicate, "fact_id"), _value(predicate, "equals"))
            for storylet in _value(getattr(package, "storylet_routes", None), "storylets", ()) or ()
            if any(_value(realization, "id") == record_id for realization in _value(storylet, "realizations", ()) or ())
            for predicate in _value(storylet, "activation_conditions", ()) or ()
            if isinstance(_value(predicate, "fact_id"), str)
        ]
    if kind == "canonical route event":
        return [
            (fact_id, True)
            for event in (
                *(_value(getattr(package, "storylet_routes", None), "bridge_events", ()) or ()),
                *(_value(getattr(package, "storylet_routes", None), "resolution_events", ()) or ()),
            )
            if _value(event, "id") == record_id
            for fact_id in (
                *(_value(_value(event, "activation"), "all_facts_true", ()) or ()),
                *(_value(_value(event, "activation"), "any_of", ()) or ()),
            )
            if isinstance(fact_id, str)
        ]
    if kind == "connection consequence":
        return [
            (_value(connection, "access_fact_id"), True)
            for connection in _value(package, "connections", ()) or ()
            if _value(connection, "id") == record_id and isinstance(_value(connection, "access_fact_id"), str)
        ]
    return []


def _skipped_precondition_problems(package: StoryPackage, beat: Mapping[str, Any]) -> list[str]:
    problems: list[str] = []
    for fact_id in sorted(beat["sets"]):
        value = beat["sets"][fact_id]
        for producer in sorted(producers(package, fact_id, value), key=lambda item: item.text):
            missing = [
                (predicate_fact, predicate_value)
                for predicate_fact, predicate_value in _writer_preconditions(package, producer)
                if beat["when"].get(predicate_fact) != predicate_value
            ]
            if not missing:
                continue
            missing_text = ", ".join(f"{name}={predicate_value!r}" for name, predicate_value in missing)
            problems.append(
                f"plan.skipped_preconditions beat sets {fact_id}, but {producer.text} requires {missing_text}; "
                f"pin those predicates in when before setting the fact"
            )
    return problems


def _diagnosis_causes(ticket_payload: Mapping[str, Any], evidence_keys: set[str]) -> set[str]:
    diagnosis = ticket_payload.get("diagnosis")
    rows = _value(diagnosis, "rows", ())
    if not isinstance(rows, list):
        return set()
    return {
        cause
        for row in rows
        if isinstance(row, Mapping)
        and _value(row, "key") in evidence_keys
        and isinstance(cause := _value(row, "cause"), str)
    }


def _contradicted_cause_problem(plan: Mapping[str, Any], ticket_payload: Mapping[str, Any]) -> str | None:
    diagnosis = ticket_payload.get("diagnosis")
    if not isinstance(diagnosis, Mapping):
        return None
    try:
        from .diagnose import CAUSES
    except ImportError:
        return None
    mentioned = {
        cause for cause in CAUSES if re.search(rf"(?<![A-Za-z0-9_]){re.escape(cause)}(?![A-Za-z0-9_])", plan["reason"])
    }
    if not mentioned:
        return None
    cited_causes = _diagnosis_causes(ticket_payload, set(plan["evidence_keys"]))
    if mentioned & cited_causes:
        return None
    cited_text = ", ".join(sorted(cited_causes)) or "none"
    return (
        "plan.contradicted_cause reason names "
        + ", ".join(sorted(mentioned))
        + f" but cited diagnosis rows name {cited_text}"
    )


def _match_source(package: StoryPackage, candidate_id: str) -> tuple[Mapping[str, Any], Mapping[str, Any]] | None:
    """Return a claim and its match document from the authored source tree."""

    try:
        tree = _source_tree(package)
    except (OSError, RuntimeError):
        return None
    if tree is None:
        return None
    for relative, document in sorted(tree.files.items()):
        if not relative.endswith(".match.yaml") or not isinstance(document, Mapping):
            continue
        claims = document.get("claims")
        claim = claims.get(candidate_id) if isinstance(claims, Mapping) else None
        if isinstance(claim, Mapping):
            return claim, document
    return None


def _scene_claim_ids(package: StoryPackage, scene: str) -> set[str]:
    indexes = getattr(package, "knowledge_indexes", None)
    scene_to_candidates = _value(indexes, "scene_to_candidates", {})
    candidates = scene_to_candidates.get(scene, ()) if isinstance(scene_to_candidates, Mapping) else ()
    return {candidate_id for candidate_id in candidates if isinstance(candidate_id, str)}


def _phrase_in_text(text: str, phrase: str) -> bool:
    return re.search(rf"(?<![a-z]){re.escape(phrase)}(?![a-z])", text.casefold()) is not None


def _claim_edit_problems(
    plan: Mapping[str, Any], ticket_payload: Mapping[str, Any], package: StoryPackage, packets: list[object]
) -> list[str]:
    edit = plan["claim_edit"]
    claim_id = edit["claim_id"]
    scene = plan["scene"]
    ticket_scene = _ticket_scene(ticket_payload)
    claim_scene = ticket_scene if ticket_scene is not None else scene
    indexes = getattr(package, "knowledge_indexes", None)
    definitions = _value(indexes, "by_id", {})
    candidate = definitions.get(claim_id) if isinstance(definitions, Mapping) else None
    scene_claim_ids = _scene_claim_ids(package, claim_scene)
    problems: list[str] = []
    valid_claim = candidate is not None and claim_id in scene_claim_ids
    if not valid_claim:
        problems.append("plan.claim claim_id must exist in the package and belong to the ticket scene")
    evidence_keys = set(plan["evidence_keys"])
    offered = {
        item
        for packet in packets
        if _value(packet, "key") in evidence_keys
        for item in (_value(packet, "candidates_offered", ()) or ())
        if isinstance(item, str)
    }
    if claim_id not in offered and claim_id not in scene_claim_ids:
        problems.append("plan.claim_offered claim_id must be offered by a selected failing turn")
    if not valid_claim:
        return problems

    source = _match_source(package, claim_id)
    source_claim = source[0] if source is not None else None
    if (
        isinstance(source_claim, Mapping)
        and isinstance(source_claim.get("use"), str)
        and "action_evidence" not in source_claim
    ):
        shared = source[1].get("shared")
        shared_record = shared.get(source_claim["use"]) if isinstance(shared, Mapping) else None
        if isinstance(shared_record, Mapping) and "action_evidence" in shared_record:
            problems.append("plan.claim_shared claim action_evidence comes from a shared use list")

    groups = _value(candidate, "action_evidence", ())
    group = edit["group"]
    if not isinstance(groups, (list, tuple)) or group < 0 or group >= len(groups):
        problems.append("plan.group group must identify an existing action_evidence group")
        current_group: object = ()
    else:
        current_group = groups[group]

    phrase = edit["phrase"]
    words = phrase.split()
    valid_phrase = bool(re.fullmatch(r"[a-z]+(?:'[a-z]+)?(?: [a-z]+(?:'[a-z]+)?){0,2}", phrase))
    if (
        not valid_phrase
        or not 1 <= len(words) <= 3
        or any(character.isdigit() or character == "_" for character in phrase)
    ):
        problems.append("plan.phrase phrase must be 1 to 3 lower-case words using only spaces and apostrophes")
    else:
        from .diagnose import STOPWORDS

        if all(word in STOPWORDS for word in words):
            problems.append("plan.phrase phrase must contain a non-stopword")
    if isinstance(current_group, (list, tuple)) and any(
        isinstance(item, str) and item.casefold() == phrase.casefold() for item in current_group
    ):
        problems.append("plan.phrase phrase is already in the selected action_evidence group")

    if not any(
        _value(packet, "key") in evidence_keys
        and isinstance(player_input := _value(packet, "player_input"), str)
        and _phrase_in_text(player_input, phrase)
        for packet in packets
    ):
        problems.append("plan.phrase_evidence phrase must occur in a selected failing-turn player_input")

    for other_id in sorted(scene_claim_ids):
        other = definitions.get(other_id) if isinstance(definitions, Mapping) else None
        if other is None:
            continue
        if other_id != claim_id and any(
            isinstance(item, str) and item.casefold() == phrase.casefold()
            for group_items in (_value(other, "action_evidence", ()) or ())
            for item in (group_items or ())
        ):
            problems.append("plan.phrase_owned phrase is already owned by another claim's action_evidence")
            break
        if any(
            isinstance(item, str) and item.casefold() == phrase.casefold()
            for item in (_value(other, "leak_terms", ()) or ())
        ):
            problems.append("plan.phrase_owned phrase is already used by a claim's leak_terms")
            break
    return problems


def lint_plan(plan: dict, ticket_payload: dict, package: StoryPackage) -> list[str]:
    """Return deterministic rule-labelled problems for one proposed fix plan."""

    legacy = isinstance(ticket_payload.get("plan"), dict)
    shape = _shape_problems(plan, legacy=legacy)
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
    if plan["kind"] == "unsupported":
        if not plan["reason"].lstrip().startswith("Reroute:"):
            problems.append("plan.reroute_reason reason for an unsupported plan must begin with Reroute:")
    elif not plan["reason"].lstrip().startswith("Precedent:"):
        problems.append(
            "plan.precedent reason must begin with Precedent: and name the proven technique followed, "
            "or Precedent: none with what was checked"
        )

    if contradicted := _contradicted_cause_problem(plan, ticket_payload):
        problems.append(contradicted)

    if plan["kind"] == "unsupported":
        return problems

    if plan["kind"] == "add_pacing_beat":
        beat = plan["beat"]
        if beat.get("test") is None and legacy:
            pass
        elif beat.get("test") not in {"fixed_replay", "adaptive_player"}:
            problems.append("plan.test add_pacing_beat requires test fixed_replay or adaptive_player")
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
        if not beat["sets"]:
            problems.append(
                "plan.empty_effect beat must set at least one declared story fact that no other pacing event or claim "
                "sets, or guard it with when pinned to the opposite value"
            )
        for fact_id in sorted(beat["sets"]):
            value = beat["sets"][fact_id]
            existing = producers(package, fact_id, value)
            if existing and beat["when"].get(fact_id) is not (not value):
                problems.append(
                    f"plan.redundant_effect beat sets {fact_id}, which {existing[0].text} already sets; "
                    f"guard when with {fact_id}: {not value} or set a fact nothing else sets"
                )
        problems.extend(_shared_effect_problems(package, beat))
        problems.extend(_skipped_precondition_problems(package, beat))
        if set(beat["sets"]) & _exit_fact_ids(package, plan["scene"]):
            problems.append("plan.exit_trigger beat may not set an exit trigger or dependency")
        if _text_problem(beat["text"], package):
            problems.append("plan.text beat text violates the bounded authored-text rules")
    elif plan["kind"] == "edit_claim_evidence":
        problems.extend(_claim_edit_problems(plan, ticket_payload, package, packets))
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


def _diagnosis_claim_ids(ticket_payload: Mapping[str, Any]) -> set[str]:
    identifiers: set[str] = set()
    diagnosis = ticket_payload.get("diagnosis")
    rows = _value(diagnosis, "rows", ())
    for row in rows if isinstance(rows, list) else ():
        signals = _value(row, "signals")
        claim_ids = _value(signals, "claim_ids", ())
        if isinstance(claim_ids, (list, tuple, set, frozenset)):
            identifiers.update(item for item in claim_ids if isinstance(item, str))
    return identifiers


def _candidate_ids(ticket_payload: Mapping[str, Any]) -> list[str]:
    identifiers: set[str] = set()
    turns = ticket_payload.get("failing_turns")
    for packet in turns if isinstance(turns, list) else ():
        offered = _value(packet, "candidates_offered", ())
        if isinstance(offered, (list, tuple)):
            identifiers.update(item for item in offered if isinstance(item, str))
    identifiers.update(_diagnosis_claim_ids(ticket_payload))
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
    action_evidence = _value(candidate, "action_evidence", ())
    bounded_action_evidence = [
        [item for item in group if isinstance(item, str)][:12]
        for group in (action_evidence[:8] if isinstance(action_evidence, (list, tuple)) else ())
        if isinstance(group, (list, tuple))
    ]
    source = _match_source(package, candidate_id)
    source_claim = source[0] if source is not None else None
    uses_shared = isinstance(source_claim, Mapping) and isinstance(source_claim.get("use"), str)
    return {
        "earn_when": _json_safe(_value(candidate, "earn_when")),
        "requires": _json_safe(_model_dump(_value(candidate, "requires", ()))),
        "action_evidence": bounded_action_evidence,
        "uses_shared": uses_shared,
        "text": text[:400],
        "source": _source_path(package, candidate_id),
    }


def _precedents_text(ticket_payload: Mapping[str, Any]) -> str | None:
    repository_root = Path(__file__).resolve().parents[2]
    raw_path = ticket_payload.get("precedents_path")
    if raw_path is None:
        path = repository_root / "factory" / "precedents" / "stuck_turns.md"
    elif isinstance(raw_path, (str, Path)):
        path = Path(raw_path)
        if not path.is_absolute():
            path = repository_root / path
    else:
        return None
    try:
        return path.read_text(encoding="utf-8")[:20_000]
    except (OSError, UnicodeError):
        return None


def _bound_evidence(
    packet: dict[str, object],
    limit: int = EVIDENCE_LIMIT_CHARS,
    protected_candidates: set[str] | None = None,
    protected_turn_keys: set[str] | None = None,
) -> dict[str, object]:
    def size() -> int:
        return len(json.dumps(packet, ensure_ascii=False, sort_keys=True, separators=(",", ":")))

    truncation: dict[str, object] = {}

    def record_count(key: str, kept: int, original: int) -> None:
        truncation[key] = {"kept": kept, "of": original}
        packet["truncated"] = truncation

    candidates = packet.get("candidates")
    original_candidate_count = len(candidates) if isinstance(candidates, dict) else 0
    protected_candidate_ids = protected_candidates or set()
    while size() > limit and isinstance(candidates, dict) and candidates:
        removable = [candidate_id for candidate_id in sorted(candidates) if candidate_id not in protected_candidate_ids]
        if not removable:
            break
        candidates.pop(removable[-1])
        record_count("candidates", len(candidates), original_candidate_count)

    fact_readers = packet.get("fact_readers")
    original_fact_reader_count = len(fact_readers) if isinstance(fact_readers, dict) else 0
    while size() > limit and isinstance(fact_readers, dict) and fact_readers:
        without_readers = [
            fact_id for fact_id, entry in fact_readers.items() if isinstance(entry, dict) and not entry.get("readers")
        ]
        fact_id = sorted(without_readers or fact_readers)[-1]
        fact_readers.pop(fact_id)
        record_count("fact_readers", len(fact_readers), original_fact_reader_count)

    turns = packet.get("failing_turns")
    original_turn_count = len(turns) if isinstance(turns, list) else 0
    for text_limit in (300, 150):
        if size() <= limit or not isinstance(turns, list):
            break
        shortened = False
        for turn in turns:
            if not isinstance(turn, dict):
                continue
            for field in ("narration", "previous_narration", "rejected_code", "rejected_message"):
                value = turn.get(field)
                if isinstance(value, str) and len(value) > text_limit:
                    turn[field] = value[:text_limit]
                    shortened = True
        if shortened:
            truncation["text_shortened_to"] = text_limit
            packet["truncated"] = truncation

    for key in ("beats", "exits"):
        values = packet.get(key)
        original_count = len(values) if isinstance(values, list) else 0
        while size() > limit and isinstance(values, list) and values:
            values.pop()
            record_count(key, len(values), original_count)

    if size() > limit and isinstance(turns, list):
        text_limit = 80
        shortened = False
        for turn in turns:
            if not isinstance(turn, dict):
                continue
            for field in ("narration", "previous_narration", "rejected_code", "rejected_message"):
                value = turn.get(field)
                if isinstance(value, str) and len(value) > text_limit:
                    turn[field] = value[:text_limit]
                    shortened = True
        if shortened:
            truncation["text_shortened_to"] = text_limit
            packet["truncated"] = truncation

    protected_keys = protected_turn_keys or set()
    while size() > limit and isinstance(turns, list) and len(turns) > (1 if original_turn_count else 0):
        removable_indexes = [
            index
            for index, turn in enumerate(turns)
            if not isinstance(turn, dict)
            or not isinstance(turn.get("key"), str)
            or turn.get("key") not in protected_keys
        ]
        index = removable_indexes[-1] if removable_indexes else len(turns) - 1
        turns.pop(index)
        record_count("failing_turns", len(turns), original_turn_count)
    return packet


def _diagnosis_evidence(ticket_payload: Mapping[str, Any]) -> dict[str, object] | None:
    raw_diagnosis = ticket_payload.get("diagnosis")
    if not isinstance(raw_diagnosis, Mapping):
        return None
    counts = raw_diagnosis.get("counts")
    raw_rows = raw_diagnosis.get("rows")
    if not isinstance(counts, Mapping) or not isinstance(raw_rows, list):
        return None

    rows: list[dict[str, object]] = []
    for row in raw_rows:
        if not isinstance(row, Mapping) or any(
            not isinstance(row.get(field), str) for field in ("key", "cause", "why")
        ):
            return None
        compact_row: dict[str, object] = {"key": row["key"], "cause": row["cause"], "why": row["why"][:160]}
        if "signals" in row:
            compact_row["signals"] = _json_safe(row["signals"])
        rows.append(compact_row)

    diagnosis: dict[str, object] = {"counts": _json_safe(counts), "rows": rows}

    def size() -> int:
        return len(json.dumps(diagnosis, ensure_ascii=False, separators=(",", ":")))

    try:
        size()
    except (TypeError, ValueError):
        return None
    if size() > 6000:
        for row in rows:
            row["why"] = ""
        while size() > 6000 and rows:
            rows.pop()
    return diagnosis


def _fact_readers(package: StoryPackage) -> dict[str, dict[str, list[str]]]:
    result: dict[str, dict[str, list[str]]] = {}
    for fact_id in sorted(_declared_facts(package)):
        readers = {consumer.record_id for consumer in consumers(package, fact_id)}
        writers = {producer.record_id for value in (True, False) for producer in producers(package, fact_id, value)}
        result[fact_id] = {"readers": sorted(readers), "writers": sorted(writers)}

    def size() -> int:
        return len(json.dumps(result, ensure_ascii=False, sort_keys=True, separators=(",", ":")))

    while size() > 2500 and result:
        without_readers = [fact_id for fact_id, entry in result.items() if not entry["readers"]]
        fact_id = sorted(without_readers)[-1] if without_readers else sorted(result)[-1]
        result.pop(fact_id)
    return result


def build_evidence(ticket_payload: dict, package: StoryPackage) -> dict:
    """Build the bounded, JSON-serialisable planner context for a story-data ticket."""

    scene = _ticket_scene(ticket_payload) or ""
    raw_turns = ticket_payload.get("failing_turns")
    turns: list[dict[str, object]] = []
    for packet in raw_turns if isinstance(raw_turns, list) else ():
        player_input = _value(packet, "player_input", "")
        narration = _value(packet, "narration", "")
        offered = _value(packet, "candidates_offered", ())
        turn: dict[str, object] = {
            "key": _value(packet, "key", ""),
            "player_input": player_input if isinstance(player_input, str) else "",
            "narration": narration[:500] if isinstance(narration, str) else "",
            "candidates_offered": [item for item in offered if isinstance(item, str)]
            if isinstance(offered, (list, tuple))
            else [],
            "matched_candidate": _value(packet, "matched_candidate"),
            "outcome": _json_safe(_value(packet, "outcome")),
        }
        for field, limit in (("previous_narration", 600), ("rejected_code", 600), ("rejected_message", 600)):
            value = _value(packet, field)
            if isinstance(value, str):
                turn[field] = value[:limit]
        turns.append(turn)

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
    diagnosis = _diagnosis_evidence(ticket_payload)
    diagnosis_rows = _value(ticket_payload.get("diagnosis"), "rows", ())
    protected_turn_keys: set[str] = set()
    if isinstance(diagnosis_rows, list):
        protected_turn_keys = {
            row["key"] for row in diagnosis_rows if isinstance(row, Mapping) and isinstance(row.get("key"), str)
        }
    evidence: dict[str, object] = {
        "scene": scene,
        "failing_turns": turns,
        "diagnosis": diagnosis,
        "candidates": {
            candidate_id: detail
            for candidate_id in _candidate_ids(ticket_payload)
            if (detail := _candidate_evidence(package, candidate_id)) is not None
        },
        "scene_window": {"min": minimum, "nudge": nudge, "handoff": handoff},
        "beats": beats,
        "exits": exits,
        "fact_readers": _fact_readers(package),
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
            {
                "kind": "edit_claim_evidence",
                "description": "Add one player-typed phrase to one existing claim action_evidence group.",
            },
            {
                "kind": "unsupported",
                "description": (
                    "Reroute when the evidence's real cause is not expressible by the three story fixes: "
                    "station_code for harness, diagnosis, or provider defects; story_edit for a bounded story "
                    "restructure; adaptive_probe when the hypothesis needs a responding player."
                ),
            },
        ],
    }
    evidence = _bound_evidence(
        evidence,
        protected_candidates=_diagnosis_claim_ids(ticket_payload),
        protected_turn_keys=protected_turn_keys,
    )
    evidence["precedents"] = _precedents_text(ticket_payload)
    fun_lessons_path = lessons_path(ticket_payload)
    try:
        evidence["fun_lessons"] = None if fun_lessons_path is None else (render_lessons(fun_lessons_path) or None)
    except Exception:
        evidence["fun_lessons"] = None
    return evidence


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
