"""Hermetic HTTP coverage for player-safe engine error responses."""

import logging
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from storygame.runtime.cloudflare import NarrationProviderError
from storygame.runtime.contracts import RuntimeContractError
from storygame.runtime.persistence import RuntimeStateSqliteStore
from storygame.runtime.state import RuntimeStateError
from storygame.runtime.validation import NARRATION_RETRY_MESSAGE, REJECTED_TURN_MESSAGE
from storygame.story_package.loader import load_story_package
from storygame.web_demo import create_demo_app

PACKAGE = load_story_package(Path("data/stories/continuity-initiative"))


class _Provider:
    def __init__(self, turn_result: object) -> None:
        self.turn_result = turn_result

    def opening(self) -> dict[str, object]:
        return {"segments": [{"kind": "narration", "text": "The house settles."}]}

    def __call__(self, _player_input: str) -> object:
        if isinstance(self.turn_result, BaseException):
            raise self.turn_result
        return self.turn_result


def _payload(text: str, *, selected: tuple[str, ...] = ()) -> dict[str, object]:
    return {
        "segments": [{"kind": "narration", "text": text}],
        "selected_knowledge_ids": list(selected),
    }


def _session_id(client: TestClient) -> str:
    response = client.post("/api/v1/session", json={"story_id": "continuity_initiative"})
    assert response.status_code == 200
    return response.json()["session_id"]


@pytest.mark.parametrize(
    ("payload", "code", "raw_detail", "protected_term", "expected_detail"),
    [
        pytest.param(
            _payload("Rebecca is in the room."),
            "narration_known_term_leak",
            "narration mentions an unavailable entity 'rebecca'",
            "rebecca",
            NARRATION_RETRY_MESSAGE,
            id="narration-known-term",
        ),
        pytest.param(
            _payload("The room stays quiet.", selected=("k_sl_1a_b_r2",)),
            "ineligible_selection",
            "selected knowledge is not eligible for this turn",
            "selected knowledge is not eligible",
            REJECTED_TURN_MESSAGE,
            id="ineligible-selection",
        ),
    ],
)
def test_rejected_turn_returns_safe_line_without_raw_reason(
    tmp_path: Path,
    caplog: pytest.LogCaptureFixture,
    payload: dict[str, object],
    code: str,
    raw_detail: str,
    protected_term: str,
    expected_detail: str,
) -> None:
    app = create_demo_app(
        store_path=tmp_path / f"{code}.sqlite",
        provider_factory=lambda _state: _Provider(payload),
    )

    with caplog.at_level(logging.WARNING, logger="storygame.web_demo"), TestClient(app) as client:
        session_id = _session_id(client)
        response = client.post(
            "/api/v1/turn",
            json={"session_id": session_id, "player_input": "Search the kitchen for signs of a struggle."},
        )

    assert response.status_code == 409
    assert response.json()["detail"] == expected_detail
    assert response.headers["X-Freytag-Rejection-Code"] == code
    response_headers = "\n".join(f"{key}: {value}" for key, value in response.headers.items())
    assert protected_term not in response.text.casefold()
    assert protected_term not in response_headers.casefold()
    assert raw_detail not in response.text
    assert raw_detail not in response_headers
    assert any(record.levelno == logging.WARNING and raw_detail in record.getMessage() for record in caplog.records)


def test_rejected_turn_restores_state_before_clean_line_commits(tmp_path: Path) -> None:
    providers = iter(
        [
            _Provider(_payload("The house settles.")),
            _Provider(_payload("Rebecca is in the room.")),
            _Provider(_payload("The latch catches.")),
        ]
    )
    app = create_demo_app(
        store_path=tmp_path / "restore.sqlite",
        provider_factory=lambda _state: next(providers),
    )

    with TestClient(app) as client:
        session_id = _session_id(client)
        store = RuntimeStateSqliteStore(tmp_path / "restore.sqlite")
        before = store.load(session_id, PACKAGE).snapshot()
        rejected = client.post(
            "/api/v1/turn",
            json={"session_id": session_id, "player_input": "Search the kitchen for signs of a struggle."},
        )
        after_rejected = store.load(session_id, PACKAGE).snapshot()
        clean = client.post(
            "/api/v1/turn",
            json={"session_id": session_id, "player_input": "Inspect the back door."},
        )

    assert rejected.status_code == 409
    assert after_rejected == before
    assert clean.status_code == 200
    assert clean.json()["lines"] == ["The latch catches."]
    assert clean.json()["state"]["turn_index"] == before.turn_index + 1


