"""Local, deterministic reviewers for immutable causal candidates."""

from __future__ import annotations

from dataclasses import dataclass

from storygame.authoring.bound_ir import BoundBlueprint, bind_blueprint
from storygame.authoring.causal_contracts import CausalCompiledStory
from storygame.authoring.causal_profiles import CausalProfileRegistry


@dataclass(frozen=True)
class CausalCriticResult:
    critic: str
    accepted: bool
    diagnostics: tuple[str, ...] = ()


class RouteFairnessCritic:
    def __init__(self, profiles: CausalProfileRegistry) -> None:
        self._profiles = profiles

    def critique(self, story: CausalCompiledStory | BoundBlueprint) -> CausalCriticResult:
        bound = story if isinstance(story, BoundBlueprint) else bind_blueprint(story)
        minimum = self._profiles.resolve(bound.story.profile).minimum_independent_proof_routes
        by_revelation: dict[str, set[str]] = {}
        for route in bound.realization_routes:
            by_revelation.setdefault(route.revelation.id, set()).update(item.kind for item in route.opportunities)
        diagnostics = tuple(
            f"revelation '{revelation.id}' has fewer than {minimum} independent opportunity kinds"
            for revelation in bound.revelations
            if revelation.required and len(by_revelation.get(revelation.id, set())) < minimum
        )
        return CausalCriticResult("route_fairness", not diagnostics, diagnostics)


class CausalCompletenessCritic:
    """Proves terminal truth -> route/evidence -> reachable opportunity chains."""

    def critique(self, story: CausalCompiledStory | BoundBlueprint) -> CausalCriticResult:
        bound = story if isinstance(story, BoundBlueprint) else bind_blueprint(story)
        end_truths = {truth.id for ending in bound.end_states for truth in ending.truths}
        route_truths = {truth.id for route in bound.realization_routes for truth in route.results}
        event_truths = {truth.id for event in bound.causal_events for truth in event.outputs}
        evidence_truths = {item.truth.id for item in bound.evidence_opportunities}
        diagnostics = tuple(
            f"terminal truth '{truth}' lacks a causal evidence/route chain"
            for truth in sorted(end_truths)
            if truth not in route_truths or truth not in event_truths or truth not in evidence_truths
        )
        return CausalCriticResult("causal_completeness", not diagnostics, diagnostics)


class FreytagProgressionCritic:
    def __init__(self, profiles: CausalProfileRegistry) -> None:
        self._profiles = profiles

    def critique(self, story: CausalCompiledStory | BoundBlueprint) -> CausalCriticResult:
        bound = story if isinstance(story, BoundBlueprint) else bind_blueprint(story)
        required = self._profiles.resolve(bound.story.profile).required_freytag_phases
        beat_order = {beat.id: index for index, beat in enumerate(bound.required_beats)}
        phase_order = {phase: index for index, phase in enumerate(required)}
        prior = -1
        diagnostics: list[str] = []
        for beat in bound.required_beats:
            position = phase_order.get(beat.declaration.phase)
            if position is None or position < prior:
                diagnostics.append(f"beat '{beat.id}' regresses Freytag progression")
            else:
                prior = position
            gated_beat_ids = (
                gate
                for revelation in bound.revelations
                if revelation.id in {item.id for item in beat.prerequisites}
                for gate in revelation.gates
            )
            if any(beat_order[gate.id] > beat_order[beat.id] for gate in gated_beat_ids):
                diagnostics.append(f"beat '{beat.id}' opens before a revelation gate")
        return CausalCriticResult("freytag_progression", not diagnostics, tuple(diagnostics))
