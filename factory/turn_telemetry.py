"""Build complete, story-agnostic turn telemetry from engine observations.

The engine does not currently record an NPC-move or recovery signal.  Their
values here are therefore contract defaults, not measurements: ``npc_move``
is always false and recovery is omitted.
"""

from __future__ import annotations

from typing import Any


def pacing_effects_by_event(package: Any) -> dict[str, list[str]]:
    """Return each package pacing event's fact effects in deterministic order."""
    return {event.id: sorted(effect.fact_id for effect in event.effects) for event in package.pacing.events}


def build_turn_telemetry(
    *,
    turn: int,
    player_input: str,
    text: str,
    bundle: dict,
    grounding_ids: list[str],
    replay_fired_ids,
    null_grounding_ids,
    fired_before,
    fired_after,
    pacing_effects: dict[str, list[str]],
    delivered_before=frozenset(),
) -> dict:
    """Build one outcome-contract turn and its grounding provenance map."""
    outcome = bundle["outcome"]
    committed = list(bundle["committed_delta"]["fact_predicates"])
    newly_fired = set(fired_after) - set(fired_before)
    pacing_facts = {fact_id for event_id in newly_fired for fact_id in pacing_effects.get(event_id, [])}
    committed_facts = [fact_id for fact_id in committed if fact_id not in pacing_facts]

    reveal_selection = bundle.get("reveal_selection")
    if isinstance(reveal_selection, dict):
        shortlist_ids = [item for item in reveal_selection.get("shortlist_ids", []) if isinstance(item, str)]
        matched_candidate = reveal_selection.get("matched")
        if not isinstance(matched_candidate, str):
            matched_candidate = None
    else:
        shortlist_ids = []
        matched_candidate = None
    candidates_offered = list(dict.fromkeys(shortlist_ids))
    if matched_candidate is not None and matched_candidate not in candidates_offered:
        candidates_offered.append(matched_candidate)

    null_ids = list(null_grounding_ids)
    delivered = set(delivered_before)
    null_set = set(null_ids)
    grounding_source = {
        grounding_id: (
            "command_match"
            if grounding_id == matched_candidate
            else "pacing"
            if grounding_id in null_set
            else "re_grounded"
            if grounding_id in delivered
            else "narrator_selection"
        )
        for grounding_id in grounding_ids
    }
    return {
        "turn": turn,
        "input": player_input,
        "text": text,
        "outcome": outcome,
        "rejected": outcome == "rejected",
        "game_break": {"outcome": "game_break"} if outcome == "game_break" else None,
        "story_complete": bundle["story_complete"],
        "grounding_ids": list(grounding_ids),
        "null_grounding_ids": null_ids,
        "committed_facts": committed_facts,
        "candidates_offered": candidates_offered,
        "matched_candidate": matched_candidate,
        "transition_cause": bundle["transition_cause"],
        "pressure_event": bool(newly_fired),
        "npc_move": False,
        "ending_latched": bundle["story_complete"],
        "grounding_source": grounding_source,
    }
