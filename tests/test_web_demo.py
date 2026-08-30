"""Hosted scene-runtime adapter contracts."""

from pathlib import Path

from fastapi.testclient import TestClient

from storygame.runtime.cloudflare import NarrationProviderError
from storygame.runtime.contracts import RuntimeContractError
from storygame.runtime.persistence import RuntimeStateSqliteStore
from storygame.story_package.loader import load_story_package
from storygame.web_demo import create_demo_app

PACKAGE = load_story_package(Path("data/stories/continuity-initiative"))


class _StubProvider:
    """Separate scene openings from ordinary turns the way the transport does."""

    def __init__(self, turn_text: str, opening_text: str = "A stub opening for this scene.") -> None:
        self.turn_text = turn_text
        self.opening_text = opening_text

    def opening(self) -> dict[str, object]:
        return {"segments": [{"kind": "narration", "text": self.opening_text}]}

    def __call__(self, _input: str) -> dict[str, object]:
        return {"segments": [{"kind": "narration", "text": self.turn_text}]}


class _TurnFailureProvider(_StubProvider):
    """Keep the scene opening valid so a test can isolate an ordinary-turn failure."""

    def __init__(self, turn) -> None:
        super().__init__("unused")
        self.turn = turn

    def __call__(self, player_input: str) -> object:
        return self.turn(player_input)


def _provider(text: str):
    return _StubProvider(text)


def test_hosted_adapter_reports_identity_and_serves_a_story_session(monkeypatch, tmp_path) -> None:
    monkeypatch.setenv("FREYTAG_DEPLOYMENT_SHA", "a" * 40)
    app = create_demo_app(
        channel="staging",
        store_path=tmp_path / "sessions.sqlite",
        provider_factory=lambda _state: _StubProvider(
            "The lead sharpens.", "Kristin steps into a house that has already been searched."
        ),
    )

    with TestClient(app) as client:
        health = client.get("/api/v1/health")
        version = client.get("/api/v1/version")
        session = client.post("/api/v1/session", json={"story_id": "continuity_initiative"})
        turn = client.post(
            "/api/v1/turn", json={"session_id": session.json()["session_id"], "player_input": "I listen."}
        )

    assert health.json() == {
        "status": "ok",
        "runtime": "scene-v1",
        "channel": "staging",
        "sha": "a" * 40,
    }
    assert version.json() == {
        "api": "v1",
        "runtime": "scene-v1",
        "channel": "staging",
        "sha": "a" * 40,
    }
    assert session.json()["state"] == {
        "story_id": "continuity_initiative",
        "scene_id": "1A",
        "phase": "exposition",
        "pending_game_break": False,
        "fired_storylet_ids": [],
        "fired_pacing_event_ids": [],
        "story_elapsed_seconds": 0,
        "turn_index": 0,
        "turns_since_scene_entry": 0,
    }
    opening = session.json()["opening"]
    entry_text = PACKAGE.scenes[0].metadata.entry_text
    # The browser renders opening["text"] as one block, so the authored paragraph break must
    # carry through without a space indenting the continuation that follows it.
    assert opening["text"] == f"{entry_text.rstrip()}\n\nKristin steps into a house that has already been searched."
    assert opening["segments"] == [
        {"kind": "narration", "text": entry_text, "speaker_id": None, "grounding_ids": []},
        {
            "kind": "narration",
            "text": "Kristin steps into a house that has already been searched.",
            "speaker_id": None,
            "grounding_ids": [],
        },
    ]
    assert opening["scene_id"] == "1A"
    assert turn.json()["segments"][0]["text"] == "The lead sharpens."
    assert turn.json()["lines"] == ["The lead sharpens."]
    assert turn.json()["delivery"] == {
        "must_convey_misses": [],
        "recovery_used": False,
        "fallback_used": False,
        "hint_staged": False,
        "handoff_staged": False,
    }


