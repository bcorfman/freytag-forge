"""Redacted, opt-in observability for one completed runtime turn."""

from __future__ import annotations

from collections.abc import Iterable
from hashlib import sha256

from storygame.runtime.contracts import ResolvedTurnProposal
from storygame.runtime.engine import RuntimeEngine


def build_knowledge_audit(
    engine: RuntimeEngine, proposal: ResolvedTurnProposal, fact_keys_before: Iterable[str]
) -> dict[str, object]:
    """Build an audit containing identifiers and measurements, never content."""

    projection = engine.last_projection
    candidates = projection.candidates if projection is not None else ()
    segments = [
        {
            "kind": segment.kind,
            "speaker_id": segment.speaker_id,
            "grounding_ids": list(segment.grounding_ids),
            "character_count": len(segment.text),
            "sha256": sha256(segment.text.encode("utf-8")).hexdigest(),
        }
        for segment in proposal.segments
    ]
    return {
        "context_candidate_ids": sorted(item.id for item in candidates),
        "provider_selected_ids": sorted(proposal.selected_knowledge_ids),
        "resolved_source_ids": sorted(
            f"{event.event_id}/{event.realization_id}" for event in proposal.events if event.realization_id
        ),
        "fact_keys_before": sorted(set(fact_keys_before)),
        "fact_keys_after": sorted({fact.predicate for fact in engine.state.facts.asserted}),
        "accepted_segments": segments,
        "result": "committed",
        "rejection_code": None,
        "recovery_used": engine.state.last_turn_delivery.recovery_used,
    }
