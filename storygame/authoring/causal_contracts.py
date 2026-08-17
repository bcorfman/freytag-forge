"""Immutable, locally validated causal-story-v2 authoring contracts.

These declarations are offline authoring input.  They deliberately do not
describe runtime effects or mutable state.
"""

from __future__ import annotations

from collections.abc import Iterable, Mapping
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, ValidationError

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


class Truth(_Contract):
    id: str = Field(pattern=_ID, max_length=80)
    summary: str = Field(min_length=1, max_length=600)
    roles: tuple[str, ...] = Field(default=(), max_length=16)


class Participant(_Contract):
    id: str = Field(pattern=_ID, max_length=80)
    role: str = Field(min_length=1, max_length=80)


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


class EndState(_Contract):
    id: str = Field(pattern=_ID, max_length=80)
    required_outcome_ids: tuple[str, ...] = Field(min_length=1, max_length=32)
    required_truth_ids: tuple[str, ...] = Field(min_length=1, max_length=32)


class CausalCompiledStory(_Contract):
    """The Phase-1 ``story-blueprint-v2`` candidate contract."""

    schema_version: Literal["story-blueprint-v2"]
    id: str = Field(pattern=_ID, max_length=80)
    version: int = Field(ge=1, le=9999)
    provenance: SourceProvenance
    genre: str = Field(min_length=1, max_length=80)
    profile: str = Field(min_length=1, max_length=80)
    title: str = Field(min_length=1, max_length=160)
    premise: str = Field(min_length=1, max_length=1200)
    opening_truth_ids: tuple[str, ...] = Field(default=(), max_length=64)
    truths: tuple[Truth, ...] = Field(min_length=1, max_length=128)
    participants: tuple[Participant, ...] = Field(min_length=1, max_length=64)
    locations: tuple[Location, ...] = Field(min_length=1, max_length=64)
    connected_routes: tuple[ConnectedRoute, ...] = Field(default=(), max_length=128)
    causal_events: tuple[CausalEvent, ...] = Field(min_length=1, max_length=128)
    timeline_constraints: tuple[TimelineConstraint, ...] = Field(default=(), max_length=128)
    evidence_opportunities: tuple[EvidenceOpportunity, ...] = Field(min_length=1, max_length=128)
    party_knowledge: tuple[PartyKnowledge, ...] = Field(default=(), max_length=64)
    knowledge_protections: tuple[KnowledgeProtection, ...] = Field(default=(), max_length=64)
    revelations: tuple[Revelation, ...] = Field(min_length=1, max_length=64)
    realization_routes: tuple[RealizationRoute, ...] = Field(min_length=1, max_length=128)
    required_outcomes: tuple[RequiredOutcome, ...] = Field(min_length=1, max_length=64)
    required_beats: tuple[Beat, ...] = Field(min_length=1, max_length=64)
    optional_beats: tuple[OptionalBeat, ...] = Field(default=(), max_length=64)
    end_states: tuple[EndState, ...] = Field(min_length=1, max_length=16)


def _ids(values: Iterable[object], category: str) -> set[str]:
    seen: set[str] = set()
    for value in values:
        identifier = value.id  # type: ignore[attr-defined]
        if identifier in seen:
            raise CausalValidationError("DUPLICATE_ID", f"duplicate {category} id '{identifier}'")
        seen.add(identifier)
    return seen


def _references(values: Iterable[str], known: set[str], owner: str) -> None:
    missing = next((value for value in values if value not in known), None)
    if missing is not None:
        raise CausalValidationError("UNKNOWN_REFERENCE", f"{owner} references unknown '{missing}'")


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


def _validate_topology(story: CausalCompiledStory, truth_ids: set[str], location_ids: set[str]) -> None:
    route_ids = _ids(story.connected_routes, "connected route")
    for route in story.connected_routes:
        _references((route.from_location_id, route.to_location_id), location_ids, f"route '{route.id}'")
        _references(route.prerequisite_truths, truth_ids, f"route '{route.id}'")
        if len(set(route.aliases)) != len(route.aliases):
            raise CausalValidationError("DUPLICATE_ALIAS", f"route '{route.id}' repeats an alias")
    if not any(location.initial_access for location in story.locations):
        raise CausalValidationError("OPENING_LOCATION_REQUIRED", "one location needs initial access")
    aliases = [alias.casefold() for route in story.connected_routes for alias in route.aliases]
    if len(aliases) != len(set(aliases)):
        raise CausalValidationError("DUPLICATE_ALIAS", "route aliases must be unique")
    _ = route_ids


