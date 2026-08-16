"""Local validation of material narration claims against candidate facts."""

from __future__ import annotations

from typing import Any

_RELATIONS = frozenset({"custody", "environment", "access", "event"})


def validate_staging_claims(state, claims: tuple[dict[str, Any], ...]) -> None:
    """Reject claims that are malformed, contradictory, or outside the scene."""
    seen: set[tuple[str, str, str]] = set()
    for claim in claims:
        relation = str(claim["relation"])
        subject_id = str(claim["subject_id"])
        target_id = str(claim["target_id"])
        location_id = str(claim["location_id"])
        state_id = str(claim["state_id"])
        key = (relation, subject_id, location_id)
        if relation not in _RELATIONS:
            raise ValueError(f"STAGING_CLAIM_UNKNOWN_RELATION:{relation}")
        if key in seen:
            raise ValueError(f"STAGING_CLAIM_DUPLICATE:{relation}:{subject_id}")
        seen.add(key)
        if not _claim_is_visible(state, relation, subject_id, target_id, location_id):
            raise ValueError(f"STAGING_CLAIM_NOT_VISIBLE:{relation}:{subject_id}")
        if not _claim_holds(state, relation, subject_id, target_id, location_id, state_id):
            raise ValueError(f"STAGING_CLAIM_CONTRADICTS_FACTS:{relation}:{subject_id}")


def _claim_is_visible(state, relation: str, subject_id: str, target_id: str, location_id: str) -> bool:
    player_locations = {fact[2] for fact in state.world_facts.query("at") if fact[1] == "player"}
    if relation == "environment":
        return location_id in player_locations
    if relation == "access":
        return location_id in player_locations
    if relation == "event":
        return location_id in player_locations
    if ("room_item", next(iter(player_locations), ""), subject_id) in state.world_facts.all():
        return True
    if ("holding", "player", subject_id) in state.world_facts.all():
        return True
    return any(
        fact[0] == "holding"
        and fact[2] == subject_id
        and ("npc_at", fact[1], next(iter(player_locations), "")) in state.world_facts.all()
        for fact in state.world_facts.all()
    )


def _claim_holds(state, relation: str, subject_id: str, target_id: str, location_id: str, state_id: str) -> bool:
    facts = state.world_facts.all()
    if relation == "custody":
        return ("holding", target_id, subject_id) in facts or ("room_item", location_id, subject_id) in facts
    if relation == "environment":
        return ("environment", location_id, state_id) in facts or ("room_exposure", location_id, state_id) in facts
    if relation == "access":
        if state_id == "blocked":
            return ("locked", subject_id, location_id, target_id) in facts
        if state_id == "available":
            return any(fact[0] == "path" and fact[1] == subject_id and location_id in fact[2:] for fact in facts)
        return False
    return ("event", subject_id, location_id) in facts
