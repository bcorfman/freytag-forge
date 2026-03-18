from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
import logging

from storygame.engine.state import Event, GameState
from storygame.llm.output_editor import OutputEditor, build_output_editor
from storygame.llm.story_agents.agents import (
    CharacterDesignerAgent,
    DefaultCharacterDesignerAgent,
    DefaultNarratorOpeningAgent,
    DefaultPlotDesignerAgent,
    DefaultRoomPresentationAgent,
    DefaultStoryArchitectAgent,
    DefaultStoryReplanAgent,
    NarratorOpeningAgent,
    PlotDesignerAgent,
    RoomPresentationAgent,
    StoryArchitectAgent,
    StoryReplanAgent,
)

_LOGGER = logging.getLogger(__name__)


class StoryDirector:
    def __init__(
        self,
        mode: str,
        output_editor: OutputEditor | None = None,
        story_architect: StoryArchitectAgent | None = None,
        character_designer: CharacterDesignerAgent | None = None,
        plot_designer: PlotDesignerAgent | None = None,
        narrator_opening: NarratorOpeningAgent | None = None,
        room_presentation: RoomPresentationAgent | None = None,
        story_replan: StoryReplanAgent | None = None,
    ) -> None:
        self._output_editor = build_output_editor(mode) if output_editor is None else output_editor
        self._story_architect = DefaultStoryArchitectAgent(mode) if story_architect is None else story_architect
        self._character_designer = (
            DefaultCharacterDesignerAgent(mode) if character_designer is None else character_designer
        )
        self._plot_designer = DefaultPlotDesignerAgent(mode) if plot_designer is None else plot_designer
        self._narrator_opening = DefaultNarratorOpeningAgent(mode) if narrator_opening is None else narrator_opening
        self._room_presentation = (
            DefaultRoomPresentationAgent(mode) if room_presentation is None else room_presentation
        )
        self._story_replan = DefaultStoryReplanAgent(mode) if story_replan is None else story_replan

    def compose_opening(self, state: GameState) -> list[str]:
        architect: dict[str, object] = {}
        cast: dict[str, object] = {}
        plan: dict[str, object] = {}
        planning_failed = False
        planning_error = ""
        try:
            architect = self._story_architect.run(state)
            cast = self._character_designer.run(state, architect)
            plan = self._plot_designer.run(state, architect, cast)
        except RuntimeError as exc:
            planning_failed = True
            planning_error = str(exc)
            _LOGGER.warning("Opening generation fell back after planning failure: %s", planning_error)
        with ThreadPoolExecutor(max_workers=2) as executor:
            room_future = executor.submit(self._ensure_room_presentation_cache, state, architect, cast, plan)
            if planning_failed:
                opening = self._fallback_opening_lines(state, architect, cast, plan)
            else:
                opening_future = executor.submit(self._narrator_opening.run, state, architect, cast, plan)
                try:
                    opening = opening_future.result()
                except RuntimeError as exc:
                    _LOGGER.warning("Opening generation fell back after narrator-opening failure: %s", str(exc))
                    opening = self._fallback_opening_lines(state, architect, cast, plan)
            room_future.result()
        return self._output_editor.review_opening(opening, state.active_goal)

    def _fallback_opening_lines(
        self,
        state: GameState,
        architect: dict[str, object],
        cast: dict[str, object],
        plan: dict[str, object],
    ) -> list[str]:
        room = state.world.rooms[state.player.location]
        protagonist = str(architect.get("protagonist_name", "")).strip() or "the detective"
        background = str(architect.get("protagonist_background", "")).strip()
        assistant_name = str(plan.get("assistant_name", "")).strip()
        contacts = cast.get("contacts", [])
        assistant_role = str(contacts[0].get("role", "")).strip() if contacts else ""
        objective = str(plan.get("actionable_objective", state.active_goal)).strip() or state.active_goal
        identity_line = f"You are {protagonist}."
        if background:
            identity_line = f"You are {protagonist}, {background.rstrip('.')}."
        assistant_line = ""
        if assistant_name:
            assistant_line = (
                f"{assistant_name} is nearby"
                + (f" as your {assistant_role}" if assistant_role else "")
                + ", waiting for your lead."
            )
        lines = [
            f"{room.name} waits in tense silence as the case begins.",
            identity_line,
            assistant_line or "You steady your breathing and take stock of the room.",
            f"Your immediate objective is clear: {objective}",
        ]
        return [line for line in lines if line.strip()]

    def _ensure_room_presentation_cache(
        self,
        state: GameState,
        architect: dict[str, object],
        cast: dict[str, object],
        plan: dict[str, object],
    ) -> None:
        existing = state.world_package.get("room_presentation_cache", {})
        if all(room_id in existing for room_id in state.world.rooms):
            return
        try:
            generated = self._room_presentation.run(state, architect, cast, plan)
            state.world_package["room_presentation_cache"] = generated
        except RuntimeError:
            fallback = {
                room_id: {
                    "long": room.description,
                    "short": room.description.split(".")[0].strip() + ".",
                }
                for room_id, room in state.world.rooms.items()
            }
            state.world_package["room_presentation_cache"] = fallback

    def review_turn(self, state: GameState, lines: list[str], events: list[Event], debug: bool = False) -> list[str]:
        return self._output_editor.review_turn(list(lines), state.active_goal, state.turn_index, debug)

    def replan_if_needed(self, state: GameState) -> Event | None:
        if not state.player.flags.get("story_replan_required", False):
            return None
        disruption = dict(state.world_package.get("story_replan_context", {}))
        plan = self._story_replan.run(state, disruption)
        new_goal = str(plan.get("new_active_goal", "")).strip()
        if new_goal:
            state.active_goal = new_goal
            goals = dict(state.world_package.get("goals", {}))
            goals["primary"] = new_goal
            goals["setup"] = new_goal
            state.world_package["goals"] = goals
        state.world_package["story_replan_plan"] = dict(plan)
        state.player.flags["story_replan_required"] = False
        state.player.flags["story_replanned"] = True
        note = str(plan.get("note", "")).strip() or "The story shifts in response to your prior choice."
        return Event(
            type="story_replan",
            tags=("story", "replan"),
            message_key=note,
            turn_index=state.turn_index,
            metadata={
                "disruption": disruption,
                "plan": dict(plan),
            },
        )
