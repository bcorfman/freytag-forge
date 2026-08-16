from __future__ import annotations

import pytest

from storygame.engine.freeform import LlmFreeformProposalAdapter, resolve_freeform_roleplay
from storygame.engine.staging_claims import validate_staging_claims
from tests.fast_fixtures import make_cached_story_state as build_default_state


def test_candidate_claims_cover_each_generic_relation() -> None:
    state = build_default_state(seed=907, genre="mystery")
    state.world_facts.assert_fact("event", "arrival", "front_steps")

    validate_staging_claims(
        state,
        (
            {
                "relation": "custody",
                "subject_id": "case_file",
                "target_id": "daria_stone",
                "location_id": "",
                "state_id": "",
            },
            {
                "relation": "environment",
                "subject_id": "",
                "target_id": "",
                "location_id": "front_steps",
                "state_id": "outdoor",
            },
            {
                "relation": "access",
                "subject_id": "mansion_entrance",
                "target_id": "",
                "location_id": "front_steps",
                "state_id": "available",
            },
            {
                "relation": "event",
                "subject_id": "arrival",
                "target_id": "",
                "location_id": "front_steps",
                "state_id": "",
            },
        ),
    )


@pytest.mark.parametrize(
    "claim",
    (
        {"relation": "custody", "subject_id": "case_file", "target_id": "player", "location_id": "", "state_id": ""},
        {
            "relation": "environment",
            "subject_id": "",
            "target_id": "",
            "location_id": "front_steps",
            "state_id": "blizzard",
        },
        {
            "relation": "access",
            "subject_id": "mansion_entrance",
            "target_id": "",
            "location_id": "front_steps",
            "state_id": "blocked",
        },
        {
            "relation": "event",
            "subject_id": "midnight_crash",
            "target_id": "",
            "location_id": "front_steps",
            "state_id": "",
        },
    ),
)
def test_contradictory_claim_is_rejected(claim: dict[str, str]) -> None:
    with pytest.raises(ValueError, match="STAGING_CLAIM"):
        validate_staging_claims(build_default_state(seed=907, genre="mystery"), (claim,))


def test_duplicate_and_non_visible_claims_are_rejected() -> None:
    state = build_default_state(seed=907, genre="mystery")
    duplicate = {
        "relation": "environment",
        "subject_id": "",
        "target_id": "",
        "location_id": "front_steps",
        "state_id": "outdoor",
    }
    with pytest.raises(ValueError, match="DUPLICATE"):
        validate_staging_claims(state, (duplicate, duplicate))
    with pytest.raises(ValueError, match="NOT_VISIBLE"):
        validate_staging_claims(state, ({**duplicate, "location_id": "foyer"},))


def test_claim_failure_uses_shared_recovery_budget_before_commit(monkeypatch: pytest.MonkeyPatch) -> None:
    state = build_default_state(seed=907, genre="mystery")
    responses = iter(
        (
            {
                "dialog_proposal": {"speaker": "narrator", "text": "The file is yours.", "tone": "in_world"},
                "action_proposal": {"intent": "inspect", "targets": [], "arguments": {}, "proposed_effects": []},
                "staging_claims": [
                    {
                        "relation": "custody",
                        "subject_id": "case_file",
                        "target_id": "player",
                        "location_id": "",
                        "state_id": "",
                    }
                ],
            },
            {
                "dialog_proposal": {"speaker": "narrator", "text": "Daria keeps the file close.", "tone": "in_world"},
                "action_proposal": {"intent": "inspect", "targets": [], "arguments": {}, "proposed_effects": []},
                "staging_claims": [
                    {
                        "relation": "custody",
                        "subject_id": "case_file",
                        "target_id": "daria_stone",
                        "location_id": "",
                        "state_id": "",
                    }
                ],
            },
        )
    )
    monkeypatch.setattr(
        "storygame.engine.freeform._story_agent_chat_complete", lambda *_args: __import__("json").dumps(next(responses))
    )

    result = resolve_freeform_roleplay(state, "inspect the scene", LlmFreeformProposalAdapter())

    assert result["state"].turn_index == state.turn_index + 1
