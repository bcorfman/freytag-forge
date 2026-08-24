"""Deterministic review of immutable dramatic-spine and storylet content."""

from __future__ import annotations

from storygame.authoring.bound_ir import BoundBlueprint
from storygame.authoring.causal_contracts import CausalCompiledStory
from storygame.authoring.causal_critics import CausalCriticResult
from storygame.authoring.causal_profiles import CausalProfileRegistry


class StoryletCoverageCritic:
    """Require a reviewed spine to have a sufficiently varied playable pool."""

    def __init__(self, profiles: CausalProfileRegistry) -> None:
        self._profiles = profiles

    def critique(self, story: CausalCompiledStory | BoundBlueprint) -> CausalCriticResult:
        story = story.story if isinstance(story, BoundBlueprint) else story
        if story.dramatic_spine is None:
            return CausalCriticResult("storylet_coverage", True)
        if not story.storylets:
            return CausalCriticResult("storylet_coverage", False, ("dramatic spine has no storylets",))
        profile = self._profiles.resolve(story.profile)
        covered = {item.beat_id for item in story.storylets}
        diagnostics = [
            f"required beat '{beat.id}' has no storylet" for beat in story.required_beats if beat.id not in covered
        ]
        purposes = {item.purpose for item in story.storylets}
        if len(purposes) < profile.minimum_storylet_variety:
            diagnostics.append(f"storylet pool has fewer than {profile.minimum_storylet_variety} purposes")
        return CausalCriticResult("storylet_coverage", not diagnostics, tuple(diagnostics))


class DramaticEscalationCritic:
    """Keep storylet pressure bands inside the declared dramatic envelope."""

    def critique(self, story: CausalCompiledStory | BoundBlueprint) -> CausalCriticResult:
        story = story.story if isinstance(story, BoundBlueprint) else story
        if story.dramatic_spine is None:
            return CausalCriticResult("dramatic_escalation", True)
        target = story.dramatic_spine.target_pressure
        diagnostics = tuple(
            f"storylet '{item.id}' pressure band is outside the dramatic spine"
            for item in story.storylets
            if item.availability.pressure.minimum < target.minimum
            or item.availability.pressure.maximum > target.maximum
        )
        return CausalCriticResult("dramatic_escalation", not diagnostics, diagnostics)


class ParticipantContinuityCritic:
    """Ensure each storylet has actors and the declared spine roles can act."""

    def critique(self, story: CausalCompiledStory | BoundBlueprint) -> CausalCriticResult:
        story = story.story if isinstance(story, BoundBlueprint) else story
        if story.dramatic_spine is None:
            return CausalCriticResult("participant_continuity", True)
        participant_roles = {item.id: item.role for item in story.participants}
        active_roles = {
            participant_roles[participant_id]
            for storylet in story.storylets
            for participant_id in storylet.availability.participant_ids
        }
        diagnostics = [
            f"storylet '{item.id}' has no declared participants"
            for item in story.storylets
            if not item.availability.participant_ids
        ]
        diagnostics.extend(
            f"dramatic spine role '{role}' has no participating storylet"
            for role in story.dramatic_spine.participant_role_requirements
            if role not in active_roles
        )
        return CausalCriticResult("participant_continuity", not diagnostics, tuple(diagnostics))


class ProtectedKnowledgeSafetyCritic:
    """Defence in depth for selector-visible storylet availability facts."""

    def critique(self, story: CausalCompiledStory | BoundBlueprint) -> CausalCriticResult:
        story = story.story if isinstance(story, BoundBlueprint) else story
        protected = {item.truth_id for item in story.knowledge_protections}
        diagnostics = tuple(
            f"storylet '{item.id}' exposes protected availability truth"
            for item in story.storylets
            if protected & set((*item.availability.required_truth_ids, *item.availability.absent_truth_ids))
        )
        return CausalCriticResult("protected_knowledge_safety", not diagnostics, diagnostics)


class FailureForwardViabilityCritic:
    """Require a failed storylet to open a genuinely usable alternative."""

    def critique(self, story: CausalCompiledStory | BoundBlueprint) -> CausalCriticResult:
        story = story.story if isinstance(story, BoundBlueprint) else story
        by_id = {item.id: item for item in story.storylets}
        diagnostics: list[str] = []
        for item in story.storylets:
            for alternative_id in item.failure_forward_storylet_ids:
                alternative = by_id[alternative_id]
                if alternative.route_family == item.route_family:
                    diagnostics.append(
                        f"storylet '{item.id}' failure-forward target '{alternative_id}' repeats its route family"
                    )
                if item.completion_truth_id in alternative.availability.required_truth_ids:
                    diagnostics.append(
                        f"storylet '{item.id}' failure-forward target '{alternative_id}' requires its completion"
                    )
        return CausalCriticResult("failure_forward_viability", not diagnostics, tuple(diagnostics))
