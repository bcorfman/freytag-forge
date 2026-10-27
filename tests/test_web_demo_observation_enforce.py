from __future__ import annotations

from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from storygame import web_demo
from storygame.runtime.capture import WorldCapture
from storygame.runtime.jev import JevClient
from storygame.runtime.observation_verifier import ObservationVerifier
from storygame.runtime.state import RuntimeState
from tests.test_observation_enforcement import _ScriptedProvider
from tests.test_observation_preview import _synthetic_package


class _OpeningProvider(_ScriptedProvider):
    def opening(self) -> dict[str, object]:
        return {"segments": [{"kind": "narration", "text": "The room waits."}]}


class _Jev:
    def __init__(self, score: float) -> None:
        self.score = score

    def ask(self, _state: object, questions: object) -> dict[str, dict[str, float]]:
        if not isinstance(questions, dict):
            return {}
        return {key: {"noul": 1.0 if key == "same_or_part" else self.score} for key in questions}


def _record_captures(monkeypatch: pytest.MonkeyPatch) -> list[WorldCapture]:
    captures: list[WorldCapture] = []
    original_init = WorldCapture.__init__

    def record(self, *args: object, **kwargs: object) -> None:
        original_init(self, *args, **kwargs)
        captures.append(self)

    monkeypatch.setattr(WorldCapture, "__init__", record)
    return captures


def _app(monkeypatch: pytest.MonkeyPatch, tmp_path: Path, *, capture: bool = True):
    if capture:
        monkeypatch.setenv("FREYTAG_WORLD_CAPTURE", "1")
    else:
        monkeypatch.delenv("FREYTAG_WORLD_CAPTURE", raising=False)
    monkeypatch.setenv("CLOUDFLARE_WORKER_URL", "https://fake.worker")

    def provider_factory(state: RuntimeState) -> _OpeningProvider:
        provider = _OpeningProvider(state, [("The room waits.", None)])
        provider.observe_automatically = False
        return provider

    return web_demo.create_demo_app(
        store_path=tmp_path / "sessions.sqlite",
        provider_factory=provider_factory,
    )


def _session(client: TestClient, story_id: str = "continuity_initiative") -> str:
    response = client.post("/api/v1/session", json={"story_id": story_id})
    assert response.status_code == 200
    return response.json()["session_id"]


