from __future__ import annotations

from storygame.engine import freeform as freeform_module
from storygame.engine.facts import initialize_world_facts
from storygame.engine.freeform import (
    LlmFreeformProposalAdapter,
    RuleBasedFreeformProposalAdapter,
    _dialog_line,
    _format_character_reply_line,
    _freeform_planner_prompt,
    _has_invalid_targeted_dialogue_speaker,
    _normalized_dialog_speaker_id,
    _normalized_movement_action_payload,
    _room_environment,
    _scope_normalized_proposals,
    _scene_scoped_dialog_override,
    _semantic_actions_for_freeform,
    _semantic_exit_direction,
    _envelope_for_action,
    _envelope_to_fact_ops,
    _topic_flag_fragment,
    resolve_freeform_roleplay,
    resolve_freeform_roleplay_with_proposals,
)
from storygame.engine.state import Npc, Room
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


def test_dialog_line_covers_targetless_and_topic_specific_branches() -> None:
    state = build_default_state(seed=4101, genre="mystery")
    npc_id = "daria_stone"

    assert _dialog_line("inspect", "", "", state) == "You focus on the details and search for a usable clue."
    assert _dialog_line("knock", "", "", state) == "Your knock echoes through the entryway."
    assert "greet Daria Stone" in _dialog_line("greet", npc_id, "", state)
    assert "apologize to Daria Stone" in _dialog_line("apologize", npc_id, "", state)
    assert "pressure on Daria Stone" in _dialog_line("threaten", npc_id, "", state)
    assert "size up your appearance" in _dialog_line("ask_about", npc_id, "player appearance", state)
    assert "remove part of their outfit" in _dialog_line("ask_about", npc_id, "remove coat request", state)
    assert "service passage" in _dialog_line("ask_about", npc_id, "service passage", state)
    assert "route key" in _dialog_line("ask_about", npc_id, "route key", state)
    assert "objective" in _dialog_line("ask_about", npc_id, "objective", state).lower()
    assert "appearance" in _dialog_line("ask_about", npc_id, "appearance", state)
    assert "going around" in _dialog_line("ask_about", npc_id, "rumors", state)


def test_dialog_line_covers_item_place_and_default_specific_question_branches() -> None:
    state = build_default_state(seed=4102, genre="mystery")
    state.world.rooms[state.player.location].item_ids = state.world.rooms[state.player.location].item_ids + ("ledger_page",)
    npc_id = "daria_stone"

    item_line = _dialog_line("ask_about", npc_id, "ledger page", state)
    place_line = _dialog_line("ask_about", npc_id, "place", state)
    default_line = _dialog_line("ask_about", npc_id, "", state)

    assert "ledger page" in item_line
    assert "front steps" in place_line.lower() or "weather has not erased" in place_line.lower()
    assert "needs a more specific question" in default_line.lower()


def test_dialog_line_covers_item_without_clue_and_generic_place_variants() -> None:
    state = build_default_state(seed=4103, genre="mystery")
    state.player.location = "foyer"
    state.world.rooms["foyer"].item_ids = ()
    npc_id = "daria_stone"

    item_line = _dialog_line("ask_about", npc_id, "field kit", state)
    place_line = _dialog_line("ask_about", npc_id, "place", state)

    assert "field kit" in item_line
    assert "room suggests" in place_line.lower() or "pushes east" in place_line.lower()


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


def test_scene_scoped_dialog_override_handles_car_door_and_generic_player_echoes() -> None:
    state = build_default_state(seed=413, genre="mystery", tone="dark")

    sedan_dialog = _scene_scoped_dialog_override(
        state,
        "open car door",
        {"intent": "freeform", "targets": [], "arguments": {}, "proposed_effects": []},
    )
    assert sedan_dialog["speaker"] == "narrator"
    assert "sedan's door" in sedan_dialog["text"].lower()

    generic_dialog = _scene_scoped_dialog_override(
        state,
        "use lantern",
        {"intent": "freeform", "targets": [], "arguments": {}, "proposed_effects": []},
    )
    assert generic_dialog["speaker"] == "narrator"
    assert generic_dialog["text"] == "You focus on the immediate action."


