"""Layer-one shape checks for non-scene story-source files."""

from __future__ import annotations

import re
from collections.abc import Iterable

from .checks import layer1_check
from .diagnostics import Diagnostic
from .reader import SourceTree

_ID = re.compile(r"^[a-z][a-z0-9_]*$")
_SCENE_ID = re.compile(r"^[1-9][A-Z]$")
_MATCH_FILE = re.compile(r"^scenes/([^/]+)\.match\.yaml$")
_LOCK_FILE = re.compile(r"^scenes/([^/]+)\.match\.lock\.yaml$")
_PLURAL = re.compile(r"\((?:s|es)\)")

_OWNERSHIP_KEYS = {"schema", "catalog", "scenes"}
_STORY_KEYS = {
    "schema",
    "story",
    "title",
    "genre",
    "protagonist",
    "budget_seconds",
    "scenes",
    "principal_characters",
    "acts",
    "front_matter",
    "retired_ids",
}
_CATALOG_KEYS = {
    "schema",
    "places",
    "characters",
    "groups",
    "items",
    "kinds",
    "props",
    "connections",
    "protected_knowledge",
    "disclosure_guards",
    "unplaced_facts",
}
_MATCH_KEYS = {"schema", "scene", "lexicon", "plural_twins", "shared", "claims", "deliveries"}
_LOCK_KEYS = {"schema", "scene", "generated_by", "claims", "deliveries"}
_LEXICON_KEYS = {"schema", "entities", "concepts", "verb_classes"}

_ENTITY_KEYS = {
    "name",
    "aliases",
    "scoped_aliases",
    "disclosure",
    "fallback_ids",
    "unnamed_label",
    "named_by",
    "narrator_bio",
}
_PLACE_KEYS = _ENTITY_KEYS | {"parent", "owner", "description"}
_CHARACTER_KEYS = _ENTITY_KEYS | {"bio", "axes", "unavailable"}
_ITEM_KEYS = _ENTITY_KEYS | {
    "fixed",
    "kind",
    "openable",
    "open",
    "hidden",
    "contents",
    "view",
    "contents_complete",
    "owner",
    "enterable",
    "enter_pole",
    "unavailable",
    "seat_for",
    "use_seated",
    "right_text",
    "enter_text",
    "leave_text",
    "take_text",
    "notice_text",
    "axes",
    "facets",
    "authored_facets",
}
_KIND_KEYS = {"is", "enterable", "fixed"}
_PROP_KEYS = {"name", "parents", "fixed", "facets"}
_CONNECTION_KEYS = {"from", "to", "via", "access_fact", "consequences", "arrival"}
_GUARD_KEYS = {"terms", "audience", "unlock_fact", "unlock_claim"}
_FACT_KEYS = {
    "purpose",
    "on_assert",
    "delivery",
}
_DELIVERY_KEYS = {
    "scene",
    "source_kind",
    "source_entity",
    "fallback_text",
    "cue_text",
    "escalation_text",
    "costs",
}
_MATCH_FIELDS = {"aliases", "action_evidence", "must_convey", "leak_terms"}
_DERIVED_KEYS = {"first", "from", "add", "drop"}


def _diagnostic(name: str, file: str, address: str, field: str, message: str) -> Diagnostic:
    """Build a source diagnostic with a stable, non-empty location."""

    return Diagnostic(name, file, address or "root", field or "root", message)


def _path(address: str, part: object) -> str:
    """Append a mapping key or sequence index to a dotted source path."""

    if isinstance(part, int):
        return f"{address}[{part}]"
    return f"{address}.{part}" if address else str(part)


def _matches(value: object, expected: type | tuple[type, ...]) -> bool:
    """Match types while keeping booleans distinct from integers."""

    expected_types = expected if isinstance(expected, tuple) else (expected,)
    return any(
        type(value) is expected_type if expected_type in (bool, int) else isinstance(value, expected_type)
        for expected_type in expected_types
    )


