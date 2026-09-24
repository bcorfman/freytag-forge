"""Storylet expiry and resolution escalation coverage."""

from __future__ import annotations

from pathlib import Path

import pytest

from storygame.runtime.engine import RuntimeEngine
from storygame.runtime.facts import Fact
from storygame.runtime.state import RuntimeState
from storygame.runtime.validation import ProposalValidationError
from storygame.story_package.loader import load_story_package
from storygame.story_package.obligations import required_storylet_ids

PACKAGE = load_story_package(Path("data/stories/continuity-initiative"))


def _engine_at(
    scene_id: str,
    turns: int,
    *,
    package=PACKAGE,
    facts: tuple[str, ...] = (),
) -> tuple[RuntimeEngine, RuntimeState]:
    scene = next(scene for scene in package.scenes if scene.metadata.scene_id == scene_id)
    state = RuntimeState(package=package, current_scene_id=scene_id, phase=scene.metadata.freytag_phase)
    for fact_id in facts:
        state.facts.assert_fact(Fact(predicate=fact_id, subject="story", value="true"))
    state.turn_index = turns
    return RuntimeEngine(state, lambda _input: {"segments": []}), state


def test_optional_storylet_expires_after_latest_turn_and_never_fires() -> None:
    storylet = next(item for item in PACKAGE.storylet_routes.storylets if item.id == "SL-1A-C")
    engine, state = _engine_at("1A", storylet.latest_turn, facts=("michelle_warning_known",))

    engine._activate_pacing()  # noqa: SLF001 - exercise the pacing boundary directly.
    assert "SL-1A-C" in state.active_event_ids
    facts_before_expiry = state.facts.asserted

    state.turn_index = storylet.latest_turn + 1
    engine._activate_pacing()  # noqa: SLF001 - exercise the pacing boundary directly.

    assert "SL-1A-C" not in state.active_event_ids
    assert "SL-1A-C" not in state.fired_event_ids
    assert state.facts.asserted == facts_before_expiry


def test_expired_optional_storylet_cannot_reopen_through_earned_forward() -> None:
    storylet = next(item for item in PACKAGE.storylet_routes.storylets if item.id == "SL-1A-C")
    engine, state = _engine_at("1A", storylet.latest_turn + 1, facts=("michelle_warning_known",))
    state.fired_event_ids.update({"SL-1A-A", "SL-1A-B"})

    engine._activate_pacing()  # noqa: SLF001 - exercise the pacing boundary directly.

    assert "SL-1A-C" not in state.active_event_ids


def test_required_storylet_stays_active_past_latest_turn() -> None:
    for turns in (3, 4):
        engine, state = _engine_at("1A", turns, facts=("memory_card_in_kristins_custody",))

        engine._activate_pacing()  # noqa: SLF001 - exercise the pacing boundary directly.

        assert "SL-1A-B" in state.active_event_ids
        assert Fact(predicate="continuity_initiative_known", subject="story", value="true") not in state.facts.asserted


def test_real_package_has_twenty_seven_required_storylets() -> None:
    assert len(required_storylet_ids(PACKAGE)) == 27


def test_resolution_scene_does_not_stage_escalation() -> None:
    window = next(window for window in PACKAGE.pacing.scenes if window.scene_id == "3B")
    engine, state = _engine_at("3B", window.handoff_after_turns)
    engine._activate_pacing()  # noqa: SLF001 - exercise the pacing boundary directly.
    assert state.staged_handoff_fact_ids

    scene = next(scene for scene in PACKAGE.scenes if scene.metadata.scene_id == "3B")
    metadata = scene.metadata.model_copy(update={"freytag_phase": "resolution"})
    package = PACKAGE.model_copy(
        update={
            "scenes": tuple(
                item.model_copy(update={"metadata": metadata}) if item.metadata.scene_id == "3B" else item
                for item in PACKAGE.scenes
            )
        }
    )
    engine, state = _engine_at("3B", window.handoff_after_turns, package=package)

    engine._activate_pacing()  # noqa: SLF001 - exercise the pacing boundary directly.

    assert state.staged_cue_fact_id is None
    assert state.staged_handoff_fact_ids == ()


def test_snapshot_restore_reapplies_expiry_without_double_expiring() -> None:
    storylet = next(item for item in PACKAGE.storylet_routes.storylets if item.id == "SL-1A-C")
    engine, state = _engine_at("1A", storylet.latest_turn, facts=("michelle_warning_known",))
    engine._activate_pacing()  # noqa: SLF001 - exercise the pacing boundary directly.
    before = state.snapshot()

    def rejected_provider(_input: str) -> dict[str, object]:
        return {
            "segments": [{"kind": "narration", "text": "The patrol approaches the gate."}],
            "selected_knowledge_ids": ["k_sl_1a_c_r1"],
        }

    engine.provider = rejected_provider
    with pytest.raises(ProposalValidationError):
        engine.turn("Check the gate.")

    state.restore_snapshot(before)
    assert "SL-1A-C" in state.active_event_ids
    assert state.turn_index == storylet.latest_turn

    state.turn_index = storylet.latest_turn + 1
    engine._activate_pacing()  # noqa: SLF001 - exercise the pacing boundary directly.

    assert "SL-1A-C" not in state.active_event_ids
    assert "SL-1A-C" not in state.fired_event_ids
