"""Hermetic tests for the committed recent-cue evidence bridge."""

from __future__ import annotations

import json
from pathlib import Path
from types import SimpleNamespace

import pytest

from storygame.runtime.cloudflare import CloudflareTurnProvider
from storygame.runtime.engine import RuntimeEngine
from storygame.runtime.recent_cue import recent_cue_referent_text
from storygame.runtime.state import RuntimeState
from storygame.runtime.validation import ProposalValidationError
from storygame.story_package.loader import load_story_package

PACKAGE = load_story_package(Path("data/stories/continuity-initiative"))
CARD_REVEAL = "k_sl_1a_b_r0"
POINTER_REVEAL = "k_sl_1a_f_r1"
KITCHEN_REVEAL = "k_sl_1a_a_r1"


class _Response:
    def __init__(self, body: object) -> None:
        self.body = json.dumps(body).encode()

    def __enter__(self) -> _Response:
        return self

    def __exit__(self, *_args: object) -> None:
        return None

    def read(self) -> bytes:
        return self.body


def _state() -> RuntimeState:
    state = RuntimeState.bootstrap(PACKAGE)
    state.active_event_ids.update({"SL-1A-E", "SL-1A-F"})
    return state


def _normal_response(_request: object, **_kwargs: object) -> _Response:
    return _Response(
        {
            "narration": json.dumps(
                {
                    "segments": [{"kind": "narration", "text": "Kristin looks at the gap."}],
                    "selected_knowledge_ids": [],
                }
            )
        }
    )


def _has_fact(state: RuntimeState, fact_id: str) -> bool:
    return any(fact.predicate == fact_id and fact.value == "true" for fact in state.facts.asserted)


def _engine(monkeypatch: pytest.MonkeyPatch, state: RuntimeState) -> tuple[RuntimeEngine, CloudflareTurnProvider]:
    monkeypatch.setattr("storygame.runtime.cloudflare.urlopen", _normal_response)
    provider = CloudflareTurnProvider(worker_url="https://worker.example/turn", token="", state=state)
    return RuntimeEngine(state, provider), provider


def _cue_state(monkeypatch: pytest.MonkeyPatch) -> tuple[RuntimeState, RuntimeEngine, CloudflareTurnProvider]:
    monkeypatch.setenv("FREYTAG_SEMANTIC_REVEAL", "0")
    state = _state()
    engine, provider = _engine(monkeypatch, state)
    engine.turn("Open the drawer.")
    return state, engine, provider


def test_accepted_unrelated_turn_expires_cue(monkeypatch: pytest.MonkeyPatch) -> None:
    state, engine, _provider = _cue_state(monkeypatch)

    engine.turn("Read the receipt.")
    result = engine.turn("Search the gap.")

    assert result.selected_knowledge_ids == ()
    assert state.turn_records[-1].reveal_ids == ()


