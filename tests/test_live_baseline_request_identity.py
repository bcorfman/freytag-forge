from __future__ import annotations

import importlib.util
import json
from pathlib import Path
from types import SimpleNamespace
from urllib.request import Request

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts/ringer/transcript_1a/live_baseline.py"


def _module():
    module_spec = importlib.util.spec_from_file_location("live_baseline_request_identity", SCRIPT)
    module = importlib.util.module_from_spec(module_spec)
    assert module_spec.loader is not None
    module_spec.loader.exec_module(module)
    return module


class _Response:
    status = 200
    headers = {}

    def __init__(self, body: object) -> None:
        self._body = json.dumps(body).encode()

    def read(self, *_args: object, **_kwargs: object) -> bytes:
        return self._body

    def __enter__(self):
        return self

    def __exit__(self, *_args: object) -> None:
        return None


def _request(url: str, payload: dict) -> Request:
    return Request(url, data=json.dumps(payload).encode(), method="POST")


def _narration_request() -> Request:
    return _request(
        "https://worker.example/turn",
        {"system": "You are the narrator.", "user": "Look under the park bench."},
    )


def _jev_request() -> Request:
    return _request(
        "https://worker.example/jev",
        {
            "input": {
                "state": {
                    "narration": "must not be recorded",
                    "scene": "Los Angeles park",
                    "starting_places": {"storm drain": "Los Angeles park"},
                },
                "questions": {"relation_0": {"type": "noul"}},
            }
        },
    )


def test_first_success_and_two_logical_attempts_keep_http_prompts_separate(monkeypatch) -> None:
    module = _module()
    counter = module.CallCounter(10, False)
    row = {"late_completions_after_turn": []}
    counter.begin_turn(2, 4, row)

    monkeypatch.setattr("urllib.request.urlopen", lambda *_args, **_kwargs: _Response({"ok": True}))
    first = counter.live_urlopen(_narration_request())
    first.read()
    second = counter.live_urlopen(_narration_request())
    second.read()

    enforce_attempts = [{"accepted": False}, {"accepted": False}]
    assert module._logical_narration_attempts(enforce_attempts) == 2
    assert module._narration_attempts(counter) == 2
    assert [entry["owner"]["dispatch_number"] for entry in counter.timings] == [1, 2]
    assert all(response["owner"]["turn_index"] == 4 for response in counter.responses)
    assert counter.timings[0]["jev_dispatches"] == []


def test_jev_dispatch_is_bounded_and_keeps_scene_values(monkeypatch) -> None:
    module = _module()
    counter = module.CallCounter(10, False)
    counter.begin_turn(0, 0, {"late_completions_after_turn": []})
    monkeypatch.setattr("urllib.request.urlopen", lambda *_args, **_kwargs: _Response({"answers": {}}))

    response = counter.live_urlopen(_jev_request())
    response.read()

    assert counter.timings[0]["jev_dispatches"] == [
        {
            "state_keys": ["narration", "scene", "starting_places"],
            "question_names": ["relation_0"],
            "scene": "Los Angeles park",
            "starting_places": {"storm drain": "Los Angeles park"},
        }
    ]
    assert "must not be recorded" not in json.dumps(counter.timings)


def test_loser_completion_is_late_and_not_next_turn_data(monkeypatch) -> None:
    module = _module()
    counter = module.CallCounter(10, False)
    first_row = {"late_completions_after_turn": [], "provider_responses": []}
    counter.begin_turn(0, 0, first_row)
    monkeypatch.setattr("urllib.request.urlopen", lambda *_args, **_kwargs: _Response({"turn": 0}))
    winner = counter.live_urlopen(_narration_request())
    loser = counter.live_urlopen(_narration_request())
    winner.read()
    first_row["call_timings"] = list(counter.timings)
    first_row["provider_responses"] = list(counter.responses)
    counter.end_turn()

    next_row = {"late_completions_after_turn": [], "provider_responses": []}
    counter.begin_turn(0, 1, next_row)
    monkeypatch.setattr("urllib.request.urlopen", lambda *_args, **_kwargs: _Response({"turn": 1}))
    current = counter.live_urlopen(_narration_request())
    current.read()
    next_row["call_timings"] = list(counter.timings)
    next_row["provider_responses"] = list(counter.responses)
    counter.end_turn()

    loser.read()
    counter.snapshot_turn(first_row)

    assert len(first_row["late_completions_after_turn"]) == 1
    assert first_row["late_completions_after_turn"][0]["owner"]["turn_index"] == 0
    assert len(next_row["call_timings"]) == 1
    assert len(next_row["provider_responses"]) == 1
    assert next_row["call_timings"][0]["owner"]["turn_index"] == 1
    assert all(item["owner"]["turn_index"] != 0 for item in next_row["provider_responses"])


def test_late_completion_crossing_replicate_boundary_stays_with_owner(monkeypatch) -> None:
    module = _module()
    counter = module.CallCounter(10, False)
    first_row = {"late_completions_after_turn": [], "provider_responses": []}
    counter.begin_turn(0, 0, first_row)
    monkeypatch.setattr("urllib.request.urlopen", lambda *_args, **_kwargs: _Response({"replicate": 0}))
    pending = counter.live_urlopen(_narration_request())
    counter.end_turn()

    second_row = {"late_completions_after_turn": [], "provider_responses": []}
    counter.begin_turn(1, 0, second_row)
    pending.read()
    counter.end_turn()
    counter.snapshot_turn(first_row)

    assert first_row["late_completions_after_turn"][0]["owner"]["replicate_index"] == 0
    assert second_row["late_completions_after_turn"] == []


def test_stale_capture_reply_is_null_and_prior_value_is_explicit() -> None:
    module = _module()
    prior = {"facts_after": {"park_bench": {"place": "Los Angeles park"}}}
    capture = SimpleNamespace(last_before={"steps": ["inspect"]}, last_after=prior)
    engine = SimpleNamespace(
        last_attempt=SimpleNamespace(
            stages=(
                {
                    "kind": "capture",
                    "request": {"old": True},
                    "reply": prior,
                },
            )
        )
    )

    steps = module._record_steps(engine, capture, prior)

    assert steps["attempt_stages"][0]["reply"] is None
    assert steps["prior_turn_capture"] == {"stale": True, "reply": prior}


def test_missing_attempt_records_are_insufficient_evidence() -> None:
    module = _module()
    assert module._logical_narration_attempts([]) is None
