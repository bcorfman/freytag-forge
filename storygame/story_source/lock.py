"""Generate, compare, and expand pass-two matcher locks."""

from __future__ import annotations

import re
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml

from .c_lexicon import resolve_match_value

_FIELDS = ("action_evidence", "must_convey", "leak_terms", "aliases")
_WORD_RE = re.compile(r"[^\W_]+(?:'[^\W_]+)*", re.UNICODE)


@dataclass
class LockReport:
    """Describe a lock update without exposing YAML implementation details."""

    changed: list[tuple[str, str]]
    mismatches: list[str]


@dataclass(frozen=True)
class DerivedValue:
    """One effective derived matcher field and its lock address."""

    section: str
    record_id: str
    field: str
    raw: object
    expanded: object
    direct: bool


def _words(value: str) -> tuple[str, ...]:
    """Return the word-normalized form used by the action matcher."""

    try:
        from storygame.runtime.candidate_matcher import _words as matcher_words
    except (ImportError, AttributeError):
        return tuple(_WORD_RE.findall(value.casefold()))
    return tuple(matcher_words(value))


def _action_group(group: object) -> frozenset[tuple[str, ...]]:
    """Return the matcher closure for one action-evidence group."""

    if not isinstance(group, (list, tuple)):
        return frozenset()
    try:
        from storygame.runtime.candidate_matcher import _LOOK_OPERATIONS, _SYNONYM_CLASSES
    except (ImportError, AttributeError):
        return frozenset(_words(value) for value in group if isinstance(value, str))
    accepted = {value for value in group if isinstance(value, str)}
    for phrase in tuple(accepted):
        normalized = " ".join(_words(phrase))
        for index, synonym_class in enumerate(_SYNONYM_CLASSES):
            if normalized in synonym_class:
                accepted.update(synonym_class)
                if index == 0:
                    accepted.update(_LOOK_OPERATIONS)
    return frozenset(_words(value) for value in accepted)


def _action_signature(value: object) -> tuple[frozenset[tuple[str, ...]], ...] | None:
    """Normalize action groups while retaining their multiset cardinality."""

    if not isinstance(value, (list, tuple)):
        return None
    return tuple(sorted((_action_group(group) for group in value), key=repr))


def _kind(value: object) -> str:
    """Return the shape kind relevant to optional leak terms."""

    if value is None:
        return "none"
    if isinstance(value, tuple):
        return "tuple"
    if isinstance(value, list):
        return "list"
    return type(value).__name__


def equivalent(field: str, expanded: object, locked: object) -> bool:
    """Return whether a generated lock preserves the field's engine semantics."""

    if field == "action_evidence":
        left = _action_signature(expanded)
        right = _action_signature(locked)
        return left is not None and right is not None and sorted(left, key=repr) == sorted(right, key=repr)
    if field == "must_convey":
        if not isinstance(expanded, (list, tuple)) or not isinstance(locked, (list, tuple)):
            return False
        if len(expanded) != len(locked):
            return False
        return all(
            isinstance(left, (list, tuple))
            and isinstance(right, (list, tuple))
            and bool(left)
            and bool(right)
            and left[0] == right[0]
            and {str(item).casefold() for item in left[1:]} == {str(item).casefold() for item in right[1:]}
            for left, right in zip(expanded, locked, strict=True)
        )
    if field == "leak_terms":
        return _kind(expanded) == _kind(locked) and (
            expanded is None
            or (isinstance(expanded, (list, tuple)) and isinstance(locked, (list, tuple)))
            and {str(item).casefold() for item in expanded} == {str(item).casefold() for item in locked}
        )
    if field == "aliases":
        return (
            isinstance(expanded, (list, tuple)) and isinstance(locked, (list, tuple)) and list(expanded) == list(locked)
        )
    return False


def _mapping(value: object) -> Mapping[str, Any] | None:
    """Return a mapping with string-key behavior where possible."""

    return value if isinstance(value, Mapping) else None


def _has_derived(value: object) -> bool:
    """Detect a derived map anywhere in a supported matcher value."""

    if isinstance(value, Mapping):
        return True
    return isinstance(value, list) and any(_has_derived(item) for item in value)


def _effective_raw(match: Mapping[str, Any], claim: Mapping[str, Any], field: str) -> object:
    """Apply shared and claim matcher precedence without expanding it."""

    base: dict[str, Any] = {}
    shared = _mapping(match.get("shared"))
    use = claim.get("use")
    if shared is not None and isinstance(use, str) and isinstance(shared.get(use), Mapping):
        base.update(shared[use])
    if shared is not None and field in shared:
        base[field] = shared[field]
    if field not in claim:
        return base.get(field)
    override = claim[field]
    if field == "leak_terms" and isinstance(override, Mapping) and "add" in override:
        original = base.get(field, [])
        if isinstance(original, Mapping):
            merged = dict(original)
            merged["add"] = [*merged.get("add", ()), *override["add"]]
            return merged
        return [*original, *override["add"]] if isinstance(original, list) else override["add"]
    return override


