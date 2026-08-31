"""Generic, fact-backed progression validation for Markdown story packages."""

from __future__ import annotations

import re
from collections.abc import Iterable
from copy import deepcopy
from itertools import combinations

from storygame.runtime.contracts import (
    FactOperation,
    NarrationSegment,
    ResolvedTurnProposal,
    SceneTransitionProposal,
    StoryEventProposal,
    TurnProposal,
)
from storygame.runtime.facts import Fact, FactStore
from storygame.runtime.state import RuntimeState, RuntimeStateError
from storygame.story_package.models import FactPredicate, StoryPackage, Transition


class ProposalValidationError(RuntimeStateError):
    """An untrusted provider proposal violates the loaded package contract."""


def unconveyed_terms(groups: tuple[tuple[str, ...], ...], text: str) -> tuple[str, ...]:
    """Return the first phrasing from each synonym group absent from ``text``."""

    replacements = str.maketrans(
        {
            "“": '"',
            "”": '"',
            "‘": "'",
            "’": "'",
            "–": "-",
            "—": "-",
        }
    )

    def normalize(value: str) -> str:
        return re.sub(r"\s+", " ", value.translate(replacements).casefold()).strip()

    def words(value: str) -> tuple[str, ...]:
        return tuple(re.findall(r"[^\W_]+(?:'[^\W_]+)*", normalize(value)))

    def word_matches(authored: str, prose: str) -> bool:
        return prose == authored or any(prose == authored + suffix for suffix in ("s", "es", "ed", "d", "ing"))

    def phrase_matches(phrasing: str, prose_words: tuple[str, ...]) -> bool:
        phrasing_words = words(phrasing)
        if not phrasing_words or len(phrasing_words) > len(prose_words):
            return False
        width = len(phrasing_words)
        return any(
            all(
                word_matches(authored, prose)
                for authored, prose in zip(phrasing_words, prose_words[start : start + width], strict=True)
            )
            for start in range(len(prose_words) - width + 1)
        )

    normalized_text = words(text)
    missing: list[str] = []
    for group in groups:
        if not any(phrase_matches(phrasing, normalized_text) for phrasing in group):
            missing.append(group[0] if group else "")
    return tuple(missing)


def derive_grounding(
    groups: tuple[tuple[str, ...], ...], segments: tuple[NarrationSegment, ...]
) -> tuple[NarrationSegment, ...]:
    """Return the smallest ordered evidence set whose text conveys every group."""

    if not groups:
        return ()
    for size in range(1, len(segments) + 1):
        for indexes in combinations(range(len(segments)), size):
            selected = tuple(segments[index] for index in indexes)
            combined_text = " ".join(segment.text for segment in selected)
            if not unconveyed_terms(groups, combined_text):
                return selected
    return ()


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


