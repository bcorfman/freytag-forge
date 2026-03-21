from __future__ import annotations

import pytest

from storygame.engine.state import Event
from storygame.engine.world import build_default_state
from storygame.llm.story_director import StoryDirector


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


class _StubRoomPresentation:
    def run(self, state, architect, cast, plan):  # noqa: ANN001
        return {
            room_id: {
                "long": f"Long {room.name}.",
                "short": f"Short {room.name}.",
            }
            for room_id, room in state.world.rooms.items()
        }


class _ObservedRoomPresentation:
    def __init__(self) -> None:
        self.called = False

    def run(self, state, architect, cast, plan):  # noqa: ANN001, ARG002
        self.called = True
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


class _PassThroughEditor:
    def review_opening(self, lines, active_goal):  # noqa: ANN001
        return list(lines)

    def review_turn(self, lines, active_goal, turn_index, debug=False):  # noqa: ANN001
        return list(lines)


def test_story_director_supports_swappable_agent_components():
    state = build_default_state(seed=7)
    director = StoryDirector(
        "mock",
        output_editor=_StubEditor(),
        story_bootstrap=_StubBootstrap(),
        story_bootstrap_critic=_StubBootstrapCritic(),
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


def test_story_director_coheres_inconsistent_bootstrap_opening_before_editor() -> None:
    class _InconsistentBootstrap:
        def run(self, state):  # noqa: ANN001, ARG002
            return {
                "protagonist_name": "Detective Elias Wren",
                "protagonist_background": "A detective dragged back for one last case.",
                "assistant_name": "Daria Stone",
                "actionable_objective": "Question Daria Stone about her involvement and inspect the front steps.",
                "primary_goal": "Expose the conspiracy behind the killing.",
                "secondary_goals": ["Find the missing witness."],
                "expanded_outline": "Trace the ledger, expose the conspiracy, and corner the mastermind.",
                "story_beats": [
                    {"beat_id": "hook", "summary": "Survey the mansion approach.", "min_progress": 0.0},
                    {"beat_id": "midpoint", "summary": "Trace the ledger trail.", "min_progress": 0.5},
                    {"beat_id": "climax", "summary": "Corner the mastermind.", "min_progress": 0.85},
                ],
                "villains": [
                    {
                        "name": "Magistrate Voss",
                        "motive": "Protect the conspiracy.",
                        "means": "Control over evidence.",
                        "opportunity": "Access to the estate.",
                    }
                ],
                "timed_events": [],
                "clue_placements": [
                    {
                        "item_id": "ledger_page",
                        "room_id": "front_steps",
                        "clue_text": "The ledger page shows a missing payment.",
                        "hidden_reason": "Someone tried to keep it out of the official file.",
                    }
                ],
                "hidden_threads": ["The ledger page links the household to a payoff."],
                "reveal_schedule": [{"thread_index": 0, "min_progress": 0.55}],
                "contacts": [{"name": "Daria Stone", "role": "assistant", "trait": "observant"}],
                "opening_paragraphs": [
                    "Rain needles the stone as you reach the front steps.",
                    "Daria Stone, your assistant, keeps the ledger page tight in her hand.",
                    "The ledger page is wedged into the wet stones in front of the mansion.",
                    "You are here to question Daria Stone about her involvement before you go inside.",
                ],
            }

    state = build_default_state(seed=702)
    director = StoryDirector(
        "mock",
        output_editor=_PassThroughEditor(),
        story_bootstrap=_InconsistentBootstrap(),
        story_bootstrap_critic=_StubBootstrapCritic(),
        room_presentation=_StubRoomPresentation(),
    )

    opening = director.compose_opening(state)
    combined = "\n".join(opening).lower()

    assert "question daria stone about her involvement" not in combined
    assert "wedged into the wet stones" not in combined
    assert combined.count("ledger page") >= 1
    assert "assistant" in combined


def test_story_director_uses_swappable_replan_component():
    state = build_default_state(seed=8)
    state.player.flags["story_replan_required"] = True
    state.world_package["story_replan_context"] = {"impact_class": "critical"}
    director = StoryDirector(
        "mock",
        output_editor=_StubEditor(),
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
        story_bootstrap=_StubBootstrap(),
        story_bootstrap_critic=_StubBootstrapCritic(),
        room_presentation=_RaisingRoomPresentation(),
    )

    opening = director.compose_opening(state)
    assert opening == ["edited:P1", "edited:P2", "edited:P3"]
    room_cache = state.world_package.get("room_presentation_cache", {})
    assert set(room_cache.keys()) == set(state.world.rooms.keys())


def test_story_director_bootstrap_opening_still_populates_room_presentation_cache():
    state = build_default_state(seed=10)
    room_presentation = _ObservedRoomPresentation()

    director = StoryDirector(
        "mock",
        output_editor=_StubEditor(),
        story_bootstrap=_StubBootstrap(),
        story_bootstrap_critic=_StubBootstrapCritic(),
        room_presentation=room_presentation,
    )

    opening = director.compose_opening(state)

    assert opening == ["edited:P1", "edited:P2", "edited:P3"]
    assert room_presentation.called is True


def test_story_director_raises_when_bootstrap_agent_fails():
    state = build_default_state(seed=11)
    director = StoryDirector(
        "mock",
        output_editor=_StubEditor(),
        story_bootstrap=_RaisingBootstrap(),
        room_presentation=_StubRoomPresentation(),
    )

    with pytest.raises(RuntimeError, match="BOOTSTRAP_TIMEOUT"):
        director.compose_opening(state)


def test_story_director_ignores_legacy_opening_components_when_bootstrap_path_is_present() -> None:
    state = build_default_state(seed=11)
    director = StoryDirector(
        "mock",
        output_editor=_StubEditor(),
        story_bootstrap=_StubBootstrap(),
        story_bootstrap_critic=_StubBootstrapCritic(),
        story_architect=object(),
        character_designer=object(),
        plot_designer=object(),
        narrator_opening=object(),
        room_presentation=_StubRoomPresentation(),
    )

    opening = director.compose_opening(state)
    assert opening == ["edited:P1", "edited:P2", "edited:P3"]


def test_story_director_raises_when_bootstrap_critic_rejects() -> None:
    class _RejectingBootstrapCritic:
        def run(self, state, bootstrap_bundle):  # noqa: ANN001, ARG002
            return {"verdict": "rejected", "continuity_summary": "opening conflict", "issues": ["bad role"]}

    state = build_default_state(seed=11)
    director = StoryDirector(
        "mock",
        output_editor=_StubEditor(),
        story_bootstrap=_StubBootstrap(),
        story_bootstrap_critic=_RejectingBootstrapCritic(),
        room_presentation=_StubRoomPresentation(),
    )

    with pytest.raises(RuntimeError, match="Story bootstrap critique rejected plan"):
        director.compose_opening(state)


def test_story_director_raises_when_bootstrap_agent_returns_empty_opening() -> None:
    class _EmptyOpeningBootstrap:
        def run(self, state):  # noqa: ANN001, ARG002
            payload = dict(_StubBootstrap().run(state))
            payload["opening_paragraphs"] = []
            return payload

    state = build_default_state(seed=12)
    director = StoryDirector(
        "mock",
        output_editor=_StubEditor(),
        story_bootstrap=_EmptyOpeningBootstrap(),
        story_bootstrap_critic=_StubBootstrapCritic(),
        room_presentation=_StubRoomPresentation(),
    )

    with pytest.raises(RuntimeError, match="empty opening_paragraphs"):
        director.compose_opening(state)

