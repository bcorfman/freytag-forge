import shutil
from pathlib import Path

import pytest

from storygame.story_package.loader import StoryPackageError, load_story_package
from storygame.story_package.models import scene_entry_texts

LIGHTHOUSE = Path(__file__).parent / "fixtures" / "stories" / "lighthouse-incident"


def _copy(tmp_path: Path) -> Path:
    target = tmp_path / "story"
    shutil.copytree(LIGHTHOUSE, target)
    return target


def _add_variant(root: Path, variant: str) -> None:
    plot = root / "plot.md"
    source = plot.read_text(encoding="utf-8")
    plot.write_text(
        source.replace(
            "entry_text: Ada returns",
            f"entry_variants:\n- {variant}\nentry_text: Ada returns",
            1,
        ),
        encoding="utf-8",
    )


def test_entry_variants_are_ordered_and_require_all_facts(tmp_path: Path) -> None:
    root = _copy(tmp_path)
    plot = root / "plot.md"
    source = plot.read_text(encoding="utf-8")
    plot.write_text(
        source.replace(
            "entry_text: Ada returns",
            "entry_variants:\n"
            "- requires: [brass_key_found]\n"
            "  text: The first conditional line.\n"
            "- requires: [chart_copied]\n"
            "  text: The second conditional line.\n"
            "entry_text: Ada returns",
            1,
        ),
        encoding="utf-8",
    )
    package = load_story_package(root)
    metadata = package.scenes[0].metadata
    assert scene_entry_texts(metadata, set()) == (metadata.entry_text,)
    assert scene_entry_texts(metadata, {"brass_key_found"}) == (metadata.entry_text, "The first conditional line.")
    assert scene_entry_texts(metadata, {"brass_key_found", "chart_copied"}) == (
        metadata.entry_text,
        "The first conditional line.",
        "The second conditional line.",
    )


@pytest.mark.parametrize(
    "variant",
    [
        "requires: [missing_fact]\n  text: A line.",
        "requires: []\n  text: A line.",
        "requires: [brass_key_found]\n  text: '   '",
    ],
)
def test_loader_rejects_invalid_entry_variants(tmp_path: Path, variant: str) -> None:
    root = _copy(tmp_path)
    _add_variant(root, variant)
    with pytest.raises(StoryPackageError):
        load_story_package(root)


def test_loader_applies_entry_text_hygiene_to_variants(tmp_path: Path) -> None:
    root = Path("data/stories/continuity-initiative")
    target = tmp_path / "continuity-initiative"
    shutil.copytree(root, target)
    plot = target / "plot.md"
    source = plot.read_text(encoding="utf-8")
    plot.write_text(
        source.replace(
            "Kristin and Brandon know the service approach. Their proof is weaker, but it may still get them inside.",
            "The copied prisoner numbers are here.",
            1,
        ),
        encoding="utf-8",
    )
    with pytest.raises(StoryPackageError, match="unavailable knowledge term"):
        load_story_package(target)


def test_variant_facts_are_read_as_player_facts() -> None:
    package = load_story_package(Path("data/stories/continuity-initiative"))
    metadata = next(scene.metadata for scene in package.scenes if scene.metadata.scene_id == "2A")
    base = scene_entry_texts(metadata, set())
    with_numbers = scene_entry_texts(metadata, {"processing_numbers_copied"})
    assert with_numbers[0] == base[0]
    assert with_numbers[1].startswith("Kristin still has the copied prisoner numbers.")
