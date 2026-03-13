from __future__ import annotations

from storygame.engine.state import Event, GameState
from storygame.llm.output_editor import OutputEditor, build_output_editor
from storygame.llm.story_agents.agents import (
    CharacterDesignerAgent,
    DefaultCharacterDesignerAgent,
    DefaultNarratorOpeningAgent,
    DefaultPlotDesignerAgent,
    DefaultStoryArchitectAgent,
    DefaultStoryReplanAgent,
    NarratorOpeningAgent,
    PlotDesignerAgent,
    StoryArchitectAgent,
    StoryReplanAgent,
)


class StoryDirector:
    def __init__(
        self,
        mode: str,
        output_editor: OutputEditor | None = None,
        story_architect: StoryArchitectAgent | None = None,
        character_designer: CharacterDesignerAgent | None = None,
        plot_designer: PlotDesignerAgent | None = None,
        narrator_opening: NarratorOpeningAgent | None = None,
        story_replan: StoryReplanAgent | None = None,
    ) -> None:
        self._output_editor = build_output_editor(mode) if output_editor is None else output_editor
        self._story_architect = DefaultStoryArchitectAgent(mode) if story_architect is None else story_architect
        self._character_designer = (
            DefaultCharacterDesignerAgent(mode) if character_designer is None else character_designer
        )
        self._plot_designer = DefaultPlotDesignerAgent(mode) if plot_designer is None else plot_designer
        self._narrator_opening = DefaultNarratorOpeningAgent(mode) if narrator_opening is None else narrator_opening
        self._story_replan = DefaultStoryReplanAgent(mode) if story_replan is None else story_replan

    def compose_opening(self, state: GameState) -> list[str]:
        architect = self._story_architect.run(state)
        cast = self._character_designer.run(state, architect)
        plan = self._plot_designer.run(state, architect, cast)
        opening = self._narrator_opening.run(state, architect, cast, plan)
        return self._output_editor.review_opening(opening, state.active_goal)

    def review_turn(self, state: GameState, lines: list[str], events: list[Event], debug: bool = False) -> list[str]:
        event_hint = ""
        if events:
            event_hint = " ".join(event.message_key for event in events if event.message_key)[:240]
        enriched = list(lines)
        if event_hint and len(enriched) > 0 and event_hint.lower() not in "\n".join(enriched).lower():
            enriched.append(event_hint)
        return self._output_editor.review_turn(enriched, state.active_goal, state.turn_index, debug)

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
