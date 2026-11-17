from pathlib import Path

import pytest
import yaml
from worldkeeper import BASE_KINDS, WorldSchema

from storygame.runtime.contracts import ResolvedTurnProposal, SceneTransitionProposal
from storygame.runtime.item_facts import package_seed
from storygame.runtime.state import RuntimeState
from storygame.runtime.world_model import apply_scene_placements, world_for
from storygame.story_package.loader import load_story_package
from storygame.story_package.models import ItemPlacement, placement_text
from storygame.story_package.world_schema import world_source_schema_data
from storygame.story_source.diagnostics import SourceError
from tests.story_source.helpers import compiled_story_copy, load_compiled_copy, patch_source

ROOT = Path(__file__).parents[1]


def placement_package(tmp_path: Path, *, phone_parent: str = "kitchen"):
    root = compiled_story_copy(tmp_path)
    catalog_path = root / "source" / "catalog.yaml"
    catalog = yaml.safe_load(catalog_path.read_text(encoding="utf-8"))
    kind_overrides = [
        {"is": ["furniture", "supporter"]},
        {"is": ["supporter"], "enterable": True},
    ]
    kinds_by_id = catalog["kinds"]
    kinds_by_id.update({"desk": kind_overrides[0], "seat": kind_overrides[1]})
    catalog["kinds"] = kinds_by_id
    catalog["places"].setdefault("kitchen", {"name": "kitchen", "parent": "mcgehee_home"})
    catalog["places"].setdefault("outside_house", {"name": "outside the house"})
    catalog["items"].update(
        {
            "kristin_truck": {"name": "Kristin's truck", "kind": "vehicle", "owner": "kristin"},
            "michelle_workstation": {"name": "Michelle's workstation", "kind": "desk"},
        }
    )
    catalog["items"]["michelle_drawer"].update(kind="container", openable=True, contents=["pens"])
    catalog["items"]["memory_card"]["hidden"] = True
    catalog_path.write_text(yaml.safe_dump(catalog, sort_keys=False), encoding="utf-8")

    patch_source(
        root,
        "source/scenes/1A.yaml",
        "placements",
        {
            "memory_card": {"parent": "michelle_drawer", "under": True},
            "michelle_phone": {"parent": phone_parent},
            "kristin_truck": {"parent": "outside_house"},
            "michelle_workstation": {"parent": "kitchen"},
            "michelle_drawer": {"parent": "michelle_workstation", "part_of": True},
            "workstation_chair": {"parent": "kitchen"},
        },
    )
    patch_source(
        root,
        "source/scenes/1B.yaml",
        "items",
        [
            "memory_card",
            "transit_card",
            "number_sequence",
            "michelle_photograph",
            "park_bench",
            "service_gate",
            "storm_drain",
            "kristin_truck",
            "park_bicycle",
            "picnic_blanket",
            "picnic_thermos",
            "picnic_cups",
            "park_fence",
            "dog_leash",
            "park_loudspeaker",
            "checkpoint_barrier",
            "gate_keypad",
            "michelle_phone",
        ],
    )
    patch_source(
        root,
        "source/scenes/1B.yaml",
        "placements",
        {
            "park_bench": {"parent": "los_angeles_park"},
            "michelle_phone": {"parent": "los_angeles_park", "text": "beside the park bench"},
        },
    )
    return load_compiled_copy(root)


def test_bootstrap_applies_structural_scene_placements(tmp_path):
    package = placement_package(tmp_path)
    state = RuntimeState.bootstrap(package)
    world = world_for(package, state.facts)

    assert world.parent("michelle_phone") == "kitchen"
    assert world.place_label("michelle_phone") == "Michelle's kitchen"
    assert world.parent("memory_card") == "michelle_drawer"
    assert world.relation("memory_card") == "under"
    assert world.parent("michelle_drawer") == "michelle_workstation"
    assert world.relation("michelle_drawer") == "part_of"
    assert world.owner("kristin_truck") == "kristin"
    assert not world.move("michelle_workstation", "mcgehee_home").ok


def test_scene_change_applies_new_scene_placements(tmp_path):
    package = placement_package(tmp_path)
    state = RuntimeState.bootstrap(package)

    state.apply_proposal(
        ResolvedTurnProposal(
            segments=({"kind": "narration", "text": "Kristin heads for the park."},),
            transition=SceneTransitionProposal(transition_id="t_1a_1b"),
        )
    )

    world = world_for(package, state.facts)
    assert state.current_scene_id == "1B"
    assert world.parent("michelle_phone") == "los_angeles_park"
    assert world.place_label("michelle_phone") == "beside the park bench"


def test_scene_replacement_clears_stale_character_placement_text():
    package = load_story_package(ROOT / "data/stories/continuity-initiative")
    state = RuntimeState.bootstrap(package)

    apply_scene_placements(package, state.facts, "1C")
    world = world_for(package, state.facts)
    assert world.place_text("captives") == "moving through the processing line below"

    scene_2c = next(scene for scene in package.scenes if scene.metadata.scene_id == "2C").metadata
    if "captives" in scene_2c.character_placements:
        apply_scene_placements(package, state.facts, "2C")
    apply_scene_placements(package, state.facts, "3A")

    assert world.parent("captives") == "detention_level"
    assert world.place_text("captives") != "moving through the processing line below"
    assert world.place_label("captives") == "detention level"

    apply_scene_placements(package, state.facts, "1C")
    assert world.parent("captives") == "processing_line"
    assert world.place_text("captives") == "moving through the processing line below"
    assert world.place_label("captives") == "moving through the processing line below"
    apply_scene_placements(package, state.facts, "1C")
    assert world.place_text("captives") == "moving through the processing line below"


def test_item_placement_forms_and_text():
    assert placement_text("on the floor") == "on the floor"
    assert placement_text(ItemPlacement(placement="on the floor")) == "on the floor"
    assert placement_text(ItemPlacement(parent="kitchen")) is None
    with pytest.raises(ValueError):
        ItemPlacement.model_validate({})
    with pytest.raises(ValueError):
        ItemPlacement.model_validate({"placement": "on the floor", "under": True})


def test_bench_seed_uses_npc_parent_name(tmp_path):
    package = placement_package(tmp_path, phone_parent="kristin")
    state = RuntimeState.bootstrap(package)

    things, _ = package_seed(package, state, "1A")

    assert things["Michelle's phone"]["place"] == "Kristin"


def test_world_kinds_are_typed_and_schema_defaults_fixed_flags(tmp_path):
    package = placement_package(tmp_path)
    assert package.world.kinds[0].is_ == ("furniture", "supporter")
    schema = WorldSchema.from_data(world_source_schema_data(package.world))

    assert schema.kind_is("desk", "furniture")
    assert not schema.kind_is("vehicle", "furniture")
    assert schema.is_fixed("michelle_workstation")
    assert schema.is_fixed("michelle_drawer")
    assert not schema.is_fixed("kristin_truck")


def test_cyclic_story_kinds_are_story_package_errors(tmp_path):
    root = compiled_story_copy(tmp_path)
    catalog_path = root / "source" / "catalog.yaml"
    catalog = yaml.safe_load(catalog_path.read_text(encoding="utf-8"))
    catalog["kinds"] = {"a": {"is": ["b"]}, "b": {"is": ["a"]}}
    for item in catalog["items"].values():
        if item.get("kind") not in BASE_KINDS:
            item["kind"] = "thing"
    catalog_path.write_text(yaml.safe_dump(catalog, sort_keys=False), encoding="utf-8")
    with pytest.raises(SourceError, match=r"L2\.cycles: :loader\.package: cycle among kinds"):
        load_compiled_copy(root)
