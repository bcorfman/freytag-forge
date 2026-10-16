"""Stage 4 reproduction for a follow-up command missing a recently introduced referent."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from storygame.runtime.cloudflare import CloudflareTurnProvider
from storygame.runtime.engine import RuntimeEngine
from storygame.runtime.state import RuntimeState
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


def _has_fact(state: RuntimeState, fact_id: str) -> bool:
    return any(fact.predicate == fact_id and fact.value == "true" for fact in state.facts.asserted)


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


def _engine(monkeypatch: pytest.MonkeyPatch, state: RuntimeState) -> RuntimeEngine:
    monkeypatch.setattr("storygame.runtime.cloudflare.urlopen", _normal_response)
    provider = CloudflareTurnProvider(worker_url="https://worker.example/turn", token="", state=state)
    return RuntimeEngine(state, provider)


@pytest.mark.parametrize("semantic", ("0", "1"))
def test_explicit_owner_follow_up_earns_memory_card(monkeypatch: pytest.MonkeyPatch, semantic: str) -> None:
    monkeypatch.setenv("FREYTAG_SEMANTIC_REVEAL", semantic)
    state = _state()
    engine = _engine(monkeypatch, state)

    first = engine.turn("Open the drawer.")
    second = engine.turn("Search the gap beneath the drawer.")

    assert first.selected_knowledge_ids == (POINTER_REVEAL,)
    assert second.selected_knowledge_ids == (CARD_REVEAL,)
    assert _has_fact(state, "memory_card_recovered")


@pytest.mark.parametrize("semantic", ("0", "1"))
def test_gap_without_prior_cue_earns_nothing(monkeypatch: pytest.MonkeyPatch, semantic: str) -> None:
    monkeypatch.setenv("FREYTAG_SEMANTIC_REVEAL", semantic)
    state = _state()
    result = _engine(monkeypatch, state).turn("Search the gap.")

    assert result.selected_knowledge_ids == ()
    assert not _has_fact(state, "memory_card_recovered")


@pytest.mark.parametrize("semantic", ("0", "1"))
@pytest.mark.parametrize("command", ("Search the gap.", "Feel along the gap.", "Check the gap."))
@pytest.mark.xfail(strict=True, reason="Stage 4: no recent-cue referent projection yet")
def test_recent_cue_referent_follow_up_earns_memory_card(
    monkeypatch: pytest.MonkeyPatch, semantic: str, command: str
) -> None:
    monkeypatch.setenv("FREYTAG_SEMANTIC_REVEAL", semantic)
    state = _state()
    engine = _engine(monkeypatch, state)

    engine.turn("Open the drawer.")
    result = engine.turn(command)

    assert result.selected_knowledge_ids == (CARD_REVEAL,)
    assert _has_fact(state, "memory_card_recovered")


@pytest.mark.parametrize("semantic", ("0", "1"))
def test_unrelated_follow_up_does_not_use_recent_cue(monkeypatch: pytest.MonkeyPatch, semantic: str) -> None:
    monkeypatch.setenv("FREYTAG_SEMANTIC_REVEAL", semantic)
    state = _state()
    engine = _engine(monkeypatch, state)

    engine.turn("Open the drawer.")
    result = engine.turn("Read the receipt.")

    assert result.selected_knowledge_ids == ()
    assert not _has_fact(state, "memory_card_recovered")


@pytest.mark.parametrize("semantic", ("0", "1"))
def test_unrelated_referent_never_resolves(monkeypatch: pytest.MonkeyPatch, semantic: str) -> None:
    monkeypatch.setenv("FREYTAG_SEMANTIC_REVEAL", semantic)
    state = _state()
    engine = _engine(monkeypatch, state)

    engine.turn("Open the drawer.")
    result = engine.turn("Search the kitchen.")

    assert result.selected_knowledge_ids == (KITCHEN_REVEAL,)
    assert not _has_fact(state, "memory_card_recovered")
