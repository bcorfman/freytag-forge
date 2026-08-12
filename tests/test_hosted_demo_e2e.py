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
    """Exercise the retained V2 browser flow and runtime-state persistence."""
    base_url = _api_base_url()

    health_status, _, health_payload = _request(f"{base_url}/api/v1/health", "GET")
    assert health_status == 200
    assert health_payload["status"] == "ok"
    expected_channel = os.getenv("HOSTED_DEMO_CHANNEL", "").strip()
    if expected_channel:
        assert health_payload["channel"] == expected_channel
        assert health_payload["sha"] == os.getenv("DEPLOYED_SHA", "").strip()

    session_status, session_headers, session_payload = _request(
        f"{base_url}/api/v1/session",
        "POST",
        {"genre": "mystery"},
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

    first_turn = run_turn("Search the square for a lead.")
    assert first_turn["state"]["turn_index"] == 1

    saved = run_turn("save")
    assert saved["state"]["turn_index"] == 1
    restored = run_turn("load")
    assert restored["state"]["turn_index"] == 1
