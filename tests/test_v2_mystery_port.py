"""The V2 mystery fixture must remain a projection of the authored V1 case."""

from storygame.authoring.compiler import load_compiled_story_fixture
from storygame.runtime.context import RuntimeContextBuilder
from storygame.runtime.state import bootstrap_runtime_state


def test_v2_mystery_fixture_preserves_the_authored_vale_mansion_opening() -> None:
    story = load_compiled_story_fixture("mystery")
    state = bootstrap_runtime_state(story)
    context = RuntimeContextBuilder().build(state, "Review the case file.").payload

    assert story.id == "vale_mansion_case"
    assert story.title == "The Vale Mansion Case"
    assert story.initial_world_state["location"] == "front_steps"
    assert {character.name for character in story.characters} >= {
        "Detective Elias Wren", "Daria Stone", "Emma Vale", "The Groundskeeper"
    }
    assert state.world.items["case_file"]["holder"] == "npc:daria_stone"
    assert "11:40 p.m." in state.world.items["case_file"]["description"]
    assert context["world"]["attributes"]["public_briefing"]["victim"] == "Emma Vale"
    assert "missing ledger payment" in context["world"]["attributes"]["public_briefing"]["strongest_lead"]


def test_v2_mystery_fixture_preserves_the_authored_case_progression_and_protection() -> None:
    story = load_compiled_story_fixture("mystery")

    assert [beat.id for beat in story.beats] == [
        "review_case_file", "trace_ledger_payment", "test_the_accusation", "expose_buried_truth", "close_vale_case"
    ]
    assert story.beats[-1].answers_central_question
    assert story.protected_revelations[0].reveal_after == ("buried_truth_exposed",)
