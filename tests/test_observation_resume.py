from __future__ import annotations

import copy
import json
from threading import Event, Thread

import pytest

from storygame.runtime import capture as capture_module
from storygame.runtime.capture import WorldCapture
from storygame.runtime.cloudflare import CloudflareTurnProvider
from storygame.runtime.engine import RuntimeEngine
from storygame.runtime.observation import ObservationRequest
from storygame.runtime.observation_preview import CandidatePreview
from storygame.runtime.state import RuntimeState
from storygame.runtime.validation import ProposalValidationError
from storygame.runtime.world_model import world_for
from tests.test_observation_enforcement import (
    PACKAGE,
    _capture,
    _observing_state,
    _provider_state_snapshot,
    _ScriptedProvider,
)
from tests.test_observation_preview import _synthetic_package
from tests.test_runtime_capture import _state_1b


def _provider(
    state: RuntimeState,
    replies: list[tuple[str, dict[str, object] | None]],
    *,
    request: ObservationRequest | None = None,
) -> _ScriptedProvider:
    provider = _ScriptedProvider(state, replies)
    provider.observe_automatically = False
    provider.observation_request = request or ObservationRequest("Inspect the truck.", "enter", "kristin_truck")
    return provider


def _serialized_preview_context(monkeypatch: pytest.MonkeyPatch, state: RuntimeState, provider: _ScriptedProvider):
    capture, asks = _capture(provider, [1.0])
    match_calls: list[object] = []
    monkeypatch.setattr(
        CloudflareTurnProvider,
        "_request_item_facts",
        lambda _provider, payload: match_calls.append(payload) or {"same_as": {"notebook": "Kristin's laptop"}},
    )
    command = "Inspect the truck."
    narration = "The laptop is visible."
    capture.before_turn(command)
    provider(command)
    candidate = copy.deepcopy(state)
    preview = capture.preview_commit(command, narration, candidate, entered_scene=False)
    payload = json.loads(json.dumps(capture.context()))
    return capture, asks, match_calls, command, narration, candidate, preview, payload


def test_context_without_preview_is_unchanged() -> None:
    enforcing_state = _observing_state()
    enforcing_provider = _provider(enforcing_state, [("The truck is quiet.", None)])
    enforcing_capture, _ = _capture(enforcing_provider, [1.0], enforcing=True)
    enforcing_capture.before_turn("Inspect the truck.")

    plain_state = _observing_state()
    plain_provider = _provider(plain_state, [("The truck is quiet.", None)])
    plain_capture, _ = _capture(plain_provider, [1.0], enforcing=False)
    plain_capture.before_turn("Inspect the truck.")

    assert "observation_preview" not in enforcing_capture.context()
    assert enforcing_capture.context() == plain_capture.context()


def test_preview_context_round_trip_replays_billed_answers(monkeypatch: pytest.MonkeyPatch) -> None:
    state = _observing_state()
    provider = _provider(state, [("The laptop is visible.", {"notebook": {"place": "driver's seat"}})])
    capture, asks, match_calls, command, narration, candidate, preview, payload = _serialized_preview_context(
        monkeypatch, state, provider
    )

    assert payload["observation_preview"] == preview.to_json()
    assert CandidatePreview.from_json(payload["observation_preview"]).facts_after == preview.facts_after

    resumed_provider = _provider(state, [])
    resumed_capture, resumed_asks = _capture(resumed_provider, [1.0])
    resumed_capture.resume(payload)
    record = resumed_capture.after_commit(command, narration, entered_scene=False)

    assert resumed_asks == []
    assert len(match_calls) == 1
    assert record["observation_diverged"] is False
    assert state.facts == candidate.facts
    assert resumed_capture._pending_preview is None
    assert asks


def _break_with_preview(
    monkeypatch: pytest.MonkeyPatch,
    *,
    post_commit: bool,
) -> tuple[RuntimeState, _ScriptedProvider, WorldCapture, list[tuple[object, object]]]:
    if post_commit:
        state = _state_1b()
        request = ObservationRequest("Inspect the transit token.", "look", "transit_card")
        replies = [("The token is damaged.", {"Transit token": {"state": "destroyed"}})]
    else:
        state = _observing_state()
        request = ObservationRequest("Inspect the truck.", "enter", "kristin_truck")
        replies = [("The laptop is visible.", {"Kristin's laptop": {"place": "driver's seat"}})]
    provider = _provider(state, replies, request=request)
    capture, asks = _capture(provider, [1.0])
    engine = RuntimeEngine(state, provider, capture=capture)
    if not post_commit:
        monkeypatch.setattr(engine.validator, "validate", lambda *_args: ("brandon",))
    proposal = engine.turn(request.action)
    assert proposal.game_break is not None
    assert state.pending_capture is not None
    return state, provider, capture, asks


