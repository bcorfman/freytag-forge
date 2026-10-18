from __future__ import annotations

from contextlib import nullcontext
from pathlib import Path
from types import SimpleNamespace

import door_transition
import pytest
from check_door_probe import check
from door_probe import EXPERIMENTS, dry_run
from door_transport import SpendBudget


class FakeState:
    current_scene_id = "2B"
    story_complete = False


class FakeProvider:
    semantic_ask = object()
    request_count = 7
    recovery_count = 2

    def _request(self, payload):  # pragma: no cover - counted provider is stubbed
        return payload


class FakeEngine:
    def __init__(self, state, provider):
        self.state = state
        self.provider = provider
        self.last_attempt = None


def setup_run(monkeypatch, turns):
    state = FakeState()
    provider = FakeProvider()
    engine = FakeEngine(state, provider)
    monkeypatch.setattr(door_transition, "load_variation", lambda path: {})
    monkeypatch.setattr(door_transition, "package_and_state", lambda variation, scene: ({}, state))
    monkeypatch.setattr(door_transition, "provider_for", lambda state, variation: provider)
    monkeypatch.setattr(door_transition, "RuntimeEngine", lambda state, provider: engine)
    monkeypatch.setattr(door_transition, "counted_provider", lambda provider, budget: nullcontext(provider))

    def score(engine, state, command, **kwargs):
        item = turns.pop(0)
        state.current_scene_id = item.get("scene", state.current_scene_id)
        state.story_complete = item.get("complete", False)
        engine.last_attempt = SimpleNamespace(transition_cause=item.get("cause", "none"))
        return {
            "status": item.get("status", "unearned"),
            "response": item.get("response", f"response to {command}"),
            "committed_reveals": item.get("committed", []),
        }

    monkeypatch.setattr(door_transition, "score_command", score)
    return state, engine


def run(monkeypatch, turns, player=None, max_commands=20, *, setup=True):
    if setup:
        setup_run(monkeypatch, turns)
    calls = []

    def ask(transcript, budget):
        calls.append(transcript)
        return (player or (lambda i: f"command {i}"))(len(calls))

    result = door_transition.run_continuation(
        Path("variation.json"), "first command", "opening screen", SpendBudget(100), max_commands, ask
    )
    return result, calls


def test_earned_exit_on_turn_three(monkeypatch):
    result, _ = run(
        monkeypatch,
        [{}, {}, {"scene": "2C", "cause": "earned", "status": "earned"}],
    )
    assert result["ended_by"] == "earned"
    assert result["transition_turn"] == 3
    assert len(result["commands"]) == 3


def test_forced_exit_is_timer_exit_at_row_boundary(monkeypatch):
    result, _ = run(monkeypatch, [{"scene": "2C", "cause": "forced"}])
    assert result["ended_by"] == "forced"


def test_cap_stops_without_a_twenty_first_player_call(monkeypatch):
    result, calls = run(monkeypatch, [{} for _ in range(20)])
    assert result["ended_by"] == "none"
    assert len(result["commands"]) == 20
    assert len(calls) == 19


def test_clarification_forwards_original_command(monkeypatch):
    received = []
    state, engine = setup_run(monkeypatch, [{"status": "clarification"}, {"scene": "2C", "cause": "earned"}])
    original_score = door_transition.score_command

    def score(engine, state, command, **kwargs):
        received.append((command, kwargs))
        return original_score(engine, state, command, **kwargs)

    # Replace the setup stub with a two-step deterministic scorer.
    steps = iter([{"status": "clarification"}, {"scene": "2C", "cause": "earned"}])

    def deterministic(engine, state, command, **kwargs):
        item = next(steps)
        state.current_scene_id = item.get("scene", "2B")
        engine.last_attempt = SimpleNamespace(transition_cause=item.get("cause", "none"))
        received.append((command, kwargs))
        return {"status": item.get("status", "unearned"), "response": "reply", "committed_reveals": []}

    monkeypatch.setattr(door_transition, "score_command", deterministic)
    result, _ = run(monkeypatch, [], player=lambda _: "clarified command", setup=False)
    assert result["clarification_turns"] == [1]
    assert received[1][1]["clarifies"] == "first command"


def test_transcript_accumulates(monkeypatch):
    result, calls = run(monkeypatch, [{}, {}, {"scene": "2C", "cause": "earned"}])
    assert "first command" in calls[0]
    assert "response to first command" in calls[0]
    assert "command 1" in calls[1]
    assert "response to command 1" in calls[1]


def test_errors_propagate_without_fabricated_row(monkeypatch):
    state, engine = setup_run(monkeypatch, [])
    monkeypatch.setattr(
        door_transition, "score_command", lambda *args, **kwargs: (_ for _ in ()).throw(ValueError("boom"))
    )
    with pytest.raises(ValueError, match="boom"):
        door_transition.run_continuation(
            Path("variation.json"), "command", "screen", SpendBudget(100), ask_player=lambda *_: "next"
        )


def test_transition_caps_and_existing_configs_are_unchanged():
    assert EXPERIMENTS["transition"]["caps"] == {
        1: {"raw": 2, "cloudflare": 40, "player": 36},
        12: {"raw": 24, "cloudflare": 480, "player": 408},
    }
    assert EXPERIMENTS["grounded"]["caps"][1] == {"raw": 2, "cloudflare": 10, "player": 4}
    assert EXPERIMENTS["source"]["arms"] == ("control", "location", "limits")


def test_transition_dry_artifacts_validate(tmp_path):
    dry_run(tmp_path, 1, "transition")
    assert check(tmp_path, 1, "dry", "transition") == []
