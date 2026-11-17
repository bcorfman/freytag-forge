"""Small deterministic converters for conditions, effects, audiences, and passages."""

from __future__ import annotations

import re
from collections.abc import Mapping
from typing import Any

from storygame.story_package.models import Audience, FactPredicate, RouteOperation

from .c_lexicon import resolve_match_value

_PART = re.compile(r"(?<!\{)\{([a-z][a-z0-9_]*)\}(?!\})")


def predicates(value: object) -> tuple[FactPredicate, ...]:
    """Convert a mapping or list of fact conditions without changing order."""

    if isinstance(value, Mapping):
        return tuple(FactPredicate(fact_id=fact_id, equals=state) for fact_id, state in value.items())
    if isinstance(value, list):
        return tuple(FactPredicate(fact_id=fact_id, equals=True) for fact_id in value)
    return ()


def operations(value: object) -> tuple[RouteOperation, ...]:
    """Convert declarative fact effects to route operations in mapping order."""

    if not isinstance(value, Mapping):
        return ()
    converted: list[RouteOperation] = []
    for fact_id, state in value.items():
        if state == "retract":
            converted.append(RouteOperation(op="retract", fact_id=fact_id, value=True))
        else:
            converted.append(RouteOperation(op="assert", fact_id=fact_id, value=state))
    return tuple(converted)


def expand(value: str | None, parts: Mapping[str, str]) -> str | None:
    """Paste named parts into a passage, retaining escaped literal braces."""

    if value is None:
        return None

    def replace(match: re.Match[str]) -> str:
        return parts[match.group(1)]

    return _PART.sub(replace, value)


def audience(value: object) -> Audience:
    """Convert the compact public or scoped audience form."""

    if value == "public":
        return Audience(kind="public", player_visible=True)
    if isinstance(value, Mapping):
        data: dict[str, Any] = dict(value)
        data.setdefault("character_ids", ())
        data.setdefault("player_visible", data.get("kind") == "public")
        return Audience.model_validate(data)
    return Audience(kind="world_only", player_visible=False)


def tuple_strings(value: object) -> tuple[str, ...]:
    """Return a stable tuple for an optional string list."""

    return tuple(value) if isinstance(value, list) else ()


def matcher_groups(value: object) -> tuple[tuple[str, ...], ...]:
    """Convert written matcher groups without sorting or deduplicating them."""

    if not isinstance(value, list):
        return ()
    return tuple(tuple(group) for group in value)


def effective_match(
    match: Mapping[str, Any],
    claim_id: str,
    field: str,
    *,
    lexicon: Mapping[str, Any] | None = None,
    lock: Mapping[str, Any] | None = None,
) -> object:
    """Resolve a match entry through one non-chaining shared block."""

    claims = match.get("claims", {})
    shared = match.get("shared", {})
    claim = claims.get(claim_id, {}) if isinstance(claims, Mapping) else {}
    base: dict[str, Any] = {}
    if isinstance(shared, Mapping):
        use = claim.get("use") if isinstance(claim, Mapping) else None
        if isinstance(use, str) and isinstance(shared.get(use), Mapping):
            base.update(shared[use])
        if field in shared:
            base[field] = shared[field]
    if isinstance(claim, Mapping) and field in claim:
        override = claim[field]
        if field == "leak_terms" and isinstance(override, Mapping) and "add" in override:
            original = base.get(field, [])
            if isinstance(original, Mapping):
                merged = dict(original)
                merged["add"] = [*merged.get("add", ()), *override["add"]]
                base[field] = merged
            else:
                base[field] = [*original, *override["add"]]
        else:
            base[field] = override
    return resolve_match_value(
        base.get(field),
        field=field,
        record_id=claim_id,
        lexicon=lexicon,
        plural_twins=match.get("plural_twins") is True,
        lock=lock,
        lock_section="claims",
    )
