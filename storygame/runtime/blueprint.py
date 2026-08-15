"""Fact-backed runtime realization for immutable authoring blueprints.

The blueprint remains immutable.  This module stores only runtime discoveries,
route availability, clocks, and completed revelations in one mutable fact map.
"""

from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass
from typing import Any

from storygame.authoring.blueprint_contracts import RealizationRoute, StoryBlueprint
from storygame.runtime.contracts import BeatUpdate


@dataclass(frozen=True)
class RouteCommit:
    route_id: str
    failed: bool


@dataclass
class BlueprintRuntime:
    blueprint: StoryBlueprint
    facts: dict[str, Any]

    @property
    def player_truths(self) -> set[str]:
        return self.facts["player_truths"]

    @property
    def completed_revelations(self) -> set[str]:
        return self.facts["completed_revelations"]

    def snapshot(self) -> dict[str, Any]:
        return deepcopy(self.facts)

    def legal_routes(self) -> tuple[RealizationRoute, ...]:
        revelations = {item.id: item for item in self.blueprint.revelations}
        return tuple(
            route
            for route in self.blueprint.realization_routes
            if set(route.availability_constraints) <= self.player_truths
            and set(revelations[route.revelation_id].prerequisite_truths) <= self.player_truths
            and set(revelations[route.revelation_id].prerequisite_revelations) <= self.completed_revelations
        )


def realize_blueprint(blueprint: StoryBlueprint) -> BlueprintRuntime:
    """Realize validated authoring declarations into the canonical fact map."""
    facts: dict[str, Any] = {truth.id: truth.summary for truth in blueprint.canonical_truths}
    facts.update(
        player_truths=set(),
        completed_revelations=set(),
        completed_beats=set(),
        available_evidence={placement.id for placement in blueprint.evidence_placements},
        evidence_custody={placement.id: placement.custody for placement in blueprint.evidence_placements},
        scene_state={"location_classes": set()},
        relationships={},
        route_history=[],
        clocks={clock.id: 0 for clock in blueprint.opposition_clocks},
        participant_knowledge={item.party_id: set(item.known_truths) for item in blueprint.participant_knowledge},
    )
    return BlueprintRuntime(blueprint=blueprint, facts=facts)


def blueprint_observer_context(runtime: BlueprintRuntime, observer_id: str) -> dict[str, Any]:
    """Return only observer-earned truths and currently legal route metadata."""
    known = (
        runtime.player_truths
        if observer_id == "player"
        else runtime.facts["participant_knowledge"].get(observer_id, set())
    )
    protected_truths = {item.truth_id for item in runtime.blueprint.protected_facts}
    visible = sorted(
        truth_id
        for truth_id in known
        if truth_id not in protected_truths or truth_id in runtime.player_truths
    )
    return {
        "known_truth_ids": visible,
        "legal_routes": [
            {"id": route.id, "revelation_id": route.revelation_id, "role": route.role}
            for route in runtime.legal_routes()
        ],
    }


class ProgressionValidator:
    """Validates declared route completion before atomically replacing facts."""

    def __init__(self, runtime: BlueprintRuntime) -> None:
        self.runtime = runtime

    def commit(self, update: BeatUpdate, *, failed: bool = False) -> RouteCommit:
        route_id = update.route_id
        if not route_id:
            raise ValueError("blueprint progression requires route_id")
        route = next((item for item in self.runtime.legal_routes() if item.id == route_id), None)
        if route is None:
            raise ValueError(f"route '{route_id}' is unavailable or undeclared")
        beat = next((item for item in self.runtime.blueprint.required_beats if item.id == update.beat_id), None)
        if beat is None or route.revelation_id not in beat.revelation_dependencies:
            raise ValueError(f"route '{route_id}' cannot complete beat '{update.beat_id}'")
        self._validate_evidence(route, update.evidence_ids)
        candidate = self.runtime.snapshot()
        truths = route.failure_forward.result_truths if failed else tuple(
            item.truth_id for item in route.satisfiers if item.operator == "establish"
        )
        candidate["player_truths"].update(truths)
        revelation = next(item for item in self.runtime.blueprint.revelations if item.id == route.revelation_id)
        if set(revelation.completion_conditions) <= candidate["player_truths"]:
            candidate["completed_revelations"].add(revelation.id)
        if all(dependency in candidate["completed_revelations"] for dependency in beat.revelation_dependencies):
            candidate["completed_beats"].add(beat.id)
        candidate["route_history"].append(RouteCommit(route.id, failed))
        self.runtime.facts = candidate
        return RouteCommit(route.id, failed)

    def _validate_evidence(self, route: RealizationRoute, evidence_ids: tuple[str, ...]) -> None:
        available = self.runtime.facts["available_evidence"]
        if not set(evidence_ids) <= available:
            raise ValueError("evidence_ids contains unavailable evidence")
        if evidence_ids:
            evidence_truths = {
                placement.truth_id
                for placement in self.runtime.blueprint.evidence_placements
                if placement.id in evidence_ids
            }
            route_truths = {item.truth_id for item in route.satisfiers}
            if not evidence_truths <= route_truths:
                raise ValueError("evidence_ids does not support the selected route")
