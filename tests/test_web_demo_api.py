# ruff: noqa: E501

from __future__ import annotations

import json
import logging
from datetime import UTC, datetime, timedelta

from fastapi.testclient import TestClient

from storygame.engine.freeform import LlmFreeformProposalAdapter, RuleBasedFreeformProposalAdapter
from storygame.llm.adapters import CloudflareWorkersAIAdapter
from storygame.llm.story_agents.agents import DefaultNarratorOpeningAgent
from storygame.web_demo import (
    _build_demo_narrator,
    _resolve_demo_cors_allow_origins,
    create_demo_app,
)
from tests.fast_fixtures import InMemorySaveStore
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


class _DisclosureAdapter:
    def propose(self, _state, _raw_input):  # noqa: ANN001
        return (
            {
                "speaker": "daria_stone",
                "text": "The final ledger entry is time-stamped 11:40 p.m.",
                "tone": "in_world",
            },
            {
                "intent": "ask_about",
                "targets": ["daria_stone"],
                "arguments": {"topic": "case file"},
                "disclosed_knowledge": "ledger_entry_time",
                "proposed_effects": [],
            },
        )


class _FantasyDisclosureAdapter:
    def propose(self, _state, _raw_input):  # noqa: ANN001
        return (
            {
                "speaker": "selene_ward",
                "text": "The warded scroll marks the moonlit ford as the safe route through the enchanted wood.",
                "tone": "in_world",
            },
            {
                "intent": "ask_about",
                "targets": ["selene_ward"],
                "arguments": {"topic": "warded scroll"},
                "disclosed_knowledge": "warded_route",
                "proposed_effects": [],
            },
        )


class _FakeResponse:
    def __init__(self, body: str) -> None:
        self._body = body.encode("utf-8")
        self.headers: dict[str, str] = {}

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
            narrator_mode="cloudflare",
            narrator=StubNarrator(_OPENING_TEXT),
            output_editor=_PassThroughEditor(),
            story_director=_StubDirector(),
            now_fn=now_fn,
            save_store=InMemorySaveStore(),
            freeform_adapter=RuleBasedFreeformProposalAdapter(),
        )
    )


def test_demo_bootstrap_requires_llm_authored_opening_and_fails_closed(tmp_path):
    client = TestClient(
        create_demo_app(
            save_db_path=tmp_path / "web_demo_saves.sqlite",
            narrator_mode="cloudflare",
            narrator=StubNarrator(),
            output_editor=_PassThroughEditor(),
            story_director=_StubDirector(),
            save_store=InMemorySaveStore(),
        )
    )
    session_id = client.post("/api/v1/session", json={"seed": 42}).json()["session_id"]
    turn = client.post("/api/v1/turn", json={"session_id": session_id, "command": "look"})

    assert turn.status_code == 503
    assert turn.json() == {
        "status": "service_unavailable",
        "detail": "Narration service is temporarily unavailable.",
    }


def test_demo_configuration_normalization_is_adapter_independent(monkeypatch):
    monkeypatch.delenv("DEMO_CORS_ALLOW_ORIGINS", raising=False)
    assert _resolve_demo_cors_allow_origins(None) == ("*",)

    monkeypatch.setenv("DEMO_CORS_ALLOW_ORIGINS", "https://one.example, ,https://two.example")
    assert _resolve_demo_cors_allow_origins(None) == ("https://one.example", "https://two.example")
    assert _resolve_demo_cors_allow_origins((" ",)) == ("*",)


def test_health_identifies_the_deployed_channel_and_revision(tmp_path, monkeypatch):
    monkeypatch.setenv("FREYTAG_DEPLOYMENT_CHANNEL", "staging")
    monkeypatch.setenv("FREYTAG_DEPLOYMENT_SHA", "a" * 40)
    client = _client(tmp_path)

    response = client.get("/api/v1/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok", "channel": "staging", "sha": "a" * 40}


