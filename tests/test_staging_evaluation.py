"""Contracts for the reproducible Phase 5 staging evaluator."""

from __future__ import annotations

import json
from io import BytesIO

from storygame.staging_evaluation import (
    SCRIPTED_PLAYER_STYLES,
    _http_request,
    _rate_limit_aware,
    run_staging_evaluation,
)


def test_staging_evaluation_records_all_genres_styles_and_sha_bound_gate() -> None:
    sessions = 0
    turns: dict[str, int] = {}

    def request(method: str, path: str, payload: dict[str, object] | None) -> tuple[int, dict[str, object]]:
        nonlocal sessions
        if method == "GET":
            return 200, {"status": "ok", "channel": "staging", "sha": "a" * 40}
        if path.endswith("/session"):
            sessions += 1
            return 200, {"session_id": f"session-{sessions}"}
        assert payload is not None
        command = str(payload["command"])
        if command == "look":
            return 200, {"status": "ok", "lines": ["An opening."], "state": {"location": "opening", "turn_index": 0}}
        session_id = str(payload["session_id"])
        if "case file" in command:
            turns[session_id] = 1
            return 200, {
                "status": "ok",
                "lines": ["The final ledger entry is time-stamped 11:40 p.m., twenty minutes before Emma Vale was last seen."],
                "state": {"location": "opening", "turn_index": 1, "known_facts": ["ledger_entry_time"]},
            }
        if "warded scroll" in command:
            turns[session_id] = 1
            return 200, {
                "status": "ok",
                "lines": ["The warded scroll marks the moonlit ford as the safe route through the enchanted wood."],
                "state": {"location": "opening", "turn_index": 1, "known_facts": ["warded_route"]},
            }
        if command in {"/save staging-evaluation", "/load staging-evaluation"}:
            return 200, {
                "status": "ok",
                "lines": [command],
                "state": {"location": "opening", "turn_index": turns[session_id]},
            }
        turns[session_id] = turns.get(session_id, 0) + 1
        return 200, {
            "status": "ok",
            "lines": ["The scene responds."],
            "state": {"location": "opening", "turn_index": turns[session_id]},
            "model_calls": 1,
        }

    report = run_staging_evaluation("https://staging.example", "a" * 40, request=request)

    assert report["promotion_gate"]["passed"] is True
    assert report["candidate_sha"] == "a" * 40
    assert set(report["fixtures"]) == {"mystery", "fantasy", "sci-fi", "relationship"}
    assert report["metrics"]["scripted_turns"] == 4 * len(SCRIPTED_PLAYER_STYLES)
    assert report["metrics"]["one_call_rate"] == 1.0


def test_staging_evaluation_fails_the_gate_for_wrong_sha_or_typed_error() -> None:
    def request(method: str, path: str, payload: dict[str, object] | None) -> tuple[int, dict[str, object]]:
        if method == "GET":
            return 200, {"status": "ok", "channel": "staging", "sha": "b" * 40}
        return 503, {"status": "service_unavailable", "detail": "unavailable"}

    report = run_staging_evaluation("https://staging.example", "a" * 40, request=request)

    assert report["promotion_gate"]["passed"] is False
    assert "deployment_identity" in report["promotion_gate"]["failures"]
    assert report["metrics"]["typed_errors"] == 4


