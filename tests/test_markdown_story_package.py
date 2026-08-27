from __future__ import annotations

import shutil
from pathlib import Path

import pytest

from storygame.story_package import StoryPackageError, load_story_package

PACKAGE = Path("data/stories/continuity-initiative")


def copied_package(tmp_path: Path) -> Path:
    destination = tmp_path / "package"
    shutil.copytree(PACKAGE, destination)
    return destination


def test_continuity_package_loads_all_scene_headings_and_storylets() -> None:
    package = load_story_package(PACKAGE)
    assert [scene.metadata.scene_id for scene in package.scenes] == [
        "1A",
        "1B",
        "1C",
        "2A",
        "2B",
        "2C",
        "3A",
        "3B",
        "3C",
    ]
    assert len(package.storylets) == 29
    assert all(storylet.source_links and storylet.sections["Protected boundary"] for storylet in package.storylets)


@pytest.mark.parametrize(
    ("path", "old", "new", "message"),
    [
        ("plot.md", "scene_id: 1A", "scene_id: 9Z", "heading and frontmatter"),
        ("plot.md", "---\nscene_id: 1A", "scene_id: 1A", "lacks YAML frontmatter"),
        ("world.yaml", "thomas_home", "unknown_home", "unknown entities"),
        ("pacing.yaml", "latest_seconds: 120", "latest_seconds: 30", "pacing timestamps"),
        ("storylets.md", "**Pacing impact**", "**Impact**", "lacks sections"),
        ("storylets.md", "plot.md#scene-1a1", "plot.md#missing", "unknown plot heading"),
    ],
)
def test_loader_rejects_malformed_sources(tmp_path: Path, path: str, old: str, new: str, message: str) -> None:
    root = copied_package(tmp_path / "fallback")
    source = root / path
    source.write_text(source.read_text().replace(old, new, 1))
    with pytest.raises(StoryPackageError, match=message):
        load_story_package(root)


def test_loader_rejects_storylet_window_outside_parent_scene(tmp_path: Path) -> None:
    root = copied_package(tmp_path)
    source = root / "storylets.md"
    source.write_text(source.read_text().replace("latest: `00:02:00`", "latest: `00:02:01`", 1))
    with pytest.raises(StoryPackageError, match="escapes its scene pacing window"):
        load_story_package(root)


def test_loader_rejects_transition_dependency_cycle(tmp_path: Path) -> None:
    root = copied_package(tmp_path)
    source = root / "pacing.yaml"
    source.write_text(
        source.read_text()
        + "\n"
        + (
            "- {id: t_cycle, source_scene_id: 3C, target_scene_id: 1A, priority: 1, "
            "triggers: [{fact_id: broadcast_started, equals: true}]}\n"
        )
    )
    with pytest.raises(StoryPackageError, match="dependency cycle"):
        load_story_package(root)


def test_loader_rejects_unknown_trigger_predicate_and_fallback(tmp_path: Path) -> None:
    root = copied_package(tmp_path)
    pacing = root / "pacing.yaml"
    pacing.write_text(pacing.read_text().replace("fact_id: sarah_lead_actionable", "fact_id: unknown_fact", 1))
    with pytest.raises(StoryPackageError, match="unknown trigger predicate"):
        load_story_package(root)

    root = copied_package(tmp_path / "fallback")
    world = root / "world.yaml"
    world.write_text(world.read_text().replace("  - sarah_phone", "  - missing_item", 1))
    with pytest.raises(StoryPackageError, match="unknown fallback"):
        load_story_package(root)


@pytest.mark.parametrize(
    ("path", "old", "new", "message"),
    [
        ("plot.md", "## Scene", "### Scene", "unknown scene"),
        ("storylets.md", "**Allowed scene:** `1A`", "**Allowed scene:** `1B`", "invalid allowed scene"),
        ("storylets.md", "earliest: `00:00:00`", "earliest: `00:99:00`", "invalid timestamp"),
        (
            "pacing.yaml",
            "  - memory_card",
            "  - unknown",
            "unknown dependency",
        ),
        ("pacing.yaml", "id: t_1b_1c", "id: t_1a_1b", "duplicate transition ID"),
    ],
)
def test_loader_rejects_remaining_boundary_errors(tmp_path: Path, path: str, old: str, new: str, message: str) -> None:
    root = copied_package(tmp_path)
    source = root / path
    source.write_text(source.read_text().replace(old, new, 1))
    with pytest.raises(StoryPackageError, match=message):
        load_story_package(root)


def test_loader_rejects_ambiguous_transition_priority(tmp_path: Path) -> None:
    root = copied_package(tmp_path)
    source = root / "pacing.yaml"
    source.write_text(
        source.read_text()
        + "\n"
        + (
            "- {id: t_tie, source_scene_id: 1A, target_scene_id: 1C, priority: 10, "
            "triggers: [{fact_id: sarah_lead_actionable, equals: true}]}\n"
        )
    )
    with pytest.raises(StoryPackageError, match="ambiguous priority"):
        load_story_package(root)
