"""Layer-one shape checks for declarative scene source files."""

from __future__ import annotations

import re
from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

from .checks import layer1_check
from .diagnostics import Diagnostic
from .reader import SourceTree

_SNAKE = re.compile(r"^[a-z][a-z0-9_]*$")
_SCENE = re.compile(r"^[1-9][A-Z]$")
_STORYLET = re.compile(r"^SL-[1-9][A-Z]-[A-Z]$")
_REALIZATION = re.compile(r"^SL-[1-9][A-Z]-[A-Z]-R[1-9][0-9]*$")
_OUTLINE = re.compile(r"^[1-9][A-Z]\.[1-9][0-9]*$")
_ANCHOR = re.compile(r"^scene-[1-9][a-z][0-9]+--[a-z][a-z0-9]*(?:-[a-z0-9]+)*$")

_PHASES = frozenset(
    {"exposition", "inciting_incident", "rising_action", "crisis", "climax", "falling_action", "resolution"}
)
_SOURCE_KINDS = frozenset({"message", "observation", "broadcast", "npc", "inference"})
_AUDIENCE_KINDS = frozenset({"public", "characters", "world_only"})
_RELATIONS = frozenset({"exists", "held", "reach"})


@dataclass(frozen=True)
class _Rule:
    """Describe one key in a declarative record."""

    required: bool
    kind: str
    enum: frozenset[Any] = frozenset()


Rules = dict[str, _Rule]
Issue = Callable[[str, str, str, str], None]


def _rule(kind: str, required: bool = False, enum: frozenset[Any] = frozenset()) -> _Rule:
    return _Rule(required=required, kind=kind, enum=enum)


def _type_name(kind: str) -> str:
    return {"mapping": "mapping", "list": "list", "str": "string", "bool": "boolean", "int": "integer"}.get(kind, kind)


def _is_kind(value: object, kind: str) -> bool:
    if kind == "mapping":
        return isinstance(value, dict)
    if kind == "list":
        return isinstance(value, list)
    if kind == "str":
        return isinstance(value, str)
    if kind == "bool":
        return isinstance(value, bool)
    if kind == "int":
        return isinstance(value, int) and not isinstance(value, bool)
    return True


def _record(value: object, address: str, rules: Rules, issue: Issue) -> dict[Any, Any] | None:
    """Validate a record's keys and shallow value types, returning safe data."""

    if not isinstance(value, dict):
        issue("L1.type", address, address.rsplit(".", 1)[-1], f"expected a mapping, got {type(value).__name__}")
        return None
    for key in value:
        if key not in rules:
            issue("L1.unknown_key", address, str(key), f"unknown key {key!r}")
    for key, rule in rules.items():
        if rule.required and key not in value:
            issue("L1.missing_key", address, key, f"required key {key!r} is missing")
        if key not in value or rule.kind == "any":
            continue
        actual = value[key]
        if not _is_kind(actual, rule.kind):
            issue("L1.type", address, key, f"key {key!r} must be a {_type_name(rule.kind)}")
        elif rule.enum and actual not in rule.enum:
            allowed = ", ".join(repr(item) for item in sorted(rule.enum, key=repr))
            issue("L1.enum", address, key, f"key {key!r} must be one of {allowed}")
    return value


def _id(value: object, address: str, field: str, pattern: re.Pattern[str], issue: Issue) -> None:
    """Report an ID pattern mismatch without repeating a type diagnostic."""

    if isinstance(value, str) and not pattern.fullmatch(value):
        issue("L1.id_pattern", address, field, f"key {field!r} does not match {pattern.pattern!r}")


def _snake_map(value: object, address: str, field: str, issue: Issue) -> None:
    """Check the author-defined IDs used as mapping keys."""

    if not isinstance(value, dict):
        return
    for key in value:
        _id(key, address, field, _SNAKE, issue)


def _strings(value: object, address: str, field: str, issue: Issue, ids: bool = False) -> None:
    """Check a list of strings, optionally using the generic ID pattern."""

    if not isinstance(value, list):
        return
    for index, item in enumerate(value):
        if not isinstance(item, str):
            issue("L1.type", f"{address}[{index}]", field, f"items of {field!r} must be strings")
        elif ids:
            _id(item, f"{address}[{index}]", field, _SNAKE, issue)