def _validate_events(
    story: CausalCompiledStory,
    truth_ids: set[str],
    participant_ids: set[str],
    location_ids: set[str],
) -> None:
    event_ids = _ids(story.causal_events, "causal event")
    for event in story.causal_events:
        _references(event.actor_ids, participant_ids, f"event '{event.id}'")
        _references((event.location_id,), location_ids, f"event '{event.id}'")
        _references((*event.input_truths, *event.output_truths), truth_ids, f"event '{event.id}'")
        _references(event.prerequisite_event_ids, event_ids, f"event '{event.id}'")
        if event.earliest > event.latest:
            raise CausalValidationError("TIMELINE_INVALID", f"event '{event.id}' ends before it begins")
    _acyclic(event_ids, {event.id: event.prerequisite_event_ids for event in story.causal_events}, "CAUSAL_CYCLE")
    by_id = {event.id: event for event in story.causal_events}
    for constraint in story.timeline_constraints:
        _references((constraint.before_event_id, constraint.after_event_id), event_ids, "timeline constraint")
        if by_id[constraint.before_event_id].latest > by_id[constraint.after_event_id].earliest:
            raise CausalValidationError("TIMELINE_INVALID", "timeline constraint has no feasible order")


def _reachable_locations(story: CausalCompiledStory) -> set[str]:
    reachable = {location.id for location in story.locations if location.initial_access}
    available_truths = set(story.opening_truth_ids)
    changed = True
    while changed:
        changed = False
        for event in story.causal_events:
            if set(event.input_truths) <= available_truths:
                new_truths = set(event.output_truths) - available_truths
                if new_truths:
                    available_truths.update(new_truths)
                    changed = True
        for route in story.connected_routes:
            if (
                route.from_location_id in reachable
                and set(route.prerequisite_truths) <= available_truths
                and route.to_location_id not in reachable
            ):
                reachable.add(route.to_location_id)
                changed = True
            if (
                route.to_location_id in reachable
                and set(route.prerequisite_truths) <= available_truths
                and route.from_location_id not in reachable
            ):
                reachable.add(route.from_location_id)
                changed = True
    return reachable


