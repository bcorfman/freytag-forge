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
    """Exercise the same session -> look sequence the GitHub Pages client runs."""
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
