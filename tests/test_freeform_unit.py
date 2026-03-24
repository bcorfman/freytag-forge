from __future__ import annotations

from storygame.engine import freeform as freeform_module
from storygame.engine.facts import initialize_world_facts
from storygame.engine.freeform import (
    LlmFreeformProposalAdapter,
    RuleBasedFreeformProposalAdapter,
    _freeform_planner_prompt,
    _envelope_for_action,
    _envelope_to_fact_ops,
    _topic_flag_fragment,
    resolve_freeform_roleplay,
    resolve_freeform_roleplay_with_proposals,
)
from storygame.engine.state import Npc
from storygame.engine.world import build_default_state


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
    assert dialog["speaker"] == "narrator"
    assert dialog["tone"] == "in_world"
    assert dialog["text"]

    _dialog, action = adapter.propose(state, "hello")
    assert action["intent"] == "greet"
    assert "topic" not in action["arguments"]

    _dialog, action = adapter.propose(state, "sorry about earlier")
    assert action["intent"] == "apologize"

    _dialog, action = adapter.propose(state, "I warn you")
    assert action["intent"] == "threaten"


def test_rule_based_adapter_matches_direct_address_by_visible_npc_name() -> None:
    state = build_default_state(seed=410)
    room = state.world.rooms[state.player.location]
    room.npc_ids = ("daria_stone",)
    state.world.npcs["daria_stone"] = Npc(
        id="daria_stone",
        name="Daria Stone",
        description="Daria watches the room closely.",
        dialogue="Ask directly.",
        identity="assistant",
        pronouns="she/her",
    )
    initialize_world_facts(state)

    dialog, action = RuleBasedFreeformProposalAdapter().propose(state, "Daria, what do you make of this place?")

    assert action["targets"] == ["daria_stone"]
    assert dialog["speaker"] == "narrator"
    assert dialog["text"]


def test_rule_based_adapter_gives_scene_specific_place_reply() -> None:
    state = build_default_state(seed=412, genre="mystery", tone="dark")

    dialog, action = RuleBasedFreeformProposalAdapter().propose(state, "Daria, what do you make of this place?")

    assert action["targets"] == ["daria_stone"]
    assert action["arguments"]["topic"] == "place"
    assert dialog["speaker"] == "narrator"
    assert dialog["text"]


def test_rule_based_adapter_does_not_fallback_for_missing_direct_address() -> None:
    state = build_default_state(seed=411, genre="thriller")

    dialog, action = RuleBasedFreeformProposalAdapter().propose(state, "Daria, what do you make of this place?")

    assert action["targets"] == []
    assert dialog["speaker"] == "narrator"
    assert dialog["text"]


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

    broad_topic = _envelope_for_action(
        state,
        {"intent": "ask_about", "targets": [npc_id], "arguments": {"topic": "forbidden topic"}},
    )
    assert any("asked_forbidden" in op["fact"][2] for op in broad_topic["assert"])
    assert broad_topic["numeric_delta"][0]["delta"] > 0.0

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
    assert "ask" in success["event"].message_key.lower()
    assert success["dialog_proposal"]["speaker"] == "narrator"
    assert success["dialog_proposal"]["text"]

    blocked = resolve_freeform_roleplay(state, "ask missing_npc about signal", adapter)
    assert blocked["dialog_proposal"]["speaker"] == "narrator"
    assert blocked["dialog_proposal"]["text"]
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


def test_resolve_freeform_roleplay_strips_unsolicited_npc_targeting_from_world_action() -> None:
    state = build_default_state(seed=416, genre="mystery")

    resolved = resolve_freeform_roleplay_with_proposals(
        state,
        "get in car",
        {"speaker": "daria_stone", "text": "What brings you to the mansion at this hour?", "tone": "in_world"},
        {
            "intent": "ask_about",
            "targets": ["daria_stone"],
            "arguments": {"topic": "arrival", "planner_source": "llm"},
            "proposed_effects": [],
        },
    )

    assert resolved["action_proposal"]["targets"] == ()
    assert resolved["action_proposal"]["intent"] == "freeform"
    assert resolved["dialog_proposal"]["speaker"] == "narrator"
    assert "daria stone says" not in resolved["event"].message_key.lower()


