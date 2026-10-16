from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from bench.core import advance_state_to_scene
from storygame.runtime import reference_resolution
from storygame.runtime.persistence import RuntimeStateSqliteStore
from storygame.story_package.loader import load_story_package
from storygame.web_demo import create_demo_app

PACKAGE = load_story_package(Path("data/stories/continuity-initiative"))


class _Provider:
    def __init__(self, calls: list[str]) -> None:
        self.calls = calls

    def opening(self) -> dict[str, object]:
        return {"segments": [{"kind": "narration", "text": "The opening."}]}

    def __call__(self, command: str) -> dict[str, object]:
        self.calls.append(command)
        return {"segments": [{"kind": "narration", "text": "The scene continues."}]}


def _seed_scene_2b(db_path: Path, session_id: str) -> None:
    store = RuntimeStateSqliteStore(db_path)
    state = store.load(session_id, PACKAGE)
    advance_state_to_scene(PACKAGE, state, "2B")
    store.save(session_id, state)


@pytest.fixture
def scene_2b(tmp_path):
    db_path = tmp_path / "sessions.sqlite"
    calls: list[str] = []
    app = create_demo_app(
        store_path=db_path,
        provider_factory=lambda _state: _Provider(calls),
    )
    with TestClient(app) as client:
        session = client.post("/api/v1/session", json={"story_id": "continuity_initiative"})
        assert session.status_code == 200
        session_id = session.json()["session_id"]
        _seed_scene_2b(db_path, session_id)
        yield client, session_id, calls, db_path


def test_ambiguous_turn_returns_question_without_provider_or_save(scene_2b) -> None:
    client, session_id, calls, db_path = scene_2b
    before = db_path.read_bytes()

    response = client.post(
        "/api/v1/turn",
        json={"session_id": session_id, "player_input": "Read the terminal."},
    )

    body = response.json()
    assert response.status_code == 200
    assert body["clarification"] == {
        "original_command": "Read the terminal.",
        "noun": "terminal",
        "options": [
            {"id": "archive_terminals", "name": "archive terminals"},
            {"id": "medical_terminal", "name": "medical terminal"},
        ],
        "round": 0,
    }
    assert body["lines"] == ["Do you mean the archive terminals or the medical terminal?"]
    assert body["segments"][0]["text"] == body["lines"][0]
    assert body["state"]["turn_index"] == 30
    assert calls == []
    assert db_path.read_bytes() == before


def test_clarification_answer_reaches_provider_with_full_name(scene_2b) -> None:
    client, session_id, calls, _db_path = scene_2b
    original = "Read the terminal."

    question = client.post(
        "/api/v1/turn",
        json={"session_id": session_id, "player_input": original},
    )
    response = client.post(
        "/api/v1/turn",
        json={
            "session_id": session_id,
            "player_input": "the medical one",
            "clarifies": original,
            "clarification_round": 0,
        },
    )

    assert question.status_code == 200
    assert response.status_code == 200
    assert "clarification" not in response.json()
    assert calls == ["Read the medical terminal."]
    assert response.json()["state"]["turn_index"] == 31


def test_unrelated_clarification_reply_is_a_fresh_command(scene_2b) -> None:
    client, session_id, calls, _db_path = scene_2b
    original = "Read the terminal."

    question = client.post(
        "/api/v1/turn",
        json={"session_id": session_id, "player_input": original},
    )
    response = client.post(
        "/api/v1/turn",
        json={
            "session_id": session_id,
            "player_input": "Look around.",
            "clarifies": original,
            "clarification_round": 0,
        },
    )

    assert question.status_code == 200
    assert response.status_code == 200
    assert "clarification" not in response.json()
    assert calls == ["Look around."]


def test_normal_turn_has_no_clarification_key(scene_2b) -> None:
    client, session_id, _calls, _db_path = scene_2b

    response = client.post(
        "/api/v1/turn",
        json={"session_id": session_id, "player_input": "Look around."},
    )

    assert response.status_code == 200
    assert "clarification" not in response.json()


def test_second_clarification_round_is_capped_into_a_normal_turn(scene_2b, monkeypatch) -> None:
    thing = reference_resolution._Thing
    monkeypatch.setattr(
        reference_resolution,
        "_scene_things",
        lambda _state: (
            thing("archive_terminals", "archive terminals", ("terminal",)),
            thing("medical_terminal", "medical terminal", ("terminal",)),
            thing("archive_desk", "archive desk", ("desk",)),
            thing("medical_desk", "medical desk", ("desk",)),
            thing("archive_console", "archive console", ("console",)),
            thing("medical_console", "medical console", ("console",)),
        ),
    )
    client, session_id, calls, _db_path = scene_2b
    original = "Read the terminal, then inspect the desk, then open the console."

    first = client.post(
        "/api/v1/turn",
        json={"session_id": session_id, "player_input": original},
    )
    second = client.post(
        "/api/v1/turn",
        json={
            "session_id": session_id,
            "player_input": "medical",
            "clarifies": original,
            "clarification_round": 0,
        },
    )
    second_original = second.json()["clarification"]["original_command"]
    third = client.post(
        "/api/v1/turn",
        json={
            "session_id": session_id,
            "player_input": "archive",
            "clarifies": second_original,
            "clarification_round": 1,
        },
    )

    assert first.status_code == 200
    assert second.status_code == 200
    assert second.json()["clarification"]["round"] == 1
    assert third.status_code == 200
    assert "clarification" not in third.json()
    assert calls == ["Read the medical terminal, then inspect the archive desk, then open the console."]


def test_fresh_session_does_not_restore_a_client_held_question(scene_2b) -> None:
    client, _old_session_id, calls, db_path = scene_2b

    session = client.post("/api/v1/session", json={"story_id": "continuity_initiative"})
    session_id = session.json()["session_id"]
    _seed_scene_2b(db_path, session_id)
    response = client.post(
        "/api/v1/turn",
        json={"session_id": session_id, "player_input": "medical"},
    )

    assert session.status_code == 200
    assert response.status_code == 200
    assert "clarification" not in response.json()
    assert calls == ["medical"]
