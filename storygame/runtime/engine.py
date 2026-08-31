"""LLM-first turn coordinator; it never parses ordinary roleplay text."""

from __future__ import annotations

from collections.abc import Callable

from storygame.runtime.contracts import (
    FactOperation,
    GameBreakWarning,
    NarrationSegment,
    ResolvedTurnProposal,
    SceneTransitionProposal,
    parse_turn_proposal,
)
from storygame.runtime.facts import Fact
from storygame.runtime.knowledge import KnowledgeProjector, TurnKnowledgeContext
from storygame.runtime.state import RuntimeState, TurnDelivery, TurnRecord
from storygame.runtime.validation import (
    ProgressionValidator,
    SelectedRevealResolver,
    predicate_matches,
    unconveyed_terms,
)
from storygame.story_package.models import FactDelivery

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
        self.state.last_turn_delivery = TurnDelivery()
        self.state.turn_index += 1
        self._activate_pacing()
        self.state.last_turn_delivery = self.state.last_turn_delivery.model_copy(
            update={
                "hint_staged": bool(self.state.staged_hint_fact_ids),
                "handoff_staged": bool(self.state.staged_handoff_fact_ids),
            }
        )
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
        canonical_event_id = None
        if self.state.staged_handoff_fact_ids and not provider_proposal.selected_knowledge_ids:
            proposal, canonical_event_id = self._prepare_handoff(proposal)
        self.state.apply_proposal(proposal, canonical_event_ids=(canonical_event_id,) if canonical_event_id else ())
        self._record_turn(proposal)
        self._advance_pacing(proposal.narrative_seconds if clock_seconds is None else clock_seconds)
        self._activate_pacing()
        if not (canonical_event_id and proposal.transition):
            self._apply_canonical_route_events()
        self._activate_pacing()
        entry_segments = self._apply_authored_transition()
        self._activate_pacing()
        if entry_segments:
            return proposal.model_copy(update={"segments": (*proposal.segments, *entry_segments)})
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

    def _apply_authored_transition(self) -> tuple[NarrationSegment, ...] | None:
        """Advance along the highest-priority authored transition once its declared triggers hold.

        The source scene's min_turns is a hard pacing floor so committed
        triggers cannot rush the player out before the scene has had its minimum play.
        Returns the source bridge and entered scene's authored entry as two
        narration segments so both package-owned paragraphs reach the player.
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
            source_scene = next(
                item for item in self.state.package.scenes if item.metadata.scene_id == transition.source_scene_id
            )
            bridge = NarrationSegment(kind="narration", text=source_scene.metadata.bridge_text[transition.id])
            entry = NarrationSegment(kind="narration", text=scene.metadata.entry_text)
            self.state.apply_proposal(
                ResolvedTurnProposal(
                    segments=(bridge, entry),
                    transition={"transition_id": transition.id},
                )
            )
            return bridge, entry
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
        self._apply_world_actions()
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
        windows = {window.scene_id: window for window in self.state.package.pacing.scenes}
        window = windows[self.state.current_scene_id]
        turns_since_entry = self.state.turn_index - self.state.scene_entered_at_turn
        missing = self._bridge_delivery_fact_ids()
        if turns_since_entry >= window.nudge_after_turns:
            self.state.staged_hint_fact_ids = missing
        if turns_since_entry >= window.handoff_after_turns:
            self.state.staged_handoff_fact_ids = missing

    def _bridge_delivery_fact_ids(self) -> tuple[str, ...]:
        true_facts = frozenset(
            fact.predicate for fact in self.state.facts.asserted if str(fact.value).lower() == "true"
        )
        deliveries = {delivery.fact_id for delivery in self.state.package.deliveries}
        for event in self.state.package.storylet_routes.bridge_events:
            if event.scene_id != self.state.current_scene_id or event.id in self.state.fired_event_ids:
                continue
            if event.activation.is_satisfied(true_facts):
                continue
            missing = event.activation.minimal_undelivered_facts(true_facts)
            return tuple(fact_id for fact_id in missing if fact_id in deliveries)
        return ()

    def _apply_world_actions(self) -> None:
        """Apply active, player-hidden route effects once their prerequisites hold."""

        for knowledge in self.state.package.knowledge.knowledge:
            if (
                knowledge.audience.kind != "world_only"
                or self.state.current_scene_id not in knowledge.available_in_scenes
                or knowledge.source.storylet_id not in self.state.active_event_ids
                or knowledge.source.storylet_id in self.state.fired_event_ids
                or not all(predicate_matches(predicate, self.state.facts) for predicate in knowledge.requires)
                or not any(
                    self._knowledge_effect_established(effect.fact_id, effect.op, effect.value)
                    for effect in knowledge.establishes
                )
            ):
                continue
            for effect in knowledge.establishes:
                fact = Fact(predicate=effect.fact_id, subject="story", value=str(effect.value).lower())
                if effect.op == "assert":
                    self.state.facts.assert_fact(fact)
                else:
                    self.state.facts.retract_fact(fact)

    def _knowledge_effect_established(self, fact_id: str, operation: str, value: object) -> bool:
        expected = str(value).lower()
        matched = any(
            (fact.value if fact.value is not None else fact.object) == expected
            for fact in self.state.facts.matching(fact_id)
        )
        return matched if operation == "assert" else not matched

    def _prepare_handoff(self, proposal: ResolvedTurnProposal) -> tuple[ResolvedTurnProposal, str | None]:
        deliveries = {
            delivery.fact_id: delivery
            for delivery in self.state.package.deliveries
            if delivery.fact_id in self.state.staged_handoff_fact_ids
        }
        segments = proposal.segments
        missing = self._missing_handoff_terms(deliveries.values(), proposal.narration)
        if missing:
            segments = tuple(
                NarrationSegment(kind="narration", text=delivery.fallback_text) for delivery in deliveries.values()
            )
        delivery_operations = tuple(
            operation for delivery in deliveries.values() for operation in self._delivery_operations(delivery)
        )
        candidate_facts = self.state.facts.clone()
        for operation in (*proposal.operations, *delivery_operations):
            self.state._apply_operation(candidate_facts, operation)
        for event in proposal.events:
            for operation in event.operations:
                self.state._apply_operation(candidate_facts, operation)
        pending_bridge_event = next(
            (
                event
                for event in self.state.package.storylet_routes.bridge_events
                if event.scene_id == self.state.current_scene_id
                and event.id not in self.state.fired_event_ids
                and not event.activation.is_satisfied(self._true_facts(self.state.facts))
            ),
            None,
        )
        world_only_operations = (
            self._world_only_bridge_operations(pending_bridge_event, candidate_facts)
            if pending_bridge_event is not None
            else ()
        )
        for operation in world_only_operations:
            self.state._apply_operation(candidate_facts, operation)
        world_operations = self._world_action_operations(candidate_facts)
        for operation in world_operations:
            self.state._apply_operation(candidate_facts, operation)
        bridge_event = next(
            (
                event
                for event in self.state.package.storylet_routes.bridge_events
                if event.scene_id == self.state.current_scene_id
                and event.id not in self.state.fired_event_ids
                and event.activation.is_satisfied(self._true_facts(candidate_facts))
            ),
            None,
        )
        bridge_operations = (
            tuple(
                FactOperation(
                    operation=operation.op,
                    fact=Fact(predicate=operation.fact_id, subject="story", value=str(operation.value).lower()),
                )
                for operation in bridge_event.operations
            )
            if bridge_event
            else ()
        )
        for operation in bridge_operations:
            self.state._apply_operation(candidate_facts, operation)
        transition = self._handoff_transition(candidate_facts) if bridge_event else None
        if transition:
            source_scene = next(
                item for item in self.state.package.scenes if item.metadata.scene_id == transition.source_scene_id
            )
            target_scene = next(
                item for item in self.state.package.scenes if item.metadata.scene_id == transition.target_scene_id
            )
            segments = (
                *segments,
                NarrationSegment(kind="narration", text=source_scene.metadata.bridge_text[transition.id]),
                NarrationSegment(kind="narration", text=target_scene.metadata.entry_text),
            )
        combined = proposal.model_copy(
            update={
                "segments": segments,
                "operations": (
                    *proposal.operations,
                    *delivery_operations,
                    *world_only_operations,
                    *world_operations,
                    *bridge_operations,
                ),
                "transition": SceneTransitionProposal(transition_id=transition.id) if transition else None,
            }
        )
        return combined, bridge_event.id if bridge_event else None

    @staticmethod
    def _true_facts(facts) -> frozenset[str]:
        return frozenset(fact.predicate for fact in facts.asserted if str(fact.value).lower() == "true")

    @staticmethod
    def _delivery_operations(delivery: FactDelivery) -> tuple[FactOperation, ...]:
        operations = [
            FactOperation(operation="assert", fact=Fact(predicate=delivery.fact_id, subject="story", value="true"))
        ]
        operations.extend(
            FactOperation(
                operation=cost.op,
                fact=Fact(predicate=cost.fact_id, subject="story", value=str(cost.value).lower()),
            )
            for cost in delivery.costs
        )
        return tuple(operations)

    def _world_only_bridge_operations(self, event, facts) -> tuple[FactOperation, ...]:
        player_safe_fact_ids = {
            effect.fact_id
            for knowledge in self.state.package.knowledge.knowledge
            if knowledge.audience.player_visible
            for effect in knowledge.establishes
        }
        missing_fact_ids = event.activation.minimal_undelivered_facts(self._true_facts(facts))
        return tuple(
            FactOperation(
                operation="assert",
                fact=Fact(predicate=fact_id, subject="story", value="true"),
            )
            for fact_id in missing_fact_ids
            if fact_id not in player_safe_fact_ids
        )

    def _world_action_operations(self, facts) -> tuple[FactOperation, ...]:
        operations: list[FactOperation] = []
        for knowledge in self.state.package.knowledge.knowledge:
            if (
                knowledge.audience.kind != "world_only"
                or self.state.current_scene_id not in knowledge.available_in_scenes
                or knowledge.source.storylet_id not in self.state.active_event_ids
                or knowledge.source.storylet_id in self.state.fired_event_ids
                or not all(predicate_matches(predicate, facts) for predicate in knowledge.requires)
                or all(
                    self._fact_operation_established(facts, effect.op, effect.fact_id, effect.value)
                    for effect in knowledge.establishes
                )
            ):
                continue
            operations.extend(
                FactOperation(
                    operation=effect.op,
                    fact=Fact(predicate=effect.fact_id, subject="story", value=str(effect.value).lower()),
                )
                for effect in knowledge.establishes
            )
        return tuple(operations)

    @staticmethod
    def _fact_operation_established(facts, operation: str, fact_id: str, value: object) -> bool:
        expected = str(value).lower()
        matched = any(
            (fact.value if fact.value is not None else fact.object) == expected for fact in facts.matching(fact_id)
        )
        return matched if operation == "assert" else not matched

    @staticmethod
    def _missing_handoff_terms(deliveries, narration: str) -> tuple[str, ...]:
        missing: list[str] = []
        for delivery in deliveries:
            missing.extend(unconveyed_terms(delivery.must_convey, narration))
        return tuple(missing)

    def _handoff_transition(self, facts):
        turns_since_entry = self.state.turn_index - self.state.scene_entered_at_turn
        windows = {window.scene_id: window for window in self.state.package.pacing.scenes}
        eligible = [
            transition
            for transition in self.state.package.pacing.transitions
            if transition.source_scene_id == self.state.current_scene_id
            and turns_since_entry >= windows[transition.source_scene_id].min_turns
            and all(predicate_matches(trigger, facts) for trigger in transition.triggers)
            and self.validator.transition_dependencies_available(transition, facts)
        ]
        return max(eligible, key=lambda transition: transition.priority, default=None)

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
