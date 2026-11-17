"""Canonical StoryPackage parity comparison and review-file loading."""

from __future__ import annotations

import hashlib
import json
import re
from collections import Counter
from collections.abc import Mapping
from pathlib import Path
from typing import Any

import yaml

_SCENE = re.compile(r"(?:scenes|scene_frames|pacing|deliveries)\[([^]]+)\]")
_SCENE_ID = re.compile(r"(?:^|[^A-Z0-9])([1-9][A-Z])(?:[^A-Z0-9]|$)")
_AUTO_CLASSES = {"op_order", "condition_order", "collection_order"}
_CONDITION_FIELDS = {"requires", "when", "triggers", "activation_conditions"}
_READER_FIELDS = {"prose", "title", "earliest_turn", "target_turn", "latest_turn"}
_COLLECTION_FIELDS = {"realizations", "events", "facts", "knowledge", "deliveries", "storylets", "scenes"}
_MAPPING_FIELDS = {
    "facts",
    "fact_effects",
    "sections",
    "beats",
    "by_id",
    "facts_to_knowledge",
    "source_to_knowledge",
    "scene_to_candidates",
    "alias_to_knowledge",
    "audience_to_known_terms",
    "prerequisite_dependents",
    "entity_alias_to_entities",
    "term_to_knowledge",
    "leak_term_to_knowledge",
    "disclosure_guards",
}


def load_review_file(path: Path) -> dict[str, Any]:
    """Load and validate one schema-1 YAML parity review mapping."""

    with Path(path).open(encoding="utf-8") as stream:
        review = yaml.safe_load(stream)
    if not isinstance(review, dict) or review.get("schema") != 1:
        raise ValueError("parity review must be a schema-1 mapping")
    if not isinstance(review.get("scene"), str):
        raise ValueError("parity review scene must be a string")
    differences = review.get("differences")
    if not isinstance(differences, list) or not all(isinstance(entry, dict) for entry in differences):
        raise ValueError("parity review differences must be a list of mappings")
    return review


def check_parity(legacy: Any, compiled: Any, *, reviews: Any = None) -> dict[str, Any]:
    """Compare two packages and return section-9 differences and summary."""

    left = _canonical(legacy)
    right = _canonical(compiled)
    review_entries = _review_entries(reviews)
    differences: list[dict[str, Any]] = []
    _compare(left, right, "", differences, left)
    for difference in differences:
        difference["reviewed"] = _is_reviewed(difference, review_entries)
    knowledge_changed = left.get("knowledge_indexes") != right.get("knowledge_indexes")
    summary = _summary(differences, _record_count(left), knowledge_changed)
    return {"differences": differences, "summary": summary}


def _canonical(package: Any) -> dict[str, Any]:
    """Return the contract's JSON-mode package dump."""

    dumped = package.model_dump(mode="json", by_alias=True)
    if not isinstance(dumped, dict):
        raise TypeError("StoryPackage.model_dump() must return a mapping")
    return dumped


def _compare(left: Any, right: Any, path: str, output: list[dict[str, Any]], root: Mapping[str, Any]) -> None:
    if left == right:
        return
    if path == "knowledge_indexes":
        _add_difference(output, path, left, right, "representation")
        return
    if isinstance(left, dict) and isinstance(right, dict):
        _compare_mappings(left, right, path, output, root)
        return
    if isinstance(left, list) and isinstance(right, list):
        _compare_lists(left, right, path, output, root)
        return
    _add_difference(output, path, left, right, _difference_class(path, left, right, root))


def _compare_mappings(
    left: Mapping[str, Any], right: Mapping[str, Any], path: str, output: list[dict[str, Any]], root: Mapping[str, Any]
) -> None:
    keys = sorted(set(left) | set(right))
    for key in keys:
        child = _part(path, key)
        if key not in left or key not in right:
            _add_difference(
                output,
                child,
                left.get(key),
                right.get(key),
                _difference_class(child, left.get(key), right.get(key), root),
            )
        else:
            _compare(left[key], right[key], child, output, root)


