"""Whole-game journeys that force each player-visible realization, offline and free.

For every realization the player can earn, one scripted playthrough prefers it over
its sibling alternatives (siblings are withheld, because a storylet fires once) and
otherwise plays the deterministic thorough policy. Each journey must reach the
resolution through real validation and commit with no deadline backstop event.

Scripted histories prove branch reachability and downstream state, not free-text
usability. Observer-only realizations (audience not player-visible) cannot be
chosen by a player and are not journeyed; the ledger lists them.

Two branches do not yet earn their scene exit; they are pinned below as named
issues so a package fix has to update this file deliberately.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

import pytest

from storygame.personas import (
    _legacy_package,
    _resolution_complete,
)
from storygame.runtime.state import RuntimeState
from storygame.story_package.loader import load_story_package
from tests.journey_prefix import run as run_with_prefix

PACKAGE = load_story_package(Path("data/stories/continuity-initiative"))
PLAYED = _legacy_package(PACKAGE)
AUTHORED_TURN_BUDGET = 120

SIBLINGS: dict[str, list[str]] = {}
for _item in PACKAGE.knowledge.knowledge:
    if _item.source.storylet_id:
        SIBLINGS.setdefault(_item.source.storylet_id, []).append(_item.id)

# A realization that needs an earlier alternative of the same scene to be offered first.
CHAINS: dict[str, tuple[str, ...]] = {
    "k_sl_1a_d_r1": ("k_sl_1a_b_r2", "k_sl_1a_d_r1"),
    "k_sl_1b_a_r1": ("k_sl_1b_d_r1", "k_sl_1b_a_r1"),
    "k_sl_1b_a_r2": ("k_sl_1b_d_r1", "k_sl_1b_a_r2"),
    "k_sl_1b_b_r1": ("k_sl_1b_d_r1", "k_sl_1b_b_r1"),
}

# Named issues N-1 and N-2 were fixed by widening the two bridge activations.
# Add entries back only for a branch that reaches the exit through a forced scene exit.
KNOWN_FORCED_EXITS: dict[str, list[tuple[str, str]]] = {}


@dataclass
class Journey:
    state: RuntimeState
    picked: list[str] = field(default_factory=list)
    forced_exits: list[tuple[str, str]] = field(default_factory=list)
    scenes: list[str] = field(default_factory=list)
    entry_texts: list[str] = field(default_factory=list)

    @property
    def deadline_events(self) -> list[str]:
        return [event for record in self.state.turn_records for event in record.deadline_event_ids]


def play(preferred: tuple[str, ...] = ()) -> Journey:
    result = run_with_prefix(preferred)
    return Journey(
        state=result.state,
        picked=result.picked,
        forced_exits=result.forced_exits,
        scenes=result.scenes,
        entry_texts=result.entry_texts,
    )


PLAYER_REALIZATIONS = [
    item.id
    for item in PACKAGE.knowledge.knowledge
    if item.source.kind == "storylet_realization" and item.audience.kind == "public" and item.audience.player_visible
]


@pytest.mark.nightly
def test_the_default_policy_earns_the_whole_chain_without_a_deadline() -> None:
    journey = play()

    assert _resolution_complete(journey.state)
    assert journey.scenes == ["1A", "1B", "1C", "2A", "2B", "2C", "3A", "3B", "3C"]
    assert journey.forced_exits == []
    assert journey.deadline_events == []
    assert journey.state.turn_index <= AUTHORED_TURN_BUDGET


@pytest.mark.parametrize("item_id", PLAYER_REALIZATIONS)
@pytest.mark.nightly
def test_every_player_realization_has_an_earned_continuation_to_the_ending(item_id: str) -> None:
    preferred = CHAINS.get(item_id, (item_id,))

    journey = play(preferred)

    assert item_id in journey.picked, f"{item_id} was never offered on a legal route"
    assert _resolution_complete(journey.state)
    assert journey.deadline_events == []
    assert journey.forced_exits == KNOWN_FORCED_EXITS.get(item_id, [])
    assert journey.state.turn_index <= AUTHORED_TURN_BUDGET