def test_observation_enforce_is_unset_by_default(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.delenv("FREYTAG_OBSERVATION_ENFORCE", raising=False)
    captures = _record_captures(monkeypatch)

    with TestClient(_app(monkeypatch, tmp_path)) as client:
        _session(client)

    assert captures[-1].enforcing_verifier is None


@pytest.mark.parametrize("value", ["0", "true", "", " 1"])
def test_observation_enforce_requires_exact_one(monkeypatch: pytest.MonkeyPatch, tmp_path: Path, value: str) -> None:
    monkeypatch.setenv("FREYTAG_OBSERVATION_ENFORCE", value)
    captures = _record_captures(monkeypatch)

    with TestClient(_app(monkeypatch, tmp_path)) as client:
        _session(client)

    assert captures[-1].enforcing_verifier is None


def test_observation_enforce_wires_a_new_verifier_to_capture_ask(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    monkeypatch.setenv("FREYTAG_OBSERVATION_ENFORCE", "1")
    fake_jev = _Jev(1.0)
    monkeypatch.setattr(JevClient, "from_environment", classmethod(lambda cls: fake_jev))
    captures = _record_captures(monkeypatch)

    with TestClient(_app(monkeypatch, tmp_path)) as client:
        _session(client)

    capture = captures[-1]
    assert isinstance(capture.enforcing_verifier, ObservationVerifier)
    assert capture.enforcing_verifier._ask is capture.ask


def test_observation_enforce_verifier_is_not_shared_between_sessions(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    monkeypatch.setenv("FREYTAG_OBSERVATION_ENFORCE", "1")
    monkeypatch.setattr(JevClient, "from_environment", classmethod(lambda cls: _Jev(1.0)))
    captures = _record_captures(monkeypatch)

    with TestClient(_app(monkeypatch, tmp_path)) as client:
        _session(client)
        _session(client)

    assert captures[0].enforcing_verifier is not captures[1].enforcing_verifier


def test_observation_enforce_has_no_effect_when_capture_is_off(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.delenv("FREYTAG_WORLD_CAPTURE", raising=False)
    monkeypatch.setenv("FREYTAG_OBSERVATION_ENFORCE", "1")
    captures = _record_captures(monkeypatch)

    with TestClient(_app(monkeypatch, tmp_path, capture=False)) as client:
        _session(client)

    assert captures == []


def test_observation_enforce_has_no_effect_for_scripted_provider(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    monkeypatch.setenv("FREYTAG_WORLD_CAPTURE", "1")
    monkeypatch.setenv("FREYTAG_OBSERVATION_ENFORCE", "1")
    monkeypatch.setenv("FREYTAG_TURN_PROVIDER", "scripted")
    captures = _record_captures(monkeypatch)

    def scripted_provider(_cls, state: RuntimeState) -> _OpeningProvider:
        return _OpeningProvider(state, [("The room waits.", None)])

    monkeypatch.setattr(web_demo.ScriptedTurnProvider, "from_environment", classmethod(scripted_provider))

    with TestClient(web_demo.create_demo_app(store_path=tmp_path / "sessions.sqlite")) as client:
        _session(client)

    assert captures == []


@pytest.mark.parametrize(("score", "status", "turn_index", "accepted"), [(0.0, 409, 0, False), (1.0, 200, 1, True)])
def test_observation_enforce_turn_uses_preview_and_rollback(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    score: float,
    status: int,
    turn_index: int,
    accepted: bool,
) -> None:
    monkeypatch.setenv("FREYTAG_WORLD_CAPTURE", "1")
    monkeypatch.setenv("FREYTAG_OBSERVATION_ENFORCE", "1")
    monkeypatch.setenv("CLOUDFLARE_WORKER_URL", "https://fake.worker")
    monkeypatch.setattr(JevClient, "from_environment", classmethod(lambda cls: _Jev(score)))
    captures: list[WorldCapture] = []
    engines = []
    original_init = web_demo.RuntimeEngine.__init__

    def record_engine(self, *args: object, **kwargs: object) -> None:
        original_init(self, *args, **kwargs)
        self.narration_validator.validate = lambda *_args, **_kwargs: None
        engines.append(self)
        captures.append(self.capture)

    monkeypatch.setattr(web_demo.RuntimeEngine, "__init__", record_engine)

    def provider_factory(state: RuntimeState) -> _OpeningProvider:
        provider = _OpeningProvider(
            state,
            [
                ("Nothing is shown.", {"calibrated lens": {"place": "survey tray"}}),
                ("The calibrated lens catches the light.", {"calibrated lens": {"place": "survey tray"}}),
            ],
        )
        provider.observe_automatically = False
        from storygame.runtime.observation import ObservationRequest

        provider.observation_request = ObservationRequest("Inspect the survey tray.", "look", "tray")
        return provider

    monkeypatch.setattr(web_demo, "load_story_package", lambda _root: _synthetic_package())
    app = web_demo.create_demo_app(
        package_roots=(tmp_path / "synthetic",),
        store_path=tmp_path / "sessions.sqlite",
        provider_factory=provider_factory,
    )
    with TestClient(app) as client:
        session_id = _session(client, "second_story")
        response = client.post(
            "/api/v1/turn",
            json={"session_id": session_id, "player_input": "Inspect the survey tray."},
        )

    assert response.status_code == status
    assert len(engines) == 2
    assert captures[-1].enforcing_verifier is not None
    assert captures[-1].provider.state.turn_index == turn_index
    if accepted:
        assert captures[-1].last_after["observation_preview"]["accepted"] is True
        assert captures[-1].last_after["observation_diverged"] is False
    else:
        assert captures[-1].last_after is None