class SelectedRevealResolver:
    """Resolve a provider knowledge ID into one immutable package route."""

    def __init__(self, package: StoryPackage) -> None:
        self.package = package
        self._validator = ProgressionValidator(package)
        self._routes = {route.id: route for route in package.storylet_routes.storylets}

    def resolve(self, state, projection, provider_proposal: TurnProposal, projector, player_input: str):
        selected = provider_proposal.selected_knowledge_ids
        if len(selected) > 1:
            raise ProposalValidationError("at most one knowledge selection is allowed per turn")
        candidate_ids = {item.id for item in projection.candidates}
        if any(item_id not in candidate_ids for item_id in selected):
            raise ProposalValidationError("selected knowledge is not eligible for this turn")
        events: tuple[StoryEventProposal, ...] = ()
        if selected:
            knowledge = self.package.knowledge_indexes.by_id[selected[0]]
            route = self._routes.get(knowledge.source.storylet_id or "")
            realization = (
                next((item for item in route.realizations if item.id == knowledge.source.realization_id), None)
                if route
                else None
            )
            if route is None or realization is None:
                raise ProposalValidationError("selected knowledge has no executable package source")
            events = (
                StoryEventProposal(
                    event_id=route.id,
                    realization_id=realization.id,
                    knowledge_ids=selected,
                    operations=tuple(self._validator._route_operation(item) for item in realization.operations),
                ),
            )
        resolved = ResolvedTurnProposal(
            segments=provider_proposal.segments,
            selected_knowledge_ids=selected,
            events=events,
        )
        allowed = {item.id for item in projection.committed_knowledge} | set(selected)
        if any(grounding_id not in allowed for segment in resolved.segments for grounding_id in segment.grounding_ids):
            raise ProposalValidationError("segment grounding is not committed or selected knowledge")
        # A reveal the player never reads is worse than one that does not commit: the
        # fact silently unlocks the scene's exit, so the story moves on to a place the
        # player was given no reason to go. Requiring the selected ID to ground one of
        # this turn's own segments keeps the commit and the telling in the same breath.
        grounded = {grounding_id for segment in resolved.segments for grounding_id in segment.grounding_ids}
        undelivered = sorted(knowledge_id for knowledge_id in selected if knowledge_id not in grounded)
        if undelivered:
            knowledge = self.package.knowledge_indexes.by_id[undelivered[0]]
            derived_segments = derive_grounding(knowledge.must_convey, resolved.segments)
            if derived_segments:
                resolved = resolved.model_copy(
                    update={
                        "segments": tuple(
                            segment.model_copy(
                                update={"grounding_ids": (*segment.grounding_ids, *undelivered)}
                            )
                            if any(segment is derived_segment for derived_segment in derived_segments)
                            else segment
                            for segment in resolved.segments
                        )
                    }
                )
            grounded = {grounding_id for segment in resolved.segments for grounding_id in segment.grounding_ids}
            undelivered = sorted(knowledge_id for knowledge_id in selected if knowledge_id not in grounded)
            if undelivered:
                raise ProposalValidationError("selected knowledge must be grounded in the segment that reveals it")
        for knowledge_id in selected:
            knowledge = self.package.knowledge_indexes.by_id[knowledge_id]
            grounded_text = " ".join(
                segment.text for segment in resolved.segments if knowledge_id in segment.grounding_ids
            )
            missing = unconveyed_terms(knowledge.must_convey, grounded_text)
            if missing:
                raise ProposalValidationError(
                    f"selected knowledge '{knowledge_id}' does not convey: {', '.join(missing)}"
                )
        self._validator.validate(state, resolved)
        candidate_state = deepcopy(state)
        candidate_state.apply_proposal(resolved)
        post_projection = projector.project(candidate_state, "player", player_input)
        return resolved, post_projection


class ProgressionValidator:
    """Validates effects, storylets, transitions, and future dependencies."""

    def __init__(self, package: StoryPackage) -> None:
        self.package = package
        self._entities = {entity.id: entity for group in (package.world.npcs, package.world.items) for entity in group}
        self._transitions = {transition.id: transition for transition in package.pacing.transitions}
        self._routes = {route.id: route for route in package.storylet_routes.storylets}

    def validate(self, state: RuntimeState, proposal: ResolvedTurnProposal) -> tuple[str, ...]:
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

    def _validate_operations(self, proposal: ResolvedTurnProposal) -> None:
        protected = set(self.package.world.protected_knowledge)
        for operation in proposal.operations:
            if operation.fact.predicate in protected or operation.fact.subject in protected:
                raise ProposalValidationError("proposal attempts to mutate protected knowledge")
            if operation.fact.predicate in self.package.world.facts:
                raise ProposalValidationError("canonical facts must use a validated storylet realization")

    def _validate_events(self, state: RuntimeState, proposal: ResolvedTurnProposal) -> None:
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

    def transition_dependencies_available(self, transition: Transition, facts: FactStore) -> bool:
        """Check the transition's declared dependencies, honoring declared fallbacks."""

        unavailable = {fact.subject for fact in facts.matching("destroyed")} | {
            fact.subject for fact in facts.matching("incapacitated")
        }
        return all(
            dependency not in unavailable
            or any(fallback not in unavailable for fallback in self._fallbacks(dependency))
            for dependency in transition.required_dependencies
        )

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
