from __future__ import annotations

import json
from dataclasses import FrozenInstanceError
from pathlib import Path

import pytest
from worldkeeper import MemoryBackend, World, WorldSchema

from storygame.runtime.state import RuntimeState
from storygame.runtime.world_model import world_for
from storygame.story_package import load_story_package

ROOT = Path(__file__).parents[1]
PACKAGE_ROOT = ROOT / "data/stories/continuity-initiative"
PACKAGE = load_story_package(PACKAGE_ROOT)


def _real_world():
    state = RuntimeState.bootstrap(PACKAGE)
    return state, world_for(PACKAGE, state.facts)


def _real_ids(world):
    return {
        "observer": world.resolve("Kristin"),
        "truck": world.resolve("Kristin's truck"),
        "driver_seat": world.resolve("driver's seat"),
        "passenger_seat": world.resolve("passenger seat"),
        "laptop": world.resolve("Kristin's laptop"),
        "drawer": world.resolve("drawer"),
        "workstation": world.resolve("workstation"),
        "kitchen": world.resolve("kitchen"),
        "memory_card": world.resolve("Michelle's memory card"),
    }


def _observation_api():
    from storygame.runtime.observation import (
        ObservationContext,
        ObservationRequest,
        ObservationScopeTooLarge,
        ObservedThing,
        build_observation_context,
    )

    return ObservationContext, ObservationRequest, ObservationScopeTooLarge, ObservedThing, build_observation_context


def _world_from_data(data):
    schema = WorldSchema.from_data(data)
    world = World(schema, MemoryBackend())
    assert world.seed().ok
    return world


def _field_names(context, field):
    value = getattr(context, field)
    if field in {"visible_things", "contingent_things"}:
        return tuple(thing.name for thing in value)
    return tuple(value)


def _context_strings(context):
    values = [context.observer, context.action, *context.completed_actions]
    for field in ("visible_things", "contingent_things"):
        for thing in getattr(context, field):
            values.extend((thing.name, thing.place))
            if thing.holder is not None:
                values.append(thing.holder)
    values.extend(context.required)
    values.extend(context.omitted_optional)
    return tuple(value for value in values if isinstance(value, str))


def _prompt_strings(value):
    if isinstance(value, str):
        return (value,)
    if isinstance(value, dict):
        return tuple(text for item in value.values() for text in _prompt_strings(item))
    if isinstance(value, (list, tuple)):
        return tuple(text for item in value for text in _prompt_strings(item))
    return ()


def test_real_package_facts_cover_observation_cases():
    _, world = _real_world()
    ids = _real_ids(world)

    assert ids == {
        "observer": "kristin",
        "truck": "kristin_truck",
        "driver_seat": "truck_driver_seat",
        "passenger_seat": "truck_passenger_seat",
        "laptop": "kristin_laptop",
        "drawer": "michelle_drawer",
        "workstation": "michelle_workstation",
        "kitchen": "kitchen",
        "memory_card": "memory_card",
    }
    assert world.parent(ids["truck"]) == "outside_house"
    assert world.parent(ids["laptop"]) == ids["passenger_seat"]
    assert world.relation(ids["laptop"]) == "on"
    assert world.holder(ids["laptop"]) is None
    assert world.place_label(ids["laptop"]) == "on the passenger seat of Kristin's truck"
    assert world.axis_values(ids["drawer"])["open"] == "closed"
    assert world.parent(ids["memory_card"]) == ids["drawer"]
    assert world.relation(ids["memory_card"]) == "under"
    assert world.is_hidden(ids["memory_card"])
    public_contents = tuple(child for child in world.contents(ids["drawer"]) if not world.is_hidden(child))
    assert public_contents
    assert all(world.is_shut_away(child) for child in public_contents)


def test_worldkeeper_visibility_is_not_observer_relative():
    _, world = _real_world()
    ids = _real_ids(world)

    outside_visibility = world.is_visible(ids["laptop"])
    assert world.parent(ids["observer"]) == "mcgehee_home"
    assert world.move(ids["observer"], ids["driver_seat"]).ok
    seated_visibility = world.is_visible(ids["laptop"])

    assert outside_visibility is True
    assert seated_visibility is True
    assert seated_visibility == outside_visibility
    assert world.parent(ids["observer"]) == ids["driver_seat"]


def test_worldkeeper_contents_cannot_distinguish_emptied_from_undescribed():
    _, world = _real_world()
    ids = _real_ids(world)

    emptied = world.create("emptied container", ids["kitchen"], kind="container")
    removed = world.create("removed object", emptied.id)
    never_described = world.create("never-described container", ids["kitchen"], kind="container")
    assert emptied.ok and removed.ok and never_described.ok
    assert world.move(removed.id, ids["kitchen"]).ok

    assert world.contents(emptied.id) == ()
    assert world.contents(never_described.id) == ()
    assert emptied.id != never_described.id