def _compare_lists(
    left: list[Any], right: list[Any], path: str, output: list[dict[str, Any]], root: Mapping[str, Any]
) -> None:
    if _same_multiset(left, right):
        if left != right:
            _add_difference(output, path, left, right, _difference_class(path, left, right, root))
        return
    if _dedupe_equivalent(left, right) and path.startswith("world.facts"):
        _add_difference(output, path, left, right, "dedupe")
        return
    keyed_left = _keyed_items(left)
    keyed_right = _keyed_items(right)
    if keyed_left is not None and keyed_right is not None and set(keyed_left) == set(keyed_right):
        if list(keyed_left) != list(keyed_right):
            difference_class = (
                "collection_order" if _collection_order_proof(left, right, path, root) else "representation"
            )
            _add_difference(output, path, left, right, difference_class)
            return
        for key in sorted(keyed_left):
            _compare(keyed_left[key], keyed_right[key], _part(path, key), output, root)
        return
    if _list_is_order_only(left, right):
        _add_difference(output, path, left, right, _difference_class(path, left, right, root))
        return
    _add_difference(output, path, left, right, _difference_class(path, left, right, root))


def _difference_class(path: str, left: Any, right: Any, root: Mapping[str, Any] | None = None) -> str:
    field = path.rsplit(".", 1)[-1]
    if isinstance(left, str) and isinstance(right, str) and _squash(left) == _squash(right):
        return "whitespace"
    if field in _CONDITION_FIELDS and _list_is_order_only(left, right):
        return "condition_order"
    if field in {"operations", "costs"} and _operation_order_proof(left, right, root):
        return "op_order"
    if field == "facts" and path.startswith("world.") and not _collection_order_proof(left, right, path, root):
        return "representation"
    if field in _COLLECTION_FIELDS and _list_is_order_only(left, right):
        return "collection_order"
    if _reader_path(path):
        return "reader_only"
    if field in {"owner", "owners", "source_owner"}:
        return "data_bug"
    return "representation"


def _add_difference(output: list[dict[str, Any]], path: str, left: Any, right: Any, difference_class: str) -> None:
    output.append(
        {
            "scene": _scene_for(path),
            "path": path.lstrip("."),
            "class": difference_class,
            "reviewed": False,
            "legacy": _digest(left),
            "compiled": _digest(right),
        }
    )


def _review_entries(reviews: Any) -> list[Mapping[str, Any]]:
    if reviews is None:
        return []
    entries = reviews.get("differences", []) if isinstance(reviews, Mapping) else reviews
    if not isinstance(entries, list):
        return []
    return [entry for entry in entries if isinstance(entry, Mapping)]


def _is_reviewed(difference: Mapping[str, Any], reviews: list[Mapping[str, Any]]) -> bool:
    if difference["path"] == "knowledge_indexes":
        return False
    if difference["class"] in _AUTO_CLASSES:
        return True
    return any(
        entry.get("path") == difference["path"]
        and entry.get("class") == difference["class"]
        and entry.get("legacy") == difference["legacy"]
        and entry.get("compiled") == difference["compiled"]
        for entry in reviews
    )


def _summary(differences: list[Mapping[str, Any]], records: int, knowledge_changed: bool) -> dict[str, Any]:
    auto = sum(item["class"] in _AUTO_CLASSES and item["reviewed"] for item in differences)
    reviewed = sum(item["reviewed"] and item["class"] not in _AUTO_CLASSES for item in differences)
    unreviewed = len(differences) - auto - reviewed
    return {
        "records": records,
        "differences": len(differences),
        "auto": auto,
        "reviewed": reviewed,
        "unreviewed": unreviewed,
        "pass": unreviewed == 0 and not knowledge_changed,
    }


def _digest(value: Any) -> str:
    encoded = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()[:12]


def _same_multiset(left: list[Any], right: list[Any]) -> bool:
    return Counter(_json_value(item) for item in left) == Counter(_json_value(item) for item in right)


def _list_is_order_only(left: Any, right: Any) -> bool:
    return isinstance(left, list) and isinstance(right, list) and _same_multiset(left, right)


def _dedupe_equivalent(left: list[Any], right: list[Any]) -> bool:
    return set(_json_value(item) for item in left) == set(_json_value(item) for item in right) and left != right


def _operation_order_proof(left: Any, right: Any, root: Mapping[str, Any] | None = None) -> bool:
    if not _list_is_order_only(left, right):
        return False
    fact_ids = [item.get("fact_id") if isinstance(item, dict) else item for item in left]
    if len(fact_ids) != len(set(_json_value(item) for item in fact_ids)):
        return False
    return _facts_have_disjoint_effects(fact_ids, root)


