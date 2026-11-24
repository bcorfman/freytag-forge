"""Tests for the side-effect-free pacing-only replay."""

from __future__ import annotations

import copy
from pathlib import Path

from storygame.runtime.engine import RuntimeEngine
from storygame.runtime.facts import Fact
from storygame.runtime.pacing_replay import replay_pacing
from storygame.runtime.state import RuntimeState
from storygame.story_package.loader import load_story_package
from storygame.story_package.models import FactPredicate
from tests.story_source.helpers import compiled_story_copy, patch_source

PACKAGE_ROOT = Path(__file__).parents[1] / "data/stories/continuity-initiative"


class CountingProvider:
    def __init__(self) -> None:
        self.calls = 0

    def __call__(self, _command: str) -> dict[str, object]:
        self.calls += 1
        return {"segments": [{"kind": "narration", "text": "The room remains quiet."}]}


def _engine(*, package=None, turns_since_entry: int = 0) -> RuntimeEngine:
    package = package or load_story_package(PACKAGE_ROOT)
    state = RuntimeState.bootstrap(package)
    scene = next(scene for scene in package.scenes if scene.metadata.scene_id == "2A")
    state.current_scene_id = "2A"
    state.phase = scene.metadata.freytag_phase
    state._assert_scene_entry_fact("2A")
    state.turn_index = state.scene_entered_at_turn + turns_since_entry
    provider = CountingProvider()
    return RuntimeEngine(state, provider)


def _package_with_event(tmp_path: Path, **updates: object):
    root = compiled_story_copy(tmp_path)
    for address, value in updates.items():
        patch_source(root / "source", "scenes/2A.yaml", address, value)
    return load_story_package(root)


def test_replay_has_no_side_effects_or_provider_calls() -> None:
    engine = _engine(turns_since_entry=4)
    state = engine.state
    before = state.snapshot()
    fields = {
        name: copy.deepcopy(getattr(state, name))
        for name in (
            "current_scene_id",
            "phase",
            "active_event_ids",
            "fired_event_ids",
            "facts",
            "turn_index",
            "scene_entered_at_turn",
            "turn_records",
            "pending_break",
            "pending_snapshot",
            "pending_proposal",
            "pending_capture",
            "delivered_cue_ids",
            "cue_stages",
            "staged_cue_fact_id",
            "staged_cue_stage",
            "staged_handoff_fact_ids",
            "last_turn_delivery",
            "story_complete",
        )
    }

    result = replay_pacing(engine)

    assert result.fired_event_ids == ("inspection_window_2a",)
    assert state.snapshot() == before
    assert {name: getattr(state, name) for name in fields} == fields
    assert engine.provider.calls == 0


def test_replay_fires_inspection_window_only_on_time() -> None:
    assert replay_pacing(_engine(turns_since_entry=4)).fired_event_ids == ("inspection_window_2a",)
    assert "inspection_window_2a" not in replay_pacing(_engine(turns_since_entry=3)).fired_event_ids


def test_replay_reports_deliveries_and_deduplicates_in_package_order() -> None:
    package = load_story_package(PACKAGE_ROOT)
    # The source validator rejects duplicate deliveries; use the frozen model copy to exercise union semantics.
    event = next(event for event in package.pacing.events if event.id == "inspection_window_2a")
    event = event.model_copy(update={"delivers": ("k_inspection_window_missed", "k_inspection_window_missed")})
    pacing = package.pacing.model_copy(update={"events": (event,)})
    package = package.model_copy(update={"pacing": pacing})
    result = replay_pacing(_engine(package=package, turns_since_entry=4))
    assert result.fired_event_ids == ("inspection_window_2a",)
    assert result.null_grounding_ids == ("k_inspection_window_missed",)


def test_replay_without_deliveries_has_no_null_grounding() -> None:
    result = replay_pacing(_engine(turns_since_entry=4))
    assert result.fired_event_ids == ("inspection_window_2a",)
    assert result.null_grounding_ids == ()


def test_clock_opened_storylets_are_not_null_grounding() -> None:
    result = replay_pacing(_engine(turns_since_entry=4))
    assert all(storylet_id not in result.fired_event_ids for storylet_id in ("SL-2A-A", "SL-2A-B"))
    assert result.null_grounding_ids == ()


def test_command_fact_is_not_replayed_until_it_exists(tmp_path: Path) -> None:
    package = _package_with_event(tmp_path)
    original = next(event for event in package.pacing.events if event.id == "inspection_nudge_2a")
    replacement = original.model_copy(update={"when": (FactPredicate(fact_id="command_fact", equals=True),)})
    events = tuple(replacement if event.id == original.id else event for event in package.pacing.events)
    package = package.model_copy(update={"pacing": package.pacing.model_copy(update={"events": events})})
    engine = _engine(package=package, turns_since_entry=6)
    assert "inspection_nudge_2a" not in replay_pacing(engine).fired_event_ids
    engine.state.facts.assert_fact(Fact(predicate="command_fact", subject="story", value="true"))
    assert "inspection_nudge_2a" in replay_pacing(engine).fired_event_ids


def test_replay_matches_new_events_from_a_real_no_effect_turn() -> None:
    first = _engine(turns_since_entry=4)
    second = _engine(turns_since_entry=4)
    expected = replay_pacing(second).fired_event_ids
    before = set(first.state.fired_event_ids)

    first.turn("Inspect the empty desk.", clock_seconds=0)

    actual = tuple(
        event.id
        for event in first.state.package.pacing.events
        if event.id not in before and event.id in first.state.fired_event_ids
    )
    assert actual == expected
    assert first.provider.calls == 1


def test_transition_event_is_reported_without_moving_live_scene() -> None:
    package = load_story_package(PACKAGE_ROOT)
    original = next(event for event in package.pacing.events if event.id == "inspection_window_2a")
    replacement = original.model_copy(update={"transition_id": "t_2a_2b"})
    events = tuple(replacement if event.id == original.id else event for event in package.pacing.events)
    package = package.model_copy(update={"pacing": package.pacing.model_copy(update={"events": events})})
    engine = _engine(package=package, turns_since_entry=4)
    scene = engine.state.current_scene_id

    result = replay_pacing(engine)

    assert "inspection_window_2a" in result.fired_event_ids
    assert engine.state.current_scene_id == scene


def test_replay_is_deterministic_when_called_twice() -> None:
    engine = _engine(turns_since_entry=4)
    assert replay_pacing(engine) == replay_pacing(engine)
