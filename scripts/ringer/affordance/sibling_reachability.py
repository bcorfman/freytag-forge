"""Report whether spent sibling reveals leave facts without another source."""

from __future__ import annotations

import sys
from collections import defaultdict
from pathlib import Path
from typing import Any

from storygame.runtime.facts import Fact, FactStore
from storygame.runtime.reveal_eligibility import explain_reveal
from storygame.runtime.state import RuntimeState
from storygame.runtime.validation import predicate_matches
from storygame.story_package.loader import load_story_package


def _storylets(package: Any) -> tuple[Any, ...]:
    routes = getattr(package, "storylet_routes", None)
    if routes is not None and hasattr(routes, "storylets"):
        return tuple(routes.storylets)
    return tuple(getattr(package, "storylets", ()))


def _knowledge(package: Any) -> tuple[Any, ...]:
    catalog = getattr(package, "knowledge", None)
    return tuple(getattr(catalog, "knowledge", ()))


def _state(package: Any, scene_id: str, active_event_ids: set[str] = ()) -> RuntimeState:
    state = RuntimeState.model_construct(
        package=package,
        current_scene_id=scene_id,
        phase="exposition",
        active_event_ids=set(active_event_ids),
        fired_event_ids=set(),
        facts=FactStore(),
        turn_index=0,
        scene_entered_at_turn=0,
        turn_records=[],
        delivered_cue_ids=(),
        staged_handoff_fact_ids=(),
    )
    state._assert_scene_entry_fact(scene_id)
    return state


def _apply_reveal(state: RuntimeState, item: Any) -> None:
    for effect in item.establishes:
        fact = Fact(predicate=effect.fact_id, subject="story", value=str(effect.value).lower())
        if effect.op == "assert":
            state.facts.assert_fact(fact)
        else:
            state.facts.retract_fact(fact)
    storylet_id = item.source.storylet_id
    if storylet_id is not None:
        state.active_event_ids.discard(storylet_id)
        state.fired_event_ids.add(storylet_id)


def _route_map(package: Any) -> dict[str, Any]:
    return {storylet.id: storylet for storylet in _storylets(package)}


def _activate_unfired_storylets(state: RuntimeState, package: Any, scene_id: str) -> None:
    for storylet in _storylets(package):
        if storylet.scene_id != scene_id or storylet.id in state.fired_event_ids:
            continue
        if all(predicate_matches(predicate, state.facts) for predicate in storylet.activation_conditions):
            state.active_event_ids.add(storylet.id)


def _effect_is_established(state: RuntimeState, effect: Any) -> bool:
    expected = str(effect.value).lower()
    matched = any(
        (fact.value if fact.value is not None else fact.object) == expected
        for fact in state.facts.matching(effect.fact_id)
    )
    return matched if effect.op == "assert" else not matched


def _obtainable_facts(state: RuntimeState, items: tuple[Any, ...], sibling: Any) -> tuple[bool, tuple[str, ...]]:
    missing: list[str] = []
    for effect in sibling.establishes:
        if _effect_is_established(state, effect):
            continue
        if any(
            item.id != sibling.id
            and state.current_scene_id in item.available_in_scenes
            and explain_reveal(state, "player", item).eligible
            and any(
                other_effect.fact_id == effect.fact_id and other_effect.op == effect.op
                for other_effect in item.establishes
            )
            for item in items
        ):
            continue
        if effect.fact_id not in missing:
            missing.append(effect.fact_id)
    return not missing, tuple(sorted(missing))


def report(package: Any) -> str:
    """Return the sibling reachability report for a loaded story package."""

    route_map = _route_map(package)
    by_source: dict[str, list[Any]] = defaultdict(list)
    for item in _knowledge(package):
        if item.source.storylet_id is not None:
            by_source[item.source.storylet_id].append(item)

    rows = ["storylet | fired reveal | now-ineligible sibling | reason | facts still obtainable | missing fact ids"]
    for storylet_id in sorted(by_source):
        siblings = tuple(sorted(by_source[storylet_id], key=lambda item: item.id))
        if len(siblings) < 2:
            continue
        storylet = route_map.get(storylet_id)
        if storylet is None:
            continue
        for fired in siblings:
            state = _state(package, storylet.scene_id, {storylet_id})
            _apply_reveal(state, fired)
            _activate_unfired_storylets(state, package, storylet.scene_id)
            for sibling in siblings:
                if sibling.id == fired.id:
                    continue
                eligibility = explain_reveal(state, "player", sibling)
                obtainable, missing = _obtainable_facts(state, _knowledge(package), sibling)
                rows.append(
                    " | ".join(
                        (
                            storylet_id,
                            fired.id,
                            sibling.id,
                            eligibility.reason,
                            "yes" if obtainable else "no",
                            ",".join(missing) or "-",
                        )
                    )
                )
    return "\n".join(rows)


def main(argv: list[str] | None = None) -> int:
    args = sys.argv[1:] if argv is None else argv
    package_dir = Path(args[0]) if args else Path("data/stories/continuity-initiative")
    print(report(load_story_package(package_dir)))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
