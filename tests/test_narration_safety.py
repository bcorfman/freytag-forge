"""Adversarial pre-commit narration safety coverage."""

from pathlib import Path

import pytest

from storygame.runtime.contracts import NarrationSegment, RuntimeContractError, parse_turn_proposal
from storygame.runtime.engine import RuntimeEngine
from storygame.runtime.facts import Fact
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


def _run_rejected(
    text: str,
    *,
    selected: list[str] | None = None,
    beats: tuple[str, ...] = (),
    package=PACKAGE,
) -> ProposalValidationError:
    state = RuntimeState.bootstrap(package)
    state.active_event_ids.add("SL-1A-B")
    payload = {
        "segments": [{"kind": "narration", "text": text, **({"grounding_ids": selected} if selected else {})}],
        "selected_knowledge_ids": selected or [],
    }
    before = state.snapshot()

    def provider(_player_input: str) -> dict[str, object]:
        state.last_turn_delivery = state.last_turn_delivery.model_copy(update={"beats_projected": beats})
        return payload

    with pytest.raises(ProposalValidationError) as caught:
        RuntimeEngine(state, provider).turn("Search the desk drawer.")
    assert state.snapshot() == before
    return caught.value


def _run_accepted(text: str, *, beats: tuple[str, ...] = (), package=PACKAGE):
    state = RuntimeState.bootstrap(package)
    state.facts.assert_fact(Fact(predicate="memory_card_in_kristins_custody", subject="story", value="true"))
    state.active_event_ids.add("SL-1A-B")

    def provider(_player_input: str) -> dict[str, object]:
        state.last_turn_delivery = state.last_turn_delivery.model_copy(update={"beats_projected": beats})
        return {"segments": [{"kind": "narration", "text": text}], "selected_knowledge_ids": []}

    return RuntimeEngine(state, provider).turn("Search the desk drawer.")


@pytest.mark.parametrize(
    ("text", "expected_code"),
    [
        pytest.param(
            "Brandon waits beside the door.",
            "narration_known_term_leak",
            id="future_entity_name_or_alias_is_rejected_without_grounding",
        ),
        pytest.param(
            "The Regional facility's detention level opens ahead.",
            "narration_known_term_leak",
            id="target_scene_detail_is_rejected_before_transition",
        ),
        pytest.param(
            "Brandon's hidden archive proves the future route is safe.",
            "narration_known_term_leak",
            id="invented_game_breaking_evidence_cannot_satisfy_a_future_dependency",
        ),
    ],
)
def test_rejected_narration_cannot_leak_future_details(text: str, expected_code: str) -> None:
    error = _run_rejected(text)

    assert error.code == expected_code


def test_determiner_variant_shares_knowledge_owners_with_bare_term() -> None:
    indexes = PACKAGE.knowledge_indexes

    assert indexes.term_to_knowledge["the memory card"] == indexes.term_to_knowledge["memory card"]


def test_earned_memory_card_accepts_determiner_but_unearned_term_is_rejected() -> None:
    knowledge_id = "k_sl_1a_b_r2"
    knowledge = PACKAGE.knowledge_indexes.by_id[knowledge_id]
    state = RuntimeState.bootstrap(PACKAGE)
    for effect in knowledge.establishes:
        state.facts.assert_fact(Fact(predicate=effect.fact_id, subject="story", value=str(effect.value).lower()))

    proposal = RuntimeEngine(
        state,
        lambda _: {
            "segments": [
                {
                    "kind": "narration",
                    "text": "The memory card is safe in Michelle's hands.",
                    "grounding_ids": [knowledge_id],
                }
            ]
        },
    ).turn("Inspect the memory card.")

    assert proposal.segments[0].text == "The memory card is safe in Michelle's hands."

    error = _run_rejected("The memory card waits beneath the drawer.")
    assert error.code in {"uncited_knowledge", "narration_known_term_leak"}


@pytest.mark.parametrize(
    ("text", "expected_codes"),
    [
        pytest.param(
            "The selection system is already ranking people.",
            {"protected_narration_leak", "narration_known_term_leak"},
            id="protected_concept_alias_is_rejected",
        ),
        pytest.param(
            "The hidden memory card waits beneath the drawer.",
            {"uncited_knowledge", "narration_known_term_leak"},
            id="uncited_knowledge_is_rejected_even_when_the_candidate_is_eligible",
        ),
        pytest.param(
            "The damaged recording warns against emergency broadcasts.",
            {"uncited_knowledge", "narration_known_term_leak"},
            id="unselected_candidate_effects_cannot_be_asserted_as_true",
        ),
    ],
)
def test_rejected_narration_cannot_use_unavailable_knowledge(text: str, expected_codes: set[str]) -> None:
    error = _run_rejected(text)

    assert error.code in expected_codes


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
    state.facts.assert_fact(Fact(predicate="memory_card_in_kristins_custody", subject="story", value="true"))
    state.active_event_ids.add("SL-1A-B")
    text = "Michelle's memory card was under the KMS drawer and plays the damaged recording about emergency broadcasts."
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


def test_named_durable_incidental_claim_is_rejected_but_local_color_is_allowed() -> None:
    error = _run_rejected("Kristin finds the hidden memory card in the drawer.")
    assert error.code in {"uncited_knowledge", "narration_known_term_leak"}

    state = RuntimeState.bootstrap(PACKAGE)
    proposal = RuntimeEngine(
        state,
        lambda _: {"segments": [{"kind": "narration", "text": "A loose screw glints beside the desk."}]},
    ).turn("Search the desk drawer.")
    assert proposal.segments == (NarrationSegment(kind="narration", text="A loose screw glints beside the desk."),)


def test_projected_beat_licenses_only_its_own_uncommitted_vocabulary() -> None:
    beat = "scene-1a2--michelles-last-investigation"

    proposal = _run_accepted("Kristin turns over the memory card she has just worked loose.", beats=(beat,))
    assert proposal.segments[0].text == "Kristin turns over the memory card she has just worked loose."

    no_beat = _run_rejected("Kristin turns over the memory card she has just worked loose.")
    assert no_beat.code == "narration_known_term_leak"

    unrelated = _run_rejected("The facility entrance waits somewhere beyond the trees.", beats=(beat,))
    assert unrelated.code == "narration_known_term_leak"

    protected = _run_rejected("The selection system is already ranking people.", beats=(beat,))
    assert protected.code == "protected_narration_leak"
