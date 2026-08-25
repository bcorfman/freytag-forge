"""Immutable, locally validated causal-story-v2 authoring contracts.

These declarations are offline authoring input.  They deliberately do not
describe runtime effects or mutable state.
"""

from __future__ import annotations

from collections.abc import Mapping
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, ValidationError

from storygame.authoring.bound_ir import BoundBlueprint, bind_blueprint
from storygame.authoring.symbol_resolution import SymbolRegistry, SymbolResolutionError

_ID = r"^[a-z][a-z0-9_]*$"


class CausalValidationError(ValueError):
    """A semantic rejection for an immutable causal candidate."""

    def __init__(self, code: str, detail: str) -> None:
        self.code = code
        self.detail = detail
        super().__init__(f"{code}: {detail}")


class _Contract(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)


class SourceProvenance(_Contract):
    source_format: Literal["story-outline-inventory-v1", "freytag-story-brief-v1"]
    source_id: str = Field(min_length=1, max_length=120)
    source_hash: str = Field(pattern=r"^[a-f0-9]{64}$")
    source_path: str | None = Field(default=None, min_length=1)
    source_schema_version: str | None = Field(default=None, min_length=1, max_length=80)
    provider: str | None = Field(default=None, min_length=1, max_length=80)
    model: str | None = Field(default=None, min_length=1, max_length=160)
    quality_tier: str | None = Field(default=None, min_length=1, max_length=32)
    generation_mode: Literal["standard", "debug"] | None = None
    response_id: str | None = Field(default=None, min_length=1, max_length=200)
    prompt_version: str | None = Field(default=None, min_length=1, max_length=80)
    validation_results: tuple[str, ...] = Field(default=(), max_length=64)


class Truth(_Contract):
    id: str = Field(pattern=_ID, max_length=80)
    summary: str = Field(min_length=1, max_length=600)
    roles: tuple[str, ...] = Field(default=(), max_length=16)


class Participant(_Contract):
    id: str = Field(pattern=_ID, max_length=80)
    role: str = Field(min_length=1, max_length=80)
    public_name: str | None = Field(default=None, min_length=1, max_length=160)
    public_role: str | None = Field(default=None, min_length=1, max_length=160)
    public_description: str | None = Field(default=None, min_length=1, max_length=1200)
    initial_location_id: str | None = Field(default=None, pattern=_ID, max_length=80)
    initial_availability: Literal["present", "away", "unavailable"] | None = None
    performance_profile_id: str | None = Field(default=None, pattern=_ID, max_length=80)
    movement_plan_ids: tuple[str, ...] = Field(default=(), max_length=32)


class NpcVoiceProfile(_Contract):
    model_config = ConfigDict(extra="forbid", frozen=True, serialize_by_alias=True)

    voice_register: str = Field(alias="register", serialization_alias="register", min_length=1, max_length=240)
    cadence: str = Field(min_length=1, max_length=240)
    diction: str = Field(min_length=1, max_length=240)
    avoidances: tuple[str, ...] = Field(default=(), max_length=16)


class NpcPerformanceProfile(_Contract):
    """Public performance guidance; never private motive or knowledge."""

    id: str = Field(pattern=_ID, max_length=80)
    participant_id: str = Field(pattern=_ID, max_length=80)
    public_manner: str = Field(min_length=1, max_length=600)
    voice: NpcVoiceProfile
    behavioral_cues: tuple[str, ...] = Field(min_length=1, max_length=16)


class Location(_Contract):
    id: str = Field(pattern=_ID, max_length=80)
    role: str = Field(min_length=1, max_length=80)
    initial_access: bool = False


class ConnectedRoute(_Contract):
    id: str = Field(pattern=_ID, max_length=80)
    from_location_id: str = Field(pattern=_ID, max_length=80)
    to_location_id: str = Field(pattern=_ID, max_length=80)
    aliases: tuple[str, ...] = Field(min_length=1, max_length=16)
    prerequisite_truths: tuple[str, ...] = Field(default=(), max_length=16)


class OpeningMetadata(_Contract):
    """Author/compiler output used to orient the player before ordinary turns."""

    scene: str = Field(min_length=1, max_length=1200)
    player_context: str = Field(min_length=1, max_length=1200)
    companions: tuple[str, ...] = Field(default=(), max_length=16)
    situation: str = Field(min_length=1, max_length=1600)
    next_steps: tuple[str, ...] = Field(min_length=1, max_length=16)
    protagonist_context: str | None = Field(default=None, max_length=1200)
    arrival_context: str | None = Field(default=None, max_length=1200)
    public_briefing: tuple[str, ...] = Field(default=(), max_length=32)
    scene_purpose: str | None = Field(default=None, max_length=1200)
    first_available_actions: tuple[str, ...] = Field(default=(), max_length=16)
    first_action_suggestions: tuple[OpeningSuggestion, ...] = Field(default=(), max_length=16)


class OpeningSuggestion(_Contract):
    """A declared first action and the current target that makes it actionable."""

    text: str = Field(min_length=1, max_length=600)
    target_kind: Literal["participant", "scene_subject", "evidence_realization", "group_encounter"]
    target_id: str = Field(pattern=_ID, max_length=80)


