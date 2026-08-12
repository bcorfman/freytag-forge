"""Reproducible, SHA-bound Phase 5 evaluation of the hosted V2 staging API."""

from __future__ import annotations

import json
import os
import time
import urllib.error
import urllib.request
from collections.abc import Callable
from pathlib import Path
from typing import Any

from storygame.authoring.compiler import load_compiled_story_fixture

SCRIPTED_PLAYER_STYLES: dict[str, str] = {
    "investigate": "I examine the scene closely for a useful detail.",
    "travel": "I leave this place and head somewhere that could change the situation.",
    "social": "I ask someone nearby what they know and listen carefully.",
    "avoidant": "I wait, observe, and refuse to commit to a risky plan yet.",
    "adversarial": "I challenge the obvious assumption and test whether it is wrong.",
    "repeated_failure": "I try the same approach again despite its previous failure.",
    "unexpected_action": "I attempt an unusual but plausible action nobody has suggested.",
}
Request = Callable[[str, str, dict[str, object] | None], tuple[int, dict[str, object]]]
Sleep = Callable[[float], None]


def run_staging_evaluation(
    api_base_url: str,
    candidate_sha: str,
    *,
    request: Request | None = None,
    sleep_fn: Sleep = time.sleep,
) -> dict[str, Any]:
    """Exercise every V2 fixture and return promotion-gate evidence, never a verdict by prose."""
    api_base_url = api_base_url.rstrip("/")
    request = _rate_limit_aware(request or _http_request(api_base_url), sleep_fn)
    health_status, health = request("GET", "/api/v1/version", None)
    identity_ok = (
        health_status == 200
        and health.get("status") == "ok"
        and health.get("channel") == "staging"
        and health.get("sha") == candidate_sha
    )
    fixtures: dict[str, dict[str, object]] = {}
    model_calls: list[int] = []
    latencies_ms: list[float] = []
    typed_errors = 0
    protected_leaks = 0
    continuity_violations = 0
    completed_sessions = 0
    for genre in ("mystery", "fantasy", "sci-fi", "relationship"):
        story = load_compiled_story_fixture(genre)
        fixture, calls, latencies, errors, leaks, continuity, completed = _run_fixture(request, genre, story)
        fixtures[genre] = fixture
        model_calls.extend(calls)
        latencies_ms.extend(latencies)
        typed_errors += errors
        protected_leaks += leaks
        continuity_violations += continuity
        completed_sessions += completed
    scripted_turns = len(model_calls) + typed_errors
    one_call_turns = sum(calls == 1 for calls in model_calls)
    failures = []
    if not identity_ok:
        failures.append("deployment_identity")
    if typed_errors:
        failures.append("typed_fail_closed_errors")
    if protected_leaks:
        failures.append("protected_revelation")
    if continuity_violations:
        failures.append("state_continuity")
    if scripted_turns != 4 * len(SCRIPTED_PLAYER_STYLES):
        failures.append("incomplete_scripted_coverage")
    return {
        "schema_version": "phase5-staging-evaluation-v1",
        "candidate_sha": candidate_sha,
        "channel": health.get("channel"),
        "health": health,
        "fixtures": fixtures,
        "metrics": {
            "scripted_turns": scripted_turns,
            "one_call_rate": one_call_turns / len(model_calls) if model_calls else 0.0,
            "repair_rate": sum(calls == 2 for calls in model_calls) / len(model_calls) if model_calls else 0.0,
            "typed_errors": typed_errors,
            "p95_turn_latency_ms": _p95(latencies_ms),
            "premature_revelations": protected_leaks,
            "continuity_violations": continuity_violations,
            "completion_rate": completed_sessions / 4,
            "user_facing_session_failures": sum(not bool(fixture["passed"]) for fixture in fixtures.values()),
        },
        "promotion_gate": {"passed": not failures, "failures": failures},
    }


