from __future__ import annotations

from typing import Any

from storygame.plot.freytag import get_phase

_DEFAULT_ROLE_BY_PHASE = {
    "exposition": "orientation",
    "rising_action": "pressure",
    "climax": "confrontation",
    "falling_action": "aftermath",
    "resolution": "closure",
}

_APPROACH_BY_INTENT = {
    "ask_about": "question",
    "talk": "question",
    "greet": "rapport",
    "apologize": "rapport",
    "threaten": "coerce",
    "look": "observe",
    "inspect": "investigate",
    "inspect_item": "investigate",
    "read_case_file": "investigate",
    "read_ledger_page": "investigate",
    "take_item": "investigate",
    "take": "investigate",
    "use": "act",
    "move": "reposition",
    "move_to": "reposition",
}


def pressure_bucket(tension: float) -> str:
    if tension < 0.45:
        return "guarded"
    if tension < 0.75:
        return "pressured"
    return "critical"


def infer_player_approach(intent: str, fallback: str = "observe") -> str:
    normalized = str(intent).strip().lower()
    return _APPROACH_BY_INTENT.get(normalized, fallback)


def infer_beat_role(phase: str, approach: str, pressure: str) -> str:
    if phase == "resolution":
        return "closure"
    if phase == "falling_action":
        return "aftermath"
    if phase == "climax":
        return "confrontation"
    if approach in {"question", "investigate"}:
        return "reveal"
    if approach in {"coerce", "act"}:
        return "escalation" if pressure == "critical" else "pressure"
    if approach == "rapport":
        return "orientation" if phase == "exposition" else "reveal"
    if approach == "reposition":
        return "pressure" if phase == "rising_action" else "orientation"
    return _DEFAULT_ROLE_BY_PHASE[phase]


def infer_dramatic_question(
    *,
    goal: str,
    approach: str,
    intent: str,
    target_name: str = "",
    topic: str = "",
) -> str:
    normalized_goal = goal.strip().rstrip(".")
    normalized_topic = topic.strip().rstrip(".")
    normalized_target = target_name.strip()
    if normalized_target and normalized_topic and approach == "question":
        return f"Will {normalized_target} answer questions about {normalized_topic}?"
    if approach == "investigate" and normalized_topic:
        return f"What will this close look at the {normalized_topic} reveal?"
    if approach == "investigate" and normalized_goal:
        return f"What new lead will this investigation reveal about {normalized_goal.lower()}?"
    if approach == "reposition" and normalized_goal:
        return f"Will changing the scene position help {normalized_goal.lower()}?"
    if approach == "coerce" and normalized_target:
        return f"How far will {normalized_target} bend under pressure?"
    if approach == "rapport" and normalized_target:
        return f"Can {normalized_target} be brought into alignment with the player?"
    if normalized_goal:
        return f"Can the player {normalized_goal.lower()}?"
    return f"What follows from this {intent or 'turn'}?"


def phase_for_progress(progress: float, fact_phase: str = "") -> str:
    resolved = fact_phase.strip()
    if resolved:
        return resolved
    return get_phase(progress)


def infer_turn_focus(
    *,
    progress: float,
    tension: float,
    goal: str,
    intent: str,
    target_name: str = "",
    topic: str = "",
) -> dict[str, str]:
    phase = phase_for_progress(progress)
    approach = infer_player_approach(intent)
    pressure = pressure_bucket(tension)
    role = infer_beat_role(phase, approach, pressure)
    question = infer_dramatic_question(
        goal=goal,
        approach=approach,
        intent=intent,
        target_name=target_name,
        topic=topic,
    )
    return {
        "beat_phase": phase,
        "player_approach": approach,
        "scene_pressure": pressure,
        "beat_role": role,
        "dramatic_question": question,
    }


def turn_focus_from_action(state, action) -> dict[str, str]:  # noqa: ANN001
    target_id = str(action.target).strip()
    target_name = ""
    if target_id and target_id in state.world.npcs:
        target_name = state.world.npcs[target_id].name
    return infer_turn_focus(
        progress=state.progress,
        tension=state.tension,
        goal=state.active_goal,
        intent=str(action.kind.value),
        target_name=target_name,
        topic=target_id,
    )


def turn_focus_from_proposal(state, proposal: dict[str, Any]) -> dict[str, str]:  # noqa: ANN401
    intent = str(proposal.get("intent", "")).strip()
    target_name = ""
    topic = ""
    semantic_actions = proposal.get("semantic_actions", ())
    for action in semantic_actions:
        target_id = str(action.get("target_id", "")).strip()
        item_id = str(action.get("item_id", "")).strip()
        if target_id and target_id in state.world.npcs:
            target_name = state.world.npcs[target_id].name
        if item_id:
            item = state.world.items.get(item_id)
            topic = item.name.lower() if item is not None else item_id.replace("_", " ")
        if target_name or topic:
            break
    if not topic and intent == "ask_about":
        topic = "the current lead"
    return infer_turn_focus(
        progress=state.progress,
        tension=state.tension,
        goal=state.active_goal,
        intent=intent,
        target_name=target_name,
        topic=topic,
    )


def turn_focus_from_freeform(state, action_proposal: dict[str, Any]) -> dict[str, str]:  # noqa: ANN401
    intent = str(action_proposal.get("intent", "")).strip()
    targets = tuple(str(target).strip() for target in action_proposal.get("targets", ()))
    target_name = ""
    if targets and targets[0] in state.world.npcs:
        target_name = state.world.npcs[targets[0]].name
    arguments = dict(action_proposal.get("arguments", {}))
    topic = str(arguments.get("topic", "")).strip()
    return infer_turn_focus(
        progress=state.progress,
        tension=state.tension,
        goal=state.active_goal,
        intent=intent,
        target_name=target_name,
        topic=topic,
    )
