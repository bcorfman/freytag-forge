from __future__ import annotations

import json
from copy import deepcopy
from dataclasses import dataclass
from hashlib import sha256
from pathlib import Path

from tests.story_source.helpers import copy_fixture, load_tree, patch_source, require_story_source


@dataclass(frozen=True)
class _PackageDump:
    records: dict[str, object]

    def model_dump(self, **_kwargs: object) -> dict[str, object]:
        return self.records


def _digest(value: object) -> str:
    canonical = json.dumps(value, ensure_ascii=False, separators=(",", ":"), sort_keys=True)
    return sha256(canonical.encode("utf-8")).hexdigest()[:12]


def _field(value: object, name: str) -> object:
    if isinstance(value, dict):
        return value[name]
    return getattr(value, name)


def test_fixture_changes_only_the_reviewed_title(tmp_path: Path) -> None:
    root = copy_fixture("mini_ok", tmp_path)
    baseline = load_tree(root)
    expected = deepcopy(baseline)
    changed_title = "The KMS Mark (review digest seed)"

    patch_source(root, "scenes/1A.yaml", "reveals[find_card].title", changed_title)
    expected["scenes/1A.yaml"]["reveals"][0]["title"] = changed_title

    mutated = load_tree(root)
    assert mutated == expected
    assert mutated != baseline


def test_stale_compiled_digest_is_unreviewed_and_fails(tmp_path: Path) -> None:
    story_source = require_story_source()
    clean_root = copy_fixture("mini_ok", tmp_path / "clean")
    assert story_source.check_source_tree(clean_root) == []

    path = "storylets[SL-1A-E].title"
    legacy_value = "The KMS Mark"
    compiled_value = "The KMS Mark (compiled)"
    stale_review = {
        "path": path,
        "class": "reader_only",
        "legacy": _digest(legacy_value),
        "compiled": _digest("The KMS Mark (old compiled value)"),
        "reason": "The title is intentionally reviewed.",
    }
    report = story_source.check_parity(
        _PackageDump({path: legacy_value}),
        _PackageDump({path: compiled_value}),
        reviews=[stale_review],
    )

    differences = _field(report, "differences")
    difference = next(item for item in differences if _field(item, "path") == path)
    assert _field(difference, "class") == "reader_only"
    assert _field(difference, "reviewed") is False
    summary = _field(report, "summary")
    assert _field(summary, "unreviewed") == 1
    assert _field(summary, "pass") is False
