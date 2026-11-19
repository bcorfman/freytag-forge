"""Parity classification for keyed collection order within scenes."""

from __future__ import annotations

import json
from dataclasses import dataclass
from hashlib import sha256

from storygame.story_source.parity import check_parity


@dataclass(frozen=True)
class _PackageDump:
    records: dict[str, object]

    def model_dump(self, **_kwargs: object) -> dict[str, object]:
        return self.records


def _digest(value: object) -> str:
    encoded = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return sha256(encoded).hexdigest()[:12]


def _report(legacy: list[dict[str, object]], compiled: list[dict[str, object]], reviews=None) -> dict[str, object]:
    return check_parity(_PackageDump({"storylets": legacy}), _PackageDump({"storylets": compiled}), reviews=reviews)


def test_cross_scene_move_is_collection_order() -> None:
    legacy = [
        {"id": "a1", "scene_id": "1A"},
        {"id": "b1", "scene_id": "1B"},
        {"id": "a2", "scene_id": "1A"},
    ]
    compiled = [legacy[1], legacy[0], legacy[2]]

    report = _report(legacy, compiled)

    assert report["differences"][0]["class"] == "collection_order"
    assert report["differences"][0]["reviewed"] is True
    assert report["summary"]["pass"] is True


def test_same_scene_swap_is_representation_and_unreviewed() -> None:
    legacy = [{"id": "a1", "scene_id": "1A"}, {"id": "a2", "scene_id": "1A"}]
    compiled = [legacy[1], legacy[0]]

    report = _report(legacy, compiled)

    assert report["differences"][0]["class"] == "representation"
    assert report["differences"][0]["reviewed"] is False
    assert report["summary"]["unreviewed"] == 1
    assert report["summary"]["pass"] is False


def test_same_scene_swap_with_matching_review_is_reviewed() -> None:
    legacy = [{"id": "a1", "scene_id": "1A"}, {"id": "a2", "scene_id": "1A"}]
    compiled = [legacy[1], legacy[0]]
    reviews = {
        "schema": 1,
        "scene": "1A",
        "differences": [
            {
                "path": "storylets",
                "class": "representation",
                "legacy": _digest(legacy),
                "compiled": _digest(compiled),
                "reason": "The source order is intentionally explicit.",
            }
        ],
    }

    report = _report(legacy, compiled, reviews=reviews)

    assert report["differences"][0]["reviewed"] is True
    assert report["summary"]["unreviewed"] == 0
    assert report["summary"]["pass"] is True
