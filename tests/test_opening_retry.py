"""Opening narration retries rejected provider proposals without committing canon."""

from __future__ import annotations

from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from storygame.runtime.cloudflare import NarrationProviderError
from storygame.runtime.engine import RuntimeEngine
from storygame.runtime.state import RuntimeState
from storygame.runtime.validation import ProposalValidationError
from storygame.story_package.loader import load_story_package
from storygame.web_demo import create_demo_app

STORY_ROOT = Path("data/stories/continuity-initiative")
LEAKING_TEXT = "JANUS watches from the shadows, already aware of Kristin."
CLEAN_TEXT = "Kristin stands in the quiet hallway."


class _QueuedOpeningProvider:
    def __init__(self, *texts: str) -> None:
        self.payloads = iter(texts)
        self.calls = 0

    def opening(self) -> object:
        self.calls += 1
        return {"segments": [{"kind": "narration", "text": next(self.payloads)}]}


@pytest.fixture
def engine_for(provider_opening_story: Path):
    package = load_story_package(provider_opening_story)

    def build(provider: object) -> RuntimeEngine:
        return RuntimeEngine(RuntimeState.bootstrap(package), provider)  # type: ignore[arg-type]

    return build


def test_opening_retries_a_leak_then_succeeds(engine_for) -> None:
    provider = _QueuedOpeningProvider(LEAKING_TEXT, CLEAN_TEXT)

    opening = engine_for(provider).opening()

    assert provider.calls == 2
    assert opening.segments[-1].text == CLEAN_TEXT


def test_opening_does_not_retry_a_clean_response(engine_for) -> None:
    provider = _QueuedOpeningProvider(CLEAN_TEXT)

    opening = engine_for(provider).opening()

    assert provider.calls == 1
    assert opening.segments[-1].text == CLEAN_TEXT


def test_opening_reraises_the_last_rejection_after_three_attempts(engine_for) -> None:
    provider = _QueuedOpeningProvider(LEAKING_TEXT, LEAKING_TEXT, LEAKING_TEXT)

    with pytest.raises(ProposalValidationError) as error_info:
        engine_for(provider).opening()

    assert provider.calls == 3
    assert error_info.value.code == "protected_narration_leak"


def test_opening_does_not_retry_provider_errors(engine_for) -> None:
    class _FailingProvider:
        calls = 0

        def opening(self) -> object:
            self.calls += 1
            raise NarrationProviderError("narration service failed", 503, "UPSTREAM_FAILURE")

    provider = _FailingProvider()
    with pytest.raises(NarrationProviderError):
        engine_for(provider).opening()

    assert provider.calls == 1


def test_web_session_retries_opening_before_saving(tmp_path, provider_opening_story: Path) -> None:
    provider = _QueuedOpeningProvider(LEAKING_TEXT, CLEAN_TEXT)
    app = create_demo_app(
        package_roots=(provider_opening_story,),
        store_path=tmp_path / "sessions.sqlite",
        provider_factory=lambda _state: provider,
    )

    with TestClient(app) as client:
        response = client.post("/api/v1/session", json={"story_id": "continuity_initiative"})

    assert response.status_code == 200
    assert provider.calls == 2
    assert response.json()["opening"]["segments"][-1]["text"] == CLEAN_TEXT


def test_scripted_opening_scene_never_calls_the_provider() -> None:
    provider = _QueuedOpeningProvider()
    package = load_story_package(STORY_ROOT)

    opening = RuntimeEngine(RuntimeState.bootstrap(package), provider).opening()  # type: ignore[arg-type]

    assert provider.calls == 0
    assert opening.segments[-1].text.rstrip().endswith("She called Michelle's name.")