def test_given_with_closed_container_mixes_shut_away_and_visible_queries():
    _, world = _real_world()
    ids = _real_ids(world)
    public_contents = tuple(child for child in world.contents(ids["drawer"]) if not world.is_hidden(child))

    assert world.axis_values(ids["drawer"])["open"] == "closed"
    assert all(not world.is_visible(child) and world.is_shut_away(child) for child in public_contents)
    assert set(public_contents).issubset(world.given_with(ids["drawer"]))
    assert ids["memory_card"] not in world.given_with(ids["drawer"])

    assert world.set_axis(ids["drawer"], "open").ok
    assert all(world.is_visible(child) and not world.is_shut_away(child) for child in public_contents)
    assert set(public_contents).issubset(world.given_with(ids["drawer"]))


def test_enter_truck_projects_laptop_and_separates_completed_step():
    _, world = _real_world()
    ids = _real_ids(world)
    assert world.move(ids["observer"], ids["driver_seat"]).ok
    assert world.parent(ids["laptop"]) == ids["passenger_seat"]
    assert world.parent(ids["observer"]) == ids["driver_seat"]

    _, ObservationRequest, _, _, build = _observation_api()
    request = ObservationRequest("Enter the truck.", "enter", ids["truck"])
    context = build(
        world,
        ids["observer"],
        request,
        completed_actions=("Kristin sat down in the driver's seat.",),
    )

    laptop = [thing for thing in context.visible_things if thing.name == "Kristin's laptop"]
    assert len(laptop) == 1
    assert laptop[0].place == "passenger seat"
    assert laptop[0].holder is None
    assert context.required == ("Kristin's laptop",)
    assert context.action == "Enter the truck."
    assert context.completed_actions == ("Kristin sat down in the driver's seat.",)
    assert context.action not in context.completed_actions
    assert not any(entity_id in _prompt_strings(context.prompt_fields()) for entity_id in world.entity_ids())


def test_approach_truck_stays_outside_and_does_not_require_laptop():
    _, world = _real_world()
    ids = _real_ids(world)
    assert world.move(ids["observer"], "outside_house").ok
    assert world.parent(ids["observer"]) == "outside_house"
    assert world.parent(ids["laptop"]) == ids["passenger_seat"]

    _, ObservationRequest, _, _, build = _observation_api()
    context = build(
        world,
        ids["observer"],
        ObservationRequest("Approach the truck.", "none", ids["truck"]),
    )

    assert "Kristin's laptop" not in context.required
    assert "Kristin's laptop" not in _field_names(context, "visible_things")


def test_inspect_passenger_seat_uses_laptop_current_location():
    _, world = _real_world()
    ids = _real_ids(world)
    assert world.move(ids["observer"], "outside_house").ok
    assert world.move(ids["laptop"], "kitchen").ok
    assert world.parent(ids["laptop"]) == ids["kitchen"]
    assert world.parent(ids["laptop"]) != ids["passenger_seat"]

    _, ObservationRequest, _, _, build = _observation_api()
    context = build(
        world,
        ids["observer"],
        ObservationRequest("Inspect the passenger seat.", "look", ids["passenger_seat"]),
    )

    assert "Kristin's laptop" not in _field_names(context, "visible_things")
    assert all(thing.place != "passenger seat" for thing in context.visible_things)


def test_examine_my_laptop_reports_holder_and_current_place_once():
    _, world = _real_world()
    ids = _real_ids(world)
    assert world.move(ids["observer"], ids["kitchen"]).ok
    assert world.move(ids["laptop"], ids["observer"]).ok
    assert world.holder(ids["laptop"]) == ids["observer"]
    assert world.parent(ids["laptop"]) == ids["observer"]
    assert world.parent(ids["laptop"]) != ids["passenger_seat"]

    _, ObservationRequest, _, _, build = _observation_api()
    context = build(
        world,
        ids["observer"],
        ObservationRequest("Examine my laptop.", "look", ids["laptop"]),
        label=lambda current_world, entity_id: (
            "Kristin" if entity_id == ids["observer"] else current_world.name(entity_id)
        ),
    )

    laptops = [thing for thing in context.visible_things if thing.name == "Kristin's laptop"]
    assert len(laptops) == 1
    assert laptops[0].holder == "Kristin"
    assert laptops[0].place != "passenger seat"
    assert context.required == ("Kristin's laptop",)


