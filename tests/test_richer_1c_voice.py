from __future__ import annotations

from storygame.runtime.cloudflare import CloudflareTurnProvider
from storygame.runtime.facts import Fact
from tests.test_richer_1c import _engine, _entries
from tests.test_speaker_lines import speaker_may_say

OBSERVATION_IDS = (
    "k_sl_1c_a_r1",
    "k_sl_1c_b_r1",
    "k_sl_1c_b_r2",
    "k_sl_1c_c_copy_numbers",
)
NEW_REVEAL_IDS = (
    "k_sl_1c_e_r1",
    "k_sl_1c_f_r1",
    "k_sl_1c_g_r1",
)


def _commit(state, entry_ids: tuple[str, ...]) -> None:
    entries = _entries()
    for entry_id in entry_ids:
        entry = entries[entry_id]
        for requirement in entry.requires:
            state.facts.assert_fact(
                Fact(
                    predicate=requirement.fact_id,
                    subject="story",
                    value=str(requirement.equals).lower(),
                )
            )
        for operation in entry.establishes:
            state.facts.assert_fact(
                Fact(predicate=operation.fact_id, subject="story", value=str(operation.value).lower())
            )
        if entry.voiceable:
            state.facts.assert_fact(Fact(predicate="knowledge_narrated", subject=entry_id, value="true"))


def test_scene_1c_observations_are_not_voiceable_and_brandons_own_beats_are():
    entries = _entries()

    assert all(entries[entry_id].voiceable is False for entry_id in OBSERVATION_IDS)
    assert entries["k_sl_1c_c_secure_route"].voiceable is True
    assert entries["k_sl_1c_d_r1"].voiceable is True
    assert all(entries[entry_id].voiceable is False for entry_id in NEW_REVEAL_IDS)


def test_brandon_is_not_offered_the_1c_observations_as_speech():
    state, engine = _engine()
    _commit(state, OBSERVATION_IDS + ("k_sl_1c_c_secure_route",))

    projection = engine.projector.project(state, "brandon", "Search the processing line.")
    sayable_ids = {entry.id for entry in projection.sayable_knowledge}
    assert not set(OBSERVATION_IDS) & sayable_ids
    assert "k_sl_1c_c_secure_route" in sayable_ids


def test_the_narrator_prompt_does_not_script_brandon_with_1c_observations():
    state, _engine_instance = _engine()
    _commit(state, OBSERVATION_IDS + ("k_sl_1c_c_secure_route",))

    provider = CloudflareTurnProvider(worker_url="", token="", state=state)
    prompt = provider.assemble_turn_prompt("Search the processing line.")["context"]
    constraints = provider._section_user_prompt(prompt)
    entries = _entries()
    for entry_id in OBSERVATION_IDS:
        statement = entries[entry_id].statement
        assert not speaker_may_say(constraints, "Brandon Corfman", statement)

    statement = entries["k_sl_1c_c_secure_route"].statement
    assert speaker_may_say(constraints, "Brandon Corfman", statement)
