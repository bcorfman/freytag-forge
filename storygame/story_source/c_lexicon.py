"""Expand optional matcher references into deterministic pass-two lists."""

from __future__ import annotations

import re
from collections.abc import Mapping, Sequence
from typing import Any

_PLURAL = re.compile(r"^(.*?)(\(s\)|\(es\))$")


def resolve_match_value(
    value: object,
    *,
    field: str,
    record_id: str,
    lexicon: Mapping[str, Any] | None,
    plural_twins: bool,
    lock: Mapping[str, Any] | None,
    lock_section: str,
) -> object:
    """Resolve one matcher value and prefer its generated lock when present."""

    derived = _has_derived(value)
    result = _resolve_value(value, field, lexicon, plural_twins)
    if derived:
        locked = _locked_value(lock, lock_section, record_id, field)
        if locked is not None:
            return locked
    return result


def _resolve_value(value: object, field: str, lexicon: Mapping[str, Any] | None, plural_twins: bool) -> object:
    """Resolve a field while retaining the shape expected by the package model."""

    if isinstance(value, Mapping):
        return _derived(value, lexicon, plural_twins)
    if not isinstance(value, list):
        return value
    if field in {"aliases", "leak_terms"}:
        return _plain_strings(value, plural_twins)
    return [_resolve_group(group, lexicon, plural_twins) for group in value]


def _has_derived(value: object) -> bool:
    """Detect a derived expression at any depth of a matcher field."""

    if isinstance(value, Mapping):
        return True
    if isinstance(value, list):
        return any(_has_derived(item) for item in value)
    return False


def _resolve_group(value: object, lexicon: Mapping[str, Any] | None, plural_twins: bool) -> list[str]:
    """Resolve one action or must-convey group."""

    if isinstance(value, Mapping):
        return _derived(value, lexicon, plural_twins)
    return _plain_strings(value if isinstance(value, list) else (), plural_twins)


def _derived(value: Mapping[str, Any], lexicon: Mapping[str, Any] | None, plural_twins: bool) -> list[str]:
    """Expand a `{first, from, add, drop}` expression in written order."""

    values: list[str] = []
    if isinstance(value.get("first"), str):
        values.extend(_plural(value["first"], plural_twins))
    for reference in value.get("from", ()):
        if isinstance(reference, str):
            values.extend(_reference(reference, lexicon, plural_twins))
    for item in value.get("add", ()):
        if isinstance(item, str):
            values.extend(_plural(item, plural_twins))
    drops = {
        variant.casefold()
        for item in value.get("drop", ())
        if isinstance(item, str)
        for variant in _plural(item, plural_twins)
    }
    return _dedupe(item for item in values if item.casefold() not in drops)


def _reference(reference: str, lexicon: Mapping[str, Any] | None, plural_twins: bool) -> list[str]:
    """Expand one `$entry`, `$entry.hidden`, or `$entry.all` reference."""

    if not reference.startswith("$") or not isinstance(lexicon, Mapping):
        return []
    name, _, selector = reference[1:].partition(".")
    for section in ("entities", "concepts", "verb_classes"):
        records = lexicon.get(section, {})
        if not isinstance(records, Mapping) or name not in records:
            continue
        record = records[name]
        if not isinstance(record, Mapping):
            return []
        if section == "verb_classes":
            values = record.get("words", ())
        else:
            values = record.get("names", ())
            if selector in {"hidden", "all"}:
                hidden = record.get("hidden_names", ())
                values = (*values, *hidden)
        return _dedupe(variant for item in values for variant in _plural(item, plural_twins))
    return []


def _plain_strings(values: Sequence[object], plural_twins: bool) -> list[str]:
    """Convert a plain list without changing its order or duplicate policy."""

    return [variant for item in values if isinstance(item, str) for variant in _plural(item, plural_twins)]


def _plural(value: str, enabled: bool) -> tuple[str, ...]:
    """Expand a terminal plural-twin marker when the scene enables it."""

    if not enabled:
        return (value,)
    match = _PLURAL.fullmatch(value)
    if match is None:
        return (value,)
    suffix = "s" if match.group(2) == "(s)" else "es"
    return (match.group(1), match.group(1) + suffix)


def _dedupe(values: Sequence[str] | Any) -> list[str]:
    """Remove later case-insensitive duplicates while preserving first occurrence."""

    result: list[str] = []
    seen: set[str] = set()
    for value in values:
        key = value.casefold()
        if key not in seen:
            seen.add(key)
            result.append(value)
    return result


def _locked_value(lock: Mapping[str, Any] | None, section: str, record_id: str, field: str) -> object:
    """Read one generated lock value, distinguishing absent from an empty list."""

    if not isinstance(lock, Mapping):
        return None
    records = lock.get(section)
    record = records.get(record_id) if isinstance(records, Mapping) else None
    if isinstance(record, Mapping) and field in record:
        return record[field]
    return None
