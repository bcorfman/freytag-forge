from __future__ import annotations

import json
import os
import urllib.error
import urllib.request

import pytest

pytestmark = pytest.mark.skipif(
    not os.getenv("HOSTED_DEMO_API_BASE_URL", "").strip(),
    reason="Live hosted-demo E2E runs only when HOSTED_DEMO_API_BASE_URL is configured.",
)


def _api_base_url() -> str:
    base_url = os.getenv("HOSTED_DEMO_API_BASE_URL", "").strip().rstrip("/")
    if not base_url:
        raise RuntimeError("HOSTED_DEMO_API_BASE_URL is required for the live hosted-demo E2E test.")
    return base_url


def _request(url: str, method: str, payload: dict[str, object] | None = None) -> tuple[int, dict[str, str], dict]:
    body = None if payload is None else json.dumps(payload).encode("utf-8")
    headers = {"Origin": os.getenv("HOSTED_DEMO_ORIGIN", "https://bcorfman.github.io").strip()}
    if body is not None:
        headers["Content-Type"] = "application/json"
    request = urllib.request.Request(url, data=body, method=method, headers=headers)
    try:
        with urllib.request.urlopen(request, timeout=30) as response:
            headers = {key.lower(): value for key, value in response.headers.items()}
            return response.status, headers, json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        headers = {key.lower(): value for key, value in exc.headers.items()}
        return exc.code, headers, json.loads(exc.read().decode("utf-8"))


@pytest.mark.live_e2e
def test_deployed_hosted_demo_creates_a_session_and_renders_an_opening() -> None:
    """Exercise the browser flow plus fact-backed continuity and persistence."""
    base_url = _api_base_url()

    health_status, _, health_payload = _request(f"{base_url}/api/v1/health", "GET")
    assert health_status == 200
    assert health_payload == {"status": "ok"}

    session_status, session_headers, session_payload = _request(
        f"{base_url}/api/v1/session",
        "POST",
        {"seed": 123, "genre": "mystery", "session_length": "short", "tone": "dark"},
    )
    assert session_status == 200
    assert session_headers.get("access-control-allow-origin") in {"*", os.getenv("HOSTED_DEMO_ORIGIN", "").strip()}
    session_id = str(session_payload["session_id"])

    turn_status, turn_headers, turn_payload = _request(
        f"{base_url}/api/v1/turn",
        "POST",
        {"session_id": session_id, "command": "look"},
    )
    assert turn_status == 200, turn_payload
    assert turn_headers.get("access-control-allow-origin") in {"*", os.getenv("HOSTED_DEMO_ORIGIN", "").strip()}
    assert turn_payload["status"] == "ok"
    assert turn_payload["session_id"] == session_id
    assert turn_payload["state"]["turn_index"] == 0
    assert turn_payload["lines"]
    opening_text = "\n".join(turn_payload["lines"])
    assert "# doctest" not in opening_text.lower()
    assert "opening_draft" not in opening_text
    assert '"""' not in opening_text
    assert "rule:" not in opening_text.lower()
    assert "fact-representable" not in opening_text.lower()

    def run_turn(command: str) -> dict:
        status, headers, payload = _request(
            f"{base_url}/api/v1/turn",
            "POST",
            {"session_id": session_id, "command": command},
        )
        assert status == 200, payload
        assert headers.get("access-control-allow-origin") in {"*", os.getenv("HOSTED_DEMO_ORIGIN", "").strip()}
        assert payload["status"] == "ok"
        assert payload["session_id"] == session_id
        return payload

    foyer = run_turn("go north")
    assert foyer["state"]["location"] == "foyer"
    assert foyer["state"]["inventory"] == ["field_kit"]

    market_lane = run_turn("go east")
    assert market_lane["state"]["location"] == "market_lane"

    collected = run_turn("take route key")
    assert collected["state"]["location"] == "market_lane"
    assert "route_key" in collected["state"]["inventory"]

    run_turn("save hosted-e2e-continuity")
    moved_on = run_turn("go north")
    assert moved_on["state"]["location"] == "records_office"

    restored = run_turn("load hosted-e2e-continuity")
    assert restored["state"]["location"] == "market_lane"
    assert restored["state"]["inventory"] == collected["state"]["inventory"]
