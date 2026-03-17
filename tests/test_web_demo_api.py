from __future__ import annotations

import logging
from datetime import UTC, datetime, timedelta

from fastapi.testclient import TestClient

from storygame.llm.adapters import CloudflareWorkersAIAdapter
from storygame.web_demo import _build_demo_narrator, create_demo_app
from tests.narrator_stubs import StubNarrator


class _PassThroughEditor:
    def review_opening(self, lines, active_goal):  # noqa: ANN001
        return lines

    def review_turn(self, lines, active_goal, turn_index, debug=False):  # noqa: ANN001
        return lines


class _StubDirector:
    def compose_opening(self, state):  # noqa: ANN001
        return list(state.world_package.get("story_plan", {}).get("setup_paragraphs", ()))

    def review_turn(self, state, lines, events, debug=False):  # noqa: ANN001
        return lines


class _Clock:
    def __init__(self, now: datetime) -> None:
        self.now = now

    def __call__(self) -> datetime:
        return self.now


class _FailingNarrator:
    def __init__(self, error_message: str) -> None:
        self._error_message = error_message

    def generate(self, _context):  # noqa: ANN001
        raise RuntimeError(self._error_message)


def _client(tmp_path, clock: _Clock | None = None) -> TestClient:
    db_path = tmp_path / "web_demo_saves.sqlite"
    now_fn = (lambda: datetime.now(UTC)) if clock is None else clock
    return TestClient(
        create_demo_app(
            save_db_path=db_path,
            narrator_mode="openai",
            narrator=StubNarrator(),
            output_editor=_PassThroughEditor(),
            story_director=_StubDirector(),
            now_fn=now_fn,
        )
    )


