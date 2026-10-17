"""Player-safe refusal lines for rejected turns."""

from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from storygame.runtime.contracts import RuntimeContractError
from storygame.runtime.persistence import RuntimeStateSqliteStore
from storygame.runtime.validation import (
    ITEM_NOT_VISIBLE_MESSAGE,
    NARRATION_RETRY_MESSAGE,
    REJECTED_TURN_MESSAGE,
    rejection_message,
)
from storygame.story_package.loader import load_story_package
from storygame.web_demo import create_demo_app

PACKAGE = load_story_package(Path("data/stories/continuity-initiative"))


class _Provider:
    def __init__(self, turn_result: object) -> None:
        self.turn_result = turn_result
        self.calls = 0

    def opening(self) -> dict[str, object]:
        return {"segments": [{"kind": "narration", "text": "The house settles."}]}

    def __call__(self, _player_input: str) -> object:
        self.calls += 1
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
    ("code", "term", "player_input", "expected"),
    [
        (
            "narration_known_term_leak",
            "Rebecca",
            "Search for Rebecca.",
            ITEM_NOT_VISIBLE_MESSAGE,
        ),
        (
            "narration_known_term_leak",
            "card",
            "Open the discard pile.",
            NARRATION_RETRY_MESSAGE,
        ),
        ("protected_narration_leak", None, "Search the room.", NARRATION_RETRY_MESSAGE),
        ("disclosure_guard_leak", "key", "Search the room.", NARRATION_RETRY_MESSAGE),
        ("ineligible_selection", "Rebecca", "Search for Rebecca.", REJECTED_TURN_MESSAGE),
    ],
)
def test_rejection_message_is_safe_and_classifies_guard_failures(
    code: str, term: str | None, player_input: str, expected: str
) -> None:
    result = rejection_message(code, term, player_input)

    assert result == expected
    assert term is None or term.casefold() not in result.casefold()


def test_typed_protected_term_returns_item_line_and_restores_state(tmp_path: Path) -> None:
    provider = _Provider(_payload("Rebecca is in the room."))
    app = create_demo_app(
        store_path=tmp_path / "typed.sqlite",
        provider_factory=lambda _state: provider,
    )

    with TestClient(app) as client:
        session_id = _session_id(client)
        store = RuntimeStateSqliteStore(tmp_path / "typed.sqlite")
        before = store.load(session_id, PACKAGE).snapshot()
        response = client.post(
            "/api/v1/turn",
            json={"session_id": session_id, "player_input": "Search for Rebecca."},
        )
        after = store.load(session_id, PACKAGE).snapshot()

    assert response.status_code == 409
    assert response.json()["detail"] == ITEM_NOT_VISIBLE_MESSAGE
    assert response.headers["X-Freytag-Rejection-Code"] == "narration_known_term_leak"
    assert after == before
    assert "rebecca" not in response.text.casefold()


def test_narrator_leak_after_guard_retry_returns_retry_line_without_term(tmp_path: Path) -> None:
    provider = _Provider(_payload("Rebecca is in the room."))
    app = create_demo_app(
        store_path=tmp_path / "narrator.sqlite",
        provider_factory=lambda _state: provider,
    )

    with TestClient(app) as client:
        session_id = _session_id(client)
        response = client.post(
            "/api/v1/turn",
            json={"session_id": session_id, "player_input": "Search the kitchen."},
        )

    assert response.status_code == 409
    assert response.json()["detail"] == NARRATION_RETRY_MESSAGE
    assert response.headers["X-Freytag-Rejection-Code"] == "narration_known_term_leak"
    assert provider.calls == 2
    assert "rebecca" not in response.text.casefold()


@pytest.mark.parametrize(
    ("turn_result", "status_code"),
    [
        (_payload("The room stays quiet.", selected=("k_sl_1a_b_r2",)), 409),
        (RuntimeContractError("provider secret"), 422),
    ],
)
def test_non_guard_rejections_keep_generic_line(tmp_path: Path, turn_result: object, status_code: int) -> None:
    app = create_demo_app(
        store_path=tmp_path / f"generic-{status_code}.sqlite",
        provider_factory=lambda _state: _Provider(turn_result),
    )

    with TestClient(app) as client:
        session_id = _session_id(client)
        response = client.post(
            "/api/v1/turn",
            json={"session_id": session_id, "player_input": "Search the kitchen."},
        )

    assert response.status_code == status_code
    assert response.json()["detail"] == REJECTED_TURN_MESSAGE
    assert "rebecca" not in response.text.casefold()


def test_unexpected_exception_keeps_generic_line(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    app = create_demo_app(
        store_path=tmp_path / "unexpected.sqlite",
        provider_factory=lambda _state: _Provider(_payload("The room stays quiet.")),
    )

    def raise_unexpected(_engine: object, _player_input: str, *, clock_seconds: int | None = None) -> object:
        raise ValueError("Rebecca secret")

    with TestClient(app) as client:
        session_id = _session_id(client)
        with monkeypatch.context() as patch:
            patch.setattr("storygame.web_demo.RuntimeEngine.turn", raise_unexpected)
            response = client.post(
                "/api/v1/turn",
                json={"session_id": session_id, "player_input": "Search the kitchen."},
            )

    assert response.status_code == 500
    assert response.json()["detail"] == REJECTED_TURN_MESSAGE
    assert "rebecca" not in response.text.casefold()