def _restore_for_break(
    state: RuntimeState,
    asks: list[tuple[object, object]],
) -> tuple[RuntimeState, _ScriptedProvider, WorldCapture, list[tuple[object, object]]]:
    restored = RuntimeState.model_validate_json(state.model_dump_json())
    provider = _provider(restored, [])
    capture, resumed_asks = _capture(provider, [1.0])
    return restored, provider, capture, resumed_asks


@pytest.mark.parametrize("post_commit", [False, True])
def test_game_break_json_resume_proceeds_once_or_returns_cleanly(
    monkeypatch: pytest.MonkeyPatch, post_commit: bool
) -> None:
    state, provider, _capture_before, asks = _break_with_preview(monkeypatch, post_commit=post_commit)
    serialized = state.pending_capture
    assert json.dumps(serialized)
    assert state.model_dump_json()

    restored, resumed_provider, resumed_capture, resumed_asks = _restore_for_break(state, asks)
    before_facts = restored.pending_snapshot.facts if restored.pending_snapshot else None
    before_turn = restored.pending_snapshot.turn_index if restored.pending_snapshot else None
    resumed = RuntimeEngine(restored, resumed_provider, capture=resumed_capture)
    resumed.resolve_break("proceed")

    assert restored.pending_break is None
    assert restored.pending_capture is None
    assert resumed_asks == []
    assert resumed_provider.narration_calls == 0
    expected_turn = before_turn + 1 if before_turn is not None and not post_commit else before_turn
    assert restored.turn_index == expected_turn
    if post_commit:
        assert world_for(PACKAGE, restored.facts).axis_values("transit_card")["intact"] == "destroyed"
    else:
        assert world_for(PACKAGE, restored.facts).parent("kristin_laptop") == "truck_driver_seat"
    assert before_facts != restored.facts
    assert provider.narration_calls == 1
    assert asks


def test_game_break_return_restores_snapshot_and_discards_preview(monkeypatch: pytest.MonkeyPatch) -> None:
    state, _provider_before, _capture_before, _asks = _break_with_preview(monkeypatch, post_commit=False)
    pending_snapshot = state.pending_snapshot
    assert pending_snapshot is not None
    restored, _provider, capture, _resumed_asks = _restore_for_break(state, _asks)

    RuntimeEngine(restored, _provider, capture=capture).resolve_break("return_to_scene")

    assert restored.snapshot() == pending_snapshot
    assert restored.pending_break is None
    assert restored.pending_capture is None
    assert capture._pending_preview is None


def test_divergence_on_proceed_restores_pending_snapshot(monkeypatch: pytest.MonkeyPatch) -> None:
    state, _provider_before, _capture_before, asks = _break_with_preview(monkeypatch, post_commit=False)
    restored, provider, capture, _resumed_asks = _restore_for_break(state, asks)
    pending_snapshot = restored.pending_snapshot
    assert pending_snapshot is not None
    world_for(restored.package, restored.facts).set_conditions("kristin_laptop", ["tampered"])

    with pytest.raises(ProposalValidationError) as caught:
        RuntimeEngine(restored, provider, capture=capture).resolve_break("proceed")

    assert caught.value.code == "observation_diverged"
    assert restored.facts == pending_snapshot.facts
    assert restored.pending_break is None
    assert restored.pending_capture is None
    provider.replies.append(("The truck is quiet.", None))
    result = RuntimeEngine(restored, provider, capture=capture).turn("Inspect the truck.")
    assert result.narration == "The truck is quiet."


