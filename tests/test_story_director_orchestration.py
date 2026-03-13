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


class _StubReplan:
    def run(self, state, disruption):  # noqa: ANN001
        return {
            "new_active_goal": "Contain the fallout and evade immediate arrest.",
            "note": "The story shifts: your previous move forces a new objective.",
        }


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


def test_story_director_uses_swappable_replan_component():
    state = build_default_state(seed=8)
    state.player.flags["story_replan_required"] = True
    state.world_package["story_replan_context"] = {"impact_class": "critical"}
    director = StoryDirector(
        "mock",
        output_editor=_StubEditor(),
        story_architect=_StubArchitect(),
        character_designer=_StubCharacter(),
        plot_designer=_StubPlot(),
        narrator_opening=_StubNarrator(),
        story_replan=_StubReplan(),
    )

    event = director.replan_if_needed(state)
    assert event is not None
    assert event.type == "story_replan"
    assert "story shifts" in event.message_key.lower()
    assert state.active_goal == "Contain the fallout and evade immediate arrest."
    assert state.player.flags["story_replan_required"] is False
