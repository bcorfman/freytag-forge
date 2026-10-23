from __future__ import annotations

import json
from pathlib import Path

import pytest

from storygame.runtime.candidate_matcher import (
    negation_scoped_command,
    uniquely_matched_authored_handoff,
)
from storygame.runtime.cloudflare import CloudflareTurnProvider
from storygame.runtime.engine import RuntimeEngine
from storygame.runtime.knowledge import KnowledgeProjector
from storygame.runtime.state import RuntimeState
from storygame.story_package.loader import load_story_package

PACKAGE = load_story_package(Path("data/stories/continuity-initiative"))


NEGATION_CASES = (
    pytest.param("Open the drawer.", "Open the drawer.", id="no-negation-is-unchanged"),
    pytest.param("Open the drawer, but do not take anything yet.", "Open the drawer", id="unrelated-restraint"),
    pytest.param(
        "Check the copied JANUS files, but do not send anything yet.",
        "Check the copied JANUS files",
        id="copied-files-restraint",
    ),
    pytest.param(
        "Search Brandon's hideout for leaked documents, but do not copy anything yet.",
        "Search Brandon's hideout for leaked documents",
        id="hideout-restraint",
    ),
    pytest.param("Open the drawer but not the cabinet.", "Open the drawer", id="different-object-restraint"),
    pytest.param("Search the room without touching the safe.", "Search the room", id="without-restraint"),
    pytest.param("Inspect the card, then do not remove anything.", "Inspect the card", id="then-restraint"),
    pytest.param("Read the broadcast schedule, and do not copy it.", "Read the broadcast schedule", id="and-restraint"),
    pytest.param("Do not open the drawer.", None, id="first-clause-do-not"),
    pytest.param("Never open the drawer.", None, id="first-clause-never"),
    pytest.param("Don't open the drawer, open the cabinet.", None, id="first-clause-dont"),
    pytest.param("Open the drawer? No.", None, id="question-no"),
    pytest.param("Open the drawer, but don't open it.", None, id="overlapping-pronoun-restraint"),
    pytest.param("Open the drawer, don't.", None, id="empty-restraint"),
    pytest.param("Open the drawer, actually don't do that.", None, id="ignored-only-restraint"),
    pytest.param("Check the files, do not check them yet.", None, id="overlapping-action-restraint"),
    pytest.param("Search the hideout, do not search the lab.", None, id="overlapping-verb-restraint"),
    pytest.param("Open the drawer, but no drawer.", None, id="overlapping-noun-restraint"),
    pytest.param("Open the drawer without opening the drawer.", None, id="without-overlap"),
    pytest.param("Open the drawer, never mind.", None, id="retraction-never-mind"),
    pytest.param("Open the drawer, no wait.", None, id="retraction-no-wait"),
    pytest.param("Open the drawer, no stop.", None, id="retraction-no-stop"),
    pytest.param("Open the drawer, don't bother.", None, id="retraction-dont-bother"),
    pytest.param("Open the drawer, nevermind.", None, id="retraction-nevermind"),
    pytest.param("Open the drawer, no, cancel that.", None, id="retraction-cancel"),
    pytest.param("Open the drawer, don't, hold on.", None, id="retraction-hold"),
    pytest.param("Open the drawer, no kidding.", None, id="retraction-kidding"),
)


@pytest.mark.parametrize(("player_input", "expected"), NEGATION_CASES)
def test_negation_scoped_command(player_input: str, expected: str | None) -> None:
    assert negation_scoped_command(player_input) == expected


def _scene_1a_candidates():
    state = RuntimeState.bootstrap(PACKAGE)
    state.active_event_ids.update({"SL-1A-E", "SL-1A-F"})
    return KnowledgeProjector().project(state, "player", "Open the drawer").candidates


@pytest.mark.parametrize(
    ("player_input", "expected"),
    [
        ("Open the drawer, but do not take anything yet.", "k_sl_1a_f_r1"),
        ("Do not open the drawer.", None),
        ("Open the drawer, but don't open it.", None),
        ("Open the drawer, never mind.", None),
        ("Open the drawer, no wait.", None),
        ("Open the drawer, no stop.", None),
        ("Open the drawer, don't bother.", None),
        ("Open the drawer, nevermind.", None),
        ("Open the drawer, no, cancel that.", None),
        ("Open the drawer, don't, hold on.", None),
        ("Open the drawer, no kidding.", None),
    ],
)
def test_scene_1a_authored_match_uses_scoped_command(player_input: str, expected: str | None) -> None:
    result = uniquely_matched_authored_handoff(player_input, _scene_1a_candidates())

    assert result is None if expected is None else result.candidate.id == expected


class _Response:
    def __init__(self, body: object) -> None:
        self.body = json.dumps(body).encode()

    def __enter__(self) -> _Response:
        return self

    def __exit__(self, *_args: object) -> None:
        return None

    def read(self) -> bytes:
        return self.body


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


def _scene_1a_state() -> RuntimeState:
    state = RuntimeState.bootstrap(PACKAGE)
    state.active_event_ids.update({"SL-1A-E", "SL-1A-F"})
    return state


@pytest.mark.parametrize(
    ("player_input", "expected"),
    [
        ("Open the drawer; do not take anything yet.", ("k_sl_1a_f_r1",)),
        ("Do not open the drawer.", ()),
    ],
)
def test_engine_provider_path_respects_negation_scope(
    monkeypatch: pytest.MonkeyPatch, player_input: str, expected: tuple[str, ...]
) -> None:
    state = _scene_1a_state()
    provider = _provider(state, monkeypatch)

    result = RuntimeEngine(state, provider).turn(player_input)

    assert result.selected_knowledge_ids == expected
