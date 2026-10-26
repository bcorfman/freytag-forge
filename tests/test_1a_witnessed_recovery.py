"""Scene 1A witnessed memory-card recovery contract."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from storygame.runtime.candidate_matcher import uniquely_matched_authored_handoff
from storygame.runtime.cloudflare import CloudflareTurnProvider
from storygame.runtime.engine import RuntimeEngine
from storygame.runtime.facts import Fact
from storygame.runtime.knowledge import KnowledgeProjector
from storygame.runtime.state import RuntimeState
from storygame.runtime.world_model import apply_world_effects, world_for
from storygame.story_package.loader import load_story_package

PACKAGE = load_story_package(Path("data/stories/continuity-initiative"))
CARD_REVEAL = "k_sl_1a_b_r0"
WITNESSED_CARD_REVEAL = "k_sl_1a_b_r0w"
STORYLET = "SL-1A-E"
COMMAND = "Feel under the drawer."
CHALLENGE = '"What have you got there?"'
WITNESSED_STATEMENT = "An officer saw Kristin take Michelle's memory card and asked what it is."
DEFAULT_PURSUIT = "The pursuers are closing in through the park. The pursuit is not over."
MARKED_PURSUIT = "The pursuers already have a description of Kristin. They are closing in through the park."


class _Response:
    def __init__(self, payload: object) -> None:
        self.payload = payload

    def __enter__(self) -> _Response:
        return self

    def __exit__(self, *_args: object) -> None:
        return None

    def read(self) -> bytes:
        return json.dumps(self.payload).encode()


def _has_true(state: RuntimeState, fact_id: str) -> bool:
    return Fact(predicate=fact_id, subject="story", value="true") in state.facts.asserted


def _state(*, patrol_in_house: bool | None = None, patrol_departed: bool = False) -> RuntimeState:
    state = RuntimeState.bootstrap(PACKAGE)
    state.active_event_ids.add(STORYLET)
    if patrol_in_house is not None:
        state.facts.assert_fact(Fact(predicate="patrol_in_house", subject="story", value=str(patrol_in_house).lower()))
    if patrol_departed:
        state.facts.assert_fact(Fact(predicate="patrol_departed", subject="story", value="true"))
    apply_world_effects(PACKAGE, state.facts)
    return state


def _candidate_ids(state: RuntimeState, command: str = COMMAND) -> set[str]:
    projection = KnowledgeProjector().project(state, "player", command)
    return {candidate.id for candidate in projection.candidates}


def _provider(monkeypatch: pytest.MonkeyPatch, state: RuntimeState, captured: list[dict] | None = None):
    def open_request(request, **_kwargs: object) -> _Response:
        if captured is not None:
            captured.append(json.loads(request.data.decode()))
        return _Response({"narration": '{"segments":[{"kind":"narration","text":"The room is quiet."}]}'})

    monkeypatch.setattr("storygame.runtime.cloudflare.urlopen", open_request)
    return CloudflareTurnProvider(worker_url="https://worker.example/turn", token="", state=state)


def _texts(proposal: object) -> tuple[str, ...]:
    return tuple(segment.text for segment in proposal.segments)


def test_witnessed_recovery_hands_off_challenge_and_commits_patrol_facts(monkeypatch: pytest.MonkeyPatch) -> None:
    state = _state(patrol_in_house=True)
    assert world_for(PACKAGE, state.facts).parent("patrol_officer") == "kitchen"

    handoff = uniquely_matched_authored_handoff(
        COMMAND, KnowledgeProjector().project(state, "player", COMMAND).candidates
    )
    assert handoff is not None
    assert handoff.candidate.id == WITNESSED_CARD_REVEAL
    assert CARD_REVEAL not in _candidate_ids(state)

    engine = RuntimeEngine(state, _provider(monkeypatch, state))
    result = engine.turn(COMMAND)

    assert result.selected_knowledge_ids == (WITNESSED_CARD_REVEAL,)
    assert _has_true(state, "memory_card_recovered")
    assert _has_true(state, "card_challenged")
    assert _has_true(state, "kristin_marked_by_patrol")
    assert world_for(PACKAGE, state.facts).parent("memory_card") == "kristin"
    assert world_for(PACKAGE, state.facts).parent("patrol_officer") == "kitchen"
    assert sum(text.count(CHALLENGE) for text in _texts(result)) == 1


@pytest.mark.parametrize("departed", [False, True], ids=["before_patrol", "after_departure"])
def test_unwitnessed_recovery_keeps_plain_card_handoff(monkeypatch: pytest.MonkeyPatch, departed: bool) -> None:
    state = _state(patrol_in_house=False if departed else None, patrol_departed=departed)
    handoff = uniquely_matched_authored_handoff(
        COMMAND, KnowledgeProjector().project(state, "player", COMMAND).candidates
    )

    assert handoff is not None
    assert handoff.candidate.id == CARD_REVEAL
    assert WITNESSED_CARD_REVEAL not in _candidate_ids(state)

    engine = RuntimeEngine(state, _provider(monkeypatch, state))
    result = engine.turn(COMMAND)

    assert result.selected_knowledge_ids == (CARD_REVEAL,)
    assert _has_true(state, "memory_card_recovered")
    assert not _has_true(state, "card_challenged")
    assert not _has_true(state, "kristin_marked_by_patrol")


def test_recovery_before_patrol_never_gains_a_witnessed_reveal(monkeypatch: pytest.MonkeyPatch) -> None:
    state = _state()
    engine = RuntimeEngine(state, _provider(monkeypatch, state))
    result = engine.turn(COMMAND)

    assert result.selected_knowledge_ids == (CARD_REVEAL,)
    assert not _has_true(state, "card_challenged")
    assert not _has_true(state, "kristin_marked_by_patrol")

    state.facts.assert_fact(Fact(predicate="patrol_in_house", subject="story", value="true"))
    apply_world_effects(PACKAGE, state.facts)

    assert WITNESSED_CARD_REVEAL not in _candidate_ids(state)
    assert (
        uniquely_matched_authored_handoff(COMMAND, KnowledgeProjector().project(state, "player", COMMAND).candidates)
        is None
    )
    assert not _has_true(state, "card_challenged")
    assert not _has_true(state, "kristin_marked_by_patrol")


def test_unreachable_witnessed_recovery_offers_neither_card_reveal() -> None:
    state = _state(patrol_in_house=True)
    assert world_for(PACKAGE, state.facts).move("kristin", "outside_house").ok

    candidate_ids = _candidate_ids(state)
    assert not {CARD_REVEAL, WITNESSED_CARD_REVEAL} & candidate_ids
    assert (
        uniquely_matched_authored_handoff(
            "Feel in the gap.", KnowledgeProjector().project(state, "player", "Feel in the gap.").candidates
        )
        is None
    )


def test_challenge_statement_reaches_the_next_cloudflare_scene_prompt(monkeypatch: pytest.MonkeyPatch) -> None:
    state = _state(patrol_in_house=True)
    captured: list[dict] = []
    provider = _provider(monkeypatch, state, captured)
    engine = RuntimeEngine(state, provider)

    engine.turn(COMMAND)
    engine.turn("Search the kitchen for signs of a struggle.")

    scene_start = captured[-1]["user"].index("SCENE:")
    assert WITNESSED_STATEMENT in captured[-1]["user"][scene_start:]


@pytest.mark.parametrize(
    ("marked", "expected"),
    [(False, DEFAULT_PURSUIT), (True, MARKED_PURSUIT)],
    ids=["unmarked", "marked"],
)
def test_1b_pursuit_realization_responds_to_patrol_mark(marked: bool, expected: str) -> None:
    state = RuntimeState.bootstrap(PACKAGE)
    state.current_scene_id = "1B"
    state.phase = next(scene.metadata.freytag_phase for scene in PACKAGE.scenes if scene.metadata.scene_id == "1B")
    state._assert_scene_entry_fact("1B")
    state.scene_entered_at_turn = 0
    state.turn_index = 2
    state.facts.assert_fact(Fact(predicate="park_pursuit_resolved", subject="story", value="true"))
    state.facts.assert_fact(Fact(predicate="trust_brandon", subject="story", value="true"))
    if marked:
        state.facts.assert_fact(Fact(predicate="kristin_marked_by_patrol", subject="story", value="true"))

    engine = RuntimeEngine(state, lambda _input: {"segments": [{"kind": "narration", "text": "Keep moving."}]})
    engine.turn("Move through the park.")
    engine.turn("Cross the park before the pursuers arrive.")

    assert state.last_turn_delivery.complication_text == expected


def test_challenge_snapshot_restores_facts_and_officer_placement(monkeypatch: pytest.MonkeyPatch) -> None:
    state = _state(patrol_in_house=True)
    engine = RuntimeEngine(state, _provider(monkeypatch, state))
    engine.turn(COMMAND)

    snapshot = state.snapshot()
    expected_facts = state.facts.asserted
    expected_parent = world_for(PACKAGE, state.facts).parent("patrol_officer")
    restored = RuntimeState.bootstrap(PACKAGE)
    restored.restore_snapshot(snapshot)

    assert restored.facts.asserted == expected_facts
    assert world_for(PACKAGE, restored.facts).parent("patrol_officer") == expected_parent == "kitchen"