class CausalEvent(_Contract):
    id: str = Field(pattern=_ID, max_length=80)
    actor_ids: tuple[str, ...] = Field(min_length=1, max_length=16)
    location_id: str = Field(pattern=_ID, max_length=80)
    input_truths: tuple[str, ...] = Field(default=(), max_length=32)
    output_truths: tuple[str, ...] = Field(min_length=1, max_length=32)
    earliest: int = Field(ge=0, le=100000)
    latest: int = Field(ge=0, le=100000)
    prerequisite_event_ids: tuple[str, ...] = Field(default=(), max_length=32)


class TimelineConstraint(_Contract):
    before_event_id: str = Field(pattern=_ID, max_length=80)
    after_event_id: str = Field(pattern=_ID, max_length=80)


class EvidenceOpportunity(_Contract):
    id: str = Field(pattern=_ID, max_length=80)
    truth_id: str = Field(pattern=_ID, max_length=80)
    kind: str = Field(min_length=1, max_length=80)
    holder_id: str = Field(pattern=_ID, max_length=80)
    location_id: str = Field(pattern=_ID, max_length=80)
    supports: bool = True
    route_id: str = Field(pattern=_ID, max_length=80)


class NpcMovementPlan(_Contract):
    id: str = Field(pattern=_ID, max_length=80)
    participant_id: str = Field(pattern=_ID, max_length=80)
    source_location_id: str = Field(pattern=_ID, max_length=80)
    destination_location_id: str = Field(pattern=_ID, max_length=80)
    activation_truth_ids: tuple[str, ...] = Field(default=(), max_length=32)
    abort_truth_ids: tuple[str, ...] = Field(default=(), max_length=32)
    player_may_accompany: bool = False


class SceneSubject(_Contract):
    id: str = Field(pattern=_ID, max_length=80)
    kind: str = Field(min_length=1, max_length=80)
    location_id: str = Field(pattern=_ID, max_length=80)
    inspectable: bool
    public_description: str = Field(min_length=1, max_length=1200)
    evidence_opportunity_ids: tuple[str, ...] = Field(default=(), max_length=32)


class EvidenceRealization(_Contract):
    id: str = Field(pattern=_ID, max_length=80)
    evidence_opportunity_id: str = Field(pattern=_ID, max_length=80)
    kind: Literal["scene_evidence", "document", "testimony", "item"]
    location_id: str = Field(pattern=_ID, max_length=80)
    custody_holder_id: str | None = Field(default=None, pattern=_ID, max_length=80)
    scene_subject_id: str | None = Field(default=None, pattern=_ID, max_length=80)
    public_description: str = Field(min_length=1, max_length=1200)


class GroupEncounter(_Contract):
    id: str = Field(pattern=_ID, max_length=80)
    location_id: str = Field(pattern=_ID, max_length=80)
    label: str = Field(min_length=1, max_length=160)
    participant_ids: tuple[str, ...] = Field(min_length=2, max_length=32)
    introduction_truth_ids: tuple[str, ...] = Field(default=(), max_length=32)


class PartyKnowledge(_Contract):
    participant_id: str = Field(pattern=_ID, max_length=80)
    truth_ids: tuple[str, ...] = Field(default=(), max_length=64)


class KnowledgeProtection(_Contract):
    truth_id: str = Field(pattern=_ID, max_length=80)
    release_after_revelation_ids: tuple[str, ...] = Field(min_length=1, max_length=16)


class FailureForward(_Contract):
    consequence_truth_ids: tuple[str, ...] = Field(min_length=1, max_length=16)
    alternative_route_ids: tuple[str, ...] = Field(default=(), max_length=16)


class RealizationRoute(_Contract):
    id: str = Field(pattern=_ID, max_length=80)
    revelation_id: str = Field(pattern=_ID, max_length=80)
    opportunity_ids: tuple[str, ...] = Field(min_length=1, max_length=16)
    prerequisite_truths: tuple[str, ...] = Field(default=(), max_length=16)
    prerequisite_revelation_ids: tuple[str, ...] = Field(default=(), max_length=16)
    result_truth_ids: tuple[str, ...] = Field(min_length=1, max_length=16)
    failure_forward: FailureForward


class Revelation(_Contract):
    id: str = Field(pattern=_ID, max_length=80)
    truth_id: str = Field(pattern=_ID, max_length=80)
    required: bool = True
    gate_beat_ids: tuple[str, ...] = Field(default=(), max_length=16)


class RequiredOutcome(_Contract):
    id: str = Field(pattern=_ID, max_length=80)
    truth_id: str = Field(pattern=_ID, max_length=80)


class Beat(_Contract):
    id: str = Field(pattern=_ID, max_length=80)
    phase: str = Field(min_length=1, max_length=80)
    required_outcome_id: str | None = Field(default=None, pattern=_ID, max_length=80)
    prerequisite_revelation_ids: tuple[str, ...] = Field(default=(), max_length=16)
    pressure: int = Field(ge=0, le=100)


class OptionalBeat(Beat):
    purpose: Literal["alternative_satisfier", "complication", "relationship_development", "world_development"]


class PressureBand(_Contract):
    minimum: int = Field(ge=0, le=100)
    maximum: int = Field(ge=0, le=100)


