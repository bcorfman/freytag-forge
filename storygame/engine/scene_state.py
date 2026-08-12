from __future__ import annotations

from storygame.engine.facts import (
    beat_phase,
    beat_role,
    current_scene,
    dramatic_question,
    player_approach,
    replace_fact_group,
    scene_location,
    scene_objective,
    scene_participants,
    scene_pressure,
)
from storygame.plot.dramatic_policy import infer_beat_role, infer_dramatic_question, pressure_bucket
from storygame.plot.freytag import get_phase


def _scene_id_for_location(location_id: str) -> str:
    return f"scene:{location_id}"

def scene_snapshot(state) -> dict[str, object]:
    scene_id = current_scene(state)
    phase = beat_phase(state) or get_phase(state.progress)
    participants = scene_participants(state, scene_id)
    if not participants:
        room = state.world.rooms[state.player.location]
        participants = ("player", *room.npc_ids)
    objective = scene_objective(state, scene_id)
    approach = player_approach(state) or "observe"
    question = dramatic_question(state, scene_id) or infer_dramatic_question(
        goal=objective,
        approach=approach,
        intent=approach,
    )
    pressure = scene_pressure(state, scene_id) or pressure_bucket(state.tension)
    return {
        "scene_id": scene_id,
        "location_id": scene_location(state, scene_id),
        "scene_objective": objective,
        "dramatic_question": question,
        "pressure": pressure,
        "beat_phase": phase,
        "beat_role": beat_role(state, scene_id) or infer_beat_role(phase, approach, pressure),
        "player_approach": approach,
        "participants": participants,
    }


def refresh_scene_state(state, turn_focus: dict[str, str] | None = None) -> dict[str, object]:
    scene_id = _scene_id_for_location(state.player.location)
    focus = {} if turn_focus is None else dict(turn_focus)
    objective = state.active_goal.strip()
    prior_question = dramatic_question(state, scene_id).strip()
    prior_approach = player_approach(state).strip()
    room = state.world.rooms[state.player.location]
    participants = ("player", *room.npc_ids)
    phase = str(focus.get("beat_phase", "")).strip() or get_phase(state.progress)
    approach = str(focus.get("player_approach", "")).strip() or prior_approach or "observe"
    pressure = str(focus.get("scene_pressure", "")).strip() or pressure_bucket(state.tension)
    role = str(focus.get("beat_role", "")).strip() or infer_beat_role(phase, approach, pressure)
    question = str(focus.get("dramatic_question", "")).strip() or prior_question or infer_dramatic_question(
        goal=objective,
        approach=approach,
        intent=approach,
    )

    replace_fact_group(state, "current_scene", (("current_scene", scene_id),))
    replace_fact_group(state, "scene_location", (("scene_location", scene_id, state.player.location),))
    replace_fact_group(state, "scene_objective", (("scene_objective", scene_id, objective),))
    replace_fact_group(state, "dramatic_question", (("dramatic_question", scene_id, question),))
    replace_fact_group(state, "scene_pressure", (("scene_pressure", scene_id, pressure),))
    replace_fact_group(state, "beat_phase", (("beat_phase", phase),))
    replace_fact_group(state, "beat_role", (("beat_role", scene_id, role),))
    replace_fact_group(state, "player_approach", (("player_approach", approach),))
    replace_fact_group(
        state,
        "scene_participant",
        tuple(("scene_participant", scene_id, participant_id) for participant_id in participants),
    )

    return scene_snapshot(state)