def test_hosted_adapter_reports_turn_index_and_scene_relative_turns(tmp_path) -> None:
    app = create_demo_app(
        store_path=tmp_path / "sessions.sqlite",
        provider_factory=lambda _state: _provider("The lead sharpens."),
    )
    with TestClient(app) as client:
        session = client.post("/api/v1/session", json={"story_id": "continuity_initiative"})
        session_id = session.json()["session_id"]
        turn = client.post("/api/v1/turn", json={"session_id": session_id, "player_input": "I listen."})

    assert session.json()["state"]["turn_index"] == 0
    assert session.json()["state"]["turns_since_scene_entry"] == 0
    assert turn.json()["state"]["turn_index"] == 1
    assert turn.json()["state"]["turns_since_scene_entry"] == 1


def test_provider_authored_operations_are_rejected_before_session_mutation(tmp_path) -> None:
    app = create_demo_app(
        store_path=tmp_path / "sessions.sqlite",
        provider_factory=lambda _state: _TurnFailureProvider(
            lambda _input: {
                "segments": [{"kind": "narration", "text": "I incapacitate Brandon."}],
                "operations": [{"operation": "assert", "fact": {"predicate": "incapacitated", "subject": "brandon"}}],
            }
        ),
    )
    with TestClient(app) as client:
        session_id = client.post("/api/v1/session", json={"story_id": "continuity_initiative"}).json()["session_id"]
        warning = client.post("/api/v1/turn", json={"session_id": session_id, "player_input": "I attack Brandon."})
    assert warning.status_code == 422
    assert "operations" in warning.json()["detail"]


def test_adapter_fails_closed_without_worker_rejects_unknown_story_and_rate_limits(monkeypatch, tmp_path) -> None:
    monkeypatch.setenv("FREYTAG_RATE_LIMIT_PER_MINUTE", "1")
    monkeypatch.delenv("CLOUDFLARE_WORKER_URL", raising=False)
    app = create_demo_app(store_path=tmp_path / "sessions.sqlite")
    with TestClient(app) as client:
        missing_story = client.post("/api/v1/session", json={"story_id": "missing"})
        unavailable = client.post("/api/v1/session", json={"story_id": "continuity_initiative"})
        allowed = client.post("/api/v1/turn", json={"session_id": "absent", "player_input": "I listen."})
        limited = client.post("/api/v1/turn", json={"session_id": "absent", "player_input": "I try again."})

    assert missing_story.status_code == 404
    assert unavailable.status_code == 503
    assert allowed.status_code == 404
    assert limited.status_code == 429


def test_adapter_exposes_a_safe_worker_error_code_header(tmp_path) -> None:
    def rejected_provider(_state):
        def reject(_input):
            raise NarrationProviderError(
                "narration service rejected the turn", 502, "WORKER_CONFIGURATION_ERROR", "trace-123", "worker-456"
            )

        return _TurnFailureProvider(reject)

    app = create_demo_app(store_path=tmp_path / "sessions.sqlite", provider_factory=rejected_provider)
    with TestClient(app) as client:
        session_id = client.post("/api/v1/session", json={"story_id": "continuity_initiative"}).json()["session_id"]
        response = client.post("/api/v1/turn", json={"session_id": session_id, "player_input": "I listen."})

    assert response.status_code == 502
    assert response.headers["X-Narration-Error-Code"] == "WORKER_CONFIGURATION_ERROR"
    assert response.headers["X-Trace-ID"] == "trace-123"
    assert response.headers["X-Worker-Revision"] == "worker-456"


def test_adapter_returns_cors_safe_invalid_provider_contract(tmp_path) -> None:
    def invalid_provider(_state):
        def reject(_input):
            raise RuntimeContractError("provider response violates the turn contract")

        return _TurnFailureProvider(reject)

    app = create_demo_app(store_path=tmp_path / "sessions.sqlite", provider_factory=invalid_provider)
    with TestClient(app) as client:
        session_id = client.post("/api/v1/session", json={"story_id": "continuity_initiative"}).json()["session_id"]
        response = client.post(
            "/api/v1/turn",
            json={"session_id": session_id, "player_input": "I listen."},
            headers={"Origin": "http://127.0.0.1:4173"},
        )

    assert response.status_code == 422
    assert response.json() == {"detail": "provider response violates the turn contract"}
    assert response.headers["access-control-allow-origin"] == "*"


