from __future__ import annotations

from random import Random

import pytest

from storygame.engine.bootstrap import validate_bootstrap_plan
from storygame.engine.scene_state import scene_snapshot
from storygame.engine.turn_runtime import execute_turn_proposal
from storygame.engine.world import build_state_from_bootstrap_plan
from storygame.llm.bootstrap_contracts import parse_bootstrap_plan
from storygame.llm.contracts import parse_turn_proposal
from storygame.persistence.savegame_sqlite import SqliteSaveStore


def _plan() -> dict[str, object]:
    return parse_bootstrap_plan(
        {
            "outline_id": "estate_runtime",
            "protagonist_id": "detective_elias_wren",
            "locations": [
                {
                    "id": "foyer",
                    "name": "Foyer",
                    "description": "A dim foyer where every footstep echoes.",
                    "exits": {"north": "study"},
                    "traits": [],
                },
                {
                    "id": "study",
                    "name": "Study",
                    "description": "A study with a burnt desk and open drawers.",
                    "exits": {"south": "foyer"},
                    "traits": [],
                },
            ],
            "characters": [
                {
                    "id": "detective_elias_wren",
                    "name": "Detective Elias Wren",
                    "description": "The detective on the case.",
                    "role": "protagonist",
                    "stable_traits": ["observant"],
                    "dynamic_traits": [],
                    "location_id": "study",
                    "inventory": [],
                },
                {
                    "id": "mara_vale",
                    "name": "Mara Vale",
                    "description": "The assistant keeps close notes.",
                    "role": "assistant",
                    "stable_traits": ["steady"],
                    "dynamic_traits": [],
                    "location_id": "study",
                    "inventory": [],
                },
            ],
            "items": [
                {
                    "id": "case_file",
                    "name": "Case File",
                    "description": "The file is still damp from the storm.",
                    "kind": "clue",
                    "stable_traits": ["paper"],
                    "dynamic_traits": [],
                    "location_id": "study",
                    "holder_id": "",
                    "portable": True,
                }
            ],
            "goals": [
                {
                    "goal_id": "recover_ledger",
                    "summary": "Recover the ledger and identify who moved it.",
                    "kind": "primary",
                    "status": "active",
                }
            ],
            "triggers": [
                {
                    "trigger_id": "find_case_file",
                    "kind": "action",
                    "enabled": True,
                    "once": True,
                    "cooldown_turns": 0,
                    "min_turn": 0,
                    "action_types": ["take_item"],
                    "actor_ids": ["player"],
                    "target_ids": [],
                    "item_ids": ["case_file"],
                    "location_ids": [],
                    "required_facts": [],
                    "forbidden_facts": [],
                    "effects": {
                        "assert": [{"fact": ["flag", "player", "case_file_found"]}],
                        "retract": [],
                        "numeric_delta": [{"key": "progress", "delta": 0.2}],
                        "reasons": ["case_file_found"],
                        "emit_message": "The case file confirms the theft was staged.",
                    },
                },
                {
                    "trigger_id": "lights_fail",
                    "kind": "turn",
                    "enabled": True,
                    "once": True,
                    "cooldown_turns": 0,
                    "min_turn": 3,
                    "action_types": [],
                    "actor_ids": [],
                    "target_ids": [],
                    "item_ids": [],
                    "location_ids": ["study"],
                    "required_facts": [],
                    "forbidden_facts": [],
                    "effects": {
                        "assert": [{"fact": ["flag", "player", "lights_failed"]}],
                        "retract": [],
                        "numeric_delta": [{"key": "tension", "delta": 0.1}],
                        "reasons": ["lights_failed"],
                        "emit_message": "The lights die and the study falls into shadow.",
                    },
                },
            ],
        }
    )


def _state():
    plan = _plan()
    validate_bootstrap_plan(plan)
    return build_state_from_bootstrap_plan(seed=91, plan=plan)


