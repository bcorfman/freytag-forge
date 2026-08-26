"""Hosted scene-runtime adapter contracts."""

from fastapi.testclient import TestClient

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
