"""Phase 2 contracts: facts, snapshots, strict provider parsing, and atomicity."""

from __future__ import annotations

from pathlib import Path

import pytest

from storygame.runtime.contracts import (
    FactOperation,
    GameBreakWarning,
    RuntimeContractError,
    SceneTransitionProposal,
    TurnProposal,
    parse_turn_proposal,
)
from storygame.runtime.facts import Fact
from storygame.runtime.persistence import RuntimeSaveError, RuntimeStateSqliteStore
from storygame.runtime.state import RuntimeState, RuntimeStateError
from storygame.story_package.loader import load_story_package

PACKAGE = load_story_package(Path("data/stories/continuity-initiative"))


def test_provider_envelope_is_normalized_but_invalid_json_fails_closed() -> None:
    proposal = parse_turn_proposal({"response": '{"narration":"Jeremiah looks around."}'})

    assert proposal.narration == "Jeremiah looks around."
    with pytest.raises(RuntimeContractError):
        parse_turn_proposal({"content": "not JSON"})
    with pytest.raises(RuntimeContractError):
        parse_turn_proposal({"narration": "ok", "unknown": True})


def test_fact_store_helpers_round_trip() -> None:
    fact = Fact(predicate="located", subject="jeremiah", object="thomas_home")
    state = RuntimeState.bootstrap(PACKAGE)
    state.facts.assert_fact(fact)

    assert state.facts.has("located", "jeremiah", "thomas_home")
    assert state.facts.matching("located", "jeremiah") == (fact,)
    assert state.facts.as_json() == [fact.model_dump(mode="json")]
    restored = state.facts.from_json(state.facts.as_json())
    restored.retract_fact(fact)
    assert not restored.has("located", "jeremiah", "thomas_home")
    with pytest.raises(ValueError, match="facts must be a list"):
        state.facts.from_json({})


def test_invalid_transition_or_event_is_atomic() -> None:
    state = RuntimeState.bootstrap(PACKAGE)
    original = state.facts.as_json()
    proposal = TurnProposal(
        narration="This cannot commit.",
        operations=(FactOperation(operation="assert", fact=Fact(predicate="noticed", subject="memory_card")),),
        transition=SceneTransitionProposal(transition_id="t_1b_1c"),
    )

    with pytest.raises(RuntimeStateError):
        state.apply_proposal(proposal)

    assert state.facts.as_json() == original
    assert state.current_scene_id == "1A"


def test_warning_persists_and_return_restores_exact_snapshot(tmp_path) -> None:
    state = RuntimeState.bootstrap(PACKAGE)
    before = state.snapshot()
    warning = GameBreakWarning(
        warning_id="destroyed_dependency",
        reason="The remaining route may be unsatisfiable.",
        affected_ids=("memory_card",),
        snapshot_id="snapshot_before_card",
    )
    state.apply_proposal(
        TurnProposal(
            narration="The card is ruined.",
            operations=(FactOperation(operation="assert", fact=Fact(predicate="destroyed", subject="memory_card")),),
            game_break=warning,
        )
    )
    store = RuntimeStateSqliteStore(tmp_path / "runtime.sqlite")
    store.save("session", state)
    restored = store.load("session", PACKAGE)

    assert restored.pending_break == warning
    assert restored.facts.as_json() == before.facts.as_json()
    with pytest.raises(RuntimeStateError):
        restored.apply_proposal(TurnProposal(narration="Ignore it."))
    restored.resolve_break("return_to_scene")
    assert restored.snapshot() == before


def test_pending_break_can_proceed_and_save_rejects_story_mismatch(tmp_path) -> None:
    state = RuntimeState.bootstrap(PACKAGE)
    state.set_pending_break(
        GameBreakWarning(warning_id="risk", reason="Risk acknowledged.", affected_ids=(), snapshot_id="snapshot_risk")
    )
    state.resolve_break("proceed")
    assert not state.has_pending_break
    store = RuntimeStateSqliteStore(tmp_path / "runtime.sqlite")
    store.save("session", state)
    mismatched = PACKAGE.model_copy(update={"story_id": "another_story"})
    with pytest.raises(RuntimeSaveError):
        store.load("session", mismatched)


def test_successful_proposal_commits_events_and_transition() -> None:
    state = RuntimeState.bootstrap(PACKAGE)
    state.active_event_ids.add("SL-1A-A")
    fact = Fact(predicate="noticed", subject="sarah_phone")
    state.apply_proposal(
        TurnProposal(
            narration="Jeremiah pockets the phone.",
            operations=(FactOperation(operation="assert", fact=fact),),
            events=(
                {
                    "event_id": "SL-1A-A",
                    "operations": [{"operation": "assert", "fact": {"predicate": "seen", "subject": "memory_card"}}],
                },
            ),
            transition=SceneTransitionProposal(transition_id="t_1a_1b"),
        )
    )

    assert state.current_scene_id == "1B"
    assert state.phase == "rising_action"
    assert state.facts.has("noticed", "sarah_phone")
    assert state.facts.has("seen", "memory_card")
    assert state.fired_event_ids == {"SL-1A-A"}


def test_invalid_break_decisions_and_missing_save_fail_closed(tmp_path) -> None:
    state = RuntimeState.bootstrap(PACKAGE)
    with pytest.raises(RuntimeStateError, match="no pending"):
        state.resolve_break("proceed")
    state.set_pending_break(
        GameBreakWarning(warning_id="risk", reason="Risk acknowledged.", snapshot_id="snapshot_risk")
    )
    with pytest.raises(RuntimeStateError, match="proceed or return_to_scene"):
        state.require_turn_allowed()
    with pytest.raises(RuntimeStateError, match="must be proceed"):
        state.resolve_break("maybe")

    store = RuntimeStateSqliteStore(tmp_path / "runtime.sqlite")
    with pytest.raises(RuntimeSaveError, match="does not exist"):
        store.load("missing", PACKAGE)
