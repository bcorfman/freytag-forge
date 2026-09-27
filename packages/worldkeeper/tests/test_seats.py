import pytest

from worldkeeper import MemoryBackend, SchemaError, World, WorldSchema


def world(*, seat_kind=True, enterable=None, vehicle_enterable=None, hidden_seat=False):
    kinds = [{"id": "seat", "is": ["supporter"], "enterable": True}] if seat_kind else []
    if vehicle_enterable is not None:
        kinds.append({"id": "van", "is": ["vehicle"], "enterable": vehicle_enterable})
    entities = [
        {"id": "room", "name": "room", "kind": "area"},
        {"id": "person", "name": "person", "kind": "character"},
        {"id": "table", "name": "table", "kind": "supporter"},
        {"id": "box", "name": "box", "kind": "container"},
        {
            "id": "chair",
            "name": "chair",
            "kind": "seat" if seat_kind else "supporter",
            "enterable": enterable,
            "hidden": hidden_seat,
            "axes": [{"poles": ["empty", "occupied"], "initial": "empty"}],
            "enter_pole": "occupied" if (enterable or seat_kind) else None,
            "seat_for": "table" if (enterable or seat_kind) else None,
        },
    ]
    if vehicle_enterable is not None:
        entities.append({"id": "van", "name": "van", "kind": "van"})
    schema = WorldSchema.from_data({"kinds": kinds, "entities": entities})
    result = World(schema, MemoryBackend())
    result.seed()
    return result


def test_enterable_supporter_holds_character_and_sets_pole():
    w = world()
    assert w.move("person", "chair").ok
    assert w.parent("person") == "chair"
    assert w.relation("person") == "on"
    assert "occupied" in w.axis_values("chair").values()


@pytest.mark.parametrize("parent", ["table", "box"])
def test_character_refuses_non_enterable_parents(parent):
    w = world()
    result = w.move("person", parent)
    assert not result.ok
    assert result.reason.startswith("characters can only be in")


def test_vehicle_is_enterable_by_kind():
    w = world(vehicle_enterable=True)
    assert w.move("person", "van").ok


def test_entity_enterable_overrides_kind_defaults():
    assert world(seat_kind=False, enterable=True).is_enterable("chair")
    data = {
        "kinds": [{"id": "van", "is": ["vehicle"], "enterable": True}],
        "entities": [{"id": "van", "name": "van", "kind": "van", "enterable": False}],
    }
    assert not WorldSchema.from_data(data).entities["van"].enterable


def test_move_effect_enters_but_place_does_not():
    w = world()
    assert w.place("person", "chair").ok
    assert w.axis_values("chair")["empty"] == "empty"
    w = world()
    assert w.apply_effects([{"move": "person", "parent": "chair"}])[0].ok
    assert "occupied" in w.axis_values("chair").values()


def test_moving_seat_carries_sitter_and_seats_are_visible_in_declaration_order():
    w = world()
    assert w.move("person", "chair").ok
    assert w.move("chair", "table").ok
    assert w.parent("person") == "chair"
    assert w.seats("table") == ("chair",)
    hidden = world(hidden_seat=True)
    assert hidden.seats("table") == ()


@pytest.mark.parametrize(
    "entity, update, message",
    [
        ("plain", {"kind": "thing", "enterable": True}, "enterable entities"),
        ("plain", {"kind": "thing", "enter_pole": "x"}, "enterable entity"),
        ("plain", {"kind": "thing", "seat_for": "room"}, "enterable entity"),
    ],
)
def test_invalid_seat_schema(entity, update, message):
    data = {"entities": [{"id": "room", "name": "room", "kind": "area"}, {"id": entity, "name": entity, **update}]}
    with pytest.raises(SchemaError, match=message):
        WorldSchema.from_data(data)


def test_enterable_kind_must_be_container_or_supporter():
    with pytest.raises(SchemaError, match="enterable kinds"):
        WorldSchema.from_data({"kinds": [{"id": "bad", "is": ["thing"], "enterable": True}]})


def test_seat_for_unknown_entity_is_rejected():
    with pytest.raises(SchemaError, match="unknown entity"):
        WorldSchema.from_data(
            {"entities": [{"id": "x", "name": "x", "kind": "container", "enterable": True, "seat_for": "missing"}]}
        )


def test_kind_declares_fixed_nearest_wins():
    schema = WorldSchema.from_data(
        {
            "kinds": [
                {"id": "movable_furniture", "is": ["furniture"], "fixed": False},
                {"id": "inherited", "is": ["movable_furniture"]},
                {"id": "deep_fixed", "is": ["inherited"], "fixed": True},
            ],
            "entities": [
                {"id": "movable", "name": "movable", "kind": "movable_furniture"},
                {"id": "inherited_item", "name": "inherited item", "kind": "inherited"},
                {"id": "deep", "name": "deep", "kind": "deep_fixed"},
                {"id": "own", "name": "own", "kind": "deep_fixed", "fixed": False},
            ],
        }
    )

    assert schema.is_fixed("movable") is False
    assert schema.is_fixed("inherited_item") is False
    assert schema.is_fixed("deep") is True
    assert schema.is_fixed("own") is False
