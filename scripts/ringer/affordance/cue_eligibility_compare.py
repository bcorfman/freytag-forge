"""Compare cue staging with player reveal eligibility.

This is an audit only.  It calls the runtime cue predicate without changing
the engine or any package data.
"""

from __future__ import annotations

import sys
from collections import Counter
from collections.abc import Iterable
from pathlib import Path
from types import SimpleNamespace
from typing import Any

from scripts.ringer.affordance.sibling_reachability import (
    _activate_unfired_storylets,
    _apply_reveal,
    _seed_reveal_state,
    _state,
    _storylets,
)
from storygame.runtime.engine import RuntimeEngine
from storygame.runtime.reveal_eligibility import explain_reveal
from storygame.story_package.loader import load_story_package

SPENT = "storylet_spent"
ESTABLISHED = "already_established"
INACTIVE = "source_inactive"
HIDDEN = "not_visible"

AGREE = "AGREE"
SPENT_CLASS = "CUE_SHOWN_BUT_SPENT"
EARNED_CLASS = "CUE_SHOWN_BUT_EARNED"
INACTIVE_CLASS = "CUE_SHOWN_BUT_INACTIVE"
HIDDEN_CLASS = "CUE_SHOWN_BUT_HIDDEN"
OTHER = "OTHER"


def _cue_available(state: Any, fact_id: str) -> bool:
    """Call the real RuntimeEngine method against this audit state."""

    return RuntimeEngine._cue_reveal_available(SimpleNamespace(state=state), fact_id)


def _cue_fact_ids(delivery: Any) -> frozenset[str]:
    return frozenset((delivery.fact_id,) + tuple(cost.fact_id for cost in delivery.costs if cost.op == "assert"))


def _matching_reveals(package: Any, scene_id: str, delivery: Any) -> tuple[Any, ...]:
    fact_ids = _cue_fact_ids(delivery)
    return tuple(
        item
        for item in package.knowledge.knowledge
        if item.audience.kind != "world_only"
        and scene_id in item.available_in_scenes
        and any(effect.op == "assert" and effect.fact_id in fact_ids for effect in item.establishes)
    )


def _scene_states(package: Any, scene_id: str) -> Iterable[tuple[str, Any]]:
    """Yield the requested entry state and one state per storylet reveal."""

    entry = _state(package, scene_id)
    _activate_unfired_storylets(entry, package, scene_id)
    yield "S0", entry

    scene_storylets = sorted(
        (storylet for storylet in _storylets(package) if storylet.scene_id == scene_id),
        key=lambda storylet: storylet.id,
    )
    for storylet in scene_storylets:
        reveals = sorted(
            (
                item
                for item in package.knowledge.knowledge
                if item.source.storylet_id == storylet.id
                and scene_id in item.available_in_scenes
                and item.audience.kind != "world_only"
            ),
            key=lambda item: item.id,
        )
        for item in reveals:
            state = _state(package, scene_id)
            _seed_reveal_state(state, storylet, item)
            _apply_reveal(state, item)
            _activate_unfired_storylets(state, package, scene_id)
            yield f"{storylet.id} fired through {item.id}", state


def _classify(
    cue_available: bool,
    explanations: tuple[tuple[Any, str], ...],
    state: Any,
) -> str:
    player_available = not explanations or any(reason == "eligible" for _, reason in explanations)
    if cue_available == player_available:
        return AGREE
    if not cue_available:
        return OTHER

    reasons = {reason for _, reason in explanations}
    fired_sources = {item.source.storylet_id for item, _ in explanations if item.source.storylet_id is not None}
    if explanations and reasons <= {SPENT, ESTABLISHED} and fired_sources & set(state.fired_event_ids):
        return SPENT_CLASS
    if explanations and reasons == {ESTABLISHED}:
        return EARNED_CLASS
    if explanations and reasons == {INACTIVE}:
        return INACTIVE_CLASS
    if explanations and reasons == {HIDDEN}:
        return HIDDEN_CLASS
    return OTHER


def _row(package: Any, scene_id: str, state_label: str, state: Any, delivery: Any) -> tuple[str, str]:
    matching = _matching_reveals(package, scene_id, delivery)
    explanations = tuple((item, explain_reveal(state, "player", item).reason) for item in matching)
    cue_available = _cue_available(state, delivery.fact_id)
    player_available = not explanations or any(reason == "eligible" for _, reason in explanations)
    classification = _classify(cue_available, explanations, state)
    reasons = ",".join(f"{item.id}:{reason}" for item, reason in explanations) or "-"
    row = " | ".join(
        (
            scene_id,
            state_label,
            delivery.fact_id,
            "True" if cue_available else "False",
            "True" if player_available else "False",
            reasons,
            classification,
        )
    )
    return row, classification


def report(package: Any) -> str:
    """Return the cue-vs-eligibility report for a loaded story package."""

    rows: list[str] = []
    counts: Counter[str] = Counter()
    spent_rows: list[str] = []
    deliveries_by_scene: dict[str, tuple[Any, ...]] = {}
    for scene in package.scenes:
        scene_id = scene.metadata.scene_id
        deliveries_by_scene[scene_id] = tuple(
            sorted(
                (delivery for delivery in package.deliveries if delivery.scene_id == scene_id and delivery.cue_text),
                key=lambda delivery: delivery.fact_id,
            )
        )

    for scene in package.scenes:
        scene_id = scene.metadata.scene_id
        deliveries = deliveries_by_scene[scene_id]
        if not deliveries:
            continue
        for state_label, state in _scene_states(package, scene_id):
            for delivery in deliveries:
                row, classification = _row(package, scene_id, state_label, state, delivery)
                rows.append(row)
                counts[classification] += 1
                if classification == SPENT_CLASS:
                    spent_rows.append(f"- scene {scene_id}; state '{state_label}'; cue fact {delivery.fact_id}")

    lines = [
        "Cue eligibility comparison",
        "WARNING: CUE_SHOWN_BUT_INACTIVE is risky to suppress; the source storylet may simply not be active yet.",
        (
            "LIMIT: This report covers only S0 scene entry and one-reveal "
            "storylet-fired states listed here. It is not exhaustive."
        ),
        "",
        "scene | state | cue fact | _cue_reveal_available | player reveal available | reveal reasons | classification",
        *rows,
        "",
        "Counts per classification",
    ]
    for classification in (AGREE, SPENT_CLASS, EARNED_CLASS, INACTIVE_CLASS, HIDDEN_CLASS, OTHER):
        lines.append(f"{classification}: {counts[classification]}")
    lines.extend(("", "CUE_SHOWN_BUT_SPENT invitations"))
    lines.extend(spent_rows or ["- none"])
    lines.extend(
        (
            "",
            (
                "Known case: scene 1A, state 'SL-1A-B fired through "
                "k_sl_1a_b_r1', cue fact continuity_initiative_known, "
                "expected CUE_SHOWN_BUT_SPENT."
            ),
        )
    )
    known = "1A | SL-1A-B fired through k_sl_1a_b_r1 | continuity_initiative_known | "
    known_observed = any(row.startswith(known) and row.endswith(SPENT_CLASS) for row in rows)
    lines.append("Known case observed: " + ("yes" if known_observed else "NO"))
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    args = sys.argv[1:] if argv is None else argv
    package_dir = Path(args[0]) if args else Path("data/stories/continuity-initiative")
    print(report(load_story_package(package_dir)))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
