from random import Random

from storygame.engine.facts import apply_fact_ops
from storygame.engine.freeform import RuleBasedFreeformProposalAdapter, resolve_freeform_roleplay
from storygame.engine.parser import parse_command
from storygame.engine.simulation import advance_turn, apply_events_to_state
from storygame.engine.scene_state import refresh_scene_state, scene_snapshot
from storygame.engine.state import Event
from storygame.engine.world import build_default_state
from storygame.llm.context import build_narration_context
from storygame.plot.beat_manager import select_beat


def test_build_default_state_seeds_scene_and_dramatic_facts() -> None:
    state = build_default_state(seed=41, genre="mystery")

    snapshot = scene_snapshot(state)

    assert snapshot["scene_id"] == f"scene:{state.player.location}"
    assert snapshot["location_id"] == state.player.location
    assert snapshot["beat_phase"] == "exposition"
    assert snapshot["scene_objective"] == state.active_goal
    assert "player" in snapshot["participants"]
    assert snapshot["pressure"] == "guarded"


def test_build_narration_context_reads_scene_facts_for_dramatic_fields() -> None:
    state = build_default_state(seed=42, genre="mystery")
    snapshot = scene_snapshot(state)
    scene_id = snapshot["scene_id"]
    npc_id = state.world.rooms[state.player.location].npc_ids[0]

    apply_fact_ops(
        state,
        [
            {"op": "assert", "fact": ("dramatic_question", scene_id, "Will Daria surrender the ledger page?")},
            {"op": "assert", "fact": ("player_approach", "press_for_answers")},
            {"op": "assert", "fact": ("npc_stance", npc_id, "player", "guarded")},
            {"op": "assert", "fact": ("npc_trust", npc_id, "player", "wary")},
        ],
    )

    state.append_event(
        Event(
            type="freeform_roleplay",
            turn_index=1,
            metadata={
                "action_proposal": {
                    "intent": "ask_about",
                    "targets": [npc_id],
                    "arguments": {"topic": "ledger page"},
                },
            },
        )
    )

    context = build_narration_context(state, parse_command("Daria, hand over the ledger page."), "hook")
    payload = context.as_dict()

    assert payload["scene"]["id"] == scene_id
    assert payload["scene"]["location_id"] == state.player.location
    assert payload["scene"]["dramatic_question"] == "Will Daria surrender the ledger page?"
    assert payload["scene"]["player_approach"] == "press_for_answers"
    assert payload["scene"]["pressure"] == "guarded"
    assert payload["addressed_npc_id"] == npc_id
    npc_fact = next(fact for fact in payload["npc_facts"] if fact["id"] == npc_id)
    assert npc_fact["stance_to_player"] == "guarded"
    assert npc_fact["trust_to_player"] == "wary"


def test_select_beat_prefers_canonical_scene_phase_and_role() -> None:
    state = build_default_state(seed=43, genre="mystery")
    state.progress = 0.05
    snapshot = scene_snapshot(state)

    apply_fact_ops(
        state,
        [
            {"op": "assert", "fact": ("beat_phase", "resolution")},
            {"op": "assert", "fact": ("beat_role", snapshot["scene_id"], "closure")},
        ],
    )

    beat = select_beat(state, Random(9))

    assert beat.type in {"closure", "epilogue"}
    assert "resolution" in beat.tags


def test_apply_events_to_state_refreshes_scene_dramatic_facts() -> None:
    state = build_default_state(seed=44, genre="mystery")

    apply_events_to_state(
        state,
        [
            Event(
                type="story_spike",
                delta_progress=0.65,
                delta_tension=0.5,
                turn_index=1,
            )
        ],
    )
    refresh_scene_state(state)
    snapshot = scene_snapshot(state)

    assert snapshot["beat_phase"] == "climax"
    assert snapshot["pressure"] == "critical"


def test_freeform_question_updates_scene_focus_and_dramatic_role() -> None:
    state = build_default_state(seed=45, genre="mystery")
    state.progress = 0.35
    refresh_scene_state(state)

    resolved = resolve_freeform_roleplay(
        state,
        "Daria, what about the ledger page?",
        RuleBasedFreeformProposalAdapter(),
    )
    snapshot = scene_snapshot(resolved["state"])

    assert snapshot["player_approach"] == "question"
    assert snapshot["beat_role"] == "reveal"
    assert "Daria Stone" in snapshot["dramatic_question"]
    assert "ledger page" in snapshot["dramatic_question"].lower()


def test_advance_turn_movement_refreshes_scene_identity_and_approach() -> None:
    state = build_default_state(seed=46, genre="mystery")
    current_room = state.player.location
    direction = sorted(state.world.rooms[current_room].exits.keys())[0]
    destination = state.world.rooms[current_room].exits[direction]

    next_state, _events, _beat, _template = advance_turn(state, parse_command(f"go {direction}"), Random(46))
    snapshot = scene_snapshot(next_state)

    assert next_state.player.location == destination
    assert snapshot["scene_id"] == f"scene:{destination}"
    assert snapshot["location_id"] == destination
    assert snapshot["player_approach"] == "reposition"
    assert "player" in snapshot["participants"]
