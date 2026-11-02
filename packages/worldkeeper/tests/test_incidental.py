"""Constrained incidental props and cosmetic facets (the richer-narration world model)."""

import pytest

from worldkeeper import (
    IncidentalPolicy,
    MemoryBackend,
    PropProposal,
    PropTemplate,
    TraitProposal,
    World,
    WorldSchema,
)

PALETTE = {
    "color": ("red", "blue"),
    "finish": ("matte", "glossy"),
    "pattern": ("striped", "plain"),
    "wear": ("old", "new"),
}
KITCHEN_PARENTS = ("table", "shelf", "kitchen", "cupboard", "safe", "hidden_box", "chair")


def kitchen_pool():
    return (
        PropTemplate("tin whistle", KITCHEN_PARENTS, facets=PALETTE),
        PropTemplate("saucer", KITCHEN_PARENTS, facets={"color": ("white", "green")}),
        PropTemplate("spoon", KITCHEN_PARENTS),
        PropTemplate("napkin", KITCHEN_PARENTS),
        PropTemplate("fixed sign", ("kitchen",), fixed=True),
        PropTemplate("cup", ("table",)),
    )


def make_policy(**overrides):
    values = {
        "templates": {
            "kitchen": kitchen_pool(),
            "cellar": (PropTemplate("lantern", ("cellar",)), PropTemplate("rope coil", ("cellar",))),
        },
        "palettes": {"cup": {"color": ("white", "blue"), "finish": ("matte", "glossy")}},
        "authored": {},
    }
    values.update(overrides)
    return IncidentalPolicy(**values)


def make_world(resolver=None):
    schema = WorldSchema.from_data(
        {
            "entities": [
                {"id": "village", "name": "the village", "kind": "area"},
                {"id": "kitchen", "name": "kitchen", "kind": "area", "parent": "village"},
                {"id": "cellar", "name": "cellar", "kind": "area", "parent": "village"},
                {"id": "ada", "name": "Ada", "kind": "character"},
                {"id": "table", "name": "table", "kind": "supporter", "fixed": True},
                {"id": "shelf", "name": "shelf", "kind": "supporter", "fixed": True},
                {"id": "cupboard", "name": "cupboard", "kind": "container", "fixed": True, "openable": True},
                {"id": "safe", "name": "safe", "kind": "container", "fixed": True, "contents_complete": True},
                {"id": "cup", "name": "cup", "kind": "thing"},
                {"id": "pipe", "name": "pipe", "kind": "thing", "aliases": ["tin whistle"]},
                {"id": "locket", "name": "locket", "kind": "thing", "hidden": True},
                {"id": "hidden_box", "name": "hidden box", "kind": "container", "hidden": True},
                {"id": "chair", "name": "chair", "kind": "furniture"},
            ]
        }
    )
    world = World(schema, MemoryBackend(), resolver=resolver)
    assert world.seed().ok
    for entity_id, parent in (
        ("table", "kitchen"),
        ("shelf", "kitchen"),
        ("cupboard", "kitchen"),
        ("safe", "kitchen"),
        ("hidden_box", "kitchen"),
        ("chair", "kitchen"),
        ("locket", "kitchen"),
        ("cup", "table"),
        ("pipe", "shelf"),
    ):
        assert world.place(entity_id, parent).ok
    assert world.move("ada", "kitchen").ok
    assert world.set_axis("cupboard", "closed").ok
    return world


def snapshot(world):
    return frozenset(world.backend.matching_all())


def one_prop(template, parent):
    return (PropProposal(template, parent),)


def test_creates_a_prop_with_provenance_and_counts_it():
    world, policy = make_world(), make_policy()
    result = world.apply_embellishments(policy, "kitchen", one_prop("tin whistle", "table"), ())
    assert result.ok and len(result.created) == 1
    prop = result.created[0]
    assert world.is_incidental(prop) and not world.is_incidental("cup")
    assert world.origin(prop) == ("kitchen", "tin whistle")
    assert world.kind(prop) == "thing" and world.name(prop) == "tin whistle"
    assert world.parent(prop) == "table" and world.resolve("tin whistle") == prop
    assert world.incidental_counts("kitchen") == (1, 1)
    assert world.incidental_counts("cellar") == (0, 1)


def test_zero_is_valid_and_an_empty_batch_changes_nothing():
    world, policy = make_world(), make_policy()
    before = snapshot(world)
    result = world.apply_embellishments(policy, "kitchen", (), ())
    assert result.ok and result.created == () and result.traits == ()
    assert snapshot(world) == before


