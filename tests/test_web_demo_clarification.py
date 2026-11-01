from pathlib import Path

import pytest
from fastapi.testclient import TestClient

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
    # This endpoint test needs a 2B context, not a full persona playthrough.
    # The consolidated 2A incident is intentionally not solvable by the
    # generic "thorough" command used by the offline seeder.
    scene = next(scene for scene in PACKAGE.scenes if scene.metadata.scene_id == "2B")
    state.current_scene_id = "2B"
    state.phase = scene.metadata.freytag_phase
    state._assert_scene_entry_fact("2B")
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
