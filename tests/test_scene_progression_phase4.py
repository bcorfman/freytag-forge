"""Regression tests retained while the provider contract is narrowed in Phase 3."""

from __future__ import annotations

from pathlib import Path

import pytest

from storygame.runtime.engine import RuntimeEngine
from storygame.runtime.state import RuntimeState
from storygame.runtime.validation import ProposalValidationError
from storygame.story_package.loader import load_story_package

PACKAGE = load_story_package(Path("data/stories/continuity-initiative"))


def _turn(text: str, selected: list[str] | None = None) -> dict[str, object]:
    return {"segments": [{"kind": "narration", "text": text}], "selected_knowledge_ids": selected or []}


def test_selected_reveal_derives_its_exact_package_route_and_effects() -> None:
    state = RuntimeState.bootstrap(PACKAGE)
    state.active_event_ids.add("SL-1A-B")
    engine = RuntimeEngine(
        state, lambda _: _turn("The damaged recording carries Michelle's warning.", ["k_sl_1a_b_r2"])
    )

    proposal = engine.turn("I search the desk drawer and play the damaged recording.")

    assert proposal.selected_knowledge_ids == ("k_sl_1a_b_r2",)
    assert [(event.event_id, event.realization_id) for event in proposal.events] == [("SL-1A-B", "SL-1A-B-R2")]
    assert state.facts.has("michelle_warning_known", "story", value="true")
    assert "SL-1A-B" in state.fired_event_ids
    assert engine.last_post_selection_projection is not None
    assert "k_sl_1a_b_r2" in {item.id for item in engine.last_post_selection_projection.committed_knowledge}


@pytest.mark.parametrize(
    "selected", [["k_sl_1c_b_r1"], ["k_sl_1a_b_r2", "k_sl_1a_b_r2"], ["k_sl_1a_b_r1", "k_sl_1a_b_r2"]]
)
def test_invalid_or_duplicate_selection_is_atomic(selected: list[str]) -> None:
    state = RuntimeState.bootstrap(PACKAGE)
    before = (state.facts.as_json(), set(state.fired_event_ids), tuple(state.turn_records))
    engine = RuntimeEngine(state, lambda _: _turn("The room yields no unearned revelation.", selected))

    with pytest.raises((ProposalValidationError, ValueError)):
        engine.turn("I inspect Michelle's phone.")

    assert (state.facts.as_json(), set(state.fired_event_ids), tuple(state.turn_records)) == before


def test_grounding_cannot_name_an_unselected_or_invented_source() -> None:
    state = RuntimeState.bootstrap(PACKAGE)
    state.active_event_ids.add("SL-1A-B")
    engine = RuntimeEngine(
        state,
        lambda _: {
            "segments": [{"kind": "narration", "text": "A recording clicks on.", "grounding_ids": ["SL-1A-B"]}],
            "selected_knowledge_ids": ["k_sl_1a_b_r2"],
        },
    )

    with pytest.raises(ProposalValidationError, match="grounding"):
        engine.turn("I recover the damaged recording.")
    assert not state.facts.has("michelle_warning_known", "story", value="true")


def test_declared_pressure_event_advances_without_provider_timing_or_prose_parsing() -> None:
    state = RuntimeState.bootstrap(PACKAGE)
    engine = RuntimeEngine(state, lambda _: _turn("Dust shifts beneath the door."))

    engine.turn("I wait.")
    engine.turn("I continue waiting.")

    assert state.facts.has("patrol_return_pressure", "story", value="true")
    assert "pressure_1a" in state.fired_event_ids
    assert state.facts.has("story_elapsed_seconds", "story", value="120")


def test_untrusted_provider_operations_and_transitions_fail_closed() -> None:
    state = RuntimeState.bootstrap(PACKAGE)
    before = (state.facts.as_json(), set(state.fired_event_ids), tuple(state.turn_records))
    engine = RuntimeEngine(
        state,
        lambda _: {
            "segments": [{"kind": "narration", "text": "An invented shortcut appears."}],
            "operations": [{"operation": "assert", "fact": {"predicate": "facility_proof", "subject": "story"}}],
        },
    )

    with pytest.raises(ValueError):
        engine.turn("I imagine distant proof.")
    assert (state.facts.as_json(), set(state.fired_event_ids), tuple(state.turn_records)) == before


def test_internal_game_break_path_keeps_the_resolved_candidate_pending_until_proceed(monkeypatch) -> None:
    state = RuntimeState.bootstrap(PACKAGE)
    engine = RuntimeEngine(state, lambda _: _turn("The choice would strand a future dependency."))
    monkeypatch.setattr(engine.validator, "validate", lambda *_: ("brandon",))

    proposal = engine.turn("I make the risky attempt.")

    assert proposal.game_break is not None
    assert state.has_pending_break
    engine.resolve_break("proceed")
    assert not state.has_pending_break