def test_one_new_prop_per_turn_and_a_refused_batch_changes_nothing():
    world, policy = make_world(), make_policy()
    before = snapshot(world)
    result = world.apply_embellishments(
        policy, "kitchen", (PropProposal("spoon", "table"), PropProposal("napkin", "table")), ()
    )
    assert not result.ok and "turn" in result.reason
    assert snapshot(world) == before


def test_three_props_per_scene_lifetime_even_after_disposal_and_movement():
    world, policy = make_world(), make_policy()
    ids = []
    for name in ("spoon", "napkin", "saucer"):
        result = world.apply_embellishments(policy, "kitchen", one_prop(name, "table"), ())
        assert result.ok
        ids.append(result.created[0])
    assert world.set_unplaced(ids[0], "gone").ok
    assert world.move(ids[1], "ada").ok
    assert world.incidental_counts("kitchen") == (3, 3)
    before = snapshot(world)
    result = world.apply_embellishments(policy, "kitchen", one_prop("tin whistle", "table"), ())
    assert not result.ok and "scene" in result.reason
    assert snapshot(world) == before


def test_twelve_per_game_default_and_custom_limit():
    assert make_policy().per_turn == 1 and make_policy().per_scene == 3 and make_policy().per_game == 12
    assert make_policy().max_facets == 3
    world = make_world()
    policy = make_policy(per_game=2)
    assert world.apply_embellishments(policy, "kitchen", one_prop("spoon", "table"), ()).ok
    assert world.apply_embellishments(policy, "kitchen", one_prop("napkin", "table"), ()).ok
    result = world.apply_embellishments(policy, "cellar", one_prop("lantern", "cellar"), ())
    assert not result.ok and "game" in result.reason
    assert world.incidental_counts("cellar") == (0, 2)


def test_a_template_may_be_used_once_per_scene_even_after_disposal():
    world, policy = make_world(), make_policy()
    first = world.apply_embellishments(policy, "kitchen", one_prop("spoon", "table"), ())
    assert first.ok and world.set_unplaced(first.created[0], "gone").ok
    second = world.apply_embellishments(policy, "kitchen", one_prop("spoon", "table"), ())
    assert not second.ok and "already used" in second.reason


def test_only_the_scenes_pool_is_eligible():
    world, policy = make_world(), make_policy()
    before = snapshot(world)
    assert not world.apply_embellishments(policy, "kitchen", one_prop("lantern", "kitchen"), ()).ok
    assert not world.apply_embellishments(policy, "attic", one_prop("spoon", "table"), ()).ok
    assert not world.apply_embellishments(policy, "kitchen", one_prop("anvil", "table"), ()).ok
    assert snapshot(world) == before


@pytest.mark.parametrize("parent", ["pipe", "locket", "hidden_box", "cupboard", "safe", "nowhere", "spoon"])
def test_illegal_or_unavailable_parents_are_refused(parent):
    """A thing cannot hold things; hidden, shut-away and complete-contents parents take no new props."""
    world = make_world()
    policy = make_policy(templates={"kitchen": (PropTemplate("spoon", KITCHEN_PARENTS + ("pipe", "locket")),)})
    before = snapshot(world)
    result = world.apply_embellishments(policy, "kitchen", one_prop("spoon", parent), ())
    assert not result.ok
    assert snapshot(world) == before


def test_a_character_or_area_may_be_a_parent_when_the_template_allows_it():
    world = make_world()
    policy = make_policy(
        templates={"kitchen": (PropTemplate("spoon", ("ada",)), PropTemplate("napkin", ("kitchen",)))}, per_scene=2
    )
    assert world.apply_embellishments(policy, "kitchen", one_prop("spoon", "ada"), ()).ok
    assert world.apply_embellishments(policy, "kitchen", one_prop("napkin", "kitchen"), ()).ok


def test_a_parent_outside_the_templates_allowed_scope_is_refused():
    world, policy = make_world(), make_policy()
    before = snapshot(world)
    result = world.apply_embellishments(policy, "kitchen", one_prop("fixed sign", "table"), ())
    assert not result.ok and "parent" in result.reason
    assert snapshot(world) == before


def test_a_new_prop_name_cannot_be_used_as_a_parent_in_the_same_batch():
    world = make_world()
    policy = make_policy(per_turn=2)
    before = snapshot(world)
    result = world.apply_embellishments(
        policy, "kitchen", (PropProposal("spoon", "table"), PropProposal("napkin", "spoon")), ()
    )
    assert not result.ok
    assert snapshot(world) == before