def test_demo_health_endpoint_is_ok(tmp_path):
    client = _client(tmp_path)
    response = client.get("/api/v1/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_demo_app_allows_configured_cors_origin(tmp_path):
    client = TestClient(
        create_demo_app(
            save_db_path=tmp_path / "web_demo_saves.sqlite",
            narrator_mode="openai",
            narrator=StubNarrator(),
            output_editor=_PassThroughEditor(),
            story_director=_StubDirector(),
            cors_allow_origins=("https://example.github.io",),
        )
    )

    response = client.options(
        "/api/v1/session",
        headers={
            "Origin": "https://example.github.io",
            "Access-Control-Request-Method": "POST",
        },
    )

    assert response.status_code == 200
    assert response.headers["access-control-allow-origin"] == "https://example.github.io"


def test_demo_session_create_then_turn_flow(tmp_path):
    client = _client(tmp_path)
    created = client.post("/api/v1/session", json={"seed": 42, "genre": "mystery", "session_length": "short", "tone": "dark"})
    assert created.status_code == 200
    payload = created.json()
    session_id = payload["session_id"]
    assert session_id
    assert payload["seed"] == 42
    assert payload["expires_at"]

    turn = client.post("/api/v1/turn", json={"session_id": session_id, "command": "look"})
    assert turn.status_code == 200
    turn_payload = turn.json()
    assert turn_payload["status"] == "ok"
    assert turn_payload["session_id"] == session_id
    assert turn_payload["lines"]
    assert turn_payload["lines"][0].startswith(">LOOK")
    assert turn_payload["state"]["turn_index"] == 1
    assert turn_payload["state"]["session_id"] == session_id


def test_demo_turn_unknown_session_returns_404(tmp_path):
    client = _client(tmp_path)
    response = client.post("/api/v1/turn", json={"session_id": "missing", "command": "look"})
    assert response.status_code == 404
    assert "Unknown or expired session_id 'missing'." in response.text


def test_demo_session_expiry_is_enforced(tmp_path):
    clock = _Clock(datetime(2026, 3, 16, 12, 0, tzinfo=UTC))
    db_path = tmp_path / "web_demo_saves.sqlite"
    client = TestClient(
        create_demo_app(
            save_db_path=db_path,
            narrator_mode="openai",
            narrator=StubNarrator(),
            output_editor=_PassThroughEditor(),
            story_director=_StubDirector(),
            session_ttl_seconds=60,
            now_fn=clock,
        )
    )
    created = client.post("/api/v1/session", json={"seed": 9})
    assert created.status_code == 200
    session_id = created.json()["session_id"]

    clock.now = clock.now + timedelta(seconds=61)
    expired = client.post("/api/v1/turn", json={"session_id": session_id, "command": "look"})
    assert expired.status_code == 404
    assert f"Unknown or expired session_id '{session_id}'." in expired.text


def test_demo_narrator_defaults_to_cloudflare_when_worker_url_set(monkeypatch):
    monkeypatch.setenv("CLOUDFLARE_WORKER_URL", "https://demo.example.workers.dev/api/narrate")
    narrator = _build_demo_narrator("openai")
    assert isinstance(narrator, CloudflareWorkersAIAdapter)


def test_demo_session_turn_cap_returns_quota_exhausted_status(tmp_path):
    client = TestClient(
        create_demo_app(
            save_db_path=tmp_path / "web_demo_saves.sqlite",
            narrator_mode="openai",
            narrator=StubNarrator(),
            output_editor=_PassThroughEditor(),
            story_director=_StubDirector(),
            session_turn_cap=1,
        )
    )
    created = client.post("/api/v1/session", json={"seed": 41})
    session_id = created.json()["session_id"]

    first = client.post("/api/v1/turn", json={"session_id": session_id, "command": "look"})
    assert first.status_code == 200

    second = client.post("/api/v1/turn", json={"session_id": session_id, "command": "look"})
    assert second.status_code == 429
    payload = second.json()
    assert payload["status"] == "quota_exhausted"
    assert "turn cap" in payload["detail"].lower()


def test_demo_ip_rate_limit_returns_rate_limited_status(tmp_path):
    clock = _Clock(datetime(2026, 3, 16, 12, 0, tzinfo=UTC))
    client = TestClient(
        create_demo_app(
            save_db_path=tmp_path / "web_demo_saves.sqlite",
            narrator_mode="openai",
            narrator=StubNarrator(),
            output_editor=_PassThroughEditor(),
            story_director=_StubDirector(),
            ip_rate_limit_per_min=1,
            now_fn=clock,
        )
    )
    session_a = client.post("/api/v1/session", json={"seed": 1}).json()["session_id"]
    session_b = client.post("/api/v1/session", json={"seed": 2}).json()["session_id"]

    first = client.post("/api/v1/turn", json={"session_id": session_a, "command": "look"})
    assert first.status_code == 200

    second = client.post("/api/v1/turn", json={"session_id": session_b, "command": "look"})
    assert second.status_code == 429
    payload = second.json()
    assert payload["status"] == "rate_limited"


def test_demo_ip_daily_cap_returns_rate_limited_status(tmp_path):
    clock = _Clock(datetime(2026, 3, 16, 12, 0, tzinfo=UTC))
    client = TestClient(
        create_demo_app(
            save_db_path=tmp_path / "web_demo_saves.sqlite",
            narrator_mode="openai",
            narrator=StubNarrator(),
            output_editor=_PassThroughEditor(),
            story_director=_StubDirector(),
            ip_rate_limit_per_min=10,
            ip_daily_turn_cap=1,
            now_fn=clock,
        )
    )
    session_a = client.post("/api/v1/session", json={"seed": 3}).json()["session_id"]
    session_b = client.post("/api/v1/session", json={"seed": 4}).json()["session_id"]

    first = client.post("/api/v1/turn", json={"session_id": session_a, "command": "look"})
    assert first.status_code == 200

    second = client.post("/api/v1/turn", json={"session_id": session_b, "command": "look"})
    assert second.status_code == 429
    payload = second.json()
    assert payload["status"] == "rate_limited"
    assert "daily cap" in payload["detail"].lower()


def test_demo_quota_failure_from_narrator_is_fail_closed(tmp_path):
    client = TestClient(
        create_demo_app(
            save_db_path=tmp_path / "web_demo_saves.sqlite",
            narrator_mode="openai",
            narrator=_FailingNarrator("AI_QUOTA_EXCEEDED"),
            output_editor=_PassThroughEditor(),
            story_director=_StubDirector(),
        )
    )
    session_id = client.post("/api/v1/session", json={"seed": 5}).json()["session_id"]
    response = client.post("/api/v1/turn", json={"session_id": session_id, "command": "look"})
    assert response.status_code == 429
    payload = response.json()
    assert payload["status"] == "quota_exhausted"


def test_demo_service_failure_from_narrator_is_fail_closed(tmp_path):
    client = TestClient(
        create_demo_app(
            save_db_path=tmp_path / "web_demo_saves.sqlite",
            narrator_mode="openai",
            narrator=_FailingNarrator("backend unavailable"),
            output_editor=_PassThroughEditor(),
            story_director=_StubDirector(),
        )
    )
    session_id = client.post("/api/v1/session", json={"seed": 6}).json()["session_id"]
    response = client.post("/api/v1/turn", json={"session_id": session_id, "command": "look"})
    assert response.status_code == 503
    payload = response.json()
    assert payload["status"] == "service_unavailable"


def test_demo_service_failure_logs_underlying_narrator_error(tmp_path, caplog):
    client = TestClient(
        create_demo_app(
            save_db_path=tmp_path / "web_demo_saves.sqlite",
            narrator_mode="openai",
            narrator=_FailingNarrator("backend unavailable"),
            output_editor=_PassThroughEditor(),
            story_director=_StubDirector(),
        )
    )
    session_id = client.post("/api/v1/session", json={"seed": 7}).json()["session_id"]
    with caplog.at_level(logging.WARNING):
        response = client.post("/api/v1/turn", json={"session_id": session_id, "command": "look"})
    assert response.status_code == 503
    assert "Narrator failed" in caplog.text
    assert "backend unavailable" in caplog.text