def test_resolve_freeform_roleplay_read_case_file_sets_specific_progress_flag() -> None:
    state = build_default_state(seed=407)
    adapter = RuleBasedFreeformProposalAdapter()

    resolved = resolve_freeform_roleplay(state, "read the case file", adapter)

    assert resolved["state"].player.flags.get("reviewed_case_file") is True
    assert "freeform:read_case_file" in resolved["state_update_envelope"]["reasons"]
    assert resolved["event"].delta_progress > 0.0


def test_resolve_freeform_roleplay_read_case_file_allows_nearby_assistant_holder() -> None:
    state = build_default_state(seed=414, genre="mystery")
    assert "case_file" not in state.player.inventory
    assert state.world_facts.holds("holding", "daria_stone", "case_file")
    adapter = RuleBasedFreeformProposalAdapter()

    resolved = resolve_freeform_roleplay(state, "review the case file", adapter)

    assert resolved["state"].player.flags.get("reviewed_case_file") is True
    assert "freeform:read_case_file" in resolved["state_update_envelope"]["reasons"]
    assert any(
        tuple(mutation["fact"]) == ("reviewed_with_holder", "daria_stone", "case_file")
        for mutation in resolved["state_update_envelope"]["assert"]
    )


def test_resolve_freeform_roleplay_read_ledger_page_sets_specific_progress_flag() -> None:
    state = build_default_state(seed=408)
    room = state.world.rooms[state.player.location]
    if "ledger_page" not in room.item_ids:
        room.item_ids = room.item_ids + ("ledger_page",)

    adapter = RuleBasedFreeformProposalAdapter()
    resolved = resolve_freeform_roleplay(state, "read the ledger page", adapter)

    assert resolved["state"].player.flags.get("reviewed_ledger_page") is True
    assert "freeform:read_ledger_page" in resolved["state_update_envelope"]["reasons"]
    assert resolved["dialog_proposal"]["speaker"] == "narrator"
    assert resolved["dialog_proposal"]["text"]
    assert resolved["event"].delta_progress > 0.0


def test_freeform_objective_reply_prefers_fact_backed_goal() -> None:
    state = build_default_state(seed=409)
    state.active_goal = "stale in-memory goal"
    state.world_facts.assert_fact("active_goal", "Press the strongest lead from the case file.")

    dialog, action = RuleBasedFreeformProposalAdapter().propose(state, "Daria, what is our objective?")

    assert action["intent"] == "ask_about"
    assert action["arguments"]["topic"] == "objective"
    assert "Press the strongest lead from the case file." in dialog["text"]
    assert dialog["speaker"] == "narrator"


def test_rule_based_adapter_handles_appearance_questions_with_contextual_reply() -> None:
    state = build_default_state(seed=413, genre="mystery", tone="dark")

    dialog, action = RuleBasedFreeformProposalAdapter().propose(state, "Daria, what are you wearing?")

    assert action["intent"] == "ask_about"
    assert action["arguments"]["topic"] == "appearance"
    assert action["targets"] == ["daria_stone"]
    assert dialog["speaker"] == "narrator"
    assert dialog["text"]


def test_rule_based_adapter_handles_ledger_questions_with_contextual_reply() -> None:
    state = build_default_state(seed=414, genre="mystery", tone="dark")

    dialog, action = RuleBasedFreeformProposalAdapter().propose(state, "Daria, what about the ledger page?")

    assert action["intent"] == "ask_about"
    assert action["arguments"]["topic"] == "ledger page"
    assert action["targets"] == ["daria_stone"]
    assert dialog["speaker"] == "narrator"
    assert dialog["text"]


def test_rule_based_adapter_handles_service_passage_follow_up_with_specific_reply() -> None:
    state = build_default_state(seed=415, genre="mystery", tone="dark")
    state.player.inventory = state.player.inventory + ("route_key",)
    initialize_world_facts(state)

    dialog, action = RuleBasedFreeformProposalAdapter().propose(
        state,
        "Daria, where is the service passage located?",
    )

    assert action["intent"] == "ask_about"
    assert action["targets"] == ["daria_stone"]
    assert "service passage" in action["arguments"]["topic"]
    assert dialog["speaker"] == "narrator"
    assert dialog["text"]


def test_rule_based_adapter_does_not_autotarget_nearby_npc_for_unrelated_action() -> None:
    state = build_default_state(seed=416, genre="mystery", tone="dark")

    dialog, action = RuleBasedFreeformProposalAdapter().propose(state, "eat some food")

    assert action["targets"] == []
    assert dialog["speaker"] == "narrator"
    assert dialog["text"]