def test_format_character_reply_line_preserves_contractions_and_wrapped_quotes() -> None:
    state = build_default_state(seed=414, genre="mystery", tone="dark")

    contraction_line = _format_character_reply_line(
        state,
        {"speaker": "daria_stone", "text": "I'm here to bring you inside.", "tone": "in_world"},
        {"intent": "ask_about", "targets": ["daria_stone"], "arguments": {}, "proposed_effects": []},
    )
    quoted_line = _format_character_reply_line(
        state,
        {"speaker": "daria_stone", "text": '"Keep your voice down."', "tone": "in_world"},
        {"intent": "ask_about", "targets": ["daria_stone"], "arguments": {}, "proposed_effects": []},
    )

    assert contraction_line == 'Daria Stone says: "I\'m here to bring you inside."'
    assert quoted_line == 'Daria Stone says: "Keep your voice down."'


def test_format_character_reply_line_maps_ai_assistant_to_target_npc() -> None:
    state = build_default_state(seed=4141, genre="mystery", tone="dark")

    line = _format_character_reply_line(
        state,
        {"speaker": "AI_Assistant", "text": "Stay sharp.", "tone": "in_world"},
        {"intent": "ask_about", "targets": ["daria_stone"], "arguments": {}, "proposed_effects": []},
    )

    assert line == 'Daria Stone says: "Stay sharp."'


def test_invalid_targeted_dialogue_speaker_flags_player_and_allows_named_npc() -> None:
    assert _has_invalid_targeted_dialogue_speaker(
        {"speaker": "player", "text": "I answer myself.", "tone": "in_world"},
        {"intent": "ask_about", "targets": ["daria_stone"], "arguments": {}, "proposed_effects": []},
    )
    assert not _has_invalid_targeted_dialogue_speaker(
        {"speaker": "daria_stone", "text": "Ask quickly.", "tone": "in_world"},
        {"intent": "ask_about", "targets": ["daria_stone"], "arguments": {}, "proposed_effects": []},
    )


def test_invalid_targeted_dialogue_speaker_ignores_empty_targets() -> None:
    assert not _has_invalid_targeted_dialogue_speaker(
        {"speaker": "narrator", "text": "No target.", "tone": "in_world"},
        {"intent": "freeform", "targets": [], "arguments": {}, "proposed_effects": []},
    )


def test_normalized_dialog_speaker_id_maps_aliases_and_visible_names() -> None:
    state = build_default_state(seed=4144, genre="mystery")

    assert _normalized_dialog_speaker_id(state, "AI_Assistant", {"targets": ["daria_stone"]}) == "daria_stone"
    assert _normalized_dialog_speaker_id(state, "Daria Stone", {"targets": []}) == "daria_stone"
    assert _normalized_dialog_speaker_id(state, "player", {"targets": []}) == "player"


def test_scope_normalized_proposals_strips_unsolicited_npc_target_and_player_echo() -> None:
    state = build_default_state(seed=4145, genre="mystery")

    dialog, action = _scope_normalized_proposals(
        state,
        "get in car",
        {"speaker": "player", "text": "open car door", "tone": "in_world"},
        {
            "intent": "ask_about",
            "targets": ["daria_stone"],
            "arguments": {"topic": "arrival"},
            "proposed_effects": [],
        },
    )

    assert dialog["speaker"] == "narrator"
    assert action["intent"] == "freeform"
    assert action["targets"] == ()


