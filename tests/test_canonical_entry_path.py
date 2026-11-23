from __future__ import annotations

import copy
from pathlib import Path
from types import SimpleNamespace

import pytest

from storygame.personas import _select_canonical
from storygame.runtime.entry_seed import advance_state_to_scene, canonical_path_report
from storygame.runtime.state import RuntimeState
from storygame.story_package.loader import load_story_package

PACKAGE = load_story_package(Path("data/stories/continuity-initiative"))
SCENE_IDS = tuple(scene.metadata.scene_id for scene in PACKAGE.scenes)


def _entry_states(persona: str) -> list[RuntimeState]:
    state = RuntimeState.bootstrap(PACKAGE)
    entries = [copy.deepcopy(state)]
    for scene_id in SCENE_IDS[1:]:
        advance_state_to_scene(PACKAGE, state, scene_id, persona=persona)
        entries.append(copy.deepcopy(state))
    return entries


def _fact_tuples(state: RuntimeState) -> tuple[tuple[str, str, str | None, str | None], ...]:
    return tuple(sorted(fact.key for fact in state.facts.asserted))


def _true_story_facts(state: RuntimeState) -> set[str]:
    return {
        fact.predicate
        for fact in state.facts.asserted
        if fact.predicate[:3] != "wk_" and str(fact.value).lower() == "true"
    }


def test_canonical_path_reaches_every_scene_in_order() -> None:
    entries = _entry_states("canonical")

    assert [state.current_scene_id for state in entries] == list(SCENE_IDS)


def test_canonical_path_is_deterministic_at_every_scene_entry() -> None:
    first = _entry_states("canonical")
    second = _entry_states("canonical")

    assert [_fact_tuples(state) for state in first] == [_fact_tuples(state) for state in second]


def test_canonical_entry_facts_are_a_strict_subset_of_thorough() -> None:
    canonical = _entry_states("canonical")
    thorough = _entry_states("thorough")
    canonical_facts = [_true_story_facts(state) for state in canonical]
    thorough_facts = [_true_story_facts(state) for state in thorough]

    assert all(left <= right for left, right in zip(canonical_facts, thorough_facts, strict=True))
    assert any(left < right for left, right in zip(canonical_facts, thorough_facts, strict=True))


def test_canonical_path_report_has_one_shape_correct_row_per_hop() -> None:
    report = canonical_path_report(PACKAGE)
    required_keys = {"from_scene", "to_scene", "turns", "earned", "transition_cause", "storylets_delivered"}

    assert len(report) == len(SCENE_IDS) - 1
    assert all(required_keys <= set(row) for row in report)
    assert [row["from_scene"] for row in report] == list(SCENE_IDS[:-1])
    assert [row["to_scene"] for row in report] == list(SCENE_IDS[1:])
    assert all(isinstance(row["turns"], int) and row["turns"] >= 0 for row in report)
    assert all(isinstance(row["earned"], bool) for row in report)
    assert all(isinstance(row["storylets_delivered"], list) for row in report)


def test_canonical_path_report_records_an_unreached_hop(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("storygame.personas._turn_cap", lambda _package: 0)

    report = canonical_path_report(PACKAGE)

    assert report[0]["reached"] is False
    assert report[0]["from_scene"] == SCENE_IDS[0]
    assert report[0]["to_scene"] == SCENE_IDS[1]


def test_entry_seed_rejects_unknown_persona() -> None:
    state = RuntimeState.bootstrap(PACKAGE)

    with pytest.raises(ValueError, match="unknown entry persona"):
        advance_state_to_scene(PACKAGE, state, SCENE_IDS[1], persona="unknown")


def test_default_entry_seed_matches_explicit_thorough() -> None:
    default_state = RuntimeState.bootstrap(PACKAGE)
    thorough_state = RuntimeState.bootstrap(PACKAGE)

    advance_state_to_scene(PACKAGE, default_state, SCENE_IDS[1])
    advance_state_to_scene(PACKAGE, thorough_state, SCENE_IDS[1], persona="thorough")

    assert _fact_tuples(default_state) == _fact_tuples(thorough_state)


def test_canonical_selector_is_story_agnostic_for_a_synthetic_package() -> None:
    def storylet(storylet_id: str):
        return SimpleNamespace(
            id=storylet_id,
            scene_id="1A",
            latest_turn=3,
            activation_conditions=(),
            realizations=(SimpleNamespace(operations=()),),
        )

    required = storylet("route-required")
    optional = storylet("optional")
    routes = SimpleNamespace(
        storylets=(required, optional),
        bridge_events=(),
        resolution_events=(SimpleNamespace(realization_storylets=(required.id,)),),
    )
    package = SimpleNamespace(
        storylet_routes=routes,
        knowledge_indexes=SimpleNamespace(
            by_id={
                "required-knowledge": SimpleNamespace(
                    source=SimpleNamespace(storylet_id=required.id), establishes=(), requires=()
                ),
                "optional-knowledge": SimpleNamespace(
                    source=SimpleNamespace(storylet_id=optional.id), establishes=(), requires=()
                ),
            }
        ),
    )
    state = SimpleNamespace(
        facts=SimpleNamespace(asserted=()),
        fired_event_ids=set(),
        current_scene_id="1A",
        turn_index=0,
        scene_entered_at_turn=0,
    )
    candidates = (SimpleNamespace(id="optional-knowledge"), SimpleNamespace(id="required-knowledge"))

    assert _select_canonical(package, state, candidates) == "required-knowledge"
    assert _select_canonical(package, state, candidates[:1]) is None
