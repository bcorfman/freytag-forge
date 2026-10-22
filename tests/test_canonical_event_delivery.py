from __future__ import annotations

import shutil
from pathlib import Path

import pytest

from storygame.runtime.engine import RuntimeEngine
from storygame.runtime.facts import Fact
from storygame.runtime.state import RuntimeState
from storygame.story_package.loader import StoryPackageError, load_story_package

ROOT = Path(__file__).resolve().parents[1]
PACKAGE_ROOT = ROOT / "data/stories/continuity-initiative"
DELIVERY_TEXT = (
    "The captives have emerged into Los Angeles. News drones, civilians, and local responders begin arriving. "
    "Brandon’s voice comes through the emergency speakers. “Reports from other detention sites are reaching the "
    "broadcast chamber. Families of the missing are calling there for news.” Then his voice falls silent. Your "
    "barrier holds the way from the maintenance network to Rebecca's executive office open for now. The broadcast "
    "chamber remains reachable while the barrier holds."
)
ENTRY_FACTS = ("broadcast_started", "brandon_confession_available", "detention_locations_secured")


def _package():
    return load_story_package(PACKAGE_ROOT)


def _state(package, *, facts: tuple[str, ...], fired: tuple[str, ...]) -> RuntimeState:
    state = RuntimeState(package=package, current_scene_id="3C", phase="resolution")
    state._assert_scene_entry_fact("3C")
    for fact_id in (*ENTRY_FACTS, *facts):
        state.facts.assert_fact(Fact(predicate=fact_id, subject="story", value="true"))
    state.fired_event_ids.update(fired)
    return state


def _engine(state: RuntimeState) -> RuntimeEngine:
    return RuntimeEngine(
        state,
        lambda _command: {"segments": [{"kind": "narration", "text": "The broadcast continues."}]},
    )


def _with_delivery(package, event_id: str, text: str):
    routes = package.storylet_routes
    events = tuple(
        event.model_copy(update={"delivery_text": text}) if event.id == event_id else event
        for event in routes.resolution_events
    )
    return package.model_copy(update={"storylet_routes": routes.model_copy(update={"resolution_events": events})})


def test_canonical_delivery_is_returned_once_after_commit() -> None:
    package = _with_delivery(_package(), "resolution_escape", DELIVERY_TEXT)
    engine = _engine(_state(package, facts=("truth_no_longer_containable",), fired=("SL-3C-C", "SL-3C-F")))

    first = engine.turn("Inspect the broadcast chamber.")
    second = engine.turn("Inspect the broadcast chamber again.")

    assert [segment.text for segment in first.segments].count(DELIVERY_TEXT) == 1
    assert [segment.text for segment in second.segments].count(DELIVERY_TEXT) == 0
    assert "resolution_escape" in engine.state.fired_event_ids


def test_canonical_event_without_delivery_text_returns_no_delivery_segment() -> None:
    package = _package()
    engine = _engine(
        _state(
            package,
            facts=ENTRY_FACTS,
            fired=("SL-3C-A",),
        )
    )

    result = engine.turn("Inspect the broadcast chamber.")
    expected = (
        "Michelle's broadcast carries the evidence, detention locations, and Brandon's confession across the "
        "country. Charles can no longer contain the truth through one channel."
    )

    assert all(segment.text != expected for segment in result.segments)


def test_loader_rejects_blank_canonical_delivery_text(tmp_path: Path) -> None:
    copied = tmp_path / "continuity-initiative"
    shutil.copytree(PACKAGE_ROOT, copied)
    routes = copied / "storylet-routes.yaml"
    source = routes.read_text(encoding="utf-8")
    source = source.replace(f'delivery_text: "{DELIVERY_TEXT}"', 'delivery_text: "   "', 1)
    routes.write_text(source, encoding="utf-8")

    with pytest.raises(StoryPackageError, match="delivery_text must not be empty"):
        load_story_package(copied)


def test_real_escape_delivery_sets_only_escape_facts() -> None:
    package = _package()
    engine = _engine(_state(package, facts=("truth_no_longer_containable",), fired=("SL-3C-C", "SL-3C-F")))

    result = engine.turn("Inspect the broadcast chamber.")
    texts = [segment.text for segment in result.segments]
    true_facts = {fact.predicate for fact in engine.state.facts.asserted if str(fact.value).lower() == "true"}

    assert texts.count(DELIVERY_TEXT) == 1
    assert "captives_reaching_surface" in true_facts
    assert "national_network_fragmenting" not in true_facts
    assert "community_rescue_efforts_begun" not in true_facts
