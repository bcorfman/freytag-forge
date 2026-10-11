import shutil
from pathlib import Path

import pytest
import yaml

from storygame.runtime.engine import RuntimeEngine
from storygame.runtime.item_facts import ItemFactsProvider
from storygame.runtime.state import RuntimeState
from storygame.runtime.validation import ProposalValidationError
from storygame.story_package.loader import StoryPackageError, load_story_package

ROOT = Path(__file__).resolve().parents[1]
FIXTURE = ROOT / "tests" / "fixtures" / "stories" / "lighthouse-keeper"


def _package(tmp_path: Path, *, alias: str = "seat"):
    destination = tmp_path / "package"
    shutil.copytree(FIXTURE, destination)
    world_path = destination / "world.yaml"
    world_data = yaml.safe_load(world_path.read_text())
    next(item for item in world_data["items"] if item["id"] == "keeper_bench")["scoped_aliases"] = [alias]
    world_path.write_text(yaml.safe_dump(world_data, sort_keys=False))
    return load_story_package(destination)


def _provider(package, scene_id: str) -> ItemFactsProvider:
    scenes = tuple(sorted(package.scenes, key=lambda scene: scene.metadata.scene_id != scene_id))
    package = package.model_copy(update={"scenes": scenes})
    state = RuntimeState.bootstrap(package)
    return ItemFactsProvider(
        worker_url="https://worker.example/turn",
        token="",
        state=state,
        item_facts={},
        mode="single_call",
        seed_from_package=True,
    )


def test_item_scoped_alias_resolves_only_when_placed_and_in_scope(tmp_path: Path) -> None:
    package = _package(tmp_path)

    placed = _provider(package, "1A")
    absent = _provider(package, "1B")

    assert placed._resolve_name(placed._world(), "seat") == "keeper_bench"
    assert absent._resolve_name(absent._world(), "seat") is None


def test_two_placed_entities_with_the_same_scoped_alias_are_ambiguous(tmp_path: Path) -> None:
    package = _package(tmp_path)
    sea_chest = next(item for item in package.world.items if item.id == "sea_chest")
    world = package.world.model_copy(
        update={
            "items": tuple(
                sea_chest.model_copy(update={"scoped_aliases": ("seat",)}) if item is sea_chest else item
                for item in package.world.items
            )
        }
    )
    package = package.model_copy(update={"world": world})
    provider = _provider(package, "1A")

    assert provider._resolve_name(provider._world(), "seat") is None


def test_scoped_alias_is_not_a_narration_guard_but_item_name_is(tmp_path: Path) -> None:
    package = _package(tmp_path)
    package = package.model_copy(
        update={"scenes": tuple(sorted(package.scenes, key=lambda scene: scene.metadata.scene_id != "1B"))}
    )
    state = RuntimeState.bootstrap(package)

    accepted = RuntimeEngine(
        state,
        lambda _: {"segments": [{"kind": "narration", "text": "The seat is dusty."}]},
    ).turn("Search the lamp room.")
    assert accepted.segments[0].text == "The seat is dusty."

    with pytest.raises(ProposalValidationError) as caught:
        RuntimeEngine(
            RuntimeState.bootstrap(package),
            lambda _: {"segments": [{"kind": "narration", "text": "The bench is dusty."}]},
        ).turn("Search the lamp room.")
    assert caught.value.code == "narration_known_term_leak"


@pytest.mark.parametrize("alias", ["", "Ada"])
def test_item_scoped_alias_loader_rejects_blank_or_declared_alias(tmp_path: Path, alias: str) -> None:
    destination = tmp_path / "package"
    shutil.copytree(FIXTURE, destination)
    world_path = destination / "world.yaml"
    world_data = yaml.safe_load(world_path.read_text())
    next(item for item in world_data["items"] if item["id"] == "keeper_bench")["scoped_aliases"] = [alias]
    world_path.write_text(yaml.safe_dump(world_data, sort_keys=False))

    with pytest.raises(StoryPackageError, match="item 'keeper_bench' scoped alias"):
        load_story_package(destination)
