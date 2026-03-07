from __future__ import annotations

from storygame.llm.coherence import (
    CRITIQUE_DIMENSIONS,
    DEFAULT_CRITICAL_FLOORS,
    DEFAULT_THRESHOLD,
    CritiqueReport,
    build_default_coherence_gate,
    judge_critique_round,
)
from storygame.llm.context import NarrationContext


def _context(memory_fragments: tuple[str, ...] = ()) -> NarrationContext:
    return NarrationContext(
        room_name="Archive Hall",
        room_description="Cold stone and ledger stacks.",
        visible_items=("ledger", "inkpot"),
        visible_npcs=("keeper",),
        npc_facts=(),
        exits=("east", "west"),
        inventory=("bronze_key",),
        recent_events=(
            {
                "type": "talk",
                "message_key": "keeper says the forged ledger moved east",
                "entities": [],
                "tags": [],
                "turn_index": 2,
            },
        ),
        phase="rising_action",
        tension=0.5,
        beat="progressive_complication",
        goal="Follow the forged ledger trail.",
        action="talk keeper",
        memory_fragments=memory_fragments,
    )


def test_default_critics_return_all_rubric_dimensions():
    gate = build_default_coherence_gate()
    reports = gate.critique_round(_context(), "You ask the keeper about the forged ledger.")

    assert len(reports) >= 3
    for report in reports:
        assert set(report["scores"].keys()) == set(CRITIQUE_DIMENSIONS)


def test_judge_uses_weighted_rubric_threshold_and_floors():
    reports: list[CritiqueReport] = [
        {
            "critic_id": "continuity",
            "scores": {"continuity": 82, "causality": 84, "dialogue_fit": 80},
            "feedback": "solid",
        },
        {
            "critic_id": "causality",
            "scores": {"continuity": 80, "causality": 88, "dialogue_fit": 76},
            "feedback": "solid",
        },
        {
            "critic_id": "dialogue_fit",
            "scores": {"continuity": 81, "causality": 83, "dialogue_fit": 90},
            "feedback": "solid",
        },
    ]
    decision = judge_critique_round(
        reports,
        threshold=DEFAULT_THRESHOLD,
        critical_floors=DEFAULT_CRITICAL_FLOORS,
        round_index=1,
    )

    assert decision["status"] == "accepted"
    assert decision["total_score"] >= 80
    assert decision["critic_ids"] == ("continuity", "causality", "dialogue_fit")
    assert set(decision["rubric_components"].keys()) == set(CRITIQUE_DIMENSIONS)


def test_coherence_gate_revises_and_passes_before_max_rounds():
    class _RevisingNarrator:
        def __init__(self) -> None:
            self.calls = 0

        def generate(self, context: NarrationContext) -> str:
            self.calls += 1
            # The gate injects revision directives into memory_fragments.
            if any("mention causality and dialogue" in fragment for fragment in context.memory_fragments):
                return (
                    "In Archive Hall, the keeper points east because the forged ledger vanished there "
                    "after the bell diversion. You answer directly and press for the next witness."
                )
            return "Random line without continuity."

    narrator = _RevisingNarrator()
    gate = build_default_coherence_gate(max_rounds=10)
    result = gate.generate_with_gate(narrator, _context())

    assert result["judge_decision"]["status"] == "accepted"
    assert result["judge_decision"]["round_index"] <= 10
    assert narrator.calls == result["judge_decision"]["round_index"]


def test_coherence_gate_fails_deterministically_after_max_rounds():
    class _BadNarrator:
        def generate(self, context: NarrationContext) -> str:
            return "Nonsense unrelated to state."

    gate = build_default_coherence_gate(max_rounds=3)
    first = gate.generate_with_gate(_BadNarrator(), _context())
    second = gate.generate_with_gate(_BadNarrator(), _context())

    assert first["judge_decision"]["status"] == "failed"
    assert first["judge_decision"]["round_index"] == 3
    assert first["judge_decision"] == second["judge_decision"]


