from __future__ import annotations

from fastapi.testclient import TestClient

from storygame.llm.story_director import StoryDirector
from storygame.engine.freeform import RuleBasedFreeformProposalAdapter
from storygame.persistence.savegame_sqlite import SqliteSaveStore
from storygame.web import create_app
from tests.fast_fixtures import InMemorySaveStore
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


class _RaisingDirector:
    def compose_opening(self, state):  # noqa: ANN001, ARG002
        raise RuntimeError("Story bootstrap unavailable.")

    def review_turn(self, state, lines, events, debug=False):  # noqa: ANN001, ARG002
        return lines


def _client(tmp_path, save_store=None):
    db_path = tmp_path / "web_saves.sqlite"
    return TestClient(
        create_app(
            save_db_path=db_path,
            narrator=StubNarrator(),
            output_editor=_PassThroughEditor(),
            story_director=_StubDirector(),
            save_store=InMemorySaveStore() if save_store is None else save_store,
            freeform_adapter=RuleBasedFreeformProposalAdapter(),
        )
    )


def test_turn_endpoint_starts_run_and_tracks_session(tmp_path):
    client = _client(tmp_path)
    response = client.post(
        "/turn",
        json={"command": "go north", "seed": 19, "genre": "thriller", "session_length": "long", "tone": "dark"},
    )
    assert response.status_code == 200

    payload = response.json()
    assert "run_id" in payload
    assert payload["state"]["turn_index"] == 1
    start_location = payload["state"]["location"]
    assert payload["lines"]
    assert payload["lines"][0]
    assert payload["lines"][-1]
    assert payload["lines"][0].startswith(">GO NORTH")
    assert any(line.startswith(">GO NORTH") for line in payload["lines"])
    assert payload["state"]["genre"] == "thriller"
    assert payload["state"]["session_length"] == "long"
    assert payload["state"]["tone"] == "dark"
    assert payload["state"]["plot_curve_id"] in {
        "thriller_macguffin_clock",
        "thriller_political_conspiracy",
    }
    assert payload["state"]["story_outline_id"]
    run_id = payload["run_id"]
    assert payload["continued"] is True

    response = client.post("/turn", json={"command": "look", "run_id": run_id, "debug": False})
    assert response.status_code == 200
    payload = response.json()
    assert payload["run_id"] == run_id
    assert payload["state"]["location"] == start_location
    assert payload["state"]["turn_index"] == 2
    assert response.status_code == 200


def test_save_and_load_are_available_through_web_turn_endpoint(tmp_path):
    client = _client(
        tmp_path,
        save_store=SqliteSaveStore(tmp_path / "web_saves.sqlite", check_same_thread=False),
    )
    response = client.post("/turn", json={"command": "go north", "seed": 7})
    assert response.status_code == 200
    run_id = response.json()["run_id"]

    pre_move = client.post("/turn", json={"run_id": run_id, "command": "go north"})
    assert pre_move.status_code == 200

    saved = client.post("/turn", json={"run_id": run_id, "command": "/save checkpoint"})
    assert saved.status_code == 200
    assert any("Saved to slot 'checkpoint'." in line for line in saved.json()["lines"])

    move_payload = pre_move.json()
    room_after_move = move_payload["state"]["location"]
    room_inventory = tuple(move_payload["state"]["inventory"])
    # fallback for empty-room seeds: ask for look output and take first known item from lines is unsupported,
    # so use a no-op take to keep endpoint behavior validated.
    item_id = room_inventory[0] if room_inventory else "missing_item"

    moved = client.post("/turn", json={"run_id": run_id, "command": f"take {item_id}"})
    assert moved.status_code == 200
    assert moved.json()["state"]["location"] == room_after_move

    loaded = client.post("/turn", json={"run_id": run_id, "command": "/load checkpoint"})
    assert loaded.status_code == 200
    loaded_payload = loaded.json()
    assert any("Loaded from slot 'checkpoint'." in line for line in loaded_payload["lines"])
    assert loaded_payload["state"]["location"] == room_after_move





def test_web_ui_bootstraps_new_scene_after_new_game_click(tmp_path):
    client = _client(tmp_path)
    response = client.get("/")
    assert response.status_code == 200
    html = response.text
    assert "async function startNewGame()" in html
    assert "await startNewGame();" in html
    assert "Ready. Save/load are available via commands, e.g. save checkpoint / load checkpoint." not in html


def test_bootstrap_only_response_includes_opening_and_initial_room_block(tmp_path):
    client = TestClient(
        create_app(
            save_db_path=tmp_path / "web_saves.sqlite",
            narrator=StubNarrator("Rain needles the stone.\n\nDaria keeps the file close.\n\nThe case starts now."),
            output_editor=_PassThroughEditor(),
            story_director=_StubDirector(),
        )
    )
    response = client.post("/turn", json={"command": "start", "seed": 91})
    assert response.status_code == 200
    payload = response.json()
    assert payload["beat"] == "setup_scene"
    assert payload["lines"]
    assert payload["lines"][0].startswith(">START")


def test_web_bootstrap_uses_fast_story_director_path_by_default(tmp_path, monkeypatch):
    observed = {"fast": 0}

    def _fast(self, state):  # noqa: ANN001
        observed["fast"] += 1
        lines = ["Fast opening one.", "Fast opening two.", "Fast opening three."]
        state.world_package["llm_story_bundle"] = {
            "opening_paragraphs": tuple(lines),
            "assistant_name": "Daria Stone",
            "actionable_objective": "Open the case file first.",
        }
        return list(lines)

    def _slow(self, state):  # noqa: ANN001, ARG002
        raise AssertionError("web should not use the slow compose_opening path by default")

    monkeypatch.setattr(StoryDirector, "compose_opening_fast", _fast)
    monkeypatch.setattr(StoryDirector, "compose_opening", _slow)

    client = TestClient(
        create_app(
            save_db_path=tmp_path / "web_saves.sqlite",
            narrator=StubNarrator("Opening fallback."),
            save_store=InMemorySaveStore(),
        )
    )

    response = client.post("/turn", json={"command": "start", "seed": 91})

    assert response.status_code == 200
    assert observed["fast"] == 1




















def test_first_substantive_command_does_not_repeat_opening_text(tmp_path):
    client = _client(tmp_path)
    response = client.post("/turn", json={"command": "Daria, knock on the door", "seed": 22})
    assert response.status_code == 200
    payload = response.json()
    assert payload["beat"] != "setup_scene"
    assert payload["lines"]
    assert payload["lines"][0].startswith(">DARIA, KNOCK ON THE DOOR")