def _cardinality(
    value: object, address: str, field: str, issue: Issue, minimum: int, maximum: int | None = None
) -> None:
    """Check the fixed minimum/maximum size of a list-shaped contract value."""

    if not isinstance(value, list):
        return
    too_short = len(value) < minimum
    too_long = maximum is not None and len(value) > maximum
    if too_short or too_long:
        limit = f"at least {minimum}" if maximum is None else f"between {minimum} and {maximum}"
        issue("L1.type", address, field, f"key {field!r} must contain {limit} entries")


def _condition(value: object, address: str, field: str, issue: Issue, all_true: bool = False) -> None:
    """Validate a condition map/list and the all-true restriction where applicable."""

    if isinstance(value, list):
        _strings(value, address, field, issue)
        return
    if not isinstance(value, dict):
        issue("L1.type", address, field, f"key {field!r} must be a condition map or list")
        return
    for fact, expected in value.items():
        if not isinstance(fact, str):
            issue("L1.type", address, field, "condition fact names must be strings")
        if not isinstance(expected, bool):
            issue("L1.type", address, str(fact), "condition values must be booleans")
        elif all_true and expected is False:
            issue("L1.condition_value", address, str(fact), "all facts in this condition must be true")


def _effects(value: object, address: str, field: str, issue: Issue, pacing: bool = False) -> None:
    """Validate an effects map, including pacing's prohibition on ``retract``."""

    if not isinstance(value, dict):
        return
    for fact, effect in value.items():
        if isinstance(effect, bool):
            continue
        if isinstance(effect, str):
            if effect != "retract":
                issue("L1.enum", address, str(fact), "effect values must be true, false, or 'retract'")
            elif pacing:
                issue("L1.condition_value", address, str(fact), "pacing sets cannot use 'retract'")
            continue
        issue("L1.type", address, str(fact), "effect values must be booleans or 'retract'")


def _audience(value: object, address: str, field: str, issue: Issue) -> None:
    """Validate the audience shorthand and its expanded mapping form."""

    if isinstance(value, str):
        if value != "public":
            issue("L1.enum", address, field, "audience shorthand must be 'public'")
        return
    rules = {
        "kind": _rule("str", True, _AUDIENCE_KINDS),
        "character_ids": _rule("list"),
        "player_visible": _rule("bool"),
    }
    audience = _record(value, address, rules, issue)
    if audience is None:
        return
    if audience.get("kind") == "characters" and "character_ids" not in audience:
        issue("L1.missing_key", address, "character_ids", "characters audience requires 'character_ids'")
    if "character_ids" in audience:
        _strings(audience["character_ids"], address, "character_ids", issue)


def _relevance(value: object, address: str, field: str, issue: Issue) -> None:
    """Validate the small relevance record used by claims and variants."""

    relevance = _record(
        value,
        address,
        {"entity_ids": _rule("list", True), "priority": _rule("int", True)},
        issue,
    )
    if relevance is not None:
        _strings(relevance.get("entity_ids"), address, "entity_ids", issue)


def _typed_relation(value: object, address: str, field: str, issue: Issue) -> None:
    """Validate one exit dependency relation."""

    _record(
        value,
        address,
        {
            "item": _rule("str", True),
            "relation": _rule("str", True, _RELATIONS),
            "holder": _rule("str"),
            "not": _rule("bool"),
        },
        issue,
    )


def _typed_relations(value: object, address: str, field: str, issue: Issue) -> None:
    """Validate a list of typed relations."""

    if not isinstance(value, list):
        return
    for index, item in enumerate(value):
        _typed_relation(item, f"{address}[{index}]", field, issue)


def _world_effect(value: object, address: str, field: str, issue: Issue) -> None:
    """Validate one of the four world-effect shapes from section 3."""

    if not isinstance(value, dict):
        issue("L1.type", address, field, "world effects must be mappings")
        return
    if "move" in value:
        _record(
            value,
            address,
            {
                "move": _rule("str", True),
                "parent": _rule("str", True),
                "text": _rule("str"),
                "under": _rule("bool"),
                "part_of": _rule("bool"),
            },
            issue,
        )
        return
    if "reveal" in value:
        _record(value, address, {"reveal": _rule("str", True)}, issue)
        return
    if "accompany" in value:
        _record(value, address, {"accompany": _rule("str", True), "with": _rule("str", True)}, issue)
        return
    _record(value, address, {"set_axis": _rule("str", True), "value": _rule("str", True)}, issue)