def test_turn_request_accepts_the_pre_scene_command_field(tmp_path) -> None:
    app = create_demo_app(
        store_path=tmp_path / "sessions.sqlite",
        provider_factory=lambda _state: _provider("The lead sharpens."),
    )
    with TestClient(app) as client:
        session_id = client.post("/api/v1/session", json={"story_id": "continuity_initiative"}).json()["session_id"]
        response = client.post("/api/v1/turn", json={"session_id": session_id, "command": "I listen."})

    assert response.status_code == 200
    assert response.json()["segments"][0]["text"] == "The lead sharpens."


def test_test_clock_is_opt_in_and_can_trigger_pacing_without_waiting(monkeypatch, tmp_path) -> None:
    monkeypatch.setenv("FREYTAG_ALLOW_TEST_CLOCK", "1")
    monkeypatch.setenv("FREYTAG_TEST_CLOCK_TOKEN", "clock-secret")
    app = create_demo_app(
        store_path=tmp_path / "sessions.sqlite",
        provider_factory=lambda _state: _provider("The patrol's radios crackle outside."),
    )
    with TestClient(app) as client:
        session_id = client.post("/api/v1/session", json={"story_id": "continuity_initiative"}).json()["session_id"]
        response = client.post(
            "/api/v1/turn",
            json={
                "session_id": session_id,
                "player_input": "I wait and listen.",
                "test_clock_seconds": 120,
                "test_clock_token": "clock-secret",
            },
        )

    assert response.status_code == 200
    assert response.json()["state"]["story_elapsed_seconds"] == 120


def test_test_clock_header_is_ignored_without_local_opt_in(monkeypatch, tmp_path) -> None:
    monkeypatch.delenv("FREYTAG_ALLOW_TEST_CLOCK", raising=False)
    app = create_demo_app(
        store_path=tmp_path / "sessions.sqlite",
        provider_factory=lambda _state: _provider("The room stays tense."),
    )
    with TestClient(app) as client:
        session_id = client.post("/api/v1/session", json={"story_id": "continuity_initiative"}).json()["session_id"]
        response = client.post(
            "/api/v1/turn",
            json={"session_id": session_id, "player_input": "I listen.", "test_clock_seconds": 120},
        )

    assert response.json()["state"]["story_elapsed_seconds"] == 60


def test_phase3_api_timeline_resolves_only_an_eligible_recording_selection(tmp_path) -> None:
    """Deterministic API E2E evidence for the Scene 1A warning regression."""

    responses = iter(
        (
            {
                "segments": [
                    {
                        "kind": "narration",
                        "text": "The damaged recording crackles: Michelle warns Kristin not to trust broadcasts.",
                        "grounding_ids": ["k_sl_1a_b_r2"],
                    }
                ],
                "selected_knowledge_ids": ["k_sl_1a_b_r2"],
            },
            {
                "segments": [{"kind": "narration", "text": "An unearned later clue appears."}],
                "selected_knowledge_ids": ["k_future_unavailable"],
            },
        )
    )

    class _SequencedProvider:
        def opening(self) -> dict[str, object]:
            return {"segments": [{"kind": "narration", "text": "The kitchen holds its breath."}]}

        def __call__(self, _input: str) -> object:
            return next(responses)

    def provider_factory(state):
        state.active_event_ids.add("SL-1A-B")
        return _SequencedProvider()

    store_path = tmp_path / "phase3.sqlite"
    app = create_demo_app(store_path=store_path, provider_factory=provider_factory)
    with TestClient(app) as client:
        session_id = client.post("/api/v1/session", json={"story_id": "continuity_initiative"}).json()["session_id"]
        accepted = client.post("/api/v1/turn", json={"session_id": session_id, "player_input": "I search the drawer."})
        invalid_session_id = client.post("/api/v1/session", json={"story_id": "continuity_initiative"}).json()[
            "session_id"
        ]
        before_rejection = RuntimeStateSqliteStore(store_path).load(invalid_session_id, PACKAGE).snapshot()
        rejected = client.post(
            "/api/v1/turn", json={"session_id": invalid_session_id, "player_input": "I check the gate."}
        )

    restored = RuntimeStateSqliteStore(store_path).load(session_id, PACKAGE)
    invalid_restored = RuntimeStateSqliteStore(store_path).load(invalid_session_id, PACKAGE)
    assert accepted.status_code == 200
    assert accepted.json()["segments"][0]["grounding_ids"] == ["k_sl_1a_b_r2"]
    assert restored.facts.has("michelle_warning_known", "story", value="true")
    assert rejected.status_code == 409
    assert invalid_restored.snapshot() == before_rejection


