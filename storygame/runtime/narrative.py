"""Immutable reviewed narrative packages and deterministic storylet selection."""

from __future__ import annotations

from dataclasses import dataclass

from storygame.authoring.causal_contracts import (
    CausalCompiledStory,
    ConnectedRoute,
    Consequence,
    DramaticSpine,
    EvidenceOpportunity,
    EvidenceRealization,
    GroupEncounter,
    InteractionFrame,
    KnowledgeProtection,
    Location,
    NpcMovementPlan,
    NpcPerformanceProfile,
    Participant,
    PartyKnowledge,
    SceneSubject,
    Storylet,
    Truth,
)
from storygame.authoring.contracts import CompiledStory
from storygame.runtime.facts import Fact, FactStore


@dataclass(frozen=True)
class RuntimeNarrativePackage:
    """Read-only reviewed declarations; facts remain the session authority."""

    source_id: str
    source_hash: str
    reviewed_candidate_sha256: str | None
    dramatic_spine: DramaticSpine | None
    truths: tuple[Truth, ...]
    participants: tuple[Participant, ...]
    npc_performance_profiles: tuple[NpcPerformanceProfile, ...]
    locations: tuple[Location, ...]
    connected_routes: tuple[ConnectedRoute, ...]
    movement_plans: tuple[NpcMovementPlan, ...]
    scene_subjects: tuple[SceneSubject, ...]
    evidence_opportunities: tuple[EvidenceOpportunity, ...]
    evidence_realizations: tuple[EvidenceRealization, ...]
    group_encounters: tuple[GroupEncounter, ...]
    party_knowledge: tuple[PartyKnowledge, ...]
    knowledge_protections: tuple[KnowledgeProtection, ...]
    storylets: tuple[Storylet, ...]
    consequences: tuple[Consequence, ...]
    interaction_frames: tuple[InteractionFrame, ...]
    protected_truth_ids: frozenset[str]
    opening_truth_ids: tuple[str, ...]


@dataclass(frozen=True)
class RuntimeNarrativeProjection:
    """Compatibility bridge carrying V1 data beside the full reviewed package."""

    compiled_story: CompiledStory
    narrative_package: RuntimeNarrativePackage


def narrative_package_from_story(
    story: CausalCompiledStory, *, reviewed_candidate_sha256: str | None = None
) -> RuntimeNarrativePackage:
    """Keep reviewed declarations immutable beside the mutable fact state."""

    return RuntimeNarrativePackage(
        source_id=story.provenance.source_id,
        source_hash=story.provenance.source_hash,
        reviewed_candidate_sha256=reviewed_candidate_sha256,
        dramatic_spine=story.dramatic_spine,
        truths=story.truths,
        participants=story.participants,
        npc_performance_profiles=story.npc_performance_profiles,
        locations=story.locations,
        connected_routes=story.connected_routes,
        movement_plans=story.movement_plans,
        scene_subjects=story.scene_subjects,
        evidence_opportunities=story.evidence_opportunities,
        evidence_realizations=story.evidence_realizations,
        group_encounters=story.group_encounters,
        party_knowledge=story.party_knowledge,
        knowledge_protections=story.knowledge_protections,
        storylets=story.storylets,
        consequences=story.consequences,
        interaction_frames=story.interaction_frames,
        protected_truth_ids=frozenset(item.truth_id for item in story.knowledge_protections),
        opening_truth_ids=story.opening_truth_ids,
    )


class StoryletSelector:
    """Read-only ranked eligibility query over one package and fact snapshot."""

    def __init__(self, package: RuntimeNarrativePackage | None, facts: FactStore) -> None:
        self.package = package
        self.facts = facts

    def select(self, *, active_beat_ids: tuple[str, ...], location_id: str, limit: int = 3) -> tuple[Storylet, ...]:
        package = self.package
        if package is None or limit <= 0:
            return ()
        pressure = _pressure(self.facts)
        eligible = [
            storylet
            for storylet in package.storylets
            if storylet.beat_id in active_beat_ids
            and location_id in storylet.availability.location_ids
            and _participants_present(self.facts, storylet.availability.participant_ids, location_id)
            and storylet.availability.pressure.minimum <= pressure <= storylet.availability.pressure.maximum
            and _truths_known(self.facts, storylet.availability.required_truth_ids)
            and not any(_truths_known(self.facts, (truth_id,)) for truth_id in storylet.availability.absent_truth_ids)
            and not _marker_is_true(self.facts, "storylet_completed", storylet.id)
            and not _marker_is_true(self.facts, "storylet_aborted", storylet.id)
        ]
        return tuple(
            sorted(
                eligible,
                key=lambda item: (
                    -_urgency(item, package, self.facts),
                    _marker_is_true(self.facts, "storylet_recently_used", item.id),
                    -item.priority,
                    item.id,
                ),
            )[:limit]
        )


def _truths_known(facts: FactStore, truth_ids: tuple[str, ...]) -> bool:
    return all(facts.has("knows", "player", truth_id) for truth_id in truth_ids)


def _participants_present(facts: FactStore, participant_ids: tuple[str, ...], location_id: str) -> bool:
    return all(facts.has("present", participant_id, location_id) for participant_id in participant_ids)


def _pressure(facts: FactStore) -> int:
    values = facts.matching("scene_pressure", "scene")
    return int(values[-1].value or "0") if values else 0


def _marker_is_true(facts: FactStore, predicate: str, storylet_id: str) -> bool:
    return facts.has(predicate, storylet_id, value="true")


def _urgency(storylet: Storylet, package: RuntimeNarrativePackage, facts: FactStore) -> int:
    return int(
        any(
            storylet.id in source.failure_forward_storylet_ids and _marker_is_true(facts, "storylet_aborted", source.id)
            for source in package.storylets
        )
    )


def seed_storylet_facts(package: RuntimeNarrativePackage, facts: FactStore) -> None:
    """Initialize explicit selection markers without making package data mutable."""

    for storylet in package.storylets:
        for predicate in (
            "storylet_active",
            "storylet_completed",
            "storylet_aborted",
            "storylet_discovered",
            "storylet_recently_used",
        ):
            facts.assert_fact(Fact(predicate=predicate, subject=storylet.id, value="false"))
    for frame in package.interaction_frames:
        for predicate in (
            "interaction_active",
            "interaction_completed",
            "interaction_aborted",
            "interaction_recently_used",
        ):
            facts.assert_fact(Fact(predicate=predicate, subject=frame.id, value="false"))