def test_scope_normalized_proposals_leaves_direct_address_and_non_npc_targets_unchanged() -> None:
    state = build_default_state(seed=4148, genre="mystery")

    direct_dialog, direct_action = _scope_normalized_proposals(
        state,
        "Daria, what happened?",
        {"speaker": "daria_stone", "text": "Not here.", "tone": "in_world"},
        {"intent": "ask_about", "targets": ["daria_stone"], "arguments": {}, "proposed_effects": []},
    )
    item_dialog, item_action = _scope_normalized_proposals(
        state,
        "inspect car",
        {"speaker": "narrator", "text": "You inspect the sedan.", "tone": "in_world"},
        {"intent": "inspect", "targets": ["arrival_sedan"], "arguments": {}, "proposed_effects": []},
    )

    assert direct_dialog["speaker"] == "daria_stone"
    assert tuple(direct_action["targets"]) == ("daria_stone",)
    assert item_dialog["speaker"] == "narrator"
    assert tuple(item_action["targets"]) == ("arrival_sedan",)


def test_semantic_actions_for_freeform_emits_move_and_take_actions() -> None:
    state = build_default_state(seed=4142, genre="mystery")
    state.world.rooms[state.player.location].item_ids = state.world.rooms[state.player.location].item_ids + ("route_key",)

    move_actions = _semantic_actions_for_freeform(
        state,
        {"intent": "move", "targets": ["north"], "arguments": {}, "proposed_effects": []},
        {"assert": [], "retract": [], "numeric_delta": [], "reasons": []},
    )
    take_actions = _semantic_actions_for_freeform(
        state,
        {"intent": "take", "targets": ["route_key"], "arguments": {}, "proposed_effects": []},
        {"assert": [], "retract": [], "numeric_delta": [], "reasons": []},
    )
    none_actions = _semantic_actions_for_freeform(
        state,
        {"intent": "ask_about", "targets": ["daria_stone"], "arguments": {}, "proposed_effects": []},
        {"assert": [], "retract": [], "numeric_delta": [], "reasons": []},
    )

    assert move_actions[0]["action_type"] == "move_to"
    assert move_actions[0]["location_id"] == "foyer"
    assert take_actions[0]["action_type"] == "take_item"
    assert take_actions[0]["item_id"] == "route_key"
    assert none_actions == ()


def test_semantic_actions_for_freeform_returns_empty_for_missing_targets_and_unmapped_move() -> None:
    state = build_default_state(seed=4146, genre="mystery")

    missing_move = _semantic_actions_for_freeform(
        state,
        {"intent": "move", "targets": ["up"], "arguments": {}, "proposed_effects": []},
        {"assert": [], "retract": [], "numeric_delta": [], "reasons": []},
    )
    missing_take = _semantic_actions_for_freeform(
        state,
        {"intent": "take", "targets": ["field_kit"], "arguments": {}, "proposed_effects": []},
        {"assert": [], "retract": [], "numeric_delta": [], "reasons": []},
    )

    assert missing_move == ()
    assert missing_take == ()


def test_format_character_reply_line_returns_plain_text_for_narrator_and_player() -> None:
    state = build_default_state(seed=4143, genre="mystery", tone="dark")

    narrator_line = _format_character_reply_line(
        state,
        {"speaker": "narrator", "text": "You focus on the immediate action.", "tone": "in_world"},
    )
    player_line = _format_character_reply_line(
        state,
        {"speaker": "player", "text": "open car door", "tone": "in_world"},
        {"intent": "freeform", "targets": [], "arguments": {}, "proposed_effects": []},
    )

    assert narrator_line == "You focus on the immediate action."
    assert player_line == "open car door"


def test_format_character_reply_line_handles_single_quoted_and_embedded_says_forms() -> None:
    state = build_default_state(seed=4147, genre="mystery", tone="dark")

    single_quoted = _format_character_reply_line(
        state,
        {"speaker": "daria_stone", "text": "'Keep moving.'", "tone": "in_world"},
        {"intent": "ask_about", "targets": ["daria_stone"], "arguments": {}, "proposed_effects": []},
    )
    embedded = _format_character_reply_line(
        state,
        {"speaker": "daria_stone", "text": "Daria says, 'Keep your voice down.'", "tone": "in_world"},
        {"intent": "ask_about", "targets": ["daria_stone"], "arguments": {}, "proposed_effects": []},
    )

    assert single_quoted == 'Daria Stone says: "Keep moving."'
    assert embedded == 'Daria Stone says: "Keep your voice down."'


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
    assert not resolved["state"].world_facts.holds(
        "player_context",
        "case_file_status",
        "You have not reviewed the case file yet, so its contents are still unknown to you.",
    )
    assert resolved["state"].world_facts.holds(
        "player_context",
        "case_file_status",
        "You have reviewed the case file and know the victim timeline plus the first credible lead.",
    )


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