def _type_check(
    diagnostics: list[Diagnostic], file: str, address: str, field: str, value: object, expected: type | tuple[type, ...]
) -> bool:
    """Report one type error and return whether a value has the expected type."""

    if _matches(value, expected):
        return True
    expected_name = ", ".join(item.__name__ for item in (expected if isinstance(expected, tuple) else (expected,)))
    diagnostics.append(_diagnostic("L1.type", file, address, field, f"{field} must be {expected_name}"))
    return False


def _unknown_keys(
    diagnostics: list[Diagnostic], file: str, address: str, value: dict[object, object], allowed: set[str]
) -> None:
    """Report keys not present in a literal schema table."""

    for key in value:
        if not isinstance(key, str) or key not in allowed:
            field = str(key)
            diagnostics.append(_diagnostic("L1.unknown_key", file, address, field, f"unknown key {field!r}"))


def _required(
    diagnostics: list[Diagnostic], file: str, address: str, value: dict[object, object], keys: Iterable[str]
) -> None:
    """Report missing required keys without attempting to inspect their values."""

    for key in keys:
        if key not in value:
            diagnostics.append(_diagnostic("L1.missing_key", file, address, key, f"missing required key {key!r}"))


def _schema(diagnostics: list[Diagnostic], file: str, value: object) -> bool:
    """Check the universal schema marker and the top-level mapping shape."""

    if not _type_check(diagnostics, file, "root", "root", value, dict):
        return False
    document = value
    assert isinstance(document, dict)
    if "schema" not in document:
        diagnostics.append(_diagnostic("L1.missing_key", file, "root", "schema", "missing required key 'schema'"))
    elif not document or next(iter(document)) != "schema":
        diagnostics.append(_diagnostic("L1.missing_key", file, "root", "schema", "schema must be the first key"))
    elif type(document["schema"]) is not int or document["schema"] != 1:
        diagnostics.append(_diagnostic("L1.enum", file, "root", "schema", "schema must be 1"))
    return True


def _field(
    diagnostics: list[Diagnostic],
    file: str,
    address: str,
    value: dict[object, object],
    name: str,
    expected: type | tuple[type, ...],
    *,
    enum: set[object] | None = None,
    pattern: re.Pattern[str] | None = None,
) -> bool:
    """Validate one present field, including enum and identifier constraints."""

    if name not in value:
        return True
    item = value[name]
    if not _type_check(diagnostics, file, address, name, item, expected):
        return False
    if enum is not None and item not in enum:
        allowed = ", ".join(repr(option) for option in sorted(enum, key=repr))
        diagnostics.append(_diagnostic("L1.enum", file, address, name, f"{name} must be one of {allowed}"))
    if pattern is not None and isinstance(item, str) and pattern.fullmatch(item) is None:
        diagnostics.append(
            _diagnostic("L1.id_pattern", file, address, name, f"{name} does not match {pattern.pattern}")
        )
    return True


def _id_map(diagnostics: list[Diagnostic], file: str, address: str, value: object) -> dict[object, object] | None:
    """Check a map keyed by snake-case ids and return it when usable."""

    if not _type_check(diagnostics, file, address, address.rsplit(".", 1)[-1], value, dict):
        return None
    assert isinstance(value, dict)
    for key in value:
        if not isinstance(key, str) or _ID.fullmatch(key) is None:
            diagnostics.append(
                _diagnostic("L1.id_pattern", file, address, str(key), f"id {key!r} must match {_ID.pattern}")
            )
    return value


def _string_list(diagnostics: list[Diagnostic], file: str, address: str, field: str, value: object) -> bool:
    """Check a plain list of strings, stopping after the first bad item."""

    if not _type_check(diagnostics, file, address, field, value, list):
        return False
    assert isinstance(value, list)
    for index, item in enumerate(value):
        if not _type_check(diagnostics, file, _path(address, index), field, item, str):
            break
    return True