def _passage_entries(value: object, address: str, field: str, issue: Issue) -> None:
    """Validate ``say`` entries and detect unreachable guarded passages."""

    if not isinstance(value, list):
        return
    unguarded_seen = False
    for index, entry in enumerate(value):
        entry_address = f"{address}[{index}]"
        record = _record(
            entry, entry_address, {"when": _rule("any"), "text": _rule("str", True), "verbatim": _rule("bool")}, issue
        )
        if record is None:
            continue
        guarded = "when" in record
        if guarded:
            _condition(record["when"], entry_address, "when", issue)
            if unguarded_seen:
                issue("L1.passage_list", entry_address, "when", "a guarded say entry cannot follow an unguarded entry")
        else:
            unguarded_seen = True
    if value and isinstance(value[-1], dict) and "when" in value[-1]:
        issue("L1.passage_list", f"{address}[{len(value) - 1}]", "when", "the last say entry must be unguarded")


def _conditional_text_list(value: object, address: str, issue: Issue) -> None:
    """Validate a list of all-true condition/text additions."""

    if not isinstance(value, list):
        return
    rules = {"when": _rule("any", True), "text": _rule("str", True)}
    for index, entry in enumerate(value):
        entry_address = f"{address}[{index}]"
        record = _record(entry, entry_address, rules, issue)
        if record is not None and "when" in record:
            _condition(record["when"], entry_address, "when", issue, all_true=True)


def _claim(value: object, address: str, issue: Issue, *, entry: bool = False) -> None:
    """Validate a claim-shaped record used by entry, bridge, and extra claims."""

    rules = {
        "claim_id": _rule("str", True),
        "says": _rule("str", True),
        "when": _rule("any"),
        "text": _rule("str"),
        "text_when": _rule("list"),
        "speaker_text": _rule("mapping"),
        "earn_when": _rule("str"),
        "entities": _rule("list"),
        "reach": _rule("list"),
        "relevance": _rule("mapping"),
        "audience": _rule("any", True),
        "voiceable": _rule("bool"),
        "repeatable": _rule("bool"),
        "commits_subset": _rule("mapping"),
        "action_contract": _rule("mapping"),
        "extra_claims": _rule("list"),
    }
    if entry:
        rules.pop("when")
        rules.pop("text")
        rules.pop("commits_subset")
    record = _record(value, address, rules, issue)
    if record is None:
        return
    _id(record.get("claim_id"), address, "claim_id", _SNAKE, issue)
    _strings(record.get("entities"), address, "entities", issue)
    _strings(record.get("reach"), address, "reach", issue)
    if "when" in record:
        _condition(record["when"], address, "when", issue)
    if "text_when" in record:
        _conditional_text_list(record["text_when"], f"{address}.text_when", issue)
    if "speaker_text" in record and isinstance(record["speaker_text"], dict):
        for speaker, text in record["speaker_text"].items():
            if not isinstance(speaker, str) or not isinstance(text, str):
                issue(
                    "L1.type",
                    f"{address}.speaker_text",
                    "speaker_text",
                    "speaker text entries must be string-to-string",
                )
    if "relevance" in record:
        _relevance(record["relevance"], f"{address}.relevance", "relevance", issue)
    if "audience" in record:
        _audience(record["audience"], address, "audience", issue)
    if "commits_subset" in record:
        _effects(record["commits_subset"], address, "commits_subset", issue)


def _check_header(data: dict[Any, Any], address: str, issue: Issue) -> None:
    """Check scene header records and their condition-bearing additions."""

    _id(data.get("scene"), address, "scene", _SCENE, issue)
    _id(data.get("location"), address, "location", _SNAKE, issue)
    _condition_list_fields = {"companions", "participants", "items", "prop_pool"}
    for field in _condition_list_fields:
        if field in data:
            _strings(data[field], address, field, issue)
    if "setting" in data:
        _strings(data["setting"], address, "setting", issue)
    if "turns" in data:
        _record(
            data["turns"],
            f"{address}.turns",
            {"min": _rule("int", True), "nudge": _rule("int", True), "handoff": _rule("int", True)},
            issue,
        )
    if "entry_additions" in data:
        _conditional_text_list(data["entry_additions"], f"{address}.entry_additions", issue)
    if "entry_claims" in data:
        _claim_list(data["entry_claims"], f"{address}.entry_claims", issue, entry=True)