class DramaticSpine(_Contract):
    active_conflict: str = Field(min_length=1, max_length=1200)
    central_question: str = Field(min_length=1, max_length=600)
    participant_role_requirements: tuple[str, ...] = Field(default=(), max_length=32)
    target_pressure: PressureBand
    completion_truth_ids: tuple[str, ...] = Field(min_length=1, max_length=32)


class StoryletAvailability(_Contract):
    required_truth_ids: tuple[str, ...] = Field(default=(), max_length=32)
    absent_truth_ids: tuple[str, ...] = Field(default=(), max_length=32)
    participant_ids: tuple[str, ...] = Field(default=(), max_length=32)
    location_ids: tuple[str, ...] = Field(default=(), max_length=32)
    pressure: PressureBand


class Consequence(_Contract):
    """An immutable, named template for later fact-policy realization."""

    id: str = Field(pattern=_ID, max_length=80)
    assert_truth_ids: tuple[str, ...] = Field(default=(), max_length=32)
    retract_truth_ids: tuple[str, ...] = Field(default=(), max_length=32)


class Storylet(_Contract):
    """A bounded dramatic situation, never a runtime command or mutable state."""

    id: str = Field(pattern=_ID, max_length=80)
    beat_id: str = Field(pattern=_ID, max_length=80)
    purpose: Literal[
        "investigation", "social_complication", "relationship", "conflict", "moral_choice", "transition", "reversal"
    ]
    route_family: str = Field(pattern=_ID, max_length=80)
    availability: StoryletAvailability
    priority: int = Field(ge=0, le=100)
    dramatic_question: str = Field(min_length=1, max_length=600)
    realization_modes: tuple[
        Literal["direct_action", "investigation", "negotiation", "dialogue", "observation", "travel", "conflict"], ...
    ] = Field(min_length=1, max_length=16)
    consequence_ids: tuple[str, ...] = Field(min_length=1, max_length=16)
    activation_truth_id: str = Field(pattern=_ID, max_length=80)
    completion_truth_id: str = Field(pattern=_ID, max_length=80)
    abort_truth_ids: tuple[str, ...] = Field(default=(), max_length=16)
    failure_forward_storylet_ids: tuple[str, ...] = Field(default=(), max_length=16)
    interaction_frame_ids: tuple[str, ...] = Field(default=(), max_length=16)


class InteractionFrame(_Contract):
    """Immutable dramatic guidance for a responsive, multi-turn exchange."""

    id: str = Field(pattern=_ID, max_length=80)
    storylet_id: str = Field(pattern=_ID, max_length=80)
    initiator_id: str = Field(pattern=_ID, max_length=80)
    participant_ids: tuple[str, ...] = Field(min_length=1, max_length=16)
    initiation: Literal["npc_initiated", "player_initiated", "either"]
    location_ids: tuple[str, ...] = Field(min_length=1, max_length=16)
    dramatic_objective: str = Field(min_length=1, max_length=600)
    opening_move: str = Field(min_length=1, max_length=600)
    response_obligations: tuple[str, ...] = Field(default=(), max_length=16)
    allowed_tactics: tuple[str, ...] = Field(default=(), max_length=16)
    agency_modes: tuple[Literal["engage", "refuse", "redirect", "interrupt", "depart"], ...] = Field(
        default=(), max_length=5
    )
    permitted_movement_plan_ids: tuple[str, ...] = Field(default=(), max_length=16)
    activation_truth_id: str = Field(pattern=_ID, max_length=80)
    continuation_truth_id: str = Field(pattern=_ID, max_length=80)
    completion_truth_id: str = Field(pattern=_ID, max_length=80)
    abort_truth_ids: tuple[str, ...] = Field(default=(), max_length=16)
    recent_use_truth_id: str = Field(pattern=_ID, max_length=80)
    failure_forward_frame_ids: tuple[str, ...] = Field(default=(), max_length=16)


class SuspectHypothesis(_Contract):
    participant_id: str = Field(pattern=_ID, max_length=80)
    supporting_truth_ids: tuple[str, ...] = Field(min_length=2, max_length=16)
    exonerating_truth_ids: tuple[str, ...] = Field(min_length=1, max_length=16)


class EndState(_Contract):
    id: str = Field(pattern=_ID, max_length=80)
    required_outcome_ids: tuple[str, ...] = Field(min_length=1, max_length=32)
    required_truth_ids: tuple[str, ...] = Field(min_length=1, max_length=32)


