from pathlib import Path

from bench.core import advance_state_to_scene
from storygame.runtime.facts import Fact
from storygame.runtime.reference_resolution import clarification_text, resolve_references, resolved_reference_names
from storygame.runtime.state import RuntimeState
from storygame.story_package.loader import _compile_knowledge_indexes, load_story_package
from storygame.story_package.models import ItemPlacement

PACKAGE = load_story_package(Path("data/stories/continuity-initiative"))


def _state(package=PACKAGE, scene_id: str = "1A", *, recovered: bool = False) -> RuntimeState:
    state = RuntimeState.bootstrap(package)
    advance_state_to_scene(package, state, scene_id)
    if recovered:
        state.facts.assert_fact(Fact(predicate="memory_card_recovered", subject="story", value="true"))
    return state


def _card_collision_package():
    transit_card = next(item for item in PACKAGE.world.items if item.id == "transit_card")
    world = PACKAGE.world.model_copy(
        update={
            "items": tuple(
                transit_card.model_copy(update={"name": "transit card"}) if item.id == transit_card.id else item
                for item in PACKAGE.world.items
            )
        }
    )
    scenes = tuple(
        scene.model_copy(
            update={
                "metadata": scene.metadata.model_copy(
                    update={
                        "item_ids": (*scene.metadata.item_ids, "transit_card"),
                        "item_placements": {
                            **scene.metadata.item_placements,
                            "transit_card": ItemPlacement(parent="kristin"),
                        },
                    }
                )
            }
        )
        if scene.metadata.scene_id == "1A"
        else scene
        for scene in PACKAGE.scenes
    )
    return PACKAGE.model_copy(
        update={
            "world": world,
            "scenes": scenes,
            "knowledge_indexes": _compile_knowledge_indexes(PACKAGE.knowledge, world),
        }
    )


def test_protected_card_is_not_a_reference_before_discovery() -> None:
    state = _state()

    for command in ("Search the card.", "Take the card."):
        result = resolve_references(state, command)
        assert result.outcome == "passthrough"
        assert result.question is None
        assert result.resolutions == ()
        assert resolved_reference_names(state, command) == ()


def test_discovered_card_resolves_to_its_full_name() -> None:
    state = _state(recovered=True)

    result = resolve_references(state, "Read the card.")

    assert result.outcome == "resolved"
    assert result.command == "Read the card."
    assert result.resolutions == (("card", "memory_card"),)
    assert resolved_reference_names(state, "Read the card.") == ("Michelle's memory card",)


def test_two_unprotected_cards_ask_and_answer_with_a_spliced_name() -> None:
    state = _state(_card_collision_package(), recovered=True)
    command = "Use the card."

    question = resolve_references(state, command)
    answer = resolve_references(state, "transit", clarifies=command)

    assert question.outcome == "asked"
    assert question.question is not None
    assert clarification_text(question.question) == "Do you mean Michelle's memory card or the transit card?"
    assert answer.outcome == "answered"
    assert answer.command == "Use the transit card."
    assert answer.resolutions == (("card", "transit_card"),)


def test_protected_memory_card_does_not_make_transit_card_ambiguous() -> None:
    state = _state(_card_collision_package())

    result = resolve_references(state, "Use the card.")

    assert result.outcome == "resolved"
    assert result.question is None
    assert result.command == "Use the card."
    assert result.resolutions == (("card", "transit_card"),)


def test_earning_memory_card_makes_the_same_collision_ambiguous() -> None:
    state = _state(_card_collision_package())
    state.facts.assert_fact(Fact(predicate="memory_card_recovered", subject="story", value="true"))

    result = resolve_references(state, "Use the card.")

    assert result.outcome == "asked"
    assert result.question is not None
    assert result.question.options == (
        ("memory_card", "Michelle's memory card"),
        ("transit_card", "transit card"),
    )


def test_characterization_held_transit_card_bare_and_article_are_guarded() -> None:
    """Synthetic state: narration refuses both forms.

    Reference resolution still resolves bare card to the transit card.
    """
    import pytest

    from storygame.runtime.contracts import NarrationSegment, ResolvedTurnProposal
    from storygame.runtime.knowledge import KnowledgeGuards, KnowledgeProjector
    from storygame.runtime.narration_safety import NarrationSafetyValidator
    from storygame.runtime.validation import ProposalValidationError
    from storygame.runtime.world_model import world_for

    state = _state(_card_collision_package())
    assert world_for(state.package, state.facts).parent("transit_card") == "kristin"
    indexes = state.package.knowledge_indexes
    from storygame.story_package.loader import guarded_narration_terms

    assert "card" not in guarded_narration_terms(indexes)
    assert "card" in indexes.disclosure_guards
    assert "memory_card_word_guard" in indexes.disclosure_guards["card"]
    assert "k_sl_1a_b_r0" in indexes.leak_term_to_knowledge["the card"]
    assert KnowledgeGuards(state).unearned(indexes.leak_term_to_knowledge["the card"])
    validator = NarrationSafetyValidator()
    with pytest.raises(ProposalValidationError, match="guarded term 'card'") as rejected:
        validator.validate(
            state,
            state,
            ResolvedTurnProposal(segments=(NarrationSegment(kind="narration", text="card"),)),
            KnowledgeProjector(),
            "Use the transit card.",
        )
    assert rejected.value.code == "disclosure_guard_leak"
    with pytest.raises(ProposalValidationError, match="unavailable knowledge 'the card'") as rejected:
        validator.validate(
            state,
            state,
            ResolvedTurnProposal(segments=(NarrationSegment(kind="narration", text="the card"),)),
            KnowledgeProjector(),
            "Use the transit card.",
        )
    assert rejected.value.code == "narration_known_term_leak"
