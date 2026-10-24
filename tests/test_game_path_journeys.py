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
    PERSONAS,
    _legacy_package,
    _resolution_complete,
    _ScriptedProvider,
    _select_thorough,
    _turn_cap,
)
from storygame.runtime.contracts import RuntimeContractError
from storygame.runtime.engine import RuntimeEngine
from storygame.runtime.state import RuntimeState
from storygame.runtime.validation import ProposalValidationError
from storygame.story_package.loader import load_story_package

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
    "k_sl_2a_c_r3": ("k_sl_1c_c_copy_numbers", "k_sl_2a_c_r3"),
    "k_sl_2a_c_r4": ("k_sl_1c_c_secure_route", "k_sl_2a_c_r4"),
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
    blocked = {
        sibling
        for item_id in preferred
        for sibling in SIBLINGS[PACKAGE.knowledge_indexes.by_id[item_id].source.storylet_id]
        if sibling not in preferred
    }
    # Incident recovery is only legal after its missed-window pressure event.
    # Keep the supported outcomes out of the projection for this branch, then
    # let the normal incident clock make the recovery realization available.
    recovery_ids = {
        item.id
        for item in PACKAGE.knowledge.knowledge
        if item.source.storylet_id
        in {incident.recovery_storylet_id for incident in PACKAGE.incidents if incident.recovery_storylet_id}
    }
    if set(preferred) & recovery_ids:
        for incident in PACKAGE.incidents:
            if incident.scene_id != "1C":
                continue
            blocked.update(
                item.id
                for item in PACKAGE.knowledge.knowledge
                if item.source.storylet_id in {outcome.storylet_id for outcome in incident.outcomes}
            )
    state = RuntimeState.bootstrap(PLAYED)
    provider = _ScriptedProvider(PLAYED, state)
    engine = RuntimeEngine(state, provider)
    journey = Journey(state=state, scenes=[state.current_scene_id])
    for _ in range(_turn_cap(PLAYED)):
        if _resolution_complete(state):
            break
        engine._activate_pacing()
        offered = tuple(
            candidate
            for candidate in engine.projector.project(state, "player", "").candidates
            if candidate.id not in blocked
        )
        wanted = next((item_id for item_id in preferred if any(c.id == item_id for c in offered)), None)
        selected = wanted or _select_thorough(PLAYED, state, offered)
        provider.selected = (selected,) if selected else ()
        scene_before = state.current_scene_id
        try:
            result = engine.turn(PERSONAS["thorough"])
        except (ProposalValidationError, RuntimeContractError):
            provider.selected = ()
            selected = None
            engine.turn(PERSONAS["thorough"])
        if selected and engine.last_attempt.outcome == "committed":
            journey.picked.append(selected)
        if state.current_scene_id != scene_before:
            journey.scenes.append(state.current_scene_id)
            if state.current_scene_id == "2A":
                journey.entry_texts.extend(segment.text for segment in result.segments)
            if engine.last_attempt.transition_cause in ("forced", "timer"):
                journey.forced_exits.append((scene_before, engine.last_attempt.transition_cause))
    return journey


PLAYER_REALIZATIONS = [
    item.id
    for item in PACKAGE.knowledge.knowledge
    if item.source.kind == "storylet_realization" and item.audience.kind == "public" and item.audience.player_visible
]


def test_the_default_policy_earns_the_whole_chain_without_a_deadline() -> None:
    journey = play()

    assert _resolution_complete(journey.state)
    assert journey.scenes == ["1A", "1B", "1C", "2A", "2B", "2C", "3A", "3B", "3C"]
    assert journey.forced_exits == []
    assert journey.deadline_events == []
    assert journey.state.turn_index <= AUTHORED_TURN_BUDGET


@pytest.mark.parametrize("item_id", PLAYER_REALIZATIONS)
def test_every_player_realization_has_an_earned_continuation_to_the_ending(item_id: str) -> None:
    preferred = CHAINS.get(item_id, (item_id,))

    journey = play(preferred)

    assert item_id in journey.picked, f"{item_id} was never offered on a legal route"
    assert _resolution_complete(journey.state)
    assert journey.deadline_events == []
    assert journey.forced_exits == KNOWN_FORCED_EXITS.get(item_id, [])
    assert journey.state.turn_index <= AUTHORED_TURN_BUDGET
