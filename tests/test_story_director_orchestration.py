from __future__ import annotations

import logging
import threading

from storygame.engine.state import Event
from storygame.engine.world import build_default_state
from storygame.llm.story_director import StoryDirector


class _StubArchitect:
    def run(self, state):  # noqa: ANN001
        return {"protagonist_name": "Stub Protagonist"}


class _StubBootstrap:
    def run(self, state):  # noqa: ANN001
        return {
            "protagonist_name": "Stub Protagonist",
            "protagonist_background": "A detective on the edge of failure.",
            "assistant_name": "Stub Ally",
            "actionable_objective": "Open the case file first.",
            "primary_goal": "Expose the larger conspiracy behind the killings.",
            "secondary_goals": ["Find the witness who saw the exchange."],
            "hidden_threads": ["A magistrate paid to bury the first murder."],
            "reveal_schedule": [{"thread_index": 0, "min_progress": 0.55}],
            "contacts": [{"name": "Stub Ally", "role": "assistant", "trait": "sharp"}],
            "opening_paragraphs": ["P1", "P2", "P3"],
        }


class _StubCharacter:
    def run(self, state, architect):  # noqa: ANN001
        return {"contacts": [{"name": "Stub Ally", "role": "assistant", "trait": "sharp"}]}


class _StubPlot:
    def run(self, state, architect, cast):  # noqa: ANN001
        return {"assistant_name": "Stub Ally", "actionable_objective": "Open the case file first."}


class _BadPlot:
    def run(self, state, architect, cast):  # noqa: ANN001, ARG002
        return {
            "assistant_name": "Daria Stone",
            "actionable_objective": (
                "Create a character profile for the tech-savvy detective, including their background, "
                "skills, and motivations, to effectively investigate the string of grisly murders."
            ),
        }


class _StubNarrator:
    def run(self, state, architect, cast, plan):  # noqa: ANN001
        return [
            "P1",
            "P2",
            "P3",
        ]


class _StubRoomPresentation:
    def run(self, state, architect, cast, plan):  # noqa: ANN001
        return {
            room_id: {
                "long": f"Long {room.name}.",
                "short": f"Short {room.name}.",
            }
            for room_id, room in state.world.rooms.items()
        }


class _ParallelAwareNarrator:
    def __init__(self, own_started: threading.Event, other_started: threading.Event) -> None:
        self._own_started = own_started
        self._other_started = other_started
        self.saw_other = False

    def run(self, state, architect, cast, plan):  # noqa: ANN001, ARG002
        self._own_started.set()
        self.saw_other = self._other_started.wait(timeout=0.2)
        return ["P1", "P2", "P3"]


class _ParallelAwareRoomPresentation:
    def __init__(self, own_started: threading.Event, other_started: threading.Event) -> None:
        self._own_started = own_started
        self._other_started = other_started
        self.saw_other = False

    def run(self, state, architect, cast, plan):  # noqa: ANN001, ARG002
        self._own_started.set()
        self.saw_other = self._other_started.wait(timeout=0.2)
        return {
            room_id: {
                "long": f"Long {room.name}.",
                "short": f"Short {room.name}.",
            }
            for room_id, room in state.world.rooms.items()
        }


class _RaisingRoomPresentation:
    def run(self, state, architect, cast, plan):  # noqa: ANN001, ARG002
        raise RuntimeError("boom")


class _RaisingNarrator:
    def run(self, state, architect, cast, plan):  # noqa: ANN001, ARG002
        raise RuntimeError("NarratorOpening agent returned non-JSON content.")


class _RaisingArchitect:
    def run(self, state):  # noqa: ANN001, ARG002
        raise RuntimeError("OPENAI_API_KEY is required for story-agent execution.")


class _RaisingBootstrap:
    def run(self, state):  # noqa: ANN001, ARG002
        raise RuntimeError("BOOTSTRAP_TIMEOUT")


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
        room_presentation=_StubRoomPresentation(),
    )

    opening = director.compose_opening(state)
    assert opening == ["edited:P1", "edited:P2", "edited:P3"]
    room_cache = state.world_package.get("room_presentation_cache", {})
    assert room_cache
    assert all("long" in room_cache[room_id] and "short" in room_cache[room_id] for room_id in state.world.rooms)

    reviewed_turn = director.review_turn(
        state,
        ["Room block", "Some event"],
        [Event(type="story_event", message_key="Reminder")],
    )
    assert reviewed_turn[0].startswith("turn:")


def test_story_director_prefers_single_bootstrap_agent_and_persists_bundle_outputs():
    state = build_default_state(seed=701)
    state.world_package["story_plan"] = {
        "protagonist_name": "Seeded Name",
        "setup_paragraphs": ("Seeded opening.",),
        "hidden_threads": (),
        "reveal_schedule": (),
    }
    state.world_package["goals"] = {"setup": "Seeded setup.", "primary": "Seeded primary.", "secondary": ()}

    director = StoryDirector(
        "mock",
        output_editor=_StubEditor(),
        story_bootstrap=_StubBootstrap(),
        room_presentation=_StubRoomPresentation(),
    )

    opening = director.compose_opening(state)

    assert opening == ["edited:P1", "edited:P2", "edited:P3"]
    assert state.active_goal == "Open the case file first."
    assert state.world_package["goals"]["setup"] == "Open the case file first."
    assert state.world_package["goals"]["primary"] == "Expose the larger conspiracy behind the killings."
    assert state.world_package["story_plan"]["protagonist_name"] == "Stub Protagonist"
    assert state.world_package["story_plan"]["setup_paragraphs"] == ("P1", "P2", "P3")
    assert state.world_package["llm_story_bundle"]["assistant_name"] == "Stub Ally"


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


