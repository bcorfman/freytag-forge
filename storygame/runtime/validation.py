"""Generic, fact-backed progression validation for Markdown story packages."""

from __future__ import annotations

from collections.abc import Iterable

from storygame.runtime.contracts import FactOperation, SceneTransitionProposal, StoryEventProposal, TurnProposal
from storygame.runtime.facts import Fact, FactStore
from storygame.runtime.state import RuntimeState, RuntimeStateError
from storygame.story_package.models import FactPredicate, StoryPackage, Transition


class ProposalValidationError(RuntimeStateError):
    """An untrusted provider proposal violates the loaded package contract."""


def predicate_matches(predicate: FactPredicate, facts: FactStore) -> bool:
    """Evaluate a declared predicate without deriving truth from narration."""

    expected = str(predicate.equals).lower() if isinstance(predicate.equals, bool) else predicate.equals
    matched = False
    for fact in facts.matching(predicate.fact_id):
        actual = fact.value if fact.value is not None else fact.object
        if predicate.equals is None or actual == expected:
            matched = True
            break
    # Route activation uses an absent fact as the ordinary false state.
    return not matched if predicate.equals is False else matched


class ProgressionValidator:
    """Validates effects, storylets, transitions, and future dependencies."""

    def __init__(self, package: StoryPackage) -> None:
        self.package = package
        self._entities = {entity.id: entity for group in (package.world.npcs, package.world.items) for entity in group}
        self._transitions = {transition.id: transition for transition in package.pacing.transitions}
        self._routes = {route.id: route for route in package.storylet_routes.storylets}

    def validate(self, state: RuntimeState, proposal: TurnProposal) -> tuple[str, ...]:
        self._validate_operations(proposal)
        candidate = state.facts.clone()
        for operation in proposal.operations:
            self._apply(candidate, operation.operation, operation.fact)
        self._validate_events(state, proposal)
        for event in proposal.events:
            for operation in event.operations:
                self._apply(candidate, operation.operation, operation.fact)
        self._validate_transition(state, proposal.transition, candidate)
        return self.unsatisfied_dependencies(state.current_scene_id, candidate)

    def normalize(self, state: RuntimeState, proposal: TurnProposal) -> TurnProposal:
        """Recover a uniquely identified active realization missing its event wrapper.

        This is a structural repair only: a full tuple, or an unambiguous subset,
        must identify one active route realization. The resulting effects always
        come from that package-authored realization, never from a new fact.
        """

        proposal = proposal.model_copy(
            update={"events": tuple(self._canonicalize_selected_knowledge_event(event) for event in proposal.events)}
        )
        proposal = proposal.model_copy(
            update={
                "operations": tuple(
                    operation
                    for operation in proposal.operations
                    if not self._canonical_operation_is_noop(state, operation)
                )
            }
        )

        if not proposal.operations:
            return proposal
        canonical_operations = tuple(
            operation for operation in proposal.operations if operation.fact.predicate in self.package.world.facts
        )
        if not canonical_operations:
            return proposal
        if proposal.events:
            event_operations = {
                operation
                for event in proposal.events
                if event.event_id in state.active_event_ids and event.event_id not in state.fired_event_ids
                if (route := self._routes.get(event.event_id)) is not None
                for realization in route.realizations
                if realization.id == event.realization_id
                if event.operations == tuple(self._route_operation(operation) for operation in realization.operations)
                for operation in event.operations
            }
            if not event_operations:
                # A provider can pair a uniquely identifying canonical subset
                # with a malformed event wrapper.  Discard only that wrapper
                # and let the same route-subset recovery below prove the
                # package-authorized effect; otherwise validation still rejects
                # the proposal unchanged.
                if not proposal.operations:
                    return proposal
                proposal = proposal.model_copy(update={"events": ()})
            else:
                return proposal.model_copy(
                    update={
                        "operations": tuple(
                            operation for operation in proposal.operations if operation not in event_operations
                        )
                    }
                )
        matches = [
            (route, realization, tuple(self._route_operation(operation) for operation in realization.operations))
            for route in self._routes.values()
            if route.id in state.active_event_ids and route.id not in state.fired_event_ids
            for realization in route.realizations
        ]
        exact_matches = [match for match in matches if match[2] == canonical_operations]
        route_ids = {route.id for route, _, _ in exact_matches}
        if len(route_ids) == 1:
            route, realization, expected_operations = exact_matches[0]
        else:
            partial_matches = [
                match for match in matches if all(operation in match[2] for operation in canonical_operations)
            ]
            partial_route_ids = {route.id for route, _, _ in partial_matches}
            partial_operation_sets: list[tuple[FactOperation, ...]] = []
            for _, _, operations in partial_matches:
                if operations not in partial_operation_sets:
                    partial_operation_sets.append(operations)
            if len(partial_route_ids) != 1 or len(partial_operation_sets) != 1:
                return proposal
            route, realization, expected_operations = partial_matches[0]
        return proposal.model_copy(
            update={
                "operations": tuple(
                    operation
                    for operation in proposal.operations
                    if operation.fact.predicate not in self.package.world.facts
                ),
                "events": (
                    StoryEventProposal(
                        event_id=route.id,
                        realization_id=realization.id,
                        operations=expected_operations,
                    ),
                ),
            }
        )

    def _canonicalize_selected_knowledge_event(self, event: StoryEventProposal) -> StoryEventProposal:
        """Use package fields only when selected knowledge agrees on one authored realization."""

        if not event.knowledge_ids:
            return event
        knowledge = self.package.knowledge_indexes.by_id
        selected = tuple(knowledge[item_id] for item_id in event.knowledge_ids if item_id in knowledge)
        if len(selected) != len(event.knowledge_ids):
            return event
        sources = {(item.source.storylet_id, item.source.realization_id) for item in selected}
        if len(sources) != 1:
            return event
        storylet_id, realization_id = sources.pop()
        route = self._routes.get(storylet_id or "")
        realization = next((item for item in route.realizations if item.id == realization_id), None) if route else None
        if realization is None:
            return event
        return event.model_copy(
            update={
                "event_id": route.id,
                "realization_id": realization.id,
                "operations": tuple(self._route_operation(operation) for operation in realization.operations),
            }
        )

    def _canonical_operation_is_noop(self, state: RuntimeState, operation: FactOperation) -> bool:
        if operation.fact.predicate not in self.package.world.facts:
            return False
        already_asserted = operation.fact in state.facts.asserted
        return already_asserted if operation.operation == "assert" else not already_asserted

    def _validate_operations(self, proposal: TurnProposal) -> None:
        protected = set(self.package.world.protected_knowledge)
        for operation in proposal.operations:
            if operation.fact.predicate in protected or operation.fact.subject in protected:
                raise ProposalValidationError("proposal attempts to mutate protected knowledge")
            if operation.fact.predicate in self.package.world.facts:
                raise ProposalValidationError("canonical facts must use a validated storylet realization")

    def _validate_events(self, state: RuntimeState, proposal: TurnProposal) -> None:
        storylet_ids = {
            storylet.id for storylet in self.package.storylets if storylet.scene_id == state.current_scene_id
        }
        for event in proposal.events:
            if event.event_id not in state.active_event_ids or event.event_id in state.fired_event_ids:
                raise ProposalValidationError(
                    f"storylet event '{event.event_id}' is not active in scene {state.current_scene_id}"
                )
            if event.event_id not in storylet_ids:
                raise ProposalValidationError("storylet is not available in the current scene")
            route = self._routes[event.event_id]
            realization = next((item for item in route.realizations if item.id == event.realization_id), None)
            if realization is None:
                raise ProposalValidationError("storylet event must name a valid realization")
            expected = tuple(self._route_operation(operation) for operation in realization.operations)
            if event.operations != expected:
                raise ProposalValidationError("storylet event operations do not match its validated realization")

    @staticmethod
    def _route_operation(operation: object) -> FactOperation:
        # Routes are world-level facts; their canonical subject is always story.
        from storygame.runtime.facts import Fact

        return FactOperation(
            operation=operation.op,
            fact=Fact(predicate=operation.fact_id, subject="story", value=str(operation.value).lower()),
        )

    def _validate_transition(
        self, state: RuntimeState, proposal: SceneTransitionProposal | None, facts: FactStore
    ) -> None:
        if proposal is None:
            return
        transition = self._transitions.get(proposal.transition_id)
        if transition is None or transition.source_scene_id != state.current_scene_id:
            raise ProposalValidationError("transition is not valid from the current scene")
        if not all(predicate_matches(trigger, facts) for trigger in transition.triggers):
            raise ProposalValidationError("transition triggers are not satisfied")

    def eligible_transitions(self, state: RuntimeState) -> tuple[Transition, ...]:
        eligible = [
            transition
            for transition in self.package.pacing.transitions
            if transition.source_scene_id == state.current_scene_id
            and all(predicate_matches(trigger, state.facts) for trigger in transition.triggers)
        ]
        return tuple(sorted(eligible, key=lambda transition: transition.priority, reverse=True))

    def unsatisfied_dependencies(self, scene_id: str, facts: FactStore) -> tuple[str, ...]:
        """Find indispensable reachable entities, honoring declared fallbacks."""

        remaining = self._reachable_transitions(scene_id)
        required = {dependency for transition in remaining for dependency in transition.required_dependencies}
        unavailable = {fact.subject for fact in facts.matching("destroyed")} | {
            fact.subject for fact in facts.matching("incapacitated")
        }
        return tuple(
            sorted(
                dependency
                for dependency in required
                if dependency in unavailable
                and not any(fallback not in unavailable for fallback in self._fallbacks(dependency))
            )
        )

    def _reachable_transitions(self, scene_id: str) -> tuple[Transition, ...]:
        seen: set[str] = set()
        pending = [scene_id]
        result: list[Transition] = []
        while pending:
            source = pending.pop()
            if source in seen:
                continue
            seen.add(source)
            outgoing = [
                transition for transition in self.package.pacing.transitions if transition.source_scene_id == source
            ]
            result.extend(outgoing)
            pending.extend(transition.target_scene_id for transition in outgoing)
        return tuple(result)

    def _fallbacks(self, entity_id: str) -> Iterable[str]:
        entity = self._entities.get(entity_id)
        return entity.fallback_ids if entity else ()

    @staticmethod
    def _apply(facts: FactStore, operation: str, fact: Fact) -> None:
        if operation == "assert":
            facts.assert_fact(fact)
        else:
            facts.retract_fact(fact)
