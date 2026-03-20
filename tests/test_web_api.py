from __future__ import annotations

from fastapi.testclient import TestClient

from storygame.web import _resolve_narrator_mode, create_app
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


def _client(tmp_path):
    db_path = tmp_path / "web_saves.sqlite"
    return TestClient(
        create_app(
            save_db_path=db_path,
            narrator_mode="openai",
            narrator=StubNarrator(),
            output_editor=_PassThroughEditor(),
            story_director=_StubDirector(),
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
    assert any(line.startswith(payload["state"]["room_name"] + "\n") for line in payload["lines"])
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
    client = _client(tmp_path)
    response = client.post("/turn", json={"command": "go north", "seed": 7})
    assert response.status_code == 200
    run_id = response.json()["run_id"]

    pre_move = client.post("/turn", json={"run_id": run_id, "command": "go north"})
    assert pre_move.status_code == 200

    saved = client.post("/turn", json={"run_id": run_id, "command": "save checkpoint"})
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

    loaded = client.post("/turn", json={"run_id": run_id, "command": "load checkpoint"})
    assert loaded.status_code == 200
    loaded_payload = loaded.json()
    assert any("Loaded from slot 'checkpoint'." in line for line in loaded_payload["lines"])
    assert loaded_payload["state"]["location"] == room_after_move


def test_unknown_web_run_id_returns_404(tmp_path):
    client = _client(tmp_path)
    response = client.post("/turn", json={"run_id": "does-not-exist", "command": "look"})
    assert response.status_code == 404
    assert "Unknown run_id 'does-not-exist'." in response.text


def test_resolve_narrator_mode_prefers_explicit_and_env(monkeypatch):
    assert _resolve_narrator_mode("  OLLAMA ") == "ollama"
    assert _resolve_narrator_mode(" OpenAI ") == "openai"

    monkeypatch.delenv("FREYTAG_NARRATOR", raising=False)
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    monkeypatch.delenv("OLLAMA_BASE_URL", raising=False)
    monkeypatch.delenv("OLLAMA_MODEL", raising=False)
    assert _resolve_narrator_mode(None) == "openai"

    monkeypatch.setenv("OPENAI_API_KEY", "abc")
    assert _resolve_narrator_mode(None) == "openai"

    monkeypatch.setenv("FREYTAG_NARRATOR", "ollama")
    assert _resolve_narrator_mode("  ") == "ollama"


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
            narrator_mode="openai",
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
    assert any(payload["state"]["room_name"] in line for line in payload["lines"])


def test_bootstrap_response_state_prefers_fact_backed_objective(tmp_path):
    class _FactGoalDirector:
        def compose_opening(self, state):  # noqa: ANN001
            state.active_goal = "stale in-memory goal"
            state.world_facts.assert_fact("active_goal", "Review the case file and press the strongest lead.")
            state.world_package["llm_story_bundle"] = {"opening_paragraphs": ["Opening line."]}
            return ["Opening line."]

        def review_turn(self, state, lines, events, debug=False):  # noqa: ANN001, ARG002
            return lines

    client = TestClient(
        create_app(
            save_db_path=tmp_path / "web_saves.sqlite",
            narrator_mode="openai",
            narrator=StubNarrator("Opening line."),
            output_editor=_PassThroughEditor(),
            story_director=_FactGoalDirector(),
        )
    )

    response = client.post("/turn", json={"command": "start", "seed": 91})
    assert response.status_code == 200
    payload = response.json()
    assert payload["state"]["objective"] == "Review the case file and press the strongest lead."


def test_bootstrap_only_response_prefers_narrator_opening_over_placeholder_story_plan(tmp_path):
    client = TestClient(
        create_app(
            save_db_path=tmp_path / "web_saves.sqlite",
            narrator_mode="openai",
            narrator=StubNarrator("Rain needles the stone.\n\nDaria keeps the file close.\n\nThe case starts now."),
            output_editor=_PassThroughEditor(),
            story_director=_StubDirector(),
        )
    )

    response = client.post("/turn", json={"command": "start", "seed": 91})
    assert response.status_code == 200
    payload = response.json()
    assert any("Rain needles the stone." in line for line in payload["lines"])
    assert any("Daria keeps the file close." in line for line in payload["lines"])
    assert not any("The situation is still taking shape" in line for line in payload["lines"])


def test_bootstrap_only_response_requires_llm_authored_opening(tmp_path):
    client = TestClient(
        create_app(
            save_db_path=tmp_path / "web_saves.sqlite",
            narrator_mode="openai",
            narrator=StubNarrator(),
            output_editor=_PassThroughEditor(),
            story_director=_StubDirector(),
        ),
        raise_server_exceptions=True,
    )

    try:
        client.post("/turn", json={"command": "start", "seed": 91})
    except RuntimeError as exc:
        assert "LLM-authored opening" in str(exc)
    else:
        raise AssertionError("Expected bootstrap-only web opening to fail without LLM-authored prose.")


def test_first_substantive_command_does_not_repeat_opening_text(tmp_path):
    client = _client(tmp_path)
    response = client.post("/turn", json={"command": "Daria, knock on the door", "seed": 22})
    assert response.status_code == 200
    payload = response.json()
    assert payload["beat"] != "setup_scene"
    assert payload["lines"]
    assert payload["lines"][0].startswith(">DARIA, KNOCK ON THE DOOR")
