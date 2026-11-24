"""Contracts for declared pacing-event knowledge links."""

from __future__ import annotations

from pathlib import Path

import pytest
from pydantic import ValidationError

from storygame.story_package.default_root import default_package_root
from storygame.story_package.loader import load_story_package
from storygame.story_package.models import FactPredicate, PacingEvent
from storygame.story_package.pacing_links import pacing_link_problems
from storygame.story_source import check_source_tree
from storygame.story_source.c_scene import build_events
from storygame.story_source.convert_scene import convert_scenes
from tests.story_source.helpers import copy_fixture, patch_source

PACKAGE = load_story_package(default_package_root())


def _event(event_id: str = "event") -> PacingEvent:
    return PacingEvent(
        id=event_id,
        scene_id="1A",
        at_turn=1,
        effects=(FactPredicate(fact_id="pressure_fact", equals=True),),
    )


def _with_events(package: object, events: tuple[PacingEvent, ...]) -> object:
    return package.model_copy(update={"pacing": package.pacing.model_copy(update={"events": events})})


def _facts(item: object) -> set[str]:
    return {predicate.fact_id for predicate in item.requires} | {operation.fact_id for operation in item.establishes}


def _pressure_items(package: object) -> tuple[object, ...]:
    return tuple(
        item
        for item in package.knowledge.knowledge
        if item.earn_when is None and not item.action_evidence and item.source.kind != "scene_entry"
    )


def _fully_declared(package: object) -> object:
    pressure = _pressure_items(package)
    events = tuple(
        event.model_copy(
            update={
                "delivers": tuple(
                    item.id
                    for item in pressure
                    if event.scene_id in item.available_in_scenes
                    and _facts(item) & {effect.fact_id for effect in event.effects}
                )
            }
        )
        for event in package.pacing.events
    )
    return _with_events(package, events)


def test_pacing_event_delivers_is_optional_round_trippable_and_unique() -> None:
    without = _event().model_dump()
    assert "delivers" not in without
    with_delivers = _event().model_copy(update={"delivers": ("k_x",)})
    assert PacingEvent.model_validate(with_delivers.model_dump()) == with_delivers
    with pytest.raises(ValidationError, match="delivers"):
        PacingEvent(**_event().model_dump(), delivers=("k_x", "k_x"))


@pytest.mark.parametrize("value", ["k_x", [1], [""]])
def test_l1_delivers_requires_non_empty_string_list(tmp_path: Path, value: object) -> None:
    root = copy_fixture("mini_ok", tmp_path)
    patch_source(root, "scenes/1A.yaml", "beats[kristin_steadies_1a].delivers", value)
    diagnostics = check_source_tree(root)
    assert any(diagnostic.name == "L1.type" and diagnostic.field == "delivers" for diagnostic in diagnostics)


def test_l1_delivers_accepts_string_list(tmp_path: Path) -> None:
    root = copy_fixture("mini_ok", tmp_path)
    patch_source(root, "scenes/1A.yaml", "beats[kristin_steadies_1a].delivers", ["k_x"])
    assert check_source_tree(root) == []


def test_scene_compiles_delivers() -> None:
    events = build_events(
        {
            "scene": "1A",
            "turns": {"min": 1, "nudge": 2, "handoff": 3},
            "pressure": "pressure",
            "beats": [{"id": "event", "at_turn": 1, "sets": {"fact": True}, "delivers": ["k_x"]}],
        }
    )
    assert events[0].delivers == ("k_x",)


def test_converter_round_trips_delivers() -> None:
    event = next(event for event in PACKAGE.pacing.events if event.realizations)
    changed = event.model_copy(update={"delivers": ("k_x",)})
    package = _with_events(PACKAGE, tuple(changed if item.id == event.id else item for item in PACKAGE.pacing.events))
    record = next(
        item for item in convert_scenes(package).scene_docs[event.scene_id]["beats"] if item["id"] == event.id
    )
    assert record["delivers"] == ["k_x"]


def test_real_package_has_exactly_eleven_unlinked_pressure_items() -> None:
    problems = pacing_link_problems(PACKAGE)
    assert problems
    assert all("unlinked pacing-linked item" in problem for problem in problems)
    expected = {"k_supervisor_escorting", "k_inspection_window_missed", "k_purge_window_missed"}
    named = {problem.split("item '", 1)[1].split("'", 1)[0] for problem in problems}
    assert len(named) == 11
    assert expected <= named


def test_declaring_all_linkable_pressure_items_clears_package() -> None:
    assert pacing_link_problems(_fully_declared(PACKAGE)) == []


def test_each_declared_link_problem_kind_names_event_and_item() -> None:
    pressure = _pressure_items(PACKAGE)
    event = PACKAGE.pacing.events[0]
    missing = next(item for item in pressure if event.scene_id not in item.available_in_scenes)
    no_fact, no_fact_event = next(
        (item, candidate)
        for candidate in PACKAGE.pacing.events
        for item in pressure
        if item.available_in_scenes == (candidate.scene_id,)
        and not (_facts(item) & {effect.fact_id for effect in candidate.effects})
    )
    entry = next(item for item in PACKAGE.knowledge.knowledge if item.source.kind == "scene_entry")
    cases = (
        ("declares unknown knowledge item", "k_missing", event),
        ("is not a pressure item", entry.id, event),
        ("is not available in event scene", missing.id, event),
        ("shares no fact", no_fact.id, no_fact_event),
    )
    for marker, item_id, chosen_event in cases:
        package = _with_events(PACKAGE, (chosen_event.model_copy(update={"delivers": (item_id,)}),))
        problems = pacing_link_problems(package)
        assert any(marker in problem and chosen_event.id in problem and item_id in problem for problem in problems)


def test_validator_does_not_mutate_and_is_deterministic() -> None:
    before = PACKAGE.model_dump()
    first = pacing_link_problems(PACKAGE)
    second = pacing_link_problems(PACKAGE)
    assert first == second == sorted(first)
    assert PACKAGE.model_dump() == before
