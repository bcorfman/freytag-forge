from random import Random

from storygame.engine.facts import apply_fact_ops, dramatic_metric, set_dramatic_metric
from storygame.engine.parser import parse_command
from storygame.engine.simulation import advance_turn
from storygame.engine.world import build_default_state
from storygame.plot.beat_manager import select_beat
from storygame.plot.beat_policy import BeatPolicy, BeatPolicyInput, build_beat_policy_input


def test_beat_policy_uses_fact_backed_phase_role_pressure_and_conflict() -> None:
    state = build_default_state(seed=601, genre="mystery")
    scene_id = f"scene:{state.player.location}"
    apply_fact_ops(
        state,
        [
            {"op": "assert", "fact": ("beat_phase", "climax")},
            {"op": "assert", "fact": ("beat_role", scene_id, "confrontation")},
            {"op": "assert", "fact": ("scene_pressure", scene_id, "critical")},
            {"op": "assert", "fact": ("active_conflict", scene_id, "expose_the_saboteur")},
            {"op": "assert", "fact": ("obstacle_mode", scene_id, "direct")},
            {"op": "assert", "fact": ("npc_scene_goal", "daria_stone", "protect_the_ledger")},
        ],
    )

    decision = BeatPolicy().decide(state, turn_index=4)

    assert decision.phase == "climax"
    assert decision.beat_role == "confrontation"
    assert decision.scene_pressure == "critical"
    assert decision.active_conflict == "expose_the_saboteur"
    assert decision.beat in {"confrontation", "irreversible_choice"}
    assert "protect_the_ledger" in decision.npc_scene_goals


def test_beat_selection_is_stable_without_rng_and_varies_by_approach() -> None:
    state = build_default_state(seed=602, genre="mystery")
    state.turn_index = 3
    state.beat_history = ("complication",)
    state.world_facts.assert_fact("player_approach", "investigate")
    first = BeatPolicy().decide(state, turn_index=state.turn_index)
    second = BeatPolicy().decide(state, turn_index=state.turn_index)
    assert first == second

    state.world_facts.retract_fact("player_approach", "investigate")
    state.world_facts.assert_fact("player_approach", "coerce")
    assert BeatPolicy().decide(state, turn_index=state.turn_index).beat != first.beat


def test_legacy_select_beat_delegates_to_fact_driven_policy() -> None:
    state = build_default_state(seed=603, genre="mystery")
    apply_fact_ops(
        state,
        [
            {"op": "retract", "fact": ("beat_phase", "exposition")},
            {"op": "assert", "fact": ("beat_phase", "resolution")},
            {"op": "retract", "fact": ("beat_role", f"scene:{state.player.location}", "orientation")},
            {"op": "assert", "fact": ("beat_role", f"scene:{state.player.location}", "closure")},
        ],
    )
    beat = select_beat(state, Random(1))
    assert beat.type in {"closure", "epilogue"}
    assert beat.selection_reason


def test_reveal_and_timed_progression_use_canonical_facts() -> None:
    state = build_default_state(seed=604, genre="mystery")
    state.world_package["story_plan"] = {}
    apply_fact_ops(
        state,
        [
            {"op": "assert", "fact": ("story_hidden_thread", "A signal identifies the missing witness.")},
            {"op": "assert", "fact": ("story_reveal_schedule", "0", "0.0")},
            {"op": "assert", "fact": ("planned_event", "alarm", "The archive alarm sounds.", "0", "foyer")},
        ],
    )
    next_state, events, _beat, _template = advance_turn(state, parse_command("look"), Random(604))
    assert any(event.type == "story_reveal" for event in events)
    assert any(event.type == "timed_story_event" for event in events)
    assert next_state.world_facts.holds("flag", "player", "story_reveal_0")


def test_policy_handles_malformed_and_deferred_schedule_entries() -> None:
    state = build_default_state(seed=605, genre="mystery")
    state.world_package["story_plan"] = {
        "hidden_threads": ("A lead",),
        "reveal_schedule": ("not-a-mapping", {"thread_index": 0, "min_progress": 2.0}),
        "timed_events": ("not-a-mapping", {"event_id": "late", "summary": "Later", "min_turn": 99}),
    }
    assert isinstance(build_beat_policy_input(state), BeatPolicyInput)
    assert BeatPolicy().progression_events(state) == []


def test_dramatic_metrics_are_canonical_projection_values() -> None:
    state = build_default_state(seed=606, genre="mystery")
    assert dramatic_metric(state, "progress", state.progress) == state.progress
    set_dramatic_metric(state, "progress", 0.42)
    assert dramatic_metric(state, "progress") == 0.42
    assert state.world_facts.holds("dramatic_metric", "progress", "0.420000")
