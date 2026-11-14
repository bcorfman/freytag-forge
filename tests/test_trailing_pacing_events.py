"""Trailing pacing-event contracts for the scene 1A patrol."""

from __future__ import annotations

import json
import shutil
from pathlib import Path

import pytest

from storygame.runtime.cloudflare import CloudflareTurnProvider
from storygame.runtime.engine import RuntimeEngine
from storygame.runtime.state import RuntimeState
from storygame.runtime.world_model import world_for
from storygame.story_package.loader import load_story_package
from storygame.story_package.models import PacingEvent

PACKAGE_DIR = Path(__file__).parents[1] / "data/stories/continuity-initiative"
ARRIVAL_TEXT = (
    "A federal emergency patrol pulls up outside Michelle's house. Two officers get out. "
    "One walks to the front door. The other looks over the street."
)
LEAVING_TEXT = "The patrol pulls away from the curb."
ENTERING_TEXT = "The front door opens. An officer walks in and heads straight for Michelle's workstation."
COMMANDS = (
    "Turn on the phone.",
    "Unlock the phone.",
    "Type in the password.",
    "Type the password into Michelle's phone.",
    "Turn off the phone.",
    "Greet the officer.",
    "Ask the officer where Dr. McGehee is.",
    "Wait and observe.",
    "Wait and observe.",
    "Wait and observe.",
)


class _Response:
    def __init__(self, payload: object) -> None:
        self.payload = payload

    def __enter__(self) -> _Response:
        return self

    def __exit__(self, *_args: object) -> None:
        return None

    def read(self) -> bytes:
        return json.dumps(self.payload).encode()


def _variant_package(tmp_path: Path, event_id: str, trailing: str) -> object:
    package_dir = tmp_path / f"continuity-{event_id}"
    shutil.copytree(PACKAGE_DIR, package_dir)
    pacing_path = package_dir / "pacing.yaml"
    pacing = pacing_path.read_text()
    anchor = f"- id: {event_id}\n  scene_id: 1A"
    assert pacing.count(anchor) == 1
    flagged = f"{anchor}\n  trailing: true"
    assert pacing.count(flagged) == 1
    if trailing == "false":
        pacing = pacing.replace(flagged, anchor)
    else:
        pacing = pacing.replace(flagged, f"{anchor}\n  trailing: {trailing}")
    pacing_path.write_text(pacing)
    # These tests watch the world the opening request sees, so scene 1A must ask the provider.
    plot_path = package_dir / "plot.md"
    plot_path.write_text(plot_path.read_text().replace("scripted_opening: true\n", "", 1))
    return load_story_package(package_dir)


def _run_commands(monkeypatch, package: object, turns: int = 10) -> tuple[RuntimeState, list[str], list[object]]:
    state = RuntimeState.bootstrap(package)
    observations: list[str] = []

    def open_request(_request, **_kwargs: object) -> _Response:
        observations.append(world_for(package, state.facts).parent("patrol_officer"))
        return _Response({"narration": '{"segments":[{"kind":"narration","text":"The house remains quiet."}]}'})

    monkeypatch.setattr("storygame.runtime.cloudflare.urlopen", open_request)
    engine = RuntimeEngine(
        state,
        CloudflareTurnProvider(worker_url="https://worker.example/turn", token="", state=state),
    )
    engine.opening()
    proposals: list[object] = []
    for command in COMMANDS[:turns]:
        proposals.append(engine.turn(command, clock_seconds=1))
    return state, observations, proposals


def _texts(proposal: object) -> tuple[str, ...]:
    return tuple(segment.text for segment in proposal.segments)


def test_pacing_event_trailing_defaults_to_false_control() -> None:
    package = load_story_package(PACKAGE_DIR)
    events = {event.id: event for event in package.pacing.events}
    assert all(
        events[event_id].trailing is False
        for event_id in ("officer_presses_1a", "home_search_narrows_1a", "patrol_returns_1a")
    )
    assert PacingEvent.model_fields["trailing"].default is False


def test_pacing_event_accepts_trailing_true(tmp_path: Path) -> None:
    package = _variant_package(tmp_path, "patrol_leaves_1a", "true")
    event = next(event for event in package.pacing.events if event.id == "patrol_leaves_1a")
    assert event.trailing is True