class CausalCompiledStory(_Contract):
    """The immutable story-blueprint-v2 candidate contract."""

    schema_version: Literal["story-blueprint-v2"]
    id: str = Field(pattern=_ID, max_length=80)
    version: int = Field(ge=1, le=9999)
    provenance: SourceProvenance
    genre: str = Field(min_length=1, max_length=80)
    profile: str = Field(min_length=1, max_length=80)
    title: str = Field(min_length=1, max_length=160)
    premise: str = Field(min_length=1, max_length=1200)
    opening_truth_ids: tuple[str, ...] = Field(default=(), max_length=64)
    opening: OpeningMetadata | None = None
    truths: tuple[Truth, ...] = Field(min_length=1, max_length=128)
    participants: tuple[Participant, ...] = Field(min_length=1, max_length=64)
    npc_performance_profiles: tuple[NpcPerformanceProfile, ...] = Field(default=(), max_length=64)
    locations: tuple[Location, ...] = Field(min_length=1, max_length=64)
    connected_routes: tuple[ConnectedRoute, ...] = Field(default=(), max_length=128)
    causal_events: tuple[CausalEvent, ...] = Field(min_length=1, max_length=128)
    timeline_constraints: tuple[TimelineConstraint, ...] = Field(default=(), max_length=128)
    evidence_opportunities: tuple[EvidenceOpportunity, ...] = Field(min_length=1, max_length=128)
    movement_plans: tuple[NpcMovementPlan, ...] = Field(default=(), max_length=128)
    scene_subjects: tuple[SceneSubject, ...] = Field(default=(), max_length=128)
    evidence_realizations: tuple[EvidenceRealization, ...] = Field(default=(), max_length=256)
    group_encounters: tuple[GroupEncounter, ...] = Field(default=(), max_length=64)
    party_knowledge: tuple[PartyKnowledge, ...] = Field(default=(), max_length=64)
    knowledge_protections: tuple[KnowledgeProtection, ...] = Field(default=(), max_length=64)
    revelations: tuple[Revelation, ...] = Field(min_length=1, max_length=64)
    realization_routes: tuple[RealizationRoute, ...] = Field(min_length=1, max_length=128)
    required_outcomes: tuple[RequiredOutcome, ...] = Field(min_length=1, max_length=64)
    required_beats: tuple[Beat, ...] = Field(min_length=1, max_length=64)
    optional_beats: tuple[OptionalBeat, ...] = Field(default=(), max_length=64)
    dramatic_spine: DramaticSpine | None = None
    consequences: tuple[Consequence, ...] = Field(default=(), max_length=128)
    storylets: tuple[Storylet, ...] = Field(default=(), max_length=256)
    interaction_frames: tuple[InteractionFrame, ...] = Field(default=(), max_length=256)
    suspect_hypotheses: tuple[SuspectHypothesis, ...] = Field(default=(), max_length=32)
    end_states: tuple[EndState, ...] = Field(min_length=1, max_length=16)


def _acyclic(nodes: set[str], edges: Mapping[str, tuple[str, ...]], code: str) -> None:
    visiting: set[str] = set()
    visited: set[str] = set()

    def visit(node: str) -> None:
        if node in visiting:
            raise CausalValidationError(code, f"graph contains '{node}'")
        if node not in visited:
            visiting.add(node)
            for dependency in edges[node]:
                visit(dependency)
            visiting.remove(node)
            visited.add(node)

    for node in nodes:
        visit(node)


def _as_bound(story: CausalCompiledStory | BoundBlueprint) -> BoundBlueprint:
    return story if isinstance(story, BoundBlueprint) else bind_blueprint(story)


def _validate_topology(bound: BoundBlueprint) -> None:
    story = bound.story
    for route in bound.connected_routes:
        if len(set(route.declaration.aliases)) != len(route.declaration.aliases):
            raise CausalValidationError("DUPLICATE_ALIAS", f"route '{route.id}' repeats an alias")
    if not any(location.declaration.initial_access for location in bound.locations):
        raise CausalValidationError("OPENING_LOCATION_REQUIRED", "one location needs initial access")
    aliases = [alias.casefold() for route in bound.connected_routes for alias in route.declaration.aliases]
    if len(aliases) != len(set(aliases)):
        raise CausalValidationError("DUPLICATE_ALIAS", "route aliases must be unique")
    _ = story


def _validate_events(bound: BoundBlueprint) -> None:
    event_ids = {event.id for event in bound.causal_events}
    for event in bound.causal_events:
        if event.declaration.earliest > event.declaration.latest:
            raise CausalValidationError("TIMELINE_INVALID", f"event '{event.id}' ends before it begins")
    _acyclic(
        event_ids,
        {event.id: tuple(item.id for item in event.prerequisites) for event in bound.causal_events},
        "CAUSAL_CYCLE",
    )
    infeasible: list[str] = []
    for constraint in bound.timeline_constraints:
        before = constraint.before
        after = constraint.after
        if before.declaration.latest > after.declaration.earliest:
            infeasible.append(f"{before.id}->{after.id}")
    if infeasible:
        raise CausalValidationError("TIMELINE_INVALID", f"infeasible timeline constraints: {', '.join(infeasible)}")


def _reachable_locations(bound: BoundBlueprint) -> set[str]:
    reachable = {location.id for location in bound.locations if location.declaration.initial_access}
    available_truths = {truth.id for truth in bound.opening_truths}
    changed = True
    while changed:
        changed = False
        for event in bound.causal_events:
            if {truth.id for truth in event.inputs} <= available_truths:
                new_truths = {truth.id for truth in event.outputs} - available_truths
                if new_truths:
                    available_truths.update(new_truths)
                    changed = True
        for route in bound.connected_routes:
            if (
                route.source.id in reachable
                and {truth.id for truth in route.prerequisites} <= available_truths
                and route.destination.id not in reachable
            ):
                reachable.add(route.destination.id)
                changed = True
            if (
                route.destination.id in reachable
                and {truth.id for truth in route.prerequisites} <= available_truths
                and route.source.id not in reachable
            ):
                reachable.add(route.source.id)
                changed = True
    return reachable


