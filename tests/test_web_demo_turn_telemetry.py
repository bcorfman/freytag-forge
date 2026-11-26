from pathlib import Path

from fastapi.testclient import TestClient

from storygame.runtime.engine import RuntimeEngine
from storygame.runtime.pacing_replay import replay_pacing
from storygame.runtime.persistence import RuntimeStateSqliteStore
from storygame.story_package.loader import load_story_package
from storygame.web_demo import create_demo_app

PACKAGE = load_story_package(Path("data/stories/continuity-initiative"))


class _Narrator:
    def opening(self):
        return {"segments": [{"kind": "narration", "text": "The search begins."}]}

    def __call__(self, _command):
        return {"segments": [{"kind": "narration", "text": "The room waits."}]}


def _app(tmp_path):
    return create_demo_app(store_path=tmp_path / "sessions.sqlite", provider_factory=lambda _state: _Narrator())


def _session(client):
    response = client.post("/api/v1/session", json={"story_id": "continuity_initiative"})
    assert response.status_code == 200
    return response.json()["session_id"]


def _turn(client, session_id):
    return client.post("/api/v1/turn", json={"session_id": session_id, "player_input": "Listen."})


def test_telemetry_is_off_by_default(monkeypatch, tmp_path):
    calls = []
    monkeypatch.setattr("storygame.web_demo.replay_pacing", lambda _engine: calls.append(True))
    with TestClient(_app(tmp_path)) as client:
        payload = _turn(client, _session(client)).json()
    assert "pacing_replay" not in payload
    assert calls == []


def test_telemetry_is_present_on_each_normal_turn(monkeypatch, tmp_path):
    monkeypatch.setenv("FREYTAG_EXPOSE_TURN_TELEMETRY", "1")
    with TestClient(_app(tmp_path)) as client:
        session_id = _session(client)
        for _ in range(2):
            replay = _turn(client, session_id).json()["pacing_replay"]
            assert set(replay) == {"fired_event_ids", "null_grounding_ids"}
            assert all(isinstance(value, list) for value in replay.values())


def test_telemetry_does_not_change_payload_or_saved_state(monkeypatch, tmp_path):
    def run(root, enabled):
        root.mkdir()
        monkeypatch.setenv("FREYTAG_EXPOSE_TURN_TELEMETRY", "1" if enabled else "0")
        with TestClient(_app(root)) as client:
            session_id = _session(client)
            payloads = []
            for _ in range(3):
                payload = _turn(client, session_id).json()
                payload.pop("pacing_replay", None)
                payloads.append(payload)
        state = RuntimeStateSqliteStore(root / "sessions.sqlite").load(session_id, PACKAGE).snapshot()
        return payloads, state

    off = run(tmp_path / "off", False)
    on = run(tmp_path / "on", True)
    assert off == on


def test_replay_failure_is_observational(monkeypatch, tmp_path):
    monkeypatch.setenv("FREYTAG_EXPOSE_TURN_TELEMETRY", "1")
    monkeypatch.setattr("storygame.web_demo.replay_pacing", lambda _engine: (_ for _ in ()).throw(RuntimeError("boom")))
    with TestClient(_app(tmp_path)) as client:
        response = _turn(client, _session(client))
    assert response.status_code == 200
    assert response.json()["pacing_replay"] is None


def test_telemetry_reports_due_pacing_event(monkeypatch, tmp_path):
    monkeypatch.setenv("FREYTAG_EXPOSE_TURN_TELEMETRY", "1")
    app = _app(tmp_path)
    store = RuntimeStateSqliteStore(tmp_path / "sessions.sqlite")
    with TestClient(app) as client:
        session_id = _session(client)
        state = store.load(session_id, PACKAGE)
        scene = next(scene for scene in PACKAGE.scenes if scene.metadata.scene_id == "2A")
        state.current_scene_id = "2A"
        state.phase = scene.metadata.freytag_phase
        state._assert_scene_entry_fact("2A")
        state.turn_index = state.scene_entered_at_turn + 4
        store.save(session_id, state)
        expected = replay_pacing(RuntimeEngine(state, lambda _command: {}))
        actual = _turn(client, session_id).json()["pacing_replay"]
    assert actual["fired_event_ids"] == list(expected.fired_event_ids)
    assert actual["null_grounding_ids"] == list(expected.null_grounding_ids)
