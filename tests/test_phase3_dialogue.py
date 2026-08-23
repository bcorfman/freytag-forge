from __future__ import annotations

from pathlib import Path

import pytest

from storygame.authoring.compiler import load_compiled_story_fixture
from storygame.runtime.contracts import DialogueProposal, RuntimeFailure, TurnResult
from storygame.runtime.engine import RuntimeEngine
from storygame.runtime.facts import Fact
from storygame.runtime.state import bootstrap_runtime_state
from storygame.runtime.validation import validate_and_commit


def _state():
    return bootstrap_runtime_state(load_compiled_story_fixture("mystery", root=Path("data/compiled_stories/v1")))


def _dialogue(**overrides: object) -> DialogueProposal:
    values: dict[str, object] = {
        "target_id": "daria_stone",
        "speaker_id": "daria_stone",
        "permitted_context": ("arrival_briefing",),
        "dialogue": "The front steps are watched. Ask me what you need.",
        "effects": (
            {
                "kind": "add",
                "path": "facts",
                "value": {"predicate": "flag", "subject": "world", "object": "asked_daria"},
            },
        ),
    }
    values.update(overrides)
    return DialogueProposal(**values)


def test_dialogue_commits_bounded_effects_before_rendering() -> None:
    state = _state()
    state.facts.assert_fact(Fact(predicate="knows", subject="daria_stone", object="arrival_briefing"))

    updated = validate_and_commit(
        state,
        TurnResult(narration="Daria answers.", dialogue=_dialogue()),
        player_input="Ask Daria what she knows.",
    )

    assert "asked_daria" in updated.world.flags
    assert state.world.flags != updated.world.flags


@pytest.mark.parametrize(
    ("change", "code"),
    [
        ({"target_id": "groundskeeper"}, "UNAVAILABLE_SPEAKER"),
        ({"speaker_id": "narrator"}, "WRONG_SPEAKER"),
        ({"permitted_context": ("protected_fact",)}, "SPEAKER_LACKS_KNOWLEDGE"),
        ({"dialogue": "Ask Daria what she knows."}, "DIALOGUE_PROMPT_PARROTING"),
        ({"dialogue": "Daria says that you should leave."}, "DIALOGUE_NARRATOR_SUBSTITUTION"),
    ],
)
def test_dialogue_validation_fails_closed(change: dict[str, object], code: str) -> None:
    state = _state()
    state.facts.assert_fact(Fact(predicate="knows", subject="daria_stone", object="arrival_briefing"))
    with pytest.raises(RuntimeFailure) as error:
        validate_and_commit(
            state,
            TurnResult(narration="The answer is rejected.", dialogue=_dialogue(**change)),
            player_input="Ask Daria what she knows.",
        )
    assert error.value.code == code


def test_engine_returns_dialogue_only_after_effects_commit() -> None:
    state = _state()
    state.facts.assert_fact(Fact(predicate="knows", subject="daria_stone", object="arrival_briefing"))

    class Model:
        def play_turn(self, context: object, *, json_object: bool) -> object:
            return {
                "narration": "Daria answers.",
                "dialogue": _dialogue().model_dump(mode="json"),
            }

    engine = RuntimeEngine(state, Model())
    response = engine.turn("Ask Daria what she knows.")
    assert response.ok
    assert response.narration == "The front steps are watched. Ask me what you need."
    assert "asked_daria" in engine.state.world.flags


def test_unambiguous_take_affordance_uses_the_shared_commit_contract() -> None:
    state = _state()
    state.world.items["case_file"]["affordances"] = ["take"]

    class Model:
        def play_turn(self, context: object, *, json_object: bool) -> object:
            return {"narration": "Taken."}

    engine = RuntimeEngine(
        state,
        Model(),
    )
    response = engine.turn("take the case file")
    assert response.ok
    assert engine.state.world.items["case_file"]["holder"] == "player"
    assert response.ok
