"""Hosted scene-runtime adapter contracts."""

from fastapi.testclient import TestClient

from storygame.runtime.cloudflare import NarrationProviderError
from storygame.web_demo import create_demo_app


def test_hosted_adapter_reports_identity_and_serves_a_story_session(monkeypatch, tmp_path) -> None:
    monkeypatch.setenv("FREYTAG_DEPLOYMENT_SHA", "a" * 40)
    app = create_demo_app(
        channel="staging",
        store_path=tmp_path / "sessions.sqlite",
        provider_factory=lambda _state: lambda _input: {"narration": "The lead sharpens."},
    )

    with TestClient(app) as client:
        health = client.get("/api/v1/health")
        version = client.get("/api/v1/version")
        session = client.post("/api/v1/session", json={"story_id": "continuity_initiative"})
        turn = client.post(
            "/api/v1/turn", json={"session_id": session.json()["session_id"], "player_input": "I listen."}
        )

    assert health.json() == {
        "status": "ok",
        "runtime": "scene-v1",
        "channel": "staging",
        "sha": "a" * 40,
    }
    assert version.json() == {
        "api": "v1",
        "runtime": "scene-v1",
        "channel": "staging",
        "sha": "a" * 40,
    }
    assert session.json()["state"] == {
        "story_id": "continuity_initiative",
        "scene_id": "1A",
        "phase": "exposition",
        "pending_game_break": False,
        "fired_storylet_ids": [],
        "fired_pacing_event_ids": [],
        "story_elapsed_seconds": 0,
    }
    assert "Sarah's phone lies facedown" in session.json()["opening"]["text"]
    assert session.json()["opening"]["text"] != "Enter 1A"
    assert turn.json()["segments"] == [{"kind": "narration", "text": "The lead sharpens."}]
    assert turn.json()["lines"] == ["The lead sharpens."]


def test_game_break_is_typed_persistent_and_resolved_server_side(tmp_path) -> None:
    app = create_demo_app(
        store_path=tmp_path / "sessions.sqlite",
        provider_factory=lambda _state: (
            lambda _input: {
                "narration": "I incapacitate Gabriel.",
                "operations": [{"operation": "assert", "fact": {"predicate": "incapacitated", "subject": "gabriel"}}],
            }
        ),
    )
    with TestClient(app) as client:
        session_id = client.post("/api/v1/session", json={"story_id": "continuity_initiative"}).json()["session_id"]
        warning = client.post("/api/v1/turn", json={"session_id": session_id, "player_input": "I attack Gabriel."})
        blocked = client.post("/api/v1/turn", json={"session_id": session_id, "player_input": "I keep going."})
        resolution = client.post(
            "/api/v1/game-break",
            json={
                "session_id": session_id,
                "warning_id": warning.json()["game_break"]["warning_id"],
                "decision": "return_to_scene",
            },
        )

    assert warning.json()["game_break"]["warning_id"] == "future_dependency_at_risk"
    assert warning.json()["state"]["pending_game_break"] is True
    assert blocked.status_code == 409
    assert resolution.json()["state"]["pending_game_break"] is False


def test_adapter_fails_closed_without_worker_rejects_unknown_story_and_rate_limits(monkeypatch, tmp_path) -> None:
    monkeypatch.setenv("FREYTAG_RATE_LIMIT_PER_MINUTE", "1")
    app = create_demo_app(store_path=tmp_path / "sessions.sqlite")
    with TestClient(app) as client:
        missing_story = client.post("/api/v1/session", json={"story_id": "missing"})
        session_id = client.post("/api/v1/session", json={"story_id": "continuity_initiative"}).json()["session_id"]
        unavailable = client.post("/api/v1/turn", json={"session_id": session_id, "player_input": "I listen."})
        limited = client.post("/api/v1/turn", json={"session_id": session_id, "player_input": "I try again."})

    assert missing_story.status_code == 404
    assert unavailable.status_code == 503
    assert limited.status_code == 429


