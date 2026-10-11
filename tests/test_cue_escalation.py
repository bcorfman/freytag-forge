"""Hermetic coverage for per-visit unresolved-cue escalation."""

from __future__ import annotations

from pathlib import Path

import pytest

from storygame.runtime.cloudflare import CloudflareTurnProvider
from storygame.runtime.contracts import parse_turn_proposal
from storygame.runtime.engine import RuntimeEngine
from storygame.runtime.state import CueStage, RuntimeSnapshot, RuntimeState
from storygame.story_package.loader import load_story_package

PACKAGE = load_story_package(Path("data/stories/continuity-initiative"))
FACT_ID = "continuity_initiative_known"


def _state() -> RuntimeState:
    package = PACKAGE.model_copy(
        update={
            "deliveries": tuple(
                delivery.model_copy(update={"escalation_text": "The workstation still holds a lead."})
                if delivery.fact_id == FACT_ID
                else delivery
                for delivery in PACKAGE.deliveries
            )
        }
    )
    state = RuntimeState(package=package, current_scene_id="1A", phase="exposition")
    state._assert_scene_entry_fact("1A")
    return state


def _provider(_text: str) -> dict[str, object]:
    return {"segments": [{"kind": "narration", "text": "The room remains quiet."}]}


def test_escalation_is_recorded_once_at_the_scene_nudge() -> None:
    state = _state()
    engine = RuntimeEngine(state, _provider)
    engine.turn("Search the drawer.")
    for _ in range(9):
        engine.turn("Inspect the workstation.")

    assert state.turn_index == 10
    assert state.cue_stages[-1].stage == 2
    assert state.cue_stages[-1].fact_id == FACT_ID
    assert state.staged_cue_fact_id is None

    for _ in range(2):
        engine.turn("Inspect the workstation.")
    assert [stage.stage for stage in state.cue_stages if stage.fact_id == FACT_ID] == [2]


def test_snapshot_round_trip_and_old_snapshot_default() -> None:
    state = _state()
    state.delivered_cue_ids = (FACT_ID,)
    state.cue_stages = state.cue_stages + (CueStage(fact_id=FACT_ID, stage=1, last_turn=1, visit_entered_at=0),)
    snapshot = state.snapshot()
    restored = _state()
    restored.restore_snapshot(snapshot)
    assert restored.cue_stages == snapshot.cue_stages
    snapshot_copy = RuntimeSnapshot(
        version=snapshot.version,
        current_scene_id=snapshot.current_scene_id,
        phase=snapshot.phase,
        active_event_ids=snapshot.active_event_ids,
        fired_event_ids=snapshot.fired_event_ids,
        facts=snapshot.facts,
        turn_index=snapshot.turn_index,
        scene_entered_at_turn=snapshot.scene_entered_at_turn,
        turn_records=snapshot.turn_records,
        delivered_cue_ids=snapshot.delivered_cue_ids,
        cue_stages=snapshot.cue_stages,
        staged_cue_fact_id=snapshot.staged_cue_fact_id,
        staged_cue_stage=snapshot.staged_cue_stage,
        staged_handoff_fact_ids=snapshot.staged_handoff_fact_ids,
        last_turn_delivery=snapshot.last_turn_delivery,
    )
    assert snapshot_copy.cue_stages == snapshot.cue_stages

    old_snapshot = RuntimeSnapshot(
        version=snapshot.version,
        current_scene_id=snapshot.current_scene_id,
        phase=snapshot.phase,
        active_event_ids=snapshot.active_event_ids,
        fired_event_ids=snapshot.fired_event_ids,
        facts=snapshot.facts,
        turn_index=snapshot.turn_index,
        scene_entered_at_turn=snapshot.scene_entered_at_turn,
        turn_records=snapshot.turn_records,
        delivered_cue_ids=snapshot.delivered_cue_ids,
        staged_cue_fact_id=snapshot.staged_cue_fact_id,
        staged_handoff_fact_ids=snapshot.staged_handoff_fact_ids,
        last_turn_delivery=snapshot.last_turn_delivery,
    )
    assert old_snapshot.cue_stages == ()
    assert old_snapshot.staged_cue_stage == 1


@pytest.mark.parametrize("stage", [1, 2])
def test_authored_composer_uses_escalation_and_falls_back(stage: int) -> None:
    state = _state()
    state.staged_cue_fact_id = FACT_ID
    state.staged_cue_stage = stage
    provider = CloudflareTurnProvider.__new__(CloudflareTurnProvider)
    provider.state = state
    proposal = parse_turn_proposal({"segments": [{"kind": "narration", "text": "The room remains quiet."}]})

    result = provider._compose_staged_cue(proposal)

    assert result.segments[-1].text == (
        "The workstation still holds a lead."
        if stage == 2
        else next(d.cue_text for d in state.package.deliveries if d.fact_id == FACT_ID)
    )


def test_escalation_falls_back_to_stage_one_text_when_unset() -> None:
    state = _state()
    delivery = next(item for item in state.package.deliveries if item.fact_id == FACT_ID)
    state.package = state.package.model_copy(
        update={
            "deliveries": tuple(
                item.model_copy(update={"escalation_text": None}) if item is delivery else item
                for item in state.package.deliveries
            )
        }
    )
    state.staged_cue_fact_id = FACT_ID
    state.staged_cue_stage = 2
    provider = CloudflareTurnProvider.__new__(CloudflareTurnProvider)
    provider.state = state

    result = provider._compose_staged_cue(
        parse_turn_proposal({"segments": [{"kind": "narration", "text": "The room remains quiet."}]})
    )

    assert result.segments[-1].text == delivery.cue_text
