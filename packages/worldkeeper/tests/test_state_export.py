from copy import deepcopy

from worldkeeper import Fact, MemoryBackend, World, WorldSchema, diff_states
from worldkeeper.state_export import WORLD_PREDICATES


def make_world():
    schema = WorldSchema.from_data(
        {
            "entities": [
                {"id": "house", "name": "house", "kind": "area"},
                {"id": "room", "name": "room", "kind": "area", "parent": "house"},
                {"id": "hero", "name": "hero", "kind": "character"},
                {"id": "friend", "name": "friend", "kind": "character"},
                {
                    "id": "box",
                    "name": "box",
                    "kind": "container",
                    "openable": True,
                    "axes": [{"poles": ["red", "blue"], "initial": "red"}],
                },
                {"id": "coin", "name": "coin", "kind": "thing", "hidden": True},
            ],
        }
    )
    world = World(schema, MemoryBackend())
    assert world.seed().ok
    for entity_id in ("hero", "friend", "box"):
        assert world.move(entity_id, "room").ok
    assert world.reveal("coin").ok
    assert world.move("coin", "room").ok
    return world


def test_export_lists_every_known_world_fact_and_drift_is_visible():
    world = make_world()
    assert world.move("coin", "box").ok
    assert world.move("box", "hero").ok
    assert world.reveal("coin").ok
    assert world.set_axis("box", "blue").ok
    assert world.add_alias("coin", "penny").ok
    assert world.set_companion("friend", "hero").ok
    assert world.set_conditions("hero", ["tired"]).ok
    assert world.set_status("hero", "incapacitated").ok

    exported = {
        (fact["predicate"], fact["subject"], fact["object"], fact["value"]) for fact in world.export_state()["facts"]
    }
    backend_facts = {
        (fact.predicate, fact.subject, fact.object, fact.value)
        for fact in world.backend.matching_all()
        if fact.predicate.startswith("wk_")
    }
    assert backend_facts == exported
    assert set(WORLD_PREDICATES) == {
        "wk_alias",
        "wk_axis",
        "wk_companion",
        "wk_condition",
        "wk_facet",
        "wk_fixed",
        "wk_hidden",
        "wk_incidental",
        "wk_kind",
        "wk_moved",
        "wk_name",
        "wk_owner",
        "wk_parent",
        "wk_place_text",
        "wk_relation",
        "wk_seeded",
        "wk_status",
        "wk_unplaced",
    }


def test_export_import_round_trip_replaces_existing_state():
    source = make_world()
    assert source.add_alias("coin", "penny").ok
    assert source.set_axis("box", "blue").ok
    snapshot = source.export_state()

    target = make_world()
    assert target.add_alias("coin", "wrong name").ok
    assert target.move("friend", "house").ok
    assert target.import_state(snapshot).ok

    assert target.export_state() == snapshot


def test_import_refuses_unknown_schema_predicate_and_subject_without_changes():
    world = make_world()
    before = world.export_state()
    for invalid in (
        {**deepcopy(before), "schema": 2},
        {**deepcopy(before), "facts": [{"predicate": "wk_nope", "subject": "hero", "object": None, "value": None}]},
        {**deepcopy(before), "facts": [{"predicate": "wk_name", "subject": "unknown", "object": None, "value": "x"}]},
    ):
        result = world.import_state(invalid)
        assert not result.ok
        assert world.export_state() == before


def test_entry_problems_accept_sound_state():
    world = make_world()
    assert world.entry_problems("hero", "room") == ()


def test_entry_problems_find_parent_cardinality_and_missing_parent():
    world = make_world()
    world.backend.assert_fact(Fact("wk_parent", "hero", value="missing"))
    assert any("hero" in problem for problem in world.entry_problems("hero", "room"))


def test_entry_problems_find_parent_cycle():
    world = make_world()
    world.backend.retract_fact(next(fact for fact in world.backend.matching("wk_parent", "hero")))
    world.backend.assert_fact(Fact("wk_parent", "hero", value="friend"))
    world.backend.retract_fact(next(fact for fact in world.backend.matching("wk_parent", "friend")))
    world.backend.assert_fact(Fact("wk_parent", "friend", value="hero"))
    assert any("hero" in problem or "friend" in problem for problem in world.entry_problems("hero", "room"))


def test_entry_problems_find_protagonist_location_hidden_held_axis_and_companion():
    world = make_world()
    assert world.move("coin", "hero").ok
    world.backend.assert_fact(Fact("wk_hidden", "coin", value="true"))
    world.backend.assert_fact(Fact("wk_axis", "box", "open", "not-a-pole"))
    world.backend.assert_fact(Fact("wk_companion", "friend", "missing"))

    problems = world.entry_problems("hero", "room")
    assert any("coin" in problem for problem in problems)
    assert any("box" in problem for problem in problems)
    assert any("friend" in problem for problem in problems)
    assert any("missing-hero" in problem for problem in world.entry_problems("missing-hero", "room"))


def test_entry_problems_rejects_wrong_location():
    world = make_world()
    assert any("hero" in problem and "house" in problem for problem in world.entry_problems("hero", "house")) is False
    assert any("hero" in problem for problem in world.entry_problems("hero", "elsewhere"))


def test_export_order_is_deterministic():
    first = make_world()
    second = World(first.schema, MemoryBackend())
    assert second.seed().ok
    assert second.reveal("coin").ok
    for entity_id, parent_id in (("coin", "room"), ("box", "hero"), ("friend", "room"), ("hero", "room")):
        assert second.move(entity_id, parent_id).ok
    assert first.move("coin", "room").ok
    assert first.move("box", "hero").ok
    assert first.move("friend", "room").ok
    assert first.move("hero", "room").ok
    assert first.export_state() == second.export_state()


def test_diff_states_groups_changes_by_predicate_and_subject():
    before = {
        "schema": 1,
        "facts": [
            {"predicate": "wk_name", "subject": "coin", "object": None, "value": "coin"},
            {"predicate": "wk_hidden", "subject": "coin", "object": "true", "value": None},
            {"predicate": "wk_name", "subject": "old", "object": None, "value": "old"},
        ],
    }
    after = {
        "schema": 1,
        "facts": [
            {"predicate": "wk_name", "subject": "coin", "object": None, "value": "penny"},
            {"predicate": "wk_hidden", "subject": "coin", "object": "true", "value": None},
            {"predicate": "wk_alias", "subject": "coin", "object": None, "value": "penny"},
        ],
    }

    assert diff_states(before, after) == {
        "added": [{"predicate": "wk_alias", "subject": "coin", "object": None, "value": "penny"}],
        "removed": [{"predicate": "wk_name", "subject": "old", "object": None, "value": "old"}],
        "changed": [
            {
                "predicate": "wk_name",
                "subject": "coin",
                "before": [{"predicate": "wk_name", "subject": "coin", "object": None, "value": "coin"}],
                "after": [{"predicate": "wk_name", "subject": "coin", "object": None, "value": "penny"}],
            }
        ],
    }
