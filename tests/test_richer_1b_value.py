from __future__ import annotations

from storygame.runtime.cloudflare import CloudflareTurnProvider
from storygame.runtime.facts import Fact
from storygame.runtime.item_facts import ItemFactsProvider
from tests.test_richer_1b import PACKAGE, _engine, _entries

OBSERVATION_IDS = (
    "k_sl_1b_a_r2",
    "k_sl_1b_f_r1",
    "k_sl_1b_g_r1",
    "k_sl_1b_h_r1",
)
BRANDON_SPEECH_IDS = (
    "k_sl_1b_b_r1",
    "k_sl_1b_b_r2",
    "k_sl_1b_c_r1",
    "k_sl_1b_c_r2",
)


def _commit(state, entry_ids: tuple[str, ...]) -> None:
    entries = _entries()
    for entry_id in entry_ids:
        for operation in entries[entry_id].establishes:
            state.facts.assert_fact(Fact(predicate=operation.fact_id, subject="story", value="true"))


def test_observation_reveals_are_not_voiceable():
    entries = _entries()

    assert all(entries[entry_id].voiceable is False for entry_id in OBSERVATION_IDS)
    assert all(entries[entry_id].voiceable is True for entry_id in BRANDON_SPEECH_IDS)


def test_brandon_is_not_offered_the_observations_as_speech():
    state, engine = _engine()
    _commit(state, OBSERVATION_IDS + ("k_sl_1b_b_r2",))

    projection = engine.projector.project(state, "brandon", "Search the park.")
    sayable_ids = {entry.id for entry in projection.sayable_knowledge}
    assert not set(OBSERVATION_IDS) & sayable_ids

    provider = CloudflareTurnProvider(worker_url="", token="", state=state)
    prompt = provider.assemble_turn_prompt("Search the park.")["context"]
    constraints = provider._section_user_prompt(prompt)
    for entry_id in OBSERVATION_IDS:
        statement = _entries()[entry_id].statement
        assert f"Brandon Corfman may say this aloud: {statement}" not in constraints

    statement = _entries()["k_sl_1b_b_r2"].statement
    assert f"Brandon Corfman may say this aloud: {statement}" in constraints


def test_scene_images_live_in_the_delivery_text_not_the_statement():
    entries = _entries()
    left_behind = entries["k_sl_1b_f_r1"]
    loop = entries["k_sl_1b_g_r1"]
    water = entries["k_sl_1b_h_r1"]

    assert all(word not in left_behind.statement.casefold() for word in ("kickstand", "leash", "tipped"))
    assert all(word in left_behind.delivery_text.casefold() for word in ("kickstand", "leash", "tipped"))
    assert len(left_behind.statement) <= 110
    assert "half-beat" not in loop.statement.casefold() and len(loop.statement) <= 110
    assert "cap" not in water.statement.casefold() and len(water.statement) <= 110


def test_the_picnic_does_not_explain_itself_before_the_thermos():
    entries = _entries()
    left_behind = entries["k_sl_1b_f_r1"].delivery_text.casefold()
    water = entries["k_sl_1b_h_r1"].delivery_text.casefold()

    assert "taken" not in left_behind and "was not" not in left_behind
    assert "drank" in water and "taken" in water
    assert "emergency-water label" in water and "lot number" in water
    assert "what brandon said" not in water


def test_the_held_photograph_shows_a_man_not_michelle():
    state, _engine_instance = _engine()
    photograph = next(item for item in PACKAGE.world.items if item.id == "michelle_photograph")
    assert photograph.name == "photograph of a man"
    assert photograph.hidden

    provider = ItemFactsProvider(
        worker_url="https://worker.example/turn",
        token="",
        state=state,
        item_facts={},
        mode="single_call",
        seed_from_package=True,
    )
    world = provider._world()
    for name in ("photograph", "photo", "Michelle's photograph", "Michelle's photo"):
        assert provider._resolve_name(world, name) == "michelle_photograph"

    entry = _entries()["k_sl_1b_a_r2"]
    assert "brandon" not in entry.statement.casefold()
    assert "brandon" not in entry.delivery_text.casefold()
