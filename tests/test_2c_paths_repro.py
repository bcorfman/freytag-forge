"""Stage 5 characterization of the skipped-copy and Michelle-first 2C paths."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from bench.core import advance_state_to_scene
from storygame.runtime.candidate_matcher import uniquely_matched_authored_handoff
from storygame.runtime.cloudflare import CloudflareTurnProvider
from storygame.runtime.engine import RuntimeEngine
from storygame.runtime.knowledge import KnowledgeProjector
from storygame.runtime.reveal_eligibility import explain_reveal
from storygame.runtime.state import RuntimeState
from storygame.runtime.world_model import world_for
from storygame.story_package.loader import load_story_package

PACKAGE = load_story_package(Path("data/stories/continuity-initiative"))
COPY_REVEALS = {"k_sl_2c_c_r1", "k_sl_2c_c_r2"}
MESSAGE_REVEALS = {"k_sl_2c_d_r1", "k_sl_2c_d_r2"}
COPY_PATH_FACTS = {"evidence_ready_to_transmit", "rebecca_office_required_for_broadcast"}


class _Response:
    def __init__(self, body: object) -> None:
        self.body = json.dumps(body).encode()

    def __enter__(self) -> _Response:
        return self

    def __exit__(self, *_args: object) -> None:
        return None

    def read(self) -> bytes:
        return self.body


def _normal_response(_request: object, **_kwargs: object) -> _Response:
    return _Response(
        {
            "narration": json.dumps(
                {
                    "segments": [{"kind": "narration", "text": "The scene continues."}],
                    "selected_knowledge_ids": [],
                }
            )
        }
    )


def _engine(monkeypatch: pytest.MonkeyPatch) -> tuple[RuntimeState, RuntimeEngine, CloudflareTurnProvider]:
    monkeypatch.setenv("FREYTAG_SEMANTIC_REVEAL", "0")
    monkeypatch.setattr("storygame.runtime.cloudflare.urlopen", _normal_response)
    state = RuntimeState.bootstrap(PACKAGE)
    advance_state_to_scene(PACKAGE, state, "2C")
    provider = CloudflareTurnProvider(worker_url="https://worker.example/turn", token="", state=state)
    return state, RuntimeEngine(state, provider), provider


def _has_fact(state: RuntimeState, fact_id: str) -> bool:
    return any(fact.predicate == fact_id and fact.value == "true" for fact in state.facts.asserted)


def _fact_values(state: RuntimeState, fact_ids: set[str]) -> dict[str, bool]:
    return {fact_id: _has_fact(state, fact_id) for fact_id in sorted(fact_ids)}


def _run_until_exit(
    state: RuntimeState,
    engine: RuntimeEngine,
    commands: tuple[str, ...],
    *,
    assert_no_copy_match: bool = False,
) -> tuple[object, tuple[str, ...], int]:
    selected: list[str] = []
    projector = KnowledgeProjector()
    for turn_number in range(1, 61):
        command = commands[turn_number - 1] if turn_number <= len(commands) else "Look around."
        if assert_no_copy_match:
            projection = projector.project(state, "player", command)
            matched = uniquely_matched_authored_handoff(command, projection.candidates)
            assert matched is None or matched.candidate.id not in COPY_REVEALS
        result = engine.turn(command)
        selected.extend(result.selected_knowledge_ids)
        if state.current_scene_id != "2C":
            return result, tuple(selected), turn_number
    pytest.fail("2C did not exit within the 60-turn cap")


def _continue_3a(state: RuntimeState, engine: RuntimeEngine) -> tuple[tuple[str, ...], object]:
    selected: list[str] = []
    commands = (
        "Find Michelle by the stolen radio.",
        "Read the experiment records.",
        "Interview the senior official about the surface gates.",
        "Start the coordinated uprising.",
    )
    for command in commands + ("Look around.",) * 20:
        result = engine.turn(command)
        selected.extend(result.selected_knowledge_ids)
        if state.current_scene_id != "3A":
            return tuple(selected), result
    pytest.fail("3A did not exit within the scripted cap")


def test_2c_static_requires_establishes_and_bridges() -> None:
    knowledge = PACKAGE.knowledge_indexes.by_id
    expected_2c = {
        "k_sl_2c_a_r1": ((), ("rebecca_offer_active",)),
        "k_sl_2c_a_r2": ((), ("rebecca_offer_active", "antagonist_split_known")),
        "k_sl_2c_b_r1": ((), ("purge_clock_started",)),
        "k_sl_2c_b_r2": ((), ("purge_clock_started",)),
        "k_sl_2c_c_r1": (("janus_evidence",), ("evidence_ready_to_transmit",)),
        "k_sl_2c_c_r2": (("janus_evidence",), ("evidence_ready_to_transmit",)),
        "k_sl_2c_d_r1": (
            ("purge_clock_started", "evidence_ready_to_transmit"),
            ("rebecca_office_required_for_broadcast", "combined_broadcast_rescue_plan_known"),
        ),
        "k_sl_2c_d_r2": (
            ("purge_clock_started", "evidence_ready_to_transmit"),
            ("rebecca_office_required_for_broadcast", "combined_broadcast_rescue_plan_known"),
        ),
    }
    for reveal_id, (required, established) in expected_2c.items():
        reveal = knowledge[reveal_id]
        assert tuple(item.fact_id for item in reveal.requires) == required
        assert tuple(item.fact_id for item in reveal.establishes) == established

    expected_3a = {
        "k_sl_3a_a_r1": (),
        "k_sl_3a_a_r2": (),
        "k_sl_3a_b_r1": ("michelle_reached",),
        "k_sl_3a_b_r2": ("michelle_reached",),
        "k_sl_3a_e_r1": ("michelle_reached", "behavioral_experiments_known"),
        "k_sl_3a_d_r1": ("michelle_reached", "behavioral_experiments_known"),
        "k_sl_3a_d_r2": ("michelle_reached", "behavioral_experiments_known"),
        "k_sl_3a_c_r1": ("michelle_reached", "uprising_prepared", "military_override_codes_available"),
        "k_sl_3a_c_r2": (
            "michelle_reached",
            "uprising_prepared",
            "military_override_codes_available",
            "override_codes_deadline_known",
        ),
    }
    for reveal_id, required in expected_3a.items():
        assert tuple(item.fact_id for item in knowledge[reveal_id].requires) == required

    pacing = next(item for item in PACKAGE.pacing.scenes if item.scene_id == "2C")
    assert (pacing.min_turns, pacing.nudge_after_turns, pacing.handoff_after_turns) == (8, 9, 16)
    transition = next(item for item in PACKAGE.pacing.transitions if item.id == "t_2c_3a")
    assert [(item.fact_id, item.equals) for item in transition.triggers] == [
        ("combined_broadcast_rescue_plan_known", True)
    ]
    assert transition.required_dependencies == ("brandon",)

    bridge = next(item for item in PACKAGE.storylet_routes.bridge_events if item.id == "bridge_2c_combined_plan")
    assert bridge.activation.all_facts_true == (
        "purge_clock_started",
        "evidence_ready_to_transmit",
        "rebecca_office_required_for_broadcast",
    )
    assert tuple(item.fact_id for item in bridge.operations) == ("combined_broadcast_rescue_plan_known",)

    bridge_3a = next(item for item in PACKAGE.storylet_routes.bridge_events if item.id == "bridge_3a_command_assault")
    assert bridge_3a.activation.all_facts_true == (
        "michelle_reached",
        "detention_uprising_started",
        "military_override_codes_available",
    )


def test_canonical_2c_order_is_earned_and_enters_3a(monkeypatch: pytest.MonkeyPatch) -> None:
    state, engine, _provider = _engine(monkeypatch)
    result, selected, turns = _run_until_exit(
        state,
        engine,
        (
            "Read the transfer orders.",
            "Copy the JANUS files to my USB drive.",
            "Argue about sending the copied files.",
            "Read Michelle's coded message.",
            "Follow the maintenance route.",
        ),
    )

    assert turns == 8
    assert state.current_scene_id == "3A"
    assert selected == ("k_sl_2c_b_r1", "k_sl_2c_c_r1", "k_sl_2c_d_r1")
    assert engine.last_attempt is not None
    assert engine.last_attempt.transition_cause == "earned"
    assert _fact_values(state, COPY_PATH_FACTS) == {
        "evidence_ready_to_transmit": True,
        "rebecca_office_required_for_broadcast": True,
    }
    assert (
        explain_reveal(state, "player", PACKAGE.knowledge_indexes.by_id["k_sl_2c_c_r2"]).reason,
        explain_reveal(state, "player", PACKAGE.knowledge_indexes.by_id["k_sl_2c_c_r2"]).detail,
    ) == (
        "already_established",
        "k_sl_2c_c_r2",
    )
    assert (
        explain_reveal(state, "player", PACKAGE.knowledge_indexes.by_id["k_sl_2c_d_r2"]).reason,
        explain_reveal(state, "player", PACKAGE.knowledge_indexes.by_id["k_sl_2c_d_r2"]).detail,
    ) == (
        "already_established",
        "k_sl_2c_d_r2",
    )
    assert "evidence was ready to transmit" in result.narration

    selected_3a, _ = _continue_3a(state, engine)
    assert selected_3a == (
        "k_sl_3a_a_r1",
        "k_sl_3a_b_r1",
        "k_sl_3a_d_r1",
        "k_sl_3a_c_r1",
    )
    assert not any("copy" in text.casefold() for text in (result.narration,))


def test_michelle_first_rejects_message_until_copy_then_enters_3a(monkeypatch: pytest.MonkeyPatch) -> None:
    state, engine, provider = _engine(monkeypatch)
    first = engine.turn("Read the transfer orders.")
    assert first.selected_knowledge_ids == ("k_sl_2c_b_r1",)
    rejected: list[tuple[str, str, str]] = []
    for reveal_id in sorted(MESSAGE_REVEALS):
        eligibility = explain_reveal(state, "player", PACKAGE.knowledge_indexes.by_id[reveal_id])
        rejected.append((reveal_id, eligibility.reason, eligibility.detail))
    assert rejected == [
        ("k_sl_2c_d_r1", "prerequisite_missing", "evidence_ready_to_transmit"),
        ("k_sl_2c_d_r2", "prerequisite_missing", "evidence_ready_to_transmit"),
    ]

    result, selected, turns = _run_until_exit(
        state,
        engine,
        (
            "Read Michelle's coded message.",
            "Follow the maintenance route.",
            "Copy the JANUS files to my USB drive.",
            "Read Michelle's coded message.",
        ),
    )

    assert turns == 7
    assert state.current_scene_id == "3A"
    assert selected == ("k_sl_2c_c_r1", "k_sl_2c_d_r1")
    assert provider.last_reveal_selection["outcome"] == "no_eligible_action"
    assert engine.last_attempt is not None
    assert engine.last_attempt.transition_cause == "earned"
    assert "evidence was ready to transmit" in result.narration
    selected_3a, _ = _continue_3a(state, engine)
    assert selected_3a[:2] == ("k_sl_3a_a_r1", "k_sl_3a_b_r1")


def test_skipped_copy_current_forced_handoff_is_characterized(monkeypatch: pytest.MonkeyPatch) -> None:
    state, engine, _provider = _engine(monkeypatch)
    result, selected, turns = _run_until_exit(
        state,
        engine,
        ("Read the transfer orders.",),
        assert_no_copy_match=True,
    )

    assert turns == 16
    assert selected == ("k_sl_2c_b_r1",)
    assert state.current_scene_id == "3A"
    assert engine.last_attempt is not None
    assert engine.last_attempt.transition_cause == "forced"
    assert _fact_values(state, COPY_PATH_FACTS) == {
        "evidence_ready_to_transmit": True,
        "rebecca_office_required_for_broadcast": True,
    }
    assert "have enough evidence" in result.narration
    assert "combined mission" in result.narration

    selected_3a, result_3a = _continue_3a(state, engine)
    assert selected_3a[:2] == ("k_sl_3a_a_r1", "k_sl_3a_b_r1")
    assert "evidence" not in result_3a.narration.casefold()


def test_skipped_copy_forced_exit_matches_the_world_because_kristin_already_carries_the_files(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """2C entry places copied_janus_files with Kristin ('She could check them now'); k_sl_2c_c_r1 only
    acknowledges them, so the forced handoff's 'evidence in hand' text agrees with the world."""

    state, engine, _provider = _engine(monkeypatch)
    _run_until_exit(state, engine, ("Read the transfer orders.",), assert_no_copy_match=True)

    assert state.current_scene_id == "3A"
    assert _has_fact(state, "janus_evidence")
    world = world_for(state.package, state.facts)
    assert world.parent("copied_janus_files") == "kristin"
