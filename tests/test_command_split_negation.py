"""Negated coordinated imperatives stay intact for matcher scoping."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from storygame.runtime.cloudflare import CloudflareTurnProvider
from storygame.runtime.command_split import split_command
from storygame.runtime.engine import RuntimeEngine
from storygame.runtime.state import RuntimeState
from storygame.story_package.loader import load_story_package

PACKAGE = load_story_package(Path("data/stories/continuity-initiative"))


@pytest.mark.parametrize(
    ("command", "expected"),
    [
        (
            "Open the drawer, but do not take anything yet.",
            ["Open the drawer, but do not take anything yet."],
        ),
        (
            "Search Brandon's hideout for leaked documents, but do not copy anything yet.",
            ["Search Brandon's hideout for leaked documents, but do not copy anything yet."],
        ),
        (
            "Check the copied JANUS files, but do not send anything yet.",
            ["Check the copied JANUS files, but do not send anything yet."],
        ),
        (
            "Open the drawer, but don't take anything yet.",
            ["Open the drawer, but don't take anything yet."],
        ),
        (
            "Open the drawer and do not take anything.",
            ["Open the drawer and do not take anything."],
        ),
        ("Open the drawer; do not take anything yet.", ["Open the drawer; do not take anything yet."]),
        ("Do not open the drawer.", ["Do not open the drawer."]),
        ("Open the drawer, never mind.", ["Open the drawer, never mind."]),
    ],
)
def test_negated_coordinated_verbs_are_not_split(command: str, expected: list[str]) -> None:
    assert split_command(command) == expected


@pytest.mark.parametrize(
    ("command", "expected"),
    [
        ("Open the drawer and take the key.", ["Open the drawer.", "Take the key."]),
        (
            "Open the drawer, take the key, then search the room.",
            ["Open the drawer.", "Take the key.", "Search the room."],
        ),
    ],
)
def test_positive_coordinated_verbs_still_split(command: str, expected: list[str]) -> None:
    assert split_command(command) == expected


def test_mixed_positive_and_negated_coordinated_verbs_do_not_promote_negation() -> None:
    pieces = split_command("Open the drawer and take the key, but don't search the room.")

    assert pieces == ["Open the drawer.", "Take the key, but don't search the room."]
    assert "Search the room." not in pieces


@pytest.mark.parametrize(
    ("command", "old_output"),
    [
        (
            "Open the drawer, but do not take anything yet.",
            ["Open the drawer, but do not.", "Take anything yet."],
        ),
        (
            "Search Brandon's hideout for leaked documents, but do not copy anything yet.",
            ["Search Brandon's hideout for leaked documents, but do not.", "Copy anything yet."],
        ),
        (
            "Check the copied JANUS files, but do not send anything yet.",
            ["Check the copied JANUS files, but do not.", "Send anything yet."],
        ),
    ],
)
def test_restraint_commands_never_use_the_old_positive_piece(command: str, old_output: list[str]) -> None:
    assert split_command(command) != old_output


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
        ("Open the drawer, but do not take anything yet.", ("k_sl_1a_f_r1",)),
        ("Do not open the drawer.", ()),
        ("Open the drawer, never mind.", ()),
    ],
)
def test_engine_path_preserves_negation_scope(
    monkeypatch: pytest.MonkeyPatch, player_input: str, expected: tuple[str, ...]
) -> None:
    state = _scene_1a_state()
    provider = _provider(state, monkeypatch)

    result = RuntimeEngine(state, provider).turn(player_input)

    assert result.selected_knowledge_ids == expected
