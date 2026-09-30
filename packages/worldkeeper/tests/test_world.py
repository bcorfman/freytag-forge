from worldkeeper import MemoryBackend, SchemaError, World, WorldSchema


def make():
    s = WorldSchema.from_data(
        {
            "kinds": [{"id": "desk", "is": ["furniture", "supporter"]}],
            "entities": [
                {"id": "village", "name": "the village", "kind": "area"},
                {"id": "parlour", "name": "parlour", "kind": "area", "parent": "village"},
                {"id": "ada", "name": "Ada Lovell", "kind": "character", "aliases": ["Ada"]},
                {"id": "bo", "name": "Bo", "kind": "character"},
                {
                    "id": "chest",
                    "name": "oak chest",
                    "kind": "container",
                    "openable": True,
                    "fixed": True,
                    "contents": ["quills"],
                },
                {
                    "id": "lamp",
                    "name": "lamp",
                    "kind": "thing",
                    "axes": [{"poles": ["lit", "dark"], "aliases": {"burning": "lit"}, "initial": "dark"}],
                },
                {"id": "key", "name": "brass key", "kind": "thing", "hidden": True},
                {"id": "desk1", "name": "desk", "kind": "desk"},
            ],
        }
    )
    w = World(s, MemoryBackend())
    assert w.seed().ok
    return w


def test_queries_and_state():
    w = make()
    assert w.is_a("chest", "thing")
    assert w.parent("chest_quills") == "chest"
    assert w.is_hidden("key")
    assert w.set_axis("lamp", "burning").ok and w.axis_values("lamp")["lit"] == "lit"
    assert w.move("ada", "parlour").ok
    assert w.apply_effects([{"move": "chest", "parent": "parlour"}])[0].ok
    assert w.move("chest_quills", "ada").ok and w.relation("chest_quills") == "carried_by"
    assert w.together("ada", "chest_quills")
    assert w.set_conditions("ada", ["tired"]).ok and w.conditions("ada") == ("tired",)
    assert w.set_status("ada", "incapacitated").ok and w.status("ada") == "incapacitated"


def test_created_area_character_and_group_persist_and_follow_placement_rules():
    w = make()
    annex = w.create("annex", parent="village", kind="area")
    character = w.create("new person", parent=annex.id, kind="character")
    group = w.create("prisoners", parent=annex.id, kind="group")
    assert annex.ok and character.ok and group.ok
    assert w.parent(annex.id) == "village"
    assert w.relation(annex.id) == "in"
    assert w.chain(annex.id) == ("village",)
    assert w.area(annex.id) == annex.id
    assert w.is_a(annex.id, "area")
    assert not w.move(annex.id, "parlour").ok
    assert not w.move("lamp", group.id).ok
    assert not w.move("ada", group.id).ok
    assert w.move(group.id, "village").ok

    rebuilt = World(w.schema, w.backend)
    assert rebuilt.parent(annex.id) == "village"
    assert rebuilt.chain(annex.id) == ("village",)
    assert rebuilt.area(annex.id) == annex.id
    assert rebuilt.kind(group.id) == "group"


def test_together_includes_nested_areas_but_not_siblings_or_unplaced():
    w = make()
    w.schema = WorldSchema.from_data(
        {
            "entities": [
                {"id": "house", "name": "house", "kind": "area"},
                {"id": "kitchen", "name": "kitchen", "kind": "area", "parent": "house"},
                {"id": "bedroom", "name": "bedroom", "kind": "area", "parent": "house"},
                {"id": "phone", "name": "phone", "kind": "thing"},
                {"id": "lamp", "name": "lamp", "kind": "thing"},
                {"id": "ada", "name": "Ada", "kind": "character"},
            ]
        }
    )
    w = World(w.schema, MemoryBackend())
    assert w.seed().ok
    assert w.place("phone", "kitchen").ok and w.place("lamp", "bedroom").ok and w.place("ada", "house").ok
    assert w.together("ada", "phone")
    assert w.together("phone", "ada")
    assert not w.together("phone", "lamp")
    assert not w.together("phone", "missing")


def test_refusals_and_place_effects():
    w = make()
    assert not w.move("key", "village").ok
    assert w.reveal("key").ok
    assert w.place("key", "village", text="by the door").ok
    assert w.place_label("key") == "by the door"
    assert w.move("key", "parlour").ok
    assert w.place_label("key") == "parlour"
    assert not w.move("chest", "key").ok
    assert not w.move("ada", "key").ok
    assert not w.set_axis("lamp", "nope").ok
    assert not w.set_conditions("ada", ["x", "y", "z"]).ok
    assert not w.set_status("ada", "gone").ok
    assert not w.place("village", "parlour").ok
    assert not w.place("lamp", "ada", part_of=True).ok
    assert w.set_unplaced("lamp", "the lane").ok and w.parent("lamp") is None and w.unplaced_name("lamp") == "the lane"