def test_hard_fail_triggers_when_narrator_token_budget_is_exhausted():
    class _LongNarrator:
        def generate(self, context: NarrationContext) -> str:
            return "word " * 200

    gate = build_default_coherence_gate(max_rounds=10, max_tokens_per_role={"narrator": 30, "critics": 3000})
    result = gate.generate_with_gate(_LongNarrator(), _context())

    assert result["judge_decision"]["status"] == "failed"
    assert result["telemetry"]["hard_fail_reason"] == "BUDGET_NARRATOR_TOKENS"
    assert result["telemetry"]["token_spend"]["narrator"] > 30


def test_hard_fail_triggers_when_wall_clock_budget_is_exhausted():
    class _SteadyNarrator:
        def generate(self, context: NarrationContext) -> str:
            return "In Archive Hall, the keeper says the ledger moved east because of the diversion."

    ticks = iter((0.0, 0.2, 0.4, 0.6, 0.8))
    gate = build_default_coherence_gate(
        max_rounds=10,
        wall_clock_timeout_ms=150,
        time_source=lambda: next(ticks),
    )
    result = gate.generate_with_gate(_SteadyNarrator(), _context())

    assert result["judge_decision"]["status"] == "failed"
    assert result["telemetry"]["hard_fail_reason"] == "BUDGET_WALL_CLOCK_TIMEOUT"
    assert result["telemetry"]["elapsed_ms"] >= 150


def test_telemetry_includes_rounds_tokens_elapsed_and_fail_reason():
    class _PassingNarrator:
        def generate(self, context: NarrationContext) -> str:
            return (
                "In Archive Hall, the keeper says the forged ledger moved east because of the bell diversion, "
                "and after that you talk to the keeper to follow the trail to the next witness."
            )

    gate = build_default_coherence_gate()
    result = gate.generate_with_gate(_PassingNarrator(), _context())
    telemetry = result["telemetry"]

    assert telemetry["critique_rounds"] >= 1
    assert "narrator" in telemetry["token_spend"]
    assert "critics" in telemetry["token_spend"]
    assert telemetry["elapsed_ms"] >= 0
    assert telemetry["hard_fail_reason"] == ""


def test_hard_fail_recovery_replans_with_constrained_reversal():
    class _ReversalNarrator:
        def generate(self, context: NarrationContext) -> str:
            if any("reversal_seed=" in fragment for fragment in context.memory_fragments):
                return (
                    "In Archive Hall, the keeper says the forged ledger moved east because of the bell diversion, "
                    "and after that you talk to the keeper to follow the trail to the next witness."
                )
            return "Nonsense unrelated to state."

    gate = build_default_coherence_gate(max_rounds=1, max_reversal_rounds=2)
    result = gate.generate_with_gate(_ReversalNarrator(), _context())
    reversal = result["reversal"]

    assert reversal["trigger_reason"] == "BUDGET_MAX_CRITIQUE_ROUNDS"
    assert reversal["replan_attempted"] is True
    assert reversal["replan_passed"] is True
    assert set(reversal["delta"].keys()) == {"preserved", "modified", "discarded"}
    assert any(item == "action=talk keeper" for item in reversal["delta"]["preserved"])
    assert any(item.startswith("reversal_seed=") for item in reversal["seed"])
    assert result["judge_decision"]["status"] == "accepted"


def test_reversal_branch_is_deterministic_for_identical_inputs():
    class _AlwaysBadNarrator:
        def generate(self, context: NarrationContext) -> str:
            return "Nonsense unrelated to state."

    gate = build_default_coherence_gate(max_rounds=1, max_reversal_rounds=1)
    first = gate.generate_with_gate(_AlwaysBadNarrator(), _context())
    second = gate.generate_with_gate(_AlwaysBadNarrator(), _context())

    assert first["reversal"] == second["reversal"]
