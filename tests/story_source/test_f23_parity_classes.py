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


@dataclass(frozen=True)
class _DifferenceSeed:
    path: str
    legacy: object
    compiled: object
    difference_class: str
    needs_review: bool


def _digest(value: object) -> str:
    canonical = json.dumps(value, ensure_ascii=False, separators=(",", ":"), sort_keys=True)
    return sha256(canonical.encode("utf-8")).hexdigest()[:12]


def _seeds() -> tuple[_DifferenceSeed, ...]:
    return (
        _DifferenceSeed("knowledge[k].operations", ["first", "second"], ["second", "first"], "op_order", False),
        _DifferenceSeed("knowledge[k].requires", ["first", "second"], ["second", "first"], "condition_order", False),
        _DifferenceSeed(
            "storylets[SL].realizations",
            [{"id": "R1", "scene_id": "1A"}, {"id": "R2", "scene_id": "1A"}],
            [{"id": "R2", "scene_id": "1A"}, {"id": "R1", "scene_id": "1A"}],
            "representation",
            True,
        ),
        _DifferenceSeed("storylets[SL].title", "Legacy title", "Compiled title", "reader_only", True),
        _DifferenceSeed("world.facts[f]", ["f", "f"], ["f"], "dedupe", True),
        _DifferenceSeed("scenes[1A].prose", "same  prose", "same prose", "whitespace", True),
        _DifferenceSeed("world.entities[e].owner", "legacy", "compiled", "data_bug", True),
        _DifferenceSeed("storylets[SL].sections", "legacy section", "compiled section", "representation", True),
    )


def _review_entries(seeds: tuple[_DifferenceSeed, ...]) -> list[dict[str, str]]:
    return [
        {
            "path": seed.path,
            "class": seed.difference_class,
            "legacy": _digest(seed.legacy),
            "compiled": _digest(seed.compiled),
            "reason": f"Review the {seed.difference_class} difference.",
        }
        for seed in seeds
        if seed.needs_review and seed.difference_class != "representation"
    ]


def _field(value: object, name: str) -> object:
    if isinstance(value, dict):
        return value[name]
    return getattr(value, name)


def test_fixture_changes_only_the_parity_seed(tmp_path: Path) -> None:
    root = copy_fixture("mini_ok", tmp_path)
    baseline = load_tree(root)
    expected = deepcopy(baseline)
    changed_title = "The KMS Mark (legacy parity seed)"

    patch_source(root, "scenes/1A.yaml", "reveals[find_card].title", changed_title)
    expected["scenes/1A.yaml"]["reveals"][0]["title"] = changed_title

    mutated = load_tree(root)
    assert mutated == expected
    assert mutated != baseline


def test_parity_classes_are_classified_and_unreviewed_differences_fail(tmp_path: Path) -> None:
    story_source = require_story_source()
    clean_root = copy_fixture("mini_ok", tmp_path / "clean")
    assert story_source.check_source_tree(clean_root) == []

    seeds = _seeds()
    legacy = _PackageDump({seed.path: seed.legacy for seed in seeds})
    compiled = _PackageDump({seed.path: seed.compiled for seed in seeds})
    report = story_source.check_parity(legacy, compiled, reviews=_review_entries(seeds))
    differences = _field(report, "differences")

    assert {_field(difference, "class") for difference in differences} == {seed.difference_class for seed in seeds}
    for seed in seeds:
        difference = next(item for item in differences if _field(item, "path") == seed.path)
        assert _field(difference, "class") == seed.difference_class
        assert _field(difference, "reviewed") is (not seed.needs_review or seed.difference_class != "representation")

    summary = _field(report, "summary")
    assert _field(summary, "unreviewed") == 2
    assert _field(summary, "pass") is False