def test_rejected_turn_does_not_expire_cue(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("FREYTAG_SEMANTIC_REVEAL", "0")
    state = _state()
    rejected = _Response(
        {
            "narration": json.dumps(
                {
                    "segments": [{"kind": "narration", "text": "The memory card is recovered."}],
                    "selected_knowledge_ids": [],
                }
            )
        }
    )
    responses = iter([_normal_response(None), rejected, rejected, _normal_response(None)])

    def next_response(_request: object, **_kwargs: object) -> _Response:
        return next(responses)

    monkeypatch.setattr("storygame.runtime.cloudflare.urlopen", next_response)
    provider = CloudflareTurnProvider(worker_url="https://worker.example/turn", token="", state=state)
    engine = RuntimeEngine(state, provider)
    engine.turn("Open the drawer.")
    record_count = len(state.turn_records)

    with pytest.raises(ProposalValidationError):
        engine.turn("Read the receipt.")

    assert len(state.turn_records) == record_count
    result = engine.turn("Search the gap.")

    assert result.selected_knowledge_ids == (CARD_REVEAL,)


def test_scene_change_expires_cue(monkeypatch: pytest.MonkeyPatch) -> None:
    state, _engine, _provider = _cue_state(monkeypatch)
    target = next(scene for scene in PACKAGE.scenes if scene.metadata.scene_id == "1B")
    state.current_scene_id = target.metadata.scene_id
    state.phase = target.metadata.freytag_phase
    state.scene_entered_at_turn = state.turn_index

    assert recent_cue_referent_text(state, "Search the gap.") == ""


def test_ambiguous_cue_owner_returns_empty() -> None:
    kristin = SimpleNamespace(id="kristin", name="Kristin", aliases=(), scoped_aliases=())
    drawer = SimpleNamespace(id="drawer", name="drawer", aliases=(), scoped_aliases=())
    receipt = SimpleNamespace(id="receipt", name="receipt", aliases=(), scoped_aliases=())
    package = SimpleNamespace(
        world=SimpleNamespace(
            protagonist_id="kristin", locations=(), npcs=(kristin,), groups=(), items=(drawer, receipt)
        ),
        knowledge_indexes=SimpleNamespace(
            by_id={
                "cue": SimpleNamespace(
                    delivery_text="A gap runs beneath the drawer.", entity_ids=("kristin", "drawer", "receipt")
                )
            }
        ),
    )
    state = SimpleNamespace(
        package=package,
        turn_records=(SimpleNamespace(id="turn_1", reveal_ids=("cue",)),),
        turn_index=1,
        scene_entered_at_turn=0,
    )

    assert recent_cue_referent_text(state, "Search the gap.") == ""


def test_owner_already_named_returns_empty(monkeypatch: pytest.MonkeyPatch) -> None:
    state, _engine, _provider = _cue_state(monkeypatch)

    assert recent_cue_referent_text(state, "Search the gap beneath the drawer.") == ""


def test_no_shared_content_word_returns_empty(monkeypatch: pytest.MonkeyPatch) -> None:
    state, _engine, _provider = _cue_state(monkeypatch)

    assert recent_cue_referent_text(state, "Read the receipt.") == ""


def test_exact_negatives_keep_their_existing_targets(monkeypatch: pytest.MonkeyPatch) -> None:
    state, engine, _provider = _cue_state(monkeypatch)
    explicit = engine.turn("Search the gap beneath the drawer.")
    assert explicit.selected_knowledge_ids == (CARD_REVEAL,)

    state, engine, _provider = _cue_state(monkeypatch)
    wrong_target = engine.turn("Search the kitchen.")
    assert wrong_target.selected_knowledge_ids == (KITCHEN_REVEAL,)
    assert not _has_fact(state, "memory_card_recovered")


def test_cue_word_does_not_grant_reveal_without_action_evidence(monkeypatch: pytest.MonkeyPatch) -> None:
    _state_value, engine, _provider = _cue_state(monkeypatch)

    result = engine.turn("Smell the gap.")

    assert result.selected_knowledge_ids == ()


def test_snapshot_after_cue_preserves_referent(monkeypatch: pytest.MonkeyPatch) -> None:
    state, _, _provider = _cue_state(monkeypatch)
    snapshot = state.snapshot()
    restored = RuntimeState.bootstrap(PACKAGE)
    restored.restore_snapshot(snapshot)
    engine, _provider = _engine(monkeypatch, restored)

    result = engine.turn("Search the gap.")

    assert result.selected_knowledge_ids == (CARD_REVEAL,)


def test_snapshot_before_cue_has_no_referent(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("FREYTAG_SEMANTIC_REVEAL", "0")
    state = _state()
    snapshot = state.snapshot()
    engine, _provider = _engine(monkeypatch, state)
    engine.turn("Open the drawer.")
    restored = RuntimeState.bootstrap(PACKAGE)
    restored.restore_snapshot(snapshot)

    assert recent_cue_referent_text(restored, "Search the gap.") == ""
    engine, _provider = _engine(monkeypatch, restored)
    result = engine.turn("Search the gap.")

    assert result.selected_knowledge_ids == ()


def test_provider_records_recent_cue_telemetry(monkeypatch: pytest.MonkeyPatch) -> None:
    state, _engine, provider = _cue_state(monkeypatch)

    provider.assemble_turn_prompt("Search the gap.")

    assert provider.last_reveal_selection["recent_cue_owner"] == "drawer"