def _has_spatial_projection(story: CausalCompiledStory) -> bool:
    return any(
        (
            story.movement_plans,
            story.scene_subjects,
            story.evidence_realizations,
            story.group_encounters,
            story.opening is not None and story.opening.first_action_suggestions,
            any(participant.public_name is not None for participant in story.participants),
        )
    )


def _validate_participant_placements(bound: BoundBlueprint) -> None:
    incomplete = [
        participant.id
        for participant in bound.participants
        if None
        in (
            participant.declaration.public_name,
            participant.declaration.public_role,
            participant.declaration.public_description,
            participant.declaration.initial_location_id,
            participant.declaration.initial_availability,
        )
    ]
    if incomplete:
        raise CausalValidationError("SPATIAL_PLACEMENT_REQUIRED", ", ".join(sorted(incomplete)))
    names_by_location: dict[str, set[str]] = {}
    for participant in bound.participants:
        declaration = participant.declaration
        if declaration.initial_availability != "present":
            continue
        names = names_by_location.setdefault(declaration.initial_location_id, set())
        name = declaration.public_name.casefold()
        if name in names:
            raise CausalValidationError("DUPLICATE_PUBLIC_NAME", declaration.initial_location_id)
        names.add(name)


def _validate_movement_plans(bound: BoundBlueprint) -> None:
    reachable = _reachable_locations(bound)
    for plan in bound.movement_plans:
        if plan.source.id not in reachable or plan.destination.id not in reachable:
            raise CausalValidationError("MOVEMENT_UNREACHABLE", plan.id)


def _validate_evidence_realizations(bound: BoundBlueprint) -> None:
    expected_ids = {item.id for item in bound.evidence_opportunities}
    actual_ids = [item.opportunity.id for item in bound.evidence_realizations]
    if set(actual_ids) != expected_ids or len(actual_ids) != len(expected_ids):
        raise CausalValidationError("EVIDENCE_REALIZATION_REQUIRED", "each opportunity needs one realization")
    for realization in bound.evidence_realizations:
        if realization.location.id != realization.opportunity.location.id:
            raise CausalValidationError("CUSTODY_INCOMPATIBLE", realization.id)
        holder = realization.custody_holder
        if holder is not None and holder.id != realization.opportunity.holder.id:
            raise CausalValidationError("CUSTODY_INCOMPATIBLE", realization.id)
        if realization.declaration.kind == "scene_evidence" and realization.scene_subject is None:
            raise CausalValidationError("SCENE_SUBJECT_REQUIRED", realization.id)
        if realization.scene_subject is not None and realization.opportunity.id not in {
            item.id for item in realization.scene_subject.opportunities
        }:
            raise CausalValidationError("CUSTODY_INCOMPATIBLE", realization.id)


def _validate_group_encounters(bound: BoundBlueprint) -> None:
    for encounter in bound.group_encounters:
        for participant in encounter.participants:
            declaration = participant.declaration
            if (
                declaration.initial_availability != "present"
                or declaration.initial_location_id != encounter.location.id
            ):
                raise CausalValidationError("GROUP_MEMBER_ABSENT", f"{encounter.id}:{participant.id}")


def _initial_target_ids(bound: BoundBlueprint, namespace: str) -> set[str]:
    initial_locations = {item.id for item in bound.locations if item.declaration.initial_access}
    if namespace == "participant":
        return {
            item.id
            for item in bound.participants
            if item.declaration.initial_availability == "present"
            and item.declaration.initial_location_id in initial_locations
        }
    if namespace == "scene_subject":
        return {item.id for item in bound.scene_subjects if item.location.id in initial_locations}
    if namespace == "evidence_realization":
        return {item.id for item in bound.evidence_realizations if item.location.id in initial_locations}
    return {
        item.id
        for item in bound.group_encounters
        if item.location.id in initial_locations
        and all(
            participant.declaration.initial_availability == "present"
            and participant.declaration.initial_location_id == item.location.id
            for participant in item.participants
        )
    }


def _validate_opening_suggestions(bound: BoundBlueprint) -> None:
    opening = bound.story.opening
    assert opening is not None
    suggestions = opening.first_action_suggestions
    if opening.first_available_actions and not suggestions:
        raise CausalValidationError("OPENING_SUGGESTION_TARGET_REQUIRED", "first actions need declared targets")
    if {item.text for item in suggestions} != set(opening.first_available_actions):
        raise CausalValidationError("OPENING_SUGGESTION_TARGET_REQUIRED", "suggestions must cover first actions")
    for suggestion in suggestions:
        if suggestion.target_id not in _initial_target_ids(bound, suggestion.target_kind):
            raise CausalValidationError("OPENING_SUGGESTION_UNSUPPORTED", suggestion.target_id)