def _run_fixture(
    request: Request, genre: str, story: object
) -> tuple[dict[str, object], list[int], list[float], int, int, int, int]:
    created_status, created = request("POST", "/api/v1/session", {"genre": genre})
    if created_status != 200 or not isinstance(created.get("session_id"), str):
        return {"passed": False, "failure": "session_creation"}, [], [], 1, 0, 0, 0
    session_id = created["session_id"]
    opening_status, opening = request("POST", "/api/v1/turn", {"session_id": session_id, "command": "look"})
    if opening_status != 200 or not _valid_state(opening.get("state"), 0):
        return {"passed": False, "failure": "opening"}, [], [], 1, 0, 1, 0
    previous_turn = 0
    calls: list[int] = []
    latencies: list[float] = []
    typed_errors = leaks = continuity = 0
    protections = tuple(item.summary.casefold() for item in story.protected_revelations)
    for style, command in SCRIPTED_PLAYER_STYLES.items():
        started = time.monotonic()
        status, result = request("POST", "/api/v1/turn", {"session_id": session_id, "command": command})
        latencies.append((time.monotonic() - started) * 1000)
        if status != 200:
            typed_errors += int(result.get("status") == "service_unavailable")
            return {"passed": False, "failure": style}, calls, latencies, typed_errors, leaks, continuity, 0
        state = result.get("state")
        expected_turn = previous_turn + 1
        if not _valid_state(state, expected_turn):
            continuity += 1
            return {"passed": False, "failure": style}, calls, latencies, typed_errors, leaks, continuity, 0
        previous_turn = expected_turn
        visible = " ".join(value for value in result.get("lines", []) if isinstance(value, str)).casefold()
        leaks += sum(protection in visible for protection in protections)
        model_calls = result.get("model_calls")
        if not isinstance(model_calls, int) or model_calls not in {1, 2}:
            continuity += 1
            return {"passed": False, "failure": "turn_metrics"}, calls, latencies, typed_errors, leaks, continuity, 0
        calls.append(model_calls)
    for command in ("/save staging-evaluation", "/load staging-evaluation"):
        status, result = request("POST", "/api/v1/turn", {"session_id": session_id, "command": command})
        if status != 200 or not _valid_state(result.get("state"), previous_turn):
            continuity += 1
            return {"passed": False, "failure": command}, calls, latencies, typed_errors, leaks, continuity, 0
    completed = int(isinstance(result.get("state"), dict) and result["state"].get("active_beats") == [])
    return (
        {"passed": leaks == 0, "styles": list(SCRIPTED_PLAYER_STYLES)},
        calls,
        latencies,
        typed_errors,
        leaks,
        continuity,
        completed,
    )


def _valid_state(state: object, expected_turn: int) -> bool:
    return (
        isinstance(state, dict) and isinstance(state.get("location"), str) and state.get("turn_index") == expected_turn
    )


def _p95(samples: list[float]) -> float:
    if not samples:
        return 0.0
    return sorted(samples)[min(len(samples) - 1, int(len(samples) * 0.95))]


def _rate_limit_aware(request: Request, sleep_fn: Sleep) -> Request:
    """Use the public staging limit; retry one bounded time after its window."""

    def call(method: str, path: str, payload: dict[str, object] | None) -> tuple[int, dict[str, object]]:
        status, result = request(method, path, payload)
        if status == 429 and result.get("status") == "rate_limited":
            sleep_fn(61)
            return request(method, path, payload)
        return status, result

    return call


def _http_request(api_base_url: str) -> Request:
    def request(method: str, path: str, payload: dict[str, object] | None) -> tuple[int, dict[str, object]]:
        body = None if payload is None else json.dumps(payload).encode()
        headers = {"Content-Type": "application/json"} if body else {}
        target = urllib.request.Request(f"{api_base_url}{path}", data=body, method=method, headers=headers)
        try:
            with urllib.request.urlopen(target, timeout=30) as response:
                return response.status, json.loads(response.read().decode())
        except urllib.error.HTTPError as exc:
            return exc.code, json.loads(exc.read().decode())

    return request


if __name__ == "__main__":
    output = Path(os.getenv("FREYTAG_EVALUATION_REPORT", "artifacts/staging-evaluation.json"))
    output.parent.mkdir(parents=True, exist_ok=True)
    report = run_staging_evaluation(os.environ["HOSTED_DEMO_API_BASE_URL"], os.environ["DEPLOYED_SHA"])
    output.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    if not report["promotion_gate"]["passed"]:
        raise SystemExit("Phase 5 staging promotion gate failed; inspect the evaluation report.")