@pytest.mark.parametrize("fault", ["both_preview", "verifier", "none_verifier", "confirm"])
@pytest.mark.parametrize("synthetic", [False, True])
def test_preview_faults_fail_closed_with_exact_rollback(
    monkeypatch: pytest.MonkeyPatch, fault: str, synthetic: bool
) -> None:
    state = RuntimeState.bootstrap(_synthetic_package()) if synthetic else _observing_state()
    if synthetic:
        command = "Inspect the survey tray."
        narration = "The calibrated lens catches the light."
        request = ObservationRequest(command, "look", "tray")
        raw = {"calibrated lens": {"place": "survey tray"}}
        match = {"calibrated lens": "lens"}
    else:
        command = "Inspect the truck."
        narration = "The laptop is visible."
        request = ObservationRequest(command, "enter", "kristin_truck")
        raw = {"notebook": {"place": "driver's seat"}}
        match = {"notebook": "Kristin's laptop"}
    provider = _provider(state, [(narration, raw)] * 2, request=request)
    capture, _asks = _capture(provider, [1.0, 1.0])
    before_state = state.snapshot()
    before_provider = _provider_state_snapshot(provider)
    match_calls: list[object] = []
    monkeypatch.setattr(
        CloudflareTurnProvider,
        "_request_item_facts",
        lambda _provider, payload: match_calls.append(payload) or {"same_as": match},
    )

    if fault == "both_preview":
        monkeypatch.setattr(capture, "preview_commit", lambda *_args, **_kwargs: (_ for _ in ()).throw(RuntimeError()))
    elif fault == "verifier":
        monkeypatch.setattr(
            capture.enforcing_verifier,
            "verify",
            lambda *_args, **_kwargs: (_ for _ in ()).throw(RuntimeError()),
        )
    elif fault == "none_verifier":
        monkeypatch.setattr(capture.enforcing_verifier, "verify", lambda *_args, **_kwargs: None)
    else:

        def failing_ask(_state: object, _questions: object):
            raise RuntimeError("confirm failed")

        def fail_inside_confirm(raw_value: object, **kwargs: object):
            kwargs["confirm"]("command", "story", "question", "statement", "player", "known")
            raise RuntimeError("confirm failed")

        capture.ask = failing_ask
        monkeypatch.setattr(provider, "apply_item_facts", fail_inside_confirm)

    engine = RuntimeEngine(state, provider, capture=capture)
    if synthetic:
        monkeypatch.setattr(engine.narration_validator, "validate", lambda *_args: None)
    with pytest.raises(ProposalValidationError) as caught:
        engine.turn(command)

    assert caught.value.code == "observation_preview_failed"
    assert state.snapshot() == before_state
    assert _provider_state_snapshot(provider) == before_provider
    assert state.last_turn_delivery == before_state.last_turn_delivery
    assert provider.narration_calls <= 2
    assert len(match_calls) <= 2
    assert engine.last_attempt is not None
    assert engine.last_attempt.outcome == "rejected"


