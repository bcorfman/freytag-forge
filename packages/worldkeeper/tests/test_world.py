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