def test_rule_based_adapter_resolves_semantic_navigation_to_unique_exit() -> None:
    state = build_default_state(seed=420, genre="mystery", tone="dark")

    dialog, action = RuleBasedFreeformProposalAdapter().propose(state, "enter the mansion")

    assert action["intent"] == "move"
    assert action["targets"] == ["north"]
    assert dialog["speaker"] == "narrator"
    assert dialog["text"]


def test_rule_based_adapter_keeps_addressed_navigation_as_conversation() -> None:
    state = build_default_state(seed=4201, genre="mystery", tone="dark")

    dialog, action = RuleBasedFreeformProposalAdapter().propose(state, "Daria, should we head inside?")

    assert action["intent"] == "ask_about"
    assert action["targets"] == ["daria_stone"]
    assert dialog["speaker"] == "narrator"


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


def test_llm_freeform_adapter_normalizes_semantic_move_target_to_exit_direction(monkeypatch) -> None:
    state = build_default_state(seed=4053, genre="mystery")

    def _fake_chat(mode: str, system: str, user: str) -> str:  # noqa: ARG001
        return (
            '{"dialog_proposal":{"speaker":"narrator","text":"You head through the front door.","tone":"in_world"},'
            '"action_proposal":{"intent":"move","targets":["mansion"],"arguments":{},'
            '"proposed_effects":["move:mansion"]}}'
        )

    monkeypatch.setattr("storygame.engine.freeform._story_agent_chat_complete", _fake_chat)
    adapter = LlmFreeformProposalAdapter(mode="openai")
    dialog, action = adapter.propose(state, "enter the mansion")

    assert dialog["speaker"] == "narrator"
    assert action["intent"] == "move"
    assert tuple(action["targets"]) == ("north",)
    assert action["arguments"]["planner_source"] == "llm"


def test_semantic_exit_direction_resolves_outdoor_return_route() -> None:
    state = build_default_state(seed=40531, genre="mystery")
    state.player.location = "foyer"

    assert _semantic_exit_direction(state, "go back outside") == "south"


def test_room_environment_classifies_mystery_start_rooms() -> None:
    state = build_default_state(seed=405311, genre="mystery")

    assert _room_environment(state.world.rooms["front_steps"]) == "outdoor"
    assert _room_environment(state.world.rooms["foyer"]) == "indoor"


def test_semantic_exit_direction_returns_empty_when_no_exit_semantics_match() -> None:
    state = build_default_state(seed=40532, genre="mystery")

    assert _semantic_exit_direction(state, "head somewhere") == ""


def test_semantic_exit_direction_returns_empty_when_room_has_no_exits() -> None:
    state = build_default_state(seed=405321, genre="mystery")
    state.world.rooms["sealed_archive"] = Room(
        id="sealed_archive",
        name="Sealed Archive",
        description="A sealed archive with stone walls and no visible doors.",
        exits={},
    )
    state.player.location = "sealed_archive"

    assert _semantic_exit_direction(state, "enter the archive") == ""


def test_normalized_movement_action_payload_leaves_non_movement_intent_unchanged() -> None:
    state = build_default_state(seed=40533, genre="mystery")
    payload = {
        "intent": "ask_about",
        "targets": ["daria_stone"],
        "arguments": {"topic": "arrival"},
        "proposed_effects": [],
    }

    normalized = _normalized_movement_action_payload(state, "ask daria about the arrival", payload)

    assert normalized == payload