def test_test_clock_rejects_invalid_or_unsafe_values(monkeypatch, tmp_path) -> None:
    monkeypatch.setenv("FREYTAG_ALLOW_TEST_CLOCK", "1")
    monkeypatch.setenv("FREYTAG_TEST_CLOCK_TOKEN", "clock-secret")
    app = create_demo_app(
        store_path=tmp_path / "sessions.sqlite",
        provider_factory=lambda _state: _provider("The room stays tense."),
    )
    with TestClient(app) as client:
        session_id = client.post("/api/v1/session", json={"story_id": "continuity_initiative"}).json()["session_id"]
        invalid = client.post(
            "/api/v1/turn",
            json={"session_id": session_id, "player_input": "I listen."},
            headers={
                "X-Freytag-Test-Clock-Seconds": "later",
                "X-Freytag-Test-Clock-Token": "clock-secret",
            },
        )
        unsafe = client.post(
            "/api/v1/turn",
            json={"session_id": session_id, "player_input": "I listen."},
            headers={
                "X-Freytag-Test-Clock-Seconds": "3601",
                "X-Freytag-Test-Clock-Token": "clock-secret",
            },
        )

    assert invalid.status_code == 422
    assert unsafe.status_code == 422


def test_test_clock_cors_header_is_available_only_with_local_opt_in(monkeypatch, tmp_path) -> None:
    monkeypatch.setenv("FREYTAG_ALLOW_TEST_CLOCK", "1")
    app = create_demo_app(store_path=tmp_path / "sessions.sqlite")
    with TestClient(app) as client:
        preflight = client.options(
            "/api/v1/turn",
            headers={
                "Origin": "http://127.0.0.1:4173",
                "Access-Control-Request-Method": "POST",
                "Access-Control-Request-Headers": ("X-Freytag-Test-Clock-Seconds, X-Freytag-Test-Clock-Token"),
            },
        )

    assert preflight.status_code == 200
    assert "x-freytag-test-clock-seconds" in preflight.headers["access-control-allow-headers"].lower()
    assert "x-freytag-test-clock-token" in preflight.headers["access-control-allow-headers"].lower()


def test_test_clock_accepts_a_correct_header_token(monkeypatch, tmp_path) -> None:
    monkeypatch.setenv("FREYTAG_ALLOW_TEST_CLOCK", "1")
    monkeypatch.setenv("FREYTAG_TEST_CLOCK_TOKEN", "clock-secret")
    app = create_demo_app(
        store_path=tmp_path / "sessions.sqlite",
        provider_factory=lambda _state: _provider("The patrol's radios crackle outside."),
    )
    with TestClient(app) as client:
        session_id = client.post("/api/v1/session", json={"story_id": "continuity_initiative"}).json()["session_id"]
        response = client.post(
            "/api/v1/turn",
            json={"session_id": session_id, "player_input": "I wait and listen."},
            headers={
                "X-Freytag-Test-Clock-Seconds": "120",
                "X-Freytag-Test-Clock-Token": "clock-secret",
            },
        )

    assert response.status_code == 200
    assert response.json()["state"]["story_elapsed_seconds"] == 120


