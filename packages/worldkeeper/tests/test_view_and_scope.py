import pytest

from worldkeeper import MemoryBackend, SchemaError, World, WorldSchema


def _world(data):
    world = World(WorldSchema.from_data(data), MemoryBackend())
    assert world.seed().ok
    return world


def _vehicle_data(extra=(), **vehicle):
    return {
        "entities": [
            {"id": "yard", "name": "yard", "kind": "area"},
            {"id": "observer", "name": "observer", "kind": "character"},
            {"id": "vehicle", "name": "vehicle", "kind": "vehicle", **vehicle},
            {"id": "cargo", "name": "cargo", "kind": "thing"},
            *extra,
        ]
    }


def test_default_queries_and_vehicle_visibility_keep_current_behavior():
    world = _world(_vehicle_data())
    assert world.move("observer", "yard").ok
    assert world.move("vehicle", "yard").ok
    assert world.move("cargo", "vehicle").ok

    assert world.is_visible("cargo")
    assert not world.sees("observer", "cargo")
    assert world.contents_complete("vehicle") is False

    assert world.move("observer", "vehicle").ok
    assert world.sees("observer", "cargo")


def test_declared_view_is_visible_from_place_until_blocked():
    world = _world(
        _vehicle_data(
            extra=(
                {
                    "id": "barrier",
                    "name": "barrier",
                    "kind": "thing",
                    "axes": [{"poles": ["clear", "holding"]}],
                },
            ),
            view=[{"from": "yard", "blocked_by": {"axis": "barrier", "pole": "holding"}}],
        )
    )
    assert world.move("observer", "yard").ok
    assert world.move("vehicle", "yard").ok
    assert world.move("cargo", "vehicle").ok
    assert world.sees("observer", "cargo")

    assert world.set_axis("barrier", "holding").ok
    assert not world.sees("observer", "cargo")


@pytest.mark.parametrize(
    "declaration, message",
    [
        ({"view": "yard"}, "view"),
        ({"view": [{"from": "missing"}]}, "view from"),
        ({"view": [{"from": "yard", "blocked_by": "barrier"}]}, "blocked_by"),
        ({"view": [{"from": "yard", "blocked_by": {"axis": "missing", "pole": "clear"}}]}, "axis"),
        ({"view": [{"from": "yard", "blocked_by": {"axis": "barrier", "pole": "missing"}}]}, "pole"),
        ({"contents_complete": "yes"}, "contents_complete"),
    ],
)
def test_view_and_scope_declarations_are_validated(declaration, message):
    with pytest.raises(SchemaError, match=message):
        WorldSchema.from_data(
            {
                "entities": [
                    {"id": "yard", "name": "yard", "kind": "area"},
                    {"id": "barrier", "name": "barrier", "kind": "thing", "axes": [{"poles": ["clear", "holding"]}]},
                    {"id": "vehicle", "name": "vehicle", "kind": "vehicle", **declaration},
                ]
            }
        )


def test_contents_complete_defaults_false_and_accepts_true():
    world = _world(
        {
            "entities": [
                {"id": "room", "name": "room", "kind": "area"},
                {"id": "complete", "name": "complete", "kind": "container", "contents_complete": True},
                {"id": "open", "name": "open", "kind": "container"},
            ]
        }
    )
    assert world.contents_complete("complete") is True
    assert world.contents_complete("open") is False
