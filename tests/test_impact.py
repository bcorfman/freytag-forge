from __future__ import annotations

from storygame.engine.impact import assess_player_command, requires_high_impact_confirmation
from storygame.engine.parser import parse_command
from storygame.engine.world import build_default_state


def test_assess_player_command_low_impact_defaults() -> None:
    state = build_default_state(seed=301)
    action = parse_command("look")
    assessment = assess_player_command(state, "look around", action)

    assert assessment["impact_class"] == "low"
    assert assessment["score"] >= 0.0
    assert assessment["consequences"] == ["No major disruption predicted."]
    assert requires_high_impact_confirmation(assessment) is False


def test_assess_player_command_critical_path_with_multiple_risk_dimensions() -> None:
    state = build_default_state(seed=302)
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


def test_assess_player_command_detects_violence_against_present_npc() -> None:
    state = build_default_state(seed=303)
    npc_id = state.world.rooms[state.player.location].npc_ids[0]
    action = parse_command(f"attack {npc_id}")
    assessment = assess_player_command(state, f"attack {npc_id}", action)

    assert "violent_action" in assessment["reasons"]
    assert "violence_against_present_npc" in assessment["reasons"]
    assert assessment["dimensions"]["goal_violation"] > 0.0