def test_open_drawer_exposes_public_contents_but_not_hidden_story_item():
    _, world = _real_world()
    ids = _real_ids(world)
    public_id = next(child for child in world.contents(ids["drawer"]) if not world.is_hidden(child))
    public_name = world.name(public_id)
    hidden_name = world.name(ids["memory_card"])
    assert world.axis_values(ids["drawer"])["open"] == "closed"
    assert world.is_shut_away(public_id)
    assert world.is_hidden(ids["memory_card"])

    _, ObservationRequest, _, _, build = _observation_api()
    context = build(
        world,
        ids["observer"],
        ObservationRequest("Open the drawer.", "open", ids["drawer"]),
    )

    assert public_name in _field_names(context, "contingent_things")
    assert hidden_name not in _context_strings(context)
    assert hidden_name not in _prompt_strings(context.prompt_fields())


def test_inspect_closed_drawer_does_not_describe_contingent_contents():
    _, world = _real_world()
    ids = _real_ids(world)
    public_names = tuple(world.name(child) for child in world.contents(ids["drawer"]) if not world.is_hidden(child))
    assert world.axis_values(ids["drawer"])["open"] == "closed"
    assert public_names
    assert all(world.is_shut_away(child) for child in world.contents(ids["drawer"]) if not world.is_hidden(child))

    _, ObservationRequest, _, _, build = _observation_api()
    context = build(
        world,
        ids["observer"],
        ObservationRequest("Inspect the closed drawer.", "look", ids["drawer"]),
    )

    assert not set(public_names) & set(_field_names(context, "visible_things"))
    assert not set(public_names) & set(context.required)
    assert context.contingent_things == ()


def test_search_beneath_drawer_does_not_refind_recovered_item():
    _, world = _real_world()
    ids = _real_ids(world)
    assert world.reveal(ids["memory_card"]).ok
    assert world.move(ids["memory_card"], ids["observer"]).ok
    assert world.holder(ids["memory_card"]) == ids["observer"]
    assert world.parent(ids["memory_card"]) == ids["observer"]
    assert world.parent(ids["memory_card"]) != ids["drawer"]

    _, ObservationRequest, _, _, build = _observation_api()
    context = build(
        world,
        ids["observer"],
        ObservationRequest("Search beneath the drawer.", "none", ids["drawer"]),
    )

    assert "Michelle's memory card" not in _context_strings(context)
    assert all(thing.place != "drawer" for thing in context.visible_things)


def test_compound_enter_and_inspect_preserves_original_action():
    _, world = _real_world()
    ids = _real_ids(world)
    assert world.move(ids["observer"], ids["driver_seat"]).ok
    assert world.parent(ids["laptop"]) == ids["passenger_seat"]

    _, ObservationRequest, _, _, build = _observation_api()
    action = "Enter the truck and inspect my laptop."
    completed = ("Kristin sat down in the driver's seat.",)
    context = build(
        world,
        ids["observer"],
        ObservationRequest(action, "enter", ids["laptop"]),
        completed_actions=completed,
    )

    assert context.action == action
    assert context.completed_actions == completed
    assert context.completed_actions.count(completed[0]) == 1
    assert context.required == ("Kristin's laptop",)


def test_examine_kitchen_does_not_expand_to_other_area_or_text_only_things():
    _, world = _real_world()
    ids = _real_ids(world)
    assert world.move(ids["observer"], ids["kitchen"]).ok
    assert world.parent(ids["laptop"]) == ids["passenger_seat"]
    assert world.area(ids["laptop"]) == "outside_house"
    assert world.resolve("kitchen") == ids["kitchen"]
    assert world.is_a(ids["kitchen"], "area")

    _, ObservationRequest, _, _, build = _observation_api()
    context = build(
        world,
        ids["observer"],
        ObservationRequest("Examine the kitchen.", "look", ids["kitchen"]),
    )

    assert "Kristin's laptop" not in _field_names(context, "visible_things")
    assert "kitchen" not in _field_names(context, "visible_things")


def test_synthetic_observatory_uses_public_lens_and_tray_names():
    world = _world_from_data(
        {
            "entities": [
                {"id": "observatory", "name": "observatory", "kind": "area"},
                {"id": "rhea", "name": "Rhea Vale", "kind": "character"},
                {"id": "telescope_tray", "name": "telescope tray", "kind": "supporter"},
                {"id": "lens", "name": "calibrated lens", "kind": "thing"},
            ]
        }
    )
    assert world.move("rhea", "observatory").ok
    assert world.place("lens", "telescope_tray").ok
    assert world.parent("lens") == "telescope_tray"
    assert world.relation("lens") == "on"
    assert world.name("rhea") != "Kristin Schweitzer"
    assert world.place_label("lens") == "telescope tray"

    _, ObservationRequest, _, _, build = _observation_api()
    context = build(
        world,
        "rhea",
        ObservationRequest("Inspect the telescope tray.", "look", "telescope_tray"),
    )

    lens = [thing for thing in context.visible_things if thing.name == "calibrated lens"]
    assert len(lens) == 1
    assert lens[0].place == "telescope tray"
    assert "calibrated lens" in context.required