def _validate_public_boundary(bound: BoundBlueprint) -> None:
    protected = {item.truth.declaration.summary.casefold() for item in bound.protections}
    public_text = [
        field
        for participant in bound.participants
        for field in (
            participant.declaration.public_name,
            participant.declaration.public_role,
            participant.declaration.public_description,
        )
        if field is not None
    ]
    public_text.extend(item.declaration.public_description for item in bound.scene_subjects)
    public_text.extend(item.declaration.public_description for item in bound.evidence_realizations)
    public_text.extend(item.declaration.label for item in bound.group_encounters)
    if bound.story.opening is not None:
        public_text.extend(
            (
                bound.story.opening.scene,
                bound.story.opening.player_context,
                bound.story.opening.situation,
                *bound.story.opening.public_briefing,
                *(item.text for item in bound.story.opening.first_action_suggestions),
            )
        )
    if any(summary.rstrip(".!?") in text.casefold() for summary in protected for text in public_text):
        raise CausalValidationError("PROTECTED_PUBLIC_LEAK", "public spatial presentation repeats a protected truth")


def _validate_spatial_projection(bound: BoundBlueprint) -> None:
    if not _has_spatial_projection(bound.story):
        return
    _validate_participant_placements(bound)
    _validate_movement_plans(bound)
    _validate_evidence_realizations(bound)
    _validate_group_encounters(bound)
    _validate_opening_suggestions(bound)
    _validate_public_boundary(bound)


def _validate_authoring_graph(bound: BoundBlueprint) -> None:
    outcome_ids = {outcome.id for outcome in bound.outcomes}
    required_beat_ids = {beat.id for beat in bound.required_beats}
    optional_ids = {beat.id for beat in bound.optional_beats}
    if required_beat_ids & optional_ids:
        raise CausalValidationError("DUPLICATE_ID", "a beat cannot be required and optional")
    hypothesis_participants = [hypothesis.participant.id for hypothesis in bound.hypotheses]
    if len(hypothesis_participants) != len(set(hypothesis_participants)):
        raise CausalValidationError("DUPLICATE_ID", "suspect hypotheses repeat a participant")
    for hypothesis in bound.hypotheses:
        if {item.id for item in hypothesis.supporting_truths} & {item.id for item in hypothesis.exonerating_truths}:
            raise CausalValidationError(
                "SUSPECT_HYPOTHESIS_INVALID", f"suspect hypothesis '{hypothesis.participant.id}' reuses its evidence"
            )
    for route in bound.realization_routes:
        failure_completes_route = {item.id for item in route.failure_consequences} & {item.id for item in route.results}
        if not failure_completes_route and not route.alternatives:
            raise CausalValidationError("FAILURE_FORWARD_DEAD_END", f"route '{route.id}' cannot fail forward")
        if any(opportunity.route.id != route.id for opportunity in route.opportunities):
            raise CausalValidationError("CUSTODY_INCOMPATIBLE", f"route '{route.id}' does not hold its opportunity")
    incomplete_alternative_satisfiers = [
        optional.id
        for optional in bound.optional_beats
        if optional.declaration.purpose == "alternative_satisfier" and optional.outcome is None
    ]
    if incomplete_alternative_satisfiers:
        beat_list = ", ".join(f"'{beat_id}'" for beat_id in incomplete_alternative_satisfiers)
        raise CausalValidationError("OPTIONAL_BEAT_INCOMPLETE", f"optional beats {beat_list} need an outcome")
    required_outcomes = {beat.outcome.id for beat in bound.required_beats if beat.outcome is not None}
    for optional in bound.optional_beats:
        if optional.declaration.purpose == "alternative_satisfier" and (
            optional.outcome is None or optional.outcome.id not in required_outcomes
        ):
            raise CausalValidationError(
                "OPTIONAL_ONLY_REQUIRED_OUTCOME", f"optional beat '{optional.id}' is the sole route"
            )
    _validate_endings(bound, outcome_ids)


def _validate_storylets(story: CausalCompiledStory) -> None:
    """Prove storylet declarations are safe authoring data before review."""

    if story.dramatic_spine is None and (story.consequences or story.storylets):
        raise CausalValidationError("DRAMATIC_SPINE_REQUIRED", "storylets require a dramatic spine")
    if story.dramatic_spine is None:
        return
    if story.dramatic_spine.target_pressure.minimum > story.dramatic_spine.target_pressure.maximum:
        raise CausalValidationError("PRESSURE_BAND_INVALID", "dramatic spine pressure range is inverted")
    protected = {item.truth_id for item in story.knowledge_protections}
    consequences = {item.id: item for item in story.consequences}
    for consequence in story.consequences:
        if set(consequence.assert_truth_ids) & set(consequence.retract_truth_ids):
            raise CausalValidationError(
                "CONSEQUENCE_INVALID", f"consequence '{consequence.id}' both asserts and retracts a truth"
            )
    for storylet in story.storylets:
        availability = storylet.availability
        if availability.pressure.minimum > availability.pressure.maximum:
            raise CausalValidationError("PRESSURE_BAND_INVALID", f"storylet '{storylet.id}' pressure range is inverted")
        if set(availability.required_truth_ids) & set(availability.absent_truth_ids):
            raise CausalValidationError("STORYLET_UNSATISFIABLE", f"storylet '{storylet.id}' requires an absent truth")
        if protected & set((*availability.required_truth_ids, *availability.absent_truth_ids)):
            raise CausalValidationError(
                "STORYLET_PROTECTED", f"storylet '{storylet.id}' exposes a protected availability truth"
            )
        asserted = {
            truth_id
            for consequence_id in storylet.consequence_ids
            for truth_id in consequences[consequence_id].assert_truth_ids
        }
        if storylet.completion_truth_id not in asserted:
            raise CausalValidationError(
                "STORYLET_MARKER_INVALID", f"storylet '{storylet.id}' completion marker is not an asserted consequence"
            )
        if storylet.activation_truth_id not in set(availability.required_truth_ids):
            raise CausalValidationError(
                "STORYLET_MARKER_INVALID",
                f"storylet '{storylet.id}' activation marker is not required; add "
                f"'{storylet.activation_truth_id}' to availability.required_truth_ids",
            )
    _acyclic(
        {storylet.id for storylet in story.storylets},
        {storylet.id: storylet.failure_forward_storylet_ids for storylet in story.storylets},
        "STORYLET_FAILURE_CYCLE",
    )


