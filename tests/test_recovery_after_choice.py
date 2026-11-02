from __future__ import annotations

from pathlib import Path

import pytest

from storygame.runtime.engine import RuntimeEngine
from storygame.runtime.state import RuntimeState
from storygame.story_package.loader import load_story_package

PACKAGE = Path("data/stories/continuity-initiative")


class _ScriptedProvider:
    def __init__(self, package) -> None:
        self.package = package
        self.selected: list[str] = []

    def __call__(self, _player_input: str) -> dict[str, object]:
        text = "A concrete authored consequence lands."
        if self.selected:
            knowledge = self.package.knowledge_indexes.by_id[self.selected[0]]
            text = knowledge.delivery_text or knowledge.statement
        return {
            "segments": [{"kind": "narration", "text": text, "grounding_ids": list(self.selected)}],
            "selected_knowledge_ids": list(self.selected),
        }


def _drive(engine: RuntimeEngine, provider: _ScriptedProvider, selection: str | None) -> None:
    provider.selected = [selection] if selection else []
    engine.turn("Act on the strongest available lead.")


def _true_facts(state: RuntimeState) -> set[str]:
    return {fact.predicate for fact in state.facts.asserted if str(fact.value).lower() == "true"}


PREFIX_TO_2A = [
    "k_sl_1a_a_r1",
    "k_sl_1a_b_r0",
    None,
    None,
    "k_sl_1a_b_r1",
    None,
    None,
    None,
    None,
    "k_sl_1b_d_r1",
    "k_sl_1b_b_r1",
    "k_sl_1b_c_r1",
    None,
    None,
    None,
    None,
    None,
    None,
    "k_sl_1c_a_r1",
    "k_sl_1c_b_r1",
    "k_sl_1c_c_copy_numbers",
    "k_sl_2a_b_r1",
]


def _start_at_2a() -> tuple[RuntimeState, _ScriptedProvider, RuntimeEngine]:
    package = load_story_package(PACKAGE)
    state = RuntimeState.bootstrap(package)
    provider = _ScriptedProvider(package)
    engine = RuntimeEngine(state, provider)
    for selection in PREFIX_TO_2A:
        _drive(engine, provider, selection)
    assert state.current_scene_id == "2A"
    return state, provider, engine


@pytest.mark.parametrize(
    ("selection", "expected_fact", "unexpected_fact"),
    [
        ("k_sl_2a_c_r5", "supervisor_convinced", "cover_suspected"),
        ("k_sl_2a_c_r6", "cover_suspected", "supervisor_convinced"),
    ],
)
@pytest.mark.parametrize("outcome_turn", [5, 6, 7])
def test_2a_recovery_never_fires_after_choice(
    selection: str, expected_fact: str, unexpected_fact: str, outcome_turn: int
) -> None:
    state, provider, engine = _start_at_2a()

    for _ in range(outcome_turn - 2):
        _drive(engine, provider, None)
    _drive(engine, provider, selection)

    facts = _true_facts(state)
    assert state.current_scene_id == "2B"
    assert expected_fact in facts
    assert "restricted_corridor_access" in facts
    assert unexpected_fact not in facts
    assert "inspection_recovery_ready" not in facts


def test_2a_neutral_staller_recovery_still_fires_and_exits() -> None:
    state, provider, engine = _start_at_2a()

    for _ in range(10):
        _drive(engine, provider, None)
        if state.current_scene_id != "2A":
            break

    facts = _true_facts(state)
    assert state.current_scene_id == "2B"
    assert "inspection_recovery_ready" in facts


def _start_at_2c() -> tuple[RuntimeState, _ScriptedProvider, RuntimeEngine]:
    state, provider, engine = _start_at_2a()
    _drive(engine, provider, "k_sl_2a_c_r5")
    assert state.current_scene_id == "2B"
    for selection in [
        "k_sl_2b_a_r1",
        None,
        None,
        None,
        None,
        None,
        None,
        "k_sl_2b_b_r5",
        "k_sl_2b_c_r3",
    ]:
        _drive(engine, provider, selection)
    assert state.current_scene_id == "2C"
    return state, provider, engine


@pytest.mark.parametrize("commitment", ["k_sl_2c_d_r3", "k_sl_2c_d_r4"])
@pytest.mark.parametrize(
    ("commit_turn", "timing"),
    [(4, "before_5"), (5, "at_5"), (6, "at_6"), (7, "at_7")],
)
@pytest.mark.parametrize("read_observation", [True, False])
def test_2c_commitment_is_exclusive_and_late_commitment_is_honoured(
    commitment: str, commit_turn: int, timing: str, read_observation: bool
) -> None:
    state, provider, engine = _start_at_2c()

    if read_observation:
        _drive(engine, provider, "k_sl_2c_c_r1")
        current_turn = 1
    else:
        current_turn = 0
    for _ in range(commit_turn - current_turn - 1):
        _drive(engine, provider, None)
    _drive(engine, provider, commitment if read_observation else None)

    facts = _true_facts(state)
    commitments = {"committed_to_transmit", "committed_to_rescue"}
    assert commit_turn == {"before_5": 4, "at_5": 5, "at_6": 6, "at_7": 7}[timing]
    if read_observation:
        expected_commitment = "committed_to_transmit" if commitment == "k_sl_2c_d_r3" else "committed_to_rescue"
        other_commitment = "committed_to_rescue" if commitment == "k_sl_2c_d_r3" else "committed_to_transmit"
        assert expected_commitment in facts
        assert other_commitment not in facts
        assert state.current_scene_id == "3A"
        if commit_turn < 7:
            assert "purge_recovery_ready" not in facts
        elif commit_turn == 7:
            # 2C holds the scene open until its minimum turn after a neutral recovery;
            # a commitment inside that window is an earned choice and is honoured.
            assert "purge_recovery_ready" in facts
    else:
        assert not commitments & facts
    assert not ("committed_to_transmit" in facts and "committed_to_rescue" in facts)


def test_2c_neutral_staller_recovery_still_fires_and_exits() -> None:
    state, provider, engine = _start_at_2c()

    for _ in range(10):
        _drive(engine, provider, None)
        if state.current_scene_id != "2C":
            break

    facts = _true_facts(state)
    assert state.current_scene_id == "3A"
    assert "purge_recovery_ready" in facts
    assert "combined_broadcast_rescue_plan_known" in facts
    assert not {"committed_to_transmit", "committed_to_rescue"} & facts
