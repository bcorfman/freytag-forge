from __future__ import annotations

from fastapi.testclient import TestClient

from storygame.web_demo import create_demo_app


class StubTurnModel:
    def play_turn(self, context: object, *, json_object: bool) -> object:
        return {
            "narration": "The next choice is yours.",
            "operations": [{"kind": "add", "path": "world.flags", "value": "acted"}],
            "beat_updates": [],
            "material_progress": True,
        }


def test_hosted_demo_uses_v2_runtime_and_persists_accepted_turns(tmp_path) -> None:
    app = create_demo_app(save_db_path=tmp_path / "runtime.sqlite", model=StubTurnModel(), channel="staging")
    with TestClient(app) as client:
        created = client.post("/api/v1/session", json={"genre": "mystery"})
        assert created.status_code == 200
        session_id = created.json()["session_id"]

        turn = client.post("/api/v1/turn", json={"session_id": session_id, "command": "I investigate."})
        assert turn.status_code == 200
        assert turn.json()["lines"] == ["The next choice is yours."]
        assert {
            key: turn.json()["state"][key] for key in ("location", "room_name", "turn_index", "available_destinations")
        } == {
            "location": "foyer",
            "room_name": "foyer",
            "turn_index": 1,
            "available_destinations": ["Study", "Library", "West Gallery", "Grounds"],
        }
        assert turn.json()["state"]["opening"]["first_available_actions"]
        assert turn.json()["model_calls"] == 1

        loaded = client.post("/api/v1/session/load", json={"session_id": session_id, "genre": "mystery"})
        assert loaded.status_code == 200
        assert loaded.json()["state"]["turn_index"] == 1


def test_hosted_demo_exposes_a_sha_bound_v1_api_identity(tmp_path, monkeypatch) -> None:
    monkeypatch.setenv("FREYTAG_DEPLOYMENT_SHA", "a" * 40)
    app = create_demo_app(save_db_path=tmp_path / "runtime.sqlite", model=StubTurnModel(), channel="staging")
    with TestClient(app) as client:
        health = client.get("/api/v1/health")
        version = client.get("/api/v1/version")

    assert health.json() == {
        "status": "ok",
        "runtime": "v2",
        "channel": "staging",
        "sha": "a" * 40,
    }
    assert version.json() == {
        "api": "v1",
        "runtime": "v2",
        "channel": "staging",
        "sha": "a" * 40,
    }


def test_hosted_demo_fails_closed_without_a_v2_model(tmp_path) -> None:
    app = create_demo_app(save_db_path=tmp_path / "runtime.sqlite", model=None, channel="production")
    with TestClient(app) as client:
        session_id = client.post("/api/v1/session", json={"genre": "fantasy"}).json()["session_id"]
        response = client.post("/api/v1/turn", json={"session_id": session_id, "command": "I wait."})

    assert response.status_code == 503
    assert response.json()["status"] == "runtime_failure"


def test_hosted_demo_rehydrates_a_persisted_session_after_process_restart(tmp_path) -> None:
    database = tmp_path / "runtime.sqlite"
    first_app = create_demo_app(save_db_path=database, model=StubTurnModel(), channel="staging")
    with TestClient(first_app) as client:
        session_id = client.post("/api/v1/session", json={"genre": "mystery"}).json()["session_id"]

    restarted_app = create_demo_app(save_db_path=database, model=StubTurnModel(), channel="staging")
    with TestClient(restarted_app) as client:
        response = client.post(
            "/api/v1/turn",
            json={"session_id": session_id, "genre": "mystery", "command": "go to the west gallery"},
        )

    assert response.status_code == 200
