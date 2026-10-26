from __future__ import annotations

from pathlib import Path

from storygame.runtime.character_names import short_name
from storygame.runtime.cloudflare import CloudflareTurnProvider
from storygame.runtime.item_facts import ItemFactsProvider
from storygame.runtime.seating import board_vehicle
from storygame.runtime.state import RuntimeState
from storygame.runtime.world_model import world_for
from storygame.story_package.loader import load_story_package
from storygame.story_package.models import Npc
from tests.test_place_scoped_feed import _synthetic_package

ROOT = Path(__file__).parents[1]
PACKAGE = load_story_package(ROOT / "data/stories/continuity-initiative")


def _synthetic_named_package():
    package = _synthetic_package()
    protagonist = package.world.npcs[0].model_copy(
        update={"name": "Alexandra Longname", "aliases": ("Alexandra", "Al")}
    )
    return package.model_copy(update={"world": package.world.model_copy(update={"npcs": (protagonist,)})})


def _item_facts_provider(package, state):
    return ItemFactsProvider(
        worker_url="",
        token="",
        state=state,
        item_facts={},
        mode="single_call",
        seed_from_package=True,
        held_by=True,
    )


def test_short_name_prefers_first_alias_over_shorter_later_alias_and_name() -> None:
    npc = Npc(id="hero", name="Longname", aliases=("Preferred", "Nick"))

    assert short_name(npc) == "Preferred"


def test_short_name_uses_name_without_aliases() -> None:
    npc = Npc(id="hero", name="Longname", aliases=())

    assert short_name(npc) == "Longname"


def test_synthetic_story_uses_first_alias_for_item_facts_narration_and_seating() -> None:
    package = _synthetic_named_package()
    state = RuntimeState.bootstrap(package)
    world = world_for(package, state.facts)
    provider = _item_facts_provider(package, state)

    assert provider._entity_label(provider._world(), "hero") == "Alexandra"

    narrator = CloudflareTurnProvider(worker_url="", token="", state=state)
    assert "The player is Alexandra." in narrator._system_prompt()

    assert world.move("hero", "driver_seat").ok
    result = board_vehicle(world, package, "Get in a blue car.", lambda *_: True, lambda *_: True)

    assert result.command == "Alexandra is already in the driver seat."
    assert result.steps == ("Alexandra is already in the driver seat.",)


def test_unnamed_label_precedes_first_alias_before_named_fact_is_true() -> None:
    package = _synthetic_package()
    npc = Npc(
        id="hero",
        name="Alexandra Longname",
        aliases=("Alexandra", "Al"),
        unnamed_label="the surveyor",
        named_by="hero_named",
    )
    package = package.model_copy(update={"world": package.world.model_copy(update={"npcs": (npc,)})})
    state = RuntimeState.bootstrap(package)
    provider = _item_facts_provider(package, state)

    assert provider._entity_label(provider._world(), "hero") == "the surveyor"


def test_shipped_story_uses_first_alias_for_non_protagonist_character() -> None:
    state = RuntimeState.bootstrap(PACKAGE)
    provider = _item_facts_provider(PACKAGE, state)
    npc = next(npc for npc in PACKAGE.world.npcs if npc.id != PACKAGE.protagonist_id and len(npc.aliases) > 1)

    assert provider._entity_label(provider._world(), npc.id) == npc.aliases[0]
