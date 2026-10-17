from pathlib import Path

import pytest

from storygame.runtime.engine import RuntimeEngine
from storygame.runtime.facts import Fact
from storygame.runtime.state import RuntimeState
from storygame.runtime.validation import ProposalValidationError
from storygame.story_package.loader import (
    StoryPackageError,
    _compile_knowledge_indexes,
    _validate_disclosure_guards,
    load_story_package,
)
from storygame.story_package.models import DisclosureGuard

PACKAGE = load_story_package(Path("data/stories/continuity-initiative"))


def _state(package=PACKAGE, scene_id="1A"):
    scene = next(scene for scene in package.scenes if scene.metadata.scene_id == scene_id)
    return RuntimeState(package=package, current_scene_id=scene_id, phase=scene.metadata.freytag_phase)


def _narrate(state, text):
    return RuntimeEngine(
        state,
        lambda _input: {"segments": [{"kind": "narration", "text": text}]},
    ).turn("Search the room for evidence.")


def _with_item(package, item):
    world = package.world.model_copy(
        update={"items": tuple(item if current.id == item.id else current for current in package.world.items)}
    )
    return package.model_copy(
        update={"world": world, "knowledge_indexes": _compile_knowledge_indexes(package.knowledge, world)}
    )


def _with_guard(package, guard):
    world = package.world.model_copy(update={"disclosure_guards": (guard,)})
    return package.model_copy(
        update={"world": world, "knowledge_indexes": _compile_knowledge_indexes(package.knowledge, world)}
    )


def _without_bench_knowledge_term(package):
    knowledge = tuple(
        item.model_copy(
            update={
                "entity_ids": tuple(entity_id for entity_id in item.entity_ids if entity_id != "park_bench"),
                "must_convey": tuple(
                    tuple(term for term in group if term not in {"bench in the park", "park bench"})
                    for group in item.must_convey
                ),
            }
        )
        if item.id == "k_sl_1a_b_r1"
        else item
        for item in package.knowledge.knowledge
    )
    catalog = package.knowledge.model_copy(update={"knowledge": knowledge})
    return package.model_copy(
        update={"knowledge": catalog, "knowledge_indexes": _compile_knowledge_indexes(catalog, package.world)}
    )


def test_public_entity_is_not_a_global_narration_guard():
    bench = next(item for item in PACKAGE.world.items if item.id == "park_bench")
    package = _without_bench_knowledge_term(PACKAGE)
    legacy = _state(_with_item(package, bench.model_copy(update={"disclosure": "legacy"})))
    with pytest.raises(ProposalValidationError, match="narration mentions an unavailable entity"):
        _narrate(legacy, "The park bench is dusty.")

    public = _state(_with_item(package, bench.model_copy(update={"disclosure": "public"})))
    _narrate(public, "The park bench is dusty.")


def test_public_entity_does_not_change_unrelated_verdicts():
    bench = next(item for item in PACKAGE.world.items if item.id == "park_bench")
    public_package = _with_item(PACKAGE, bench.model_copy(update={"disclosure": "public"}))
    sentences = (
        ("1A", "The phone lies beside the laptop."),
        ("1A", "Search the drawer for a hidden message."),
        ("1B", "The gate blocks the path."),
        ("1B", "Examine the storm drain."),
        ("1C", "The terminal hums in the empty room."),
        ("2A", "Follow the truck toward the facility."),
        ("2B", "Inspect the security corridor."),
        ("3A", "Read the medical records."),
    )
    for scene_id, sentence in sentences:
        outcomes = []
        for package in (PACKAGE, public_package):
            try:
                _narrate(_state(package, scene_id), sentence)
            except ProposalValidationError as exc:
                outcomes.append((False, exc.code))
            else:
                outcomes.append((True, None))
        assert outcomes[0] == outcomes[1], (scene_id, sentence)


def test_fact_guard_is_global_and_unlocks_after_assertion():
    guard = DisclosureGuard(id="bench_guard", terms=("bench",), unlock_fact="facility_proof")
    package = _with_guard(PACKAGE, guard)
    with pytest.raises(ProposalValidationError) as exc_info:
        _narrate(_state(package, "1B"), "The bench is dusty.")
    assert exc_info.value.code == "disclosure_guard_leak"

    state = _state(package, "1B")
    state.facts.assert_fact(Fact(predicate="facility_proof", subject="story", value="true"))
    _narrate(state, "The bench is dusty.")


