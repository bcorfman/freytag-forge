from __future__ import annotations

from pathlib import Path

import pytest

from storygame.runtime.cloudflare import NarrationProviderError
from storygame.runtime.engine import RuntimeEngine
from storygame.runtime.reference_resolution import Clarification, ReferenceResult
from storygame.runtime.state import RuntimeSnapshot, RuntimeState
from storygame.runtime.validation import ProposalValidationError
from storygame.story_package.loader import load_story_package
from tests.test_continuity_1c_incident import _facts

PACKAGE = load_story_package(Path("data/stories/continuity-initiative"))
WITHDRAWAL = (
    "The sweep reaches the loading docks. Brandon pulls Kristin away from the observation shaft. "
    '"We are leaving. Now," he says. They slip out the way they came, with no numbers and no route. '
    'Brandon says, "We will have to find another way in."'
)
NUDGE = (
    "A siren sounds somewhere below. The sweep is coming closer. Brandon grabs Kristin's arm. "
    '"We are almost out of time," he says. "The service entrance is still open. Follow me through it, '
    'or we leave with nothing."'
)
MISS = (
    'The view down the observation shaft goes dark. Brandon says, "That chance is gone. We can still try '
    'the service entrance. Follow me through it if you want to try. We will have to risk the sweep."'
)
ADVANTAGE_FALLBACKS = (
    "Kristin copies the prisoner numbers and matches them to missing-person records.",
    "Brandon explains the transfer route and opens the service entrance.",
)


def _state() -> RuntimeState:
    state = RuntimeState.bootstrap(PACKAGE)
    state.current_scene_id = "1C"
    state.phase = next(scene.metadata.freytag_phase for scene in PACKAGE.scenes if scene.metadata.scene_id == "1C")
    state._assert_scene_entry_fact("1C")
    state.active_event_ids.update({"SL-1C-A", "SL-1C-B", "SL-1C-C"})
    return state


def _provider(_command: str) -> dict[str, object]:
    return {"segments": [{"kind": "narration", "text": "Kristin checks the loading docks."}]}


def _recovery_provider(_command: str) -> dict[str, object]:
    return {
        "segments": [{"kind": "narration", "text": "Brandon leads Kristin through the service entrance."}],
        "selected_knowledge_ids": ["k_sl_1c_d_r1"],
    }


def _run_to_turn(state: RuntimeState, turn: int, provider=_provider) -> list[str]:
    engine = RuntimeEngine(state, provider)
    texts: list[str] = []
    while state.turn_index < turn:
        result = engine.turn("Inspect the loading docks for a safe route.")
        texts.extend(segment.text for segment in result.segments)
    return texts


def test_staller_gets_miss_nudge_withdrawal_and_clean_no_advantage_handoff() -> None:
    state = _state()
    engine = RuntimeEngine(state, _provider)
    responses = []
    for _ in range(8):
        responses.append(engine.turn("Inspect the loading docks for a safe route."))

    by_turn = {
        index: tuple(segment.text for segment in response.segments) for index, response in enumerate(responses, 1)
    }
    assert MISS in by_turn[5]
    assert by_turn[6].count(NUDGE) == 1
    assert WITHDRAWAL in by_turn[8]
    assert state.current_scene_id == "2A"
    assert not {
        "processing_numbers_copied",
        "service_level_access_known",
        "evidence_gap_processing_numbers",
        "trust_brandon",
        "terminal_sweep_closing",
        "facility_proof",
        "captives_confirmed_alive",
    } & _facts(state)
    all_text = " ".join(text for texts in by_turn.values() for text in texts)
    assert not any(fallback in all_text for fallback in ADVANTAGE_FALLBACKS)
    assert by_turn[8] == (WITHDRAWAL, PACKAGE.scenes[3].metadata.entry_text)


@pytest.mark.parametrize("recovery_turn", [6, 7, 8])
def test_recovery_on_deadline_turn_prevents_nudge_or_withdrawal(recovery_turn: int) -> None:
    state = _state()
    engine = RuntimeEngine(state, _provider)
    responses = []
    for _ in range(5):
        responses.append(engine.turn("Inspect the loading docks for a safe route."))
    for _ in range(5, recovery_turn - 1):
        responses.append(engine.turn("Inspect the loading docks for a safe route."))
    recovery = RuntimeEngine(state, _recovery_provider).turn("Follow Brandon through the service entrance.")
    responses.append(recovery)

    texts = [segment.text for response in responses for segment in response.segments]
    assert state.current_scene_id == "2A"
    assert texts.count(NUDGE) == (0 if recovery_turn == 6 else 1)
    assert WITHDRAWAL not in texts
    assert "facility_infiltration_needed" in _facts(state)
    assert "terminal_sweep_closing" in _facts(state)


@pytest.mark.parametrize("save_turn", [5, 6])
def test_save_load_after_miss_and_nudge_preserves_stall_exit(save_turn: int) -> None:
    original = _state()
    _run_to_turn(original, save_turn)
    saved = RuntimeSnapshot.model_validate_json(original.snapshot().model_dump_json())
    restored = _state()
    restored.restore_snapshot(saved)
    texts = _run_to_turn(restored, 8)
    assert WITHDRAWAL in texts
    assert restored.current_scene_id == "2A"


def test_rejected_turn_does_not_advance_stall_exit_clock() -> None:
    state = _state()
    before = state.snapshot()

    def rejected(_command: str) -> dict[str, object]:
        return {
            "segments": [{"kind": "narration", "text": "Kristin waits."}],
            "selected_knowledge_ids": ["k_sl_1c_d_r1"],
        }

    with pytest.raises(ProposalValidationError):
        RuntimeEngine(state, rejected).turn("Follow Brandon through the service entrance.")
    assert state.snapshot() == before


def test_clarification_does_not_advance_stall_exit_clock(monkeypatch: pytest.MonkeyPatch) -> None:
    state = _state()
    before = state.snapshot()
    clarification = Clarification("Inspect the loading docks.", "docks", (("loading_docks", "docks"),), 0)
    monkeypatch.setattr(
        "storygame.runtime.engine.resolve_references",
        lambda *_args, **_kwargs: ReferenceResult(
            command="Inspect the loading docks.",
            question=clarification,
            outcome="ambiguous",
            original="Inspect the docks.",
            resolutions=(),
        ),
    )

    RuntimeEngine(state, _provider).turn("Inspect the docks.")
    assert state.snapshot() == before


def test_transport_error_does_not_advance_stall_exit_clock() -> None:
    state = _state()
    before = state.snapshot()

    def transport_error(_command: str) -> object:
        raise NarrationProviderError("temporary service failure", error_code="TRANSIENT")

    with pytest.raises(NarrationProviderError):
        RuntimeEngine(state, transport_error).turn("Inspect the loading docks for a safe route.")
    assert state.snapshot() == before