def test_rule_based_adapter_handles_player_appearance_question_without_using_npc_clothing() -> None:
    state = build_default_state(seed=417, genre="mystery", tone="dark")

    dialog, action = RuleBasedFreeformProposalAdapter().propose(state, "Daria, what am I wearing?")

    assert action["intent"] == "ask_about"
    assert action["targets"] == ["daria_stone"]
    assert "player appearance" in action["arguments"]["topic"]
    assert dialog["speaker"] == "narrator"
    assert dialog["text"]


def test_rule_based_adapter_handles_clothing_request_as_character_reaction() -> None:
    state = build_default_state(seed=418, genre="mystery", tone="dark")

    dialog, action = RuleBasedFreeformProposalAdapter().propose(state, "Daria, take off your coat")

    assert action["intent"] == "ask_about"
    assert action["targets"] == ["daria_stone"]
    assert "remove coat request" in action["arguments"]["topic"]
    assert dialog["speaker"] == "narrator"
    assert dialog["text"]


def test_rule_based_adapter_fallback_dialogue_stays_generic_for_npc_questions() -> None:
    state = build_default_state(seed=419, genre="mystery", tone="dark")

    dialog, action = RuleBasedFreeformProposalAdapter().propose(state, "Daria, take off your coat and boots")

    assert action["intent"] == "ask_about"
    assert action["targets"] == ["daria_stone"]
    assert dialog["speaker"] == "narrator"
    lower = dialog["text"].lower()
    assert "ask" in lower or "press" in lower
    assert "coat stays on" not in lower
    assert "most rumors fall apart" not in lower


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
    assert resolved["dialog_proposal"]["speaker"] == npc_id
    assert resolved["dialog_proposal"]["text"] == "Sure, ask directly."


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
    assert dialog["text"]
    assert action["intent"] == "ask_about"
    assert action["arguments"]["planner_source"] == "llm"


def test_llm_freeform_adapter_tolerates_list_shaped_arguments(monkeypatch) -> None:
    state = build_default_state(seed=4051)

    def _fake_chat(mode: str, system: str, user: str) -> str:  # noqa: ARG001
        return (
            '{"dialog_proposal":{"speaker":"daria_stone","text":"I dress for weather, not ceremony.","tone":"in_world"},'
            '"action_proposal":{"intent":"ask_about","targets":["daria_stone"],"arguments":[],"proposed_effects":["asked:appearance"]}}'
        )

    monkeypatch.setattr("storygame.engine.freeform._story_agent_chat_complete", _fake_chat)
    adapter = LlmFreeformProposalAdapter(mode="openai")
    dialog, action = adapter.propose(state, "Daria, what are you wearing?")

    assert dialog["speaker"] == "daria_stone"
    assert action["intent"] == "ask_about"
    assert tuple(action["targets"]) == ("daria_stone",)
    assert action["arguments"]["planner_source"] == "llm"


def test_freeform_planner_prompt_includes_scene_and_item_facts() -> None:
    state = build_default_state(seed=4052, genre="mystery")

    _system, user = _freeform_planner_prompt(state, "Daria, what are you wearing?")

    assert '"scene_facts"' in user
    assert "drove your own sedan" in user
    assert '"appearance": "a crisp white blouse and a tailored black skirt with dark hair pulled back into a neat bun"' in user
    assert '"name": "dark sedan"' in user
    assert '"state": "parked_by_drive"' in user
    assert '"visible_item_names": ["dark sedan"]' in user
    assert '"visible_item_ids"' not in user


def test_llm_freeform_adapter_fails_closed_when_planner_errors(monkeypatch) -> None:
    state = build_default_state(seed=406)

    def _boom(mode: str, system: str, user: str) -> str:  # noqa: ARG001
        raise RuntimeError("planner unavailable")

    monkeypatch.setattr("storygame.engine.freeform._story_agent_chat_complete", _boom)
    adapter = LlmFreeformProposalAdapter(mode="openai")
    try:
        adapter.propose(state, "hello")
    except RuntimeError as exc:
        assert "FREEFORM_PLANNER_UNAVAILABLE" in str(exc)
        assert "planner unavailable" in str(exc)
    else:
        raise AssertionError("Expected planner failure to fail closed.")