def _expanded(raw: object, field: str, record_id: str, lexicon: object, plural_twins: bool) -> object:
    """Expand a raw field without consulting a lock."""

    return resolve_match_value(
        raw,
        field=field,
        record_id=record_id,
        lexicon=_mapping(lexicon),
        plural_twins=plural_twins,
        lock=None,
        lock_section="claims",
    )


def derived_values(match: Mapping[str, Any], lexicon: object) -> tuple[DerivedValue, ...]:
    """Yield every effective derived claim and delivery field in source order."""

    result: list[DerivedValue] = []
    plural_twins = match.get("plural_twins") is True
    claims = _mapping(match.get("claims")) or {}
    for record_id, claim in claims.items():
        if not isinstance(record_id, str) or not isinstance(claim, Mapping):
            continue
        for field in _FIELDS:
            raw = _effective_raw(match, claim, field)
            if _has_derived(raw):
                result.append(
                    DerivedValue(
                        "claims",
                        record_id,
                        field,
                        raw,
                        _expanded(raw, field, record_id, lexicon, plural_twins),
                        field in claim,
                    )
                )
    deliveries = _mapping(match.get("deliveries")) or {}
    for record_id, delivery in deliveries.items():
        if not isinstance(record_id, str) or not isinstance(delivery, Mapping):
            continue
        raw = delivery.get("must_convey")
        if _has_derived(raw):
            result.append(
                DerivedValue(
                    "deliveries",
                    record_id,
                    "must_convey",
                    raw,
                    _expanded(raw, "must_convey", record_id, lexicon, plural_twins),
                    True,
                )
            )
    return tuple(result)


def lock_value(lock: object, value: DerivedValue) -> tuple[bool, object]:
    """Return a lock value while distinguishing an absent entry from an empty one."""

    document = _mapping(lock)
    records = _mapping(document.get(value.section)) if document is not None else None
    record = _mapping(records.get(value.record_id)) if records is not None else None
    if record is None or value.field not in record:
        return False, None
    return True, record[value.field]


def _load(path: Path) -> object:
    """Read one YAML document, returning ``None`` for a missing file."""

    if not path.is_file():
        return None
    with path.open(encoding="utf-8") as stream:
        return yaml.safe_load(stream)


def _source(root: Path, scene: str) -> tuple[dict[str, Any], object, object]:
    """Load the match file and only load lexicon data for lexicon-on scenes."""

    match = _mapping(_load(root / f"scenes/{scene}.match.yaml"))
    if match is None:
        raise FileNotFoundError(f"scenes/{scene}.match.yaml")
    lexicon = _load(root / "lexicon.yaml") if match.get("lexicon") is True else None
    lock = _load(root / f"scenes/{scene}.match.lock.yaml")
    return dict(match), lexicon, lock


def _mismatch(value: DerivedValue, locked: object) -> str:
    """Describe the additions and removals needed to replace a lock value."""

    added, dropped = _differences(value.field, value.expanded, locked)
    return f"{value.record_id}.{value.field}: add: {added!r}; drop: {dropped!r}"


def _differences(field: str, expanded: object, locked: object) -> tuple[list[object], list[object]]:
    """Return the semantic entries that must be added to or dropped from a lock."""

    if field == "action_evidence" and isinstance(expanded, list) and isinstance(locked, list):
        left = {_action_group(item): item for item in expanded}
        right = {_action_group(item): item for item in locked}
    elif field == "must_convey" and isinstance(expanded, list) and isinstance(locked, list):
        left = {_must_group(item): item for item in expanded}
        right = {_must_group(item): item for item in locked}
    elif field == "leak_terms" and isinstance(expanded, (list, tuple)) and isinstance(locked, (list, tuple)):
        left = {str(item).casefold(): item for item in expanded}
        right = {str(item).casefold(): item for item in locked}
    else:
        left = {repr(item): item for item in expanded} if isinstance(expanded, (list, tuple)) else {}
        right = {repr(item): item for item in locked} if isinstance(locked, (list, tuple)) else {}
    return [left[key] for key in left if key not in right], [right[key] for key in right if key not in left]


def _must_group(group: object) -> tuple[object, frozenset[str]]:
    """Return the equivalence key for one must-convey group."""

    if not isinstance(group, (list, tuple)) or not group:
        return None, frozenset()
    return group[0], frozenset(str(item).casefold() for item in group[1:])