def _validate_ownership(file: str, value: dict[object, object], diagnostics: list[Diagnostic]) -> None:
    """Validate the optional coexistence manifest."""

    _unknown_keys(diagnostics, file, "root", value, _OWNERSHIP_KEYS)
    _required(diagnostics, file, "root", value, ("catalog", "scenes"))
    _field(diagnostics, file, "root", value, "catalog", str, enum={"legacy", "compiled"})
    scenes = value.get("scenes")
    if "scenes" in value and _type_check(diagnostics, file, "root", "scenes", scenes, dict):
        assert isinstance(scenes, dict)
        for scene, owner in scenes.items():
            if not isinstance(scene, str) or _SCENE_ID.fullmatch(scene) is None:
                diagnostics.append(
                    _diagnostic("L1.id_pattern", file, "scenes", str(scene), f"scene id {scene!r} is invalid")
                )
            if not _matches(owner, str):
                _type_check(diagnostics, file, "scenes", str(scene), owner, str)
            elif owner not in {"legacy", "compiled"}:
                diagnostics.append(
                    _diagnostic("L1.enum", file, "scenes", str(scene), "scene owner must be legacy or compiled")
                )


def _validate_story(file: str, value: dict[object, object], diagnostics: list[Diagnostic]) -> None:
    """Validate story identity, ordering, and reader-only root fields."""

    _unknown_keys(diagnostics, file, "root", value, _STORY_KEYS)
    _required(diagnostics, file, "root", value, ("story", "protagonist", "budget_seconds", "scenes"))
    _field(diagnostics, file, "root", value, "story", str, pattern=_ID)
    _field(diagnostics, file, "root", value, "protagonist", str, pattern=_ID)
    _field(diagnostics, file, "root", value, "budget_seconds", int)
    for name in ("title", "genre"):
        _field(diagnostics, file, "root", value, name, str)
    scenes = value.get("scenes")
    if "scenes" in value and _string_list(diagnostics, file, "root", "scenes", scenes):
        assert isinstance(scenes, list)
        for scene in scenes:
            if isinstance(scene, str) and _SCENE_ID.fullmatch(scene) is None:
                diagnostics.append(
                    _diagnostic("L1.id_pattern", file, "root", "scenes", f"scene id {scene!r} is invalid")
                )
    for name in ("principal_characters",):
        items = value.get(name)
        if name in value and _string_list(diagnostics, file, "root", name, items):
            assert isinstance(items, list)
            for item in items:
                if isinstance(item, str) and _ID.fullmatch(item) is None:
                    diagnostics.append(_diagnostic("L1.id_pattern", file, "root", name, f"id {item!r} is invalid"))
    if "acts" in value:
        _validate_acts(file, value["acts"], diagnostics)
    if "retired_ids" in value:
        _validate_retired_ids(file, value["retired_ids"], diagnostics)


def _validate_acts(file: str, value: object, diagnostics: list[Diagnostic]) -> None:
    """Validate the optional story act records."""

    if not _type_check(diagnostics, file, "root", "acts", value, list):
        return
    assert isinstance(value, list)
    for index, act in enumerate(value):
        address = _path("acts", index)
        if not _type_check(diagnostics, file, address, "act", act, dict):
            continue
        assert isinstance(act, dict)
        _unknown_keys(diagnostics, file, address, act, {"title", "intro", "scenes"})
        _required(diagnostics, file, address, act, ("title", "intro", "scenes"))
        _field(diagnostics, file, address, act, "title", str)
        _field(diagnostics, file, address, act, "intro", str)
        if _string_list(diagnostics, file, address, "scenes", act.get("scenes")):
            for scene in act.get("scenes", []):
                if isinstance(scene, str) and _SCENE_ID.fullmatch(scene) is None:
                    diagnostics.append(
                        _diagnostic("L1.id_pattern", file, address, "scenes", f"scene id {scene!r} is invalid")
                    )