def _validate_interactions(bound: BoundBlueprint) -> None:
    """Validate public performance and multi-turn dramatic-frame coherence."""

    story = bound.story
    if not bound.interaction_frames and not bound.npc_performance_profiles:
        return
    profiles = {item.id: item for item in bound.npc_performance_profiles}
    participants = {item.id: item for item in bound.participants}
    storylets = {item.id: item.declaration for item in bound.storylets}
    frames_by_id = {item.id: item for item in bound.interaction_frames}

    for profile in profiles.values():
        participant = profile.participant.declaration
        if participant.performance_profile_id is None:
            raise CausalValidationError("NPC_PROFILE_REQUIRED", participant.id)
        if participant.performance_profile_id != profile.id:
            raise CausalValidationError("NPC_PROFILE_MISMATCH", profile.id)
    for frame in bound.interaction_frames:
        declaration = frame.declaration
        storylet = storylets[frame.storylet.id]
        if "dialogue" not in storylet.realization_modes:
            raise CausalValidationError("INTERACTION_DIALOGUE_REQUIRED", frame.id)
        if frame.id not in storylet.interaction_frame_ids:
            raise CausalValidationError("INTERACTION_LINK_REQUIRED", frame.id)
        if frame.initiator.id not in {item.id for item in frame.participants}:
            raise CausalValidationError("INTERACTION_INITIATOR_INVALID", frame.id)
        if frame.initiator.id not in storylet.availability.participant_ids:
            raise CausalValidationError("INTERACTION_PARTICIPANT_INCOMPATIBLE", frame.id)
        if not {item.id for item in frame.locations} <= set(storylet.availability.location_ids):
            raise CausalValidationError("INTERACTION_LOCATION_INCOMPATIBLE", frame.id)
        for participant in frame.participants:
            profile_id = participant.declaration.performance_profile_id
            if profile_id is None or profile_id not in profiles:
                raise CausalValidationError("NPC_PROFILE_REQUIRED", participant.id)
            if profiles[profile_id].participant.id != participant.id:
                raise CausalValidationError("NPC_PROFILE_MISMATCH", participant.id)
        for plan in frame.permitted_movement_plans:
            if plan.participant.id != frame.initiator.id or plan.destination.id not in {
                item.id for item in frame.locations
            }:
                raise CausalValidationError("INTERACTION_MOVEMENT_UNREACHABLE", frame.id)
        markers = {
            frame.activation_truth.id,
            frame.continuation_truth.id,
            frame.completion_truth.id,
            frame.recent_use_truth.id,
            *(item.id for item in frame.abort_truths),
        }
        expected_marker_count = 4 + len(frame.abort_truths)
        if len(markers) != expected_marker_count:
            raise CausalValidationError(
                "INTERACTION_MARKER_INVALID",
                f"interaction frame '{frame.id}' activation, continuation, completion, recent-use, and abort "
                "truth IDs must be pairwise distinct",
            )
        if frame.activation_truth.id != storylet.activation_truth_id:
            raise CausalValidationError(
                "INTERACTION_MARKER_INVALID",
                f"interaction frame '{frame.id}' activation marker must equal its storylet activation marker",
            )
        if frame.completion_truth.id != storylet.completion_truth_id:
            raise CausalValidationError(
                "INTERACTION_MARKER_INVALID",
                f"interaction frame '{frame.id}' completion marker must equal its storylet completion marker",
            )
        if not {item.id for item in frame.abort_truths} <= set(storylet.abort_truth_ids):
            raise CausalValidationError(
                "INTERACTION_MARKER_INVALID",
                f"interaction frame '{frame.id}' abort markers must be a subset of its storylet abort markers",
            )
        if len(declaration.agency_modes) < 2 or not declaration.response_obligations:
            raise CausalValidationError(
                "INTERACTION_AGENCY_REQUIRED",
                f"interaction frame '{frame.id}' needs at least two agency modes and one response obligation",
            )
        if declaration.initiation in {"npc_initiated", "either"}:
            initiator = participants[frame.initiator.id].declaration
            present = initiator.initial_availability == "present" and initiator.initial_location_id in {
                item.id for item in frame.locations
            }
            movable = any(
                plan.participant.id == frame.initiator.id
                and plan.source.id == initiator.initial_location_id
                and plan.destination.id in {item.id for item in frame.locations}
                for plan in frame.permitted_movement_plans
            )
            if not present and not movable:
                raise CausalValidationError("INTERACTION_INITIATOR_UNAVAILABLE", frame.id)
            if not frame.abort_truths or not {"refuse", "interrupt", "depart"} & set(declaration.agency_modes):
                raise CausalValidationError(
                    "INTERACTION_AGENCY_REQUIRED",
                    f"interaction frame '{frame.id}' with initiation npc_initiated or either must declare at least "
                    "one abort_truth_id and allow refuse, interrupt, or depart",
                )

    for storylet in story.storylets:
        linked = {frame.id for frame in bound.interaction_frames if frame.storylet.id == storylet.id}
        if set(storylet.interaction_frame_ids) != linked:
            raise CausalValidationError("INTERACTION_LINK_REQUIRED", storylet.id)
        if "dialogue" in storylet.realization_modes and not storylet.interaction_frame_ids:
            raise CausalValidationError("INTERACTION_FRAME_REQUIRED", storylet.id)
    _acyclic(
        set(frames_by_id),
        {frame.id: frame.declaration.failure_forward_frame_ids for frame in bound.interaction_frames},
        "INTERACTION_FAILURE_CYCLE",
    )

    protected = {item.truth.declaration.summary.casefold().rstrip(".!?") for item in bound.protections}
    public_profile_text = [
        text
        for profile in bound.npc_performance_profiles
        for text in (
            profile.declaration.public_manner,
            profile.declaration.voice.voice_register,
            profile.declaration.voice.cadence,
            profile.declaration.voice.diction,
            *profile.declaration.voice.avoidances,
            *profile.declaration.behavioral_cues,
        )
    ]
    if any(summary in text.casefold() for summary in protected for text in public_profile_text):
        raise CausalValidationError("PROTECTED_PUBLIC_LEAK", "public performance profile repeats a protected truth")


