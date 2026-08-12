from __future__ import annotations

import pytest

from storygame.llm.coherence import CoherenceGate, _EntityReachabilityValidator
from storygame.llm.context import NarrationContext
from storygame.llm.contracts import (
    ContractValidationError,
    parse_agent_proposal,
    parse_critique_report,
    parse_judge_decision,
    parse_revision_directive,
    parse_story_patch,
)


def _context() -> NarrationContext:
    return NarrationContext(
        room_name="Operations Hall",
        room_description="Cold stone and mission boards.",
        visible_items=("dossier", "inkpot"),
        visible_npcs=("guide",),
        npc_facts=(),
        exits=("east", "west"),
        inventory=("route_key",),
        recent_events=(),
        phase="rising_action",
        tension=0.5,
        beat="progressive_complication",
        goal="Follow the forged directive trail.",
        action="talk guide",
        memory_fragments=(),
    )


def test_contract_parsers_accept_valid_payloads():
    patch = parse_story_patch(
        {
            "patch_id": "patch-1",
            "operations": (
                {"op": "set", "path": "goal", "value": "Follow ledger east"},
                {"op": "add", "path": "memory", "value": "guide testimony"},
            ),
            "rationale": "Apply deterministic updates from accepted narration.",
        }
    )
    proposal = parse_agent_proposal(
        {
            "agent_id": "narrator",
            "narration": "You question the guide and follow the trail east.",
            "story_patch": patch,
            "rationale": "Grounded in visible facts and current objective.",
        }
    )
    report = parse_critique_report(
        {
            "critic_id": "continuity",
            "scores": {"continuity": 84, "causality": 82, "dialogue_fit": 79},
            "feedback": "Continuity anchors are explicit and stable.",
        }
    )
    decision = parse_judge_decision(
        {
            "decision_id": "judge-001",
            "status": "accepted",
            "round_index": 1,
            "threshold": 80,
            "total_score": 82,
            "rubric_components": {"continuity": 84, "causality": 82, "dialogue_fit": 79},
            "critical_floors": {"continuity": 70, "causality": 70},
            "critic_ids": ("continuity",),
            "critic_reports": (report,),
            "judge": "director",
            "rationale": "All thresholds and critical floors are satisfied.",
        }
    )
    directive = parse_revision_directive(
        {
            "directive_id": "rev-001",
            "target_agent_id": "narrator",
            "focus_dimensions": ("causality",),
            "instruction": "Tie the next line to the latest event with explicit causality.",
            "rationale": "Causality score remains the weakest component.",
        }
    )

    assert proposal["agent_id"] == "narrator"
    assert patch["operations"][0]["op"] == "set"
    assert decision["judge"] == "director"
    assert directive["focus_dimensions"] == ("causality",)


def test_contract_parser_rejects_missing_fields_with_deterministic_error_code():
    with pytest.raises(ContractValidationError) as exc_info:
        parse_critique_report(
            {
                "critic_id": "continuity",
                "scores": {"continuity": 84, "causality": 82, "dialogue_fit": 79},
            }
        )

    exc = exc_info.value
    assert exc.code == "CONTRACT_INVALID_CRITIQUE_REPORT"
    assert exc.contract_name == "CritiqueReport"


def test_contract_parser_rejects_oversized_rationale():
    with pytest.raises(ContractValidationError) as exc_info:
        parse_revision_directive(
            {
                "directive_id": "rev-002",
                "target_agent_id": "narrator",
                "focus_dimensions": ("continuity",),
                "instruction": "Keep room and inventory facts explicit.",
                "rationale": "x" * 281,
            }
        )

    assert exc_info.value.code == "CONTRACT_INVALID_REVISION_DIRECTIVE"


def test_coherence_gate_rejects_malformed_critic_contracts():
    class _InvalidCritic:
        critic_id = "broken"

        def critique(self, context: NarrationContext, narration: str) -> dict[str, object]:  # noqa: ARG002
            return {"critic_id": "broken", "scores": {"continuity": 99, "causality": 99, "dialogue_fit": 99}}

    class _Narrator:
        def generate(self, context: NarrationContext) -> str:  # noqa: ARG002
            return "The guide points east because the forged directive moved after the alarm."

    gate = CoherenceGate(
        critics=(_InvalidCritic(),),
        validators=(_EntityReachabilityValidator(),),
        max_rounds=1,
    )

    with pytest.raises(RuntimeError, match="CONTRACT_INVALID_CRITIQUE_REPORT"):
        gate.generate_with_gate(_Narrator(), _context())