def test_synthetic_skiff_has_same_projection_shape_with_different_names():
    world = _world_from_data(
        {
            "kinds": [{"id": "seat", "is": ["supporter"], "enterable": True}],
            "entities": [
                {"id": "shore", "name": "tidal shore", "kind": "area"},
                {"id": "marin", "name": "Marin Okafor", "kind": "character"},
                {"id": "skiff", "name": "survey skiff", "kind": "vehicle"},
                {
                    "id": "stern_bench",
                    "name": "stern bench",
                    "kind": "seat",
                    "enterable": True,
                    "seat_for": "skiff",
                    "axes": [{"poles": ["empty", "occupied"], "initial": "empty"}],
                    "enter_pole": "occupied",
                },
                {"id": "cargo", "name": "survey crate", "kind": "thing"},
            ],
        }
    )
    assert world.move("marin", "shore").ok
    assert world.move("skiff", "shore").ok
    assert world.move("stern_bench", "skiff").ok
    assert world.move("cargo", "stern_bench").ok
    assert world.move("marin", "stern_bench").ok
    assert world.parent("cargo") == "stern_bench"
    assert world.parent("marin") == "stern_bench"
    assert world.place_label("cargo") == "stern bench"

    _, ObservationRequest, _, _, build = _observation_api()
    context = build(
        world,
        "marin",
        ObservationRequest("Board the skiff.", "enter", "skiff"),
        completed_actions=("Marin sat on the stern bench.",),
    )

    cargo = [thing for thing in context.visible_things if thing.name == "survey crate"]
    assert len(cargo) == 1
    assert cargo[0].place == "stern bench"
    assert "survey crate" in context.required


def test_required_scope_overflow_raises_but_optional_detail_is_reported():
    world = _world_from_data(
        {
            "entities": [
                {"id": "room", "name": "room", "kind": "area"},
                {"id": "observer", "name": "observer", "kind": "character"},
                {"id": "tray", "name": "display tray", "kind": "supporter"},
                {"id": "lens", "name": "lens", "kind": "thing"},
                {"id": "compass", "name": "compass", "kind": "thing"},
                {"id": "book", "name": "field book", "kind": "thing"},
                {"id": "lamp", "name": "lamp", "kind": "thing"},
            ]
        }
    )
    assert world.move("observer", "room").ok
    assert world.place("lens", "tray").ok
    assert world.place("compass", "tray").ok
    assert world.place("book", "room").ok
    assert world.place("lamp", "room").ok
    assert set(world.contents("tray")) == {"compass", "lens"}

    _, ObservationRequest, ObservationScopeTooLarge, _, build = _observation_api()
    with pytest.raises(ObservationScopeTooLarge):
        build(
            world,
            "observer",
            ObservationRequest("Inspect the display tray.", "look", "tray"),
            max_required=1,
        )

    optional = build(
        world,
        "observer",
        ObservationRequest("Look around the room.", "none", "room"),
        max_optional=1,
    )
    assert len(optional.visible_things) <= 1
    assert len(optional.omitted_optional) >= 1
    assert set(optional.omitted_optional).isdisjoint(_field_names(optional, "visible_things"))


def test_observation_projection_is_deterministic():
    _, world = _real_world()
    ids = _real_ids(world)
    assert world.move(ids["observer"], "outside_house").ok
    assert world.parent(ids["laptop"]) == ids["passenger_seat"]

    _, ObservationRequest, _, _, build = _observation_api()
    request = ObservationRequest("Approach the truck.", "none", ids["truck"])
    first = build(world, ids["observer"], request)
    second = build(world, ids["observer"], request)

    assert first == second
    with pytest.raises(FrozenInstanceError):
        first.action = "changed"


