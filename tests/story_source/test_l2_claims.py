"""Focused failing-case tests for the claims and scene-scope layer-two checks."""

# NOTE: F14 treats a compiled manifest entry plus its declarative scene file as
# the two ownership sources; this test follows that fixture contract wording.

from pathlib import Path

from tests.story_source.helpers import copy_fixture, patch_source, require_story_source


def _assert_clean(story_source: object, root: Path) -> None:
    """Keep every mutation test honest about the unmutated fixture."""

    assert story_source.check_source_tree(root) == []


def test_claim_authorized_rejects_subset_outside_variant_commits(tmp_path: Path) -> None:
    story_source = require_story_source()
    clean = copy_fixture("mini_ok", tmp_path / "clean")
    _assert_clean(story_source, clean)
    root = copy_fixture("mini_ok", tmp_path / "mutated")
    patch_source(root, "scenes/1A.yaml", "reveals[find_card].variants.quiet.commits_subset", {"card_challenged": True})

    diagnostics = story_source.check_source_tree(root)

    assert [item.name for item in diagnostics] == ["L2.claim_authorized"]
    assert diagnostics[0].field == "commits_subset"
    assert "k_sl_1a_b_r0" in diagnostics[0].message


def test_override_add_only_rejects_plain_shared_leak_override(tmp_path: Path) -> None:
    story_source = require_story_source()
    clean = copy_fixture("mini_ok", tmp_path / "clean")
    _assert_clean(story_source, clean)
    root = copy_fixture("mini_ok", tmp_path / "mutated")
    patch_source(root, "scenes/1A.match.yaml", "claims.k_sl_1a_b_r0.leak_terms", ["memory card"])

    diagnostics = story_source.check_source_tree(root)

    assert [item.name for item in diagnostics] == ["L2.override_add_only"]
    assert diagnostics[0].field == "leak_terms"
    assert "k_sl_1a_b_r0" in diagnostics[0].message


def test_match_coverage_rejects_a_claim_without_a_match_entry(tmp_path: Path) -> None:
    story_source = require_story_source()
    clean = copy_fixture("mini_ok", tmp_path / "clean")
    _assert_clean(story_source, clean)
    root = copy_fixture("mini_ok", tmp_path / "mutated")
    from tests.story_source.helpers import DELETE

    patch_source(root, "scenes/1A.match.yaml", "claims.k_sl_1a_b_r0", DELETE)
    diagnostics = story_source.check_source_tree(root)

    matches = [item for item in diagnostics if item.name == "L2.match_coverage"]
    assert len(matches) == 1
    assert matches[0].field == "claims"
    assert "k_sl_1a_b_r0" in matches[0].message


def test_incident_observes_outcomes_rejects_missing_outcome_claim(tmp_path: Path) -> None:
    story_source = require_story_source()
    clean = copy_fixture("mini_ok", tmp_path / "clean")
    _assert_clean(story_source, clean)
    root = copy_fixture("mini_ok", tmp_path / "mutated")
    patch_source(root, "scenes/2C.yaml", "incidents[i_2c_rebecca_corridor].observed_by", ["k_sl_2c_c_r1"])

    diagnostics = story_source.check_source_tree(root)

    matches = [item for item in diagnostics if item.name == "L2.incident_observes_outcomes"]
    assert {item.field for item in matches} == {"observed_by"}
    assert all("i_2c_rebecca_corridor" in item.message for item in matches)


def test_scene_scope_rejects_reach_outside_scene_items(tmp_path: Path) -> None:
    story_source = require_story_source()
    clean = copy_fixture("mini_ok", tmp_path / "clean")
    _assert_clean(story_source, clean)
    root = copy_fixture("mini_ok", tmp_path / "mutated")
    patch_source(root, "scenes/1A.yaml", "reveals[find_card].reach", ["not_a_scene_item"])

    diagnostics = story_source.check_source_tree(root)

    matches = [item for item in diagnostics if item.name == "L2.scene_scope"]
    assert len(matches) == 1
    assert matches[0].field == "reach"
    assert "not_a_scene_item" in matches[0].message


def test_ending_scene_rejects_ending_before_last_story_scene(tmp_path: Path) -> None:
    story_source = require_story_source()
    clean = copy_fixture("mini_ok", tmp_path / "clean")
    _assert_clean(story_source, clean)
    root = copy_fixture("mini_ok", tmp_path / "mutated")
    patch_source(
        root,
        "scenes/1A.yaml",
        "ending",
        {"when": [], "text": "Too soon.", "marker": "early"},
    )

    diagnostics = story_source.check_source_tree(root)

    matches = [item for item in diagnostics if item.name == "L2.ending_scene"]
    assert len(matches) == 1
    assert matches[0].field == "ending"
    assert "1A" in matches[0].message


def test_ownership_rejects_compiled_scene_with_source_definition(tmp_path: Path) -> None:
    story_source = require_story_source()
    clean = copy_fixture("mini_ok", tmp_path / "clean")
    _assert_clean(story_source, clean)
    root = copy_fixture("mini_ok", tmp_path / "mutated")
    (root / "ownership.yaml").write_text(
        "schema: 1\ncatalog: legacy\nscenes:\n  1A: compiled\n",
        encoding="utf-8",
    )

    diagnostics = story_source.check_source_tree(root)

    matches = [item for item in diagnostics if item.name == "L2.ownership"]
    assert len(matches) == 1
    assert matches[0].file == "ownership.yaml"
    assert matches[0].field == "scenes"
    assert "ownership.yaml" in matches[0].message
    assert "scenes/1A.yaml" in matches[0].message
