from __future__ import annotations

from storygame.engine import freeform as freeform_module
from storygame.engine.freeform import (
    LlmFreeformProposalAdapter,
    RuleBasedFreeformProposalAdapter,
    _dialog_line,
    _envelope_for_action,
    _envelope_to_fact_ops,
    _topic_flag_fragment,
    resolve_freeform_roleplay,
    resolve_freeform_roleplay_with_proposals,
)
from storygame.engine.world import build_default_state


def test_dialog_line_variants_cover_intents_and_missing_target() -> None:
    assert "no one here" in _dialog_line("ask_about", "", "rumors").lower()
    assert "nods once" in _dialog_line("greet", "mina", "")
    assert "all right" in _dialog_line("apologize", "mina", "").lower()
    assert "threats won't help" in _dialog_line("threaten", "mina", "").lower()
    ask_line = _dialog_line("ask_about", "mina", "ledger").lower()
    assert "about ledger" in ask_line
    assert "follow the signal" not in ask_line
    assert "their voice" not in ask_line
    assert "specific question" in _dialog_line("ask_about", "mina", "").lower()


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
    disallowed = _envelope_for_action(
        state,
        {"intent": "dance", "targets": [npc_id], "arguments": {}},
    )
    assert "POLICY_GENERIC_FREEFORM" in disallowed["reasons"]
    assert any(op["fact"][2].startswith("freeform_intent_") for op in disallowed["assert"])

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
    assert success["event"].message_key.startswith(f"{state.world.npcs[npc_id].name} says: \"")
    assert success["event"].message_key.endswith("\"")

    blocked = resolve_freeform_roleplay(state, "ask missing_npc about signal", adapter)
    assert "no one here answers" in blocked["dialog_proposal"]["text"].lower()
    assert blocked["event"].metadata["fact_ops"] == []


def test_resolve_freeform_roleplay_applies_generic_policy_for_arbitrary_intents() -> None:
    state = build_default_state(seed=404)
    adapter = RuleBasedFreeformProposalAdapter()

    inspect = resolve_freeform_roleplay(state, "examine the case file", adapter)
    assert inspect["state"].player.flags.get("freeform_intent_read_case_file") is True
    assert inspect["state"].player.flags.get("reviewed_case_file") is True
    assert inspect["state"].progress > state.progress
    assert inspect["event"].delta_progress > 0.0

    knock = resolve_freeform_roleplay(state, "Daria, knock on the door", adapter)
    assert knock["state"].player.flags.get("freeform_intent_knock") is True
    assert knock["event"].delta_progress > 0.0


def test_resolve_freeform_roleplay_read_case_file_sets_specific_progress_flag() -> None:
    state = build_default_state(seed=407)
    adapter = RuleBasedFreeformProposalAdapter()

    resolved = resolve_freeform_roleplay(state, "read the case file", adapter)

    assert resolved["state"].player.flags.get("reviewed_case_file") is True
    assert "freeform:read_case_file" in resolved["state_update_envelope"]["reasons"]
    assert resolved["event"].delta_progress > 0.0


def test_resolve_freeform_roleplay_with_proposals_uses_provided_payloads() -> None:
    state = build_default_state(seed=409)
    npc_id = state.world.rooms[state.player.location].npc_ids[0]

    resolved = resolve_freeform_roleplay_with_proposals(
        state,
        f"ask {npc_id} about signal",
        {"speaker": npc_id, "text": "Sure, ask directly.", "tone": "in_world"},
        {"intent": "ask_about", "targets": [npc_id], "arguments": {"topic": "signal"}, "proposed_effects": []},
    )

    assert resolved["state"].player.flags.get(f"asked_signal_{npc_id}") is True
    assert resolved["event"].message_key.startswith(f"{state.world.npcs[npc_id].name} says:")


def test_llm_freeform_adapter_uses_planner_payload_when_valid(monkeypatch) -> None:
    state = build_default_state(seed=405)

    def _fake_chat(mode: str, system: str, user: str) -> str:  # noqa: ARG001
        return (
            '{"dialog_proposal":{"speaker":"daria_stone","text":"Daria nods and signals the butler.","tone":"in_world"},'
            '"action_proposal":{"intent":"question","targets":["daria_stone"],"arguments":{"topic":"ledger"},'
            '"proposed_effects":["new_lead"]}}'
        )

    monkeypatch.setattr("storygame.engine.freeform._story_agent_chat_complete", _fake_chat)
    adapter = LlmFreeformProposalAdapter(mode="openai")
    dialog, action = adapter.propose(state, "ask daria about the ledger page")

    assert dialog["speaker"] == "daria_stone"
    assert action["intent"] == "question"
    assert action["arguments"]["planner_source"] == "llm"


def test_llm_freeform_adapter_falls_back_when_planner_errors(monkeypatch) -> None:
    state = build_default_state(seed=406)

    def _boom(mode: str, system: str, user: str) -> str:  # noqa: ARG001
        raise RuntimeError("planner unavailable")

    monkeypatch.setattr("storygame.engine.freeform._story_agent_chat_complete", _boom)
    adapter = LlmFreeformProposalAdapter(mode="openai")
    dialog, action = adapter.propose(state, "hello")

    assert dialog["text"]
    assert action["arguments"]["planner_source"] == "fallback"
    assert "planner unavailable" in action["arguments"]["planner_error"]
