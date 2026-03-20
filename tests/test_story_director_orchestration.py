from __future__ import annotations

import threading

import pytest

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
            "assistant_name": "Daria Stone",
            "actionable_objective": "Open the case file first.",
            "primary_goal": "Expose the larger conspiracy behind the killings.",
            "secondary_goals": ["Find the witness who saw the exchange."],
            "expanded_outline": "Open with the case file, uncover the buried network, and force the mastermind into the open.",
            "story_beats": [
                {"beat_id": "hook", "summary": "Open the case file.", "min_progress": 0.0},
                {"beat_id": "midpoint", "summary": "Reveal the larger network.", "min_progress": 0.5},
                {"beat_id": "climax", "summary": "Force the mastermind into the open.", "min_progress": 0.85},
            ],
            "villains": [
                {
                    "name": "Magistrate Voss",
                    "motive": "Protect the network.",
                    "means": "Control over evidence.",
                    "opportunity": "Constant access to the case.",
                }
            ],
            "timed_events": [
                {
                    "event_id": "warning",
                    "summary": "A warning reaches the foyer.",
                    "min_turn": 2,
                    "location": "foyer",
                    "participants": ["Daria Stone"],
                }
            ],
            "clue_placements": [
                {
                    "item_id": "route_key",
                    "room_id": "watch_tower",
                    "clue_text": "The route key marks the escape route.",
                    "hidden_reason": "It was hidden in the tower masonry.",
                }
            ],
            "hidden_threads": ["A magistrate paid to bury the first murder."],
            "reveal_schedule": [{"thread_index": 0, "min_progress": 0.55}],
            "contacts": [{"name": "Daria Stone", "role": "assistant", "trait": "sharp"}],
            "opening_paragraphs": ["P1", "P2", "P3"],
        }


class _StubBootstrapCritic:
    def run(self, state, bootstrap_bundle):  # noqa: ANN001, ARG002
        return {"verdict": "accepted", "continuity_summary": "Coherent plan.", "issues": []}


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
        story_bootstrap_critic=_StubBootstrapCritic(),
        room_presentation=_StubRoomPresentation(),
    )

    opening = director.compose_opening(state)

    assert opening == ["edited:P1", "edited:P2", "edited:P3"]
    assert state.active_goal == "Open the case file first."
    assert state.world_package["goals"]["setup"] == "Open the case file first."
    assert state.world_package["goals"]["primary"] == "Expose the larger conspiracy behind the killings."
    assert state.world_package["story_plan"]["protagonist_name"] == "Stub Protagonist"
    assert state.world_package["story_plan"]["setup_paragraphs"] == ("P1", "P2", "P3")
    assert state.world_package["llm_story_bundle"]["assistant_name"] == "Daria Stone"
    assert state.world.npcs["daria_stone"].identity.startswith("your assistant")
    assert state.world_facts.holds("player_name", "Stub Protagonist")
    assert state.world_facts.holds("player_background", "A detective on the edge of failure.")
    assert state.world_facts.holds("npc_role", "Daria Stone", "assistant")
    assert state.world_facts.holds("story_hidden_thread", "A magistrate paid to bury the first murder.")
    assert state.world_facts.holds("story_reveal_schedule", "0", "0.55")
    assert state.world_facts.holds("planned_event_participant", "warning", "Daria Stone")


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


def test_story_director_light_replan_keeps_existing_goal() -> None:
    state = build_default_state(seed=81)
    prior_goal = state.active_goal
    state.player.flags["story_replan_required"] = True
    state.world_package["story_replan_context"] = {
        "impact_class": "high",
        "replan_scope": "light",
        "command": "threaten the desk clerk",
    }
    director = StoryDirector("mock", output_editor=_StubEditor())

    event = director.replan_if_needed(state)

    assert event is not None
    assert event.type == "story_replan"
    assert state.active_goal == prior_goal
    assert state.player.flags["story_replan_required"] is False
    assert state.world_package["story_replan_plan"]["replan_scope"] == "light"


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

    with pytest.raises(RuntimeError, match="NarratorOpening agent returned non-JSON content."):
        director.compose_opening(state)


def test_story_director_raises_when_narrator_agent_fails() -> None:
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

    with pytest.raises(RuntimeError, match="NarratorOpening agent returned non-JSON content."):
        director.compose_opening(state)


def test_story_director_narrator_failure_does_not_substitute_bad_planner_fields():
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

    with pytest.raises(RuntimeError, match="NarratorOpening agent returned non-JSON content."):
        director.compose_opening(state)


def test_story_director_raises_when_story_architect_agent_fails():
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

    with pytest.raises(RuntimeError, match="OPENAI_API_KEY is required for story-agent execution."):
        director.compose_opening(state)


def test_story_director_raises_when_planning_fails() -> None:
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

    with pytest.raises(RuntimeError, match="OPENAI_API_KEY is required for story-agent execution."):
        director.compose_opening(state)