def test_prompt_fields_are_safe_public_json_values():
    _, world = _real_world()
    ids = _real_ids(world)
    shut_away_names = tuple(world.name(child) for child in world.contents(ids["drawer"]) if world.is_shut_away(child))
    hidden_names = (world.name(ids["memory_card"]),)
    assert world.is_hidden(ids["memory_card"])
    assert world.axis_values(ids["drawer"])["open"] == "closed"

    _, ObservationRequest, _, _, build = _observation_api()
    context = build(
        world,
        ids["observer"],
        ObservationRequest("Inspect the closed drawer.", "look", ids["drawer"]),
    )
    fields = context.prompt_fields()
    assert json.dumps(fields)
    for value in fields.values():
        assert isinstance(value, (str, bool)) or (
            isinstance(value, list) and all(isinstance(item, str) for item in value)
        )
    prompt_strings = _prompt_strings(fields)
    assert not any(entity_id in prompt_strings for entity_id in world.entity_ids())
    assert not set(hidden_names) & set(prompt_strings)
    assert not set(shut_away_names) & set(prompt_strings)


def test_declared_window_view_is_observer_relative_and_blockable():
    data = {
        "entities": [
            {"id": "yard", "name": "yard", "kind": "area"},
            {"id": "observer", "name": "observer", "kind": "character"},
            {
                "id": "truck",
                "name": "truck",
                "kind": "vehicle",
                "view": [{"from": "yard", "blocked_by": {"axis": "barrier", "pole": "holding"}}],
            },
            {
                "id": "barrier",
                "name": "window barrier",
                "kind": "thing",
                "axes": [{"poles": ["clear", "holding"], "initial": "clear"}],
            },
            {"id": "laptop", "name": "laptop", "kind": "thing"},
        ]
    }
    world = _world_from_data(data)
    assert world.move("observer", "yard").ok
    assert world.move("truck", "yard").ok
    assert world.move("laptop", "truck").ok
    assert world.parent("observer") == "yard"
    assert world.parent("laptop") == "truck"
    assert world.axis_values("barrier")["clear"] == "clear"

    _, ObservationRequest, _, _, build = _observation_api()
    visible = build(
        world,
        "observer",
        ObservationRequest("Look through the truck window.", "look", "truck"),
    )
    assert world.parent("observer") == "yard"
    assert "laptop" in _field_names(visible, "visible_things")

    assert world.set_axis("barrier", "holding").ok
    assert world.axis_values("barrier")["clear"] == "holding"
    blocked = build(
        world,
        "observer",
        ObservationRequest("Look through the truck window.", "look", "truck"),
    )
    assert "laptop" not in _field_names(blocked, "visible_things")


def test_declared_contents_completeness_distinguishes_empty_from_open_world():
    data = {
        "entities": [
            {"id": "room", "name": "room", "kind": "area"},
            {"id": "observer", "name": "observer", "kind": "character"},
            {
                "id": "complete_box",
                "name": "complete box",
                "kind": "container",
                "contents_complete": True,
            },
            {
                "id": "open_world_box",
                "name": "open-world box",
                "kind": "container",
            },
        ]
    }
    world = _world_from_data(data)
    assert world.move("observer", "room").ok
    assert world.move("complete_box", "room").ok
    assert world.move("open_world_box", "room").ok
    assert world.contents("complete_box") == ()
    assert world.contents("open_world_box") == ()
    assert world.parent("observer") == "room"

    _, ObservationRequest, _, _, build = _observation_api()
    complete = build(
        world,
        "observer",
        ObservationRequest("Search beneath the complete box.", "none", "complete_box"),
    )
    assert complete.scope_complete is True
    assert complete.visible_things == ()

    incomplete = build(
        world,
        "observer",
        ObservationRequest("Search beneath the open-world box.", "none", "open_world_box"),
    )
    assert incomplete.scope_complete is False
    assert incomplete.visible_things == ()


def test_inspect_bench_includes_items_with_story_kinds():
    world = _world_from_data(
        {
            "kinds": [{"id": "gadget", "is": ["thing"]}],
            "entities": [
                {"id": "area", "name": "area", "kind": "area"},
                {"id": "observer", "name": "observer", "kind": "character"},
                {"id": "bench", "name": "bench", "kind": "supporter"},
                {"id": "probe", "name": "probe", "kind": "gadget"},
                {"id": "cup", "name": "cup", "kind": "thing"},
            ],
        }
    )
    assert world.move("observer", "area").ok
    assert world.move("bench", "area").ok
    assert world.place("probe", "bench").ok
    assert world.place("cup", "bench").ok

    _, ObservationRequest, _, _, build = _observation_api()
    context = build(
        world,
        "observer",
        ObservationRequest("Inspect the bench.", "look", "bench"),
    )

    visible_names = _field_names(context, "visible_things")
    assert context.required == ("cup", "probe")
    assert "cup" in visible_names
    assert "probe" in visible_names
    assert "bench" not in visible_names
    assert "bench" not in context.required
