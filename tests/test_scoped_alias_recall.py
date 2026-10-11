import shutil
from pathlib import Path

import yaml

from storygame.runtime.item_facts import ItemFactsProvider
from storygame.runtime.knowledge import _input_referenced_entity_ids
from storygame.runtime.state import RuntimeState
from storygame.runtime.world_model import world_for
from storygame.story_package.loader import load_story_package
from storygame.story_package.models import CharacterPlacement, Group

ROOT = Path(__file__).resolve().parents[1]
FIXTURE = ROOT / "tests" / "fixtures" / "stories" / "lighthouse-keeper"


def _package(tmp_path: Path, *, aliases: dict[str, list[str]], name: str = "package"):
    destination = tmp_path / name
    shutil.copytree(FIXTURE, destination)
    world_path = destination / "world.yaml"
    world_data = yaml.safe_load(world_path.read_text())
    for entity in (*world_data["items"], *world_data.get("groups", [])):
        if entity["id"] in aliases:
            entity["scoped_aliases"] = aliases[entity["id"]]
    world_path.write_text(yaml.safe_dump(world_data, sort_keys=False))
    return load_story_package(destination)


def _answers(package, scene_id: str, player_input: str, alias: str):
    package = package.model_copy(
        update={"scenes": tuple(sorted(package.scenes, key=lambda scene: scene.metadata.scene_id != scene_id))}
    )
    state = RuntimeState.bootstrap(package)
    scene = next(scene for scene in package.scenes if scene.metadata.scene_id == scene_id)
    recalled = _input_referenced_entity_ids(
        package.world,
        player_input,
        scope_world=world_for(package, state.facts),
        scene=scene,
        protagonist_id=package.world.protagonist_id,
    )
    provider = ItemFactsProvider(
        worker_url="https://worker.example/turn",
        token="",
        state=state,
        item_facts={},
        mode="single_call",
        seed_from_package=True,
    )
    return alias, recalled, provider._resolve_name(provider._world(), alias)


def test_scoped_alias_recall_and_resolver_match_when_placed(tmp_path: Path) -> None:
    package = _package(tmp_path, aliases={"keeper_bench": ["seat"]})

    alias, recalled, resolved = _answers(package, "1A", "Check the seat.", "seat")

    assert alias == "seat"
    assert "keeper_bench" in recalled
    assert resolved == "keeper_bench"


def test_scoped_alias_recall_and_resolver_reject_unplaced_and_ambiguous_aliases(tmp_path: Path) -> None:
    package = _package(tmp_path, aliases={"keeper_bench": ["seat"], "sea_chest": ["seat"]})

    _, recalled, resolved = _answers(package, "1A", "Check the seat.", "seat")
    assert "keeper_bench" not in recalled
    assert "sea_chest" not in recalled
    assert resolved is None

    package = _package(tmp_path, aliases={"keeper_bench": ["seat"]}, name="package-unplaced")
    _, recalled, resolved = _answers(package, "1B", "Check the seat.", "seat")
    assert "keeper_bench" not in recalled
    assert resolved is None


def test_group_scoped_alias_recall_and_resolver_match_when_placed(tmp_path: Path) -> None:
    package = _package(tmp_path, aliases={})
    group = Group(id="captives", name="captives", scoped_aliases=("prisoners",))
    world = package.world.model_copy(update={"groups": (group,)})
    scene = next(scene for scene in package.scenes if scene.metadata.scene_id == "1A")
    scene = scene.model_copy(
        update={
            "metadata": scene.metadata.model_copy(
                update={"participant_ids": (*scene.metadata.participant_ids, "captives")}
            )
        }
    )
    scene = scene.model_copy(
        update={
            "metadata": scene.metadata.model_copy(
                update={"character_placements": {"captives": CharacterPlacement(parent="parlour")}}
            )
        }
    )
    package = package.model_copy(
        update={
            "world": world,
            "scenes": (scene, *(item for item in package.scenes if item.metadata.scene_id != "1A")),
        }
    )

    _, recalled, resolved = _answers(package, "1A", "Search the prisoners.", "prisoners")

    assert "captives" in recalled
    assert resolved == "captives"
