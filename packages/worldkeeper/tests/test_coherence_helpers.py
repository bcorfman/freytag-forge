from worldkeeper import MemoryBackend, World, WorldSchema


def make_world():
    schema = WorldSchema.from_data(
        {
            "entities": [
                {"id": "atrium", "name": "atrium", "kind": "area"},
                {"id": "gallery", "name": "gallery", "kind": "area", "parent": "atrium"},
                {"id": "isolated", "name": "isolated", "kind": "area"},
                {"id": "zara", "name": "zara", "kind": "character"},
                {"id": "alice", "name": "alice", "kind": "character"},
                {"id": "bob", "name": "bob", "kind": "character"},
                {"id": "item", "name": "item", "kind": "thing"},
            ]
        }
    )
    world = World(schema, MemoryBackend())
    assert world.seed().ok
    return world


def test_characters_together_same_and_nested_areas():
    world = make_world()
    for entity_id in ("zara", "alice", "bob", "item"):
        assert world.move(entity_id, "atrium").ok
    assert world.move("bob", "gallery").ok

    assert world.characters_together("zara") == ("alice", "bob")
    assert world.characters_together("alice") == ("bob", "zara")


def test_characters_together_excludes_separate_unplaced_and_self():
    world = make_world()
    assert world.move("zara", "atrium").ok
    assert world.move("alice", "atrium").ok
    assert world.move("bob", "isolated").ok

    assert world.characters_together("zara") == ("alice",)
    assert world.characters_together("bob") == ()


def test_apart_for_separate_placed_entities():
    world = make_world()
    assert world.move("zara", "atrium").ok
    assert world.move("alice", "isolated").ok

    assert world.apart("zara", "alice")


def test_apart_false_for_same_nested_or_unplaced_entities():
    world = make_world()
    assert world.move("zara", "atrium").ok
    assert world.move("alice", "atrium").ok
    assert not world.apart("zara", "alice")

    assert world.move("bob", "gallery").ok
    assert not world.apart("zara", "bob")
    assert not world.apart("zara", "item")


def test_apart_true_for_item_in_another_area():
    world = make_world()
    assert world.move("zara", "atrium").ok
    assert world.move("item", "isolated").ok

    assert world.apart("zara", "item")
