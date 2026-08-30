"""LLM-first turn coordinator; it never parses ordinary roleplay text."""

from __future__ import annotations

from collections.abc import Callable

from storygame.runtime.contracts import (
    FactOperation,
    GameBreakWarning,
    NarrationSegment,
    ResolvedTurnProposal,
    parse_turn_proposal,
)
from storygame.runtime.facts import Fact
from storygame.runtime.knowledge import KnowledgeProjector, TurnKnowledgeContext
from storygame.runtime.state import RuntimeState, TurnRecord
from storygame.runtime.validation import ProgressionValidator, SelectedRevealResolver

SCENE_ENTRY_REQUEST = "Narrate the opening of this scene."


class RuntimeEngine:
    def __init__(
        self, state: RuntimeState, provider: Callable[[str], object], *, projector: KnowledgeProjector | None = None
    ) -> None:
        self.state = state
        self.provider = provider
        self.validator = ProgressionValidator(state.package)
        self.reveal_resolver = SelectedRevealResolver(state.package)
        self.projector = projector or KnowledgeProjector()
        self.last_projection: TurnKnowledgeContext | None = None
        self.last_post_selection_projection: TurnKnowledgeContext | None = None

    def opening(self) -> ResolvedTurnProposal:
        """Open on the authored entry text, then the provider's embellishment; an opening commits no canon.

        The package owns the first words verbatim, so the scene always starts the
        way plot.md wrote it. The provider only continues from there, embellishing
        the scene's first authored beat, and no scene text is written in the runtime.
        """

        self.last_projection = self.projector.project(self.state, "player", "")
        scene = next(
            item for item in self.state.package.scenes if item.metadata.scene_id == self.state.current_scene_id
        )
        request = getattr(self.provider, "opening", None)
        proposal = parse_turn_proposal(request() if callable(request) else self.provider(SCENE_ENTRY_REQUEST))
        entry = NarrationSegment(kind="narration", text=scene.metadata.entry_text)
        return ResolvedTurnProposal(segments=(entry, *proposal.segments))

    def turn(self, player_input: str, *, clock_seconds: int | None = None) -> ResolvedTurnProposal:
        """Call the provider once, then validate before any canonical mutation."""

        self.state.require_turn_allowed()
        self.state.turn_index += 1
        self._activate_pacing()
        self.last_projection = self.projector.project(self.state, "player", player_input)
        provider_proposal = parse_turn_proposal(self.provider(player_input))
        proposal, self.last_post_selection_projection = self.reveal_resolver.resolve(
            self.state, self.last_projection, provider_proposal, self.projector, player_input
        )
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
        self._record_turn(proposal)
        self._advance_pacing(proposal.narrative_seconds if clock_seconds is None else clock_seconds)
        self._activate_pacing()
        self._apply_canonical_route_events()
        self._activate_pacing()
        entry_text = self._apply_authored_transition()
        self._activate_pacing()
        if entry_text:
            return proposal.model_copy(
                update={"segments": (*proposal.segments, NarrationSegment(kind="narration", text=entry_text))}
            )
        return proposal

    def _record_turn(self, proposal: ResolvedTurnProposal) -> None:
        event_ids = tuple(sorted(event.event_id for event in proposal.events))
        reveal_ids = tuple(
            knowledge_id
            for event in proposal.events
            for knowledge_id in self.state.package.knowledge_indexes.source_to_knowledge.get(
                f"storylet:{event.event_id}:{event.realization_id}", ()
            )
        )
        fact_keys = tuple(
            sorted(
                {operation.fact.predicate for operation in proposal.operations}
                | {operation.fact.predicate for event in proposal.events for operation in event.operations}
            )
        )
        event_operations = tuple(operation for event in proposal.events for operation in event.operations)
        all_operations = (*proposal.operations, *event_operations)
        affected_entity_ids = tuple(
            sorted(
                {
                    entity_id
                    for operation in all_operations
                    for entity_id in (operation.fact.subject, operation.fact.object)
                    if entity_id is not None
                }
            )
        )
        self.state.turn_records.append(
            TurnRecord(
                id=f"turn_{len(self.state.turn_records) + 1}",
                reveal_ids=reveal_ids,
                affected_entity_ids=affected_entity_ids,
                event_ids=event_ids,
                transition_id=proposal.transition.transition_id if proposal.transition else None,
                fact_keys=fact_keys,
            )
        )
        del self.state.turn_records[:-24]

    def resolve_break(self, decision: str) -> None:
        self.state.resolve_break(decision)
        if decision == "proceed":
            self._apply_canonical_route_events()
            self._activate_pacing()
            self._apply_authored_transition()
            self._activate_pacing()

    def _apply_authored_transition(self) -> str | None:
        """Advance along the highest-priority authored transition once its declared triggers hold.

        The source scene's min_turns is a hard pacing floor so committed
        triggers cannot rush the player out before the scene has had its minimum play.
        Returns the entered scene's authored entry text so the turn can open the
        new scene with the package's own words.
        """

        if self.state.has_pending_break:
            return None
        turns_since_entry = self.state.turn_index - self.state.scene_entered_at_turn
        windows = {window.scene_id: window for window in self.state.package.pacing.scenes}
        for transition in self.validator.eligible_transitions(self.state):
            if turns_since_entry < windows[transition.source_scene_id].min_turns:
                continue
            if not self.validator.transition_dependencies_available(transition, self.state.facts):
                continue
            scene = next(
                item for item in self.state.package.scenes if item.metadata.scene_id == transition.target_scene_id
            )
            self.state.apply_proposal(
                ResolvedTurnProposal(
                    segments=(NarrationSegment(kind="narration", text=scene.metadata.entry_text),),
                    transition={"transition_id": transition.id},
                )
            )
            return scene.metadata.entry_text
        return None

    def _activate_pacing(self) -> None:
        """Activate only package-declared, scene-bound optional storylets."""

        turns_since_entry = self.state.turn_index - self.state.scene_entered_at_turn
        for storylet in self.state.package.storylet_routes.storylets:
            if (
                storylet.scene_id == self.state.current_scene_id
                and storylet.earliest_turn <= turns_since_entry
                and all(self._predicate_matches(predicate) for predicate in storylet.activation_conditions)
                and storylet.id not in self.state.fired_event_ids
            ):
                self.state.active_event_ids.add(storylet.id)
        for event in self.state.package.pacing.events:
            if (
                event.scene_id == self.state.current_scene_id
                and event.id not in self.state.fired_event_ids
                and turns_since_entry >= event.at_turn
            ):
                for effect in event.effects:
                    self.state.facts.assert_fact(
                        Fact(predicate=effect.fact_id, subject="story", value=str(effect.equals).lower())
                    )
                self.state.fired_event_ids.add(event.id)
                if event.transition_id:
                    self.state.apply_proposal(
                        ResolvedTurnProposal(
                            segments=(
                                NarrationSegment(
                                    kind="narration", text="A declared pacing event changes the situation."
                                ),
                            ),
                            transition={"transition_id": event.transition_id},
                        )
                    )

    def _apply_canonical_route_events(self) -> None:
        """Commit only route-authored bridge/resolution facts once their conditions hold."""

        routes = self.state.package.storylet_routes
        events = (*routes.bridge_events, *routes.resolution_events)
        for event in events:
            if event.scene_id != self.state.current_scene_id or event.id in self.state.fired_event_ids:
                continue
            true_facts = frozenset(
                fact.predicate for fact in self.state.facts.asserted if str(fact.value).lower() == "true"
            )
            if not event.activation.is_satisfied(true_facts):
                continue
            operations = tuple(
                FactOperation(
                    operation=operation.op,
                    fact=Fact(predicate=operation.fact_id, subject="story", value=str(operation.value).lower()),
                )
                for operation in event.operations
            )
            for operation in operations:
                self.state._apply_operation(self.state.facts, operation)
            self.state.fired_event_ids.add(event.id)

    def _predicate_matches(self, predicate: object) -> bool:
        from storygame.runtime.validation import predicate_matches

        return predicate_matches(predicate, self.state.facts)

    def _advance_pacing(self, seconds: int) -> None:
        previous = self._elapsed_seconds()
        self.state.facts.retract_fact(Fact(predicate="story_elapsed_seconds", subject="story", value=str(previous)))
        self.state.facts.assert_fact(
            Fact(predicate="story_elapsed_seconds", subject="story", value=str(previous + seconds))
        )

    def _elapsed_seconds(self) -> int:
        values = self.state.facts.matching("story_elapsed_seconds", "story")
        return int(values[-1].value) if values and values[-1].value is not None else 0
