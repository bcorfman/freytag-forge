from worldkeeper import MemoryBackend, World, WorldSchema


def make_world():
    schema = WorldSchema.from_data(
        {
            "kinds": [{"id": "people", "is": ["group"]}],
            "entities": [
                {"id": "room", "name": "room", "kind": "area"},
                {"id": "nested", "name": "nested", "kind": "area", "parent": "room"},
                {"id": "other", "name": "other", "kind": "area"},
                {"id": "box", "name": "box", "kind": "container", "openable": True, "enterable": True},
                {"id": "hero", "name": "hero", "kind": "character"},
                {"id": "same", "name": "same", "kind": "character"},
                {"id": "nested_person", "name": "nested person", "kind": "character"},
                {"id": "other_person", "name": "other person", "kind": "character"},
                {"id": "hidden", "name": "hidden", "kind": "character", "hidden": True},
                {"id": "shut", "name": "shut", "kind": "character"},
                {"id": "missing", "name": "missing", "kind": "character"},
                {"id": "companion", "name": "companion", "kind": "character"},
                {"id": "walked_off", "name": "walked off", "kind": "character"},
                {"id": "captives", "name": "captives", "kind": "people"},
                {"id": "group_member", "name": "group member", "kind": "character"},
                {"id": "direct", "name": "direct", "kind": "character"},
            ],
        }
    )
    world = World(schema, MemoryBackend())
    assert world.seed().ok
    for entity_id in ("hero", "same", "missing", "companion", "direct", "box", "captives"):
        assert world.move(entity_id, "room").ok
    assert world.move("nested_person", "nested").ok
    assert world.move("other_person", "other").ok
    assert world.move("shut", "box").ok
    assert world.move("group_member", "captives").ok
    assert world.move("walked_off", "other").ok
    assert world.set_status("missing", "missing").ok
    assert world.set_axis("box", "closed").ok
    assert world.set_companion("companion", "hero").ok
    assert world.set_companion("walked_off", "hero").ok
    return world


def test_people_alongside_filters_visibility_spot_companions_and_groups():
    world = make_world()

    assert world.people_alongside("hero") == ("direct", "same")


def test_people_alongside_excludes_entity_and_companions_even_when_companion_walks_off():
    world = make_world()

    assert "hero" not in world.people_alongside("hero")
    assert "companion" not in world.people_alongside("hero")
    # A companion who walked to another area is also absent because it is not alongside.
    assert "walked_off" not in world.people_alongside("hero")
