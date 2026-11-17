"""Report pass-2 matcher overrides and enforce the one-third gate."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any

from .c_lexicon import resolve_match_value
from .reader import read_source_tree

_FIELDS = ("action_evidence", "must_convey", "leak_terms", "aliases")


def override_ratio(root: Path) -> list[dict[str, object]]:
    """Return one override-ratio row for every derived claim field."""

    tree, _ = read_source_tree(Path(root))
    rows: list[dict[str, object]] = []
    for scene_id in _scene_order(tree.files):
        match = _mapping(tree.files.get(f"scenes/{scene_id}.match.yaml"))
        if match is None:
            continue
        lexicon = tree.files.get("lexicon.yaml") if match.get("lexicon") is True else None
        claims = _mapping(match.get("claims")) or {}
        for claim_id, claim in claims.items():
            if not isinstance(claim_id, str) or not isinstance(claim, Mapping):
                continue
            for field in _FIELDS:
                value = _effective_value(match, claim, field)
                metrics = _metrics(value, field, lexicon, match.get("plural_twins") is True, claim_id)
                if metrics is not None:
                    rows.append(_row(scene_id, claim_id, field, metrics))
    return rows


def pass2_gate(root: Path) -> bool:
    """Return whether every derived matcher field stays within one third."""

    return all(row["status"] == "ok" for row in override_ratio(root))


def _scene_order(files: Mapping[str, object]) -> tuple[str, ...]:
    """Use declared story order, with sorted source files as a fallback."""

    story = _mapping(files.get("story.yaml"))
    declared = story.get("scenes") if story is not None else None
    if isinstance(declared, list):
        return tuple(scene for scene in declared if isinstance(scene, str))
    return tuple(
        sorted(
            path.removeprefix("scenes/").removesuffix(".match.yaml")
            for path in files
            if path.startswith("scenes/") and path.endswith(".match.yaml")
        )
    )


def _mapping(value: object) -> Mapping[str, Any] | None:
    """Return a string-keyed mapping or ``None``."""

    return value if isinstance(value, Mapping) else None


def _effective_value(match: Mapping[str, Any], claim: Mapping[str, Any], field: str) -> object:
    """Apply the source's shared block and claim override rules."""

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


def _metrics(value: object, field: str, lexicon: object, plural_twins: bool, claim_id: str) -> dict[str, int] | None:
    """Aggregate override counts over the derived expressions in one field."""

    expressions = _expressions(value)
    if not expressions:
        return None
    totals = {"derived": len(expressions), "expanded": 0, "added": 0, "dropped": 0}
    for expression in expressions:
        base = {key: expression[key] for key in ("first", "from") if key in expression}
        expanded = resolve_match_value(
            base,
            field=field,
            record_id=claim_id,
            lexicon=_mapping(lexicon),
            plural_twins=plural_twins,
            lock=None,
            lock_section="claims",
        )
        totals["expanded"] += (
            len(expanded) if isinstance(expanded, Sequence) and not isinstance(expanded, (str, bytes)) else 0
        )
        totals["added"] += _entry_count(expression.get("add"))
        totals["dropped"] += _entry_count(expression.get("drop"))
    return totals


def _expressions(value: object) -> tuple[Mapping[str, Any], ...]:
    """Find derived mappings at the field's supported nesting level."""

    if isinstance(value, Mapping):
        return (value,)
    if isinstance(value, list):
        return tuple(item for item in value if isinstance(item, Mapping))
    return ()


def _entry_count(value: object) -> int:
    """Count authored override entries without expanding plural twins."""

    return sum(isinstance(item, str) for item in value) if isinstance(value, list) else 0


def _row(scene_id: str, claim_id: str, field: str, metrics: Mapping[str, int]) -> dict[str, object]:
    """Build a stable report row from aggregate counts."""

    expanded = metrics["expanded"]
    ratio = (metrics["added"] + metrics["dropped"]) / expanded if expanded else 0
    return {
        "scene": scene_id,
        "claim": claim_id,
        "field": field,
        "derived": metrics["derived"],
        "expanded": expanded,
        "added": metrics["added"],
        "dropped": metrics["dropped"],
        "ratio": ratio,
        "status": "over" if ratio > 1 / 3 else "ok",
    }