def test_pacing_event_rejects_non_boolean_trailing(tmp_path: Path) -> None:
    with pytest.raises(ValueError, match=r"(?is)trailing.*boolean|boolean.*trailing"):
        _variant_package(tmp_path, "patrol_leaves_1a", "maybe")


def test_trailing_departure_request_sees_pre_event_world(tmp_path: Path, monkeypatch) -> None:
    package = _variant_package(tmp_path, "patrol_leaves_1a", "true")
    _state, observations, _proposals = _run_commands(monkeypatch, package)
    assert observations[10] == "kitchen"


def test_trailing_departure_commits_and_appends_text_once(tmp_path: Path, monkeypatch) -> None:
    package = _variant_package(tmp_path, "patrol_leaves_1a", "true")
    state, _observations, proposals = _run_commands(monkeypatch, package)
    assert world_for(package, state.facts).parent("patrol_officer") == "patrol_staging"
    texts = _texts(proposals[9])
    assert texts.count(LEAVING_TEXT) == 1
    assert texts[-1] == LEAVING_TEXT
    assert "patrol_leaves_1a" in state.fired_event_ids


def test_trailing_departure_next_turn_sees_post_event_world(tmp_path: Path, monkeypatch) -> None:
    package = _variant_package(tmp_path, "patrol_leaves_1a", "true")
    state, observations, _proposals = _run_commands(monkeypatch, package)
    engine = RuntimeEngine(
        state,
        CloudflareTurnProvider(worker_url="https://worker.example/turn", token="", state=state),
    )
    engine.turn("Look at the wall calendar.", clock_seconds=1)
    assert observations[11] == "patrol_staging"


def test_non_trailing_departure_request_sees_post_event_world_control(tmp_path: Path, monkeypatch) -> None:
    package = _variant_package(tmp_path, "patrol_leaves_1a", "false")
    _state, observations, proposals = _run_commands(monkeypatch, package)
    assert observations[10] == "patrol_staging"
    assert _texts(proposals[9]).count(LEAVING_TEXT) == 1


def test_trailing_arrival_request_sees_pre_event_world(tmp_path: Path, monkeypatch) -> None:
    package = _variant_package(tmp_path, "patrol_enters_1a", "true")
    state, observations, proposals = _run_commands(monkeypatch, package, turns=7)
    assert observations[7] == "outside_house"
    assert world_for(package, state.facts).parent("patrol_officer") == "kitchen"
    assert _texts(proposals[5]).count(ARRIVAL_TEXT) == 1
    assert _texts(proposals[6]).count(ENTERING_TEXT) == 1


def test_trailing_event_rolled_back_with_snapshot(tmp_path: Path, monkeypatch) -> None:
    package = _variant_package(tmp_path, "patrol_leaves_1a", "true")
    state, _observations, _proposals = _run_commands(monkeypatch, package, turns=9)
    engine = RuntimeEngine(
        state,
        CloudflareTurnProvider(worker_url="https://worker.example/turn", token="", state=state),
    )
    snapshot = state.snapshot()
    engine.turn(COMMANDS[9], clock_seconds=1)
    state.restore_snapshot(snapshot)
    assert "patrol_leaves_1a" not in state.fired_event_ids
    assert world_for(package, state.facts).parent("patrol_officer") == "kitchen"
    engine.turn(COMMANDS[9], clock_seconds=1)
    assert list(state.fired_event_ids).count("patrol_leaves_1a") == 1


def test_trailing_event_survives_snapshot_round_trip(tmp_path: Path, monkeypatch) -> None:
    package = _variant_package(tmp_path, "patrol_leaves_1a", "true")
    state, _observations, _proposals = _run_commands(monkeypatch, package)
    snapshot = state.snapshot()
    state.restore_snapshot(snapshot)
    assert "patrol_leaves_1a" in state.fired_event_ids
    assert world_for(package, state.facts).parent("patrol_officer") == "patrol_staging"
    engine = RuntimeEngine(
        state,
        CloudflareTurnProvider(worker_url="https://worker.example/turn", token="", state=state),
    )
    proposal = engine.turn("Look at the wall calendar.", clock_seconds=1)
    assert _texts(proposal).count(LEAVING_TEXT) == 0


def test_trailing_flag_is_documented_control() -> None:
    docs = Path(__file__).parents[1] / "docs/markdown-story-authoring/pacing-and-incidents.md"
    assert "trailing" in docs.read_text()