def _lock_document(scene: str, records: Mapping[str, Any], deliveries: Mapping[str, Any]) -> dict[str, Any]:
    """Build the stable generated lock document."""

    return {
        "schema": 1,
        "scene": scene,
        "generated_by": "story lock",
        "claims": dict(records),
        "deliveries": dict(deliveries),
    }


def _write_lock(path: Path, document: Mapping[str, Any]) -> None:
    """Write a generated lock with stable key order."""

    path.write_text(yaml.safe_dump(document, sort_keys=False, width=10_000, allow_unicode=True), encoding="utf-8")


def lock_scene(root: Path, scene: str, *, adopt: bool = False) -> LockReport:
    """Generate or refresh one scene lock and report semantic mismatches."""

    root = Path(root)
    match, lexicon, existing = _source(root, scene)
    values = derived_values(match, lexicon)
    current = _mapping(existing) or _lock_document(scene, {}, {})
    records = {
        key: dict(value) for key, value in (_mapping(current.get("claims")) or {}).items() if isinstance(value, Mapping)
    }
    deliveries = {
        key: dict(value)
        for key, value in (_mapping(current.get("deliveries")) or {}).items()
        if isinstance(value, Mapping)
    }
    changed: list[tuple[str, str]] = []
    mismatches: list[str] = []
    for value in values:
        present, locked = lock_value(current, value)
        if present and value.direct and not equivalent(value.field, value.expanded, locked):
            mismatches.append(_mismatch(value, locked))
            if adopt:
                continue
            changed.append((value.record_id, value.field))
            (records if value.section == "claims" else deliveries).setdefault(value.record_id, {})[value.field] = (
                value.expanded
            )
        elif not present:
            changed.append((value.record_id, value.field))
            (records if value.section == "claims" else deliveries).setdefault(value.record_id, {})[value.field] = (
                value.expanded
            )
    if adopt and mismatches:
        return LockReport([], mismatches)
    if changed:
        _write_lock(root / f"scenes/{scene}.match.lock.yaml", _lock_document(scene, records, deliveries))
    return LockReport(changed, mismatches)


def _replace_claim_values(
    match: dict[str, Any], values: tuple[DerivedValue, ...], lock: object, lexicon: object
) -> None:
    """Replace direct claim and delivery expressions with their plain lock lists."""

    claims = match.get("claims")
    deliveries = match.get("deliveries")
    for value in values:
        records = claims if value.section == "claims" else deliveries
        record = records.get(value.record_id) if isinstance(records, dict) else None
        if not isinstance(record, dict):
            continue
        if value.section == "claims" and value.field not in record:
            continue
        present, locked = lock_value(lock, value)
        if present:
            record[value.field] = locked
        else:
            record[value.field] = value.expanded


def _replace_shared_values(match: dict[str, Any], values: tuple[DerivedValue, ...], lock: object) -> None:
    """Replace shared expressions when all effective users have one lock value."""

    shared = match.get("shared")
    if not isinstance(shared, dict):
        return
    claims = match.get("claims") if isinstance(match.get("claims"), dict) else {}
    blocks = (("top", shared), *[(str(key), item) for key, item in shared.items() if isinstance(item, dict)])
    for section_name, block in blocks:
        if not isinstance(block, dict):
            continue
        for field in _FIELDS:
            raw = block.get(field)
            if not _has_derived(raw):
                continue
            users = [
                claim_id
                for claim_id, claim in claims.items()
                if isinstance(claim_id, str)
                and isinstance(claim, Mapping)
                and ((section_name == "top" and field not in claim) or claim.get("use") == section_name)
                and _has_derived(_effective_raw(match, claim, field))
            ]
            locked_values = [
                lock_value(lock, item)[1] for item in values if item.record_id in users and item.field == field
            ]
            if locked_values and all(candidate == locked_values[0] for candidate in locked_values[1:]):
                block[field] = locked_values[0]
            elif locked_values:
                block[field] = next(item.expanded for item in values if item.record_id in users and item.field == field)


def expand_scene(root: Path, scene: str) -> None:
    """Materialize a scene's lock values and disable lexicon expansion."""

    root = Path(root)
    match, lexicon, lock = _source(root, scene)
    values = derived_values(match, lexicon)
    _replace_shared_values(match, values, lock)
    _replace_claim_values(match, values, lock, lexicon)
    match["lexicon"] = False
    path = root / f"scenes/{scene}.match.yaml"
    path.write_text(yaml.safe_dump(match, sort_keys=False, width=10_000, allow_unicode=True), encoding="utf-8")