def _validate_endings(bound: BoundBlueprint, outcome_ids: set[str]) -> None:
    for end_state in bound.end_states:
        if set(outcome_ids) - {outcome.id for outcome in end_state.outcomes}:
            raise CausalValidationError("ENDING_NOT_VIABLE", f"end state '{end_state.id}' omits an outcome")
        outcome_truth_ids = {outcome.truth.id for outcome in end_state.outcomes}
        required_truth_ids = {truth.id for truth in end_state.truths}
        if not outcome_truth_ids <= required_truth_ids:
            raise CausalValidationError(
                "ENDING_TRUTH_MISMATCH",
                f"end state '{end_state.id}' must require the truth for every required outcome",
            )


def validate_causal_compiled_story(payload: Mapping[str, object] | CausalCompiledStory) -> CausalCompiledStory:
    """Parse and prove generic structural/map/knowledge invariants locally."""

    try:
        story = payload if isinstance(payload, CausalCompiledStory) else CausalCompiledStory.model_validate(payload)
    except ValidationError as exc:
        diagnostics = tuple(
            f"{'.'.join(str(part) for part in error['loc'])}: {error['type']}" for error in exc.errors()[:20]
        )
        suffix = " (additional contract errors omitted)" if len(exc.errors()) > len(diagnostics) else ""
        raise CausalValidationError("CONTRACT_INVALID", f"{' ; '.join(diagnostics)}{suffix}") from exc
    try:
        registry = SymbolRegistry.from_story(story)
        registry.bind(SymbolRegistry.reference_sites(story))
    except SymbolResolutionError as exc:
        duplicate = any(item.code == "DUPLICATE_SYMBOL" for item in exc.diagnostics)
        code = "DUPLICATE_ID" if duplicate else "UNKNOWN_REFERENCE"
        if all(item.path.startswith("evidence_opportunities[") for item in exc.diagnostics):
            legacy = "invalid opportunity references: " + ", ".join(
                f"{story.evidence_opportunities[int(item.path.split('[', 1)[1].split(']', 1)[0])].id}."
                f"{item.path.rsplit('.', 1)[-1]}->{item.supplied_id}"
                for item in exc.diagnostics
            )
            detail = (
                legacy
                if all(item.path.endswith("].route_id") for item in exc.diagnostics)
                else legacy + "; " + "; ".join(item.render() for item in exc.diagnostics)
            )
        else:
            detail = "; ".join(item.render() for item in exc.diagnostics)
        if any(item.path.startswith("party_knowledge[") for item in exc.diagnostics):
            detail += "; party knowledge reference uses a foreign namespace; use the mapped declared truth ID"
        raise CausalValidationError(code, detail) from exc
    bound = bind_blueprint(story)
    _validate_topology(bound)
    _validate_events(bound)
    _validate_authoring_graph(bound)
    _validate_spatial_projection(bound)
    _validate_storylets(story)
    _validate_interactions(bound)
    reachable = _reachable_locations(bound)
    blocked = [item.id for item in bound.evidence_opportunities if item.location.id not in reachable]
    if blocked:
        raise CausalValidationError("LOCATION_UNREACHABLE", f"opportunities are unreachable: {', '.join(blocked)}")
    return story
