from worldkeeper import MemoryBackend, World, WorldSchema


def make_world():
    schema = WorldSchema.from_data(
        {
            "entities": [
                {"id": "room", "name": "room", "kind": "area"},
                {"id": "alice", "name": "alice", "kind": "character"},
                {"id": "bob", "name": "bob", "kind": "character"},
                {"id": "item", "name": "item", "kind": "thing"},
                {"id": "box", "name": "box", "kind": "container"},
            ]
        }
    )
    world = World(schema, MemoryBackend())
    assert world.seed().ok
    for entity_id in ("alice", "bob", "item", "box"):
        assert world.move(entity_id, "room").ok
    return world


def test_holds_direct_and_area_placements():
    world = make_world()

    assert world.move("item", "alice").ok
    assert world.holds("alice", "item")
    assert not world.holds("bob", "item")
    assert world.move("item", "room").ok
    assert not world.holds("alice", "item")
    assert not world.holds("bob", "item")


def test_holds_nested_and_reassigned_placements():
    world = make_world()

    assert world.move("item", "box").ok
    assert world.move("box", "alice").ok
    assert world.holds("alice", "item")
    assert world.move("item", "bob").ok
    assert not world.holds("alice", "item")
    assert world.holds("bob", "item")


def test_holds_none_is_false():
    world = make_world()

    assert not world.holds(None, "item")