def test_move_effect_text_lasts_until_holder_moves():
    w = make()
    assert w.apply_effects([{"move": "key", "parent": "ada", "text": "in Ada's pocket"}, {"reveal": "key"}])[0].ok
    assert w.place_text("key") == "in Ada's pocket"
    assert w.place_label("key") == "in Ada's pocket"
    assert w.move("ada", "parlour").ok
    assert w.place_text("key") is None
    assert w.place_label("key") == "Ada Lovell"


def test_closed_companion_create_resolution_effects_and_backend_rebuild():
    w = make()
    assert w.move("ada", "village").ok
    assert w.move("bo", "village").ok
    assert w.set_companion("bo", "ada").ok
    assert w.move("ada", "parlour").ok and w.parent("bo") == "parlour"
    assert w.clear_companion("bo").ok
    assert w.set_axis("chest", "closed").ok
    assert w.apply_effects([{"move": "chest", "parent": "parlour"}])[0].ok
    assert not w.is_visible("quills")
    assert w.apply_effects(
        [{"reveal": "key"}, {"move": "key", "parent": "parlour"}, {"set_axis": "chest", "value": "open"}]
    )[1].ok
    r = w.create("silver coin", "parlour")
    assert r.ok and r.id == "n_silver_coin_1"
    assert w.create("silver  coin").id == "n_silver_coin_2"
    assert w.resolve("the parlour floor") == "parlour" and w.resolve("Ada's hands") == "ada"
    assert w.resolve("unknown") is None
    w2 = World(w.schema, w.backend)
    assert w2.parent("n_silver_coin_1") == "parlour" and w2.status("chest") is None


def test_owner_possessive_names_resolve_from_names_and_aliases():
    schema = WorldSchema.from_data(
        {
            "entities": [
                {"id": "owner", "name": "keeper", "kind": "character", "aliases": ["K"]},
                {"id": "thing", "name": "tool", "kind": "thing", "aliases": ["implement"], "owner": "owner"},
            ]
        }
    )
    w = World(schema, MemoryBackend())
    assert w.seed().ok
    assert w.resolve("keeper's tool") == "thing"
    assert w.resolve("the k's implement") == "thing"


def test_learned_aliases_are_fact_backed_and_refuse_conflicts():
    w = make()
    before = set(w.backend.matching_all())

    assert w.add_alias("lamp", "the glowing lamp").ok
    assert w.resolve("glowing lamp") == "lamp"
    assert w.add_alias("lamp", "the glowing lamp").ok
    assert set(w.backend.matching_all()) == before | {
        next(fact for fact in w.backend.matching_all() if fact.predicate == "wk_alias")
    }

    after_alias = set(w.backend.matching_all())
    unknown = w.add_alias("missing", "unknown name")
    assert not unknown.ok and unknown.reason == "unknown entity"
    empty = w.add_alias("lamp", "")
    assert not empty.ok and empty.reason == "alias name must not be empty"
    non_text = w.add_alias("lamp", None)
    assert not non_text.ok and non_text.reason == "alias name must not be empty"
    conflict = w.add_alias("lamp", "Ada")
    assert not conflict.ok and conflict.reason == "alias already resolves to a different entity"
    assert set(w.backend.matching_all()) == after_alias

    rebuilt = World(w.schema, w.backend)
    assert rebuilt.resolve("the glowing lamp") == "lamp"


def test_add_alias_does_not_call_resolver():
    calls = []
    w = World(make().schema, MemoryBackend(), resolver=lambda name, ids: calls.append((name, ids)) or "lamp")

    assert w.add_alias("lamp", "new name").ok
    assert calls == []


def test_also_called_names_include_declared_and_learned_names_in_order():
    w = make()
    w.schema.entities["lamp"].aliases = ("light", "lamp")

    assert w.names("lamp") == ("lamp", "light")
    assert w.add_alias("lamp", "glowing lamp").ok
    assert w.names("lamp") == ("lamp", "light", "glowing lamp")
    assert w.names("missing") == ()


def test_schema_errors_and_resolver():
    for data in ({"kinds": [{"id": "x", "is": ["x"]}]}, {"entities": [{"id": "a", "name": "a", "kind": "missing"}]}):
        try:
            WorldSchema.from_data(data)
            assert False
        except SchemaError:
            pass
    s = WorldSchema.from_data(
        {"entities": [{"id": "a", "name": "coin", "kind": "thing"}, {"id": "b", "name": "coin", "kind": "thing"}]}
    )
    w = World(s, MemoryBackend(), resolver=lambda n, c: "b")
    assert w.resolve("coin") == "b"
