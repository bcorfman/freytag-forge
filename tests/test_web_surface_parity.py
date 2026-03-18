from __future__ import annotations

from fastapi.testclient import TestClient

from storygame.web import create_app
from storygame.web_demo import create_demo_app
from tests.narrator_stubs import StubNarrator


class _PassThroughEditor:
    def review_opening(self, lines, active_goal):  # noqa: ANN001
        return lines

    def review_turn(self, lines, active_goal, turn_index, debug=False):  # noqa: ANN001
        return lines


class _StubDirector:
    def compose_opening(self, state):  # noqa: ANN001
        return list(state.world_package.get("story_plan", {}).get("setup_paragraphs", ()))

    def review_turn(self, state, lines, events, debug=False):  # noqa: ANN001
        return lines


def _local_client(tmp_path) -> TestClient:
    return TestClient(
        create_app(
            save_db_path=tmp_path / "web_saves.sqlite",
            narrator_mode="openai",
            narrator=StubNarrator("A cold certainty settles over the threshold."),
            output_editor=_PassThroughEditor(),
            story_director=_StubDirector(),
        )
    )


def _demo_client(tmp_path) -> TestClient:
    return TestClient(
        create_demo_app(
            save_db_path=tmp_path / "web_demo_saves.sqlite",
            narrator_mode="openai",
            narrator=StubNarrator("A cold certainty settles over the threshold."),
            output_editor=_PassThroughEditor(),
            story_director=_StubDirector(),
        )
    )


def test_first_substantive_turn_matches_between_local_web_and_demo(tmp_path):
    local_client = _local_client(tmp_path)
    demo_client = _demo_client(tmp_path)

    local_response = local_client.post("/turn", json={"command": "go north", "seed": 31})
    assert local_response.status_code == 200

    session_id = demo_client.post("/api/v1/session", json={"seed": 31}).json()["session_id"]
    demo_response = demo_client.post("/api/v1/turn", json={"session_id": session_id, "command": "go north"})
    assert demo_response.status_code == 200

    local_payload = local_response.json()
    demo_payload = demo_response.json()

    assert local_payload["action_raw"] == demo_payload["action_raw"]
    assert local_payload["beat"] == demo_payload["beat"]
    assert local_payload["continued"] == demo_payload["continued"]
    assert local_payload["lines"] == demo_payload["lines"]
    assert local_payload["state"]["location"] == demo_payload["state"]["location"]
    assert local_payload["state"]["room_name"] == demo_payload["state"]["room_name"]
    assert local_payload["state"]["turn_index"] == demo_payload["state"]["turn_index"]