def _validate_retired_ids(file: str, value: object, diagnostics: list[Diagnostic]) -> None:
    """Validate the optional save-identity retirement map."""

    if not _type_check(diagnostics, file, "root", "retired_ids", value, dict):
        return
    assert isinstance(value, dict)
    for kind, records in value.items():
        if not isinstance(kind, str) or _ID.fullmatch(kind) is None:
            diagnostics.append(_diagnostic("L1.id_pattern", file, "retired_ids", str(kind), f"id {kind!r} is invalid"))
        if not _type_check(diagnostics, file, "retired_ids", str(kind), records, dict):
            continue
        assert isinstance(records, dict)
        for identifier, reason in records.items():
            if not isinstance(identifier, str) or _ID.fullmatch(identifier) is None:
                diagnostics.append(
                    _diagnostic(
                        "L1.id_pattern",
                        file,
                        _path("retired_ids", str(kind)),
                        str(identifier),
                        f"id {identifier!r} is invalid",
                    )
                )
            _type_check(diagnostics, file, _path("retired_ids", str(kind)), str(identifier), reason, str)


def _validate_catalog(file: str, value: dict[object, object], diagnostics: list[Diagnostic]) -> None:
    """Validate catalog sections and the shape of their world records."""

    _unknown_keys(diagnostics, file, "root", value, _CATALOG_KEYS)
    _required(diagnostics, file, "root", value, _CATALOG_KEYS - {"schema"})
    for section in ("places", "characters", "groups", "items"):
        records = _id_map(diagnostics, file, section, value.get(section)) if section in value else None
        if records is not None:
            fields = {
                "places": _PLACE_KEYS,
                "characters": _CHARACTER_KEYS,
                "groups": _ENTITY_KEYS,
                "items": _ITEM_KEYS,
            }[section]
            for identifier, record in records.items():
                _validate_entity(file, section, identifier, record, fields, diagnostics)
    _validate_simple_maps(file, value, diagnostics)


def _validate_simple_maps(file: str, value: dict[object, object], diagnostics: list[Diagnostic]) -> None:
    """Validate catalog maps whose records have small, dedicated schemas."""

    for section, fields, required in (
        ("kinds", _KIND_KEYS, ()),
        ("props", _PROP_KEYS, ("name", "parents")),
        ("connections", _CONNECTION_KEYS, ("from", "to", "arrival")),
        ("disclosure_guards", _GUARD_KEYS, ("terms",)),
        ("unplaced_facts", _FACT_KEYS, ("purpose",)),
    ):
        records = _id_map(diagnostics, file, section, value.get(section)) if section in value else None
        if records is None:
            continue
        for identifier, record in records.items():
            address = _path(section, str(identifier))
            if not _type_check(diagnostics, file, address, str(identifier), record, dict):
                continue
            assert isinstance(record, dict)
            _unknown_keys(diagnostics, file, address, record, fields)
            _required(diagnostics, file, address, record, required)
            _validate_catalog_record(file, section, address, record, diagnostics)
    if "protected_knowledge" in value:
        protected = value["protected_knowledge"]
        _string_list(diagnostics, file, "root", "protected_knowledge", protected)


