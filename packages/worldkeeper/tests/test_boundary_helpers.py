from worldkeeper import MemoryBackend, World, WorldSchema


def make_world():
    schema = WorldSchema.from_data(
        {
            "kinds": [{"id": "seat", "is": ["supporter"], "enterable": True}],
            "entities": [
                {"id": "root", "name": "root", "kind": "area"},
                {"id": "hall", "name": "hall", "kind": "area", "parent": "root"},
                {"id": "gallery", "name": "gallery", "kind": "area", "parent": "hall"},
                {"id": "other", "name": "other", "kind": "area", "parent": "root"},
                {"id": "observer", "name": "observer", "kind": "character"},
                {"id": "companion", "name": "companion", "kind": "character"},
                {"id": "box", "name": "box", "kind": "container", "openable": True, "open": False},
                {"id": "nested", "name": "nested", "kind": "container"},
                {"id": "table", "name": "table", "kind": "supporter"},
                {"id": "apple", "name": "apple", "kind": "thing"},
                {"id": "z_item", "name": "z item", "kind": "thing"},
                {"id": "deep", "name": "deep", "kind": "thing"},
                {"id": "coin", "name": "coin", "kind": "thing"},
                {"id": "book", "name": "book", "kind": "thing"},
                {"id": "hidden", "name": "hidden", "kind": "thing", "hidden": True},
                {"id": "unplaced", "name": "unplaced", "kind": "thing"},
                {"id": "fixed", "name": "fixed", "kind": "furniture"},
                {"id": "vehicle", "name": "the van", "kind": "vehicle"},
                {
                    "id": "seat",
                    "name": "driver seat",
                    "kind": "seat",
                    "seat_for": "vehicle",
                    "axes": [{"poles": ["empty", "occupied"], "initial": "empty"}],
                    "enter_pole": "occupied",
                },
                {"id": "luggage", "name": "travel luggage", "kind": "thing"},
                {"id": "cycle_a", "name": "cycle a", "kind": "thing"},
                {"id": "cycle_b", "name": "cycle b", "kind": "thing"},
            ],
        }
    )
    world = World(schema, MemoryBackend())
    world.seed()
    assert world.move("observer", "hall").ok
    assert world.move("companion", "hall").ok
    assert world.place("box", "hall").ok
    assert world.place("nested", "box").ok
    assert world.place("apple", "box").ok
    assert world.place("z_item", "box").ok
    assert world.place("deep", "nested").ok
    assert world.place("table", "hall").ok
    assert world.place("coin", "table", under=True).ok
    assert world.place("book", "table").ok
    assert world.place("hidden", "hall").ok
    assert world.place("fixed", "hall").ok
    assert world.place("vehicle", "hall").ok
    assert world.place("seat", "hall").ok
    assert world.place("luggage", "vehicle").ok
    return world


def test_descendants_are_ordered_unique_and_cycle_safe():
    world = make_world()
    assert world.descendants("box") == ("apple", "nested", "z_item", "deep")

    world._replace("wk_parent", "cycle_a", value="cycle_b")
    world._replace("wk_relation", "cycle_a", value="in")
    world._replace("wk_parent", "cycle_b", value="cycle_a")
    world._replace("wk_relation", "cycle_b", value="in")
    assert world.descendants("cycle_a") == ("cycle_b",)
    assert world.descendants("unknown") == ()


def test_contains_includes_self_and_handles_cycles_and_unknowns():
    world = make_world()
    assert world.contains("hall", "hall")
    assert world.contains("hall", "apple")
    assert not world.contains("box", "hall")
    assert not world.contains("unknown", "apple")

    world._replace("wk_parent", "cycle_a", value="cycle_b")
    world._replace("wk_parent", "cycle_b", value="cycle_a")
    assert world.contains("cycle_a", "cycle_b")
    assert world.contains("cycle_b", "cycle_a")


def test_under_contents_is_direct_and_preserves_contents_order():
    world = make_world()
    assert world.under_contents("table") == ("coin",)
    assert world.under_contents("box") == ()
    assert world.under_contents("unknown") == ()


def test_open_state_is_limited_to_openable_containers_and_known_poles():
    world = make_world()
    assert world.open_state("box") == "closed"
    assert world.set_axis("box", "open").ok
    assert world.open_state("box") == "open"
    assert world.open_state("table") is None
    assert world.open_state(None) is None
    assert world.open_state("unknown") is None
    world._replace("wk_axis", "nested", "open", "closed")
    assert world.open_state("nested") is None
    world._replace("wk_axis", "box", "open", "ajar")
    assert world.open_state("box") is None