def test_turn_runtime_commits_semantic_action_and_fires_action_trigger() -> None:
    state = _state()
    proposal = parse_turn_proposal(
        {
            "turn_id": "turn-1",
            "intent": "search",
            "narration": "You lift the case file from the desk and scan the wet pages.",
            "dialogue_lines": [],
            "semantic_actions": [
                {
                    "action_id": "take-file",
                    "action_type": "take_item",
                    "actor_id": "player",
                    "target_id": "",
                    "item_id": "case_file",
                    "location_id": "study",
                }
            ],
            "state_delta": {"assert": [], "retract": [], "numeric_delta": [], "reasons": []},
        }
    )

    result = execute_turn_proposal(state, proposal, Random(5))

    assert result["state"].world_facts.holds("holding", "player", "case_file")
    assert result["state"].world_facts.holds("flag", "player", "case_file_found")
    assert any(event.type == "semantic_action" for event in result["events"])
    assert any(event.type == "trigger" for event in result["events"])
    assert result["accepted_narration"].startswith("You lift the case file")


def test_turn_runtime_does_not_mutate_state_from_narration_only() -> None:
    state = _state()
    proposal = parse_turn_proposal(
        {
            "turn_id": "turn-2",
            "intent": "look",
            "narration": "You imagine taking the case file, but do not touch it.",
            "dialogue_lines": [],
            "semantic_actions": [],
            "state_delta": {"assert": [], "retract": [], "numeric_delta": [], "reasons": []},
        }
    )

    result = execute_turn_proposal(state, proposal, Random(6))

    assert not result["state"].world_facts.holds("holding", "player", "case_file")
    assert not result["state"].world_facts.holds("flag", "player", "case_file_found")
    assert all(event.type != "trigger" for event in result["events"])


def test_turn_runtime_refreshes_scene_facts_from_conversational_proposal() -> None:
    state = _state()
    state.progress = 0.4
    proposal = parse_turn_proposal(
        {
            "turn_id": "turn-conversation",
            "intent": "ask_about",
            "narration": "Mara narrows her eyes and answers your question about the ledger.",
            "dialogue_lines": ["Mara Vale says: \"The ledger was moved before dawn.\""],
            "semantic_actions": [
                {
                    "action_id": "question-mara",
                    "action_type": "ask_about",
                    "actor_id": "player",
                    "target_id": "mara_vale",
                    "item_id": "",
                    "location_id": "study",
                }
            ],
            "state_delta": {
                "assert": [],
                "retract": [],
                "numeric_delta": [{"key": "trust:mara_vale:player", "delta": 0.05}],
                "reasons": ["conversation"],
            },
        }
    )

    result = execute_turn_proposal(state, proposal, Random(8))
    snapshot = scene_snapshot(result["state"])

    assert snapshot["player_approach"] == "question"
    assert snapshot["beat_role"] == "reveal"
    assert "Mara Vale" in snapshot["dramatic_question"]


def test_turn_runtime_prefers_canonical_facts_over_stale_legacy_views() -> None:
    state = _state()
    state.world.rooms["study"].item_ids = state.world.rooms["study"].item_ids + ("forged_note",)
    proposal = parse_turn_proposal(
        {
            "turn_id": "turn-stale-legacy",
            "intent": "search",
            "narration": "You reach for a forged note that is not really there.",
            "dialogue_lines": [],
            "semantic_actions": [
                {
                    "action_id": "take-fake-note",
                    "action_type": "take_item",
                    "actor_id": "player",
                    "target_id": "",
                    "item_id": "forged_note",
                    "location_id": "study",
                }
            ],
            "state_delta": {"assert": [], "retract": [], "numeric_delta": [], "reasons": []},
        }
    )

    with pytest.raises(ValueError, match="forged_note"):
        execute_turn_proposal(state, proposal, Random(6))


def test_turn_runtime_fires_turn_trigger_once_when_turn_threshold_is_reached() -> None:
    state = _state()
    state.turn_index = 2
    proposal = parse_turn_proposal(
        {
            "turn_id": "turn-3",
            "intent": "wait",
            "narration": "You hold still and listen to the house settle.",
            "dialogue_lines": [],
            "semantic_actions": [],
            "state_delta": {"assert": [], "retract": [], "numeric_delta": [], "reasons": []},
        }
    )

    first = execute_turn_proposal(state, proposal, Random(7))
    second = execute_turn_proposal(first["state"], proposal, Random(7))

    assert first["state"].world_facts.holds("flag", "player", "lights_failed")
    assert any(event.message_key == "The lights die and the study falls into shadow." for event in first["events"])
    assert len([event for event in first["events"] if event.type == "trigger"]) == 1
    assert len([event for event in second["events"] if event.type == "trigger"]) == 0


