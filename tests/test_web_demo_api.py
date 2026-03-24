from __future__ import annotations

import logging
import json
from datetime import UTC, datetime, timedelta

from fastapi.testclient import TestClient

from storygame.engine.world import build_default_state
from storygame.llm.adapters import CloudflareWorkersAIAdapter
from storygame.llm.story_director import StoryDirector
from storygame.web_demo import _build_demo_narrator, create_demo_app
from tests.narrator_stubs import StubNarrator

_OPENING_TEXT = "Rain needles the stone.\n\nDaria keeps the file close.\n\nThe case starts now."


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


class _BundleDirector:
    def compose_opening(self, state):  # noqa: ANN001
        lines = ("Rain needles the stone.", "Daria keeps the file close.", "The case starts now.")
        state.world_package["llm_story_bundle"] = {"opening_paragraphs": lines}
        return list(lines)

    def review_turn(self, state, lines, events, debug=False):  # noqa: ANN001
        return lines


class _RaisingDirector:
    def compose_opening(self, state):  # noqa: ANN001, ARG002
        raise RuntimeError("Story bootstrap unavailable.")

    def review_turn(self, state, lines, events, debug=False):  # noqa: ANN001, ARG002
        return lines


class _Clock:
    def __init__(self, now: datetime) -> None:
        self.now = now

    def __call__(self) -> datetime:
        return self.now


class _FailingNarrator:
    def __init__(self, error_message: str) -> None:
        self._error_message = error_message

    def generate(self, _context):  # noqa: ANN001
        raise RuntimeError(self._error_message)


class _FakeResponse:
    def __init__(self, body: str) -> None:
        self._body = body.encode("utf-8")

    def read(self) -> bytes:
        return self._body

    def __enter__(self) -> _FakeResponse:
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        return None


def _client(tmp_path, clock: _Clock | None = None) -> TestClient:
    db_path = tmp_path / "web_demo_saves.sqlite"
    now_fn = (lambda: datetime.now(UTC)) if clock is None else clock
    return TestClient(
        create_demo_app(
            save_db_path=db_path,
            narrator_mode="openai",
            narrator=StubNarrator(_OPENING_TEXT),
            output_editor=_PassThroughEditor(),
            story_director=_StubDirector(),
            now_fn=now_fn,
        )
    )


