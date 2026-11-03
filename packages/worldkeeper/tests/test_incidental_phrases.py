"""Short condition phrases that match an approved facet value become facets."""

from test_incidental import PALETTE, make_policy, make_world, one_prop

from worldkeeper import MemoryBackend, World


def route(world, policy, entity_id, phrases, scene="kitchen"):
    return world.route_condition_phrases(policy, scene, entity_id, phrases)


def test_matching_phrases_become_facets_and_the_rest_are_left_over():
    world, policy = make_world(), make_policy()
    routed = route(world, policy, "cup", ["Blue", "  glossy ", "cracked"])
    assert routed.facets == (("color", "blue"), ("finish", "glossy"))
    assert routed.leftover == ("cracked",) and routed.refused == ()
    assert world.facets("cup") == {"color": "blue", "finish": "glossy"}


def test_the_same_value_again_is_a_no_op_and_a_different_one_is_refused():
    world, policy = make_world(), make_policy()
    route(world, policy, "cup", ["blue"])
    again = route(world, policy, "cup", ["blue"])
    assert again.facets == (("color", "blue"),) and again.refused == () and again.leftover == ()
    other = route(world, policy, "cup", ["white"])
    assert other.facets == () and other.leftover == ()
    assert len(other.refused) == 1 and other.refused[0][0] == "white" and "already" in other.refused[0][1]
    assert world.facets("cup") == {"color": "blue"}


def test_the_facet_limit_refuses_a_matching_phrase():
    world, policy = make_world(), make_policy(palettes={"cup": PALETTE})
    routed = route(world, policy, "cup", ["red", "matte", "plain", "old"])
    assert [facet for facet, _value in routed.facets] == ["color", "finish", "pattern"]
    assert len(routed.refused) == 1 and routed.refused[0][0] == "old" and "facet" in routed.refused[0][1]


def test_an_authored_value_wins_over_a_matching_phrase():
    world, policy = make_world(), make_policy(authored={"cup": {"color": "white"}})
    routed = route(world, policy, "cup", ["blue"])
    assert routed.facets == () and routed.leftover == ()
    assert len(routed.refused) == 1 and "authored" in routed.refused[0][1]
    assert world.facets("cup") == {}


def test_an_object_without_a_palette_leaves_every_phrase_over_and_stores_nothing():
    world, policy = make_world(), make_policy()
    before = snapshot(world)
    routed = route(world, policy, "chair", ["blue", "old"])
    assert routed.facets == () and routed.refused == () and routed.leftover == ("blue", "old")
    assert route(world, policy, "no_such_entity", ["blue"]).leftover == ("blue",)
    assert snapshot(world) == before


def test_an_incidental_prop_uses_its_templates_palette():
    world, policy = make_world(), make_policy()
    prop = world.apply_embellishments(policy, "kitchen", one_prop("tin whistle", "table"), ()).created[0]
    routed = route(world, policy, prop, ["red", "chipped"])
    assert routed.facets == (("color", "red"),) and routed.leftover == ("chipped",)
    assert world.facets(prop) == {"color": "red"}
    assert world.is_incidental(prop)


def test_a_phrase_that_fits_two_facets_is_left_over_not_guessed():
    world = make_world()
    policy = make_policy(palettes={"cup": {"wear": ("old", "new"), "age": ("old", "young")}})
    routed = route(world, policy, "cup", ["old", "new"])
    assert routed.facets == (("wear", "new"),) and routed.leftover == ("old",)


def test_routing_costs_no_allowance_and_never_calls_the_resolver():
    def explode(name, candidates):
        raise AssertionError("routing must not use the resolver")

    world, policy = make_world(resolver=explode), make_policy()
    route(world, policy, "cup", ["blue", "nonsense"])
    assert world.incidental_counts("kitchen") == (0, 0)
    assert isinstance(world, World) and isinstance(world.backend, MemoryBackend)


def snapshot(world):
    return frozenset(world.backend.matching_all())
