"""Hosted V2 adapter contracts."""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from storygame.authoring.compiler import load_compiled_story_fixture
from storygame.persistence.runtime_state_sqlite import RuntimeSaveError, RuntimeStateSqliteStore
from storygame.runtime.context import RuntimeContext
from storygame.runtime.state import bootstrap_runtime_state
from storygame.web_demo import create_demo_app


class _Model:
    def __init__(self) -> None:
        self.calls: list[bool] = []

    def play_turn(self, context: RuntimeContext, *, json_object: bool) -> object:
        self.calls.append(json_object)
        return {
            "narration": f"You act in {context.payload['world']['location']}.",
            "operations": [{"kind": "add", "path": "world.flags", "value": "acted"}],
            "beat_updates": [],
            "material_progress": True,
        }


def _client(tmp_path, model: _Model | None = None) -> TestClient:
    return TestClient(
        create_demo_app(
            save_db_path=tmp_path / "v2.sqlite",
            turn_model=_Model() if model is None else model,
            channel="staging",
            session_namespace="staging-test",
            cors_allow_origins=("https://example.test",),
        )
    )


def test_v2_session_opening_turn_and_load_round_trip(tmp_path) -> None:
    with _client(tmp_path) as client:
        created = client.post("/api/v1/session", json={"genre": "mystery"}).json()
        session_id = created["session_id"]
        opening = client.post("/api/v1/turn", json={"session_id": session_id, "command": "look"})
        assert opening.status_code == 200
        assert opening.json()["state"]["location"] == "square"

        turn = client.post("/api/v1/turn", json={"session_id": session_id, "command": "Search the square."})
        assert turn.status_code == 200
        assert turn.json()["state"]["turn_index"] == 1
        assert turn.json()["lines"] == ["You act in square."]
        assert turn.json()["model_calls"] == 1

        assert client.post("/api/v1/turn", json={"session_id": session_id, "command": "save"}).status_code == 200
        assert (
            client.post("/api/v1/turn", json={"session_id": session_id, "command": "load"}).json()["state"][
                "turn_index"
            ]
            == 1
        )


def test_v2_demo_keeps_channel_namespaces_isolated(tmp_path) -> None:
    model = _Model()
    with _client(tmp_path, model) as client:
        session_id = client.post("/api/v1/session", json={}).json()["session_id"]
    app = create_demo_app(
        save_db_path=tmp_path / "v2.sqlite",
        turn_model=model,
        channel="production",
        session_namespace="production-test",
    )
    with TestClient(app) as isolated:
        assert isolated.post("/api/v1/turn", json={"session_id": session_id, "command": "look"}).status_code == 404


def test_runtime_store_rejects_v1_schema_and_tampered_snapshot(tmp_path) -> None:
    path = tmp_path / "saves.sqlite"
    story = load_compiled_story_fixture("mystery")
    store = RuntimeStateSqliteStore(path, namespace="staging")
    store.conn.execute("CREATE TABLE state_snapshots(slot TEXT PRIMARY KEY, payload TEXT NOT NULL)")
    with pytest.raises(RuntimeSaveError, match="V1 saves") as legacy:
        store.load("legacy", story)
    assert legacy.value.code == "unsupported_save_version"
    store.save("valid", bootstrap_runtime_state(story))
    store.conn.execute("UPDATE runtime_sessions SET snapshot = '{}' WHERE session_id = 'valid'")
    with pytest.raises(RuntimeSaveError) as tampered:
        store.load("valid", story)
    assert tampered.value.code == "save_integrity_failed"
    store.close()


def test_v2_demo_preserves_cors_quota_and_request_id(tmp_path) -> None:
    with _client(tmp_path) as client:
        assert (
            client.options(
                "/api/v1/session", headers={"Origin": "https://example.test", "Access-Control-Request-Method": "POST"}
            ).headers["access-control-allow-origin"]
            == "https://example.test"
        )
        session_id = client.post("/api/v1/session", json={}).json()["session_id"]
        response = client.post("/api/v1/turn", json={"session_id": session_id, "command": "anything"})
        assert response.headers["x-request-id"]
        assert client.get("/api/v1/version").json()["channel"] == "staging"


def test_v2_demo_enforces_session_turn_quota(tmp_path) -> None:
    app = create_demo_app(
        save_db_path=tmp_path / "quota.sqlite",
        turn_model=_Model(),
        channel="staging",
        session_namespace="quota-test",
        session_turn_cap=1,
    )
    with TestClient(app) as client:
        session_id = client.post("/api/v1/session", json={}).json()["session_id"]
        assert client.post("/api/v1/turn", json={"session_id": session_id, "command": "act"}).status_code == 200
        limited = client.post("/api/v1/turn", json={"session_id": session_id, "command": "act again"})
        assert limited.status_code == 429
        assert limited.json()["status"] == "quota_exhausted"


def test_staging_evaluation_token_bypasses_only_staging_limits(tmp_path) -> None:
    app = create_demo_app(
        save_db_path=tmp_path / "evaluation.sqlite",
        turn_model=_Model(),
        channel="staging",
        session_namespace="evaluation-test",
        ip_rate_limit_per_min=1,
        evaluation_token="test-token",
    )
    with TestClient(app) as client:
        session_id = client.post("/api/v1/session", json={}).json()["session_id"]
        headers = {"X-Freytag-Evaluation-Token": "test-token"}
        assert (
            client.post("/api/v1/turn", json={"session_id": session_id, "command": "act"}, headers=headers).status_code
            == 200
        )
        assert (
            client.post(
                "/api/v1/turn", json={"session_id": session_id, "command": "again"}, headers=headers
            ).status_code
            == 200
        )
