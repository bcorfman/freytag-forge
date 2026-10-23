from pathlib import Path

from bench.core import advance_state_to_scene
from storygame.runtime.reference_resolution import resolve_references
from storygame.runtime.state import RuntimeState
from storygame.story_package.loader import load_story_package

PACKAGE = load_story_package(Path("data/stories/continuity-initiative"))


def _state(scene_id: str) -> RuntimeState:
    state = RuntimeState.bootstrap(PACKAGE)
    advance_state_to_scene(PACKAGE, state, scene_id)
    return state


def test_unique_scoped_alias_is_recorded_without_rewriting_the_command() -> None:
    result = resolve_references(_state("1A"), "Inspect the chair.")

    assert result.outcome == "resolved"
    assert result.command == "Inspect the chair."
    assert result.resolutions == (("chair", "workstation_chair"),)


def test_scoped_alias_counts_but_plain_alias_does_not() -> None:
    assert resolve_references(_state("1A"), "Inspect the chair.").resolutions
    plain_alias = resolve_references(_state("1A"), "Talk to Shelly.")
    assert plain_alias.outcome == "passthrough"
    assert plain_alias.command == "Talk to Shelly."


def test_answers_match_full_name_distinguishing_word_and_ordinal() -> None:
    state = _state("2B")
    command = "Read the terminal."

    full_name = resolve_references(state, "medical terminal", clarifies=command)
    distinguishing = resolve_references(state, "the archive one", clarifies=command)
    ordinal = resolve_references(state, "second", clarifies=command)

    assert full_name.command == "Read the medical terminal."
    assert distinguishing.command == "Read the archive terminals."
    assert ordinal.command == "Read the medical terminal."
    assert all(result.outcome == "answered" for result in (full_name, distinguishing, ordinal))


def test_unrelated_answer_drops_question_and_runs_fresh_command() -> None:
    result = resolve_references(_state("2B"), "Look around.", clarifies="Read the terminal.")

    assert result.outcome == "dropped"
    assert result.command == "Look around."
    assert result.question is None


def test_changed_scene_drops_client_held_question() -> None:
    state = _state("1A")

    result = resolve_references(state, "Look around.", clarifies="Read the terminal.")

    assert result.outcome == "dropped"
    assert result.command == "Look around."
