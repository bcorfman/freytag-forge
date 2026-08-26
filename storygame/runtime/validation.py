"""Generic, fact-backed progression validation for Markdown story packages."""

from __future__ import annotations

from collections.abc import Iterable

from storygame.runtime.contracts import SceneTransitionProposal, TurnProposal
from storygame.runtime.facts import Fact, FactStore
from storygame.runtime.state import RuntimeState, RuntimeStateError
from storygame.story_package.models import FactPredicate, StoryPackage, Transition


class ProposalValidationError(RuntimeStateError):
    """An untrusted provider proposal violates the loaded package contract."""


def predicate_matches(predicate: FactPredicate, facts: FactStore) -> bool:
    """Evaluate a declared predicate without deriving truth from narration."""

    expected = str(predicate.equals).lower() if isinstance(predicate.equals, bool) else predicate.equals
    for fact in facts.matching(predicate.fact_id):
        actual = fact.value if fact.value is not None else fact.object
        if predicate.equals is None or actual == expected:
            return True
    return False


class ProgressionValidator:
    """Validates effects, storylets, transitions, and future dependencies."""

    def __init__(self, package: StoryPackage) -> None:
        self.package = package
        self._entities = {entity.id: entity for group in (package.world.npcs, package.world.items) for entity in group}
        self._transitions = {transition.id: transition for transition in package.pacing.transitions}

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

    def _validate_operations(self, proposal: TurnProposal) -> None:
        protected = set(self.package.world.protected_knowledge)
        for operation in proposal.operations:
            if operation.fact.predicate in protected or operation.fact.subject in protected:
                raise ProposalValidationError("proposal attempts to mutate protected knowledge")

    def _validate_events(self, state: RuntimeState, proposal: TurnProposal) -> None:
        storylet_ids = {
            storylet.id for storylet in self.package.storylets if storylet.scene_id == state.current_scene_id
        }
        for event in proposal.events:
            if event.event_id not in state.active_event_ids or event.event_id in state.fired_event_ids:
                raise ProposalValidationError("event is not active")
            if event.event_id.startswith("SL-") and event.event_id not in storylet_ids:
                raise ProposalValidationError("storylet is not available in the current scene")

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
