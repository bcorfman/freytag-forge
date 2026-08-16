"""Fact-backed, package-declared environmental complications."""

from __future__ import annotations

from typing import Any

_CONSEQUENCE_CLASSES = frozenset({"pressure", "setback", "cost", "opportunity"})


def validate_environment_transitions(
    transitions: object, room_ids: set[str], paths: list[dict[str, Any]], item_ids: set[str]
) -> list[dict[str, Any]]:
    """Validate generic, bounded environmental complication declarations."""
    if not isinstance(transitions, list) or not transitions:
        raise ValueError("environment transitions require at least one declaration")
    route_ids_by_room: dict[str, set[str]] = {}
    for path in paths:
        room_id = str(path.get("from", ""))
        route_id = str(path.get("id", path.get("direction", ""))).strip()
        route_ids_by_room.setdefault(room_id, set()).add(route_id)
    normalized: list[dict[str, Any]] = []
    ids: set[str] = set()
    for raw in transitions:
        if not isinstance(raw, dict):
            raise ValueError("environment transition must be a mapping")
        transition_id = str(raw.get("id", "")).strip()
        room_id = str(raw.get("room_id", "")).strip()
        from_state = str(raw.get("from_state", "")).strip()
        to_state = str(raw.get("to_state", "")).strip()
        consequence_class = str(raw.get("consequence_class", "")).strip()
        blocked = [str(route_id).strip() for route_id in raw.get("blocked_route_ids", [])]
        recoveries = raw.get("evidence_routes", [])
        if not transition_id or transition_id in ids or not room_id or not from_state or not to_state:
            raise ValueError("environment transition requires unique id, room_id, from_state, and to_state")
        if room_id not in room_ids or from_state == to_state or consequence_class not in _CONSEQUENCE_CLASSES:
            raise ValueError("environment transition has an invalid room, state, or consequence class")
        if len(blocked) != len(set(blocked)) or not set(blocked) <= route_ids_by_room.get(room_id, set()):
            raise ValueError("environment transition references an unknown route")
        if not isinstance(recoveries, list):
            raise ValueError("environment transition evidence routes must be a list")
        normalized_recoveries: list[dict[str, str]] = []
        for recovery in recoveries:
            if not isinstance(recovery, dict):
                raise ValueError("environment recovery must be a mapping")
            evidence_id = str(recovery.get("evidence_id", "")).strip()
            route_id = str(recovery.get("route_id", "")).strip()
            if evidence_id not in item_ids or route_id not in blocked:
                raise ValueError("environment recovery references unknown evidence or route")
            normalized_recoveries.append({"evidence_id": evidence_id, "route_id": route_id})
        exits = route_ids_by_room.get(room_id, set())
        if exits and set(blocked) == exits and not normalized_recoveries:
            raise ValueError("environment complication must leave a viable route or evidence recovery")
        ids.add(transition_id)
        normalized.append(
            {
                "id": transition_id,
                "room_id": room_id,
                "from_state": from_state,
                "to_state": to_state,
                "consequence_class": consequence_class,
                "blocked_route_ids": blocked,
                "evidence_routes": normalized_recoveries,
            }
        )
    return normalized


def apply_environment_transition(state: Any, transition_id: str) -> tuple[dict[str, Any], ...]:
    """Stage declared facts for one currently legal environmental transition."""
    transition = next(iter(state.world_facts.query("environment_transition", transition_id, None, None, None)), None)
    if transition is None:
        raise ValueError(f"Unknown environment transition '{transition_id}'.")
    _, _, room_id, from_state, to_state = transition
    if not state.world_facts.holds("environment", room_id, from_state):
        raise ValueError(f"Environment transition '{transition_id}' is not currently available.")
    consequence = next(iter(state.world_facts.query("environment_consequence", transition_id, None)), None)
    if consequence is None:
        raise ValueError(f"Environment transition '{transition_id}' has no bounded consequence.")
    ops: list[dict[str, Any]] = [
        {"op": "retract", "fact": ("environment", room_id, from_state)},
        {"op": "assert", "fact": ("environment", room_id, to_state)},
        {"op": "assert", "fact": ("dramatic_consequence", transition_id, consequence[2])},
    ]
    ops.extend(
        {"op": "assert", "fact": ("route_blocked", room_id, fact[2], transition_id)}
        for fact in state.world_facts.query("transition_blocks_route", transition_id, None)
    )
    return tuple(ops)


def resolve_environment_complication(state: Any, transition_id: str, evidence_id: str) -> tuple[dict[str, Any], ...]:
    """Use held, package-declared evidence to remove only its declared route block."""
    recoveries = state.world_facts.query("environment_recovery", transition_id, evidence_id, None)
    if not recoveries or not state.world_facts.holds("holding", "player", evidence_id):
        raise ValueError("Environment complication recovery requires declared held evidence.")
    ops = [{"op": "retract", "fact": ("route_blocked", fact[3], transition_id)} for fact in recoveries]
    blocked = state.world_facts.query("route_blocked", None, None, transition_id)
    if len(blocked) == len(ops):
        consequence = next(iter(state.world_facts.query("dramatic_consequence", transition_id, None)), None)
        if consequence is not None:
            ops.append({"op": "retract", "fact": consequence})
    return tuple(ops)