def _validate_catalog_record(
    file: str, section: str, address: str, record: dict[object, object], diagnostics: list[Diagnostic]
) -> None:
    """Validate fields that differ among kinds, props, connections, and guards."""

    if section == "kinds":
        _string_list(diagnostics, file, address, "is", record.get("is"))
        for name in ("enterable", "fixed"):
            _field(diagnostics, file, address, record, name, bool)
    elif section == "props":
        _string_list(diagnostics, file, address, "parents", record.get("parents"))
        _field(diagnostics, file, address, record, "fixed", bool)
        _string_map_of_string_lists(file, address, record, "facets", diagnostics)
    elif section == "connections":
        for name in ("from", "to", "via", "access_fact"):
            _field(diagnostics, file, address, record, name, str, pattern=_ID)
        _field(diagnostics, file, address, record, "arrival", str)
        if "consequences" in record and not _type_check(
            diagnostics, file, address, "consequences", record["consequences"], (list, dict)
        ):
            return
    elif section == "disclosure_guards":
        _string_list(diagnostics, file, address, "terms", record.get("terms"))
        _field(diagnostics, file, address, record, "audience", str, enum={"player"})
        for name in ("unlock_fact", "unlock_claim"):
            _field(diagnostics, file, address, record, name, str, pattern=_ID)
    elif section == "unplaced_facts":
        _validate_fact_fields(file, address, record, diagnostics)


def _validate_entity(
    file: str, section: str, identifier: object, record: object, fields: set[str], diagnostics: list[Diagnostic]
) -> None:
    """Validate one catalog entity without assuming its container is well formed."""

    address = _path(section, str(identifier))
    if not _type_check(diagnostics, file, address, str(identifier), record, dict):
        return
    assert isinstance(record, dict)
    _unknown_keys(diagnostics, file, address, record, fields)
    _required(diagnostics, file, address, record, ("name",))
    _field(diagnostics, file, address, record, "name", str)
    for name in ("aliases", "scoped_aliases", "fallback_ids", "contents"):
        if name in record:
            _string_list(diagnostics, file, address, name, record[name])
    _field(diagnostics, file, address, record, "disclosure", str, enum={"legacy", "public"})
    for name in (
        "unnamed_label",
        "narrator_bio",
        "bio",
        "description",
        "right_text",
        "enter_text",
        "leave_text",
        "take_text",
        "notice_text",
    ):
        _field(diagnostics, file, address, record, name, str)
    for name in ("named_by", "parent", "owner", "unavailable", "kind", "enter_pole", "seat_for"):
        _field(diagnostics, file, address, record, name, str, pattern=_ID)
    if section == "characters":
        _validate_axes(file, address, record, diagnostics)
    if section == "items":
        for name in ("fixed", "openable", "open", "hidden", "contents_complete", "enterable", "use_seated"):
            _field(diagnostics, file, address, record, name, bool)
        _validate_axes(file, address, record, diagnostics)
        _string_map_of_string_lists(file, address, record, "facets", diagnostics)
        _string_map(file, address, record, "authored_facets", diagnostics)


def _validate_axes(file: str, address: str, record: dict[object, object], diagnostics: list[Diagnostic]) -> None:
    """Validate the catalog axis list used by characters and items."""

    if "axes" not in record:
        return
    if not _type_check(diagnostics, file, address, "axes", record["axes"], list):
        return
    assert isinstance(record["axes"], list)
    for index, axis in enumerate(record["axes"]):
        item_address = _path(address, index)
        if not _type_check(diagnostics, file, item_address, "axes", axis, dict):
            break
        assert isinstance(axis, dict)
        for name, poles in axis.items():
            _string_list(diagnostics, file, item_address, str(name), poles)


def _string_map(
    file: str, address: str, record: dict[object, object], name: str, diagnostics: list[Diagnostic]
) -> None:
    """Validate a map whose values are strings."""

    if name not in record:
        return
    if not _type_check(diagnostics, file, address, name, record[name], dict):
        return
    assert isinstance(record[name], dict)
    for key, item in record[name].items():
        _type_check(diagnostics, file, _path(address, name), str(key), item, str)


def _string_map_of_string_lists(
    file: str, address: str, record: dict[object, object], name: str, diagnostics: list[Diagnostic]
) -> None:
    """Validate a map whose values are lists of strings."""

    if name not in record:
        return
    if not _type_check(diagnostics, file, address, name, record[name], dict):
        return
    assert isinstance(record[name], dict)
    for key, item in record[name].items():
        _string_list(diagnostics, file, _path(address, name), str(key), item)


