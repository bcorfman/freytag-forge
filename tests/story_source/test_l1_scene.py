"""Focused layer-one checks for declarative scene files."""

# NOTE: The contract leaves the exact source-kind enum open; tests use the four kinds present in the source fixtures.

from __future__ import annotations

from pathlib import Path

import pytest

from tests.story_source.helpers import DELETE, copy_fixture, patch_source, require_story_source


def _only_layer_one(root: Path, name: str) -> None:
    """Assert a mutation produced one located diagnostic of the requested kind."""

    story_source = require_story_source()
    diagnostics = story_source.check_source_tree(root)
    matching = [diagnostic for diagnostic in diagnostics if diagnostic.name == name]
    assert matching
    for diagnostic in matching:
        assert diagnostic.file
        assert diagnostic.address
        assert diagnostic.field
    assert require_story_source().check_source_tree(copy_fixture("mini_ok", root.parent / "clean")) == []


@pytest.mark.parametrize(
    ("address", "replacement", "expected_name"),
    [
        pytest.param(
            "reveals[find_card].done_when",
            "the card is found",
            "L1.unknown_key",
            id="unknown_scene_key",
        ),
        pytest.param("pressure", DELETE, "L1.missing_key", id="missing_scene_key"),
        pytest.param("turns.min", "soon", "L1.type", id="wrong_scene_value_type"),
        pytest.param("freytag_phase", "sideways", "L1.enum", id="wrong_scene_enum"),
        pytest.param(
            "reveals[find_card].storylet_id",
            "storylet-one",
            "L1.id_pattern",
            id="scene_id_pattern",
        ),
    ],
)
def test_scene_address_mutations_produce_one_layer_one_diagnostic(
    tmp_path: Path, address: str, replacement: object, expected_name: str
) -> None:
    root = copy_fixture("mini_ok", tmp_path)
    patch_source(root, "scenes/1A.yaml", address, replacement)

    _only_layer_one(root, expected_name)


def test_all_true_condition_rejects_false(tmp_path: Path) -> None:
    root = copy_fixture("mini_ok", tmp_path)
    patch_source(
        root, "scenes/1A.yaml", "entry_additions", [{"when": {"memory_card_recovered": False}, "text": "extra"}]
    )

    _only_layer_one(root, "L1.condition_value")


def test_say_passage_requires_unguarded_default_last(tmp_path: Path) -> None:
    root = copy_fixture("mini_ok", tmp_path)
    patch_source(
        root,
        "scenes/1A.yaml",
        "beats[patrol_leaves_1a].say",
        [{"when": {"card_challenged": True}, "text": "guarded"}],
    )

    _only_layer_one(root, "L1.passage_list")


def test_claim_keys_require_claim_id(tmp_path: Path) -> None:
    root = copy_fixture("mini_ok", tmp_path)
    patch_source(root, "scenes/1A.yaml", "reveals[find_card].variants.quiet.claim_id", DELETE)

    _only_layer_one(root, "L1.claim_keys_without_claim")
