from __future__ import annotations

import json
from pathlib import Path

import pytest

from storygame.runtime.cloudflare import CloudflareTurnProvider
from storygame.runtime.engine import RuntimeEngine
from storygame.runtime.state import RuntimeState
from storygame.runtime.world_model import apply_scene_placements
from storygame.story_package.loader import load_story_package
from storygame.story_source.lookup import story_text

PACKAGE = load_story_package(Path("data/stories/continuity-initiative"))
WARNING = "The shift supervisor checks the time on his tablet. He is waiting for an answer."


class _Response:
    def __init__(self, payload: object) -> None:
        self.payload = payload

    def __enter__(self) -> _Response:
        return self

    def __exit__(self, *_args: object) -> None:
        return None

    def read(self) -> bytes:
        return json.dumps(self.payload).encode()


def _state() -> RuntimeState:
    state = RuntimeState.bootstrap(PACKAGE)
    state.current_scene_id = "2A"
    state.phase = next(scene.metadata.freytag_phase for scene in PACKAGE.scenes if scene.metadata.scene_id == "2A")
    state._assert_scene_entry_fact("2A")
    assert apply_scene_placements(PACKAGE, state.facts, "2A") == ()
    return state


def _payload(text: str = "Kristin studies the gate.", selected: tuple[str, ...] = ()) -> dict[str, str]:
    return {
        "narration": json.dumps(
            {
                "segments": [{"kind": "narration", "text": text, "grounding_ids": list(selected)}],
                "selected_knowledge_ids": list(selected),
            }
        )
    }


def _engine(monkeypatch: pytest.MonkeyPatch, state: RuntimeState, payloads: list[dict[str, str]]) -> RuntimeEngine:
    responses = iter(payloads)
    monkeypatch.setattr(
        "storygame.runtime.cloudflare.urlopen",
        lambda *_args, **_kwargs: _Response(next(responses)),
    )
    provider = CloudflareTurnProvider(worker_url="https://worker.example/turn", token="", state=state)
    return RuntimeEngine(state, provider)


def _texts(result: object) -> tuple[str, ...]:
    return tuple(segment.text for segment in result.segments)


def _has_true_fact(state: RuntimeState, fact_id: str) -> bool:
    return any(fact.predicate == fact_id and fact.value == "true" for fact in state.facts.asserted)


def test_supervisor_warning_fires_at_turn_three_once_and_not_again(monkeypatch: pytest.MonkeyPatch) -> None:
    state = _state()
    engine = _engine(monkeypatch, state, [_payload() for _ in range(5)])

    first = engine.turn("Read the alarm log.")
    second = engine.turn("Ask Brandon about the badges.")
    assert WARNING not in _texts(first)
    assert WARNING not in _texts(second)
    assert not _has_true_fact(state, "supervisor_impatient")

    third = engine.turn("Inspect the gate.")
    assert state.turn_index - state.scene_entered_at_turn == 3
    assert _texts(third).count(WARNING) == 1
    assert _has_true_fact(state, "supervisor_impatient")

    fourth = engine.turn("Study the facility gate.")
    fifth = engine.turn("Check the supervisor's tablet.")
    assert WARNING not in _texts(fourth)
    assert WARNING not in _texts(fifth)


def test_quick_diagnosis_leaves_before_supervisor_warning(monkeypatch: pytest.MonkeyPatch) -> None:
    state = _state()
    engine = _engine(
        monkeypatch,
        state,
        [
            _payload(story_text("claim:k_sl_2a_b_r1.text", package=PACKAGE), ("k_sl_2a_b_r1",)),
            _payload(story_text("claim:k_sl_2a_c_r5.text", package=PACKAGE), ("k_sl_2a_c_r5",)),
        ],
    )

    first = engine.turn("Feel the cooling lines at the manifold.")
    second = engine.turn("Explain the pressure fault and the ventilation problem to the supervisor.")

    assert state.turn_index == 2
    assert state.current_scene_id == "2B"
    assert not _has_true_fact(state, "supervisor_impatient")
    assert WARNING not in (*_texts(first), *_texts(second))
