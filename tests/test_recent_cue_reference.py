"""Stage 4 reproduction for a follow-up command missing a recently introduced referent."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from storygame.runtime.capture import WorldCapture
from storygame.runtime.cloudflare import CloudflareTurnProvider
from storygame.runtime.engine import RuntimeEngine
from storygame.runtime.facts import Fact
from storygame.runtime.item_facts import ItemFactsProvider
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


def _engine(
    monkeypatch: pytest.MonkeyPatch,
    state: RuntimeState,
    captured: list[dict[str, object]] | None = None,
    *,
    with_capture: bool = False,
) -> RuntimeEngine:
    def transport(request: object, **kwargs: object) -> _Response:
        if captured is not None:
            captured.append(json.loads(request.data))
        return _normal_response(request, **kwargs)

    monkeypatch.setattr("storygame.runtime.cloudflare.urlopen", transport)
    if not with_capture:
        provider = CloudflareTurnProvider(worker_url="https://worker.example/turn", token="", state=state)
        return RuntimeEngine(state, provider)
    provider = ItemFactsProvider(
        worker_url="https://worker.example/turn",
        token="",
        state=state,
        item_facts={},
        mode="single_call",
        seed_from_package=True,
        held_by=True,
    )
    capture = WorldCapture(provider, lambda _state, questions: {next(iter(questions)): True})
    return RuntimeEngine(state, provider, capture=capture)


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
@pytest.mark.parametrize("command", ("Feel in the gap.", "Search the gap."))
def test_staged_cue_referent_follow_up_earns_memory_card(
    monkeypatch: pytest.MonkeyPatch, semantic: str, command: str
) -> None:
    monkeypatch.setenv("FREYTAG_SEMANTIC_REVEAL", semantic)
    state = _state()
    engine = _engine(monkeypatch, state)

    first = engine.turn("Go in the house.")
    cue_text = next(item.cue_text for item in PACKAGE.deliveries if item.fact_id == "continuity_initiative_known")
    result = engine.turn(command)

    assert first.selected_knowledge_ids == ()
    assert cue_text in tuple(segment.text for segment in first.segments)
    assert state.cue_stages[-1].last_turn == state.turn_index - 1
    assert result.selected_knowledge_ids == (CARD_REVEAL,)
    assert _has_fact(state, "memory_card_recovered")


def test_recent_cue_owner_is_rendered_in_the_narrator_player_line(monkeypatch: pytest.MonkeyPatch) -> None:
    captured: list[dict[str, object]] = []
    state = _state()
    engine = _engine(monkeypatch, state, captured, with_capture=True)

    engine.turn("Go in the house.")
    engine.turn("Feel in the gap.")

    assert captured[-1]["user"].endswith("- Feel in the gap. (meaning the drawer)")


@pytest.mark.parametrize("command", ("Search the kitchen.", "Look around."))
def test_unresolved_recent_cue_keeps_the_plain_narrator_player_line(
    monkeypatch: pytest.MonkeyPatch, command: str
) -> None:
    captured: list[dict[str, object]] = []
    state = _state()
    engine = _engine(monkeypatch, state, captured, with_capture=True)

    engine.turn("Go in the house.")
    engine.turn(command)

    assert captured[-1]["user"].endswith(f"- {command}")
    assert "(meaning the " not in captured[-1]["user"]


@pytest.mark.parametrize("semantic", ("0", "1"))
@pytest.mark.parametrize("command", ("Search the gap.", "Feel along the gap.", "Check the gap."))
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

    first = engine.turn("Go in the house.")
    result = engine.turn("Read the receipt.")

    assert first.selected_knowledge_ids == ()
    assert result.selected_knowledge_ids == ()
    assert not _has_fact(state, "memory_card_recovered")


@pytest.mark.parametrize("semantic", ("0", "1"))
def test_unrelated_referent_never_resolves(monkeypatch: pytest.MonkeyPatch, semantic: str) -> None:
    monkeypatch.setenv("FREYTAG_SEMANTIC_REVEAL", semantic)
    state = _state()
    engine = _engine(monkeypatch, state)

    first = engine.turn("Go in the house.")
    result = engine.turn("Search the kitchen.")

    assert first.selected_knowledge_ids == ()
    assert result.selected_knowledge_ids == (KITCHEN_REVEAL,)
    assert not _has_fact(state, "memory_card_recovered")


@pytest.mark.parametrize("semantic", ("0", "1"))
def test_staged_cue_referent_expires_after_unrelated_turn(monkeypatch: pytest.MonkeyPatch, semantic: str) -> None:
    monkeypatch.setenv("FREYTAG_SEMANTIC_REVEAL", semantic)
    state = _state()
    engine = _engine(monkeypatch, state)

    first = engine.turn("Go in the house.")
    unrelated = engine.turn("Search the kitchen.")
    result = engine.turn("Feel in the gap.")

    assert first.selected_knowledge_ids == ()
    assert unrelated.selected_knowledge_ids == (KITCHEN_REVEAL,)
    assert result.selected_knowledge_ids == ()
    assert not _has_fact(state, "memory_card_recovered")


@pytest.mark.parametrize("semantic", ("0", "1"))
def test_staged_cue_does_not_select_recovered_card(monkeypatch: pytest.MonkeyPatch, semantic: str) -> None:
    monkeypatch.setenv("FREYTAG_SEMANTIC_REVEAL", semantic)
    state = _state()
    engine = _engine(monkeypatch, state)

    first = engine.turn("Go in the house.")
    state.facts.assert_fact(Fact(predicate="memory_card_recovered", subject="story", value="true"))
    result = engine.turn("Feel in the gap.")

    assert first.selected_knowledge_ids == ()
    assert result.selected_knowledge_ids == ()
