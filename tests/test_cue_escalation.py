"""Hermetic coverage for per-visit unresolved-cue escalation."""

from __future__ import annotations

from pathlib import Path

import pytest

from storygame.runtime.cloudflare import CloudflareTurnProvider
from storygame.runtime.contracts import parse_turn_proposal
from storygame.runtime.engine import RuntimeEngine
from storygame.runtime.facts import Fact
from storygame.runtime.state import CueStage, RuntimeSnapshot, RuntimeState
from storygame.runtime.validation import ProposalValidationError
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


def _stubbed_cloudflare_provider(monkeypatch, state: RuntimeState, *texts: str) -> CloudflareTurnProvider:
    provider = CloudflareTurnProvider(worker_url="https://worker.example/turn", token="", state=state)
    replies = iter(texts or ("The room remains quiet.",))
    monkeypatch.setattr(
        provider,
        "_request_allowing_one_transient_retry",
        lambda _payload: {"segments": [{"kind": "narration", "text": next(replies)}]},
    )
    return provider


def _texts(result) -> tuple[str, ...]:
    return tuple(segment.text for segment in result.segments)


def _assert_observable(
    state: RuntimeState,
    result,
    *,
    cue_stages: tuple[CueStage, ...],
    delivered_cue_ids: tuple[str, ...],
    staged_cue_fact_id: str | None,
    staged_cue_stage: int,
    current_scene_id: str,
) -> None:
    assert state.cue_stages == cue_stages
    assert state.delivered_cue_ids == delivered_cue_ids
    assert state.staged_cue_fact_id == staged_cue_fact_id
    assert state.staged_cue_stage == staged_cue_stage
    assert state.current_scene_id == current_scene_id
    assert _texts(result)


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


def test_earned_reveal_before_nudge_never_escalates(monkeypatch) -> None:
    state = _state()
    provider = _stubbed_cloudflare_provider(monkeypatch, state, *(["The room remains quiet."] * 12))
    engine = RuntimeEngine(state, provider)

    first = engine.turn("Inspect the workstation.")
    state.facts.assert_fact(Fact(predicate=FACT_ID, subject="story", value="true"))
    last = first
    for _ in range(9):
        last = engine.turn("Inspect the workstation.")

    _assert_observable(
        state,
        last,
        cue_stages=(CueStage(fact_id=FACT_ID, stage=1, last_turn=1, visit_entered_at=0),),
        delivered_cue_ids=(FACT_ID,),
        staged_cue_fact_id=None,
        staged_cue_stage=1,
        current_scene_id="1A",
    )
    assert all(state.package.deliveries[0].escalation_text not in text for text in _texts(last))
    assert all(stage.stage != 2 for stage in state.cue_stages)


def test_spent_reveal_never_escalates(monkeypatch) -> None:
    state = _state()
    state.delivered_cue_ids = (FACT_ID,)
    state.cue_stages = (CueStage(fact_id=FACT_ID, stage=1, last_turn=1, visit_entered_at=0),)
    state.turn_index = 9
    state.facts.assert_fact(Fact(predicate="memory_card_recovered", subject="story", value="true"))
    state.fired_event_ids.update(("SL-1A-B", "SL-1A-D"))
    provider = _stubbed_cloudflare_provider(monkeypatch, state, *(["The room remains quiet."] * 12))
    engine = RuntimeEngine(state, provider)
    assert not engine._cue_reveal_available(FACT_ID)

    last = engine.turn("Inspect the workstation.")

    _assert_observable(
        state,
        last,
        cue_stages=(CueStage(fact_id=FACT_ID, stage=1, last_turn=1, visit_entered_at=0),),
        delivered_cue_ids=(FACT_ID,),
        staged_cue_fact_id=None,
        staged_cue_stage=1,
        current_scene_id="1A",
    )
    assert all(stage.stage != 2 for stage in state.cue_stages)
    assert all(
        delivery.escalation_text not in text
        for delivery in state.package.deliveries
        if delivery.fact_id == FACT_ID
        for text in _texts(last)
    )


def test_rejected_nudge_restores_state_then_accepted_nudge_records_stage_two(monkeypatch) -> None:
    state = _state()
    provider = _stubbed_cloudflare_provider(
        monkeypatch,
        state,
        *(["The room remains quiet."] * 9),
        # The engine retries a rejected narration once, so the turn fails only when both replies are rejected.
        "Phase Two is active.",
        "Phase Two is active.",
        "The room remains quiet.",
    )
    engine = RuntimeEngine(state, provider)
    engine.turn("Search the drawer.")
    for _ in range(8):
        engine.turn("Inspect the workstation.")
    before = state.snapshot()

    with pytest.raises(ProposalValidationError):
        engine.turn("Inspect the workstation.")

    assert state.turn_index == before.turn_index
    assert state.cue_stages == before.cue_stages
    assert state.delivered_cue_ids == before.delivered_cue_ids
    assert state.staged_cue_fact_id is None
    assert state.staged_cue_stage == 1

    accepted = engine.turn("Inspect the workstation.")
    escalation = next(item.escalation_text for item in state.package.deliveries if item.fact_id == FACT_ID)
    assert _texts(accepted)[-1] == escalation
    assert _texts(accepted).count(escalation) == 1
    _assert_observable(
        state,
        accepted,
        cue_stages=(CueStage(fact_id=FACT_ID, stage=2, last_turn=10, visit_entered_at=0),),
        delivered_cue_ids=(FACT_ID,),
        staged_cue_fact_id=None,
        staged_cue_stage=1,
        current_scene_id="1A",
    )