def test_normalized_movement_action_payload_converts_generic_freeform_to_move() -> None:
    state = build_default_state(seed=40534, genre="mystery")
    payload = {
        "intent": "freeform",
        "targets": [],
        "arguments": {},
        "proposed_effects": [],
    }

    normalized = _normalized_movement_action_payload(state, "head in the front door", payload)

    assert normalized["intent"] == "move"
    assert normalized["targets"] == ["north"]
    assert normalized["arguments"]["semantic_navigation"] == "true"


def test_normalized_movement_action_payload_rewrites_invalid_move_target() -> None:
    state = build_default_state(seed=40535, genre="mystery")
    payload = {
        "intent": "move",
        "targets": ["mansion"],
        "arguments": {},
        "proposed_effects": [],
    }

    normalized = _normalized_movement_action_payload(state, "enter the mansion", payload)

    assert normalized["targets"] == ["north"]
    assert normalized["proposed_effects"] == ["move:north"]


def test_semantic_exit_direction_prefers_destination_name_match() -> None:
    state = build_default_state(seed=40536, genre="mystery")

    assert _semantic_exit_direction(state, "head to the foyer") == "north"


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


def test_llm_freeform_adapter_retries_directed_npc_turn_when_first_reply_uses_narrator(monkeypatch) -> None:
    state = build_default_state(seed=40511, genre="mystery")
    responses = iter(
        (
            '{"dialog_proposal":{"speaker":"narrator","text":"You ask Olivia about the victim.","tone":"in_world"},'
            '"action_proposal":{"intent":"ask_about","targets":["olivia_thompson"],"arguments":{"topic":"victim"},'
            '"proposed_effects":["asked:victim"]}}',
            '{"dialog_proposal":{"speaker":"olivia_thompson","text":"He was already dead by the time I reached the hall.","tone":"in_world"},'
            '"action_proposal":{"intent":"ask_about","targets":["olivia_thompson"],"arguments":{"topic":"victim"},'
            '"proposed_effects":["asked:victim"]}}',
        )
    )

    def _fake_chat(mode: str, system: str, user: str) -> str:  # noqa: ARG001
        return next(responses)

    monkeypatch.setattr("storygame.engine.freeform._story_agent_chat_complete", _fake_chat)
    adapter = LlmFreeformProposalAdapter(mode="openai")
    dialog, action = adapter.propose(state, "Olivia, tell me about the victim")

    assert dialog["speaker"] == "olivia_thompson"
    assert "already dead" in dialog["text"]
    assert action["intent"] == "ask_about"


def test_llm_freeform_adapter_retries_directed_npc_turn_when_wrong_npc_answers(monkeypatch) -> None:
    state = build_default_state(seed=40513, genre="mystery")
    state.world.rooms["foyer"].npc_ids = ("olivia_thompson", "daria_stone")
    state.player.location = "foyer"
    responses = iter(
        (
            '{"dialog_proposal":{"speaker":"daria_stone","text":"The victim was found upstairs after midnight.","tone":"in_world"},'
            '"action_proposal":{"intent":"ask_about","targets":["olivia_thompson"],"arguments":{"topic":"victim"},'
            '"proposed_effects":["asked:victim"]}}',
            '{"dialog_proposal":{"speaker":"olivia_thompson","text":"She was dead before the staff started lying to each other.","tone":"in_world"},'
            '"action_proposal":{"intent":"ask_about","targets":["olivia_thompson"],"arguments":{"topic":"victim"},'
            '"proposed_effects":["asked:victim"]}}',
        )
    )

    def _fake_chat(mode: str, system: str, user: str) -> str:  # noqa: ARG001
        return next(responses)

    monkeypatch.setattr("storygame.engine.freeform._story_agent_chat_complete", _fake_chat)
    adapter = LlmFreeformProposalAdapter(mode="openai")
    dialog, action = adapter.propose(state, "Olivia, tell me about the victim")

    assert dialog["speaker"] == "olivia_thompson"
    assert "dead before the staff" in dialog["text"]
    assert action["intent"] == "ask_about"


