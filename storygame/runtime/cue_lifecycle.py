"""Story-agnostic checks for staged discovery display."""

from collections.abc import Collection
from typing import Protocol


class _FactState(Protocol):
    current_scene_id: str
    staged_cue_fact_id: str | None
    staged_cue_stage: int
    delivered_cue_ids: Collection[str]
    cue_stages: Collection[object]
    facts: object


class _Delivery(Protocol):
    fact_id: str
    scene_id: str


def staged_cue_is_eligible(
    state: _FactState,
    delivery: _Delivery,
    *,
    final_scene_id: str | None = None,
    final_facts: object | None = None,
    reveal_available: bool = True,
    check_stage: bool = True,
) -> bool:
    """Return whether a staged cue can still be displayed for this turn."""

    facts = final_facts if final_facts is not None else state.facts
    if delivery.scene_id != (final_scene_id or state.current_scene_id):
        return False
    if any(fact.predicate == delivery.fact_id and str(fact.value).lower() == "true" for fact in facts.asserted):
        return False
    if not reveal_available:
        return False
    if check_stage:
        stage = next((item for item in state.cue_stages if item.fact_id == delivery.fact_id), None)
        if stage is not None and stage.stage >= 2 and delivery.fact_id in state.delivered_cue_ids:
            return False
        if state.staged_cue_stage == 1 and delivery.fact_id in state.delivered_cue_ids:
            return False
    return True


def clear_staged_cue(state: _FactState) -> None:
    """Clear a rejected staged cue so it cannot be replayed."""

    state.staged_cue_fact_id = None
    state.staged_cue_stage = 1
