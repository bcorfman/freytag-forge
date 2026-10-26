from __future__ import annotations

import copy
from pathlib import Path

import pytest

from storygame.runtime.capture import WorldCapture
from storygame.runtime.cloudflare import CloudflareTurnProvider, NarrationProviderError
from storygame.runtime.engine import RuntimeEngine
from storygame.runtime.item_facts import ItemFactsProvider
from storygame.runtime.observation import ObservationRequest
from storygame.runtime.observation_verifier import ObservationVerifier
from storygame.runtime.state import RuntimeState
from storygame.runtime.validation import ProposalValidationError
from storygame.runtime.world_model import world_for
from storygame.story_package.loader import load_story_package
from tests.test_observation_mode import _state_at
from tests.test_observation_preview import _provider_snapshot, _synthetic_package

ROOT = Path(__file__).parents[1]
PACKAGE = load_story_package(ROOT / "data/stories/continuity-initiative")


class _ScriptedProvider(ItemFactsProvider):
    def __init__(self, state: RuntimeState, replies: list[tuple[str, dict[str, object] | None]]) -> None:
        super().__init__(
            worker_url="",
            token="",
            state=state,
            item_facts={},
            mode="single_call",
            seed_from_package=True,
            held_by=True,
        )
        self.replies = replies
        self.narration_calls = 0
        self.rejections: list[tuple[str | None, str | None]] = []

    def __call__(self, _command: str) -> object:
        narration, item_facts = self.replies[self.narration_calls]
        self.narration_calls += 1
        self._pending_item_facts = copy.deepcopy(item_facts)
        self._pending_item_facts_present = item_facts is not None
        return {"segments": [{"kind": "narration", "text": narration}], "selected_knowledge_ids": []}

    def note_rejection(self, code: str | None, term: str | None = None) -> None:
        self.rejections.append((code, term))


def _capture(
    provider: _ScriptedProvider,
    scores: list[float | None],
    *,
    enforcing: bool = True,
    boarding: bool = False,
) -> tuple[WorldCapture, list[tuple[object, object]]]:
    asks: list[tuple[object, object]] = []

    def ask(state: object, questions: object) -> dict[str, dict[str, float]] | None:
        relation_calls = len([item for item in asks if isinstance(item[1], dict) and "relation_0" in item[1]])
        asks.append((state, questions))
        score = scores[min(relation_calls, len(scores) - 1)]
        if score is None:
            return None
        if not isinstance(questions, dict):
            return {}
        return {
            key: {
                "noul": 1.0
                if key == "same_or_part" or (boarding and key in {"boards_vehicle", "only_boards_vehicle"})
                else score
            }
            for key in questions
        }

    capture = WorldCapture(provider, ask)
    if enforcing:
        capture.enforcing_verifier = ObservationVerifier(ask)
    return capture, asks


def _observing_state() -> RuntimeState:
    return _state_at("outside_house", already_aboard=True)


def _observing_provider(state: RuntimeState, replies: list[tuple[str, dict[str, object] | None]]) -> _ScriptedProvider:
    provider = _ScriptedProvider(state, replies)
    provider.observe_automatically = False
    provider.observation_request = ObservationRequest("Inspect the truck.", "enter", "kristin_truck")
    return provider


def _provider_state_snapshot(provider: ItemFactsProvider) -> dict[str, object]:
    snapshot = _provider_snapshot(provider)
    for name in ("replies", "narration_calls", "rejections", "item_facts_match_calls"):
        snapshot.pop(name, None)
    return snapshot


def test_enforcement_off_never_previews_and_keeps_legacy_behavior(monkeypatch: pytest.MonkeyPatch) -> None:
    state = _observing_state()
    provider = _observing_provider(state, [("The truck is quiet.", None)])
    capture, _asks = _capture(provider, [0.0], enforcing=False)
    preview_calls: list[object] = []
    monkeypatch.setattr(capture, "preview_commit", lambda *args, **kwargs: preview_calls.append(args))

    result = RuntimeEngine(state, provider, capture=capture).turn("Inspect the truck.")

    assert result.narration == "The truck is quiet."
    assert preview_calls == []


