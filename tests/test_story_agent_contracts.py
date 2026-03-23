from __future__ import annotations

import pytest

from storygame.llm.story_agents.contracts import (
    parse_story_bootstrap_output,
    StoryAgentContractError,
    parse_character_designer_output,
    parse_narrator_opening_output,
    parse_plot_designer_output,
    parse_story_architect_output,
)
from storygame.llm.story_agents.prompts import (
    build_story_bootstrap_prompt,
    build_character_designer_prompt,
    build_narrator_opening_prompt,
    build_plot_designer_prompt,
    build_story_architect_prompt,
)


def test_story_agent_contracts_accept_valid_payloads():
    bootstrap = parse_story_bootstrap_output(
        {
            "protagonist_name": "Noah Kade",
            "protagonist_background": "A detective returning for one last case.",
            "assistant_name": "Mina Cole",
            "actionable_objective": "Review the case file and choose the first lead.",
            "primary_goal": "Expose the buried conspiracy behind the murders.",
            "secondary_goals": ["Find the missing witness."],
            "expanded_outline": "Investigate the murders, expose the conspiracy, and survive the retaliation.",
            "story_beats": [
                {"beat_id": "hook", "summary": "Arrive at the estate and assess the scene.", "min_progress": 0.0},
                {"beat_id": "midpoint", "summary": "Identify the conspiracy behind the killings.", "min_progress": 0.5},
                {"beat_id": "climax", "summary": "Confront the killer with proof.", "min_progress": 0.85},
            ],
            "villains": [
                {
                    "name": "Magistrate Voss",
                    "motive": "Protect the conspiracy.",
                    "means": "Control over hired killers and records.",
                    "opportunity": "Direct access to the estate and witnesses.",
                }
            ],
            "timed_events": [
                {
                    "event_id": "butler_warning",
                    "summary": "The butler quietly warns that someone is destroying records.",
                    "min_turn": 2,
                    "location": "foyer",
                    "participants": ["Mina Cole"],
                }
            ],
            "clue_placements": [
                {
                    "item_id": "case_file",
                    "room_id": "front_steps",
                    "clue_text": "The file highlights the victim timeline.",
                    "hidden_reason": "It was tucked under the detective's arm on arrival.",
                }
            ],
            "hidden_threads": ["The assistant knows more than she admits."],
            "reveal_schedule": [{"thread_index": 0, "min_progress": 0.55}],
            "contacts": [{"name": "Mina Cole", "role": "assistant", "trait": "observant"}],
            "opening_paragraphs": ["p1", "p2", "p3"],
        }
    )
    architect = parse_story_architect_output(
        {
            "protagonist_name": "Noah Kade",
            "protagonist_background": "A detective returning for one last case.",
            "secrets_to_hide": ["late reveal 1"],
            "tone": "dark",
        }
    )
    cast = parse_character_designer_output(
        {"contacts": [{"name": "Mina Cole", "role": "assistant", "trait": "observant"}]}
    )
    plot = parse_plot_designer_output(
        {"assistant_name": "Mina Cole", "actionable_objective": "Review the case file and pick first lead."}
    )
    opening = parse_narrator_opening_output(
        {"paragraphs": ["p1", "p2", "p3"]}
    )

    assert bootstrap["assistant_name"] == "Mina Cole"
    assert bootstrap["villains"][0]["name"] == "Magistrate Voss"
    assert architect["protagonist_name"] == "Noah Kade"
    assert cast["contacts"][0]["name"] == "Mina Cole"
    assert plot["assistant_name"] == "Mina Cole"
    assert len(opening["paragraphs"]) == 3


def test_story_agent_contracts_reject_invalid_shapes():
    with pytest.raises(StoryAgentContractError):
        parse_story_bootstrap_output({"protagonist_name": "", "assistant_name": ""})
    with pytest.raises(StoryAgentContractError):
        parse_story_architect_output({"protagonist_name": "", "tone": "dark"})
    with pytest.raises(StoryAgentContractError):
        parse_character_designer_output({"contacts": [{"name": "Premise", "role": "assistant"}]})
    with pytest.raises(StoryAgentContractError):
        parse_plot_designer_output({"assistant_name": "", "actionable_objective": ""})
    with pytest.raises(StoryAgentContractError):
        parse_narrator_opening_output({"paragraphs": ["only one"]})


