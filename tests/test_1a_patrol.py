"""Scene 1A patrol timing, grounding, and persistence contract."""

from __future__ import annotations

import json
import re
from pathlib import Path

from storygame.runtime.cloudflare import CloudflareTurnProvider
from storygame.runtime.engine import RuntimeEngine
from storygame.runtime.facts import Fact
from storygame.runtime.state import RuntimeState
from storygame.runtime.world_model import world_for
from storygame.story_package.loader import load_story_package

PACKAGE = load_story_package(Path("data/stories/continuity-initiative"))
ARRIVAL_TEXT = (
    "A federal emergency patrol pulls up outside Michelle's house. Two officers get out. "
    "One walks to the front door. The other looks over the street."
)
ENTERING_TEXT = "The front door opens. An officer walks in and heads straight for Michelle's workstation."
LEAVING_TEXT = "The patrol pulls away from the curb."
RETURNING_TEXT = "The patrol is coming back to the house."
DEFAULT_RETURN_TEXT = "A federal emergency patrol turns onto Michelle's street."


class _Response:
    def __init__(self, payload: object) -> None:
        self.payload = payload

    def __enter__(self) -> _Response:
        return self

    def __exit__(self, *_args: object) -> None:
        return None

    def read(self) -> bytes:
        return json.dumps(self.payload).encode()


def _neutral_provider(_command: str) -> dict[str, object]:
    return {"segments": [{"kind": "narration", "text": "The house remains quiet."}]}


def _texts(proposal: object) -> tuple[str, ...]:
    return tuple(segment.text for segment in proposal.segments)


def _has_fact(state: RuntimeState, fact_id: str, value: bool) -> bool:
    expected = str(value).lower()
    return Fact(predicate=fact_id, subject="story", value=expected) in state.facts.asserted


def test_scene_1a_patrol_is_a_fact_driven_placed_timeline(monkeypatch) -> None:
    prompts: list[str] = []

    def open_request(request, **_kwargs: object) -> _Response:
        prompts.append(request.data.decode())
        return _Response({"narration": '{"segments":[{"kind":"narration","text":"The house remains quiet."}]}'})

    monkeypatch.setattr("storygame.runtime.cloudflare.urlopen", open_request)
    state = RuntimeState.bootstrap(PACKAGE)
    assert world_for(PACKAGE, state.facts).parent("patrol_officer") is None
    engine = RuntimeEngine(
        state,
        CloudflareTurnProvider(worker_url="https://worker.example/turn", token="", state=state),
    )
    player_text: list[str] = []

    for turn in range(1, 10):
        proposal = engine.turn("Wait and observe.")
        player_text.extend(_texts(proposal))
        if turn < 4:
            assert not re.search(r"\b(officer|patrol)\b", prompts[turn - 1], re.IGNORECASE)
            assert not any(re.search(r"\b(officer|patrol)\b", text, re.IGNORECASE) for text in _texts(proposal))

        if turn < 7:
            assert not any(re.search(r"\b(back|return|again)\b", text, re.IGNORECASE) for text in _texts(proposal))

        if turn == 4:
            assert _texts(proposal).count(ARRIVAL_TEXT) == 1
            assert _has_fact(state, "patrol_on_scene", True)
            assert world_for(PACKAGE, state.facts).parent("patrol_officer") == "outside_house"
        if turn == 5:
            assert _texts(proposal).count(ENTERING_TEXT) == 1
            assert _has_fact(state, "patrol_in_house", True)
            assert world_for(PACKAGE, state.facts).parent("patrol_officer") == "kitchen"
        if turn == 7:
            assert _texts(proposal).count(LEAVING_TEXT) == 1
            assert _has_fact(state, "patrol_departed", True)
            assert _has_fact(state, "patrol_on_scene", False)
            assert _has_fact(state, "patrol_in_house", False)
            assert world_for(PACKAGE, state.facts).parent("patrol_officer") == "patrol_staging"
        if turn == 9:
            assert state.last_turn_delivery.complication_text == RETURNING_TEXT

    assert player_text.count(ARRIVAL_TEXT) == 1
    assert player_text.count(ENTERING_TEXT) == 1
    assert player_text.count(LEAVING_TEXT) == 1


def test_scene_1a_patrol_return_uses_default_without_departure() -> None:
    state = RuntimeState.bootstrap(PACKAGE)
    state.turn_index = 8
    state.fired_event_ids.update({"patrol_arrives_1a", "patrol_enters_1a", "patrol_leaves_1a"})
    state.facts.assert_fact(Fact(predicate="patrol_return_pressure", subject="story", value="true"))

    engine = RuntimeEngine(state, _neutral_provider)
    engine.turn("Wait and observe.")

    assert state.last_turn_delivery.complication_text == DEFAULT_RETURN_TEXT


def test_scene_1a_patrol_snapshot_restores_facts_and_placement() -> None:
    state = RuntimeState.bootstrap(PACKAGE)
    engine = RuntimeEngine(state, _neutral_provider)
    for _ in range(5):
        engine.turn("Wait and observe.")

    snapshot = state.snapshot()
    expected_facts = state.facts.asserted
    expected_parent = world_for(PACKAGE, state.facts).parent("patrol_officer")
    restored = RuntimeState.bootstrap(PACKAGE)
    restored.restore_snapshot(snapshot)

    assert restored.facts.asserted == expected_facts
    assert world_for(PACKAGE, restored.facts).parent("patrol_officer") == expected_parent == "kitchen"