def _validate_authoring_graph(story: CausalCompiledStory, truth_ids: set[str], participant_ids: set[str]) -> None:
    route_ids = _ids(story.realization_routes, "realization route")
    revelation_ids = _ids(story.revelations, "revelation")
    outcome_ids = _ids(story.required_outcomes, "required outcome")
    required_beat_ids = _ids(story.required_beats, "required beat")
    optional_ids = _ids(story.optional_beats, "optional beat")
    if required_beat_ids & optional_ids:
        raise CausalValidationError("DUPLICATE_ID", "a beat cannot be required and optional")
    opportunity_ids = _ids(story.evidence_opportunities, "evidence opportunity")
    location_ids = {location.id for location in story.locations}
    for opportunity in story.evidence_opportunities:
        _references((opportunity.truth_id,), truth_ids, f"opportunity '{opportunity.id}'")
        _references((opportunity.holder_id,), participant_ids, f"opportunity '{opportunity.id}'")
        _references((opportunity.location_id,), location_ids, f"opportunity '{opportunity.id}'")
        _references((opportunity.route_id,), route_ids, f"opportunity '{opportunity.id}'")
    for knowledge in story.party_knowledge:
        _references((knowledge.participant_id,), participant_ids, "party knowledge")
        _references(knowledge.truth_ids, truth_ids, f"knowledge '{knowledge.participant_id}'")
    for protection in story.knowledge_protections:
        _references((protection.truth_id,), truth_ids, "knowledge protection")
        _references(protection.release_after_revelation_ids, revelation_ids, "knowledge protection")
    protected = {item.truth_id for item in story.knowledge_protections}
    for knowledge in story.party_knowledge:
        if protected & set(knowledge.truth_ids):
            raise CausalValidationError(
                "PREMATURE_PROTECTED_KNOWLEDGE", f"'{knowledge.participant_id}' knows protected truth"
            )
    for revelation in story.revelations:
        _references((revelation.truth_id,), truth_ids, f"revelation '{revelation.id}'")
        _references(revelation.gate_beat_ids, required_beat_ids, f"revelation '{revelation.id}'")
    for route in story.realization_routes:
        _references((route.revelation_id,), revelation_ids, f"route '{route.id}'")
        _references(route.opportunity_ids, opportunity_ids, f"route '{route.id}'")
        _references((*route.prerequisite_truths, *route.result_truth_ids), truth_ids, f"route '{route.id}'")
        _references(route.prerequisite_revelation_ids, revelation_ids, f"route '{route.id}'")
        _references(route.failure_forward.consequence_truth_ids, truth_ids, f"route '{route.id}' failure-forward")
        _references(route.failure_forward.alternative_route_ids, route_ids, f"route '{route.id}' failure-forward")
        failure_completes_route = set(route.failure_forward.consequence_truth_ids) & set(route.result_truth_ids)
        if not failure_completes_route and not route.failure_forward.alternative_route_ids:
            raise CausalValidationError("FAILURE_FORWARD_DEAD_END", f"route '{route.id}' cannot fail forward")
        selected_opportunities = (
            opportunity for opportunity in story.evidence_opportunities if opportunity.id in route.opportunity_ids
        )
        if any(opportunity.route_id != route.id for opportunity in selected_opportunities):
            raise CausalValidationError("CUSTODY_INCOMPATIBLE", f"route '{route.id}' does not hold its opportunity")
    for outcome in story.required_outcomes:
        _references((outcome.truth_id,), truth_ids, f"outcome '{outcome.id}'")
    for beat in (*story.required_beats, *story.optional_beats):
        _references(beat.prerequisite_revelation_ids, revelation_ids, f"beat '{beat.id}'")
        if beat.required_outcome_id is not None:
            _references((beat.required_outcome_id,), outcome_ids, f"beat '{beat.id}'")
    for optional in story.optional_beats:
        if optional.purpose == "alternative_satisfier" and optional.required_outcome_id is None:
            raise CausalValidationError("OPTIONAL_BEAT_INCOMPLETE", f"optional beat '{optional.id}' needs an outcome")
    required_outcomes = {beat.required_outcome_id for beat in story.required_beats}
    for optional in story.optional_beats:
        if optional.purpose == "alternative_satisfier" and optional.required_outcome_id not in required_outcomes:
            raise CausalValidationError(
                "OPTIONAL_ONLY_REQUIRED_OUTCOME", f"optional beat '{optional.id}' is the sole route"
            )
    _validate_endings(story, outcome_ids, truth_ids)


def _validate_endings(story: CausalCompiledStory, outcome_ids: set[str], truth_ids: set[str]) -> None:
    _ids(story.end_states, "end state")
    for end_state in story.end_states:
        _references(end_state.required_outcome_ids, outcome_ids, f"end state '{end_state.id}'")
        _references(end_state.required_truth_ids, truth_ids, f"end state '{end_state.id}'")
        if set(outcome_ids) - set(end_state.required_outcome_ids):
            raise CausalValidationError("ENDING_NOT_VIABLE", f"end state '{end_state.id}' omits an outcome")


def validate_causal_compiled_story(payload: Mapping[str, object] | CausalCompiledStory) -> CausalCompiledStory:
    """Parse and prove generic structural/map/knowledge invariants locally."""

    try:
        story = payload if isinstance(payload, CausalCompiledStory) else CausalCompiledStory.model_validate(payload)
    except ValidationError as exc:
        first = exc.errors()[0]
        path = ".".join(str(part) for part in first["loc"])
        raise CausalValidationError("CONTRACT_INVALID", f"{path}: {first['type']}") from exc
    truth_ids = _ids(story.truths, "truth")
    participant_ids = _ids(story.participants, "participant")
    location_ids = _ids(story.locations, "location")
    _references(story.opening_truth_ids, truth_ids, "opening")
    _validate_topology(story, truth_ids, location_ids)
    _validate_events(story, truth_ids, participant_ids, location_ids)
    _validate_authoring_graph(story, truth_ids, participant_ids)
    reachable = _reachable_locations(story)
    blocked = [item.id for item in story.evidence_opportunities if item.location_id not in reachable]
    if blocked:
        raise CausalValidationError("LOCATION_UNREACHABLE", f"opportunities are unreachable: {', '.join(blocked)}")
    return story