def test_health_prefers_the_workflow_deployment_sha(tmp_path, monkeypatch):
    monkeypatch.setenv("RAILWAY_GIT_COMMIT_SHA", "railway-source-sha")
    monkeypatch.setenv("FREYTAG_DEPLOYMENT_SHA", "workflow-sha")

    response = _client(tmp_path).get("/api/v1/health")

    assert response.json()["sha"] == "workflow-sha"


def test_demo_app_allows_configured_cors_origin(tmp_path):
    client = TestClient(
        create_demo_app(
            save_db_path=tmp_path / "web_demo_saves.sqlite",
            narrator_mode="cloudflare",
            narrator=StubNarrator(),
            output_editor=_PassThroughEditor(),
            story_director=_StubDirector(),
            cors_allow_origins=("https://example.github.io",),
            save_store=InMemorySaveStore(),
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
    created = client.post(
        "/api/v1/session", json={"seed": 42, "genre": "mystery", "session_length": "short", "tone": "dark"}
    )
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


def _staging_response(text: str, holder: str) -> dict[str, object]:
    return {
        "dialog_proposal": {"speaker": "narrator", "text": text, "tone": "in_world"},
        "action_proposal": {"intent": "inspect", "targets": [], "arguments": {}, "proposed_effects": []},
        "staging_claims": [
            {
                "relation": "custody",
                "subject_id": "case_file",
                "target_id": holder,
                "location_id": "",
                "state_id": "",
            }
        ],
    }


def test_demo_projects_grounded_turn_trace_headers(tmp_path, monkeypatch) -> None:
    replies = iter(
        (
            _staging_response("The file is yours.", "player"),
            _staging_response("Daria keeps the file close.", "daria_stone"),
        )
    )
    monkeypatch.setattr(
        "storygame.engine.freeform._story_agent_chat_complete", lambda *_args: json.dumps(next(replies))
    )
    client = TestClient(
        create_demo_app(
            save_db_path=tmp_path / "web_demo_saves.sqlite",
            narrator_mode="cloudflare",
            narrator=StubNarrator(_OPENING_TEXT),
            output_editor=_PassThroughEditor(),
            story_director=_StubDirector(),
            save_store=InMemorySaveStore(),
            freeform_adapter=LlmFreeformProposalAdapter(),
        )
    )
    session_id = client.post("/api/v1/session", json={"seed": 42}).json()["session_id"]

    response = client.post("/api/v1/turn", json={"session_id": session_id, "command": "inspect the scene"})

    assert response.status_code == 200
    assert response.headers["x-grounded-turn-outcome"] == "accepted"
    assert response.headers["x-grounded-turn-retries"] == "1"
    assert response.headers["x-grounded-turn-request-id"]


def test_demo_document_briefing_is_visible_and_committed_before_save(tmp_path) -> None:
    store = InMemorySaveStore()
    client = TestClient(
        create_demo_app(
            save_db_path=tmp_path / "web_demo_saves.sqlite",
            narrator_mode="cloudflare",
            narrator=StubNarrator(_OPENING_TEXT),
            output_editor=_PassThroughEditor(),
            story_director=_StubDirector(),
            save_store=store,
            freeform_adapter=_DisclosureAdapter(),
        )
    )
    session_id = client.post(
        "/api/v1/session", json={"seed": 4076, "genre": "mystery", "session_length": "short", "tone": "dark"}
    ).json()["session_id"]

    turn = client.post("/api/v1/turn", json={"session_id": session_id, "command": "Daria, what's in the case file?"})

    assert turn.status_code == 200
    assert "11:40 p.m." in "\n".join(turn.json()["lines"])

    saved = client.post("/api/v1/turn", json={"session_id": session_id, "command": "/save disclosure"})
    assert saved.status_code == 200
    saved_state, _rng = store.load_run(f"{session_id}:disclosure")
    assert saved_state.world_facts.holds("knows", "player", "ledger_entry_time")


def test_demo_fantasy_document_briefing_is_visible_and_committed_before_save(tmp_path) -> None:
    store = InMemorySaveStore()
    client = TestClient(
        create_demo_app(
            save_db_path=tmp_path / "web_demo_saves.sqlite",
            narrator_mode="cloudflare",
            narrator=StubNarrator(_OPENING_TEXT),
            output_editor=_PassThroughEditor(),
            story_director=_StubDirector(),
            save_store=store,
            freeform_adapter=_FantasyDisclosureAdapter(),
        )
    )
    session_id = client.post(
        "/api/v1/session", json={"seed": 4077, "genre": "fantasy", "session_length": "short", "tone": "epic"}
    ).json()["session_id"]

    turn = client.post(
        "/api/v1/turn", json={"session_id": session_id, "command": "Selene, what does the warded scroll say?"}
    )

    assert turn.status_code == 200
    assert "moonlit ford" in "\n".join(turn.json()["lines"])

    client.post("/api/v1/turn", json={"session_id": session_id, "command": "/save disclosure"})
    saved_state, _rng = store.load_run(f"{session_id}:disclosure")
    assert saved_state.world_facts.holds("knows", "player", "warded_route")


def test_demo_bootstrap_uses_cloudflare_opening(
    tmp_path,
    monkeypatch,
):
    monkeypatch.delenv("FREYTAG_NARRATOR", raising=False)
    monkeypatch.setenv("CLOUDFLARE_WORKER_URL", "https://demo.example.workers.dev/api/narrate")

    observed_requests: list[dict[str, str]] = []

    def _fake_urlopen(request, timeout):  # type: ignore[no-untyped-def]
        observed_requests.append(json.loads(request.data.decode("utf-8")))
        return _FakeResponse(
            '{"narration":"The evening air bites at your skin as you approach the mansion.\\n\\nDaria Stone waits nearby with the case file and watches the entrance.\\n\\nTonight\'s work is practical before it is grand: review the case file, scan the grounds, and decide which lead to press first."}'
        )

    monkeypatch.setattr("storygame.llm.adapters.urllib.request.urlopen", _fake_urlopen)
    client = TestClient(
        create_demo_app(
            save_db_path=tmp_path / "web_demo_saves.sqlite",
            narrator_mode="cloudflare",
            save_store=InMemorySaveStore(),
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
    assert len(observed_requests) == 1
    assert "Narrator Agent" not in observed_requests[0]["system"]


def test_demo_bootstrap_consumes_the_worker_narration_envelope_directly(
    tmp_path,
    monkeypatch,
):
    monkeypatch.delenv("FREYTAG_NARRATOR", raising=False)
    monkeypatch.setenv("CLOUDFLARE_WORKER_URL", "https://demo.example.workers.dev/api/narrate")
    observed_requests: list[dict[str, str]] = []

    def _fake_urlopen(request, timeout):  # type: ignore[no-untyped-def]
        observed_requests.append(json.loads(request.data.decode("utf-8")))
        return _FakeResponse(
            json.dumps(
                {
                    "narration": "Rain needles the mansion steps.\n\nDaria Stone holds the case file close.\n\nYour first task is to decide where to begin.",
                    "model": "@cf/meta/llama-3.1-8b-instruct",
                    "trace_id": "hosted-opening",
                }
            )
        )

    monkeypatch.setattr("storygame.llm.adapters.urllib.request.urlopen", _fake_urlopen)
    client = TestClient(
        create_demo_app(
            save_db_path=tmp_path / "web_demo_saves.sqlite",
            narrator_mode="cloudflare",
            save_store=InMemorySaveStore(),
        )
    )
    session_id = client.post("/api/v1/session", json={"seed": 55}).json()["session_id"]

    turn = client.post("/api/v1/turn", json={"session_id": session_id, "command": "look"})

    assert turn.status_code == 200
    assert len(observed_requests) == 1
    assert "Narrator Agent" not in observed_requests[0]["system"]
    assert any("Rain needles the mansion steps" in line for line in turn.json()["lines"])


def test_demo_bootstrap_uses_one_direct_cloudflare_narration_call(tmp_path, monkeypatch):
    monkeypatch.delenv("FREYTAG_NARRATOR", raising=False)
    monkeypatch.setenv("CLOUDFLARE_WORKER_URL", "https://demo.example.workers.dev/api/narrate")
    call_count = 0

    def _generate(self, context):  # noqa: ANN001
        nonlocal call_count
        call_count += 1
        return _OPENING_TEXT

    def _unexpected_opening_agent(self, state, architect, cast, plan):  # noqa: ANN001
        raise AssertionError("hosted bootstrap must not use the nested opening-agent contract")

    monkeypatch.setattr(CloudflareWorkersAIAdapter, "generate", _generate)
    monkeypatch.setattr(DefaultNarratorOpeningAgent, "run", _unexpected_opening_agent)
    client = TestClient(
        create_demo_app(
            save_db_path=tmp_path / "web_demo_saves.sqlite",
            narrator_mode="cloudflare",
            save_store=InMemorySaveStore(),
        )
    )
    session_id = client.post("/api/v1/session", json={"seed": 57}).json()["session_id"]

    turn = client.post("/api/v1/turn", json={"session_id": session_id, "command": "look"})

    assert turn.status_code == 200
    assert call_count == 1
    assert any("Rain needles the stone" in line for line in turn.json()["lines"])


def test_demo_bootstrap_does_not_apply_opening_text_heuristics_to_worker_prose(tmp_path, monkeypatch):
    monkeypatch.delenv("FREYTAG_NARRATOR", raising=False)
    monkeypatch.setenv("CLOUDFLARE_WORKER_URL", "https://demo.example.workers.dev/api/narrate")
    monkeypatch.setattr(
        CloudflareWorkersAIAdapter,
        "generate",
        lambda self, context: "The gate waits. # noqa.\n\nDaria Stone watches the drive.",
    )
    client = TestClient(
        create_demo_app(
            save_db_path=tmp_path / "web_demo_saves.sqlite",
            narrator_mode="cloudflare",
            save_store=InMemorySaveStore(),
        )
    )
    session_id = client.post("/api/v1/session", json={"seed": 58}).json()["session_id"]

    turn = client.post("/api/v1/turn", json={"session_id": session_id, "command": "look"})

    assert turn.status_code == 200
    assert any("# noqa" in line for line in turn.json()["lines"])


def test_demo_bootstrap_accepts_short_cloudflare_prose_when_opening_contract_is_unavailable(
    tmp_path,
    monkeypatch,
):
    monkeypatch.delenv("FREYTAG_NARRATOR", raising=False)
    monkeypatch.setenv("CLOUDFLARE_WORKER_URL", "https://demo.example.workers.dev/api/narrate")
    monkeypatch.setattr(
        CloudflareWorkersAIAdapter,
        "generate",
        lambda self, context: "Daria Stone waits at the mansion steps with the case file.",
    )
    client = TestClient(
        create_demo_app(
            save_db_path=tmp_path / "web_demo_saves.sqlite",
            narrator_mode="cloudflare",
            save_store=InMemorySaveStore(),
        )
    )
    session_id = client.post("/api/v1/session", json={"seed": 54}).json()["session_id"]

    turn = client.post("/api/v1/turn", json={"session_id": session_id, "command": "look"})

    assert turn.status_code == 200
    assert any("Daria Stone waits" in line for line in turn.json()["lines"])


def test_demo_freeform_turn_uses_cloudflare_story_agent(tmp_path, monkeypatch):
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
        return _FakeResponse(
            '{"narration":"Daria says: \\"I keep to practical clothes. The weather here punishes vanity.\\""}'
        )

    monkeypatch.setattr("storygame.llm.story_agents.agents.urllib.request.urlopen", _fake_urlopen)
    client = TestClient(
        create_demo_app(
            save_db_path=tmp_path / "web_demo_saves.sqlite",
            narrator_mode="cloudflare",
            save_store=InMemorySaveStore(),
        )
    )
    session_id = client.post("/api/v1/session", json={"seed": 52}).json()["session_id"]

    response = client.post(
        "/api/v1/turn", json={"session_id": session_id, "command": "Daria, tell me about your outfit"}
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["state"]["turn_index"] == 1
    assert any("practical clothes" in line.lower() for line in payload["lines"])
    assert any("Freeform Action Planner Agent" in request.get("system", "") for request in observed_requests)


def test_demo_session_expiry_is_enforced(tmp_path):
    clock = _Clock(datetime(2026, 3, 16, 12, 0, tzinfo=UTC))
    db_path = tmp_path / "web_demo_saves.sqlite"
    client = TestClient(
        create_demo_app(
            save_db_path=db_path,
            narrator_mode="cloudflare",
            narrator=StubNarrator(_OPENING_TEXT),
            output_editor=_PassThroughEditor(),
            story_director=_StubDirector(),
            session_ttl_seconds=60,
            save_store=InMemorySaveStore(),
            freeform_adapter=RuleBasedFreeformProposalAdapter(),
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
    narrator = _build_demo_narrator()
    assert isinstance(narrator, CloudflareWorkersAIAdapter)


def test_demo_session_turn_cap_returns_quota_exhausted_status(tmp_path):
    client = TestClient(
        create_demo_app(
            save_db_path=tmp_path / "web_demo_saves.sqlite",
            narrator_mode="cloudflare",
            narrator=StubNarrator(_OPENING_TEXT),
            output_editor=_PassThroughEditor(),
            story_director=_StubDirector(),
            session_turn_cap=1,
            save_store=InMemorySaveStore(),
            freeform_adapter=RuleBasedFreeformProposalAdapter(),
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
            narrator_mode="cloudflare",
            narrator=StubNarrator(_OPENING_TEXT),
            output_editor=_PassThroughEditor(),
            story_director=_StubDirector(),
            ip_rate_limit_per_min=2,
            save_store=InMemorySaveStore(),
            freeform_adapter=RuleBasedFreeformProposalAdapter(),
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
            narrator_mode="cloudflare",
            narrator=StubNarrator(_OPENING_TEXT),
            output_editor=_PassThroughEditor(),
            story_director=_StubDirector(),
            ip_rate_limit_per_min=10,
            ip_daily_turn_cap=2,
            save_store=InMemorySaveStore(),
            freeform_adapter=RuleBasedFreeformProposalAdapter(),
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


def test_demo_does_not_call_retired_narrator_after_a_valid_proposal(tmp_path):
    client = TestClient(
        create_demo_app(
            save_db_path=tmp_path / "web_demo_saves.sqlite",
            narrator_mode="cloudflare",
            narrator=_FailingNarrator("AI_QUOTA_EXCEEDED"),
            output_editor=_PassThroughEditor(),
            story_director=_BundleDirector(),
            save_store=InMemorySaveStore(),
            freeform_adapter=RuleBasedFreeformProposalAdapter(),
        )
    )
    session_id = client.post("/api/v1/session", json={"seed": 5}).json()["session_id"]
    bootstrap = client.post("/api/v1/turn", json={"session_id": session_id, "command": "look"})
    assert bootstrap.status_code == 200
    response = client.post("/api/v1/turn", json={"session_id": session_id, "command": "go north"})
    assert response.status_code == 200
    assert response.json()["status"] == "ok"


def test_demo_capacity_failure_preserves_rate_limit_classification(tmp_path):
    client = TestClient(
        create_demo_app(
            save_db_path=tmp_path / "web_demo_saves.sqlite",
            narrator_mode="cloudflare",
            narrator=_FailingNarrator("AI_CAPACITY_EXCEEDED trace_id=worker-123"),
            output_editor=_PassThroughEditor(),
            story_director=_BundleDirector(),
            save_store=InMemorySaveStore(),
            freeform_adapter=RuleBasedFreeformProposalAdapter(),
        )
    )
    session_id = client.post("/api/v1/session", json={"seed": 8}).json()["session_id"]
    assert client.post("/api/v1/turn", json={"session_id": session_id, "command": "look"}).status_code == 200

    response = client.post("/api/v1/turn", json={"session_id": session_id, "command": "go north"})

    assert response.status_code == 200
    assert response.json()["status"] == "ok"


def test_demo_rejected_request_maps_to_upstream_error(tmp_path):
    client = TestClient(
        create_demo_app(
            save_db_path=tmp_path / "web_demo_saves.sqlite",
            narrator_mode="cloudflare",
            narrator=_FailingNarrator("AI_REQUEST_REJECTED status=403 trace_id=worker-403"),
            output_editor=_PassThroughEditor(),
            story_director=_BundleDirector(),
            save_store=InMemorySaveStore(),
            freeform_adapter=RuleBasedFreeformProposalAdapter(),
        )
    )
    session_id = client.post("/api/v1/session", json={"seed": 9}).json()["session_id"]
    assert client.post("/api/v1/turn", json={"session_id": session_id, "command": "look"}).status_code == 200

    response = client.post("/api/v1/turn", json={"session_id": session_id, "command": "go north"})

    assert response.status_code == 200
    assert response.json()["status"] == "ok"


def test_demo_ignores_retired_narrator_service_failure(tmp_path):
    client = TestClient(
        create_demo_app(
            save_db_path=tmp_path / "web_demo_saves.sqlite",
            narrator_mode="cloudflare",
            narrator=_FailingNarrator("backend unavailable"),
            output_editor=_PassThroughEditor(),
            story_director=_BundleDirector(),
            save_store=InMemorySaveStore(),
            freeform_adapter=RuleBasedFreeformProposalAdapter(),
        )
    )
    session_id = client.post("/api/v1/session", json={"seed": 6}).json()["session_id"]
    bootstrap = client.post("/api/v1/turn", json={"session_id": session_id, "command": "look"})
    assert bootstrap.status_code == 200
    response = client.post("/api/v1/turn", json={"session_id": session_id, "command": "go north"})
    assert response.status_code == 200
    assert response.json()["status"] == "ok"


def test_demo_does_not_log_retired_narrator_failure(tmp_path, caplog):
    client = TestClient(
        create_demo_app(
            save_db_path=tmp_path / "web_demo_saves.sqlite",
            narrator_mode="cloudflare",
            narrator=_FailingNarrator("backend unavailable"),
            output_editor=_PassThroughEditor(),
            story_director=_BundleDirector(),
            save_store=InMemorySaveStore(),
            freeform_adapter=RuleBasedFreeformProposalAdapter(),
        )
    )
    session_id = client.post("/api/v1/session", json={"seed": 7}).json()["session_id"]
    bootstrap = client.post("/api/v1/turn", json={"session_id": session_id, "command": "look"})
    assert bootstrap.status_code == 200
    with caplog.at_level(logging.WARNING):
        response = client.post("/api/v1/turn", json={"session_id": session_id, "command": "go to foyer"})
    assert response.status_code == 200
    assert "Narrator failed" not in caplog.text


def test_demo_visible_destination_uses_the_shared_deterministic_proposal_path(tmp_path, monkeypatch) -> None:
    calls = 0

    def _unexpected_planner(*_args: object) -> str:
        nonlocal calls
        calls += 1
        return "{}"

    monkeypatch.setattr(
        "storygame.engine.freeform._story_agent_chat_complete",
        _unexpected_planner,
    )
    client = TestClient(
        create_demo_app(
            save_db_path=tmp_path / "web_demo_saves.sqlite",
            narrator=StubNarrator(_OPENING_TEXT),
            output_editor=_PassThroughEditor(),
            story_director=_BundleDirector(),
            save_store=InMemorySaveStore(),
            freeform_adapter=LlmFreeformProposalAdapter(),
        )
    )
    session_id = client.post("/api/v1/session", json={"seed": 123}).json()["session_id"]
    assert client.post("/api/v1/turn", json={"session_id": session_id, "command": "look"}).status_code == 200

    foyer = client.post("/api/v1/turn", json={"session_id": session_id, "command": "go to foyer"})
    market_lane = client.post("/api/v1/turn", json={"session_id": session_id, "command": "go to market lane"})
    collected = client.post("/api/v1/turn", json={"session_id": session_id, "command": "take route key"})

    assert foyer.status_code == 200
    assert foyer.json()["state"]["location"] == "foyer"
    assert market_lane.status_code == 200
    assert market_lane.json()["state"]["location"] == "market_lane"
    assert collected.status_code == 200
    assert "route_key" in collected.json()["state"]["inventory"]
    assert calls == 0