def _check_order(value: object, address: str, issue: Issue) -> None:
    """Check the optional per-scene collection order lists."""

    if not isinstance(value, dict):
        return
    allowed = {"storylets", "deliveries", "knowledge", "pacing_events"}
    for key in value:
        if key not in allowed:
            issue("L1.unknown_key", address, str(key), f"unknown order key {key!r}")
    for key in allowed:
        if key in value:
            if not isinstance(value[key], list):
                issue("L1.type", f"{address}.{key}", key, f"key {key!r} must be a list")
            else:
                _strings(value[key], address, key, issue)


def _claim_list(value: object, address: str, issue: Issue, *, entry: bool = False) -> None:
    """Check a list of claim records."""

    if not isinstance(value, list):
        return
    for index, item in enumerate(value):
        claim_id = item.get("claim_id") if isinstance(item, dict) else None
        claim_address = f"claim:{claim_id}" if isinstance(claim_id, str) else f"{address}[{index}]"
        _claim(item, claim_address, issue, entry=entry)


def _check_outline(value: object, address: str, issue: Issue) -> None:
    """Check outline beat records."""

    if not isinstance(value, list):
        return
    _cardinality(value, address, "outline", issue, 1)
    for index, item in enumerate(value):
        beat_address = f"{address}[{index}]"
        rules = {
            "id": _rule("str", True),
            "anchor": _rule("str", True),
            "title": _rule("str", True),
            "details": _rule("list", True),
            "prose": _rule("str", True),
        }
        record = _record(item, beat_address, rules, issue)
        if record is None:
            continue
        beat_id = record.get("id")
        beat_address = f"outline:{beat_id}" if isinstance(beat_id, str) else beat_address
        _id(beat_id, beat_address, "id", _OUTLINE, issue)
        _id(record.get("anchor"), beat_address, "anchor", _ANCHOR, issue)
        _strings(record.get("details"), beat_address, "details", issue)
        _cardinality(record.get("details"), beat_address, "details", issue, 3, 7)


def _check_facts(value: object, address: str, issue: Issue) -> None:
    """Check fact declarations, delivery records, and world effects."""

    if not isinstance(value, dict):
        return
    _snake_map(value, address, "fact", issue)
    for fact_id, declaration in value.items():
        record_address = f"fact:{fact_id}"
        record = _record(
            declaration,
            record_address,
            {"purpose": _rule("str", True), "on_assert": _rule("list"), "delivery": _rule("mapping")},
            issue,
        )
        if record is None:
            continue
        if "on_assert" in record and isinstance(record["on_assert"], list):
            for index, effect in enumerate(record["on_assert"]):
                _world_effect(effect, f"{record_address}.on_assert[{index}]", "on_assert", issue)
        if "delivery" in record:
            _check_delivery(record["delivery"], f"delivery:{fact_id}", issue)


def _check_delivery(value: object, address: str, issue: Issue) -> None:
    """Check a fact delivery record."""

    rules = {
        "scene": _rule("str"),
        "source_kind": _rule("str", True, _SOURCE_KINDS),
        "source_entity": _rule("str"),
        "fallback_text": _rule("str", True),
        "cue_text": _rule("str"),
        "escalation_text": _rule("str"),
        "costs": _rule("mapping"),
    }
    record = _record(value, address, rules, issue)
    if record is None:
        return
    if "costs" in record:
        _effects(record["costs"], address, "costs", issue)


def _check_placements(value: object, address: str, issue: Issue) -> None:
    """Check placement declarations, including the supported legacy form."""

    if not isinstance(value, dict):
        return
    _snake_map(value, address, "placement", issue)
    for entity, placement in value.items():
        record_address = f"placement:{entity}"
        if isinstance(placement, str):
            continue
        if not isinstance(placement, dict):
            _record(placement, record_address, {"parent": _rule("str", True)}, issue)
            continue
        if "parent" in placement:
            placement = {
                key: item
                for key, item in placement.items()
                if not (item is None and isinstance(key, str) and " " in key)
            }
            _record(
                placement,
                record_address,
                {"parent": _rule("str", True), "text": _rule("str"), "under": _rule("bool"), "part_of": _rule("bool")},
                issue,
            )
        else:
            _record(
                placement,
                record_address,
                {"placement": _rule("str", True), "while_fact_true": _rule("str"), "while_fact_false": _rule("str")},
                issue,
            )


