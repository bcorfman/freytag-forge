import re

import pytest

from worldkeeper import MemoryBackend, World, WorldSchema


def regression_schema():
    return WorldSchema.from_data(
        {
            "entities": [
                {"id": "room", "name": "room", "kind": "area"},
                {
                    "id": "cleo",
                    "name": "Cleo",
                    "kind": "character",
                    "axes": [{"poles": ["awake", "asleep"]}],
                },
                {
                    "id": "box",
                    "name": "box",
                    "kind": "container",
                    "openable": True,
                    "axes": [{"poles": ["dry", "wet"]}],
                },
                {"id": "coin", "name": "coin", "kind": "thing"},
                {"id": "table", "name": "table", "kind": "supporter"},
            ]
        }
    )


def test_all_axes_are_seeded_and_written_independently():
    world = World(regression_schema(), MemoryBackend())

    assert world.seed().ok
    assert world.axis_values("cleo") == {"captive": "free", "awake": "awake"}
    assert world.axis_values("box") == {"open": "closed", "dry": "dry"}
    assert world.set_axis("box", "dry").ok
    assert world.set_axis("box", "open").ok
    assert world.axis_values("box") == {"open": "open", "dry": "dry"}


def test_created_entities_are_rebuilt_only_from_backend_facts():
    backend = MemoryBackend()
    world = World(regression_schema(), backend)
    snapshot = set(backend.matching_all())
    created = world.create("pebble", "room")
    assert created.ok and world.name(created.id) == "pebble"

    # Emulate restoring the host store to its pre-create snapshot.
    for fact in tuple(backend.matching_all()):
        backend.retract_fact(fact)
    for fact in snapshot:
        backend.assert_fact(fact)
    assert not world.exists(created.id)
    assert world.resolve("pebble") is None
    recreated = world.create("pebble", "room")
    assert recreated.id == created.id


def test_seed_is_additive_after_play():
    world = World(regression_schema(), MemoryBackend())
    assert world.seed().ok
    assert world.move("cleo", "room").ok
    assert world.set_axis("cleo", "asleep").ok
    assert world.set_unplaced("coin", "far beyond the old stone gate").ok
    assert world.seed().ok
    assert world.axis_values("cleo")["awake"] == "asleep"
    assert world.parent("cleo") == "room"
    assert world.parent("coin") is None
    assert world.unplaced_name("coin") == "far beyond the old stone gate"


def test_story_kind_inherits_furniture_fixed_default():
    schema = WorldSchema.from_data(
        {
            "kinds": [{"id": "desk", "is": ["furniture", "supporter"]}],
            "entities": [
                {"id": "room", "name": "room", "kind": "area"},
                {"id": "desk", "name": "desk", "kind": "desk"},
            ],
        }
    )
    world = World(schema, MemoryBackend())
    assert world.seed().ok
    assert not world.move("desk", "room").ok


class StrictFact:
    def __init__(self, *, predicate, subject, object=None, value=None):
        assert re.fullmatch(r"wk_[a-z][a-z0-9_]*", predicate)
        assert len(subject) <= 120
        assert object is None or len(object) <= 120
        self.predicate, self.subject, self.object, self.value = predicate, subject, object, value

    def __hash__(self):
        return hash((self.predicate, self.subject, self.object, self.value))

    def __eq__(self, other):
        return (self.predicate, self.subject, self.object, self.value) == (
            other.predicate,
            other.subject,
            other.object,
            other.value,
        )


class StrictBackend(MemoryBackend):
    def matching(self, predicate, subject=None):
        return tuple(
            sorted(
                super().matching(predicate, subject),
                key=lambda fact: (fact.predicate, fact.subject, fact.object or "", fact.value or ""),
            )
        )


def test_free_text_is_stored_in_value_for_strict_hosts():
    backend = StrictBackend()
    world = World(regression_schema(), backend, make_fact=StrictFact)
    long_text = "a very long authored placement " * 50
    assert world.place("coin", "room", text=long_text).ok
    assert world.set_unplaced("coin", long_text).ok
    assert world.create("new " + "name " * 10, "room").ok
    assert world.set_conditions("coin", ["the " + "condition " * 3]).ok
    for fact in backend.matching_all():
        assert fact.object is None or len(fact.object) <= 120


def companion_world():
    schema = WorldSchema.from_data(
        {
            "entities": [
                {"id": "hall", "name": "hall", "kind": "area"},
                {"id": "yard", "name": "yard", "kind": "area"},
                {"id": "attic", "name": "attic", "kind": "area"},
                {"id": "leader", "name": "leader", "kind": "character"},
                {"id": "companion", "name": "companion", "kind": "character"},
                {"id": "stray", "name": "stray", "kind": "character"},
            ]
        }
    )
    world = World(schema, MemoryBackend())
    assert world.seed().ok
    assert world.move("leader", "hall").ok
    assert world.move("companion", "hall").ok
    assert world.move("stray", "attic").ok
    assert world.set_companion("companion", "leader").ok
    assert world.set_companion("stray", "leader").ok
    return world


def test_story_effect_move_carries_companions_in_the_old_place():
    world = companion_world()

    assert world.apply_effects([{"move": "leader", "parent": "yard"}])[0].ok
    assert world.parent("companion") == "yard"
    assert world.parent("stray") == "attic"


def test_move_does_not_carry_companions_when_leader_is_unplaced():
    world = companion_world()
    world.set_unplaced("leader", "the road")
    world.set_unplaced("companion", "the road")
    world.set_unplaced("stray", "the road")

    assert world.move("leader", "hall").ok
    assert world.parent("companion") is None
    assert world.parent("stray") is None


def test_story_effect_move_does_not_carry_companions_when_leader_is_unplaced():
    world = companion_world()
    world.set_unplaced("leader", "the road")
    world.set_unplaced("companion", "the road")
    world.set_unplaced("stray", "the road")

    assert world.apply_effects([{"move": "leader", "parent": "hall"}])[0].ok
    assert world.parent("companion") is None
    assert world.parent("stray") is None


def test_create_rejects_removed_parent_id_keyword():
    with pytest.raises(TypeError):
        companion_world().create("new thing", parent_id="hall")


def test_only_in_transfers_open_a_closed_container():
    world = World(regression_schema(), MemoryBackend())
    world.seed()
    assert world.place("coin", "box", under=True).ok
    assert world.set_axis("box", "closed").ok
    assert world.move("coin", "table", under=True).ok
    assert world.axis_values("box")["open"] == "closed"
    assert world.place("coin", "box").ok
    assert world.set_axis("box", "closed").ok
    assert world.move("coin", "room").ok
    assert world.axis_values("box")["open"] == "open"


def test_conditions_retain_input_order():
    world = World(regression_schema(), MemoryBackend())
    world.seed()
    assert world.set_conditions("cleo", ["first phrase", "second phrase"]).ok
    assert world.conditions("cleo") == ("first phrase", "second phrase")
