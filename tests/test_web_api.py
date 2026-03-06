from __future__ import annotations

from fastapi.testclient import TestClient

from storygame.web import _resolve_narrator_mode, create_app


def _client(tmp_path):
    db_path = tmp_path / "web_saves.sqlite"
    return TestClient(create_app(save_db_path=db_path, narrator_mode="mock"))


def test_turn_endpoint_starts_run_and_tracks_session(tmp_path):
    client = _client(tmp_path)
    response = client.post("/turn", json={"command": "look", "seed": 19})
    assert response.status_code == 200

    payload = response.json()
    assert "run_id" in payload
    assert payload["state"]["location"] == "harbor"
    run_id = payload["run_id"]
    assert payload["continued"] is True
    assert payload["state"]["inventory"]

    response = client.post("/turn", json={"command": "go north", "run_id": run_id, "debug": False})
    assert response.status_code == 200
    payload = response.json()
    assert payload["run_id"] == run_id
    assert payload["state"]["location"] == "market"
    assert response.status_code == 200


def test_save_and_load_are_available_through_web_turn_endpoint(tmp_path):
    client = _client(tmp_path)
    response = client.post("/turn", json={"command": "look", "seed": 7})
    assert response.status_code == 200
    run_id = response.json()["run_id"]

    pre_move = client.post("/turn", json={"run_id": run_id, "command": "go north"})
    assert pre_move.status_code == 200

    saved = client.post("/turn", json={"run_id": run_id, "command": "save checkpoint"})
    assert saved.status_code == 200
    assert any("Saved to slot 'checkpoint'." in line for line in saved.json()["lines"])

    moved = client.post("/turn", json={"run_id": run_id, "command": "take bronze key"})
    assert moved.status_code == 200
    assert moved.json()["state"]["location"] == "market"
    assert "bronze_key" in moved.json()["state"]["inventory"]

    loaded = client.post("/turn", json={"run_id": run_id, "command": "load checkpoint"})
    assert loaded.status_code == 200
    loaded_payload = loaded.json()
    assert any("Loaded from slot 'checkpoint'." in line for line in loaded_payload["lines"])
    assert loaded_payload["state"]["location"] == "market"


def test_unknown_web_run_id_returns_404(tmp_path):
    client = _client(tmp_path)
    response = client.post("/turn", json={"run_id": "does-not-exist", "command": "look"})
    assert response.status_code == 404
    assert "Unknown run_id 'does-not-exist'." in response.text


def test_resolve_narrator_mode_prefers_explicit_and_env(monkeypatch):
    assert _resolve_narrator_mode("None") == "none"
    assert _resolve_narrator_mode("  OLLAMA ") == "ollama"

    monkeypatch.delenv("FREYTAG_NARRATOR", raising=False)
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    monkeypatch.delenv("OLLAMA_BASE_URL", raising=False)
    monkeypatch.delenv("OLLAMA_MODEL", raising=False)
    assert _resolve_narrator_mode(None) == "mock"

    monkeypatch.setenv("OPENAI_API_KEY", "abc")
    assert _resolve_narrator_mode(None) == "openai"

    monkeypatch.setenv("FREYTAG_NARRATOR", "none")
    assert _resolve_narrator_mode("  ") == "none"
