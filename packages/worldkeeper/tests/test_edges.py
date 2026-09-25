import re

import pytest
from test_world import make

from worldkeeper import MemoryBackend, World, WorldSchema


def test_schema_and_query_edges():
    with pytest.raises(ValueError):
        WorldSchema.from_data({"kinds": [{"id": "x", "is": ["missing"]}]})
    with pytest.raises(ValueError):
        WorldSchema.from_data({"entities": [{"id": "a", "name": "a", "kind": "thing", "parent": "a"}]})
    with pytest.raises(ValueError):
        WorldSchema.from_data({"entities": [{"id": "a", "name": "a", "kind": "thing", "owner": "nobody"}]})
    with pytest.raises(ValueError):
        WorldSchema.from_data(
            {"entities": [{"id": "a", "name": "a", "kind": "thing", "axes": [{"poles": ["x", "x"]}]}]}
        )
    w = make()
    assert w.kind("missing") == "" and w.name("missing") == "" and w.owner("missing") is None
    assert w.parent("missing") is None and w.relation("missing") is None
    assert w.chain("missing") == () and w.area("missing") is None and w.holder("missing") is None
    assert not w.together("missing", "ada")
    assert w.contents("village") == ("parlour",)
    assert not w.is_visible("missing")
    assert w.given_with("lamp") == () and w.given_with("chest") == ()
    assert w.place_label("missing") is None


def test_move_and_place_refusals_and_part_of():
    w = make()
    for result in (
        w.move("missing", "village"),
        w.move("lamp", "missing"),
        w.move("village", "parlour"),
        w.move("chest", "village"),
        w.move("key", "village"),
        w.move("lamp", "ada", under=True),
        w.move("ada", "lamp"),
        w.move("chest", "chest_quills"),
        w.place("missing", "village"),
        w.place("village", "parlour"),
        w.place("lamp", "ada", part_of=True),
        w.place("chest", "chest_quills"),
    ):
        assert not result.ok and result.reason
    assert w.place("lamp", "chest", part_of=True, text="inside the wood").ok
    assert w.relation("lamp") == "part_of"
    before = set(w.backend.matching_all())
    assert not w.move("lamp", "chest_quills").ok
    assert set(w.backend.matching_all()) == before


def test_create_rejections_and_owner_and_custom_backend():
    w = make()
    assert not w.create("").ok
    assert not w.create("x" * 81).ok
    assert not w.create("lamp").ok
    assert not w.create("new", kind="character").ok
    assert not w.create("new", owner="lamp").ok
    assert not w.create("new", parent="lamp").ok
    assert not w.create("new", parent="ada", under=True).ok
    result = w.create("new box", parent="ada", owner="ada")
    assert result.ok and w.owner(result.id) == "ada" and w.relation(result.id) == "carried_by"

    class HostFact:
        def __init__(self, *, predicate, subject, object=None, value=None):
            assert re.fullmatch(r"[a-z][a-z0-9_]{0,63}", predicate)
            assert len(subject) <= 120 and (object is None or len(object) <= 120)
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

    class SortedBackend(MemoryBackend):
        def matching(self, predicate, subject=None):
            return tuple(
                sorted(
                    super().matching(predicate, subject),
                    key=lambda f: (f.predicate, f.subject, f.object or "", f.value or ""),
                )
            )

    backend = SortedBackend()
    host = World(w.schema, backend, make_fact=HostFact)
    assert host.seed().ok and host.move("lamp", "chest").ok
    rebuilt = World(w.schema, backend, make_fact=HostFact)
    assert rebuilt.exists("lamp") and rebuilt.parent("lamp") == "chest"


def test_state_edges_axes_status_companions_and_effect_failures():
    w = make()
    assert w.set_axis("ada", "captive").ok and w.axis_values("ada")["captive"] == "captive"
    assert w.set_axis("chest", "open").ok
    assert w.set_conditions("ada", [" tired ", "alert"]).ok
    assert not w.set_conditions("missing", []).ok
    assert not w.set_status("missing", "missing").ok
    assert w.set_status("ada", "missing").ok and w.parent("ada") is None
    assert not w.set_companion("ada", "missing").ok
    assert not w.clear_companion("lamp").ok
    assert w.apply_effects([{}, {"accompany": "ada", "with": "ada"}, {"set_axis": "lamp"}][0:]).__len__() == 3
    assert not w.apply_effects([{"move": "ada", "parent": "missing"}])[0].ok


def test_closed_visibility_and_resolution_callback():
    w = make()
    assert w.set_axis("chest", "closed").ok
    assert not w.is_visible("chest_quills")
    assert w.given_with("chest") == ()
    assert w.set_axis("chest", "open").ok and w.given_with("chest") == ("chest_quills",)
    assert w.resolve("the brass key") == "key"
    assert w.resolve("parlour floor") == "parlour"
    assert w.resolve("Ada's hand") == "ada"
    calls = []
    callback_world = World(w.schema, w.backend, resolver=lambda name, ids: calls.append((name, ids)) or "key")
    assert callback_world.resolve("unknown") == "key"
    assert calls and calls[0][0] == "unknown"