def test_llm_freeform_adapter_retries_directed_npc_turn_when_reply_leaks_code_artifact(monkeypatch) -> None:
    state = build_default_state(seed=40514, genre="mystery")
    responses = iter(
        (
            '{"dialog_proposal":{"speaker":"daria_stone","text":"getStringExtra from the case file is not available yet, but it is extensive.","tone":"in_world"},'
            '"action_proposal":{"intent":"ask_about","targets":["daria_stone"],"arguments":{"topic":"case file"},'
            '"proposed_effects":["asked:case_file"]}}',
            '{"dialog_proposal":{"speaker":"daria_stone","text":"The file fixes the victim timeline, names the last verified witness, and points us to the strongest lead inside.","tone":"in_world"},'
            '"action_proposal":{"intent":"ask_about","targets":["daria_stone"],"arguments":{"topic":"case file"},'
            '"proposed_effects":["asked:case_file"]}}',
        )
    )

    def _fake_chat(mode: str, system: str, user: str) -> str:  # noqa: ARG001
        return next(responses)

    monkeypatch.setattr("storygame.engine.freeform._story_agent_chat_complete", _fake_chat)
    adapter = LlmFreeformProposalAdapter(mode="openai")
    dialog, action = adapter.propose(state, "Daria, summarize the case file for me")

    assert dialog["speaker"] == "daria_stone"
    assert "getStringExtra" not in dialog["text"]
    assert "victim timeline" in dialog["text"]
    assert action["intent"] == "ask_about"


def test_llm_freeform_adapter_retries_when_first_reply_is_non_json_for_movement(monkeypatch) -> None:
    state = build_default_state(seed=40512, genre="mystery")
    responses = iter(
        (
            "You head toward the mansion entrance.",
            '{"dialog_proposal":{"speaker":"narrator","text":"You head through the front door.","tone":"in_world"},'
            '"action_proposal":{"intent":"move","targets":["mansion"],"arguments":{},'
            '"proposed_effects":["move:mansion"]}}',
        )
    )

    def _fake_chat(mode: str, system: str, user: str) -> str:  # noqa: ARG001
        return next(responses)

    monkeypatch.setattr("storygame.engine.freeform._story_agent_chat_complete", _fake_chat)
    adapter = LlmFreeformProposalAdapter(mode="openai")
    dialog, action = adapter.propose(state, "HEAD INTO THE MANSION")

    assert dialog["speaker"] == "narrator"
    assert action["intent"] == "move"
    assert tuple(action["targets"]) == ("north",)
    assert action["arguments"]["planner_source"] == "llm"


def test_llm_freeform_adapter_fallback_normalizes_semantic_navigation(monkeypatch) -> None:
    state = build_default_state(seed=4054, genre="mystery")

    def _boom(mode: str, system: str, user: str) -> str:  # noqa: ARG001
        raise RuntimeError("planner unavailable")

    monkeypatch.setattr("storygame.engine.freeform._story_agent_chat_complete", _boom)
    adapter = LlmFreeformProposalAdapter(mode="openai", fallback=RuleBasedFreeformProposalAdapter())
    dialog, action = adapter.propose(state, "head in the front door")

    assert dialog["speaker"] == "narrator"
    assert action["intent"] == "move"
    assert tuple(action["targets"]) == ("north",)
    assert action["arguments"]["planner_source"] == "fallback"
    assert "planner unavailable" in action["arguments"]["planner_error"]


def test_freeform_planner_prompt_includes_scene_and_item_facts() -> None:
    state = build_default_state(seed=4052, genre="mystery")

    _system, user = _freeform_planner_prompt(state, "Daria, what are you wearing?")

    assert '"scene_facts"' in user
    assert "drove your own sedan" in user
    assert '"appearance": "a crisp white blouse and a tailored black skirt with dark hair pulled back into a neat bun"' in user
    assert '"name": "dark sedan"' in user
    assert '"state": "parked_by_drive"' in user
    assert '"visible_item_names": ["dark sedan"]' in user
    assert '"exit_facts": [{"direction": "north", "destination_name": "Mansion Foyer"' in user
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
