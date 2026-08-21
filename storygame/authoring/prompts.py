"""Prompts for the offline compiled-story authoring boundary."""

from __future__ import annotations

import json
from collections.abc import Mapping


def build_compiler_prompt(outline: str, genre_profile: Mapping[str, object]) -> str:
    """Request the portable V2 authoring contract, not runtime facts or proposals."""

    profile = json.dumps(dict(genre_profile), sort_keys=True, separators=(",", ":"))
    return (
        "Return one JSON object only, labelled by this contract: COMPILED_STORY_JSON. "
        "Create an immutable compiled-story-v1 authoring input. Include stable IDs, "
        "characters, protected revelations, and required Freytag beats. Include at least "
        "one crisis, climax, and resolution; the climax must depend on earlier required work, "
        "and a resolution must answer the central question. Pacing thresholds must increase.\n"
        f"Genre profile: {profile}\nOutline: {outline.strip()}"
    )


def build_blueprint_compiler_prompt(
    outline: str,
    genre_profile: Mapping[str, object],
    source_provenance: Mapping[str, object],
    *,
    source_profile: str | None = None,
    diagnostics: tuple[Mapping[str, str], ...] = (),
) -> str:
    """Request an immutable, backwards-planned causal V2 blueprint."""

    profile = json.dumps(dict(genre_profile), sort_keys=True, separators=(",", ":"))
    provenance = json.dumps(dict(source_provenance), sort_keys=True, separators=(",", ":"))
    repair = ""
    if diagnostics:
        repair = (
            "\nRepair the candidate against these structured local diagnostics only. "
            "Do not change source provenance, weaken profile obligations, or remove obligations. "
            f"Diagnostics: {json.dumps(diagnostics, sort_keys=True, separators=(',', ':'))}"
        )
    return (
        "Return one JSON object only for the STORY_BLUEPRINT_V2_JSON contract. "
        "Do not wrap it in a STORY_BLUEPRINT_V2_JSON key. Its top-level keys must be "
        "schema_version, id, version, provenance, genre, profile, title, premise, opening_truth_ids, "
        "truths, participants, locations, connected_routes, causal_events, timeline_constraints, "
        "evidence_opportunities, party_knowledge, knowledge_protections, revelations, realization_routes, "
        "required_outcomes, required_beats, optional_beats, and end_states. "
        "Use JSON primitives exactly: JSON booleans must be the unquoted literals true or false; "
        "integer fields must be JSON numbers; and every plural field must be a JSON array, never a string. "
        "Every ID is lowercase snake_case. Required nested collection shapes (fields with ? are optional): "
        'truths: [{"id":"lowercase_id","summary":"non-empty summary","roles":["profile_role"]?}]; '
        "participants: [{id,role}]; locations: [{id,role,initial_access}]; "
        "connected_routes: [{id,from_location_id,to_location_id,aliases,prerequisite_truths?}]; "
        "causal_events: [{id,actor_ids,location_id,input_truths?,output_truths,earliest,latest,"
        "prerequisite_event_ids?}]; "
        "timeline_constraints: [{before_event_id,after_event_id}]; "
        "evidence_opportunities: [{id,truth_id,kind,holder_id,location_id,route_id}]; "
        "party_knowledge: [{participant_id,truth_ids?}]; "
        "knowledge_protections: [{truth_id,release_after_revelation_ids}]; "
        "revelations: [{id,truth_id,required?,gate_beat_ids?}]; "
        "realization_routes: [{id,revelation_id,opportunity_ids,result_truth_ids,failure_forward}], where "
        "failure_forward is {consequence_truth_ids,alternative_route_ids?}; "
        "evidence_opportunities[].route_id must equal a realization_routes[].id; it must never reference a "
        "connected_routes map-navigation ID. "
        "evidence_opportunities[].holder_id must equal a participants[].id, while location_id must equal a "
        "locations[].id; never use a location as an evidence holder. "
        "Every evidence_opportunity.location_id must be reachable from an initial_access location through "
        "connected_routes whose prerequisite_truths can be established; add an authored map connection or relocate "
        "the opportunity when necessary. "
        "Make connected_routes spatially coherent with the outline's setting: use setting-appropriate transition "
        "locations and layered travel between private interiors, local surroundings, and distant civic destinations; "
        "do not add implausible direct connections merely to satisfy reachability. "
        "required_outcomes: [{id,truth_id}]; "
        "required_beats: [{id,phase,pressure,required_outcome_id?,prerequisite_revelation_ids?}]; "
        "optional_beats: [{id,phase,pressure,purpose,required_outcome_id?,prerequisite_revelation_ids?}]; "
        "end_states: [{id,required_outcome_ids,required_truth_ids}]. "
        "For each timeline_constraint, before_event_id.latest must be less than or equal to "
        "after_event_id.earliest; do not declare a constraint for overlapping ranges. "
        "For every beat, pressure is an integer from 0 through 100, never a label. Required beats must include "
        "every required_freytag_phases value from the supplied genre profile. Optional-beat purpose is exactly one of "
        "alternative_satisfier, complication, relationship_development, or world_development. Before responding, "
        "verify every required field and cross-reference against this guide. "
        "Compile immutable story-blueprint-v2 authoring data, never runtime facts or executable effects. "
        "Plan in order: establish terminal truths; enumerate causal events and timeline; work backward "
        "to evidence, testimony, and reachable opportunities; bind them to concrete locations; then assign "
        "revelation gates and Freytag beats. "
        "For every profile-required revelation declare independently realizable proof routes, distinguish proof "
        "from suspicion, classify each beat as required, optional/substitutable, or an alternative satisfier, "
        "and provide bounded failure-forward consequences without prescribing player actions. "
        "Include the supplied source provenance unchanged. Local validation is authoritative.\n"
        f"Genre profile: {profile}\nSource profile ID: {source_profile or ''}\n"
        f"Source provenance: {provenance}\nOutline: {outline.strip()}{repair}"
    )