def test_save_and_load_preserve_bootstrap_world_package_and_triggered_state(tmp_path) -> None:
    db_path = tmp_path / "saves.sqlite"
    state = _state()
    proposal = parse_turn_proposal(
        {
            "turn_id": "turn-4",
            "intent": "search",
            "narration": "You take the case file and mark the key page.",
            "dialogue_lines": [],
            "semantic_actions": [
                {
                    "action_id": "take-file",
                    "action_type": "take_item",
                    "actor_id": "player",
                    "target_id": "",
                    "item_id": "case_file",
                    "location_id": "study",
                }
            ],
            "state_delta": {"assert": [], "retract": [], "numeric_delta": [], "reasons": []},
        }
    )
    result = execute_turn_proposal(state, proposal, Random(8))

    with SqliteSaveStore(db_path) as store:
        store.save_run("bootstrap_slot", result["state"], Random(8), raw_command="search desk", action_kind="search")
        loaded_state, _rng = store.load_run("bootstrap_slot")

    assert loaded_state.world_package["bootstrap_plan"]["outline_id"] == "estate_runtime"
    assert loaded_state.world_facts.holds("flag", "player", "case_file_found")
    assert loaded_state.world_facts.holds("holding", "player", "case_file")


def test_parse_turn_proposal_accepts_v2_shape() -> None:
    proposal = parse_turn_proposal(
        {
            "turn_id": "turn-v2",
            "mode": "conversation",
            "player_intent": {
                "summary": "Ask Mara about the ledger.",
                "addressed_npc_id": "mara_vale",
                "target_ids": ["mara_vale"],
                "item_ids": ["case_file"],
                "location_id": "study",
            },
            "scene_framing": {
                "focus": "Mara's reaction to the missing ledger.",
                "dramatic_question": "Will Mara admit what she saw before dawn?",
                "player_approach": "question",
            },
            "semantic_actions": [
                {
                    "action_id": "question-mara",
                    "action_type": "question_npc",
                    "actor_id": "player",
                    "target_id": "mara_vale",
                    "item_id": "",
                    "location_id": "study",
                }
            ],
            "state_delta": {"assert": [], "retract": [], "numeric_delta": [], "reasons": []},
            "npc_dialogue": {"speaker_id": "mara_vale", "text": "The ledger was already gone when I arrived."},
            "narration": "Mara lowers her voice and answers without looking up.",
            "beat_hints": {"escalation": "soft", "reveal_thread_ids": ["ledger"], "obstacle_mode": "guarded"},
        }
    )

    assert proposal["mode"] == "conversation"
    assert proposal["player_intent"]["summary"] == "Ask Mara about the ledger."
    assert proposal["npc_dialogue"]["speaker_id"] == "mara_vale"
    assert proposal["beat_hints"]["obstacle_mode"] == "guarded"


def test_turn_runtime_surfaces_v2_npc_dialogue_as_dialogue_lines() -> None:
    state = _state()
    proposal = parse_turn_proposal(
        {
            "turn_id": "turn-v2-dialogue",
            "mode": "conversation",
            "player_intent": {
                "summary": "Ask Mara about the ledger.",
                "addressed_npc_id": "mara_vale",
                "target_ids": ["mara_vale"],
                "item_ids": [],
                "location_id": "study",
            },
            "scene_framing": {
                "focus": "Mara's answer",
                "dramatic_question": "What does Mara know about the ledger?",
                "player_approach": "question",
            },
            "semantic_actions": [
                {
                    "action_id": "question-mara",
                    "action_type": "question_npc",
                    "actor_id": "player",
                    "target_id": "mara_vale",
                    "item_id": "",
                    "location_id": "study",
                }
            ],
            "state_delta": {"assert": [], "retract": [], "numeric_delta": [], "reasons": ["conversation"]},
            "npc_dialogue": {"speaker_id": "mara_vale", "text": "The ledger was moved before dawn."},
            "narration": "Mara narrows her eyes before answering.",
            "beat_hints": {"escalation": "none", "reveal_thread_ids": [], "obstacle_mode": "guarded"},
        }
    )

    result = execute_turn_proposal(state, proposal, Random(8))

    assert result["dialogue_lines"] == ('Mara Vale says: "The ledger was moved before dawn."',)
