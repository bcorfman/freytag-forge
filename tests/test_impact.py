from __future__ import annotations

from storygame.engine.impact import (
    assess_player_command,
    replan_scope_for_assessment,
    requires_high_impact_confirmation,
)
from storygame.engine.parser import parse_command
from tests.fast_fixtures import make_tiny_state


def test_assess_player_command_low_impact_defaults() -> None:
    state = make_tiny_state(seed=301)
    action = parse_command("look")
    assessment = assess_player_command(state, "look around", action)

    assert assessment["impact_class"] == "low"
    assert assessment["score"] >= 0.0
    assert assessment["consequences"] == ["No major disruption predicted."]
    assert requires_high_impact_confirmation(assessment) is False


def test_assess_player_command_critical_path_with_multiple_risk_dimensions() -> None:
    state = make_tiny_state(seed=302)
    action = parse_command("use gun")
    assessment = assess_player_command(
        state,
        "jump down the well and punch the police officer and spray graffiti on the school sign with a gun",
        action,
    )

    assert assessment["impact_class"] == "critical"
    assert "violent_action" in assessment["reasons"]
    assert "self_harm_risk" in assessment["reasons"]
    assert "criminal_behavior" in assessment["reasons"]
    assert "authority_target" in assessment["reasons"]
    assert "public_disruption" in assessment["reasons"]
    assert "weapon_use_signal" in assessment["reasons"]
    assert len(assessment["consequences"]) <= 3
    assert requires_high_impact_confirmation(assessment) is True
    assert replan_scope_for_assessment(assessment) == "goal_change"


def test_assess_player_command_detects_violence_against_present_npc() -> None:
    state = make_tiny_state(seed=303)
    npc_id = state.world.rooms[state.player.location].npc_ids[0]
    action = parse_command(f"attack {npc_id}")
    assessment = assess_player_command(state, f"attack {npc_id}", action)

    assert "violent_action" in assessment["reasons"]
    assert "violence_against_present_npc" in assessment["reasons"]
    assert assessment["dimensions"]["goal_violation"] > 0.0


def test_assess_player_command_can_limit_replan_to_light_scope() -> None:
    state = make_tiny_state(seed=304)
    action = parse_command("spray graffiti on statue")
    assessment = assess_player_command(state, "spray graffiti on statue", action)

    assert requires_high_impact_confirmation(assessment) is False
    assert replan_scope_for_assessment(assessment) == "light"


def test_assess_player_command_keeps_authority_status_questions_playable() -> None:
    state = make_tiny_state(seed=305)

    assessment = assess_player_command(
        state,
        "Daria, are the police inside?",
        parse_command("Daria, are the police inside?"),
    )

    assert assessment["impact_class"] == "low"
    assert "authority_target" not in assessment["reasons"]
    assert requires_high_impact_confirmation(assessment) is False


def test_assess_player_command_flags_an_actual_authority_escalation() -> None:
    state = make_tiny_state(seed=306)

    assessment = assess_player_command(state, "Call the police.", parse_command("Call the police."))

    assert "authority_target" in assessment["reasons"]
    assert requires_high_impact_confirmation(assessment) is True
