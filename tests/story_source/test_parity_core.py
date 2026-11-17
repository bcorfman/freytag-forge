"""Focused tests for canonical parity reports and review matching."""

from __future__ import annotations

import json
from dataclasses import dataclass
from hashlib import sha256
from pathlib import Path

from storygame.story_source.parity import check_parity, load_review_file


@dataclass(frozen=True)
class _PackageDump:
    records: dict[str, object]

    def model_dump(self, **_kwargs: object) -> dict[str, object]:
        return self.records


def _digest(value: object) -> str:
    encoded = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return sha256(encoded).hexdigest()[:12]


def test_identical_packages_have_no_differences_and_pass() -> None:
    package = _PackageDump({"story_id": "story", "knowledge_indexes": {"known": ["fact"]}})

    report = check_parity(package, package)

    assert report["differences"] == []
    assert report["summary"]["pass"] is True
    assert report["summary"]["unreviewed"] == 0


def test_stale_review_digest_is_unreviewed() -> None:
    path = "storylets[SL-1A-E].title"
    legacy_value = "Legacy title"
    compiled_value = "Compiled title"
    stale_review = {
        "schema": 1,
        "scene": "1A",
        "differences": [
            {
                "path": path,
                "class": "reader_only",
                "legacy": _digest(legacy_value),
                "compiled": _digest("old compiled title"),
                "reason": "The title is intentionally reviewed.",
            }
        ],
    }

    report = check_parity(
        _PackageDump({path: legacy_value}),
        _PackageDump({path: compiled_value}),
        reviews=stale_review,
    )

    difference = report["differences"][0]
    assert difference["class"] == "reader_only"
    assert difference["reviewed"] is False
    assert report["summary"]["unreviewed"] == 1
    assert report["summary"]["pass"] is False


def test_load_review_file_reads_schema_one_mapping(tmp_path: Path) -> None:
    path = tmp_path / "review.yaml"
    path.write_text("schema: 1\nscene: 1A\ndifferences: []\n", encoding="utf-8")

    assert load_review_file(path) == {"schema": 1, "scene": "1A", "differences": []}


def test_knowledge_indexes_difference_cannot_be_reviewed() -> None:
    legacy = _PackageDump({"knowledge_indexes": {"known": ["fact"]}})
    compiled = _PackageDump({"knowledge_indexes": {"known": ["other_fact"]}})

    report = check_parity(legacy, compiled)

    assert report["differences"][0]["path"] == "knowledge_indexes"
    assert report["differences"][0]["reviewed"] is False
    assert report["summary"]["pass"] is False
