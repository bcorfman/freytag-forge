"""Core tests for pass-two lock generation, comparison, and expansion."""

from __future__ import annotations

import json
from pathlib import Path

import pytest
import yaml

from storygame.story_source.lock import equivalent, expand_scene, lock_scene
from tests.story_source.helpers import copy_fixture, load_tree, patch_source, require_story_source


def _set_lexicon(root: Path, enabled: bool = True) -> None:
    """Enable lexicon expansion in the fixture's first scene."""

    path = root / "scenes/1A.match.yaml"
    document = load_tree(root)["scenes/1A.match.yaml"]
    document = {"schema": document["schema"], "scene": document["scene"], "lexicon": enabled}
    document.update(
        {key: value for key, value in load_tree(root)["scenes/1A.match.yaml"].items() if key not in document}
    )
    path.write_text(yaml.safe_dump(document, sort_keys=False, width=10_000, allow_unicode=True), encoding="utf-8")


def _write_lexicon(root: Path) -> None:
    """Write the small lexicon used by the lock tests."""

    document = {
        "schema": 1,
        "entities": {
            "memory_card": {
                "names": ["memory card", "card", "Michelle's card", "the card", "new card name"],
                "hidden_names": ["hidden card", "hidden memory card"],
            }
        },
        "concepts": {},
        "verb_classes": {},
    }
    (root / "lexicon.yaml").write_text(
        yaml.safe_dump(document, sort_keys=False, width=10_000, allow_unicode=True), encoding="utf-8"
    )


def _derived_fixture(tmp_path: Path) -> Path:
    """Build a lexicon-enabled fixture with a shared derived matcher."""

    root = copy_fixture("mini_ok", tmp_path / "derived")
    _set_lexicon(root)
    patch_source(root, "scenes/1A.match.yaml", "shared.drawer_search.must_convey", [{"from": ["$memory_card.all"]}])
    _write_lexicon(root)
    return root


def _stale_fixture(tmp_path: Path) -> Path:
    """Build the F20 stale-alias fixture without changing the gate test."""

    root = copy_fixture("mini_ok", tmp_path / "stale")
    _set_lexicon(root)
    patch_source(root, "scenes/1A.match.yaml", "claims.k_sl_1a_b_r0.aliases", {"from": ["$memory_card"]})
    _write_lexicon(root)
    lock = {
        "schema": 1,
        "scene": "1A",
        "generated_by": "story lock",
        "claims": {"k_sl_1a_b_r0": {"aliases": ["memory card", "card", "Michelle's card", "the card"]}},
        "deliveries": {},
    }
    (root / "scenes/1A.match.lock.yaml").write_text(
        yaml.safe_dump(lock, sort_keys=False, width=10_000, allow_unicode=True), encoding="utf-8"
    )
    return root


def test_equivalent_uses_each_field_contract() -> None:
    """Each matcher field gets one semantic match and one rejected match."""

    assert equivalent("action_evidence", [["look"]], [["inspect"]])
    assert not equivalent("action_evidence", [["look"]], [["read"]])
    assert equivalent("must_convey", [["Memory card", "CARD"]], [["Memory card", "card"]])
    assert not equivalent("must_convey", [["Memory card"]], [["card"]])
    assert equivalent("leak_terms", ["Memory Card"], ["memory card"])
    assert not equivalent("leak_terms", (), [])
    assert equivalent("aliases", ["one", "two"], ["one", "two"])
    assert not equivalent("aliases", ["one", "two"], ["two", "one"])


def test_adopt_refuses_a_non_equivalent_existing_lock(tmp_path: Path) -> None:
    """Adoption is atomic when an existing generated list disagrees."""

    root = _stale_fixture(tmp_path)
    path = root / "scenes/1A.match.lock.yaml"
    before = path.read_bytes()
    report = lock_scene(root, "1A", adopt=True)
    assert report.changed == []
    assert report.mismatches and "add:" in report.mismatches[0] and "drop:" in report.mismatches[0]
    assert path.read_bytes() == before


def test_adopt_preserves_the_pass_one_package(tmp_path: Path) -> None:
    """A first lock generated from equivalent expansions does not alter bytes."""

    story_source = require_story_source()
    baseline = copy_fixture("mini_ok", tmp_path / "baseline")
    from tests.story_source.test_f19_lexicon_roundtrip import _build_roundtrip_fixture

    root = copy_fixture("mini_ok", tmp_path / "derived")
    _build_roundtrip_fixture(root)
    expected = story_source.compile_source_tree(baseline)
    report = lock_scene(root, "1A", adopt=True)
    assert report.mismatches == []
    assert story_source.compile_source_tree(root) == expected


def test_expand_scene_compiles_without_lexicon(tmp_path: Path) -> None:
    """Materialized lock values keep the compiled package stable."""

    story_source = require_story_source()
    from tests.story_source.test_f19_lexicon_roundtrip import _build_roundtrip_fixture

    root = copy_fixture("mini_ok", tmp_path / "expanded")
    _build_roundtrip_fixture(root)
    expected = story_source.compile_source_tree(_baseline_for(root, tmp_path))
    lock_scene(root, "1A")
    expand_scene(root, "1A")
    assert load_tree(root)["scenes/1A.match.yaml"]["lexicon"] is False
    (root / "lexicon.yaml").unlink()
    assert _canonical(story_source.compile_source_tree(root)) == _canonical(expected)


def _baseline_for(root: Path, tmp_path: Path) -> Path:
    """Return a clean fixture beside a mutated fixture."""

    return copy_fixture("mini_ok", tmp_path / f"baseline-{root.name}")


def _canonical(package: object) -> str:
    """Serialize a package using the parity contract's canonical model form."""

    return json.dumps(package.model_dump(mode="json", by_alias=True), sort_keys=True)


def test_stale_lock_names_claim_and_field(tmp_path: Path) -> None:
    """The real layer-two check reports F20's stale aliases location."""

    story_source = require_story_source()
    root = _stale_fixture(tmp_path)
    diagnostics = story_source.check_source_tree(root)
    stale = [diagnostic for diagnostic in diagnostics if diagnostic.name == "L2.lock_stale"]
    assert len(stale) == 1
    assert stale[0].file == "scenes/1A.match.lock.yaml"
    assert stale[0].field == "aliases"
    assert "k_sl_1a_b_r0" in stale[0].message
    with pytest.raises(story_source.SourceError):
        story_source.compile_source_tree(root)


def test_unused_drop_is_reported_after_lock_generation(tmp_path: Path) -> None:
    """Layer two reports a drop that removes no lexicon expansion."""

    story_source = require_story_source()
    root = copy_fixture("mini_ok", tmp_path / "unused-drop")
    _set_lexicon(root)
    patch_source(
        root,
        "scenes/1A.match.yaml",
        "claims.k_sl_1a_b_r0.aliases",
        {"from": ["$memory_card"], "drop": ["not present"]},
    )
    _write_lexicon(root)
    lock_scene(root, "1A")
    diagnostics = story_source.check_source_tree(root)
    assert [diagnostic.name for diagnostic in diagnostics] == ["L2.drop_unused"]
