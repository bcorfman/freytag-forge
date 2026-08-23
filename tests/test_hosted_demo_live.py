from __future__ import annotations

import json
import os
from urllib.error import HTTPError
from urllib.request import Request, urlopen

import pytest


def _request(base_url: str, path: str, *, payload: dict[str, object] | None = None) -> object:
    body = None
    headers = {}
    if payload is not None:
        body = json.dumps(payload).encode("utf-8")
        headers["Content-Type"] = "application/json"
    request = Request(f"{base_url.rstrip('/')}{path}", data=body, headers=headers, method="POST" if body else "GET")
    try:
        with urlopen(request, timeout=30) as response:
            assert response.status == 200
            return json.loads(response.read())
    except HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")
        raise AssertionError(f"{request.full_url} returned HTTP {exc.code}: {detail}") from exc


@pytest.mark.live_e2e
def test_deployed_hosted_demo_identity_pages_and_session_flow() -> None:
    api_base_url = os.getenv("HOSTED_DEMO_API_BASE_URL", "").strip()
    pages_base_url = os.getenv("HOSTED_DEMO_PAGES_URL", "").strip().rstrip("/")
    if not api_base_url or not pages_base_url:
        pytest.skip("live hosted-demo targets are not configured")

    expected_channel = os.getenv("HOSTED_DEMO_CHANNEL", "production").strip()
    expected_sha = os.getenv("DEPLOYED_SHA", "").strip()
    health = _request(api_base_url, "/api/v1/health")
    version = _request(api_base_url, "/api/v1/version")
    assert health["status"] == "ok"
    assert health["runtime"] == "v2"
    assert health["channel"] == expected_channel
    assert version == {
        "api": "v1",
        "runtime": "v2",
        "channel": expected_channel,
        "sha": health["sha"],
    }
    if expected_sha:
        assert health["sha"] == expected_sha

    pages_path = "/deployment.json" if expected_channel == "production" else "/dev/deployment.json"
    deployment = _request(pages_base_url, pages_path)
    assert deployment["channel"] == expected_channel
    if expected_sha:
        assert deployment["sha"] == expected_sha

    session = _request(api_base_url, "/api/v1/session", payload={"genre": "mystery"})
    session_id = session["session_id"]
    assert session["state"]["opening"]
    turn = _request(
        api_base_url,
        "/api/v1/turn",
        payload={"session_id": session_id, "genre": "mystery", "command": "I investigate the foyer."},
    )
    assert turn["status"] == "ok"
    assert turn["state"]["turn_index"] == 1
