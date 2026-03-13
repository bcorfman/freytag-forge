from __future__ import annotations

from storygame.engine.state import Event
from storygame.engine.world import build_default_state
from storygame.llm.story_director import StoryDirector


class _StubArchitect:
    def run(self, state):  # noqa: ANN001
        return {"protagonist_name": "Stub Protagonist"}


class _StubCharacter:
    def run(self, state, architect):  # noqa: ANN001
        return {"contacts": [{"name": "Stub Ally", "role": "assistant", "trait": "sharp"}]}


class _StubPlot:
    def run(self, state, architect, cast):  # noqa: ANN001
        return {"assistant_name": "Stub Ally", "actionable_objective": "Open the case file first."}


class _StubNarrator:
    def run(self, state, architect, cast, plan):  # noqa: ANN001
        return [
            "P1",
            "P2",
            "P3",
        ]


class _StubEditor:
    def review_opening(self, lines, active_goal):  # noqa: ANN001
        return [f"edited:{line}" for line in lines]

    def review_turn(self, lines, active_goal, turn_index, debug=False):  # noqa: ANN001
        return [f"turn:{line}" for line in lines]


def test_story_director_supports_swappable_agent_components():
    state = build_default_state(seed=7)
    director = StoryDirector(
        "mock",
        output_editor=_StubEditor(),
        story_architect=_StubArchitect(),
        character_designer=_StubCharacter(),
        plot_designer=_StubPlot(),
        narrator_opening=_StubNarrator(),
    )

    opening = director.compose_opening(state)
    assert opening == ["edited:P1", "edited:P2", "edited:P3"]

    reviewed_turn = director.review_turn(
        state,
        ["Room block", "Some event"],
        [Event(type="story_event", message_key="Reminder")],
    )
    assert reviewed_turn[0].startswith("turn:")
