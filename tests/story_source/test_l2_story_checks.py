from __future__ import annotations

import pytest

from storygame.story_package.loader import StoryPackageError
from storygame.story_source.diagnostics import SourceError
from storygame.story_source.l2_story import check_story_logic
from storygame.story_source.reader import read_source_tree

from .helpers import compiled_story_copy, load_compiled_copy, patch_source


def _source_tree(root):
    tree, reader_diagnostics = read_source_tree(root / "source")
    assert not reader_diagnostics
    return tree


def test_rejects_transition_trigger_without_a_source_producer(tmp_path):
    root = compiled_story_copy(tmp_path)
    source = root / "source"
    patch_source(
        source,
        "scenes/1A.yaml",
        "exit.when_all",
        ["michelle_lead_actionable", "patrol_return_pressure", "memory_card_recovered", "never_asserted_fact"],
    )
    patch_source(source, "scenes/1A.yaml", "facts.never_asserted_fact", {"purpose": "test-only fact"})

    diagnostics = check_story_logic(_source_tree(root))

    matching = [diagnostic for diagnostic in diagnostics if diagnostic.name == "L2.transition_source"]
    assert len(matching) == 1
    assert matching[0].file == "scenes/1A.yaml"
    assert matching[0].address == "exit:t_1a_1b"
    assert "never_asserted_fact" in matching[0].field
    assert "can never fail" in matching[0].message
    with pytest.raises((StoryPackageError, SourceError), match="t_1a_1b.*never_asserted_fact.*can never fail"):
        load_compiled_copy(root)


def test_rejects_delivery_for_fact_without_a_player_visible_claim(tmp_path):
    root = compiled_story_copy(tmp_path)
    source = root / "source"
    patch_source(
        source,
        "scenes/1A.yaml",
        "facts.patrol_on_scene.delivery",
        {
            "source_kind": "observation",
            "fallback_text": "The patrol officer is outside the house.",
            "cue_text": "The patrol officer is outside the house.",
        },
    )
    patch_source(
        source,
        "scenes/1A.match.yaml",
        "deliveries.patrol_on_scene",
        {"must_convey": [["patrol"], ["outside"]]},
    )

    diagnostics = check_story_logic(_source_tree(root))

    matching = [diagnostic for diagnostic in diagnostics if diagnostic.name == "L2.delivery_unseen"]
    assert len(matching) == 1
    assert matching[0].file == "scenes/1A.yaml"
    assert matching[0].address == "fact:patrol_on_scene"
    assert "patrol_on_scene" in matching[0].message
    with pytest.raises((StoryPackageError, SourceError), match="patrol_on_scene.*player-visible"):
        load_compiled_copy(root)


def test_default_source_has_no_story_logic_diagnostics(tmp_path):
    root = compiled_story_copy(tmp_path)

    assert check_story_logic(_source_tree(root)) == []
