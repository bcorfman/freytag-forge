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
        assert turn.json()["state"] == {"location": "front_steps", "room_name": "front_steps", "turn_index": 1}
        assert turn.json()["model_calls"] == 1

        loaded = client.post("/api/v1/session/load", json={"session_id": session_id, "genre": "mystery"})
        assert loaded.status_code == 200
        assert loaded.json()["state"]["turn_index"] == 1


def test_hosted_demo_fails_closed_without_a_v2_model(tmp_path) -> None:
    app = create_demo_app(save_db_path=tmp_path / "runtime.sqlite", model=None, channel="production")
    with TestClient(app) as client:
        session_id = client.post("/api/v1/session", json={"genre": "fantasy"}).json()["session_id"]
        response = client.post("/api/v1/turn", json={"session_id": session_id, "command": "I wait."})

    assert response.status_code == 503
    assert response.json()["status"] == "runtime_failure"
