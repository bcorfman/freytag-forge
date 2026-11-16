from __future__ import annotations

import copy
from pathlib import Path

import pytest

from tests.story_source.helpers import copy_fixture, load_tree, patch_source


def test_claim_order_fixture_changes_only_match_mapping_order(tmp_path: Path) -> None:
    baseline = load_tree(copy_fixture("mini_ok", tmp_path / "baseline"))
    root = copy_fixture("mini_ok", tmp_path / "mutated")
    match = load_tree(root)["scenes/2C.match.yaml"]
    reordered = {"k_sl_2c_e_route_effects": match["claims"]["k_sl_2c_e_route_effects"]}
    reordered.update(
        {claim_id: value for claim_id, value in match["claims"].items() if claim_id != "k_sl_2c_e_route_effects"}
    )
    patch_source(root, "scenes/2C.match.yaml", "claims", reordered)

    actual = load_tree(root)
    expected = copy.deepcopy(baseline)
    expected["scenes/2C.match.yaml"]["claims"] = reordered  # type: ignore[index]
    assert actual == expected
    assert list(actual["scenes/2C.match.yaml"]["claims"]) == list(reordered)  # type: ignore[index]
    assert list(actual["scenes/2C.match.yaml"]["claims"]) != list(  # type: ignore[index]
        baseline["scenes/2C.match.yaml"]["claims"]
    )


def test_compiled_claim_order_follows_the_match_file(tmp_path: Path) -> None:
    story_source = pytest.importorskip("storygame.story_source")
    clean = copy_fixture("mini_ok", tmp_path / "clean")
    assert story_source.check_source_tree(clean) == []
    root = copy_fixture("mini_ok", tmp_path / "mutated")
    match = load_tree(root)["scenes/2C.match.yaml"]
    reordered = {"k_sl_2c_e_route_effects": match["claims"]["k_sl_2c_e_route_effects"]}
    reordered.update(
        {claim_id: value for claim_id, value in match["claims"].items() if claim_id != "k_sl_2c_e_route_effects"}
    )
    patch_source(root, "scenes/2C.match.yaml", "claims", reordered)
    package = story_source.compile_source_tree(root)

    expected_order = tuple(reordered)
    actual_order = tuple(item.id for item in package.knowledge.knowledge if item.available_in_scenes == ("2C",))
    assert actual_order == expected_order
