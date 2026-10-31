from __future__ import annotations

from pathlib import Path

from storygame.runtime.item_facts import ItemFactsProvider
from storygame.runtime.state import RuntimeState
from storygame.runtime.world_model import apply_scene_placements
from storygame.story_package.loader import load_story_package

ROOT = Path(__file__).parents[1]
PACKAGE = load_story_package(ROOT / "data/stories/continuity-initiative")
OPENING_FACT = "It has no open or closed state and nothing inside."


def _provider(scene_id: str, *, opening_things_fact: bool = False) -> ItemFactsProvider:
    state = RuntimeState.bootstrap(PACKAGE)
    state.current_scene_id = scene_id
    apply_scene_placements(PACKAGE, state.facts, scene_id)
    return ItemFactsProvider(
        worker_url="",
        token="",
        state=state,
        item_facts={},
        mode="single_call",
        seed_from_package=True,
        opening_things_fact=opening_things_fact,
    )


def _narrator_things(provider: ItemFactsProvider, names: list[str]) -> str:
    provider._selected_names = names
    provider._referred_names = names
    prompt = provider.assemble_turn_prompt("Inspect the named things.")
    return provider._section_user_prompt(prompt["context"]).split("THINGS:\n", 1)[1].split("\n\n", 1)[0]


def test_flag_off_keeps_the_drain_narrator_prompt_unchanged() -> None:
    default = _provider("1B")
    explicit_off = _provider("1B", opening_things_fact=False)

    assert _narrator_things(default, ["storm drain"]) == _narrator_things(explicit_off, ["storm drain"])
    assert OPENING_FACT not in _narrator_things(default, ["storm drain"])


def test_flag_on_marks_openings_but_not_drawer_or_plain_thing() -> None:
    park = _provider("1B", opening_things_fact=True)
    park_things = _narrator_things(park, ["storm drain", "service gate", "park bench"])

    assert park_things.count(OPENING_FACT) == 2
    assert "- storm drain. Place: Los Angeles park. " + OPENING_FACT in park_things
    assert "- service gate. Place: Los Angeles park. " + OPENING_FACT in park_things
    assert "- park bench. Place: Los Angeles park. " + OPENING_FACT not in park_things

    house = _provider("1A", opening_things_fact=True)
    house_things = _narrator_things(house, ["back door", "drawer"])

    assert "- back door. Place: kitchen. " + OPENING_FACT in house_things
    assert "- drawer. Place: in Michelle's workstation. " + OPENING_FACT not in house_things


def test_flag_on_does_not_change_matcher_or_item_facts_things() -> None:
    off = _provider("1B")
    on = _provider("1B", opening_things_fact=True)
    names = ["storm drain", "service gate"]
    for provider in (off, on):
        provider._selected_names = names
        provider._referred_names = names

    assert on._things_block() == off._things_block()
    assert on._match_payload("Inspect the storm drain.", []) == off._match_payload("Inspect the storm drain.", [])