def test_shared_guard_term_requires_every_guard_to_unlock():
    package = PACKAGE.model_copy(
        update={
            "world": PACKAGE.world.model_copy(
                update={
                    "disclosure_guards": (
                        DisclosureGuard(id="bench_first", terms=("bench",), unlock_fact="facility_proof"),
                        DisclosureGuard(id="bench_second", terms=("bench",), unlock_fact="false_identities_ready"),
                    )
                }
            )
        }
    )
    package = package.model_copy(
        update={"knowledge_indexes": _compile_knowledge_indexes(package.knowledge, package.world)}
    )
    state = _state(package, "1B")
    state.facts.assert_fact(Fact(predicate="facility_proof", subject="story", value="true"))
    with pytest.raises(ProposalValidationError) as exc_info:
        _narrate(state, "The bench is dusty.")
    assert exc_info.value.code == "disclosure_guard_leak"

    state.facts.assert_fact(Fact(predicate="false_identities_ready", subject="story", value="true"))
    _narrate(state, "The bench is dusty.")


def test_knowledge_guard_unlocks_when_knowledge_is_earned():
    guard = DisclosureGuard(id="gate_guard", terms=("service gate",), unlock_knowledge_id="k_sl_1b_a_r1")
    package = _with_guard(PACKAGE, guard)
    state = _state(package, "1B")
    with pytest.raises(ProposalValidationError) as exc_info:
        _narrate(state, "The service gate is dusty.")
    assert exc_info.value.code == "disclosure_guard_leak"

    state.facts.assert_fact(Fact(predicate="transport_route_identified", subject="story", value="true"))
    _narrate(state, "The service gate is dusty.")


def test_guard_handoff_text_is_exempted():
    guard = DisclosureGuard(id="gate_guard", terms=("service gate",), unlock_fact="facility_proof")
    package = _with_guard(PACKAGE, guard)
    state = _state(package, "1B")
    state.staged_handoff_fact_ids = ("park_pursuit_resolved",)
    _narrate(state, "The service gate is dusty.")


@pytest.mark.parametrize(
    ("guard", "message"),
    [
        (DisclosureGuard(id="bad", terms=("bench",), unlock_fact="missing"), "bad"),
        (DisclosureGuard(id="bad", terms=("bench",), unlock_knowledge_id="missing"), "bad"),
    ],
)
def test_guard_validation_names_guard_id(guard, message):
    with pytest.raises(StoryPackageError, match=message):
        _validate_disclosure_guards(_with_guard(PACKAGE, guard))


def test_public_item_restrictions_name_the_entity():
    hidden = next(item for item in PACKAGE.world.items if item.id == "memory_card")
    package = _with_item(PACKAGE, hidden.model_copy(update={"disclosure": "public"}))
    with pytest.raises(StoryPackageError, match="memory_card"):
        _validate_disclosure_guards(package)


@pytest.mark.parametrize("text", ("card", "the card", "a card", "memory card", "hidden card", "Michelle's card"))
def test_memory_card_words_are_guarded_before_recovery(text):
    with pytest.raises(ProposalValidationError, match="narration"):
        _narrate(_state(), f"Kristin notices {text}.")


def test_memory_card_word_guard_allows_card_after_recovery():
    state = _state()
    state.facts.assert_fact(Fact(predicate="memory_card_recovered", subject="story", value="true"))

    _narrate(state, "Kristin notices the card.")
    _narrate(state, "Kristin notices card.")


def test_memory_card_word_guard_does_not_match_discard():
    _narrate(_state(), "Kristin notices the discard pile.")


def test_memory_card_word_guard_allows_transit_card_in_scene_1b_after_recovery():
    state = _state(scene_id="1B")
    state.facts.assert_fact(Fact(predicate="memory_card_recovered", subject="story", value="true"))

    _narrate(state, "Kristin examines the transit card.")
    _narrate(state, "Kristin examines the card.")
