from pathlib import Path

from storygame.runtime.facts import Fact
from storygame.runtime.item_facts import ItemFactsProvider
from storygame.runtime.state import RuntimeState
from storygame.runtime.world_model import apply_scene_placements, apply_world_effects
from storygame.story_package.loader import load_story_package

ROOT = Path(__file__).resolve().parents[1]
PACKAGE = load_story_package(ROOT / "data" / "stories" / "continuity-initiative")


def _office_reveal_provider():
    state = RuntimeState.bootstrap(PACKAGE)
    state.current_scene_id = "3B"
    apply_scene_placements(PACKAGE, state.facts, "3B")
    provider = ItemFactsProvider(
        worker_url="https://worker.example/turn",
        token="",
        state=state,
        item_facts={},
        mode="single_call",
        seed_from_package=True,
    )
    provider.state.facts.assert_fact(Fact(predicate="human_security_control", subject="story", value="true"))
    provider.prepare_turn("Lead Michelle into the executive office.")
    provider.state.facts.assert_fact(Fact(predicate="rebecca_office_reached", subject="story", value="true"))
    apply_world_effects(PACKAGE, provider.state.facts)
    return provider


def test_null_place_keeps_condition_when_fact_override_runs():
    provider = _office_reveal_provider()

    _facts, issues = provider.apply_item_facts({"Brandon": {"place": None, "condition": ["lit"]}})

    world = provider._world()
    assert world.conditions(world.resolve("Brandon")) == ("lit",)
    assert not any("overridden" in issue for issue in issues)


def test_apply_move_ignores_null_place():
    provider = _office_reveal_provider()
    world = provider._world()
    entity_id = world.resolve("Kristin's laptop")
    place_parent = world.resolve("kitchen")
    before = world.parent(entity_id)

    provider._apply_move(world, entity_id, "Kristin's laptop", {"place": None}, place_parent, [])

    assert world.parent(entity_id) == before