def test_story_director_room_presentation_falls_back_when_agent_fails():
    state = build_default_state(seed=9)
    director = StoryDirector(
        "mock",
        output_editor=_StubEditor(),
        story_architect=_StubArchitect(),
        character_designer=_StubCharacter(),
        plot_designer=_StubPlot(),
        narrator_opening=_StubNarrator(),
        room_presentation=_RaisingRoomPresentation(),
    )

    opening = director.compose_opening(state)
    assert opening == ["edited:P1", "edited:P2", "edited:P3"]
    room_cache = state.world_package.get("room_presentation_cache", {})
    assert set(room_cache.keys()) == set(state.world.rooms.keys())


def test_story_director_parallelizes_narrator_and_room_presentation():
    state = build_default_state(seed=10)
    narrator_started = threading.Event()
    room_started = threading.Event()
    narrator = _ParallelAwareNarrator(narrator_started, room_started)
    room_presentation = _ParallelAwareRoomPresentation(room_started, narrator_started)

    director = StoryDirector(
        "mock",
        output_editor=_StubEditor(),
        story_architect=_StubArchitect(),
        character_designer=_StubCharacter(),
        plot_designer=_StubPlot(),
        narrator_opening=narrator,
        room_presentation=room_presentation,
    )

    opening = director.compose_opening(state)

    assert opening == ["edited:P1", "edited:P2", "edited:P3"]
    assert narrator.saw_other is True
    assert room_presentation.saw_other is True


def test_story_director_opening_falls_back_when_narrator_agent_fails():
    state = build_default_state(seed=11)
    director = StoryDirector(
        "mock",
        output_editor=_StubEditor(),
        story_architect=_StubArchitect(),
        character_designer=_StubCharacter(),
        plot_designer=_StubPlot(),
        narrator_opening=_RaisingNarrator(),
        room_presentation=_StubRoomPresentation(),
    )

    opening = director.compose_opening(state)
    assert opening
    assert all(line.startswith("edited:") for line in opening)


def test_story_director_logs_when_opening_falls_back_after_narrator_failure(caplog):
    state = build_default_state(seed=11)
    director = StoryDirector(
        "mock",
        output_editor=_StubEditor(),
        story_architect=_StubArchitect(),
        character_designer=_StubCharacter(),
        plot_designer=_StubPlot(),
        narrator_opening=_RaisingNarrator(),
        room_presentation=_StubRoomPresentation(),
    )

    with caplog.at_level(logging.WARNING):
        opening = director.compose_opening(state)

    assert opening
    assert "Opening generation fell back after narrator-opening failure" in caplog.text
    assert "NarratorOpening agent returned non-JSON content." in caplog.text


def test_story_director_narrator_failure_prefers_seeded_story_plan_over_bad_planner_fields():
    state = build_default_state(seed=11)
    director = StoryDirector(
        "mock",
        output_editor=_StubEditor(),
        story_architect=_StubArchitect(),
        character_designer=_StubCharacter(),
        plot_designer=_BadPlot(),
        narrator_opening=_RaisingNarrator(),
        room_presentation=_StubRoomPresentation(),
    )

    opening = director.compose_opening(state)

    assert any("has kept a low profile for years" in line for line in opening)
    assert not any("Create a character profile" in line for line in opening)


def test_story_director_opening_falls_back_when_story_architect_agent_fails():
    state = build_default_state(seed=12)
    director = StoryDirector(
        "mock",
        output_editor=_StubEditor(),
        story_architect=_RaisingArchitect(),
        character_designer=_StubCharacter(),
        plot_designer=_StubPlot(),
        narrator_opening=_StubNarrator(),
        room_presentation=_StubRoomPresentation(),
    )

    opening = director.compose_opening(state)
    assert opening
    assert all(line.startswith("edited:") for line in opening)
    assert any("has kept a low profile for years" in line for line in opening)


def test_story_director_logs_when_opening_falls_back_after_planning_failure(caplog):
    state = build_default_state(seed=12)
    director = StoryDirector(
        "mock",
        output_editor=_StubEditor(),
        story_architect=_RaisingArchitect(),
        character_designer=_StubCharacter(),
        plot_designer=_StubPlot(),
        narrator_opening=_StubNarrator(),
        room_presentation=_StubRoomPresentation(),
    )

    with caplog.at_level(logging.WARNING):
        opening = director.compose_opening(state)

    assert opening
    assert "Opening generation fell back after planning failure" in caplog.text
    assert "OPENAI_API_KEY is required for story-agent execution." in caplog.text
