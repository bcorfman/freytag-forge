from pathlib import Path

import pytest

from storygame.runtime.context import ContextFact, SceneContextBuilder
from storygame.runtime.facts import Fact
from storygame.runtime.state import RuntimeState
from storygame.story_package import load_story_package


def _state() -> RuntimeState:
    return RuntimeState.bootstrap(load_story_package(Path("data/stories/continuity-initiative")))


def test_default_context_is_scene_local_and_excludes_protected_knowledge() -> None:
    state = _state()
    state.facts.assert_fact(Fact(predicate="located_at", subject="gabriel", object="los_angeles_park"))
    state.facts.assert_fact(Fact(predicate="knows", subject="gabriel", object="janus_selection_system"))

    context = SceneContextBuilder().build(state, "I search the kitchen.")

    assert {entity.id for entity in context.entities} == {"jeremiah", "sarah", "memory_card", "sarah_phone"}
    assert context.facts == ()
    assert "gabriel" not in context.prompt()
    assert "janus_selection_system" not in context.prompt()


def test_unambiguous_reference_adds_public_entity_and_history_only() -> None:
    state = _state()
    state.facts.assert_fact(Fact(predicate="located_at", subject="gabriel", object="los_angeles_park"))
    state.facts.assert_fact(Fact(predicate="knows", subject="gabriel", object="janus_selection_system"))

    context = SceneContextBuilder().build(state, "Could Gabriel Dexter have left a message?")

    assert context.reference_resolution.matched_ids == ("gabriel",)
    assert "gabriel" in {entity.id for entity in context.entities}
    assert context.referenced_history == (
        ContextFact(predicate="located_at", subject="gabriel", object="los_angeles_park"),
    )
    assert "janus_selection_system" not in context.prompt()


def test_owned_entity_is_local_without_exposing_private_facts() -> None:
    state = _state()
    state.facts.assert_fact(Fact(predicate="custody", subject="jeremiah", object="transit_card"))

    context = SceneContextBuilder().build(state, "I check my pockets.")

    assert "transit_card" in {entity.id for entity in context.entities}
    assert ContextFact(predicate="custody", subject="jeremiah", object="transit_card") in context.facts


def test_ambiguous_reference_does_not_add_private_or_entity_context() -> None:
    state = _state()
    # Two public names can be supplied by a package; use names that collide through aliases in a copied model.
    world = state.package.world.model_copy(
        update={"npcs": tuple(item.model_copy(update={"aliases": ("contact",)}) for item in state.package.world.npcs)}
    )
    state.package = state.package.model_copy(update={"world": world})

    context = SceneContextBuilder().build(state, "I call the contact.")

    assert context.reference_resolution.ambiguous_names == ("contact",)
    assert context.reference_resolution.matched_ids == ()
    assert "jeremiah" in {entity.id for entity in context.entities}
    assert "gabriel" not in {entity.id for entity in context.entities}


def test_active_storylet_is_scene_bound_and_prompt_declares_bounded_schema() -> None:
    state = _state()
    builder = SceneContextBuilder()

    context = builder.build(state, "I look under the drawer.", active_storylet_ids=("SL-1A-B",))

    assert context.active_storylets[0].id == "SL-1A-B"
    realization = context.active_storylets[0].realizations[0]
    assert realization.id == "SL-1A-B-R1"
    operations = [
        (operation.operation, operation.fact.predicate, operation.fact.value) for operation in realization.operations
    ]
    assert operations == [
        ("assert", "continuity_initiative_known", "true"),
        ("assert", "sarah_abduction_suspicion", "true"),
        ("assert", "sarah_lead_actionable", "true"),
    ]
    assert '"response_schema"' in context.prompt()
    with pytest.raises(ValueError, match="current scene"):
        builder.build(state, "I wait.", active_storylet_ids=("SL-1B-A",))
