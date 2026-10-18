from __future__ import annotations

import json
from contextlib import nullcontext
from pathlib import Path
from types import SimpleNamespace

import door_transition
import pytest
from check_door_probe import check
from door_probe import EXPERIMENTS, dry_run, live_run
from door_transport import SpendBudget

from storygame.runtime.state import TurnDelivery


class FakeState:
    current_scene_id = "2B"
    story_complete = False
    last_turn_delivery = TurnDelivery()


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
        state.last_turn_delivery = TurnDelivery(segments_dropped=item.get("segments_dropped", 0))
        engine.last_attempt = SimpleNamespace(transition_cause=item.get("cause", "none"))
        return {
            "status": item.get("status", "unearned"),
            "response": item.get("response", f"response to {command}"),
            "committed_reveals": item.get("committed", []),
        }

    monkeypatch.setattr(door_transition, "score_command", score)
    return state, engine


def test_segments_dropped_are_recorded_per_turn(monkeypatch):
    result, _ = run(
        monkeypatch,
        [{}, {"status": "clarification", "segments_dropped": 1}, {"scene": "2C", "cause": "earned"}],
    )
    assert result["segments_dropped_by_turn"] == [0, 1, 0]
    assert len(result["segments_dropped_by_turn"]) == len(result["commands"])


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


def test_transition_live_artifacts_validate_with_stubs(monkeypatch, tmp_path):
    """Exercise live_run end to end without a provider, player, or network call."""
    import door_probe

    monkeypatch.setenv("DOOR_LEDGER_PATH", str(tmp_path / "ledger.jsonl"))

    class Provider:
        semantic_ask = None
        request_count = 0
        recovery_count = 0

        def _request(self, payload):  # pragma: no cover - raw request is stubbed
            return payload

    def raw_request_stub(provider, system, user, budget):
        budget.reserve("cloudflare", "raw_2A")
        budget.acknowledge("cloudflare", True)
        return SimpleNamespace(proposal=SimpleNamespace(narration="stub narration"), item_facts=[])

    def ask_player_stub(screen, budget):
        budget.reserve("raw_player")
        budget.acknowledge("raw_player", True)
        return "stub command"

    def continuation_stub(variation_path, first_command, screen, budget, max_commands):
        return {
            "final_scene": "2B",
            "ended_by": "none",
            "transition_turn": None,
            "commands": [first_command],
            "responses": ["stub response"],
            "clarification_turns": [],
            "committed_reveals_by_turn": [[]],
            "panel_named": False,
            "turn_statuses": ["unearned"],
            "request_count": 0,
            "recovery_count": 0,
        }

    monkeypatch.setattr(door_probe, "raw_request", raw_request_stub)
    monkeypatch.setattr(door_probe, "_ask_player", ask_player_stub)
    monkeypatch.setattr(door_probe, "provider_for", lambda state, variation: Provider())
    monkeypatch.setattr("door_transition.run_continuation", continuation_stub)

    live_run(tmp_path, 1, "transition")

    summary = json.loads((tmp_path / "summary.json").read_text(encoding="utf-8"))
    assert summary["max_commands"] == 20
    assert check(tmp_path, 1, "artifacts", "transition") == []
