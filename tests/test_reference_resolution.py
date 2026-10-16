from pathlib import Path

from bench.core import advance_state_to_scene
from storygame.runtime.reference_resolution import _Thing, clarification_text, resolve_references
from storygame.runtime.state import RuntimeState
from storygame.story_package.loader import load_story_package

PACKAGE = load_story_package(Path("data/stories/continuity-initiative"))


def _state(scene_id: str) -> RuntimeState:
    state = RuntimeState.bootstrap(PACKAGE)
    advance_state_to_scene(PACKAGE, state, scene_id)
    return state


def test_unique_scoped_alias_resolves_to_the_full_name() -> None:
    result = resolve_references(_state("1A"), "Inspect the chair.")

    assert result.outcome == "resolved"
    assert result.command == "Inspect the workstation chair."
    assert result.resolutions == (("chair", "workstation_chair"),)


def test_terminal_collision_asks_in_deterministic_order() -> None:
    result = resolve_references(_state("2B"), "Read the terminal.")

    assert result.outcome == "asked"
    assert result.question is not None
    assert result.question.options == (
        ("archive_terminals", "archive terminals"),
        ("medical_terminal", "medical terminal"),
    )
    assert clarification_text(result.question) == "Do you mean the archive terminals or the medical terminal?"


def test_full_name_precedence_and_negative_scope_cases() -> None:
    state = _state("2B")
    assert resolve_references(state, "Read the messages on the medical terminal.").question is None
    assert resolve_references(_state("1A"), "Read the terminal.").command == "Read the terminal."
    assert resolve_references(_state("2B"), "Read the archive terminal.").question is None


def test_scoped_alias_counts_but_plain_alias_does_not() -> None:
    assert resolve_references(_state("1A"), "Inspect the chair.").resolutions
    plain_alias = resolve_references(_state("1A"), "Talk to Shelly.")
    assert plain_alias.outcome == "passthrough"
    assert plain_alias.command == "Talk to Shelly."


def test_unrelated_bare_word_is_untouched() -> None:
    result = resolve_references(_state("2B"), "Wait by the window.")

    assert result.outcome == "passthrough"
    assert result.command == "Wait by the window."


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


def test_round_cap_leaves_a_second_ambiguous_noun_untouched(monkeypatch) -> None:
    state = _state("2B")
    monkeypatch.setattr(
        "storygame.runtime.reference_resolution._scene_things",
        lambda _state: (
            _Thing("archive_terminals", "archive terminals", ("terminal",)),
            _Thing("medical_terminal", "medical terminal", ("terminal",)),
            _Thing("archive_desk", "archive desk", ("desk",)),
            _Thing("medical_desk", "medical desk", ("desk",)),
            _Thing("archive_console", "archive console", ("console",)),
            _Thing("medical_console", "medical console", ("console",)),
        ),
    )
    original = "Read the terminal, then inspect the desk, then open the console."
    first = resolve_references(state, original)
    second = resolve_references(state, "medical", clarifies=original, clarification_round=0)
    capped = resolve_references(state, "archive", clarifies=second.command, clarification_round=1)

    assert first.outcome == "asked"
    assert second.outcome == "answered"
    assert second.question is not None
    assert capped.outcome == "capped"
    assert capped.question is None
    assert capped.command == "Read the medical terminal, then inspect the archive desk, then open the console."


def test_resolution_does_not_mutate_runtime_state() -> None:
    state = _state("2B")
    before = state.model_dump(mode="json", exclude={"package": True})

    resolve_references(state, "Read the terminal.")

    assert state.model_dump(mode="json", exclude={"package": True}) == before