def test_a_template_name_that_collides_with_an_entity_or_alias_is_refused_without_cost():
    world = make_world()
    policy = make_policy(
        templates={
            "kitchen": (
                PropTemplate("cup", ("table",)),
                PropTemplate("tin whistle", ("table",)),
                PropTemplate("spoon", ("table",)),
            )
        }
    )
    before = snapshot(world)
    assert not world.apply_embellishments(policy, "kitchen", one_prop("cup", "table"), ()).ok
    assert not world.apply_embellishments(policy, "kitchen", one_prop("tin whistle", "table"), ()).ok
    assert snapshot(world) == before
    assert world.incidental_counts("kitchen") == (0, 0)


def test_props_are_ordinary_things_and_fixed_templates_stay_put():
    world, policy = make_world(), make_policy(per_scene=5)
    movable = world.apply_embellishments(policy, "kitchen", one_prop("spoon", "table"), ()).created[0]
    fixed = world.apply_embellishments(policy, "kitchen", one_prop("fixed sign", "kitchen"), ()).created[0]
    assert world.move(movable, "ada").ok and world.relation(movable) == "carried_by"
    assert not world.move(fixed, "ada").ok and world.parent(fixed) == "kitchen"
    assert world.kind(movable) == world.kind(fixed) == "thing"


def test_trusted_create_is_unchanged_and_not_incidental():
    world = make_world()
    created = world.create("brass bell", parent="table")
    assert created.ok and not world.is_incidental(created.id)
    assert world.incidental_counts("kitchen") == (0, 0)
    assert world.origin(created.id) is None


def test_trait_on_an_existing_object_costs_no_allowance_and_is_stable():
    world, policy = make_world(), make_policy()
    result = world.apply_embellishments(policy, "kitchen", (), (TraitProposal("cup", "color", "blue"),))
    assert result.ok and result.traits == (("cup", "color", "blue"),)
    assert world.facets("cup") == {"color": "blue"}
    assert world.incidental_counts("kitchen") == (0, 0)
    assert world.apply_embellishments(policy, "kitchen", (), (TraitProposal("cup", "color", "blue"),)).ok
    before = snapshot(world)
    changed = world.apply_embellishments(policy, "kitchen", (), (TraitProposal("cup", "color", "white"),))
    assert not changed.ok and "already" in changed.reason
    assert snapshot(world) == before
    assert world.facets("cup") == {"color": "blue"}


@pytest.mark.parametrize(
    ("target", "facet", "value"),
    [("cup", "color", "purple"), ("cup", "pattern", "plain"), ("table", "color", "red"), ("nobody", "color", "red")],
)
def test_traits_must_come_from_the_objects_palette(target, facet, value):
    world, policy = make_world(), make_policy()
    before = snapshot(world)
    result = world.apply_embellishments(policy, "kitchen", (), (TraitProposal(target, facet, value),))
    assert not result.ok
    assert snapshot(world) == before


def test_at_most_three_facets_per_object():
    world = make_world()
    policy = make_policy(palettes={"cup": PALETTE})
    for facet, value in (("color", "red"), ("finish", "matte"), ("pattern", "plain")):
        assert world.apply_embellishments(policy, "kitchen", (), (TraitProposal("cup", facet, value),)).ok
    before = snapshot(world)
    result = world.apply_embellishments(policy, "kitchen", (), (TraitProposal("cup", "wear", "old"),))
    assert not result.ok and "facet" in result.reason
    assert snapshot(world) == before


def test_authored_facet_values_win_and_count_toward_the_limit():
    world = make_world()
    policy = make_policy(palettes={"cup": PALETTE}, authored={"cup": {"color": "white", "finish": "matte"}})
    before = snapshot(world)
    assert not world.apply_embellishments(policy, "kitchen", (), (TraitProposal("cup", "color", "red"),)).ok
    assert snapshot(world) == before
    assert world.apply_embellishments(policy, "kitchen", (), (TraitProposal("cup", "color", "white"),)).ok
    assert world.apply_embellishments(policy, "kitchen", (), (TraitProposal("cup", "pattern", "plain"),)).ok
    assert not world.apply_embellishments(policy, "kitchen", (), (TraitProposal("cup", "wear", "old"),)).ok


def test_a_new_prop_can_take_its_templates_facets_in_the_same_turn():
    world, policy = make_world(), make_policy()
    result = world.apply_embellishments(
        policy,
        "kitchen",
        one_prop("tin whistle", "table"),
        (TraitProposal("tin whistle", "color", "red"), TraitProposal("tin whistle", "finish", "glossy")),
    )
    assert result.ok
    assert world.facets(result.created[0]) == {"color": "red", "finish": "glossy"}
    refused = world.apply_embellishments(policy, "kitchen", (), (TraitProposal("tin whistle", "color", "blue"),))
    assert not refused.ok