def _keyed_items(value: list[Any]) -> dict[str, Any] | None:
    keys = [_item_key(item) for item in value]
    if any(key is None for key in keys) or len(set(keys)) != len(keys):
        return None
    return dict(zip(keys, value, strict=False))


def _item_key(item: Any) -> str | None:
    if not isinstance(item, dict):
        return None
    for field in ("id", "claim_id", "fact_id", "scene_id"):
        if field in item and isinstance(item[field], str):
            return item[field]
    metadata = item.get("metadata")
    if isinstance(metadata, dict) and isinstance(metadata.get("scene_id"), str):
        return metadata["scene_id"]
    return None


def _collection_order_proof(
    left: list[Any], right: list[Any], path: str, root: Mapping[str, Any] | None = None
) -> bool:
    if path == "world.facts":
        return _facts_keep_effect_order(left, right, root)
    if path.rsplit(".", 1)[-1] in _COLLECTION_FIELDS:
        return True
    scenes_left = _scene_sequence(left)
    scenes_right = _scene_sequence(right)
    return scenes_left is not None and scenes_left == scenes_right


def _facts_have_disjoint_effects(fact_ids: list[Any], root: Mapping[str, Any] | None) -> bool:
    if not root:
        return True
    effects = root.get("world", {}).get("fact_effects", {})
    targets = [_effect_targets(effects.get(fact_id, ())) for fact_id in fact_ids]
    return all(not (left & right) for index, left in enumerate(targets) for right in targets[index + 1 :])


def _effect_targets(effects: Any) -> set[str]:
    if not isinstance(effects, list):
        return set()
    target_fields = {"move", "parent", "reveal", "accompany", "with", "set_axis"}
    return {
        str(effect[field])
        for effect in effects
        if isinstance(effect, dict)
        for field in target_fields
        if effect.get(field) is not None
    }


def _facts_keep_effect_order(left: list[Any], right: list[Any], root: Mapping[str, Any] | None) -> bool:
    if not root:
        return True
    effects = root.get("world", {}).get("fact_effects", {})
    sensitive_pairs = {
        frozenset((left_id, right_id))
        for index, left_id in enumerate(left)
        for right_id in left[index + 1 :]
        if _effect_targets(effects.get(left_id, ())) & _effect_targets(effects.get(right_id, ()))
    }
    return all(_ordered_pair(left, right, pair) for pair in sensitive_pairs)


def _ordered_pair(left: list[Any], right: list[Any], pair: frozenset[Any]) -> bool:
    left_positions = [left.index(item) for item in pair]
    right_positions = [right.index(item) for item in pair]
    return (left_positions[0] < left_positions[1]) == (right_positions[0] < right_positions[1])


def _scene_sequence(items: list[Any]) -> list[list[str]] | None:
    if not all(isinstance(item, dict) and isinstance(item.get("scene_id"), str) for item in items):
        return None
    by_scene: dict[str, list[str]] = {}
    for item in items:
        by_scene.setdefault(item["scene_id"], []).append(_item_key(item) or "")
    return [by_scene[key] for key in sorted(by_scene)]


def _reader_path(path: str) -> bool:
    field = path.rsplit(".", 1)[-1]
    return field in _READER_FIELDS and (path.startswith("scenes[") or path.startswith("storylets["))


def _scene_for(path: str) -> str:
    match = _SCENE.search(path)
    if match:
        return match.group(1)
    match = _SCENE_ID.search(path)
    return match.group(1) if match else "*"


def _part(path: str, key: Any) -> str:
    if not path:
        return str(key)
    if path.rsplit(".", 1)[-1] in _MAPPING_FIELDS:
        return f"{path}[{key}]"
    return f"{path}.{key}"


def _squash(value: str) -> str:
    return " ".join(value.split())


def _json_value(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def _record_count(value: Any) -> int:
    if isinstance(value, dict) and value and all("[" in key or "." in key for key in value):
        return len(value)
    return max(1, _count_records(value))


def _count_records(value: Any) -> int:
    if isinstance(value, list):
        return sum(1 if _item_key(item) else _count_records(item) for item in value)
    if isinstance(value, dict):
        if _item_key(value):
            return 1 + sum(_count_records(item) for item in value.values())
        return sum(_count_records(item) for item in value.values())
    return 0