def test_is_item_uses_kind_ancestry_and_unknown_ids_are_false():
    world = make_world()
    assert world.is_item("apple")
    assert not world.is_item("box")
    assert not world.is_item("table")
    assert not world.is_item("seat")
    assert not world.is_item("fixed")
    assert not world.is_item("vehicle")
    assert not world.is_item("unknown")


def test_observable_items_matches_focus_rules_and_area_order():
    world = make_world()
    assert world.observable_items("observer", None) == ("apple", "book", "coin", "deep", "hidden", "luggage", "z_item")
    assert world.observable_items("observer", "hall") == (
        "apple",
        "book",
        "coin",
        "deep",
        "hidden",
        "luggage",
        "z_item",
    )
    assert world.observable_items("observer", "box") == ("apple", "nested", "z_item", "deep")
    assert world.observable_items("observer", "apple") == ("apple",)
    assert world.observable_items("observer", "table") == ("book", "coin")
    assert world.observable_items("observer", "unknown") == (
        "apple",
        "book",
        "coin",
        "deep",
        "hidden",
        "luggage",
        "z_item",
    )
    assert world.observable_items("unknown", None) == ("cycle_a", "cycle_b", "unplaced")


def test_required_observations_filters_visibility_and_under_relation():
    world = make_world()
    visible = {"apple", "deep", "coin", "book", "hidden"}
    assert world.required_observations("observer", "apple", visible) == {"apple"}
    assert world.set_axis("box", "open").ok
    assert world.required_observations("observer", "box", visible) == {"apple", "deep"}
    assert world.required_observations("observer", "table", visible, kind="under") == {"coin"}
    assert world.required_observations("observer", "table", visible) == {"book", "coin"}
    assert world.required_observations("observer", None, visible) == set()
    assert world.required_observations("observer", "unknown", visible) == set()


def test_moved_since_returns_ids_sorted_by_the_names_used_by_storygame():
    world = make_world()
    before = {"apple": "box", "deep": "nested", "book": None, "fixed": "hall", "unknown": "hall"}
    assert world.move("apple", "table").ok
    assert world.moved_since(before) == ("apple",)
    assert world.moved_since(before, excluded_ids=("apple",)) == ()


def test_schema_area_helpers_include_nested_ancestors_and_descendants():
    schema = make_world().schema
    assert schema.related_areas("hall") == frozenset({"root", "hall", "gallery"})
    assert schema.related_areas("root") == frozenset({"root", "hall", "gallery", "other"})
    assert schema.area_ancestors("gallery") == frozenset({"hall", "root"})
    assert schema.area_ancestors("root") == frozenset()
    assert schema.area_ancestors("unknown") == frozenset()


def test_current_seat_and_reachable_from_seat_use_visible_world_entities():
    world = make_world()
    assert world.current_seat("observer") is None
    assert world.move("observer", "seat").ok
    assert world.current_seat("observer") == "seat"
    assert world.current_seat("unknown") is None
    assert world.reachable_from_seat("seat", "observer") == ("luggage", "seat", "vehicle")


def test_takeable_items_filter_area_visibility_kind_fixed_and_holder():
    world = make_world()
    assert world.move("apple", "hall").ok
    assert world.move("luggage", "observer").ok
    assert world.move("companion", "hall").ok
    assert world.set_companion("companion", "observer").ok
    assert world.takeable_items(("apple", "vehicle", "fixed", "hidden", "unplaced", "luggage"), "observer") == (
        "apple",
    )
    assert world.takeable_items(("apple",), "observer", fixed_ids=("apple",)) == ()


def test_fixed_visible_items_support_default_and_explicit_scopes():
    world = make_world()
    assert world.fixed_visible_items(("fixed", "hidden", "box", "unknown"), "observer") == ("fixed",)
    assert world.fixed_visible_items(("fixed", "hidden"), "observer", scope_ids=("hidden",)) == ()
    assert world.fixed_visible_items(("fixed",), "unknown") == ()


def test_visible_vehicle_seats_matches_visible_world_seats_and_order():
    world = make_world()
    assert world.visible_vehicle_seats(("vehicle", "box", "unknown")) == (("vehicle", ("seat",)),)
    world._replace("wk_hidden", "seat", "true")
    assert world.visible_vehicle_seats(("vehicle",)) == (("vehicle", ()),)