def test_a_trait_for_a_prop_that_is_not_in_the_batch_or_world_is_refused():
    world, policy = make_world(), make_policy()
    before = snapshot(world)
    assert not world.apply_embellishments(policy, "kitchen", (), (TraitProposal("spoon", "color", "red"),)).ok
    assert snapshot(world) == before


def test_a_batch_is_all_or_nothing_in_both_directions():
    world, policy = make_world(), make_policy()
    before = snapshot(world)
    bad_trait = world.apply_embellishments(
        policy, "kitchen", one_prop("spoon", "table"), (TraitProposal("cup", "color", "purple"),)
    )
    assert not bad_trait.ok and snapshot(world) == before
    bad_prop = world.apply_embellishments(
        policy, "kitchen", one_prop("spoon", "locket"), (TraitProposal("cup", "color", "blue"),)
    )
    assert not bad_prop.ok and snapshot(world) == before
    assert world.facets("cup") == {} and world.incidental_counts("kitchen") == (0, 0)


def test_check_embellishments_is_read_only_and_agrees_with_apply():
    world, policy = make_world(), make_policy()
    before = snapshot(world)
    good = world.check_embellishments(policy, "kitchen", one_prop("spoon", "table"), ())
    bad = world.check_embellishments(policy, "kitchen", one_prop("spoon", "locket"), ())
    assert good.ok and not bad.ok and bad.reason
    assert snapshot(world) == before
    assert world.apply_embellishments(policy, "kitchen", one_prop("spoon", "table"), ()).ok


def test_counts_facets_and_origin_survive_a_fresh_world_over_the_same_facts():
    world, policy = make_world(), make_policy()
    prop = world.apply_embellishments(
        policy, "kitchen", one_prop("tin whistle", "table"), (TraitProposal("tin whistle", "color", "red"),)
    ).created[0]
    assert world.move(prop, "ada").ok
    reloaded = World(world.schema, world.backend.clone())
    assert reloaded.incidental_counts("kitchen") == (1, 1)
    assert reloaded.origin(prop) == ("kitchen", "tin whistle")
    assert reloaded.facets(prop) == {"color": "red"}
    again = reloaded.apply_embellishments(policy, "kitchen", one_prop("tin whistle", "table"), ())
    assert not again.ok


def test_memory_backend_clone_is_independent():
    backend = MemoryBackend()
    world = World(WorldSchema.from_data({"entities": [{"id": "a", "name": "a", "kind": "area"}]}), backend)
    assert world.seed().ok
    copy = backend.clone()
    assert set(copy.matching_all()) == set(backend.matching_all())
    copy.assert_fact(next(iter(backend.matching_all())).__class__("wk_test", "a"))
    assert len(copy.matching_all()) == len(backend.matching_all()) + 1


def test_embellishment_never_calls_the_resolver():
    def explode(name, candidates):
        raise AssertionError("embellishments must not use the resolver")

    world, policy = make_world(resolver=explode), make_policy()
    assert not world.apply_embellishments(policy, "kitchen", one_prop("spoon", "a place no one named"), ()).ok
    assert not world.apply_embellishments(policy, "kitchen", (), (TraitProposal("thingy", "color", "red"),)).ok
    assert world.apply_embellishments(policy, "kitchen", one_prop("spoon", "table"), ()).ok


def test_zero_allowance_policy_refuses_props_but_not_empty_batches():
    world, policy = make_world(), make_policy(per_turn=0)
    assert world.apply_embellishments(policy, "kitchen", (), ()).ok
    assert not world.apply_embellishments(policy, "kitchen", one_prop("spoon", "table"), ()).ok


def test_policy_declarations_are_validated():
    with pytest.raises(ValueError):
        make_policy(templates={"kitchen": (PropTemplate("spoon", ("table",)), PropTemplate("spoon", ("shelf",)))})
    with pytest.raises(ValueError):
        PropTemplate("", ("table",))
    with pytest.raises(ValueError):
        PropTemplate("spoon", ())
    with pytest.raises(ValueError):
        PropTemplate("spoon", ("table",), facets={"color": ()})
    with pytest.raises(ValueError):
        make_policy(per_turn=-1)
    with pytest.raises(ValueError):
        make_policy(palettes={"cup": {"color": ("red", "red")}})
