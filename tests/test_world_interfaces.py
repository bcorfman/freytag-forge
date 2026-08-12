from __future__ import annotations

import pytest

from storygame.engine.interfaces import (
    load_npc_voice_cards,
    load_predicate_schema,
    load_rule_pack,
    parse_action_proposal,
    parse_dialog_proposal,
    parse_state_update_envelope,
)


def test_predicate_schema_core_and_genre_load() -> None:
    core = load_predicate_schema("core")
    mystery = load_predicate_schema("mystery")

    assert core["schema_version"] >= 1
    assert any(item["name"] == "at" for item in core["predicates"])
    assert mystery["schema_version"] >= 1
    assert mystery["genre"] == "mystery"


def test_rule_pack_core_and_genre_load() -> None:
    core = load_rule_pack("core")
    mystery = load_rule_pack("mystery")

    assert core["schema_version"] >= 1
    assert core["scope"] == "core"
    assert mystery["scope"] == "genre"
    assert mystery["genre"] == "mystery"


def test_npc_voice_cards_load() -> None:
    payload = load_npc_voice_cards()

    assert payload["schema_version"] >= 1
    assert any(card["npc_id"] == "guide" for card in payload["cards"])


def test_action_dialog_and_state_update_contracts_validate() -> None:
    action = parse_action_proposal(
        {
            "intent": "mock",
            "targets": ["oracle"],
            "arguments": {"intensity": "low"},
            "proposed_effects": ["annoy_target"],
        }
    )
    dialog = parse_dialog_proposal(
        {
            "speaker": "guide",
            "text": "That approach won't help. Focus on verifiable facts.",
            "tone": "stern",
        }
    )
    envelope = parse_state_update_envelope(
        {
            "assert": [{"fact": ["flag", "player", "warned_oracle"]}],
            "retract": [{"fact": ["flag", "player", "trusted_oracle"]}],
            "numeric_delta": [{"key": "trust:oracle:player", "delta": -0.1}],
            "reasons": ["mock_npc"],
        }
    )

    assert action["intent"] == "mock"
    assert dialog["speaker"] == "guide"
    assert envelope["numeric_delta"][0]["delta"] == -0.1


def test_state_update_contract_rejects_invalid_fact_shape() -> None:
    with pytest.raises(ValueError, match="Invalid state update envelope"):
        parse_state_update_envelope(
            {
                "assert": [{"fact": ["flag"]}],
                "retract": [],
                "numeric_delta": [],
                "reasons": ["bad_fact"],
            }
        )