def test_story_agent_prompts_contain_contract_and_json_instruction():
    system, user = build_story_bootstrap_prompt(
        "A detective returns.",
        "mystery",
        "dark",
        "medium",
        ["hook", "midpoint", "climax"],
        [{"name": "Mina Cole", "role": "assistant", "trait": "observant"}],
        {
            "room_id": "front_steps",
            "name": "Outside The Mansion",
            "description": "Cold stone.",
            "items": ["case_file"],
            "npcs": ["Mina Cole"],
        },
        [{"room_id": "front_steps", "name": "Outside The Mansion", "description": "Cold stone.", "items": ["case_file"], "npcs": ["Mina Cole"], "exits": {"north": "foyer"}}],
        [{"item_id": "case_file", "name": "Case File", "description": "Folder.", "kind": "clue"}],
        ["field kit"],
    )
    assert "json only" in system.lower()
    assert "opening_paragraphs" in system
    assert "story_beats" in system
    assert "villains" in system
    assert "opening_paragraphs must stay materially consistent with opening_room description, exits, visible npcs, visible items, and inventory_seed" in system.lower()
    assert "do not invent extra furniture, worksurfaces, papers, desks, tables, or document piles" in system.lower()
    assert "premise" in user.lower()

    system, user = build_story_architect_prompt("A detective returns.", "Noah", "mystery", "dark")
    assert "json only" in system.lower()
    assert "protagonist_name" in system
    assert "premise" in user.lower()

    system, _user = build_character_designer_prompt("Noah", [{"name": "Mina"}])
    assert "contacts" in system

    system, _user = build_plot_designer_prompt("Goal", "Mina")
    assert "actionable_objective" in system

    system, _user = build_narrator_opening_prompt("draft")
    assert "paragraphs" in system
    assert "stay materially consistent with the room description, exits, visible items, visible npcs, and inventory" in system.lower()
    assert "do not invent extra furniture, desks, tables, papers, or document staging" in system.lower()


def test_story_agent_contracts_normalize_light_pattern_variants() -> None:
    bootstrap = parse_story_bootstrap_output(
        {
            "protagonist_name": "Name: Noah Kade",
            "protagonist_background": "Background: A detective returning for one last case",
            "assistant_name": "assistant_name: Daria Stone",
            "actionable_objective": "Objective: Review the case file first",
            "primary_goal": "Primary goal: Expose the conspiracy",
            "secondary_goals": ["  Find the witness  ", ""],
            "expanded_outline": "Outline: Follow the murders to the buried conspiracy",
            "story_beats": [
                {"beat_id": "hook", "summary": "The estate opens under heavy rain", "min_progress": 0.0},
                {"beat_id": "midpoint", "summary": "The route key reveals the conspiracy", "min_progress": 0.5},
                {"beat_id": "climax", "summary": "Confront the mastermind", "min_progress": 0.85},
            ],
            "villains": [
                {
                    "name": "Name: Magistrate Voss",
                    "motive": "Motive: protect the conspiracy",
                    "means": "Means: hired killers",
                    "opportunity": "Opportunity: access to the estate",
                }
            ],
            "timed_events": [
                {
                    "event_id": "warning",
                    "summary": "A warning reaches the foyer",
                    "min_turn": 2,
                    "location": "foyer",
                    "participants": [" Daria Stone ", ""],
                }
            ],
            "clue_placements": [
                {
                    "item_id": "route_key",
                    "room_id": "watch_tower",
                    "clue_text": "The key opens the service route",
                    "hidden_reason": "Hidden behind a loose stone",
                }
            ],
            "hidden_threads": ["  buried ledger  ", ""],
            "reveal_schedule": [{"thread_index": 0, "min_progress": 0.55}],
            "contacts": [
                {"name": "Characters:", "role": "assistant", "trait": "observant"},
                {"name": "Name: Daria Stone", "role": "Role: assistant", "trait": "Trait: observant"},
            ],
            "opening_paragraphs": ["first paragraph", "second paragraph", "third paragraph"],
            "unused": {"ignored": True},
        }
    )
    architect = parse_story_architect_output(
        {
            "protagonist_name": "Name: Noah Kade",
            "protagonist_background": "Background: A detective returning for one last case",
            "secrets_to_hide": ["  late reveal 1  ", ""],
            "tone": " Dark ",
            "extra_key": "ignored",
        }
    )
    cast = parse_character_designer_output(
        {
            "contacts": [
                {"name": "Characters:", "role": "assistant", "trait": "observant"},
                {"name": "Name: Daria Stone", "role": "Role: assistant", "trait": "Trait: observant"},
            ]
        }
    )
    plot = parse_plot_designer_output(
        {
            "assistant_name": "assistant_name: Daria Stone",
            "actionable_objective": "Objective: Review the case file and pick your first lead",
            "unused": {"ignored": True},
        }
    )
    opening = parse_narrator_opening_output(
        {"paragraphs": ["first paragraph", "second paragraph.", "third paragraph"], "other": "ignored"}
    )

    assert bootstrap["protagonist_name"] == "Noah Kade"
    assert bootstrap["contacts"][0]["name"] == "Daria Stone"
    assert bootstrap["villains"][0]["name"] == "Magistrate Voss"
    assert bootstrap["opening_paragraphs"][0].endswith(".")
    assert architect["protagonist_name"] == "Noah Kade"
    assert architect["protagonist_background"].endswith(".")
    assert architect["tone"] == "dark"
    assert cast["contacts"][0]["name"] == "Daria Stone"
    assert plot["assistant_name"] == "Daria Stone"
    assert plot["actionable_objective"].endswith(".")
    assert all(paragraph.endswith((".", "!", "?")) for paragraph in opening["paragraphs"])


def test_narrator_opening_contract_accepts_wrapped_draft_shape() -> None:
    opening = parse_narrator_opening_output(
        {
            "draft": {
                "paragraphs": [
                    "first paragraph",
                    "second paragraph",
                    "third paragraph",
                ]
            }
        }
    )

    assert len(opening["paragraphs"]) == 3