def _check_beats(value: object, address: str, issue: Issue) -> None:
    """Check pacing events and their passage lists."""

    if not isinstance(value, list):
        return
    rules = {
        "id": _rule("str", True),
        "at_turn": _rule("int", True),
        "when": _rule("any"),
        "sets": _rule("mapping", True),
        "trailing": _rule("bool"),
        "delivers": _rule("list"),
        "verbatim": _rule("bool"),
        "say": _rule("any"),
        "exit": _rule("str"),
        "note": _rule("str"),
    }
    for index, item in enumerate(value):
        record = _record(item, f"{address}[{index}]", rules, issue)
        if record is None:
            continue
        event_id = record.get("id")
        event_address = f"beat:{event_id}" if isinstance(event_id, str) else f"{address}[{index}]"
        _id(event_id, event_address, "id", _SNAKE, issue)
        if "when" in record:
            _condition(record["when"], event_address, "when", issue)
        if "sets" in record:
            _effects(record["sets"], event_address, "sets", issue, pacing=True)
        if "delivers" in record:
            _strings(record["delivers"], event_address, "delivers", issue)
            if isinstance(record["delivers"], list):
                for index, delivery_id in enumerate(record["delivers"]):
                    if isinstance(delivery_id, str) and not delivery_id:
                        issue(
                            "L1.type",
                            f"{event_address}.delivers[{index}]",
                            "delivers",
                            "items of 'delivers' must be non-empty strings",
                        )
        if "say" in record:
            if isinstance(record["say"], list):
                _passage_entries(record["say"], f"{event_address}.say", "say", issue)
            elif not isinstance(record["say"], str):
                issue("L1.type", event_address, "say", "key 'say' must be a string or list")


def _check_reveal_defaults(record: dict[Any, Any], address: str, issue: Issue) -> None:
    """Check reveal-level defaults shared by its variants."""

    for field in ("helps_exit", "entities", "reach"):
        if field in record:
            _strings(record[field], address, field, issue)
    if "relevance" in record:
        _relevance(record["relevance"], f"{address}.relevance", "relevance", issue)
    if "audience" in record:
        _audience(record["audience"], address, "audience", issue)


def _check_variant(value: object, address: str, issue: Issue, reveal_defaults: dict[Any, Any]) -> None:
    """Check one realization variant and distinguish claimless variants."""

    rules = {
        "realization_id": _rule("str", True),
        "intent": _rule("str", True),
        "commits": _rule("mapping", True),
        "from_outline": _rule("list"),
        "helps_exit": _rule("list"),
        "outcome": _rule("mapping"),
        "claim_id": _rule("str"),
        "says": _rule("str"),
        "when": _rule("any"),
        "text": _rule("str"),
        "text_when": _rule("list"),
        "speaker_text": _rule("mapping"),
        "earn_when": _rule("str"),
        "entities": _rule("list"),
        "reach": _rule("list"),
        "relevance": _rule("mapping"),
        "boundaries": _rule("list"),
        "audience": _rule("any"),
        "voiceable": _rule("bool"),
        "repeatable": _rule("bool"),
        "commits_subset": _rule("mapping"),
        "action_contract": _rule("mapping"),
        "extra_claims": _rule("list"),
    }
    record = _record(value, address, rules, issue)
    if record is None:
        return
    _id(record.get("realization_id"), address, "realization_id", _REALIZATION, issue)
    if "from_outline" in record:
        _strings(record["from_outline"], address, "from_outline", issue)
        _cardinality(record["from_outline"], address, "from_outline", issue, 1)
    if "helps_exit" in record:
        _strings(record["helps_exit"], address, "helps_exit", issue)
    if "when" in record:
        _condition(record["when"], address, "when", issue)
    _effects(record.get("commits"), address, "commits", issue)
    if "outcome" in record:
        _check_outcome(record["outcome"], f"{address}.outcome", issue)
    _check_variant_claim(record, address, issue, reveal_defaults)