def _validate_fact_fields(file: str, address: str, record: dict[object, object], diagnostics: list[Diagnostic]) -> None:
    """Validate the fact declaration fields used by catalog.unplaced_facts."""

    _field(diagnostics, file, address, record, "purpose", str)
    if "on_assert" in record and not _type_check(diagnostics, file, address, "on_assert", record["on_assert"], list):
        return
    delivery = record.get("delivery")
    if delivery is None:
        return
    if not _type_check(diagnostics, file, address, "delivery", delivery, dict):
        return
    assert isinstance(delivery, dict)
    _unknown_keys(diagnostics, file, address, delivery, _DELIVERY_KEYS)
    _required(diagnostics, file, address, delivery, ("source_kind", "fallback_text"))
    _field(
        diagnostics,
        file,
        address,
        delivery,
        "source_kind",
        str,
        enum={"message", "npc", "broadcast", "observation", "inference"},
    )
    for name in ("scene",):
        _field(diagnostics, file, address, delivery, name, str, pattern=_SCENE_ID)
    for name in ("source_entity", "fallback_text", "cue_text", "escalation_text"):
        _field(diagnostics, file, address, delivery, name, str)


def _validate_match(
    file: str, scene_from_name: str, value: dict[object, object], diagnostics: list[Diagnostic]
) -> tuple[bool, bool]:
    """Validate one match file and return its lexicon and plural flags."""

    _unknown_keys(diagnostics, file, "root", value, _MATCH_KEYS)
    _required(diagnostics, file, "root", value, ("scene", "claims"))
    _field(diagnostics, file, "root", value, "scene", str, pattern=_SCENE_ID)
    if isinstance(value.get("scene"), str) and value["scene"] != scene_from_name:
        diagnostics.append(
            _diagnostic("L1.match_scene", file, "root", "scene", f"scene must match file name {scene_from_name}")
        )
    for name in ("lexicon", "plural_twins"):
        _field(diagnostics, file, "root", value, name, bool)
    if "shared" in value:
        _validate_shared_or_claims(file, "shared", value["shared"], diagnostics, required=False)
    if "claims" in value:
        _validate_shared_or_claims(file, "claims", value["claims"], diagnostics, required=True)
    else:
        _required(diagnostics, file, "root", value, ("claims",))
    if "deliveries" in value:
        _validate_match_deliveries(file, value["deliveries"], diagnostics)
    return value.get("lexicon") is True, value.get("plural_twins") is True


def _validate_shared_or_claims(
    file: str, section: str, value: object, diagnostics: list[Diagnostic], *, required: bool
) -> None:
    """Validate shared matcher blocks or claim matcher records."""

    if value is None:
        if required:
            _type_check(diagnostics, file, "root", section, value, dict)
        else:
            _type_check(diagnostics, file, "root", section, value, dict)
        return
    records = _id_map(diagnostics, file, "root", value)
    if records is None:
        return
    for identifier, record in records.items():
        address = _path(section, str(identifier))
        if not _type_check(diagnostics, file, address, str(identifier), record, dict):
            continue
        assert isinstance(record, dict)
        _unknown_keys(diagnostics, file, address, record, _MATCH_FIELDS | ({"use"} if section == "claims" else set()))
        if section == "claims" and "aliases" not in record and "use" not in record:
            diagnostics.append(_diagnostic("L1.missing_key", file, address, "aliases", "missing aliases (or use)"))
        _field(diagnostics, file, address, record, "use", str, pattern=_ID)
        for name in _MATCH_FIELDS:
            if name in record:
                _validate_match_value(file, address, name, record[name], diagnostics)


