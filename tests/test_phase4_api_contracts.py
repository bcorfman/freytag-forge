"""HTTP and game-break rendering contracts for Phase 4."""

from pathlib import Path

from fastapi.testclient import TestClient

from storygame.runtime.persistence import RuntimeStateSqliteStore
from storygame.runtime.validation import ProgressionValidator
from storygame.story_package.loader import load_story_package
from storygame.web_demo import create_demo_app

PACKAGE = load_story_package(Path("data/stories/continuity-initiative"))


class _Provider:
    def __init__(self, payload: dict[str, object]) -> None:
        self.payload = payload

    def opening(self) -> dict[str, object]:
        return {"segments": [{"kind": "narration", "text": "The house settles."}]}

    def __call__(self, _player_input: str) -> dict[str, object]:
        return self.payload


def test_rejected_http_turn_never_returns_rejected_segments(tmp_path) -> None:
    text = "Brandon waits beside the door."
    app = create_demo_app(
        store_path=tmp_path / "rejected.sqlite",
        provider_factory=lambda _state: _Provider(
            {"segments": [{"kind": "narration", "text": text}], "selected_knowledge_ids": []}
        ),
    )

    with TestClient(app) as client:
        session_id = client.post("/api/v1/session", json={"story_id": "continuity_initiative"}).json()["session_id"]
        response = client.post(
            "/api/v1/turn", json={"session_id": session_id, "player_input": "Search the desk drawer."}
        )

    assert response.status_code == 409
    assert response.headers["X-Freytag-Rejection-Code"] == "narration_known_term_leak"
    assert text not in response.text
    assert "segments" not in response.json()
    assert "lines" not in response.json()


def test_accepted_http_turn_preserves_validated_segment_structure(tmp_path) -> None:
    text = "The loose screw glints beside the desk."
    provider = _Provider(
        {
            "segments": [
                {
                    "kind": "dialogue",
                    "speaker_id": "kristin",
                    "text": text,
                    "grounding_ids": [],
                }
            ],
            "selected_knowledge_ids": [],
        }
    )
    app = create_demo_app(store_path=tmp_path / "accepted.sqlite", provider_factory=lambda _state: provider)

    with TestClient(app) as client:
        session_id = client.post("/api/v1/session", json={"story_id": "continuity_initiative"}).json()["session_id"]
        response = client.post(
            "/api/v1/turn", json={"session_id": session_id, "player_input": "Search the desk drawer."}
        )

    assert response.status_code == 200
    assert response.json()["segments"] == [
        {"kind": "dialogue", "text": text, "speaker_id": "kristin", "grounding_ids": []}
    ]


def test_game_break_response_hides_candidate_until_proceed(monkeypatch, tmp_path) -> None:
    candidate_text = "The risky route exposes an unverified future consequence."
    monkeypatch.setattr(ProgressionValidator, "validate", lambda *_: ("brandon",))
    provider = _Provider({"segments": [{"kind": "narration", "text": candidate_text}]})
    store_path = tmp_path / "break.sqlite"
    app = create_demo_app(store_path=store_path, provider_factory=lambda _state: provider)

    with TestClient(app) as client:
        session_id = client.post("/api/v1/session", json={"story_id": "continuity_initiative"}).json()["session_id"]
        warning = client.post(
            "/api/v1/turn", json={"session_id": session_id, "player_input": "Search the desk drawer."}
        )
        warning_json = warning.json()
        proceed = client.post(
            "/api/v1/game-break",
            json={
                "session_id": session_id,
                "warning_id": warning_json["game_break"]["warning_id"],
                "decision": "proceed",
            },
        )

    assert warning.status_code == 200
    assert warning_json["game_break"] is not None
    assert warning_json["segments"] == []
    assert warning_json["lines"] == []
    assert candidate_text not in warning.text
    assert proceed.status_code == 200
    assert proceed.json()["segments"][0]["text"] == candidate_text


def test_return_to_scene_restores_the_persisted_pre_break_snapshot(monkeypatch, tmp_path) -> None:
    monkeypatch.setattr(ProgressionValidator, "validate", lambda *_: ("brandon",))
    store_path = tmp_path / "return.sqlite"
    app = create_demo_app(
        store_path=store_path,
        provider_factory=lambda _state: _Provider(
            {"segments": [{"kind": "narration", "text": "A risky consequence waits."}]}
        ),
    )

    with TestClient(app) as client:
        session_id = client.post("/api/v1/session", json={"story_id": "continuity_initiative"}).json()["session_id"]
        before = RuntimeStateSqliteStore(store_path).load(session_id, PACKAGE).snapshot()
        warning = client.post(
            "/api/v1/turn", json={"session_id": session_id, "player_input": "Search the desk drawer."}
        ).json()
        returned = client.post(
            "/api/v1/game-break",
            json={
                "session_id": session_id,
                "warning_id": warning["game_break"]["warning_id"],
                "decision": "return_to_scene",
            },
        )

    after = RuntimeStateSqliteStore(store_path).load(session_id, PACKAGE).snapshot()
    assert returned.status_code == 200
    assert after == before
