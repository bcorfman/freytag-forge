"""Local, deterministic reviewers for immutable causal candidates."""

from __future__ import annotations

from dataclasses import dataclass

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

    def critique(self, story: CausalCompiledStory) -> CausalCriticResult:
        minimum = self._profiles.resolve(story.profile).minimum_independent_proof_routes
        by_revelation: dict[str, set[str]] = {}
        opportunities = {item.id: item for item in story.evidence_opportunities}
        for route in story.realization_routes:
            by_revelation.setdefault(route.revelation_id, set()).update(
                opportunities[item].kind for item in route.opportunity_ids
            )
        diagnostics = tuple(
            f"revelation '{revelation.id}' has fewer than {minimum} independent opportunity kinds"
            for revelation in story.revelations
            if revelation.required and len(by_revelation.get(revelation.id, set())) < minimum
        )
        return CausalCriticResult("route_fairness", not diagnostics, diagnostics)


class CausalCompletenessCritic:
    """Proves terminal truth -> route/evidence -> reachable opportunity chains."""

    def critique(self, story: CausalCompiledStory) -> CausalCriticResult:
        end_truths = {truth for ending in story.end_states for truth in ending.required_truth_ids}
        route_truths = {truth for route in story.realization_routes for truth in route.result_truth_ids}
        event_truths = {truth for event in story.causal_events for truth in event.output_truths}
        evidence_truths = {item.truth_id for item in story.evidence_opportunities}
        diagnostics = tuple(
            f"terminal truth '{truth}' lacks a causal evidence/route chain"
            for truth in sorted(end_truths)
            if truth not in route_truths or truth not in event_truths or truth not in evidence_truths
        )
        return CausalCriticResult("causal_completeness", not diagnostics, diagnostics)


class FreytagProgressionCritic:
    def __init__(self, profiles: CausalProfileRegistry) -> None:
        self._profiles = profiles

    def critique(self, story: CausalCompiledStory) -> CausalCriticResult:
        required = self._profiles.resolve(story.profile).required_freytag_phases
        beats = {beat.id: beat for beat in story.required_beats}
        phase_order = {phase: index for index, phase in enumerate(required)}
        prior = -1
        diagnostics: list[str] = []
        for beat in story.required_beats:
            position = phase_order.get(beat.phase)
            if position is None or position < prior:
                diagnostics.append(f"beat '{beat.id}' regresses Freytag progression")
            else:
                prior = position
            gated_beat_ids = (
                gate
                for revelation in story.revelations
                if revelation.id in beat.prerequisite_revelation_ids
                for gate in revelation.gate_beat_ids
            )
            if any(beats[gate].pressure > beat.pressure for gate in gated_beat_ids):
                diagnostics.append(f"beat '{beat.id}' opens before a revelation gate")
        return CausalCriticResult("freytag_progression", not diagnostics, tuple(diagnostics))