def test_demo_health_endpoint_is_ok(tmp_path):
    client = _client(tmp_path)
    response = client.get("/api/v1/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_demo_app_allows_configured_cors_origin(tmp_path):
    client = TestClient(
        create_demo_app(
            save_db_path=tmp_path / "web_demo_saves.sqlite",
            narrator_mode="openai",
            narrator=StubNarrator(),
            output_editor=_PassThroughEditor(),
            story_director=_StubDirector(),
            cors_allow_origins=("https://example.github.io",),
        )
    )

    response = client.options(
        "/api/v1/session",
        headers={
            "Origin": "https://example.github.io",
            "Access-Control-Request-Method": "POST",
        },
    )

    assert response.status_code == 200
    assert response.headers["access-control-allow-origin"] == "https://example.github.io"


def test_demo_session_create_then_turn_flow(tmp_path):
    client = _client(tmp_path)
    created = client.post("/api/v1/session", json={"seed": 42, "genre": "mystery", "session_length": "short", "tone": "dark"})
    assert created.status_code == 200
    payload = created.json()
    session_id = payload["session_id"]
    assert session_id
    assert payload["seed"] == 42
    assert payload["expires_at"]

    turn = client.post("/api/v1/turn", json={"session_id": session_id, "command": "look"})
    assert turn.status_code == 200
    turn_payload = turn.json()
    assert turn_payload["status"] == "ok"
    assert turn_payload["session_id"] == session_id
    assert turn_payload["lines"]
    assert turn_payload["beat"] == "setup_scene"
    assert turn_payload["state"]["turn_index"] == 0
    assert turn_payload["state"]["session_id"] == session_id

    next_turn = client.post("/api/v1/turn", json={"session_id": session_id, "command": "go north"})
    assert next_turn.status_code == 200
    next_payload = next_turn.json()
    assert next_payload["lines"][0].startswith(">GO NORTH")
    assert next_payload["state"]["turn_index"] == 1


def test_demo_bootstrap_only_response_includes_opening_and_initial_room_block(tmp_path):
    client = TestClient(
            create_demo_app(
                save_db_path=tmp_path / "web_demo_saves.sqlite",
                narrator_mode="openai",
                narrator=StubNarrator(_OPENING_TEXT),
                output_editor=_PassThroughEditor(),
                story_director=_StubDirector(),
            )
    )
    session_id = client.post("/api/v1/session", json={"seed": 42}).json()["session_id"]

    turn = client.post("/api/v1/turn", json={"session_id": session_id, "command": "look"})
    assert turn.status_code == 200
    payload = turn.json()
    assert payload["beat"] == "setup_scene"
    assert payload["lines"]
    assert payload["state"]["turn_index"] == 0
    assert any(payload["state"]["room_name"] in line for line in payload["lines"])


def test_demo_bootstrap_uses_fast_story_director_path_by_default(tmp_path, monkeypatch):
    observed = {"fast": 0}
    original_fast = StoryDirector.compose_opening_fast
    original_slow = StoryDirector.compose_opening

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
        raise AssertionError("web_demo should not use the slow compose_opening path by default")

    monkeypatch.setattr(StoryDirector, "compose_opening_fast", _fast)
    monkeypatch.setattr(StoryDirector, "compose_opening", _slow)

    client = TestClient(
        create_demo_app(
            save_db_path=tmp_path / "web_demo_saves.sqlite",
            narrator_mode="openai",
            narrator=StubNarrator(_OPENING_TEXT),
        )
    )
    session_id = client.post("/api/v1/session", json={"seed": 42}).json()["session_id"]

    turn = client.post("/api/v1/turn", json={"session_id": session_id, "command": "look"})

    assert turn.status_code == 200
    assert observed["fast"] == 1


def test_demo_bootstrap_prefers_narrator_opening_over_placeholder_story_plan(tmp_path):
    client = TestClient(
            create_demo_app(
                save_db_path=tmp_path / "web_demo_saves.sqlite",
                narrator_mode="openai",
                narrator=StubNarrator(_OPENING_TEXT),
                output_editor=_PassThroughEditor(),
                story_director=_StubDirector(),
            )
    )
    session_id = client.post("/api/v1/session", json={"seed": 42}).json()["session_id"]

    turn = client.post("/api/v1/turn", json={"session_id": session_id, "command": "look"})
    assert turn.status_code == 200
    payload = turn.json()
    assert any("Rain needles the stone." in line for line in payload["lines"])
    assert any("Daria keeps the file close." in line for line in payload["lines"])
    assert not any("The situation is still taking shape" in line for line in payload["lines"])


def test_demo_bootstrap_filters_directive_shaped_opening_paragraphs(tmp_path):
    client = TestClient(
        create_demo_app(
            save_db_path=tmp_path / "web_demo_saves.sqlite",
            narrator_mode="openai",
            narrator=StubNarrator(
                "The lantern throws a warm pool of light across the front steps.\n\n"
                "Daria Stone waits beside you, case file in hand.\n\n"
                "The evening feels still enough for the smallest sound to matter.\n\n"
                "Room name: Front Steps Room description: Broad stone steps rise to a carved oak door. "
                "Items: arrival_sedan Exits: north NPC interactions: Daria Stone stands beside you. "
                "Background events: None."
            ),
            output_editor=_PassThroughEditor(),
            story_director=_RaisingDirector(),
        )
    )
    session_id = client.post("/api/v1/session", json={"seed": 42}).json()["session_id"]

    turn = client.post("/api/v1/turn", json={"session_id": session_id, "command": "look"})

    assert turn.status_code == 200
    payload = turn.json()
    assert not any("Room name:" in line for line in payload["lines"])


def test_demo_bootstrap_requires_llm_authored_opening_and_fails_closed(tmp_path):
    client = TestClient(
        create_demo_app(
            save_db_path=tmp_path / "web_demo_saves.sqlite",
            narrator_mode="openai",
            narrator=StubNarrator(),
            output_editor=_PassThroughEditor(),
            story_director=_StubDirector(),
        )
    )
    session_id = client.post("/api/v1/session", json={"seed": 42}).json()["session_id"]

    turn = client.post("/api/v1/turn", json={"session_id": session_id, "command": "look"})
    assert turn.status_code == 503
    assert turn.json() == {
        "status": "service_unavailable",
        "detail": "Narration service is temporarily unavailable.",
    }


def test_demo_bootstrap_falls_through_to_narrator_when_story_bootstrap_fails(tmp_path):
    client = TestClient(
        create_demo_app(
            save_db_path=tmp_path / "web_demo_saves.sqlite",
            narrator_mode="openai",
            narrator=StubNarrator(_OPENING_TEXT),
            output_editor=_PassThroughEditor(),
            story_director=_RaisingDirector(),
        )
    )
    session_id = client.post("/api/v1/session", json={"seed": 42}).json()["session_id"]

    turn = client.post("/api/v1/turn", json={"session_id": session_id, "command": "look"})

    assert turn.status_code == 200
    payload = turn.json()
    assert payload["status"] == "ok"
    assert any("Rain needles the stone." in line for line in payload["lines"])


def test_demo_bootstrap_fallback_narrator_normalizes_assistant_targeting_before_validation(tmp_path):
    client = TestClient(
        create_demo_app(
            save_db_path=tmp_path / "web_demo_saves.sqlite",
            narrator_mode="openai",
            narrator=StubNarrator(
                "Rain needles the stone.\n\n"
                "Daria Stone, your assistant, studies the foyer windows.\n\n"
                "You need to question Daria Stone about her involvement before you go inside."
            ),
            output_editor=_PassThroughEditor(),
            story_director=_RaisingDirector(),
        )
    )
    session_id = client.post("/api/v1/session", json={"seed": 42}).json()["session_id"]

    turn = client.post("/api/v1/turn", json={"session_id": session_id, "command": "look"})

    assert turn.status_code == 200
    payload = turn.json()
    assert payload["status"] == "ok"
    assert any("consult Daria Stone" in line for line in payload["lines"])
    assert not any("question Daria Stone" in line for line in payload["lines"])


def test_demo_bootstrap_fallback_drops_truncated_fourth_paragraph(tmp_path):
    client = TestClient(
        create_demo_app(
            save_db_path=tmp_path / "web_demo_saves.sqlite",
            narrator_mode="openai",
            narrator=StubNarrator(
                "Detective Elias Wren stood at the entrance of the grand mansion, the warm sunlight catching on the stonework.\n\n"
                "As he stepped onto the front steps, Daria Stone watched him from beside the heavy door.\n\n"
                "\"Good morning, Detective Wren,\" Daria said. \"I've been expecting you.\"\n\n"
                "Detective Wren's eyes scanned the area, taking in the manicured lawn and the perfectly trimmed hedges. A small, sleek car was parked by the side of the driveway, its"
            ),
            output_editor=_PassThroughEditor(),
            story_director=_RaisingDirector(),
        )
    )
    session_id = client.post("/api/v1/session", json={"seed": 42}).json()["session_id"]

    turn = client.post("/api/v1/turn", json={"session_id": session_id, "command": "look"})

    assert turn.status_code == 200
    payload = turn.json()
    assert payload["status"] == "ok"
    assert not any("its." in line for line in payload["lines"])
    assert not any("its" == line.strip() for line in payload["lines"])
    assert not any("small, sleek car" in line for line in payload["lines"])


def test_demo_bootstrap_rejects_invalid_narrator_opening_and_fails_closed(tmp_path):
    client = TestClient(
        create_demo_app(
            save_db_path=tmp_path / "web_demo_saves.sqlite",
            narrator_mode="openai",
            narrator=StubNarrator(
                "Rain needles the stone.\n\n"
                "Daria Stone, your assistant, keeps the ledger page in hand.\n\n"
                "The ledger page lies exposed on the front steps."
            ),
            output_editor=_PassThroughEditor(),
            story_director=_RaisingDirector(),
        )
    )
    session_id = client.post("/api/v1/session", json={"seed": 42}).json()["session_id"]

    turn = client.post("/api/v1/turn", json={"session_id": session_id, "command": "look"})

    assert turn.status_code == 503
    assert turn.json() == {
        "status": "service_unavailable",
        "detail": "Narration service is temporarily unavailable.",
    }


def test_demo_bootstrap_failure_logs_debug_context_for_railway(tmp_path, caplog):
    client = TestClient(
        create_demo_app(
            save_db_path=tmp_path / "web_demo_saves.sqlite",
            narrator_mode="openai",
            narrator=StubNarrator(),
            output_editor=_PassThroughEditor(),
            story_director=_RaisingDirector(),
        )
    )
    session_id = client.post("/api/v1/session", json={"seed": 42}).json()["session_id"]

    with caplog.at_level(logging.WARNING):
        turn = client.post("/api/v1/turn", json={"session_id": session_id, "command": "look"})

    assert turn.status_code == 503
    assert "Bootstrap opening unavailable" in caplog.text
    assert "Story bootstrap unavailable." in caplog.text
    assert "debug=" in caplog.text
    assert session_id in caplog.text
    assert "'command': 'look'" in caplog.text
    assert "'active_goal':" in caplog.text
    assert "'room_name':" in caplog.text


def test_demo_bootstrap_failure_logs_bundle_opening_context(tmp_path, caplog):
    class _InvalidBundleDirector:
        def compose_opening(self, state):  # noqa: ANN001
            lines = (
                "Rain needles the stone.",
                "Daria Stone, your assistant, keeps the ledger page in hand.",
                "You are here to question Daria Stone about her involvement before you go inside.",
            )
            state.world_package["llm_story_bundle"] = {
                "assistant_name": "Daria Stone",
                "actionable_objective": "Review the case file first.",
                "opening_paragraphs": lines,
            }
            raise RuntimeError(
                "Opening validation failed: Daria Stone is framed as an assistant/contact and the direct question target at the same time."
            )

        def review_turn(self, state, lines, events, debug=False):  # noqa: ANN001, ARG002
            return lines

    client = TestClient(
        create_demo_app(
            save_db_path=tmp_path / "web_demo_saves.sqlite",
            narrator_mode="openai",
            narrator=StubNarrator(),
            output_editor=_PassThroughEditor(),
            story_director=_InvalidBundleDirector(),
        )
    )
    session_id = client.post("/api/v1/session", json={"seed": 42}).json()["session_id"]

    with caplog.at_level(logging.WARNING):
        turn = client.post("/api/v1/turn", json={"session_id": session_id, "command": "look"})

    assert turn.status_code == 503
    assert "assistant/contact and the direct question target" in caplog.text
    assert "bundle_opening_paragraphs" in caplog.text
    assert "question Daria Stone about her involvement" in caplog.text
    assert "bundle_actionable_objective" in caplog.text


def test_demo_bootstrap_uses_cloudflare_opening_without_openai_credentials(
    tmp_path,
    monkeypatch,
):
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    monkeypatch.delenv("FREYTAG_NARRATOR", raising=False)
    monkeypatch.setenv("CLOUDFLARE_WORKER_URL", "https://demo.example.workers.dev/api/narrate")

    observed_requests: list[dict[str, str]] = []

    def _fake_urlopen(request, timeout):  # type: ignore[no-untyped-def]
        observed_requests.append(json.loads(request.data.decode("utf-8")))
        body = observed_requests[-1]
        system = body.get("system", "")
        if "Narrator Agent" in system:
            return _FakeResponse(
                "{\"narration\":\"The evening air bites at your skin as you approach the mansion.\\n\\nDaria Stone waits nearby with the case file and watches the entrance.\\n\\nTonight's work is practical before it is grand: review the case file, scan the grounds, and decide which lead to press first.\"}"
            )
        raise AssertionError(f"Unexpected system prompt: {system}")

    monkeypatch.setattr("storygame.llm.story_agents.agents.urllib.request.urlopen", _fake_urlopen)
    client = TestClient(
        create_demo_app(
            save_db_path=tmp_path / "web_demo_saves.sqlite",
            narrator_mode="openai",
        )
    )
    session_id = client.post("/api/v1/session", json={"seed": 52}).json()["session_id"]

    turn = client.post("/api/v1/turn", json={"session_id": session_id, "command": "look"})
    assert turn.status_code == 200
    payload = turn.json()
    assert payload["status"] == "ok"
    assert payload["beat"] == "setup_scene"
    assert payload["lines"]
    assert any("The evening air bites at your skin" in line for line in payload["lines"])
    assert any("Tonight" in line and "work is practical before it is grand" in line for line in payload["lines"])
    assert any("Narrator Agent" in request.get("system", "") for request in observed_requests)
    assert not any("Story Bootstrap Agent" in request.get("system", "") for request in observed_requests)


def test_demo_bootstrap_uses_cloudflare_narrator_opening_when_story_bootstrap_json_is_unavailable(
    tmp_path,
    monkeypatch,
):
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    monkeypatch.delenv("FREYTAG_NARRATOR", raising=False)
    monkeypatch.setenv("CLOUDFLARE_WORKER_URL", "https://demo.example.workers.dev/api/narrate")

    observed_requests: list[dict[str, str]] = []

    def _fake_urlopen(request, timeout):  # type: ignore[no-untyped-def]
        observed_requests.append(json.loads(request.data.decode("utf-8")))
        body = observed_requests[-1]
        system = body.get("system", "")
        if "Narrator Agent" in system:
            return _FakeResponse(
                '{"narration":"The evening air bites as you face the mansion steps.\\n\\nDaria Stone waits nearby with the case file tucked under one arm.\\n\\nYou have only just arrived, and the practical work starts here."}'
            )
        raise AssertionError(f"Unexpected system prompt: {system}")

    monkeypatch.setattr("storygame.llm.story_agents.agents.urllib.request.urlopen", _fake_urlopen)
    monkeypatch.setattr(CloudflareWorkersAIAdapter, "generate", lambda self, context: "")
    client = TestClient(
        create_demo_app(
            save_db_path=tmp_path / "web_demo_saves.sqlite",
            narrator_mode="openai",
        )
    )
    session_id = client.post("/api/v1/session", json={"seed": 53}).json()["session_id"]

    turn = client.post("/api/v1/turn", json={"session_id": session_id, "command": "look"})

    assert turn.status_code == 200
    payload = turn.json()
    assert payload["status"] == "ok"
    assert any("evening air bites" in line.lower() for line in payload["lines"])
    assert not any("Story Bootstrap Agent" in request.get("system", "") for request in observed_requests)
    assert any("Narrator Agent" in request.get("system", "") for request in observed_requests)


def test_demo_bootstrap_normalizes_assistant_question_objective_from_story_agent(
    tmp_path,
    monkeypatch,
) -> None:
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    monkeypatch.delenv("FREYTAG_NARRATOR", raising=False)
    monkeypatch.setenv("CLOUDFLARE_WORKER_URL", "https://demo.example.workers.dev/api/narrate")

    def _fake_urlopen(request, timeout):  # type: ignore[no-untyped-def]
        body = json.loads(request.data.decode("utf-8"))
        system = body.get("system", "")
        if "Narrator Agent" in system:
            return _FakeResponse(
                "{\"narration\":\"The evening air bites at your skin as you approach the mansion.\\n\\nDaria Stone waits by the door with the case file.\\n\\nTonight's work is practical before it is grand: question Daria Stone about the foyer and inspect the front steps.\"}"
            )
        raise AssertionError(f"Unexpected system prompt: {system}")

    monkeypatch.setattr("storygame.llm.story_agents.agents.urllib.request.urlopen", _fake_urlopen)
    client = TestClient(
        create_demo_app(
            save_db_path=tmp_path / "web_demo_saves.sqlite",
            narrator_mode="openai",
        )
    )
    session_id = client.post("/api/v1/session", json={"seed": 52}).json()["session_id"]

    turn = client.post("/api/v1/turn", json={"session_id": session_id, "command": "look"})

    assert turn.status_code == 200
    payload = turn.json()
    assert payload["status"] == "ok"
    assert any("consult Daria Stone" in line for line in payload["lines"])


def test_demo_bootstrap_normalizes_assistant_targeting_inside_opening_paragraphs(
    tmp_path,
    monkeypatch,
) -> None:
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    monkeypatch.delenv("FREYTAG_NARRATOR", raising=False)
    monkeypatch.setenv("CLOUDFLARE_WORKER_URL", "https://demo.example.workers.dev/api/narrate")

    def _fake_urlopen(request, timeout):  # type: ignore[no-untyped-def]
        body = json.loads(request.data.decode("utf-8"))
        system = body.get("system", "")
        if "Narrator Agent" in system:
            return _FakeResponse(
                "{\"narration\":\"The evening air bites at your skin as you approach the mansion.\\n\\nDaria Stone, your assistant, studies the foyer windows from inside the estate.\\n\\nYou are here to question Daria Stone about her involvement before you go inside.\"}"
            )
        raise AssertionError(f"Unexpected system prompt: {system}")

    monkeypatch.setattr("storygame.llm.story_agents.agents.urllib.request.urlopen", _fake_urlopen)
    client = TestClient(
        create_demo_app(
            save_db_path=tmp_path / "web_demo_saves.sqlite",
            narrator_mode="openai",
        )
    )
    session_id = client.post("/api/v1/session", json={"seed": 52}).json()["session_id"]

    turn = client.post("/api/v1/turn", json={"session_id": session_id, "command": "look"})

    assert turn.status_code == 200
    payload = turn.json()
    assert payload["status"] == "ok"
    assert any("consult Daria Stone" in line for line in payload["lines"])
    assert not any("question Daria Stone" in line for line in payload["lines"])


def test_demo_freeform_turn_uses_cloudflare_story_agent_without_openai_credentials(tmp_path, monkeypatch):
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    monkeypatch.delenv("FREYTAG_NARRATOR", raising=False)
    monkeypatch.setenv("CLOUDFLARE_WORKER_URL", "https://demo.example.workers.dev/api/narrate")

    observed_requests: list[dict[str, str]] = []

    def _fake_urlopen(request, timeout):  # type: ignore[no-untyped-def]
        observed_requests.append(json.loads(request.data.decode("utf-8")))
        body = observed_requests[-1]
        system = body.get("system", "")
        if "Freeform Action Planner Agent" in system:
            return _FakeResponse(
                '{"narration":"{\\"dialog_proposal\\":{\\"speaker\\":\\"daria_stone\\",\\"text\\":\\"I keep to practical clothes. The weather here punishes vanity.\\",\\"tone\\":\\"in_world\\"},\\"action_proposal\\":{\\"intent\\":\\"ask_about\\",\\"targets\\":[\\"daria_stone\\"],\\"arguments\\":{\\"topic\\":\\"appearance\\"},\\"proposed_effects\\":[\\"asked:appearance\\"]}}"}'
            )
        return _FakeResponse('{"narration":"Daria says: \\"I keep to practical clothes. The weather here punishes vanity.\\""}')

    monkeypatch.setattr("storygame.llm.story_agents.agents.urllib.request.urlopen", _fake_urlopen)
    client = TestClient(
        create_demo_app(
            save_db_path=tmp_path / "web_demo_saves.sqlite",
            narrator_mode="openai",
        )
    )
    session_id = client.post("/api/v1/session", json={"seed": 52}).json()["session_id"]

    response = client.post("/api/v1/turn", json={"session_id": session_id, "command": "Daria, tell me about your outfit"})

    assert response.status_code == 200
    payload = response.json()
    assert payload["state"]["turn_index"] == 1
    assert any("practical clothes" in line.lower() for line in payload["lines"])
    assert any("Freeform Action Planner Agent" in request.get("system", "") for request in observed_requests)


def test_demo_first_substantive_command_does_not_repeat_opening_text(tmp_path):
    client = _client(tmp_path)
    session_id = client.post("/api/v1/session", json={"seed": 43}).json()["session_id"]

    response = client.post("/api/v1/turn", json={"session_id": session_id, "command": "Daria, knock on the door"})
    assert response.status_code == 200
    payload = response.json()
    assert payload["beat"] != "setup_scene"
    assert payload["state"]["turn_index"] == 0
    assert payload["lines"][0].startswith(">DARIA, KNOCK ON THE DOOR")
    assert any("story response unavailable" in line.lower() for line in payload["lines"])


def test_demo_turn_unknown_session_returns_404(tmp_path):
    client = _client(tmp_path)
    response = client.post("/api/v1/turn", json={"session_id": "missing", "command": "look"})
    assert response.status_code == 404
    assert "Unknown or expired session_id 'missing'." in response.text


def test_demo_session_expiry_is_enforced(tmp_path):
    clock = _Clock(datetime(2026, 3, 16, 12, 0, tzinfo=UTC))
    db_path = tmp_path / "web_demo_saves.sqlite"
    client = TestClient(
            create_demo_app(
                save_db_path=db_path,
                narrator_mode="openai",
                narrator=StubNarrator(_OPENING_TEXT),
                output_editor=_PassThroughEditor(),
                story_director=_StubDirector(),
                session_ttl_seconds=60,
            now_fn=clock,
        )
    )
    created = client.post("/api/v1/session", json={"seed": 9})
    assert created.status_code == 200
    session_id = created.json()["session_id"]

    clock.now = clock.now + timedelta(seconds=61)
    expired = client.post("/api/v1/turn", json={"session_id": session_id, "command": "look"})
    assert expired.status_code == 404
    assert f"Unknown or expired session_id '{session_id}'." in expired.text


def test_demo_narrator_defaults_to_cloudflare_when_worker_url_set(monkeypatch):
    monkeypatch.setenv("CLOUDFLARE_WORKER_URL", "https://demo.example.workers.dev/api/narrate")
    narrator = _build_demo_narrator("openai")
    assert isinstance(narrator, CloudflareWorkersAIAdapter)


def test_demo_session_turn_cap_returns_quota_exhausted_status(tmp_path):
    client = TestClient(
            create_demo_app(
                save_db_path=tmp_path / "web_demo_saves.sqlite",
                narrator_mode="openai",
                narrator=StubNarrator(_OPENING_TEXT),
                output_editor=_PassThroughEditor(),
                story_director=_StubDirector(),
                session_turn_cap=1,
        )
    )
    created = client.post("/api/v1/session", json={"seed": 41})
    session_id = created.json()["session_id"]

    first = client.post("/api/v1/turn", json={"session_id": session_id, "command": "look"})
    assert first.status_code == 200

    second = client.post("/api/v1/turn", json={"session_id": session_id, "command": "go north"})
    assert second.status_code == 200

    third = client.post("/api/v1/turn", json={"session_id": session_id, "command": "look"})
    assert third.status_code == 429
    payload = third.json()
    assert payload["status"] == "quota_exhausted"
    assert "turn cap" in payload["detail"].lower()


def test_demo_ip_rate_limit_returns_rate_limited_status(tmp_path):
    clock = _Clock(datetime(2026, 3, 16, 12, 0, tzinfo=UTC))
    client = TestClient(
            create_demo_app(
                save_db_path=tmp_path / "web_demo_saves.sqlite",
                narrator_mode="openai",
                narrator=StubNarrator(_OPENING_TEXT),
                output_editor=_PassThroughEditor(),
                story_director=_StubDirector(),
                ip_rate_limit_per_min=2,
            now_fn=clock,
        )
    )
    session_a = client.post("/api/v1/session", json={"seed": 1}).json()["session_id"]
    session_b = client.post("/api/v1/session", json={"seed": 2}).json()["session_id"]

    bootstrap = client.post("/api/v1/turn", json={"session_id": session_a, "command": "look"})
    assert bootstrap.status_code == 200

    first = client.post("/api/v1/turn", json={"session_id": session_a, "command": "go north"})
    assert first.status_code == 200

    second = client.post("/api/v1/turn", json={"session_id": session_b, "command": "go north"})
    assert second.status_code == 429
    payload = second.json()
    assert payload["status"] == "rate_limited"


def test_demo_ip_daily_cap_returns_rate_limited_status(tmp_path):
    clock = _Clock(datetime(2026, 3, 16, 12, 0, tzinfo=UTC))
    client = TestClient(
            create_demo_app(
                save_db_path=tmp_path / "web_demo_saves.sqlite",
                narrator_mode="openai",
                narrator=StubNarrator(_OPENING_TEXT),
                output_editor=_PassThroughEditor(),
                story_director=_StubDirector(),
                ip_rate_limit_per_min=10,
            ip_daily_turn_cap=2,
            now_fn=clock,
        )
    )
    session_a = client.post("/api/v1/session", json={"seed": 3}).json()["session_id"]
    session_b = client.post("/api/v1/session", json={"seed": 4}).json()["session_id"]

    bootstrap = client.post("/api/v1/turn", json={"session_id": session_a, "command": "look"})
    assert bootstrap.status_code == 200

    first = client.post("/api/v1/turn", json={"session_id": session_a, "command": "go north"})
    assert first.status_code == 200

    second = client.post("/api/v1/turn", json={"session_id": session_b, "command": "go north"})
    assert second.status_code == 429
    payload = second.json()
    assert payload["status"] == "rate_limited"
    assert "daily cap" in payload["detail"].lower()


def test_demo_quota_failure_from_narrator_is_fail_closed(tmp_path):
    client = TestClient(
            create_demo_app(
                save_db_path=tmp_path / "web_demo_saves.sqlite",
                narrator_mode="openai",
                narrator=_FailingNarrator("AI_QUOTA_EXCEEDED"),
                output_editor=_PassThroughEditor(),
                story_director=_BundleDirector(),
            )
    )
    session_id = client.post("/api/v1/session", json={"seed": 5}).json()["session_id"]
    bootstrap = client.post("/api/v1/turn", json={"session_id": session_id, "command": "look"})
    assert bootstrap.status_code == 200
    response = client.post("/api/v1/turn", json={"session_id": session_id, "command": "go north"})
    assert response.status_code == 429
    payload = response.json()
    assert payload["status"] == "quota_exhausted"


def test_demo_service_failure_from_narrator_is_fail_closed(tmp_path):
    client = TestClient(
            create_demo_app(
                save_db_path=tmp_path / "web_demo_saves.sqlite",
                narrator_mode="openai",
                narrator=_FailingNarrator("backend unavailable"),
                output_editor=_PassThroughEditor(),
                story_director=_BundleDirector(),
            )
    )
    session_id = client.post("/api/v1/session", json={"seed": 6}).json()["session_id"]
    bootstrap = client.post("/api/v1/turn", json={"session_id": session_id, "command": "look"})
    assert bootstrap.status_code == 200
    response = client.post("/api/v1/turn", json={"session_id": session_id, "command": "go north"})
    assert response.status_code == 503
    payload = response.json()
    assert payload["status"] == "service_unavailable"


def test_demo_service_failure_logs_underlying_narrator_error(tmp_path, caplog):
    client = TestClient(
            create_demo_app(
                save_db_path=tmp_path / "web_demo_saves.sqlite",
                narrator_mode="openai",
                narrator=_FailingNarrator("backend unavailable"),
                output_editor=_PassThroughEditor(),
                story_director=_BundleDirector(),
            )
    )
    session_id = client.post("/api/v1/session", json={"seed": 7}).json()["session_id"]
    bootstrap = client.post("/api/v1/turn", json={"session_id": session_id, "command": "look"})
    assert bootstrap.status_code == 200
    with caplog.at_level(logging.WARNING):
        response = client.post("/api/v1/turn", json={"session_id": session_id, "command": "go north"})
    assert response.status_code == 503
    assert "Narrator failed" in caplog.text
    assert "backend unavailable" in caplog.text
    assert session_id in caplog.text
    assert "command=go north" in caplog.text
    assert "beat=" in caplog.text
    assert "location=foyer" in caplog.text
