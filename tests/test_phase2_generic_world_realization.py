from __future__ import annotations

from copy import deepcopy

from storygame.engine.facts import case_facts, player_context_facts
from storygame.engine.world import realize_world_package
from storygame.engine.world_builder import build_world_package, validate_world_package


def test_packages_with_distinct_openings_realize_through_the_same_service() -> None:
    first = build_world_package("fantasy", "short", 13, "epic")
    first_state = realize_world_package(first, seed=13)
    second = deepcopy(first)
    second["map"]["rooms"] = ["harbor", "observatory"]
    second["map"]["paths"] = [
        {"direction": "up", "from": "harbor", "to": "observatory"},
        {"direction": "down", "from": "observatory", "to": "harbor"},
    ]
    second["map"]["environment"] = {
        "harbor": {"exposure": "outdoor", "ambient_source": "the quay"},
        "observatory": {"exposure": "enclosed"},
    }
    second["map"]["locks"] = []
    second["map"]["room_presentation"] = {
        "harbor": {"name": "Storm Harbor", "description": "Salt spray lashes the empty quay."},
        "observatory": {"name": "Old Observatory", "description": "The dome points at a broken moon."},
    }
    second["characters"] = [
        {
            "id": "navigator",
            "name": "Ilya North",
            "location": "harbor",
            "available": True,
            "traits": ["precise"],
            "appearance": "A weathered navigator in a wool coat.",
            "role": "guide",
            "relationship": "trusted_contact",
            "scene_purpose": "Keep the expedition from leaving before the tide turns.",
            "initial_knowledge": ["tide_table"],
            "protected_knowledge": ["sealed_chart"],
        }
    ]
    second["entities"]["npcs"] = ["Ilya North"]
    second["items"] = [
        {
            "id": "weather_log",
            "name": "weather log",
            "description": "A water-stained log of the storm.",
            "kind": "document",
            "portable": True,
            "tags": ["document"],
            "clue_text": "The tide will turn before dawn.",
            "initial_state": "sealed",
            "initial_custody": {"kind": "npc", "id": "navigator"},
        }
    ]
    second["item_graph"]["items"] = ["weather_log"]
    second["item_graph"]["edges"] = []
    second["opening_setup"] = {
        "protagonist_name": "Captain Rowan",
        "opening_contact": {"id": "navigator", "role": "guide", "relationship": "trusted_contact"},
        "public_briefing": ["The harbor is closing under the storm."],
        "pending_knowledge": ["tide_table"],
        "protected_knowledge": ["sealed_chart"],
        "player_context": {"arrival": "You arrived by cutter before the storm closed the harbor."},
        "case_facts": {"document_status": "The weather log remains sealed."},
    }

    state = realize_world_package(validate_world_package(second), seed=13)

    assert first_state.player.location != state.player.location
    assert first_state.world.rooms != state.world.rooms
    assert state.player.location == "harbor"
    assert state.world.rooms["harbor"].name == "Storm Harbor"
    assert state.world.rooms["harbor"].description == "Salt spray lashes the empty quay."
    assert state.world_facts.holds("holding", "navigator", "weather_log")
    assert state.world_facts.holds("item_state", "weather_log", "sealed")
    assert state.world_facts.holds("npc_relationship", "Ilya North", "player", "trusted_contact")
    assert state.world_facts.holds(
        "npc_scene_purpose", "navigator", "Keep the expedition from leaving before the tide turns."
    )
    assert {entry["key"]: entry["text"] for entry in player_context_facts(state)}["arrival"].startswith("You arrived")
    assert {entry["key"]: entry["value"] for entry in case_facts(state)}["document_status"].startswith("The weather")


def test_mystery_world_realization_has_no_genre_setup_branch() -> None:
    state = realize_world_package(build_world_package("mystery", "short", 103, "dark"), seed=103)

    assert state.world_facts.holds("holding", "daria_stone", "case_file")
    assert state.world_facts.holds("room_item", "front_steps", "arrival_sedan")
