from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace

from storygame.runtime.facts import Fact
from storygame.runtime.item_facts import ItemFactsProvider
from storygame.runtime.knowledge import KnowledgeProjector
from storygame.runtime.state import RuntimeState
from storygame.runtime.world_model import world_for
from storygame.story_package.loader import load_story_package
from tests.test_boarding import _synthetic_vehicle_world

PACKAGE = load_story_package(Path("data/stories/continuity-initiative"))


def _provider() -> ItemFactsProvider:
    return ItemFactsProvider(
        worker_url="",
        token="",
        state=RuntimeState.bootstrap(PACKAGE),
        item_facts={},
        mode="off",
        seed_from_package=True,
    )


def test_protagonist_landing_at_vehicle_stays_at_its_area_when_not_aboard():
    provider = _provider()

    _facts, issues = provider.apply_item_facts(
        {"Kristin": {"place": "Kristin's truck"}}, player_input="Go out to Kristin's truck."
    )

    assert issues
    assert provider._world().parent("kristin") == "outside_house"


def test_protagonist_landing_at_outside_area_stays_in_the_area():
    provider = _provider()

    _facts, issues = provider.apply_item_facts({"Kristin": {"place": "outside the house"}}, player_input="Go outside.")

    assert not issues
    assert provider._world().parent("kristin") == "outside_house"


def test_non_protagonist_landing_at_vehicle_is_not_seated():
    provider = _provider()

    _facts, issues = provider.apply_item_facts(
        {"Kristin's laptop": {"place": "Kristin's truck"}}, player_input="Put my laptop in the truck."
    )

    assert not issues
    assert provider._world().parent("kristin_laptop") == "kristin_truck"


def test_synthetic_vehicle_landing_stays_at_its_area_without_story_names():
    package, world = _synthetic_vehicle_world()
    provider = SimpleNamespace(
        state=SimpleNamespace(package=SimpleNamespace(world=SimpleNamespace(protagonist_id=package.protagonist_id)))
    )

    ItemFactsProvider._apply_move(provider, world, "player", "Player", {"place": "boat 0"}, "boat_0", [])

    assert world.parent("player") == "harbor"


def test_reachable_kitchen_reveal_is_not_offered_outside():
    state = RuntimeState.bootstrap(PACKAGE)
    state.active_event_ids.add("SL-1A-A")
    state.facts.assert_fact(Fact(predicate="memory_card_recovered", subject="story", value="true"))
    world = world_for(PACKAGE, state.facts)
    assert world.move("kristin", "outside_house").ok

    candidates = KnowledgeProjector().project(state, "player", "Search the kitchen.").candidates
    assert "k_sl_1a_a_r1" not in {candidate.id for candidate in candidates}

    assert world.move("kristin", "kitchen").ok
    candidates = KnowledgeProjector().project(state, "player", "Search the kitchen.").candidates
    assert "k_sl_1a_a_r1" in {candidate.id for candidate in candidates}
