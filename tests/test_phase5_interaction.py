from __future__ import annotations

from dataclasses import replace

import pytest

from storygame.runtime.contracts import (
    ActionSegment,
    InteractionEffect,
    InteractionProposal,
    RuntimeFailure,
    SpeechSegment,
    StateOperation,
    TurnResult,
)
from storygame.runtime.engine import RuntimeEngine
from storygame.runtime.facts import Fact
from storygame.runtime.state import bootstrap_runtime_state
from storygame.runtime.validation import validate_and_commit
from tests.test_causal_spatial_projection_phase4 import _projection


def _state():
    state = bootstrap_runtime_state(_projection())
    state.world.location = "relay"
    for subject in ("player", "engineer"):
        state.facts.retract_fact(Fact(predicate="at", subject=subject, object="dock"))
        state.facts.assert_fact(Fact(predicate="at", subject=subject, object="relay"))
    state.facts.retract_fact(Fact(predicate="present", subject="engineer", object="dock"))
    state.facts.assert_fact(Fact(predicate="present", subject="engineer", object="relay"))
    state.facts.assert_fact(Fact(predicate="knows", subject="player", object="failure"))
    state.facts.retract_fact(Fact(predicate="scene_pressure", subject="scene", value="0"))
    state.facts.assert_fact(Fact(predicate="scene_pressure", subject="scene", value="20"))
    for beat_id in ("setup", "rise"):
        state.beat_runtime[beat_id].completed_tags.add(f"{beat_id}_completed")
    return state


def _proposal(**overrides: object) -> InteractionProposal:
    values: dict[str, object] = {
        "interaction_frame_id": "engineer_warning",
        "initiation": "npc_initiated",
        "participant_ids": ("engineer", "player"),
        "segments": (
            SpeechSegment(
                speaker_id="engineer",
                addressee_ids=("player",),
                used_fact_ids=("failure",),
                text="The relay will fail unless we choose the repair now.",
            ),
            ActionSegment(actor_id="engineer", grounding="expressive", text="The engineer checks the warning display."),
        ),
        "effects": (),
    }
    values.update(overrides)
    return InteractionProposal(**values)


def test_npc_initiation_commits_active_continuation_without_forcing_completion() -> None:
    state = _state()

    updated = validate_and_commit(
        state,
        TurnResult(narration="The engineer turns from the console.", interaction=_proposal()),
    )

    assert updated.facts.has("interaction_active", "engineer_warning", value="true")
    assert updated.facts.has("interaction_recently_used", "engineer_warning", value="true")
    assert not updated.facts.has("interaction_completed", "engineer_warning", value="true")


def test_player_addressed_continuation_stays_in_the_active_interaction() -> None:
    state = _state()
    started = validate_and_commit(state, TurnResult(narration="The engineer turns.", interaction=_proposal()))
    reply = _proposal(initiation="continuation")

    updated = validate_and_commit(
        started,
        TurnResult(narration="The engineer answers.", interaction=reply),
        player_input="Engineer, can the crew get clear first?",
    )

    assert updated.facts.has("interaction_active", "engineer_warning", value="true")


@pytest.mark.parametrize(
    ("proposal", "code"),
    (
        (_proposal(initiation="player_initiated"), "INVALID_INTERACTION_INITIATION"),
        (_proposal(participant_ids=("navigator", "player")), "INTERACTION_PARTICIPANTS"),
    ),
)
def test_invalid_interaction_proposals_fail_closed(proposal: InteractionProposal, code: str) -> None:
    state = _state()

    with pytest.raises(RuntimeFailure) as exc_info:
        validate_and_commit(state, TurnResult(narration="The console hums.", interaction=proposal))

    assert exc_info.value.code == code
    assert not state.facts.has("interaction_active", "engineer_warning", value="true")


def test_malformed_material_action_fails_closed_at_the_provider_boundary() -> None:
    state = _state()
    payload = _proposal().model_dump(mode="json")
    payload["segments"] = [
        {
            "kind": "action",
            "actor_id": "engineer",
            "grounding": "material",
            "text": "The engineer moves the access key across the console.",
        }
    ]

    with pytest.raises(RuntimeFailure) as exc_info:
        TurnResult.from_provider({"narration": "The console hums.", "interaction": payload})

    assert exc_info.value.code == "INVALID_TURN"
    assert not state.facts.has("interaction_active", "engineer_warning", value="true")


def test_ineligible_initiation_and_refusal_abort_use_the_same_proposal_boundary() -> None:
    state = _state()
    state.facts.retract_fact(Fact(predicate="scene_pressure", subject="scene", value="20"))
    state.facts.assert_fact(Fact(predicate="scene_pressure", subject="scene", value="0"))

    with pytest.raises(RuntimeFailure) as exc_info:
        validate_and_commit(state, TurnResult(narration="The console hums.", interaction=_proposal()))

    assert exc_info.value.code == "INELIGIBLE_INTERACTION"

    state = _state()
    package = state.narrative_package
    assert package is not None
    primary = package.interaction_frames[0]
    follow_up = primary.model_copy(update={"id": "engineer_warning_alternate", "failure_forward_frame_ids": ()})
    state.narrative_package = replace(
        package,
        interaction_frames=(primary.model_copy(update={"failure_forward_frame_ids": (follow_up.id,)}), follow_up),
    )
    refused = _proposal(agency_mode="refuse", outcome="abort")

    updated = validate_and_commit(state, TurnResult(narration="The engineer waits.", interaction=refused))

    assert updated.facts.has("interaction_aborted", primary.id, value="true")
    assert updated.facts.has("interaction_active", follow_up.id, value="true")


def test_material_action_effect_commits_before_engine_response() -> None:
    state = _state()
    proposal = _proposal(
        segments=(
            ActionSegment(
                actor_id="engineer",
                grounding="material",
                text="The engineer releases the emergency latch.",
                effect_refs=("release_latch",),
            ),
        ),
        effects=(
            InteractionEffect(
                id="release_latch",
                operation=StateOperation(kind="add", path="world.flags", value="emergency_latch_released"),
            ),
        ),
    )

    class Model:
        def play_turn(self, context: object, *, json_object: bool) -> object:
            return {"narration": "The latch clicks open.", "interaction": proposal.model_dump(mode="json")}

    engine = RuntimeEngine(state, Model())
    response = engine.turn("I watch the engineer closely.")

    assert response.ok
    assert "emergency_latch_released" in engine.state.world.flags