def test_enforcement_off_does_not_snapshot_or_discard_on_provider_error(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    class FailingProvider(_ScriptedProvider):
        def __call__(self, _command: str) -> object:
            raise NarrationProviderError("narration failed", 503, "NARRATION_FAILED")

    state = _observing_state()
    provider = FailingProvider(state, [])
    provider.observe_automatically = False
    provider.observation_request = ObservationRequest("Inspect the truck.", "enter", "kristin_truck")
    capture, _asks = _capture(provider, [0.0], enforcing=False)
    calls: list[str] = []
    original_discard = capture.discard
    original_resume = capture.resume

    monkeypatch.setattr(capture, "context", lambda: calls.append("context") or {})
    monkeypatch.setattr(capture, "discard", lambda: calls.append("discard") or original_discard())
    monkeypatch.setattr(capture, "resume", lambda context: calls.append("resume") or original_resume(context))

    with pytest.raises(NarrationProviderError):
        RuntimeEngine(state, provider, capture=capture).turn("Inspect the truck.")

    assert calls == []


def test_accepted_preview_replays_item_facts_once(monkeypatch: pytest.MonkeyPatch) -> None:
    state = _observing_state()
    provider = _observing_provider(state, [("The laptop is visible.", {"notebook": {"place": "driver's seat"}})])
    capture, asks = _capture(provider, [1.0])
    match_calls: list[object] = []
    monkeypatch.setattr(
        CloudflareTurnProvider,
        "_request_item_facts",
        lambda _provider, payload: match_calls.append(payload) or {"same_as": {"notebook": "Kristin's laptop"}},
    )

    RuntimeEngine(state, provider, capture=capture).turn("Inspect the truck.")

    assert provider.narration_calls == 1
    assert len(match_calls) == 1
    fact_asks = [
        item for item in asks if isinstance(item[1], dict) and ("same_or_part" in item[1] or "relation_0" in item[1])
    ]
    assert len(fact_asks) == 2
    assert capture.last_after["observation_preview"]["accepted"] is True
    assert capture.last_after["observation_diverged"] is False
    assert world_for(PACKAGE, state.facts).parent("kristin_laptop") == "truck_driver_seat"


def test_rejected_preview_retries_and_does_not_commit_first_facts(monkeypatch: pytest.MonkeyPatch) -> None:
    state = _observing_state()
    provider = _observing_provider(
        state,
        [
            ("Nothing is shown.", {"Kristin's laptop": {"place": "driver's seat"}}),
            ("The laptop is visible.", {"Kristin's laptop": {"place": "passenger seat"}}),
        ],
    )
    capture, _asks = _capture(provider, [0.0, 1.0])
    match_calls: list[object] = []
    monkeypatch.setattr(
        CloudflareTurnProvider,
        "_request_item_facts",
        lambda _provider, payload: match_calls.append(payload) or {"same_as": {"notebook": "Kristin's laptop"}},
    )

    engine = RuntimeEngine(state, provider, capture=capture)
    engine.turn("Inspect the truck.")

    assert provider.narration_calls == 2
    assert provider.rejections == [("observation_unverified", None)]
    assert state.last_turn_delivery.guard_retry_used is True
    assert len(match_calls) <= 2
    assert "driver's seat" not in str(state.facts)
    assert engine.last_attempt is not None
    assert engine.last_attempt.outcome == "committed"


def test_rejected_twice_restores_state_provider_and_records_attempt(monkeypatch: pytest.MonkeyPatch) -> None:
    state = _observing_state()
    provider = _observing_provider(
        state,
        [
            ("Nothing is shown.", {"notebook": {"place": "driver's seat"}}),
            ("Still nothing.", {"notebook": {"place": "kitchen"}}),
        ],
    )
    capture, _asks = _capture(provider, [0.0, 0.0])
    monkeypatch.setattr(
        CloudflareTurnProvider,
        "_request_item_facts",
        lambda _provider, _payload: {"same_as": {"notebook": "Kristin's laptop"}},
    )
    before_state = state.snapshot()
    before_provider = _provider_state_snapshot(provider)

    with pytest.raises(ProposalValidationError) as caught:
        RuntimeEngine(state, provider, capture=capture).turn("Inspect the truck.")

    assert caught.value.code == "observation_unverified"
    assert provider.narration_calls == 2
    assert state.snapshot() == before_state
    assert _provider_state_snapshot(provider) == before_provider
    assert state.last_turn_delivery == before_state.last_turn_delivery
    assert capture.last_after is None


@pytest.mark.parametrize("score", [None, 0.5])
def test_unavailable_and_uncertain_verdicts_reject(monkeypatch: pytest.MonkeyPatch, score: float | None) -> None:
    state = _observing_state()
    provider = _observing_provider(
        state,
        [("No details.", {"notebook": {"place": "driver's seat"}}), ("No details.", None)],
    )
    capture, _asks = _capture(provider, [score, score])
    monkeypatch.setattr(
        CloudflareTurnProvider,
        "_request_item_facts",
        lambda _provider, _payload: {"same_as": {"notebook": "Kristin's laptop"}},
    )

    with pytest.raises(ProposalValidationError) as caught:
        RuntimeEngine(state, provider, capture=capture).turn("Inspect the truck.")

    assert caught.value.code == "observation_unverified"


def test_verifier_request_budget_is_per_attempt_and_resets(monkeypatch: pytest.MonkeyPatch) -> None:
    state = _observing_state()
    provider = _observing_provider(
        state,
        [
            ("The laptop is visible.", {"notebook": {"place": "driver's seat"}}),
            ("The laptop is visible.", {"notebook": {"place": "driver's seat"}}),
        ],
    )
    capture, asks = _capture(provider, [1.0])
    monkeypatch.setattr(
        CloudflareTurnProvider,
        "_request_item_facts",
        lambda _provider, _payload: {"same_as": {"notebook": "Kristin's laptop"}},
    )
    engine = RuntimeEngine(state, provider, capture=capture)

    engine.turn("Inspect the truck.")
    first_turn_requests = len([item for item in asks if isinstance(item[1], dict) and "relation_0" in item[1]])
    provider.observation_request = ObservationRequest("Inspect the truck.", "enter", "kristin_truck")
    engine.turn("Inspect the truck.")
    second_turn_requests = len([item for item in asks if isinstance(item[1], dict) and "relation_0" in item[1]])

    assert first_turn_requests == 1
    assert second_turn_requests == 2


def test_commit_divergence_rolls_back_everything(monkeypatch: pytest.MonkeyPatch) -> None:
    state = _observing_state()
    provider = _observing_provider(state, [("The laptop is visible.", {"notebook": {"place": "driver's seat"}})])
    capture, _asks = _capture(provider, [1.0])
    monkeypatch.setattr(
        CloudflareTurnProvider,
        "_request_item_facts",
        lambda _provider, _payload: {"same_as": {"notebook": "Kristin's laptop"}},
    )
    before_state = state.snapshot()
    before_provider = _provider_state_snapshot(provider)
    apply_item_facts = provider.apply_item_facts

    def diverging_apply(raw, **kwargs):
        result = apply_item_facts(raw, **kwargs)
        if provider.state is state:
            world_for(PACKAGE, state.facts).move("kristin_laptop", "kitchen")
        return result

    monkeypatch.setattr(provider, "apply_item_facts", diverging_apply)
    engine = RuntimeEngine(state, provider, capture=capture)

    with pytest.raises(ProposalValidationError) as caught:
        engine.turn("Inspect the truck.")

    assert caught.value.code == "observation_diverged"
    assert state.snapshot() == before_state
    assert _provider_state_snapshot(provider) == before_provider
    assert engine.last_attempt is not None
    assert engine.last_attempt.outcome == "rejected"
    assert engine.last_attempt.rejection.code == "observation_diverged"


def test_boarding_retry_seats_once_and_paces_once(monkeypatch: pytest.MonkeyPatch) -> None:
    state = _state_at("outside_house")
    provider = _ScriptedProvider(
        state,
        [
            ("Nothing is shown.", {"notebook": {"place": "passenger seat"}}),
            ("The truck is quiet.", {"notebook": {"place": "passenger seat"}}),
        ],
    )
    provider.observe_automatically = False
    provider.observation_request = ObservationRequest("Enter the truck.", "enter", "kristin_truck")
    capture, _asks = _capture(provider, [0.0, 1.0], boarding=True)
    monkeypatch.setattr(
        CloudflareTurnProvider,
        "_request_item_facts",
        lambda _provider, _payload: {"same_as": {"notebook": "Kristin's laptop"}},
    )
    engine = RuntimeEngine(state, provider, capture=capture)

    engine.turn("Enter the truck.")

    assert provider.narration_calls == 2
    assert world_for(PACKAGE, state.facts).parent("kristin") == "truck_driver_seat"
    assert state.turn_index == 1
    assert len(state.turn_records) == 1


def test_previewed_narration_is_passed_to_commit(monkeypatch: pytest.MonkeyPatch) -> None:
    state = _observing_state()
    provider = _observing_provider(state, [("The laptop is visible.", {"notebook": {"place": "driver's seat"}})])
    capture, _asks = _capture(provider, [1.0])
    monkeypatch.setattr(
        CloudflareTurnProvider,
        "_request_item_facts",
        lambda _provider, _payload: {"same_as": {"notebook": "Kristin's laptop"}},
    )
    received: list[str] = []
    original = capture.after_commit

    def wrapped(command: str, narration: str, *, entered_scene: bool):
        received.append(narration)
        return original(command, narration, entered_scene=entered_scene)

    monkeypatch.setattr(capture, "after_commit", wrapped)
    RuntimeEngine(state, provider, capture=capture).turn("Inspect the truck.")

    assert received == ["The laptop is visible."]


def test_preview_provider_error_is_an_operational_failure(monkeypatch: pytest.MonkeyPatch) -> None:
    state = _observing_state()
    provider = _observing_provider(state, [("The laptop is visible.", {"notebook": {"place": "driver's seat"}})])
    capture, _asks = _capture(provider, [1.0])
    before_state = state.snapshot()
    before_provider = _provider_state_snapshot(provider)

    def exhausted(*_args, **_kwargs):
        raise NarrationProviderError("item facts exhausted", 503, "ITEM_FACTS_REQUEST_BUDGET_EXHAUSTED")

    monkeypatch.setattr(provider, "apply_item_facts", exhausted)
    engine = RuntimeEngine(state, provider, capture=capture)

    with pytest.raises(NarrationProviderError):
        engine.turn("Inspect the truck.")

    assert state.snapshot() == before_state
    assert _provider_state_snapshot(provider) == before_provider
    assert engine.last_attempt is not None
    assert engine.last_attempt.outcome == "operational_failure"


def test_enforcing_verifier_without_observation_request_is_inert() -> None:
    state = _observing_state()
    provider = _observing_provider(state, [("The truck is quiet.", None)])
    provider.observation_request = None
    capture, asks = _capture(provider, [0.0])

    RuntimeEngine(state, provider, capture=capture).turn("Inspect the truck.")

    assert not [item for item in asks if isinstance(item[1], dict) and "relation_0" in item[1]]
    assert "observation_preview" not in capture.last_after


@pytest.mark.parametrize(
    ("scores", "expected_calls", "raises"),
    [([1.0], 1, False), ([0.0, 1.0], 2, False), ([0.0, 0.0], 2, True)],
)
def test_synthetic_story_accepts_and_rejects_with_same_two_attempt_cap(
    monkeypatch: pytest.MonkeyPatch,
    scores: list[float],
    expected_calls: int,
    raises: bool,
) -> None:
    state = RuntimeState.bootstrap(_synthetic_package())
    provider = _ScriptedProvider(
        state,
        [
            ("The calibrated lens catches the light.", {"calibrated lens": {"place": "survey tray"}})
            for _ in range(expected_calls)
        ],
    )
    provider.observe_automatically = False
    provider.observation_request = ObservationRequest("Inspect the survey tray.", "look", "tray")
    capture, _asks = _capture(provider, scores)
    engine = RuntimeEngine(state, provider, capture=capture)
    monkeypatch.setattr(engine.narration_validator, "validate", lambda *_args: None)

    if raises:
        with pytest.raises(ProposalValidationError) as caught:
            engine.turn("Inspect the survey tray.")
        assert caught.value.code == "observation_unverified"
    else:
        engine.turn("Inspect the survey tray.")

    assert provider.narration_calls == expected_calls
