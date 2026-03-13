from __future__ import annotations

import pytest

from storygame.llm.story_agents.contracts import (
    StoryAgentContractError,
    parse_character_designer_output,
    parse_narrator_opening_output,
    parse_plot_designer_output,
    parse_story_architect_output,
)


def test_story_architect_contract_rejects_empty_normalized_fields() -> None:
    with pytest.raises(StoryAgentContractError, match="protagonist_name:min_length"):
        parse_story_architect_output(
            {
                "protagonist_name": "Name: ",
                "protagonist_background": "Background: detective",
                "secrets_to_hide": [],
                "tone": "dark",
            }
        )

    with pytest.raises(StoryAgentContractError, match="protagonist_background:min_length"):
        parse_story_architect_output(
            {
                "protagonist_name": "Noah Kade",
                "protagonist_background": "Background: ",
                "secrets_to_hide": [],
                "tone": "dark",
            }
        )


def test_character_and_plot_contract_reject_when_all_candidates_invalid() -> None:
    with pytest.raises(StoryAgentContractError, match="missing_valid_contact"):
        parse_character_designer_output(
            {
                "contacts": [
                    {"name": "Characters:", "role": "assistant", "trait": "observant"},
                    {"name": "Name: ", "role": "Role: ", "trait": "Trait: "},
                ]
            }
        )

    with pytest.raises(StoryAgentContractError, match="assistant_name:min_length"):
        parse_plot_designer_output({"assistant_name": "name: ", "actionable_objective": "Objective: valid"})

    with pytest.raises(StoryAgentContractError, match="actionable_objective:min_length"):
        parse_plot_designer_output({"assistant_name": "Mina", "actionable_objective": "objective: "})


def test_narrator_opening_contract_rejects_empty_paragraphs_after_trim() -> None:
    with pytest.raises(StoryAgentContractError, match="paragraphs:min_length"):
        parse_narrator_opening_output({"paragraphs": [" ", "  ", "\n"]})
