from pathlib import Path

import pytest

from storygame.story_package.loader import load_story_package
from storygame.story_package.models import scene_entry_texts
from storygame.story_source.diagnostics import SourceError
from tests.story_source.helpers import compiled_story_copy, load_compiled_copy, patch_source

PACKAGE = Path("data/stories/continuity-initiative")


def _copy(tmp_path: Path) -> Path:
    return compiled_story_copy(tmp_path)


def _add_variant(root: Path, variant: dict[str, object]) -> None:
    patch_source(root, "source/scenes/1A.yaml", "entry_additions", [variant])


def test_entry_variants_are_ordered_and_require_all_facts(tmp_path: Path) -> None:
    root = _copy(tmp_path)
    patch_source(
        root,
        "source/scenes/1A.yaml",
        "entry_additions",
        [
            {"when": ["processing_numbers_copied"], "text": "The first conditional line."},
            {"when": ["service_level_access_known"], "text": "The second conditional line."},
        ],
    )
    package = load_compiled_copy(root)
    metadata = next(scene.metadata for scene in package.scenes if scene.metadata.scene_id == "1A")
    assert scene_entry_texts(metadata, set()) == (metadata.entry_text,)
    assert scene_entry_texts(metadata, {"processing_numbers_copied"}) == (
        metadata.entry_text,
        "The first conditional line.",
    )
    assert scene_entry_texts(metadata, {"processing_numbers_copied", "service_level_access_known"}) == (
        metadata.entry_text,
        "The first conditional line.",
        "The second conditional line.",
    )


@pytest.mark.parametrize(
    "variant",
    [
        {"when": ["missing_fact"], "text": "A line."},
        {"when": [], "text": "A line."},
        {"when": ["processing_numbers_copied"], "text": "   "},
    ],
)
def test_loader_rejects_invalid_entry_variants(tmp_path: Path, variant: dict[str, object]) -> None:
    root = _copy(tmp_path)
    _add_variant(root, variant)
    with pytest.raises(SourceError):
        load_story_package(root)


def test_loader_applies_entry_text_hygiene_to_variants(tmp_path: Path) -> None:
    root = _copy(tmp_path)
    patch_source(
        root,
        "source/scenes/2A.yaml",
        "entry_additions",
        [
            {
                "when": ["processing_numbers_copied"],
                "text": (
                    "Kristin still has the copied prisoner numbers. The codes on the supervisor's work orders "
                    "look like the same system."
                ),
            },
            {"when": ["service_level_access_known"], "text": "Rebecca's secured office is ready."},
        ],
    )
    with pytest.raises(SourceError, match="unavailable knowledge term"):
        load_compiled_copy(root)


def test_variant_facts_are_read_as_player_facts() -> None:
    package = load_story_package(PACKAGE)
    metadata = next(scene.metadata for scene in package.scenes if scene.metadata.scene_id == "2A")
    base = scene_entry_texts(metadata, set())
    with_numbers = scene_entry_texts(metadata, {"processing_numbers_copied"})
    assert with_numbers[0] == base[0]
    assert with_numbers[1].startswith("Kristin still has the copied prisoner numbers.")
