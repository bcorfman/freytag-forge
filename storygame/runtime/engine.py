"""LLM-first turn coordinator; it never parses ordinary roleplay text."""

from __future__ import annotations

from collections.abc import Callable

from storygame.runtime.contracts import GameBreakWarning, TurnProposal, parse_turn_proposal
from storygame.runtime.facts import Fact
from storygame.runtime.state import RuntimeState
from storygame.runtime.validation import ProgressionValidator


class RuntimeEngine:
    def __init__(self, state: RuntimeState, provider: Callable[[str], object]) -> None:
        self.state = state
        self.provider = provider
        self.validator = ProgressionValidator(state.package)

    def turn(self, player_input: str) -> TurnProposal:
        """Call the provider once, then validate before any canonical mutation."""

        self.state.require_turn_allowed()
        proposal = parse_turn_proposal(self.provider(player_input))
        at_risk = self.validator.validate(self.state, proposal)
        if at_risk:
            warning = GameBreakWarning(
                warning_id="future_dependency_at_risk",
                reason="This consequence would leave a required future dependency unavailable.",
                affected_ids=at_risk,
                snapshot_id=self.state.new_snapshot_id(),
            )
            self.state.set_pending_break(warning, proposal=proposal)
            return proposal.model_copy(update={"game_break": warning})
        self.state.apply_proposal(proposal)
        self._advance_pacing(proposal.narrative_seconds)
        self._activate_pacing()
        return proposal

    def resolve_break(self, decision: str) -> None:
        self.state.resolve_break(decision)
        if decision == "proceed":
            self._activate_pacing()

    def _activate_pacing(self) -> None:
        """Activate only package-declared, scene-bound optional storylets."""

        scene_pacing = next(
            item for item in self.state.package.pacing.scenes if item.scene_id == self.state.current_scene_id
        )
        for storylet in self.state.package.storylets:
            if (
                storylet.scene_id == self.state.current_scene_id
                and storylet.earliest_seconds <= scene_pacing.target_seconds <= storylet.latest_seconds
                and storylet.id not in self.state.fired_event_ids
            ):
                self.state.active_event_ids.add(storylet.id)
        elapsed = self._elapsed_seconds()
        for event in self.state.package.pacing.events:
            if (
                event.scene_id == self.state.current_scene_id
                and event.id not in self.state.fired_event_ids
                and elapsed >= event.at_seconds
            ):
                for effect in event.effects:
                    self.state.facts.assert_fact(
                        Fact(predicate=effect.fact_id, subject="story", value=str(effect.equals).lower())
                    )
                self.state.fired_event_ids.add(event.id)
                if event.transition_id:
                    self.state.apply_proposal(
                        TurnProposal(
                            narration="A declared pacing event changes the situation.",
                            transition={"transition_id": event.transition_id},
                        )
                    )

    def _advance_pacing(self, seconds: int) -> None:
        previous = self._elapsed_seconds()
        self.state.facts.retract_fact(Fact(predicate="story_elapsed_seconds", subject="story", value=str(previous)))
        self.state.facts.assert_fact(
            Fact(predicate="story_elapsed_seconds", subject="story", value=str(previous + seconds))
        )

    def _elapsed_seconds(self) -> int:
        values = self.state.facts.matching("story_elapsed_seconds", "story")
        return int(values[-1].value) if values and values[-1].value is not None else 0
