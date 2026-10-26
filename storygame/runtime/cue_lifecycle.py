"""Story-agnostic checks for staged discovery display."""

from collections.abc import Collection
from typing import Protocol

from storygame.runtime.reveal_eligibility import NOT_REACHABLE, PREREQUISITE_MISSING, explain_reveal


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
    costs: Collection[object]


def staged_cue_reveal_is_reachable(state: _FactState, delivery: _Delivery) -> bool:
    """Return whether an earning reveal is reachable from the protagonist's place."""

    package = getattr(state, "package", None)
    knowledge_catalog = getattr(package, "knowledge", None)
    knowledge_items = getattr(knowledge_catalog, "knowledge", ())
    cost_fact_ids = {cost.fact_id for cost in delivery.costs if cost.op == "assert"}
    reveal_fact_ids = cost_fact_ids or {delivery.fact_id}
    reveals = tuple(
        knowledge
        for knowledge in knowledge_items
        if state.current_scene_id in knowledge.available_in_scenes
        and any(effect.op == "assert" and effect.fact_id in reveal_fact_ids for effect in knowledge.establishes)
    )
    ready_reveals = tuple(
        knowledge for knowledge in reveals if explain_reveal(state, "player", knowledge).reason != PREREQUISITE_MISSING
    )
    return not ready_reveals or any(
        explain_reveal(state, "player", knowledge).reason != NOT_REACHABLE for knowledge in ready_reveals
    )


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