@pytest.mark.nightly
def test_scene_reentry_clears_cues_and_allows_a_new_escalation(monkeypatch) -> None:
    state = _state()
    provider = _stubbed_cloudflare_provider(monkeypatch, state, *(["The room remains quiet."] * 24))
    engine = RuntimeEngine(state, provider)
    engine.turn("Search the drawer.")
    for _ in range(8):
        engine.turn("Inspect the workstation.")
    first_escalation = engine.turn("Inspect the workstation.")
    assert state.cue_stages[-1].stage == 2
    assert state.delivered_cue_ids == (FACT_ID,)
    assert state.staged_cue_fact_id is None
    assert state.current_scene_id == "1A"
    assert _texts(first_escalation)[-1] == next(
        item.escalation_text for item in state.package.deliveries if item.fact_id == FACT_ID
    )

    state.current_scene_id = "1B"
    state.phase = next(
        scene.metadata.freytag_phase for scene in state.package.scenes if scene.metadata.scene_id == "1B"
    )
    state._assert_scene_entry_fact("1B")
    assert state.cue_stages == ()
    assert state.delivered_cue_ids == ()
    state.current_scene_id = "1A"
    state.phase = "exposition"
    state._assert_scene_entry_fact("1A")
    assert state.cue_stages == ()
    assert state.delivered_cue_ids == ()

    engine.turn("Search the drawer.")
    for _ in range(8):
        engine.turn("Inspect the workstation.")
    escalation = engine.turn("Inspect the workstation.")
    _assert_observable(
        state,
        escalation,
        cue_stages=(CueStage(fact_id=FACT_ID, stage=2, last_turn=20, visit_entered_at=10),),
        delivered_cue_ids=(FACT_ID,),
        staged_cue_fact_id=None,
        staged_cue_stage=1,
        current_scene_id="1A",
    )
    assert _texts(escalation)[-1] == next(
        item.escalation_text for item in state.package.deliveries if item.fact_id == FACT_ID
    )


def test_forced_handoff_still_changes_scene_with_escalation(monkeypatch) -> None:
    def run(package):
        state = RuntimeState(package=package, current_scene_id="1A", phase="exposition")
        state._assert_scene_entry_fact("1A")
        engine = RuntimeEngine(state, _provider)
        result = None
        for _ in range(13):
            result = engine.turn("Inspect the workstation.")
        return state, result

    baseline_state, baseline_result = run(PACKAGE)
    escalated_package = PACKAGE.model_copy(
        update={
            "deliveries": tuple(
                item.model_copy(update={"escalation_text": "The workstation still holds a lead."})
                if item.fact_id == FACT_ID
                else item
                for item in PACKAGE.deliveries
            )
        }
    )
    escalated_state, escalated_result = run(escalated_package)

    assert baseline_state.current_scene_id == escalated_state.current_scene_id == "1B"
    assert baseline_state.cue_stages == escalated_state.cue_stages
    assert baseline_state.staged_handoff_fact_ids == escalated_state.staged_handoff_fact_ids == ()
    assert baseline_state.delivered_cue_ids == escalated_state.delivered_cue_ids
    assert baseline_state.staged_cue_fact_id == escalated_state.staged_cue_fact_id
    assert baseline_state.staged_cue_stage == escalated_state.staged_cue_stage
    assert _texts(baseline_result)[-1] == _texts(escalated_result)[-1]


def test_escalation_is_last_segment_once_and_not_repeated(monkeypatch) -> None:
    state = _state()
    provider = _stubbed_cloudflare_provider(monkeypatch, state, *(["The room remains quiet."] * 12))
    engine = RuntimeEngine(state, provider)
    engine.turn("Search the drawer.")
    for _ in range(8):
        engine.turn("Inspect the workstation.")
    nudge = engine.turn("Inspect the workstation.")
    after = engine.turn("Inspect the workstation.")
    escalation = next(item.escalation_text for item in state.package.deliveries if item.fact_id == FACT_ID)

    assert _texts(nudge)[-1] == escalation
    assert _texts(nudge).count(escalation) == 1
    assert escalation not in _texts(after)
    _assert_observable(
        state,
        after,
        cue_stages=(CueStage(fact_id=FACT_ID, stage=2, last_turn=10, visit_entered_at=0),),
        delivered_cue_ids=(FACT_ID,),
        staged_cue_fact_id=None,
        staged_cue_stage=1,
        current_scene_id="1A",
    )


def test_old_save_delivered_cue_without_stage_escalates_at_nudge(monkeypatch) -> None:
    state = _state()
    state.delivered_cue_ids = (FACT_ID,)
    state.cue_stages = ()
    provider = _stubbed_cloudflare_provider(monkeypatch, state, *(["The room remains quiet."] * 12))
    engine = RuntimeEngine(state, provider)

    first = engine.turn("Inspect the workstation.")
    assert state.cue_stages == ()
    assert state.delivered_cue_ids == (FACT_ID,)
    assert state.staged_cue_fact_id is None
    assert state.staged_cue_stage == 1
    last = first
    for _ in range(9):
        last = engine.turn("Inspect the workstation.")
    escalation = last
    expected = next(item.escalation_text for item in state.package.deliveries if item.fact_id == FACT_ID)
    _assert_observable(
        state,
        escalation,
        cue_stages=(CueStage(fact_id=FACT_ID, stage=2, last_turn=10, visit_entered_at=0),),
        delivered_cue_ids=(FACT_ID,),
        staged_cue_fact_id=None,
        staged_cue_stage=1,
        current_scene_id="1A",
    )
    assert expected in _texts(escalation)
    assert expected not in _texts(first)