def test_rejected_debug_line_exposes_raw_detail_and_attempt_bundle(monkeypatch, tmp_path: Path) -> None:
    raw_detail = "narration mentions an unavailable entity 'rebecca'"
    monkeypatch.setenv("FREYTAG_EXPOSE_PROMPT", "1")
    app = create_demo_app(
        store_path=tmp_path / "debug.sqlite",
        provider_factory=lambda _state: _Provider(_payload("Rebecca is in the room.")),
    )

    with TestClient(app) as client:
        session_id = _session_id(client)
        response = client.post(
            "/api/v1/turn",
            json={"session_id": session_id, "player_input": "Search the kitchen for signs of a struggle."},
        )

    assert response.status_code == 409
    assert response.json()["detail"] == raw_detail
    assert response.json()["attempt_bundle"] is not None


def test_rejected_opening_keeps_session_creation_error_line_unchanged(tmp_path: Path) -> None:
    class _LeakingOpeningProvider(_Provider):
        def opening(self) -> dict[str, object]:
            return {
                "segments": [{"kind": "narration", "text": "JANUS watches from the shadows, already aware of Kristin."}]
            }

    app = create_demo_app(
        store_path=tmp_path / "opening.sqlite",
        provider_factory=lambda _state: _LeakingOpeningProvider(_payload("unused")),
    )

    with TestClient(app) as client:
        response = client.post("/api/v1/session", json={"story_id": "continuity_initiative"})

    assert response.status_code == 409
    assert response.headers["X-Freytag-Rejection-Code"] == "protected_narration_leak"
    assert response.json()["detail"] != REJECTED_TURN_MESSAGE


def test_rejected_contract_error_returns_safe_line_without_provider_prose(tmp_path: Path) -> None:
    raw_detail = "provider prose secret"
    app = create_demo_app(
        store_path=tmp_path / "contract.sqlite",
        provider_factory=lambda _state: _Provider(RuntimeContractError(raw_detail)),
    )

    with TestClient(app) as client:
        session_id = _session_id(client)
        response = client.post(
            "/api/v1/turn",
            json={"session_id": session_id, "player_input": "Listen to the recording."},
        )

    assert response.status_code == 422
    assert response.json()["detail"] == REJECTED_TURN_MESSAGE
    assert raw_detail not in response.text


def test_rejected_state_error_returns_safe_line(tmp_path: Path) -> None:
    raw_detail = "state secret"
    app = create_demo_app(
        store_path=tmp_path / "state.sqlite",
        provider_factory=lambda _state: _Provider(RuntimeStateError(raw_detail)),
    )

    with TestClient(app) as client:
        session_id = _session_id(client)
        response = client.post(
            "/api/v1/turn",
            json={"session_id": session_id, "player_input": "Listen to the recording."},
        )

    assert response.status_code == 409
    assert response.json()["detail"] == REJECTED_TURN_MESSAGE
    assert raw_detail not in response.text


def test_rejected_unexpected_engine_error_returns_safe_line_and_logs_traceback(
    monkeypatch: pytest.MonkeyPatch,
    caplog: pytest.LogCaptureFixture,
    tmp_path: Path,
) -> None:
    def raise_unexpected(_engine: object, _player_input: str, *, clock_seconds: int | None = None) -> object:
        raise ValueError("boom secret")

    app = create_demo_app(
        store_path=tmp_path / "unexpected.sqlite",
        provider_factory=lambda _state: _Provider(_payload("The room stays quiet.")),
    )

    with TestClient(app) as client:
        session_id = _session_id(client)
        with monkeypatch.context() as patch:
            patch.setattr("storygame.web_demo.RuntimeEngine.turn", raise_unexpected)
            with caplog.at_level(logging.ERROR, logger="storygame.web_demo"):
                response = client.post(
                    "/api/v1/turn",
                    json={"session_id": session_id, "player_input": "Listen to the recording."},
                )
        clean = client.post(
            "/api/v1/turn",
            json={"session_id": session_id, "player_input": "Listen to the recording."},
        )

    assert response.status_code == 500
    assert response.json()["detail"] == REJECTED_TURN_MESSAGE
    assert "boom secret" not in response.text
    assert all("boom secret" not in value for value in response.headers.values())
    assert any(
        record.levelno == logging.ERROR and record.exc_info and "boom secret" in record.getMessage()
        for record in caplog.records
    )
    assert clean.status_code == 200


def test_typed_narration_failure_keeps_service_line_and_headers(tmp_path: Path) -> None:
    app = create_demo_app(
        store_path=tmp_path / "provider.sqlite",
        provider_factory=lambda _state: _Provider(
            NarrationProviderError("worker message", 503, "WORKER_DOWN", "trace-123", "worker-456")
        ),
    )

    with TestClient(app) as client:
        session_id = _session_id(client)
        response = client.post(
            "/api/v1/turn",
            json={"session_id": session_id, "player_input": "Listen to the recording."},
        )

    assert response.status_code == 503
    assert response.json()["detail"] == "worker message"
    assert response.headers["X-Narration-Error-Code"] == "WORKER_DOWN"
    assert response.headers["X-Trace-ID"] == "trace-123"
    assert response.headers["X-Worker-Revision"] == "worker-456"
