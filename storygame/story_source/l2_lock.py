"""Layer-two checks for stale generated matcher locks and unused drops."""

from __future__ import annotations

import re
from collections.abc import Mapping
from typing import Any

from .c_lexicon import resolve_match_value
from .checks import layer2_check
from .diagnostics import Diagnostic
from .lock import DerivedValue, derived_values, equivalent, lock_value
from .reader import SourceTree

_PLURAL = re.compile(r"\((?:s|es)\)")


def _mapping(value: object) -> Mapping[str, Any] | None:
    """Return mappings only, keeping malformed layer-one values out of this check."""

    return value if isinstance(value, Mapping) else None


def _match_files(tree: SourceTree) -> list[tuple[str, str, Mapping[str, Any]]]:
    """Yield lexicon-enabled match files in deterministic order."""

    result: list[tuple[str, str, Mapping[str, Any]]] = []
    for file, value in sorted(tree.files.items()):
        if not file.startswith("scenes/") or not file.endswith(".match.yaml"):
            continue
        match = _mapping(value)
        scene = match.get("scene") if match is not None else None
        if isinstance(scene, str) and match.get("lexicon") is True:
            result.append((file, scene, match))
    return result


def _stale_diagnostic(scene: str, value: DerivedValue, reason: str) -> Diagnostic:
    """Build the contract's lock-file diagnostic for one stale field."""

    return Diagnostic(
        "L2.lock_stale",
        f"scenes/{scene}.match.lock.yaml",
        f"claim:{value.record_id}.{value.field}",
        value.field,
        f"claim {value.record_id!r} field {value.field!r} has {reason} lock entry",
    )


def _drop_diagnostic(file: str, value: DerivedValue) -> Diagnostic:
    """Build a diagnostic for a drop expression with no effect."""

    return Diagnostic(
        "L2.drop_unused",
        file,
        f"claim:{value.record_id}.{value.field}",
        "drop",
        f"claim {value.record_id!r} field {value.field!r} has a drop entry that removes nothing",
    )


def _drop_unused(raw: object, field: str, record_id: str, lexicon: object, plural_twins: bool) -> bool:
    """Return whether any drop in one derived expression removes no value."""

    expressions = (
        [raw]
        if isinstance(raw, Mapping)
        else [item for item in raw if isinstance(item, Mapping)]
        if isinstance(raw, list)
        else []
    )
    return any(_drop_unused_expression(item, field, record_id, lexicon, plural_twins) for item in expressions)


def _drop_unused_expression(
    expression: Mapping[str, Any], field: str, record_id: str, lexicon: object, plural_twins: bool
) -> bool:
    """Check the drops in one derived map."""

    drops = expression.get("drop")
    if not isinstance(drops, list):
        return False
    for index, _drop in enumerate(drops):
        without = dict(expression)
        without["drop"] = [item for position, item in enumerate(drops) if position != index]
        with_drop = resolve_match_value(
            expression,
            field=field,
            record_id=record_id,
            lexicon=_mapping(lexicon),
            plural_twins=plural_twins,
            lock=None,
            lock_section="claims",
        )
        without_drop = resolve_match_value(
            without,
            field=field,
            record_id=record_id,
            lexicon=_mapping(lexicon),
            plural_twins=plural_twins,
            lock=None,
            lock_section="claims",
        )
        if _folded(with_drop) == _folded(without_drop):
            return True
    return False


def _folded(value: object) -> frozenset[str]:
    """Return a case-insensitive set for drop-effect comparison."""

    return frozenset(str(item).casefold() for item in value) if isinstance(value, (list, tuple)) else frozenset()


def _contains_plural(value: object) -> bool:
    """Avoid cascading lock errors when layer one rejects plural syntax."""

    if isinstance(value, str):
        return _PLURAL.search(value) is not None
    if isinstance(value, Mapping):
        return any(_contains_plural(item) for item in value.values())
    if isinstance(value, list):
        return any(_contains_plural(item) for item in value)
    return False


@layer2_check
def check_lock(tree: SourceTree) -> list[Diagnostic]:
    """Check every effective derived value without touching lexicon-off scenes."""

    diagnostics: list[Diagnostic] = []
    for file, scene, match in _match_files(tree):
        lexicon = tree.files.get("lexicon.yaml")
        if match.get("plural_twins") is not True and (_contains_plural(match) or _contains_plural(lexicon)):
            continue
        lock = tree.files.get(f"scenes/{scene}.match.lock.yaml")
        for value in derived_values(match, lexicon):
            present, locked = lock_value(lock, value)
            if not present:
                diagnostics.append(_stale_diagnostic(scene, value, "missing"))
            elif value.direct and not equivalent(value.field, value.expanded, locked):
                diagnostics.append(_stale_diagnostic(scene, value, "stale"))
            if value.direct and _drop_unused(
                value.raw, value.field, value.record_id, lexicon, match.get("plural_twins") is True
            ):
                diagnostics.append(_drop_diagnostic(file, value))
    return diagnostics
