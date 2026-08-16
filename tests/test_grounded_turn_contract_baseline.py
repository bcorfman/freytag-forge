"""Phase-0 regression specifications for the typed staging-claim migration.

These tests are deliberately xfailed until Phase 1 makes material staging a
locally validated part of the ordinary-turn proposal.  They use the production
freeform provider seam and assert the required fail-closed behavior without
depending on wording-specific detection.
"""

from __future__ import annotations

import json

import pytest

from storygame.engine.freeform import (
    LlmFreeformProposalAdapter,
    OrdinaryTurnRecoveryExhausted,
    resolve_freeform_roleplay,
)
from tests.fast_fixtures import make_cached_story_state as build_default_state


@pytest.mark.parametrize(
    ("relation_family", "contradictory_narration"),
    (
        ("custody", "The case file waits on the balcony balustrade."),
        ("environment", "A sudden blizzard closes over the foyer."),
        ("access", "The sealed archive door swings open without resistance."),
        ("event", "At midnight, the chandelier crashes into the hall."),
    ),
)
@pytest.mark.xfail(
    strict=True,
    reason="Phase 1 staging_claims validation is not implemented; Phase 0 records this measured gap.",
)
def test_contradictory_material_narration_is_rejected_without_fact_commit(
    monkeypatch: pytest.MonkeyPatch,
    relation_family: str,
    contradictory_narration: str,
) -> None:
    state = build_default_state(seed=907, genre="mystery")
    facts_before = state.world_facts.all()
    provider_response = json.dumps(
        {
            "dialog_proposal": {
                "speaker": "narrator",
                "text": contradictory_narration,
                "tone": "in_world",
            },
            "action_proposal": {
                "intent": "inspect",
                "targets": [],
                "arguments": {},
                "proposed_effects": [],
            },
        }
    )
    monkeypatch.setattr(
        "storygame.engine.freeform._story_agent_chat_complete",
        lambda _mode, _system, _user: provider_response,
    )

    with pytest.raises(OrdinaryTurnRecoveryExhausted, match="ORDINARY_TURN_RECOVERY_EXHAUSTED"):
        resolve_freeform_roleplay(state, "inspect the scene", LlmFreeformProposalAdapter())

    assert state.world_facts.all() == facts_before, relation_family