def test_adapter_exposes_a_safe_worker_error_code_header(tmp_path) -> None:
    def rejected_provider(_state):
        def reject(_input):
            raise NarrationProviderError(
                "narration service rejected the turn", 502, "WORKER_CONFIGURATION_ERROR", "trace-123", "worker-456"
            )

        return reject

    app = create_demo_app(store_path=tmp_path / "sessions.sqlite", provider_factory=rejected_provider)
    with TestClient(app) as client:
        session_id = client.post("/api/v1/session", json={"story_id": "continuity_initiative"}).json()["session_id"]
        response = client.post("/api/v1/turn", json={"session_id": session_id, "player_input": "I listen."})

    assert response.status_code == 502
    assert response.headers["X-Narration-Error-Code"] == "WORKER_CONFIGURATION_ERROR"
    assert response.headers["X-Trace-ID"] == "trace-123"
    assert response.headers["X-Worker-Revision"] == "worker-456"


def test_turn_request_accepts_the_pre_scene_command_field(tmp_path) -> None:
    app = create_demo_app(
        store_path=tmp_path / "sessions.sqlite",
        provider_factory=lambda _state: lambda _input: {"narration": "The lead sharpens."},
    )
    with TestClient(app) as client:
        session_id = client.post("/api/v1/session", json={"story_id": "continuity_initiative"}).json()["session_id"]
        response = client.post("/api/v1/turn", json={"session_id": session_id, "command": "I listen."})

    assert response.status_code == 200
    assert response.json()["segments"] == [{"kind": "narration", "text": "The lead sharpens."}]


def test_test_clock_is_opt_in_and_can_trigger_pacing_without_waiting(monkeypatch, tmp_path) -> None:
    monkeypatch.setenv("FREYTAG_ALLOW_TEST_CLOCK", "1")
    app = create_demo_app(
        store_path=tmp_path / "sessions.sqlite",
        provider_factory=lambda _state: lambda _input: {"narration": "The patrol's radios crackle outside."},
    )
    with TestClient(app) as client:
        session_id = client.post("/api/v1/session", json={"story_id": "continuity_initiative"}).json()["session_id"]
        response = client.post(
            "/api/v1/turn",
            json={"session_id": session_id, "player_input": "I wait and listen."},
            headers={"X-Freytag-Test-Clock-Seconds": "120"},
        )

    assert response.status_code == 200
    assert response.json()["state"]["story_elapsed_seconds"] == 120


def test_test_clock_header_is_ignored_without_local_opt_in(tmp_path) -> None:
    app = create_demo_app(
        store_path=tmp_path / "sessions.sqlite",
        provider_factory=lambda _state: lambda _input: {"narration": "The room stays tense.", "narrative_seconds": 40},
    )
    with TestClient(app) as client:
        session_id = client.post("/api/v1/session", json={"story_id": "continuity_initiative"}).json()["session_id"]
        response = client.post(
            "/api/v1/turn",
            json={"session_id": session_id, "player_input": "I listen."},
            headers={"X-Freytag-Test-Clock-Seconds": "120"},
        )

    assert response.json()["state"]["story_elapsed_seconds"] == 40


def test_test_clock_rejects_invalid_or_unsafe_values(monkeypatch, tmp_path) -> None:
    monkeypatch.setenv("FREYTAG_ALLOW_TEST_CLOCK", "1")
    app = create_demo_app(
        store_path=tmp_path / "sessions.sqlite",
        provider_factory=lambda _state: lambda _input: {"narration": "The room stays tense."},
    )
    with TestClient(app) as client:
        session_id = client.post("/api/v1/session", json={"story_id": "continuity_initiative"}).json()["session_id"]
        invalid = client.post(
            "/api/v1/turn",
            json={"session_id": session_id, "player_input": "I listen."},
            headers={"X-Freytag-Test-Clock-Seconds": "later"},
        )
        unsafe = client.post(
            "/api/v1/turn",
            json={"session_id": session_id, "player_input": "I listen."},
            headers={"X-Freytag-Test-Clock-Seconds": "3601"},
        )

    assert invalid.status_code == 422
    assert unsafe.status_code == 422


def test_test_clock_cors_header_is_available_only_with_local_opt_in(monkeypatch, tmp_path) -> None:
    monkeypatch.setenv("FREYTAG_ALLOW_TEST_CLOCK", "1")
    app = create_demo_app(store_path=tmp_path / "sessions.sqlite")
    with TestClient(app) as client:
        preflight = client.options(
            "/api/v1/turn",
            headers={
                "Origin": "http://127.0.0.1:4173",
                "Access-Control-Request-Method": "POST",
                "Access-Control-Request-Headers": "X-Freytag-Test-Clock-Seconds",
            },
        )

    assert preflight.status_code == 200
    assert "x-freytag-test-clock-seconds" in preflight.headers["access-control-allow-headers"].lower()