def _check_variant_claim(record: dict[Any, Any], address: str, issue: Issue, reveal_defaults: dict[Any, Any]) -> None:
    """Check claim-only variant fields and the claimless-variant restriction."""

    claim_keys = {"says", "text", "text_when", "speaker_text", "audience", "commits_subset", "extra_claims"}
    if "claim_id" not in record:
        for key in claim_keys & record.keys():
            issue("L1.claim_keys_without_claim", address, str(key), f"claim key {key!r} requires 'claim_id'")
    else:
        for key in ("entities", "reach"):
            if key in record:
                _strings(record[key], address, key, issue)
        if "relevance" in record:
            _relevance(record["relevance"], f"{address}.relevance", "relevance", issue)
        if "audience" in record:
            _audience(record["audience"], address, "audience", issue)
        for key in ("says", "audience"):
            inherited = key == "audience" and key in reveal_defaults
            if key not in record and not inherited:
                issue("L1.missing_key", address, key, f"claim variants require {key!r}")
        if "text_when" in record:
            _conditional_text_list(record["text_when"], f"{address}.text_when", issue)
        if "commits_subset" in record:
            _effects(record["commits_subset"], address, "commits_subset", issue)
        if "extra_claims" in record:
            _claim_list(record["extra_claims"], f"{address}.extra_claims", issue)
    if "boundaries" in record:
        _strings(record["boundaries"], address, "boundaries", issue)


def _check_outcome(value: object, address: str, issue: Issue) -> None:
    """Check an incident outcome attached to a realization."""

    record = _record(
        value, address, {"id": _rule("str", True), "advantages": _rule("list", True), "costs": _rule("list")}, issue
    )
    if record is None:
        return
    _id(record.get("id"), address, "id", _SNAKE, issue)
    _strings(record.get("advantages"), address, "advantages", issue)
    _strings(record.get("costs"), address, "costs", issue)


def _check_reveals(value: object, address: str, issue: Issue) -> None:
    """Check reveal, guidance, and realization records."""

    if not isinstance(value, list):
        return
    reveal_rules = {
        "id": _rule("str", True),
        "storylet_id": _rule("str", True),
        "title": _rule("str", True),
        "guidance": _rule("mapping", True),
        "from_outline": _rule("list", True),
        "commits_common": _rule("mapping"),
        "parts": _rule("mapping"),
        "notes": _rule("mapping"),
        "needs": _rule("list"),
        "audience": _rule("any"),
        "helps_exit": _rule("list"),
        "entities": _rule("list"),
        "reach": _rule("list"),
        "relevance": _rule("mapping"),
        "voiceable": _rule("bool"),
        "repeatable": _rule("bool"),
        "earn_when": _rule("str"),
        "variants": _rule("mapping", True),
    }
    for index, item in enumerate(value):
        record = _record(item, f"{address}[{index}]", reveal_rules, issue)
        if record is None:
            continue
        reveal_id = record.get("id")
        reveal_address = f"reveal:{reveal_id}" if isinstance(reveal_id, str) else f"{address}[{index}]"
        _id(reveal_id, reveal_address, "id", _SNAKE, issue)
        _id(record.get("storylet_id"), reveal_address, "storylet_id", _STORYLET, issue)
        _check_guidance(record.get("guidance"), f"{reveal_address}.guidance", issue)
        _strings(record.get("from_outline"), reveal_address, "from_outline", issue)
        _cardinality(record.get("from_outline"), reveal_address, "from_outline", issue, 1)
        if "commits_common" in record:
            _effects(record["commits_common"], reveal_address, "commits_common", issue)
        if "parts" in record:
            _snake_map(record["parts"], f"{reveal_address}.parts", "parts", issue)
            if isinstance(record["parts"], dict):
                for part, text in record["parts"].items():
                    if not isinstance(text, str):
                        issue("L1.type", f"{reveal_address}.parts", str(part), "part values must be strings")
        if "notes" in record:
            _check_notes(record["notes"], f"{reveal_address}.notes", issue)
        if "needs" in record:
            _typed_relations(record["needs"], f"{reveal_address}.needs", "needs", issue)
        _check_reveal_defaults(record, reveal_address, issue)
        variants = record.get("variants")
        if isinstance(variants, dict):
            _snake_map(variants, f"{reveal_address}.variants", "variant", issue)
            for variant_key, variant in variants.items():
                _check_variant(variant, f"variant:{reveal_id}/{variant_key}", issue, record)


