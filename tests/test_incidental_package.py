"""Authoring and adapter contract for incidental props and cosmetic facets (richer-narration step 2)."""

from __future__ import annotations

import shutil
from pathlib import Path

import pytest
from worldkeeper import IncidentalPolicy, PropProposal, PropTemplate, TraitProposal

from storygame.runtime.state import RuntimeState
from storygame.runtime.world_model import incidental_policy_for, world_for
from storygame.story_package.loader import StoryPackageError, load_story_package

ROOT = Path(__file__).parents[1]
LIGHTHOUSE = ROOT / "tests/fixtures/stories/lighthouse-keeper"
CONTINUITY = ROOT / "data/stories/continuity-initiative"

PROPS = """
props:
- id: tea_cup
  name: tea cup
  parents: [keeper_bench, parlour]
  facets: {color: [white, blue], finish: [matte, glossy]}
- id: harbor_sign
  name: harbor sign
  parents: [shore]
  fixed: true
- id: lamp_rag
  name: lamp rag
  parents: [lamp_room]
"""
LOGBOOK = "- id: logbook\n  name: Tom's logbook\n  owner: tom\n"
LOGBOOK_WITH_FACETS = LOGBOOK + "  facets: {color: [brown, black]}\n  authored_facets: {finish: worn}\n"


def lighthouse(
    tmp_path,
    *,
    props=PROPS,
    world_edits=(),
    plot_edits=((("objective: Find the brass key\n"), "objective: Find the brass key\nprop_pool: [tea_cup]\n"),),
):
    root = tmp_path / "lighthouse"
    shutil.copytree(LIGHTHOUSE, root)
    world = (root / "world.yaml").read_text()
    assert LOGBOOK in world
    world = world.replace(LOGBOOK, LOGBOOK_WITH_FACETS) + props
    for old, new in world_edits:
        assert old in world, old
        world = world.replace(old, new)
    (root / "world.yaml").write_text(world)
    plot = (root / "plot.md").read_text()
    for old, new in plot_edits:
        assert old in plot, old
        plot = plot.replace(old, new, 1)
    (root / "plot.md").write_text(plot)
    return root


def test_authored_props_and_palettes_load_into_the_package(tmp_path):
    package = load_story_package(lighthouse(tmp_path))
    props = {prop.id: prop for prop in package.world.props}
    assert set(props) == {"tea_cup", "harbor_sign", "lamp_rag"}
    assert props["tea_cup"].name == "tea cup" and tuple(props["tea_cup"].parents) == ("keeper_bench", "parlour")
    assert props["harbor_sign"].fixed is True and props["tea_cup"].fixed is False
    scene = next(scene for scene in package.scenes if scene.metadata.scene_id == "1A")
    assert tuple(scene.metadata.prop_pool) == ("tea_cup",)
    logbook = next(item for item in package.world.items if item.id == "logbook")
    assert {facet: tuple(values) for facet, values in logbook.facets.items()} == {"color": ("brown", "black")}
    assert dict(logbook.authored_facets) == {"finish": "worn"}


def test_the_adapter_builds_a_policy_from_the_package(tmp_path):
    policy = incidental_policy_for(load_story_package(lighthouse(tmp_path)))
    assert isinstance(policy, IncidentalPolicy)
    assert policy.templates["1A"] == (
        PropTemplate(
            "tea cup", ("keeper_bench", "parlour"), False, {"color": ("white", "blue"), "finish": ("matte", "glossy")}
        ),
    )
    assert not policy.templates.get("1B")
    assert {facet: tuple(values) for facet, values in policy.palettes["logbook"].items()} == {
        "color": ("brown", "black")
    }
    assert dict(policy.authored["logbook"]) == {"finish": "worn"}
    assert (policy.per_turn, policy.per_scene, policy.per_game, policy.max_facets) == (1, 3, 12, 3)


@pytest.mark.parametrize("root", [LIGHTHOUSE, CONTINUITY], ids=["lighthouse-keeper", "continuity-initiative"])
def test_a_package_without_any_prop_policy_gets_none(root):
    assert incidental_policy_for(load_story_package(root)) is None


def test_the_policy_drives_the_real_world_end_to_end(tmp_path):
    package = load_story_package(lighthouse(tmp_path))
    policy = incidental_policy_for(package)
    state = RuntimeState.bootstrap(package)
    world = world_for(package, state.facts)
    result = world.apply_embellishments(
        policy, "1A", (PropProposal("tea cup", "bench"),), (TraitProposal("tea cup", "color", "blue"),)
    )
    assert result.ok
    cup = result.created[0]
    assert world.parent(cup) == "keeper_bench" and world.facets(cup) == {"color": "blue"}
    refused = world.apply_embellishments(policy, "1A", (), (TraitProposal("Tom's logbook", "finish", "glossy"),))
    assert not refused.ok
    allowed = world.apply_embellishments(policy, "1A", (), (TraitProposal("Tom's logbook", "color", "brown"),))
    assert allowed.ok and world.facets("logbook") == {"color": "brown"}
    assert not world.apply_embellishments(policy, "1A", (PropProposal("lamp rag", "bench"),), ()).ok


@pytest.mark.parametrize(
    ("kwargs", "message"),
    [
        ({"props": PROPS + "- id: tea_cup\n  name: another cup\n  parents: [shore]\n"}, "duplicate prop"),
        ({"props": PROPS.replace("[shore]", "[nowhere]")}, "unknown parent"),
        ({"props": PROPS.replace("name: lamp rag", "name: sea chest")}, "prop name"),
        ({"props": PROPS.replace("name: lamp rag", "name: Ada")}, "prop name"),
        (
            {
                "plot_edits": (
                    (("objective: Find the brass key\n"), "objective: Find the brass key\nprop_pool: [ghost_prop]\n"),
                )
            },
            "unknown prop",
        ),
        (
            {
                "plot_edits": (
                    (("objective: Find the brass key\n"), "objective: Find the brass key\nprop_pool: [lamp_rag]\n"),
                )
            },
            "not available in scene",
        ),
        ({"props": PROPS.replace("{color: [white, blue], finish: [matte, glossy]}", "{color: []}")}, "facet"),
        ({"props": PROPS.replace("[white, blue]", "[white, white]")}, "facet"),
        (
            {
                "props": PROPS.replace(
                    "{color: [white, blue], finish: [matte, glossy]}", "{a: [x], b: [y], c: [z], d: [w]}"
                )
            },
            "too many facets",
        ),
        (
            {
                "world_edits": (
                    ("authored_facets: {finish: worn}", "authored_facets: {finish: worn, pattern: plain, wear: old}"),
                )
            },
            "too many facets",
        ),
    ],
)
def test_the_loader_rejects_bad_prop_declarations(tmp_path, kwargs, message):
    with pytest.raises(StoryPackageError, match=message):
        load_story_package(lighthouse(tmp_path, **kwargs))
