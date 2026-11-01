"""Coverage for the separate recall and narration-leak vocabularies."""

from pathlib import Path

import pytest

from storygame.runtime.engine import RuntimeEngine
from storygame.runtime.state import RuntimeState
from storygame.runtime.validation import ProposalValidationError
from storygame.story_package.loader import _compile_knowledge_indexes, load_story_package

PACKAGE = load_story_package(Path("data/stories/continuity-initiative"))


def _package_for(*, leak_terms: tuple[str, ...] | None, must_convey: tuple[tuple[str, ...], ...] | None = None):
    legacy_knowledge = tuple(item.model_copy(update={"leak_terms": None}) for item in PACKAGE.knowledge.knowledge)
    item = legacy_knowledge[0].model_copy(
        update={
            "aliases": ("sealed letter",),
            "leak_terms": leak_terms,
            "must_convey": must_convey or (("sealed letter", "harmless delivery phrase"),),
        }
    )
    catalog = PACKAGE.knowledge.model_copy(update={"knowledge": (item,) + legacy_knowledge[1:]})
    indexes = _compile_knowledge_indexes(catalog, PACKAGE.world)
    return PACKAGE.model_copy(update={"knowledge": catalog, "knowledge_indexes": indexes})


def _run(package, text: str):
    state = RuntimeState.bootstrap(package)
    before = state.snapshot()
    with pytest.raises(ProposalValidationError) as caught:
        RuntimeEngine(
            state,
            lambda _: {"segments": [{"kind": "narration", "text": text}], "selected_knowledge_ids": []},
        ).turn("Search the desk.")
    return state, before, caught.value


def test_absent_field_preserves_the_legacy_leak_index() -> None:
    package = _package_for(leak_terms=None)

    assert package.knowledge_indexes.leak_term_to_knowledge == package.knowledge_indexes.term_to_knowledge


def test_recall_alias_is_not_a_leak_when_reviewed() -> None:
    package = _package_for(leak_terms=())

    assert package.knowledge_indexes.alias_to_knowledge["sealed letter"]
    result = RuntimeEngine(
        RuntimeState.bootstrap(package),
        lambda _: {"segments": [{"kind": "narration", "text": "Kristin reads the sealed letter."}]},
    ).turn("Search the desk.")

    assert result.segments[0].text == "Kristin reads the sealed letter."


def test_explicit_leak_term_rejects_before_its_item_is_earned() -> None:
    package = _package_for(leak_terms=("silver tunnel password",))

    state, before, error = _run(package, "Kristin finds the silver tunnel password.")

    assert error.code == "narration_known_term_leak"
    assert state.snapshot() == before


def test_must_convey_synonym_is_not_a_guard_for_reviewed_item() -> None:
    package = _package_for(leak_terms=("silver tunnel password",))

    result = RuntimeEngine(
        RuntimeState.bootstrap(package),
        lambda _: {"segments": [{"kind": "narration", "text": "Kristin mentions a harmless delivery phrase."}]},
    ).turn("Search the desk.")

    assert result.segments[0].text == "Kristin mentions a harmless delivery phrase."


def test_empty_review_does_not_remove_another_items_shared_leak_owner() -> None:
    first, second = PACKAGE.knowledge.knowledge[:2]
    first = first.model_copy(update={"aliases": ("shared silver phrase",), "leak_terms": ()})
    second = second.model_copy(update={"aliases": ("shared silver phrase",), "leak_terms": None})
    catalog = PACKAGE.knowledge.model_copy(update={"knowledge": (first, second) + PACKAGE.knowledge.knowledge[2:]})
    indexes = _compile_knowledge_indexes(catalog, PACKAGE.world)

    assert set(indexes.term_to_knowledge["shared silver phrase"]) == {first.id, second.id}
    assert set(indexes.leak_term_to_knowledge["shared silver phrase"]) == {second.id}


def test_empty_review_does_not_bypass_protected_or_entity_checks() -> None:
    package = _package_for(leak_terms=())

    _, _, protected_error = _run(package, "Brandon's history is finally clear.")
    _, _, entity_error = _run(package, "Brandon waits beside the door.")

    assert protected_error.code in {"protected_narration_leak", "narration_known_term_leak"}
    assert entity_error.code == "narration_known_term_leak"


def test_loader_and_runtime_use_the_same_reviewed_vocabulary() -> None:
    package = load_story_package(Path("data/stories/continuity-initiative"))
    reply = package.knowledge_indexes.by_id["k_sl_2b_c_r3"]

    assert any("maintenance line" in group for group in reply.action_evidence)
    assert "maintenance line" not in package.knowledge_indexes.leak_term_to_knowledge


def _scene_state(scene_id: str) -> RuntimeState:
    scene = next(scene for scene in PACKAGE.scenes if scene.metadata.scene_id == scene_id)
    state = RuntimeState.bootstrap(PACKAGE)
    state.current_scene_id = scene_id
    state.phase = scene.metadata.freytag_phase
    state._assert_scene_entry_fact(scene_id)
    return state


def _narrate(scene_id: str, text: str, player_input: str):
    return RuntimeEngine(
        _scene_state(scene_id),
        lambda _: {"segments": [{"kind": "narration", "text": text}], "selected_knowledge_ids": []},
    ).turn(player_input)


def test_neutral_negotiation_is_not_a_leak_in_2c_before_commitment() -> None:
    state = _scene_state("2C")
    assert not state.facts.matching("evidence_ready_to_transmit")
    assert not state.facts.matching("combined_broadcast_rescue_plan_known")
    assert not state.facts.matching("rebecca_office_required_for_broadcast")

    result = RuntimeEngine(
        state,
        lambda _: {
            "segments": [{"kind": "narration", "text": "Kristin weighs Rebecca's offer."}],
            "selected_knowledge_ids": [],
        },
    ).turn("Ask Rebecca what she is offering.")

    assert result.segments[0].text == "Kristin weighs Rebecca's offer."


def test_neutral_negotiation_is_not_a_leak_outside_2c() -> None:
    result = _narrate(
        "1A",
        "Kristin weighs the next move.",
        "Consider the next move.",
    )

    assert result.segments[0].text == "Kristin weighs the next move."


def test_2c_route_and_office_disclosures_still_reject_before_their_reveals() -> None:
    for text in (
        "Rebecca's secured office can broadcast the evidence.",
        "Michelle's maintenance access route leads to her holding block.",
    ):
        with pytest.raises(ProposalValidationError) as caught:
            _narrate(
                "2C",
                text,
                "Assess the cost of transmitting our evidence right now to the people still held here.",
            )

        assert caught.value.code == "narration_known_term_leak"


def test_2c_commitment_terms_do_not_reintroduce_old_reviewed_owners() -> None:
    index = PACKAGE.knowledge_indexes.leak_term_to_knowledge

    for term in ("broadcast proof", "send the evidence", "risk the captives", "evidence ready to transmit"):
        assert not any(owner.startswith("k_sl_2c_c_") for owner in index.get(term, ()))
    assert not any(owner.startswith("k_sl_2c_c_") for owner in index.get("transmit the evidence", ()))