def _check_guidance(value: object, address: str, issue: Issue) -> None:
    """Check reveal guidance and its pacing window."""

    record = _record(
        value,
        address,
        {
            "pressure_role": _rule("str", True),
            "window": _rule("mapping", True),
            "available_while": _rule("any"),
            "boundaries": _rule("list"),
        },
        issue,
    )
    if record is None:
        return
    window = _record(
        record.get("window"),
        f"{address}.window",
        {"earliest_turn": _rule("int", True), "target_turn": _rule("int", True), "latest_turn": _rule("int", True)},
        issue,
    )
    if window is not None:
        pass
    if "available_while" in record:
        _condition(record["available_while"], address, "available_while", issue)
    _strings(record.get("boundaries"), address, "boundaries", issue)


def _check_notes(value: object, address: str, issue: Issue) -> None:
    """Check the fixed reader-only note section names."""

    names = {
        "allowed_scene",
        "source_beats",
        "pacing_window",
        "storylet_title",
        "available_when",
        "participants",
        "dramatic_purpose",
        "possible_realizations",
        "effects",
        "completion",
        "abort",
        "protected_boundary",
        "non_coercion_note",
    }
    rules = {name: _rule("str") for name in names}
    _record(value, address, rules, issue)


def _check_bridge(value: object, address: str, issue: Issue) -> None:
    """Check canonical bridge and resolution events."""

    if not isinstance(value, list):
        return
    rules = {
        "id": _rule("str", True),
        "kind": _rule("str", False, frozenset({"bridge", "resolution"})),
        "when": _rule("any"),
        "when_any": _rule("list"),
        "at_least": _rule("int"),
        "commits": _rule("mapping", True),
        "realized_by": _rule("list"),
        "fallback_text": _rule("str"),
        "delivery_text": _rule("str"),
        "note": _rule("str"),
        "claim": _rule("mapping"),
    }
    for index, item in enumerate(value):
        record = _record(item, f"{address}[{index}]", rules, issue)
        if record is None:
            continue
        event_id = record.get("id")
        event_address = f"bridge:{event_id}" if isinstance(event_id, str) else f"{address}[{index}]"
        _id(event_id, event_address, "id", _SNAKE, issue)
        if "when" in record:
            _condition(record["when"], event_address, "when", issue)
        if "when_any" in record:
            _strings(record["when_any"], event_address, "when_any", issue)
        _effects(record.get("commits"), event_address, "commits", issue)
        if "realized_by" in record:
            _strings(record["realized_by"], event_address, "realized_by", issue)
        if "claim" in record:
            _claim(record["claim"], f"{event_address}.claim", issue)
        if record.get("kind") == "resolution" and "fallback_text" not in record:
            issue("L1.missing_key", event_address, "fallback_text", "resolution events require 'fallback_text'")


def _check_incidents(value: object, address: str, issue: Issue) -> None:
    """Check the optional single incident record and its required lists."""

    if not isinstance(value, list):
        return
    rules = {
        "id": _rule("str", True),
        "reveal": _rule("str", True),
        "outcomes": _rule("list", True),
        "recovery": _rule("str", True),
        "missed_window": _rule("str", True),
        "successor": _rule("str"),
        "observed_by": _rule("list", True),
        "completes_scene": _rule("bool"),
    }
    for index, item in enumerate(value):
        record = _record(item, f"{address}[{index}]", rules, issue)
        if record is None:
            continue
        incident_id = record.get("id")
        incident_address = f"incident:{incident_id}" if isinstance(incident_id, str) else f"{address}[{index}]"
        _id(incident_id, incident_address, "id", _SNAKE, issue)
        _strings(record.get("outcomes"), incident_address, "outcomes", issue)
        _cardinality(record.get("outcomes"), incident_address, "outcomes", issue, 2)
        _strings(record.get("observed_by"), incident_address, "observed_by", issue)