def test_referent_match_finishes_before_implicit_taking(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("FREYTAG_JEV_BATCH", raising=False)
    state = RuntimeState.bootstrap(_synthetic_package())
    provider = _provider(
        state,
        [("The calibrated lens is visible.", {"calibrated lens": {"place": "survey tray"}})],
        request=ObservationRequest("Inspect the survey tray.", "look", "tray"),
    )
    prefetch_started = Event()
    referent_match_started = Event()
    overlap_confirmed = Event()
    prepare_completed = Event()
    take_started = Event()
    world_move_started = Event()
    calls = []

    def ask(_state, questions):
        if len(questions) > 1:
            prefetch_started.set()
            referent_match_started.wait()
            overlap_confirmed.set()
        return {key: {"noul": 1.0 if key.split(":", 1)[0] == "moves_thing" else 0.0} for key in questions}

    def request_item_facts(_provider, _payload):
        referent_match_started.set()
        prefetch_started.wait()
        overlap_confirmed.set()
        return {"same_as": {"calibrated lens": "lens"}}

    class GatedConcurrentCall:
        def __init__(self, target):
            self.target = target
            self.release = Event()
            self.thread = None
            self.value = None
            self.error = None
            calls.append(self)

        def start(self):
            self.thread = Thread(target=self._run, daemon=True)
            self.thread.start()

        def join(self):
            self.release.set()
            self.thread.join()
            if self.error is not None:
                raise self.error
            return self.value

        def _run(self):
            self.release.wait()
            try:
                self.value = self.target()
                prepare_completed.set()
            except BaseException as error:
                self.error = error

    monkeypatch.setattr(capture_module, "ConcurrentCall", GatedConcurrentCall)
    monkeypatch.setattr(capture_module, "_prefetch_targets", lambda *_args, **_kwargs: (("one", "two"), (), ()))
    monkeypatch.setattr(CloudflareTurnProvider, "_request_item_facts", request_item_facts)
    world_type = type(provider._world())
    original_world_move = world_type.move

    def checked_world_move(world, entity_id, parent_id, *, under=False):
        if not prepare_completed.is_set():
            raise AssertionError("world.move began before referent matching completed")
        world_move_started.set()
        return original_world_move(world, entity_id, parent_id, under=under)

    monkeypatch.setattr(world_type, "move", checked_world_move)
    original_take_before_put = capture_module.take_before_put

    def checked_take_before_put(world, package, command, moves_thing):
        if not prepare_completed.is_set():
            calls[0].release.set()
            calls[0].thread.join()
            raise AssertionError("implicit taking began before referent matching completed")
        take_started.set()
        return original_take_before_put(world, package, command, moves_thing)

    monkeypatch.setattr(capture_module, "take_before_put", checked_take_before_put)
    capture = WorldCapture(provider, ask)

    capture.before_turn("Inspect the survey tray.")

    assert take_started.is_set()
    assert world_move_started.is_set()
    assert prepare_completed.is_set()
    assert overlap_confirmed.is_set()


def test_first_preview_fault_retries_and_commits_once(monkeypatch: pytest.MonkeyPatch) -> None:
    state = _observing_state()
    provider = _provider(state, [("The laptop is visible.", {"notebook": {"place": "driver's seat"}})] * 2)
    capture, _asks = _capture(provider, [1.0, 1.0])
    original = capture.preview_commit
    calls = 0

    def fail_once(*args, **kwargs):
        nonlocal calls
        calls += 1
        if calls == 1:
            raise RuntimeError("preview failed")
        return original(*args, **kwargs)

    monkeypatch.setattr(capture, "preview_commit", fail_once)
    monkeypatch.setattr(
        CloudflareTurnProvider,
        "_request_item_facts",
        lambda _provider, _payload: {"same_as": {"notebook": "Kristin's laptop"}},
    )

    RuntimeEngine(state, provider, capture=capture).turn("Inspect the truck.")

    assert calls == 2
    assert provider.narration_calls == 2
    assert capture.last_after["observation_diverged"] is False
    assert world_for(PACKAGE, state.facts).parent("kristin_laptop") == "truck_driver_seat"


def test_rejected_attempt_preview_is_not_consumed_by_retry(monkeypatch: pytest.MonkeyPatch) -> None:
    state = _observing_state()
    provider = _provider(
        state,
        [
            ("Nothing is shown.", {"notebook": {"place": "driver's seat"}}),
            ("The laptop is visible.", {"notebook": {"place": "driver's seat"}}),
        ],
    )
    capture, _asks = _capture(provider, [0.0, 1.0])
    previews: list[CandidatePreview] = []
    original = capture.preview_commit

    def record_preview(*args, **kwargs):
        preview = original(*args, **kwargs)
        previews.append(preview)
        return preview

    monkeypatch.setattr(capture, "preview_commit", record_preview)
    monkeypatch.setattr(
        CloudflareTurnProvider,
        "_request_item_facts",
        lambda _provider, _payload: {"same_as": {"notebook": "Kristin's laptop"}},
    )

    RuntimeEngine(state, provider, capture=capture).turn("Inspect the truck.")

    assert [preview.accepted for preview in previews] == [False, True]
    assert capture.last_after["observation_preview"]["accepted"] is True
    assert capture._pending_preview is None


def test_after_commit_failure_keeps_existing_apply_behavior(monkeypatch: pytest.MonkeyPatch) -> None:
    state = _observing_state()
    provider = _provider(state, [("The laptop is visible.", {"notebook": {"place": "driver's seat"}})])
    capture, _asks = _capture(provider, [1.0])
    monkeypatch.setattr(
        CloudflareTurnProvider,
        "_request_item_facts",
        lambda _provider, _payload: {"same_as": {"notebook": "Kristin's laptop"}},
    )
    monkeypatch.setattr(capture, "after_commit", lambda *_args, **_kwargs: (_ for _ in ()).throw(RuntimeError()))

    with pytest.raises(RuntimeError):
        RuntimeEngine(state, provider, capture=capture).turn("Inspect the truck.")

    assert world_for(PACKAGE, state.facts).parent("kristin_laptop") == "truck_passenger_seat"


@pytest.mark.parametrize("synthetic", [False, True])
def test_synthetic_and_canonical_stories_round_trip_preview(monkeypatch: pytest.MonkeyPatch, synthetic: bool) -> None:
    state = RuntimeState.bootstrap(_synthetic_package()) if synthetic else _observing_state()
    if synthetic:
        provider = _provider(
            state,
            [("The calibrated lens catches the light.", {"calibrated lens": {"place": "survey tray"}})],
            request=ObservationRequest("Inspect the survey tray.", "look", "tray"),
        )
        command = "Inspect the survey tray."
        narration = "The calibrated lens catches the light."
    else:
        provider = _provider(state, [("The laptop is visible.", {"notebook": {"place": "driver's seat"}})])
        command = "Inspect the truck."
        narration = "The laptop is visible."
    capture, _asks = _capture(provider, [1.0])
    match_calls: list[object] = []
    monkeypatch.setattr(
        CloudflareTurnProvider,
        "_request_item_facts",
        lambda _provider, payload: match_calls.append(payload) or {"same_as": {"calibrated lens": "lens"}},
    )
    capture.before_turn(command)
    provider(command)
    preview = capture.preview_commit(command, narration, copy.deepcopy(state), entered_scene=False)
    context = json.loads(json.dumps(capture.context()))
    resumed_provider = _provider(state, [])
    resumed_capture, asks = _capture(resumed_provider, [1.0])
    resumed_capture.resume(context)
    record = resumed_capture.after_commit(command, narration, entered_scene=False)

    assert preview.accepted is True
    assert record.get("observation_diverged", False) is False
    assert asks == []
    assert len(match_calls) == 1