def test_test_clock_rejects_a_wrong_token_without_disclosing_secrets(monkeypatch, tmp_path) -> None:
    monkeypatch.setenv("FREYTAG_ALLOW_TEST_CLOCK", "1")
    monkeypatch.setenv("FREYTAG_TEST_CLOCK_TOKEN", "clock-secret")
    app = create_demo_app(
        store_path=tmp_path / "sessions.sqlite",
        provider_factory=lambda _state: _provider("The room stays tense."),
    )
    with TestClient(app) as client:
        session_id = client.post("/api/v1/session", json={"story_id": "continuity_initiative"}).json()["session_id"]
        response = client.post(
            "/api/v1/turn",
            json={
                "session_id": session_id,
                "player_input": "I listen.",
                "test_clock_seconds": 120,
                "test_clock_token": "wrong-secret",
            },
        )

    assert response.status_code == 403
    assert "clock-secret" not in response.text
    assert "wrong-secret" not in response.text


def test_test_clock_rejects_a_missing_token(monkeypatch, tmp_path) -> None:
    monkeypatch.setenv("FREYTAG_ALLOW_TEST_CLOCK", "1")
    monkeypatch.setenv("FREYTAG_TEST_CLOCK_TOKEN", "clock-secret")
    app = create_demo_app(
        store_path=tmp_path / "sessions.sqlite",
        provider_factory=lambda _state: _provider("The room stays tense."),
    )
    with TestClient(app) as client:
        session_id = client.post("/api/v1/session", json={"story_id": "continuity_initiative"}).json()["session_id"]
        response = client.post(
            "/api/v1/turn",
            json={"session_id": session_id, "player_input": "I listen.", "test_clock_seconds": 120},
        )

    assert response.status_code == 403


def test_test_clock_fails_closed_without_a_configured_secret(monkeypatch, tmp_path) -> None:
    monkeypatch.setenv("FREYTAG_ALLOW_TEST_CLOCK", "1")
    monkeypatch.delenv("FREYTAG_TEST_CLOCK_TOKEN", raising=False)
    app = create_demo_app(
        store_path=tmp_path / "sessions.sqlite",
        provider_factory=lambda _state: _provider("The room stays tense."),
    )
    with TestClient(app) as client:
        session_id = client.post("/api/v1/session", json={"story_id": "continuity_initiative"}).json()["session_id"]
        response = client.post(
            "/api/v1/turn",
            json={"session_id": session_id, "player_input": "I listen.", "test_clock_seconds": 120},
        )

    assert response.status_code == 503
    assert response.json()["detail"] == "test clock is enabled but no shared secret is configured"


def test_test_clock_allows_an_ordinary_turn_without_a_configured_secret(monkeypatch, tmp_path) -> None:
    monkeypatch.setenv("FREYTAG_ALLOW_TEST_CLOCK", "1")
    monkeypatch.delenv("FREYTAG_TEST_CLOCK_TOKEN", raising=False)
    app = create_demo_app(
        store_path=tmp_path / "sessions.sqlite",
        provider_factory=lambda _state: _provider("The room stays tense."),
    )
    with TestClient(app) as client:
        session_id = client.post("/api/v1/session", json={"story_id": "continuity_initiative"}).json()["session_id"]
        response = client.post("/api/v1/turn", json={"session_id": session_id, "player_input": "I listen."})

    assert response.status_code == 200


def test_test_clock_field_is_ignored_without_opt_in_even_with_a_wrong_token(monkeypatch, tmp_path) -> None:
    monkeypatch.delenv("FREYTAG_ALLOW_TEST_CLOCK", raising=False)
    monkeypatch.setenv("FREYTAG_TEST_CLOCK_TOKEN", "clock-secret")
    app = create_demo_app(
        store_path=tmp_path / "sessions.sqlite",
        provider_factory=lambda _state: _provider("The room stays tense."),
    )
    with TestClient(app) as client:
        session_id = client.post("/api/v1/session", json={"story_id": "continuity_initiative"}).json()["session_id"]
        response = client.post(
            "/api/v1/turn",
            json={
                "session_id": session_id,
                "player_input": "I listen.",
                "test_clock_seconds": 120,
                "test_clock_token": "wrong-secret",
            },
        )

    assert response.status_code == 200
    assert response.json()["state"]["story_elapsed_seconds"] == 60
