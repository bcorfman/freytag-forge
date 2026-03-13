from __future__ import annotations

import pytest

from storygame.llm.story_agents.contracts import (
    StoryAgentContractError,
    parse_character_designer_output,
    parse_narrator_opening_output,
    parse_plot_designer_output,
    parse_story_architect_output,
)
from storygame.llm.story_agents.prompts import (
    build_character_designer_prompt,
    build_narrator_opening_prompt,
    build_plot_designer_prompt,
    build_story_architect_prompt,
)


def test_story_agent_contracts_accept_valid_payloads():
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

    assert architect["protagonist_name"] == "Noah Kade"
    assert cast["contacts"][0]["name"] == "Mina Cole"
    assert plot["assistant_name"] == "Mina Cole"
    assert len(opening["paragraphs"]) == 3


def test_story_agent_contracts_reject_invalid_shapes():
    with pytest.raises(StoryAgentContractError):
        parse_story_architect_output({"protagonist_name": "", "tone": "dark"})
    with pytest.raises(StoryAgentContractError):
        parse_character_designer_output({"contacts": [{"name": "Premise", "role": "assistant"}]})
    with pytest.raises(StoryAgentContractError):
        parse_plot_designer_output({"assistant_name": "", "actionable_objective": ""})
    with pytest.raises(StoryAgentContractError):
        parse_narrator_opening_output({"paragraphs": ["only one"]})


def test_story_agent_prompts_contain_contract_and_json_instruction():
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


def test_story_agent_contracts_normalize_light_pattern_variants() -> None:
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

    assert architect["protagonist_name"] == "Noah Kade"
    assert architect["protagonist_background"].endswith(".")
    assert architect["tone"] == "dark"
    assert cast["contacts"][0]["name"] == "Daria Stone"
    assert plot["assistant_name"] == "Daria Stone"
    assert plot["actionable_objective"].endswith(".")
    assert all(paragraph.endswith((".", "!", "?")) for paragraph in opening["paragraphs"])