def _validate_match_deliveries(file: str, value: object, diagnostics: list[Diagnostic]) -> None:
    """Validate delivery matcher records when the optional section is present."""

    if value is None:
        _type_check(diagnostics, file, "root", "deliveries", value, dict)
        return
    records = _id_map(diagnostics, file, "root", value)
    if records is None:
        return
    for identifier, record in records.items():
        address = _path("deliveries", str(identifier))
        if not _type_check(diagnostics, file, address, str(identifier), record, dict):
            continue
        assert isinstance(record, dict)
        _unknown_keys(diagnostics, file, address, record, {"must_convey"})
        _required(diagnostics, file, address, record, ("must_convey",))
        if "must_convey" in record:
            _validate_match_value(file, address, "must_convey", record["must_convey"], diagnostics)


def _validate_match_value(file: str, address: str, name: str, value: object, diagnostics: list[Diagnostic]) -> None:
    """Validate a matcher list or a lexicon-derived matcher value."""

    if isinstance(value, list):
        if name == "aliases" or name == "leak_terms":
            _string_list(diagnostics, file, address, name, value)
            return
        for index, group in enumerate(value):
            group_address = _path(address, index)
            if isinstance(group, list):
                _string_list(diagnostics, file, group_address, name, group)
            elif isinstance(group, dict):
                _validate_derived(file, group_address, group, diagnostics)
            else:
                _type_check(diagnostics, file, group_address, name, group, (list, dict))
        return
    if isinstance(value, dict):
        _validate_derived(file, address, value, diagnostics)
        return
    _type_check(diagnostics, file, address, name, value, (list, dict))


def _validate_derived(file: str, address: str, value: dict[object, object], diagnostics: list[Diagnostic]) -> None:
    """Validate the pass-two {from, add, drop, first} matcher form."""

    _unknown_keys(diagnostics, file, address, value, _DERIVED_KEYS)
    for name in ("from", "add", "drop"):
        if name in value:
            _string_list(diagnostics, file, address, name, value[name])
    _field(diagnostics, file, address, value, "first", str)


def _validate_lock(file: str, value: dict[object, object], diagnostics: list[Diagnostic]) -> None:
    """Validate generated match-lock structure without checking its references."""

    _unknown_keys(diagnostics, file, "root", value, _LOCK_KEYS)
    _required(diagnostics, file, "root", value, ("scene", "generated_by", "claims", "deliveries"))
    _field(diagnostics, file, "root", value, "scene", str, pattern=_SCENE_ID)
    _field(diagnostics, file, "root", value, "generated_by", str)
    for section in ("claims", "deliveries"):
        records = _id_map(diagnostics, file, section, value.get(section)) if section in value else None
        if records is None:
            continue
        for identifier, record in records.items():
            address = _path(section, str(identifier))
            if not _type_check(diagnostics, file, address, str(identifier), record, dict):
                continue
            assert isinstance(record, dict)
            _unknown_keys(diagnostics, file, address, record, _MATCH_FIELDS)
            for name, item in record.items():
                if name in _MATCH_FIELDS:
                    _validate_match_value(file, address, name, item, diagnostics)


def _validate_lexicon(file: str, value: dict[object, object], diagnostics: list[Diagnostic]) -> None:
    """Validate the optional pass-two lexicon."""

    _unknown_keys(diagnostics, file, "root", value, _LEXICON_KEYS)
    _required(diagnostics, file, "root", value, ("entities", "concepts", "verb_classes"))
    for section in ("entities", "concepts", "verb_classes"):
        records = _id_map(diagnostics, file, section, value.get(section)) if section in value else None
        if records is None:
            continue
        for identifier, record in records.items():
            address = _path(section, str(identifier))
            if not _type_check(diagnostics, file, address, str(identifier), record, dict):
                continue
            assert isinstance(record, dict)
            allowed = (
                {"names", "hidden_names"}
                if section == "entities"
                else {"names"}
                if section == "concepts"
                else {"words"}
            )
            required = ("names", "words")[section == "verb_classes"]
            _unknown_keys(diagnostics, file, address, record, allowed)
            _required(diagnostics, file, address, record, (required,))
            if required in record:
                _string_list(diagnostics, file, address, required, record[required])
            if "hidden_names" in record:
                _string_list(diagnostics, file, address, "hidden_names", record["hidden_names"])


