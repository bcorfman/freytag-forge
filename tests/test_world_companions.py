from __future__ import annotations

import shutil
from pathlib import Path

import pytest
import yaml

from storygame.runtime.state import RuntimeState
from storygame.runtime.world_model import apply_scene_placements, world_for
from storygame.story_package import StoryPackageError, load_story_package

FIXTURE = Path("tests/fixtures/stories/lighthouse-keeper")


def copied_package(tmp_path: Path) -> Path:
    destination = tmp_path / "package"
    shutil.copytree(FIXTURE, destination)
    return destination


def edit_scene(root: Path, scene_id: str, **fields: object) -> None:
    plot = root / "plot.md"
    contents = plot.read_text(encoding="utf-8")
    marker = f"## Scene {scene_id} "
    start = contents.index(marker)
    frontmatter_start = contents.index("---\n", start) + 4
    frontmatter_end = contents.index("\n---\n", frontmatter_start)
    metadata = yaml.safe_load(contents[frontmatter_start:frontmatter_end])
    metadata.update(fields)
    replacement = yaml.safe_dump(metadata, sort_keys=False).rstrip()
    plot.write_text(contents[:frontmatter_start] + replacement + contents[frontmatter_end:], encoding="utf-8")


def test_character_placement_and_protagonist_override(tmp_path: Path) -> None:
    root = copied_package(tmp_path)
    edit_scene(
        root,
        "1A",
        participant_ids=["ada", "tom"],
        character_placements={"ada": {"parent": "shore", "text": "watching the tide"}, "tom": {"parent": "shore"}},
    )

    package = load_story_package(root)
    state = RuntimeState.bootstrap(package)
    world = world_for(package, state.facts)

    assert world.parent("ada") == "shore"
    assert world.parent("tom") == "shore"
    assert world.place_text("ada") == "watching the tide"


def test_companion_follows_and_scene_start_resets_it(tmp_path: Path) -> None:
    root = copied_package(tmp_path)
    edit_scene(root, "1B", participant_ids=["ada", "tom"], companions=["tom"])
    package = load_story_package(root)
    state = RuntimeState.bootstrap(package)

    apply_scene_placements(package, state.facts, "1B")
    world = world_for(package, state.facts)
    assert world.companions("ada") == ("tom",)
    assert world.parent("tom") == world.parent("ada")

    assert world.move("ada", "shore").ok
    assert world.parent("tom") == "shore"

    apply_scene_placements(package, state.facts, "1A")
    assert world_for(package, state.facts).companions("ada") == ()


def test_companion_with_own_placement_stays_there_until_leader_moves(tmp_path: Path) -> None:
    root = copied_package(tmp_path)
    edit_scene(
        root,
        "1B",
        participant_ids=["ada", "tom"],
        companions=["tom"],
        character_placements={"tom": {"parent": "shore", "text": "mending nets"}},
    )
    package = load_story_package(root)
    state = RuntimeState.bootstrap(package)
    apply_scene_placements(package, state.facts, "1B")
    world = world_for(package, state.facts)

    assert world.parent("tom") == "shore"
    assert world.place_text("tom") == "mending nets"


@pytest.mark.parametrize(
    ("fields", "message"),
    [
        ({"companions": ["ada"], "participant_ids": ["ada"]}, "protagonist cannot be a companion"),
        ({"companions": ["keeper_bench"], "participant_ids": ["ada", "keeper_bench"]}, "must name an NPC"),
        ({"companions": ["tom"], "participant_ids": ["ada"]}, "listed in participant_ids"),
        (
            {"character_placements": {"keeper_bench": {"parent": "shore"}}, "participant_ids": ["ada", "keeper_bench"]},
            "must name an NPC",
        ),
        ({"character_placements": {"tom": {"parent": "shore"}}, "participant_ids": ["ada"]}, "must name participants"),
        ({"character_placements": {"tom": {"parent": "missing"}}, "participant_ids": ["ada", "tom"]}, "unknown parent"),
        (
            {"character_placements": {"tom": {"parent": "keeper_bench"}}, "participant_ids": ["ada", "tom"]},
            "characters can only be in areas or containers",
        ),
    ],
)
def test_loader_rejects_bad_character_declarations(tmp_path: Path, fields: dict, message: str) -> None:
    root = copied_package(tmp_path)
    edit_scene(root, "1A", **fields)

    with pytest.raises(StoryPackageError, match=message):
        load_story_package(root)
