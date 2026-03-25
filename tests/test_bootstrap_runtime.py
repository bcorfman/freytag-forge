from __future__ import annotations

from storygame.engine.bootstrap import validate_bootstrap_plan
from storygame.engine.world import build_state_from_bootstrap_plan
from storygame.llm.bootstrap_contracts import parse_bootstrap_plan, parse_story_outline


def _bootstrap_payload() -> dict[str, object]:
    return {
        "premise": "A detective must untangle a theft inside a sealed estate.",
        "setting": "Rain-soaked manor",
        "tone": "mystery",
        "cast": [
            {"name": "Detective Elias Wren", "role": "protagonist"},
            {"name": "Mara Vale", "role": "assistant"},
        ],
        "items": [
            {"name": "Case File", "kind": "clue"},
            {"name": "Brass Key", "kind": "tool"},
        ],
        "main_goal": "Recover the stolen ledger before the house turns on itself.",
        "subgoals": ["Identify who moved the ledger."],
        "event_hints": ["The lights fail on the third turn."],
        "constraints": ["Keep the estate explorable room by room."],
    }


def _validated_bootstrap_plan() -> dict[str, object]:
    return parse_bootstrap_plan(
        {
            "outline_id": "estate_theft",
            "protagonist_id": "detective_elias_wren",
            "locations": [
                {
                    "id": "foyer",
                    "name": "Foyer",
                    "description": "A narrow entry hall with rain on the tiles.",
                    "exits": {"north": "study"},
                    "traits": ["indoors"],
                },
                {
                    "id": "study",
                    "name": "Study",
                    "description": "Shelves and ash crowd the walls.",
                    "exits": {"south": "foyer"},
                    "traits": ["quiet"],
                },
            ],
            "characters": [
                {
                    "id": "detective_elias_wren",
                    "name": "Detective Elias Wren",
                    "description": "A patient detective with a rigid memory for detail.",
                    "role": "protagonist",
                    "stable_traits": ["observant", "male"],
                    "dynamic_traits": ["wet coat"],
                    "location_id": "foyer",
                    "inventory": [],
                },
                {
                    "id": "mara_vale",
                    "name": "Mara Vale",
                    "description": "An assistant who notices what others miss.",
                    "role": "assistant",
                    "stable_traits": ["observant"],
                    "dynamic_traits": [],
                    "location_id": "foyer",
                    "inventory": ["brass_key"],
                },
            ],
            "items": [
                {
                    "id": "case_file",
                    "name": "Case File",
                    "description": "A damp folder with the first witness statement.",
                    "kind": "clue",
                    "stable_traits": ["paper"],
                    "dynamic_traits": [],
                    "location_id": "study",
                    "holder_id": "",
                    "portable": True,
                },
                {
                    "id": "brass_key",
                    "name": "Brass Key",
                    "description": "A heavy key warmed by constant handling.",
                    "kind": "tool",
                    "stable_traits": ["metal"],
                    "dynamic_traits": [],
                    "location_id": "",
                    "holder_id": "mara_vale",
                    "portable": True,
                },
            ],
            "goals": [
                {
                    "goal_id": "recover_ledger",
                    "summary": "Recover the stolen ledger before it leaves the estate.",
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
                        "numeric_delta": [{"key": "progress", "delta": 0.1}],
                        "reasons": ["case_file_found"],
                        "emit_message": "Finding the case file sharpens the investigation.",
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
                    "location_ids": ["foyer"],
                    "required_facts": [],
                    "forbidden_facts": [],
                    "effects": {
                        "assert": [{"fact": ["flag", "player", "lights_failed"]}],
                        "retract": [],
                        "numeric_delta": [{"key": "tension", "delta": 0.15}],
                        "reasons": ["lights_failed"],
                        "emit_message": "The manor lights fail, leaving only the storm outside.",
                    },
                },
            ],
        }
    )


def test_story_outline_contract_accepts_minimal_outline() -> None:
    outline = parse_story_outline(_bootstrap_payload())

    assert outline["premise"].startswith("A detective")
    assert outline["cast"][0]["name"] == "Detective Elias Wren"
    assert outline["main_goal"].startswith("Recover the stolen ledger")


def test_bootstrap_plan_validation_rejects_unknown_references() -> None:
    payload = _validated_bootstrap_plan()
    payload["items"] = list(payload["items"])
    payload["items"][0] = dict(payload["items"][0], location_id="missing_room")

    plan = parse_bootstrap_plan(payload)

    try:
        validate_bootstrap_plan(plan)
    except ValueError as exc:
        assert "missing_room" in str(exc)
    else:
        raise AssertionError("Expected bootstrap validation failure for unknown room reference.")


def test_build_state_from_bootstrap_plan_realizes_world_and_facts() -> None:
    plan = _validated_bootstrap_plan()
    validate_bootstrap_plan(plan)

    state = build_state_from_bootstrap_plan(seed=77, plan=plan, tone="stormy")

    assert state.player.location == "foyer"
    assert state.world.rooms["study"].item_ids == ("case_file",)
    assert state.world_facts.holds("holding", "mara_vale", "brass_key")
    assert state.world_facts.holds("story_goal", "primary", "Recover the stolen ledger before it leaves the estate.")
    assert state.world_facts.holds("active_goal", "Recover the stolen ledger before it leaves the estate.")
    assert state.world_package["bootstrap_plan"]["outline_id"] == "estate_theft"
    assert len(state.world_package["trigger_specs"]) == 2
