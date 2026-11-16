from __future__ import annotations

from pathlib import Path

import pytest
import yaml

from tests.story_source.helpers import DELETE, copy_fixture, load_tree, patch_source, require_story_source


def test_fixture_copies_and_loads(tmp_path: Path) -> None:
    root = copy_fixture("mini_ok", tmp_path)
    tree = load_tree(root)

    assert set(tree) == {
        "story.yaml",
        "catalog.yaml",
        "scenes/1A.yaml",
        "scenes/1A.match.yaml",
        "scenes/2C.yaml",
        "scenes/2C.match.yaml",
    }


def test_every_yaml_file_starts_with_schema(tmp_path: Path) -> None:
    root = copy_fixture("mini_ok", tmp_path)
    tree = load_tree(root)

    for document in tree.values():
        assert isinstance(document, dict)
        assert list(document)[0] == "schema"
        assert document["schema"] == 1


def test_patch_helper_round_trips_and_deletes(tmp_path: Path) -> None:
    root = copy_fixture("mini_ok", tmp_path)

    patch_source(root, "scenes/1A.yaml", "reveals[find_card].variants.quiet.says", "new text")
    patched = load_tree(root)["scenes/1A.yaml"]
    assert patched["reveals"][0]["variants"]["quiet"]["says"] == "new text"

    patch_source(root, "scenes/1A.yaml", "reveals[find_card].variants.quiet.says", DELETE)
    patched = load_tree(root)["scenes/1A.yaml"]
    assert "says" not in patched["reveals"][0]["variants"]["quiet"]


def test_patch_helper_selects_by_id_and_index_and_adds(tmp_path: Path) -> None:
    root = copy_fixture("mini_ok", tmp_path)

    patch_source(root, "scenes/1A.yaml", "reveals[find_card].variants.quiet.voiceable", True)
    patch_source(root, "scenes/1A.yaml", "reveals[0].variants.quiet.intent", "changed")
    patch_source(root, "scenes/1A.yaml", "reveals[find_card].variants.quiet.added", "value")
    patched = load_tree(root)["scenes/1A.yaml"]
    quiet = patched["reveals"][0]["variants"]["quiet"]
    assert quiet["voiceable"] is True
    assert quiet["intent"] == "changed"
    assert quiet["added"] == "value"


def test_patch_helper_unknown_path_raises_key_error(tmp_path: Path) -> None:
    root = copy_fixture("mini_ok", tmp_path)

    with pytest.raises(KeyError, match="missing_path"):
        patch_source(root, "scenes/1A.yaml", "reveals[find_card].missing_path.more", "value")


def test_duplicate_keys_are_rejected_on_load(tmp_path: Path) -> None:
    root = copy_fixture("mini_ok", tmp_path)
    duplicate = root / "duplicate.yaml"
    duplicate.write_text("schema: 1\nschema: 1\n", encoding="utf-8")

    with pytest.raises(yaml.YAMLError, match="duplicate key"):
        load_tree(root)


@pytest.mark.parametrize("scene", ["1A", "2C"])
def test_scene_claims_equal_match_claims(tmp_path: Path, scene: str) -> None:
    root = copy_fixture("mini_ok", tmp_path)
    tree = load_tree(root)
    source = tree[f"scenes/{scene}.yaml"]
    match = tree[f"scenes/{scene}.match.yaml"]

    claim_ids = {claim["claim_id"] for claim in source.get("entry_claims", [])}
    for reveal in source.get("reveals", []):
        for variant in reveal.get("variants", {}).values():
            if "claim_id" in variant:
                claim_ids.add(variant["claim_id"])
            claim_ids.update(claim["claim_id"] for claim in variant.get("extra_claims", []))
    assert claim_ids == set(match["claims"])


def test_mini_ok_compiles_when_api_exists(tmp_path: Path) -> None:
    story_source = require_story_source()
    root = copy_fixture("mini_ok", tmp_path)

    assert story_source.check_source_tree(root) == []
    package = story_source.compile_source_tree(root)
    assert [scene.scene_id for scene in package.scenes] == ["1A", "2C"]
