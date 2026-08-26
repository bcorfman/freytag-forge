"""End-to-end validation for LLM-first scene progression."""

from __future__ import annotations

from pathlib import Path

import pytest

from storygame.runtime.engine import RuntimeEngine
from storygame.runtime.state import RuntimeState, RuntimeStateError
from storygame.story_package.loader import load_story_package

PACKAGE = load_story_package(Path("data/stories/continuity-initiative"))


def _provider(payload: dict[str, object], calls: list[str]):
    def call(player_input: str) -> dict[str, object]:
        calls.append(player_input)
        return payload

    return call


def test_normal_freeform_turn_calls_provider_once_and_transitions() -> None:
    calls: list[str] = []
    engine = RuntimeEngine(
        RuntimeState.bootstrap(PACKAGE),
        _provider(
            {
                "narration": "I connect Sarah's disappearance to the card.",
                "operations": [
                    {
                        "operation": "assert",
                        "fact": {"predicate": "sarah_abduction_suspicion", "subject": "story", "value": "true"},
                    }
                ],
                "transition": {"transition_id": "t_1a_1b"},
            },
            calls,
        ),
    )

    engine.turn("I question everyone, then head for the dead drop.")

    assert calls == ["I question everyone, then head for the dead drop."]
    assert engine.state.current_scene_id == "1B"


def test_unsatisfied_trigger_leaves_state_unchanged() -> None:
    engine = RuntimeEngine(
        RuntimeState.bootstrap(PACKAGE),
        _provider({"narration": "I leave now.", "transition": {"transition_id": "t_1a_1b"}}, []),
    )

    with pytest.raises(RuntimeStateError, match="triggers"):
        engine.turn("I leave immediately.")

    assert engine.state.current_scene_id == "1A"
    assert engine.state.facts.as_json() == []


def test_deadline_pacing_event_advances_without_parsing_player_text() -> None:
    calls: list[str] = []
    engine = RuntimeEngine(
        RuntimeState.bootstrap(PACKAGE),
        _provider({"narration": "I hesitate.", "narrative_seconds": 60}, calls),
    )

    engine.turn("wait")
    engine.turn("I keep waiting, unsure what to do.")

    assert calls == ["wait", "I keep waiting, unsure what to do."]
    assert engine.state.current_scene_id == "1A"
    assert engine.state.facts.has("facility_proof", "story", value="true")
    assert "pressure_1a" in engine.state.fired_event_ids


def test_game_break_proceed_commits_candidate_and_return_restores_snapshot() -> None:
    state = RuntimeState.bootstrap(PACKAGE)
    engine = RuntimeEngine(
        state,
        _provider(
            {
                "narration": "I permanently incapacitate Gabriel.",
                "operations": [{"operation": "assert", "fact": {"predicate": "incapacitated", "subject": "gabriel"}}],
            },
            [],
        ),
    )

    proposal = engine.turn("I attack Gabriel.")
    assert proposal.game_break is not None
    assert state.facts.as_json() == []
    engine.resolve_break("return_to_scene")
    assert state.facts.as_json() == []

    engine.turn("I attack Gabriel again.")
    engine.resolve_break("proceed")
    assert state.facts.has("incapacitated", "gabriel")


def test_declared_item_fallback_prevents_false_game_break() -> None:
    state = RuntimeState.bootstrap(PACKAGE)
    engine = RuntimeEngine(
        state,
        _provider(
            {
                "narration": "The memory card is destroyed.",
                "operations": [{"operation": "assert", "fact": {"predicate": "destroyed", "subject": "memory_card"}}],
            },
            [],
        ),
    )

    engine.turn("I smash the memory card.")

    assert not state.has_pending_break
    assert state.facts.has("destroyed", "memory_card")


@pytest.mark.parametrize(("turns", "narrative_seconds"), ((18, 65), (20, 60), (22, 55)))
def test_main_path_pacing_simulations_reach_resolution_in_target_narrative_window(
    turns: int, narrative_seconds: int
) -> None:
    transitions = (
        ("sarah_abduction_suspicion", "t_1a_1b"),
        ("facility_proof", "t_1b_1c"),
        ("false_identities_ready", "t_1c_2a"),
        ("janus_evidence", "t_2a_2b"),
        ("purge_clock_started", "t_2b_2c"),
        ("sarah_reached", "t_2c_3a"),
        ("relay_open", "t_3a_3b"),
        ("broadcast_started", "t_3b_3c"),
    )
    payloads: list[dict[str, object]] = [
        {
            "narration": f"I make progress toward {fact_id}.",
            "narrative_seconds": narrative_seconds,
            "operations": [
                {"operation": "assert", "fact": {"predicate": fact_id, "subject": "story", "value": "true"}}
            ],
            "transition": {"transition_id": transition_id},
        }
        for fact_id, transition_id in transitions
    ] + [{"narration": "I take stock of what comes next.", "narrative_seconds": narrative_seconds}] * (turns - 8)

    def provider(_: str) -> dict[str, object]:
        return payloads.pop(0)

    engine = RuntimeEngine(RuntimeState.bootstrap(PACKAGE), provider)
    phases: list[str] = []
    for _ in range(turns):
        engine.turn("I follow the lead.")
        phases.append(engine.state.phase)

    assert engine.state.current_scene_id == "3C"
    assert 19 * 60 <= engine._elapsed_seconds() <= 21 * 60
    assert phases == sorted(
        phases,
        key=(
            "exposition",
            "inciting_incident",
            "rising_action",
            "crisis",
            "climax",
            "falling_action",
            "resolution",
        ).index,
    )
    assert len(engine.state.fired_event_ids) == len(set(engine.state.fired_event_ids))