def _scan_lexicon_off(file: str, value: object, diagnostics: list[Diagnostic], address: str = "root") -> None:
    """Reject pass-two syntax in a match file whose lexicon flag is off."""

    if isinstance(value, dict):
        for key, item in value.items():
            child = _path(address, str(key))
            if key == "from":
                diagnostics.append(
                    _diagnostic("L1.lexicon_off", file, child, "from", "lexicon references require lexicon: true")
                )
                continue
            _scan_lexicon_off(file, item, diagnostics, child)
    elif isinstance(value, list):
        for index, item in enumerate(value):
            _scan_lexicon_off(file, item, diagnostics, _path(address, index))
    elif isinstance(value, str) and value.startswith("$"):
        diagnostics.append(
            _diagnostic("L1.lexicon_off", file, address, "value", "lexicon references require lexicon: true")
        )


def _scan_plural(file: str, value: object, diagnostics: list[Diagnostic], address: str = "root") -> None:
    """Reject plural-twin syntax when the owning match option is disabled."""

    if isinstance(value, dict):
        for key, item in value.items():
            _scan_plural(file, item, diagnostics, _path(address, str(key)))
    elif isinstance(value, list):
        for index, item in enumerate(value):
            _scan_plural(file, item, diagnostics, _path(address, index))
    elif isinstance(value, str) and _PLURAL.search(value):
        diagnostics.append(
            _diagnostic("L1.plural_off", file, address, "value", "plural twins require plural_twins: true")
        )


@layer1_check
def check_root_and_match_files(tree: SourceTree) -> list[Diagnostic]:
    """Run all shape and pass-two checks owned by the root/match worker."""

    diagnostics: list[Diagnostic] = []
    match_files: list[tuple[str, object, bool, bool]] = []
    for file, value in tree.files.items():
        if value is None:
            continue
        if file == "ownership.yaml":
            if _schema(diagnostics, file, value):
                assert isinstance(value, dict)
                _validate_ownership(file, value, diagnostics)
        elif file == "story.yaml":
            if _schema(diagnostics, file, value):
                assert isinstance(value, dict)
                _validate_story(file, value, diagnostics)
        elif file == "catalog.yaml":
            if _schema(diagnostics, file, value):
                assert isinstance(value, dict)
                _validate_catalog(file, value, diagnostics)
        elif match := _MATCH_FILE.fullmatch(file):
            if _schema(diagnostics, file, value):
                assert isinstance(value, dict)
                lexicon_on, plural_on = _validate_match(file, match.group(1), value, diagnostics)
                match_files.append((file, value, lexicon_on, plural_on))
        elif _LOCK_FILE.fullmatch(file) and _schema(diagnostics, file, value):
            assert isinstance(value, dict)
            _validate_lock(file, value, diagnostics)
    lexicon_on = any(item[2] for item in match_files)
    if lexicon_on and "lexicon.yaml" in tree.files and tree.files["lexicon.yaml"] is not None:
        value = tree.files["lexicon.yaml"]
        if _schema(diagnostics, "lexicon.yaml", value):
            assert isinstance(value, dict)
            _validate_lexicon("lexicon.yaml", value, diagnostics)
    for file, value, lexicon_enabled, plural_enabled in match_files:
        if not lexicon_enabled:
            _scan_lexicon_off(file, value, diagnostics)
        if not plural_enabled:
            _scan_plural(file, value, diagnostics)
    if (
        lexicon_on
        and any(item[2] and not item[3] for item in match_files)
        and tree.files.get("lexicon.yaml") is not None
    ):
        _scan_plural("lexicon.yaml", tree.files["lexicon.yaml"], diagnostics)
    return diagnostics
