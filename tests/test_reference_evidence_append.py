from __future__ import annotations

import json
from pathlib import Path

import pytest

from bench.core import advance_state_to_scene
from storygame.runtime.cloudflare import CloudflareTurnProvider
from storygame.runtime.engine import ClarificationTurn, RuntimeEngine
from storygame.runtime.facts import Fact
from storygame.runtime.reference_resolution import resolve_references, resolved_reference_names
from storygame.runtime.state import RuntimeState
from storygame.story_package.loader import load_story_package

PACKAGE = load_story_package(Path("data/stories/continuity-initiative"))
COPY_COMMAND = "Copy the encrypted Project Echelon file to my laptop."
LEAD_COMMANDS = (
    "Lead the captives through the emergency gate.",
    "Guide the captives through the open emergency gate.",
)


class _Response:
    def __init__(self, body: object) -> None:
        self.body = json.dumps(body).encode()

    def __enter__(self) -> _Response:
        return self

    def __exit__(self, *_args: object) -> None:
        return None

    def read(self) -> bytes:
        return self.body


def _state(scene_id: str, *fact_ids: str) -> RuntimeState:
    state = RuntimeState.bootstrap(PACKAGE)
    advance_state_to_scene(PACKAGE, state, scene_id)
    for fact_id in fact_ids:
        state.facts.assert_fact(Fact(predicate=fact_id, subject="story", value="true"))
    return state


def _provider(state: RuntimeState, monkeypatch: pytest.MonkeyPatch) -> CloudflareTurnProvider:
    monkeypatch.setenv("FREYTAG_SEMANTIC_REVEAL", "0")
    monkeypatch.setattr(
        "storygame.runtime.cloudflare.urlopen",
        lambda _request, **_kwargs: _Response(
            {
                "narration": json.dumps(
                    {"segments": [{"kind": "narration", "text": "The scene continues."}], "selected_knowledge_ids": []}
                )
            }
        ),
    )
    return CloudflareTurnProvider(worker_url="https://worker.example/turn", token="", state=state)


def test_2c_copying_bare_file_earns_copied_files_reveal(monkeypatch: pytest.MonkeyPatch) -> None:
    state = _state("2C", "janus_evidence")
    provider = _provider(state, monkeypatch)

    result = RuntimeEngine(state, provider).turn(COPY_COMMAND)

    assert result.selected_knowledge_ids == ("k_sl_2c_c_r1",)
    assert provider.last_reveal_selection["reference_names"] == ["copied JANUS files"]


@pytest.mark.parametrize("command", LEAD_COMMANDS)
def test_3a_leading_captives_through_bare_gate_earns_uprising_reveal(
    monkeypatch: pytest.MonkeyPatch, command: str
) -> None:
    state = _state(
        "3A",
        "michelle_reached",
        "military_override_codes_available",
        "override_codes_deadline_known",
        "uprising_prepared",
    )
    provider = _provider(state, monkeypatch)

    result = RuntimeEngine(state, provider).turn(command)

    assert result.selected_knowledge_ids == ("k_sl_3a_c_r1",)
    assert provider.last_reveal_selection["reference_names"] == ["detention captives", "emergency surface gates"]


def test_resolved_reference_names_skip_full_names_and_unrelated_words() -> None:
    state = _state("2C", "janus_evidence")

    assert resolved_reference_names(state, COPY_COMMAND) == ("copied JANUS files",)
    assert resolved_reference_names(state, "Copy the copied JANUS files to my laptop.") == ()
    assert resolved_reference_names(state, "Wait by the window.") == ()


def test_ambiguous_reference_still_asks_without_provider_call() -> None:
    state = _state("2B")
    calls: list[str] = []

    def provider(command: str) -> dict[str, object]:
        calls.append(command)
        return {"segments": [{"kind": "narration", "text": "The scene continues."}]}

    result = RuntimeEngine(state, provider).turn("Read the next terminal.")

    assert isinstance(result, ClarificationTurn)
    assert calls == []
    assert resolved_reference_names(state, "Read the next terminal.") == ()
    assert resolve_references(state, "Read the next terminal.").question is not None


def test_narrator_context_keeps_original_player_input(monkeypatch: pytest.MonkeyPatch) -> None:
    state = _state("2C", "janus_evidence")
    provider = _provider(state, monkeypatch)

    prompt = provider.assemble_turn_prompt(COPY_COMMAND)

    assert prompt["context"]["player_input"] == COPY_COMMAND
    assert "copied JANUS files" not in prompt["context"]["player_input"]
    assert provider.last_reveal_selection["reference_names"] == ["copied JANUS files"]


def test_negated_copy_does_not_earn_reveal(monkeypatch: pytest.MonkeyPatch) -> None:
    state = _state("2C", "janus_evidence")
    provider = _provider(state, monkeypatch)

    result = RuntimeEngine(state, provider).turn("Do not copy the file.")

    assert result.selected_knowledge_ids == ()
    assert provider.last_reveal_selection["reference_names"] == ["copied JANUS files"]