def test_staging_evaluation_requires_committed_opening_disclosures() -> None:
    sessions: dict[str, dict[str, object]] = {}

    def request(method: str, path: str, payload: dict[str, object] | None) -> tuple[int, dict[str, object]]:
        if method == "GET":
            return 200, {"status": "ok", "channel": "staging", "sha": "a" * 40}
        if path.endswith("/session"):
            assert payload is not None
            genre = str(payload["genre"])
            session_id = f"session-{genre}"
            sessions[session_id] = {"genre": genre, "turn": 0}
            return 200, {"session_id": session_id}
        assert payload is not None
        session = sessions[str(payload["session_id"])]
        command = str(payload["command"])
        if command == "look":
            return 200, {"status": "ok", "lines": ["An opening."], "state": {"location": "opening", "turn_index": 0}}
        if "case file" in command:
            session["turn"] = 1
            return 200, {
                "status": "ok",
                "lines": ["The final ledger entry is time-stamped 11:40 p.m., twenty minutes before Emma Vale was last seen."],
                "state": {"location": "opening", "turn_index": 1, "known_facts": ["ledger_entry_time"]},
            }
        if "warded scroll" in command:
            session["turn"] = 1
            return 200, {
                "status": "ok",
                "lines": ["The warded scroll marks the moonlit ford as the safe route through the enchanted wood."],
                "state": {"location": "opening", "turn_index": 1, "known_facts": ["warded_route"]},
            }
        if command in {"/save staging-evaluation", "/load staging-evaluation"}:
            return 200, {"status": "ok", "lines": [command], "state": {"location": "opening", "turn_index": session["turn"]}}
        session["turn"] = int(session["turn"]) + 1
        return 200, {
            "status": "ok",
            "lines": ["The scene responds."],
            "state": {"location": "opening", "turn_index": session["turn"]},
            "model_calls": 1,
        }

    report = run_staging_evaluation("https://staging.example", "a" * 40, request=request)

    assert report["promotion_gate"]["passed"] is True
    assert report["fixtures"]["mystery"]["disclosure"]["key"] == "ledger_entry_time"
    assert report["fixtures"]["fantasy"]["disclosure"]["key"] == "warded_route"


def test_staging_evaluation_records_session_and_opening_failures() -> None:
    def unavailable_session(method: str, path: str, payload: dict[str, object] | None) -> tuple[int, dict[str, object]]:
        if method == "GET":
            return 200, {"status": "ok", "channel": "staging", "sha": "a" * 40}
        return 503, {"status": "service_unavailable"}

    report = run_staging_evaluation("https://staging.example", "a" * 40, request=unavailable_session)
    assert report["metrics"]["typed_errors"] == 4
    assert report["metrics"]["user_facing_session_failures"] == 4

    def invalid_opening(method: str, path: str, payload: dict[str, object] | None) -> tuple[int, dict[str, object]]:
        if method == "GET":
            return 200, {"status": "ok", "channel": "staging", "sha": "a" * 40}
        if path.endswith("/session"):
            return 200, {"session_id": "one"}
        return 200, {"status": "ok", "state": {"location": "opening", "turn_index": 2}}

    opening_report = run_staging_evaluation("https://staging.example", "a" * 40, request=invalid_opening)
    assert opening_report["metrics"]["continuity_violations"] == 4
    assert opening_report["promotion_gate"]["passed"] is False


def test_http_request_serializes_payload_and_decodes_error_response(monkeypatch) -> None:
    captured: dict[str, object] = {}

    class Response:
        status = 201
        headers: dict[str, str] = {}

        def read(self) -> bytes:
            return b'{"session_id":"one"}'

        def __enter__(self):
            return self

        def __exit__(self, *args):
            return None

    def success(request, timeout):
        captured["url"] = request.full_url
        captured["payload"] = json.loads(request.data)
        return Response()

    monkeypatch.setattr("urllib.request.urlopen", success)
    request = _http_request("https://staging.example")
    assert request("POST", "/api/v1/session", {"genre": "mystery"}) == (201, {"session_id": "one"})
    assert captured == {"url": "https://staging.example/api/v1/session", "payload": {"genre": "mystery"}}

    from urllib.error import HTTPError

    def failure(request, timeout):
        raise HTTPError(request.full_url, 503, "unavailable", {}, BytesIO(b'{"status":"service_unavailable"}'))

    monkeypatch.setattr("urllib.request.urlopen", failure)
    assert request("GET", "/api/v1/version", None) == (503, {"status": "service_unavailable"})


def test_staging_evaluation_retries_one_public_rate_limit_window() -> None:
    calls = 0
    waits: list[float] = []

    def request(method: str, path: str, payload: dict[str, object] | None) -> tuple[int, dict[str, object]]:
        nonlocal calls
        calls += 1
        if calls == 1:
            return 429, {"status": "rate_limited"}
        return 200, {"status": "ok"}

    limited = _rate_limit_aware(request, waits.append)
    assert limited("POST", "/api/v1/turn", {}) == (200, {"status": "ok"})
    assert waits == [61]
