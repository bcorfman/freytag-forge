from __future__ import annotations

from storygame.engine import freeform as freeform_module
from storygame.engine.freeform import (
    RuleBasedFreeformProposalAdapter,
    _dialog_line,
    _envelope_for_action,
    _envelope_to_fact_ops,
    _topic_flag_fragment,
    resolve_freeform_roleplay,
)
from storygame.engine.world import build_default_state


def test_dialog_line_variants_cover_intents_and_missing_target() -> None:
    assert "no one here" in _dialog_line("ask_about", "", "rumors").lower()
    assert "nods once" in _dialog_line("greet", "mina", "")
    assert "fine" in _dialog_line("apologize", "mina", "").lower()
    assert "threats travel" in _dialog_line("threaten", "mina", "").lower()
    assert "about ledger" in _dialog_line("ask_about", "mina", "ledger").lower()
    assert "clearer question" in _dialog_line("ask_about", "mina", "").lower()


def test_topic_flag_fragment_normalizes_and_filters_stopwords() -> None:
    assert _topic_flag_fragment("about the signal") == "signal"
    assert _topic_flag_fragment("   ") == "rumors"
    assert _topic_flag_fragment("the of to") == "rumors"


def test_rule_based_adapter_propose_intent_paths() -> None:
    state = build_default_state(seed=401)
    adapter = RuleBasedFreeformProposalAdapter()
    npc_id = state.world.rooms[state.player.location].npc_ids[0]

    dialog, action = adapter.propose(state, f"ask {npc_id} about ledger")
    assert action["intent"] == "ask_about"
    assert action["targets"] == [npc_id]
    assert action["arguments"]["topic"] == "ledger"
    assert dialog["speaker"] == npc_id

    _dialog, action = adapter.propose(state, "hello")
    assert action["intent"] == "greet"
    assert "topic" not in action["arguments"]

    _dialog, action = adapter.propose(state, "sorry about earlier")
    assert action["intent"] == "apologize"

    _dialog, action = adapter.propose(state, "I warn you")
    assert action["intent"] == "threaten"


def test_envelope_for_action_policy_rejections_and_allowed_paths(monkeypatch) -> None:
    state = build_default_state(seed=402)
    npc_id = state.world.rooms[state.player.location].npc_ids[0]

    assert _envelope_for_action(state, {"intent": "ask_about", "targets": [], "arguments": {}})["reasons"] == [
        "POLICY_NO_TARGET"
    ]
    assert _envelope_for_action(
        state,
        {"intent": "ask_about", "targets": ["missing_npc"], "arguments": {}},
    )["reasons"] == ["POLICY_TARGET_NOT_PRESENT"]
    assert _envelope_for_action(
        state,
        {"intent": "dance", "targets": [npc_id], "arguments": {}},
    )["reasons"] == ["POLICY_INTENT_NOT_ALLOWED"]

    blocked = _envelope_for_action(
        state,
        {"intent": "ask_about", "targets": [npc_id], "arguments": {"topic": "forbidden topic"}},
    )
    assert "POLICY_TOPIC_BLOCKED" in blocked["reasons"]

    allowed = _envelope_for_action(
        state,
        {"intent": "ask_about", "targets": [npc_id], "arguments": {"topic": "signal"}},
    )
    assert any("asked_signal" in op["fact"][2] for op in allowed["assert"])
    assert allowed["numeric_delta"][0]["delta"] > 0.0

    monkeypatch.setattr(freeform_module, "_PER_TURN_DELTA_BOUND", 0.01)
    clamped_greet = _envelope_for_action(state, {"intent": "greet", "targets": [npc_id], "arguments": {}})
    assert clamped_greet["numeric_delta"][0]["delta"] == 0.01
    clamped_threat = _envelope_for_action(state, {"intent": "threaten", "targets": [npc_id], "arguments": {}})
    assert clamped_threat["numeric_delta"][0]["delta"] == -0.01


def test_envelope_to_fact_ops_converts_all_mutation_types() -> None:
    envelope = {
        "assert": [{"fact": ["flag", "player", "x"]}],
        "retract": [{"fact": ["flag", "player", "y"]}],
        "numeric_delta": [{"key": "trust:a:player", "delta": 0.1}],
        "reasons": ["ok"],
    }
    ops = _envelope_to_fact_ops(envelope)
    assert {"op": "assert", "fact": ("flag", "player", "x")} in ops
    assert {"op": "retract", "fact": ("flag", "player", "y")} in ops
    assert {"op": "numeric_delta", "key": "trust:a:player", "delta": 0.1} in ops


def test_resolve_freeform_roleplay_applies_fact_ops_or_boundary_message() -> None:
    state = build_default_state(seed=403)
    npc_id = state.world.rooms[state.player.location].npc_ids[0]
    adapter = RuleBasedFreeformProposalAdapter()

    success = resolve_freeform_roleplay(state, f"ask {npc_id} about signal", adapter)
    assert success["state"].player.flags.get(f"asked_signal_{npc_id}") is True
    assert success["event"].type == "freeform_roleplay"
    assert success["event"].metadata["fact_ops"]

    blocked = resolve_freeform_roleplay(state, "ask missing_npc about signal", adapter)
    assert "no one here answers" in blocked["dialog_proposal"]["text"].lower()
    assert blocked["event"].metadata["fact_ops"] == []
