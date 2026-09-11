"""Adversarial pre-commit narration safety coverage."""

from pathlib import Path

import pytest

from storygame.runtime.contracts import NarrationSegment, RuntimeContractError, parse_turn_proposal
from storygame.runtime.engine import RuntimeEngine
from storygame.runtime.state import RuntimeState
from storygame.runtime.validation import ProposalValidationError
from storygame.story_package.loader import load_story_package
from storygame.story_package.models import Audience

PACKAGE = load_story_package(Path("data/stories/continuity-initiative"))


def test_provider_cannot_smuggle_canonical_operations_or_event_ids() -> None:
    for leaked in (
        {"operations": [{"operation": "assert", "fact": {"predicate": "x", "subject": "story"}}]},
        {"event_id": "SL-1A-B"},
    ):
        with pytest.raises(RuntimeContractError):
            parse_turn_proposal({"segments": [{"kind": "narration", "text": "The room is quiet."}], **leaked})


def _run_rejected(text: str, *, selected: list[str] | None = None, package=PACKAGE) -> ProposalValidationError:
    state = RuntimeState.bootstrap(package)
    state.active_event_ids.add("SL-1A-B")
    payload = {
        "segments": [{"kind": "narration", "text": text, **({"grounding_ids": selected} if selected else {})}],
        "selected_knowledge_ids": selected or [],
    }
    before = state.snapshot()
    with pytest.raises(ProposalValidationError) as caught:
        RuntimeEngine(state, lambda _: payload).turn("Search the desk drawer.")
    assert state.snapshot() == before
    return caught.value


def test_future_entity_name_or_alias_is_rejected_without_grounding() -> None:
    error = _run_rejected("Brandon waits beside the door.")

    assert error.code == "narration_known_term_leak"


def test_protected_concept_alias_is_rejected() -> None:
    error = _run_rejected("The selection system is already ranking people.")

    assert error.code in {"protected_narration_leak", "narration_known_term_leak"}


def test_uncited_knowledge_is_rejected_even_when_the_candidate_is_eligible() -> None:
    error = _run_rejected("The hidden memory card waits beneath the drawer.")

    assert error.code in {"uncited_knowledge", "narration_known_term_leak"}


def test_wrong_speaker_dialogue_cannot_use_a_private_projection() -> None:
    knowledge_id = "k_sl_1a_b_r2"
    original = PACKAGE.knowledge_indexes.by_id[knowledge_id]
    private = original.model_copy(
        update={"audience": Audience(kind="characters", character_ids=("michelle",), player_visible=True)}
    )
    package = PACKAGE.model_copy(
        update={
            "knowledge": PACKAGE.knowledge.model_copy(
                update={
                    "knowledge": tuple(
                        private if item.id == knowledge_id else item for item in PACKAGE.knowledge.knowledge
                    )
                }
            ),
            "knowledge_indexes": PACKAGE.knowledge_indexes.model_copy(
                update={"by_id": {**PACKAGE.knowledge_indexes.by_id, knowledge_id: private}}
            ),
        }
    )
    state = RuntimeState.bootstrap(package)
    state.active_event_ids.add("SL-1A-B")
    text = "Michelle's hidden memory card plays the damaged recording about emergency broadcasts."
    payload = {
        "segments": [
            {
                "kind": "dialogue",
                "speaker_id": "kristin",
                "text": text,
                "grounding_ids": [knowledge_id],
            }
        ],
        "selected_knowledge_ids": [knowledge_id],
    }

    with pytest.raises(ProposalValidationError) as caught:
        RuntimeEngine(state, lambda _: payload).turn("Ask Michelle about the recording.")

    assert caught.value.code == "dialogue_grounding_not_sayable"


def test_unselected_candidate_effects_cannot_be_asserted_as_true() -> None:
    error = _run_rejected("The damaged recording warns against emergency broadcasts.")

    assert error.code in {"uncited_knowledge", "narration_known_term_leak"}


def test_target_scene_detail_is_rejected_before_transition() -> None:
    error = _run_rejected("The Regional facility's detention level opens ahead.")

    assert error.code == "narration_known_term_leak"


def test_invented_game_breaking_evidence_cannot_satisfy_a_future_dependency() -> None:
    error = _run_rejected("Brandon's hidden archive proves the future route is safe.")

    assert error.code == "narration_known_term_leak"


def test_named_durable_incidental_claim_is_rejected_but_local_color_is_allowed() -> None:
    error = _run_rejected("Kristin finds the hidden memory card in the drawer.")
    assert error.code in {"uncited_knowledge", "narration_known_term_leak"}

    state = RuntimeState.bootstrap(PACKAGE)
    proposal = RuntimeEngine(
        state,
        lambda _: {"segments": [{"kind": "narration", "text": "A loose screw glints beneath the drawer."}]},
    ).turn("Search the desk drawer.")
    assert proposal.segments == (NarrationSegment(kind="narration", text="A loose screw glints beneath the drawer."),)
