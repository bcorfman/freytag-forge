from __future__ import annotations

from random import Random

import pytest

from storygame.engine.freeform import (
    RuleBasedFreeformProposalAdapter,
    resolve_freeform_roleplay,
    resolve_freeform_roleplay_with_proposals,
)
from tests.fast_fixtures import InMemorySaveStore
from tests.fast_fixtures import make_cached_story_state as build_default_state


def _disclosure_cases() -> list[tuple[str, str, str, str, str, str, str]]:
    cases = []
    for genre in ("mystery", "fantasy"):
        state = build_default_state(seed=1, genre=genre)
        for _predicate, item_id, npc_id, key in state.world_facts.query("document_disclosure", None, None, None):
            alias = next(fact[2] for fact in state.world_facts.query("item_alias", item_id, None))
            npc_name = state.world.npcs[npc_id].name
            value = next(fact[2] for fact in state.world_facts.query("case_fact", key, None))
            cases.append((genre, item_id, npc_id, key, alias, npc_name, value))
    return cases


@pytest.mark.parametrize(("genre", "item_id", "npc_id", "key", "alias", "npc_name", "value"), _disclosure_cases())
def test_player_visible_disclosure_matrix(
    genre: str, item_id: str, npc_id: str, key: str, alias: str, npc_name: str, value: str
) -> None:
    state = build_default_state(seed=2, genre=genre)
    assert not state.world_facts.holds("knows", "player", key)

    read = resolve_freeform_roleplay(state, f"read the {alias}", RuleBasedFreeformProposalAdapter())
    assert read["state"].world_facts.holds("knows", "player", key)
    assert value in read["dialog_proposal"]["text"]

    state = build_default_state(seed=3, genre=genre)
    proposal = {
        "intent": "ask_about",
        "targets": [npc_id],
        "arguments": {"topic": alias},
        "disclosed_knowledge": key,
        "proposed_effects": [],
    }
    dialog = {"speaker": npc_id, "text": value, "tone": "in_world"}
    disclosed = resolve_freeform_roleplay_with_proposals(
        state, f"{npc_name}, what does the {alias} say?", dialog, proposal
    )
    assert disclosed["state"].world_facts.holds("knows", "player", key)
    assert disclosed["event"].metadata["fact_ops"]

    repeated = resolve_freeform_roleplay_with_proposals(
        disclosed["state"], f"ask {npc_name} about {alias}", dialog, proposal
    )
    assert repeated["state_update_envelope"]["reasons"] == ("POLICY_INVALID_DISCLOSURE",)

    store = InMemorySaveStore()
    store.save_run("disclosure", disclosed["state"], Random(1))
    loaded, _rng = store.load_run("disclosure")
    assert loaded.world_facts.holds("knows", "player", key)
