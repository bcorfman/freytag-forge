"""Regression coverage for the authored Scene 1A pacing clock."""

from __future__ import annotations

import json
from pathlib import Path

from storygame.runtime.cloudflare import CloudflareTurnProvider
from storygame.runtime.engine import RuntimeEngine
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
NARROWS_TEXT = (
    "The patrol is checking parked vehicles and speaking to neighbors. "
    "The house is no longer the only place under watch."
)
RETURNING_TEXT = "The patrol is coming back to the house."


class _Response:
    def __init__(self, payload: object) -> None:
        self.payload = payload

    def __enter__(self) -> _Response:
        return self

    def __exit__(self, *_args: object) -> None:
        return None

    def read(self) -> bytes:
        return json.dumps(self.payload).encode()


def test_scene_1a_clock_delivers_trailing_patrol_timeline(monkeypatch) -> None:
    parents_at_narrator_request: list[str | None] = []
    state = RuntimeState.bootstrap(PACKAGE)

    def open_request(request, **_kwargs: object) -> _Response:
        del request
        parents_at_narrator_request.append(world_for(PACKAGE, state.facts).parent("patrol_officer"))
        return _Response({"narration": '{"segments":[{"kind":"narration","text":"The house remains quiet."}]}'})

    monkeypatch.setattr("storygame.runtime.cloudflare.urlopen", open_request)
    engine = RuntimeEngine(
        state,
        CloudflareTurnProvider(worker_url="https://worker.example/turn", token="", state=state),
    )

    window = next(window for window in PACKAGE.pacing.scenes if window.scene_id == "1A")
    assert (window.min_turns, window.nudge_after_turns, window.handoff_after_turns) == (13, 14, 15)
    events = {event.id: event for event in PACKAGE.pacing.events if event.scene_id == "1A"}
    assert {
        event_id: events[event_id].at_turn
        for event_id in (
            "patrol_arrives_1a",
            "patrol_enters_1a",
            "patrol_leaves_1a",
            "home_search_narrows_1a",
            "patrol_returns_1a",
        )
    } == {
        "patrol_arrives_1a": 6,
        "patrol_enters_1a": 7,
        "patrol_leaves_1a": 10,
        "home_search_narrows_1a": 11,
        "patrol_returns_1a": 13,
    }
    assert all(events[event_id].trailing for event_id in ("patrol_arrives_1a", "patrol_enters_1a", "patrol_leaves_1a"))

    deliveries: dict[int, tuple[str, ...]] = {}
    complications: dict[int, str | None] = {}
    for turn in range(1, 14):
        proposal = engine.turn("Wait and observe.")
        deliveries[turn] = tuple(segment.text for segment in proposal.segments)
        complications[turn] = state.last_turn_delivery.complication_text

    assert parents_at_narrator_request[6] == "outside_house"
    assert parents_at_narrator_request[7:10] == ["kitchen", "kitchen", "kitchen"]
    assert parents_at_narrator_request[10] == "patrol_staging"
    assert deliveries[6][-1] == ARRIVAL_TEXT
    assert deliveries[7][-1] == ENTERING_TEXT
    assert deliveries[10][-1] == LEAVING_TEXT
    assert sum(text == ARRIVAL_TEXT for texts in deliveries.values() for text in texts) == 1
    assert sum(text == ENTERING_TEXT for texts in deliveries.values() for text in texts) == 1
    assert sum(text == LEAVING_TEXT for texts in deliveries.values() for text in texts) == 1
    assert complications[11] == NARROWS_TEXT
    assert complications[13] == RETURNING_TEXT