def _check_exit(value: object, address: str, issue: Issue) -> None:
    """Check the scene exit and its all-true trigger."""

    record = _record(
        value,
        address,
        {
            "id": _rule("str", True),
            "to": _rule("str", True),
            "priority": _rule("int", True),
            "when_all": _rule("any", True),
            "needs": _rule("list"),
            "bridge": _rule("str", True),
        },
        issue,
    )
    if record is None:
        return
    _id(record.get("id"), address, "id", _SNAKE, issue)
    _condition(record.get("when_all"), address, "when_all", issue, all_true=True)
    if "needs" in record:
        _typed_relations(record["needs"], f"{address}.needs", "needs", issue)


def _check_ending(value: object, address: str, issue: Issue) -> None:
    """Check the optional ending record and all-true additions."""

    record = _record(
        value,
        address,
        {
            "when": _rule("any", True),
            "text": _rule("str", True),
            "additions": _rule("list"),
            "marker": _rule("str", True),
        },
        issue,
    )
    if record is not None:
        _condition(record.get("when"), address, "when", issue, all_true=True)
        if "additions" in record:
            _conditional_text_list(record["additions"], f"{address}.additions", issue)


def _check_scene_file(file: str, data: object, issue: Issue) -> None:
    """Run all scene-file checks while isolating malformed sections."""

    root_rules: Rules = {
        "schema": _rule("int", True, frozenset({1})),
        "scene": _rule("str", True),
        "title": _rule("str"),
        "location": _rule("str", True),
        "objective": _rule("str", True),
        "freytag_phase": _rule("str", True, _PHASES),
        "situation": _rule("str"),
        "pressure": _rule("str", True),
        "turns": _rule("mapping", True),
        "scripted_opening": _rule("bool"),
        "companions": _rule("list"),
        "participants": _rule("list"),
        "items": _rule("list"),
        "setting": _rule("list"),
        "prop_pool": _rule("list"),
        "entry": _rule("str", True),
        "entry_additions": _rule("list"),
        "entry_claims": _rule("list"),
        "brief": _rule("str"),
        "outline": _rule("list", True),
        "facts": _rule("mapping"),
        "placements": _rule("mapping"),
        "beats": _rule("list"),
        "reveals": _rule("list"),
        "bridge": _rule("list"),
        "incidents": _rule("list"),
        "exit": _rule("mapping"),
        "ending": _rule("mapping"),
        "order": _rule("mapping"),
    }
    record = _record(data, f"scene:{file}", root_rules, issue)
    if record is None:
        return
    scene = record.get("scene") if isinstance(record.get("scene"), str) else "unknown"
    scene_address = f"scene:{scene}"
    _check_header(record, scene_address, issue)
    _check_outline(record.get("outline"), f"{scene_address}.outline", issue)
    _check_facts(record.get("facts"), f"{scene_address}.facts", issue)
    _check_placements(record.get("placements"), f"{scene_address}.placements", issue)
    _check_beats(record.get("beats"), f"{scene_address}.beats", issue)
    if "order" in record:
        _check_order(record["order"], f"{scene_address}.order", issue)
    _check_reveals(record.get("reveals"), f"{scene_address}.reveals", issue)
    _check_bridge(record.get("bridge"), f"{scene_address}.bridge", issue)
    _check_incidents(record.get("incidents"), f"{scene_address}.incidents", issue)
    if "exit" in record:
        _check_exit(
            record["exit"],
            f"exit:{record['exit'].get('id', 'unknown')}"
            if isinstance(record["exit"], dict)
            else f"{scene_address}.exit",
            issue,
        )
    if "ending" in record:
        _check_ending(record["ending"], "ending:story", issue)


@layer1_check
def check_scene_files(tree: SourceTree) -> list[Diagnostic]:
    """Validate every parsed ``scenes/<id>.yaml`` source file."""

    diagnostics: list[Diagnostic] = []

    def issue(name: str, address: str, field: str, message: str) -> None:
        diagnostics.append(Diagnostic(name=name, file=current_file, address=address, field=field, message=message))

    for current_file, data in sorted(tree.files.items()):
        if not re.fullmatch(r"scenes/[^/.]+\.yaml", current_file) or data is None:
            continue
        _check_scene_file(current_file, data, issue)
    return diagnostics
