"""Rejection codes the runtime registers, used by the evidence tests."""

from __future__ import annotations

KNOWN_REJECTION_CODES = frozenset(
    {
        "multiple_knowledge_selection",
        "ineligible_selection",
        "missing_package_source",
        "invalid_grounding_reference",
        "unknown_grounding_reference",
        "invisible_grounding_reference",
        "uncited_knowledge",
        "narration_known_term_leak",
        "protected_narration_leak",
        "dialogue_speaker_missing",
        "unknown_dialogue_speaker",
        "dialogue_grounding_not_sayable",
        "selection_source_mismatch",
        "ungrounded_selection",
        "missing_knowledge_content",
        "protected_knowledge_mutation",
        "canonical_fact_mutation",
        "world_fact_mutation",
        "inactive_storylet_event",
        "unavailable_storylet",
        "invalid_storylet_realization",
        "storylet_operation_mismatch",
        "invalid_transition",
        "unsatisfied_transition_triggers",
    }
)
