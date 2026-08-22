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
    source_authoring_context: Mapping[str, object] | None = None,
    diagnostics: tuple[Mapping[str, str], ...] = (),
) -> str:
    """Request an immutable, backwards-planned causal V2 blueprint."""

    profile = json.dumps(dict(genre_profile), sort_keys=True, separators=(",", ":"))
    provenance = json.dumps(dict(source_provenance), sort_keys=True, separators=(",", ":"))
    authoring_context = json.dumps(dict(source_authoring_context or {}), sort_keys=True, separators=(",", ":"))
    repair = ""
    if diagnostics:
        repair = (
            "\nRepair the candidate against these structured local diagnostics only. "
            "Do not change source provenance, weaken profile obligations, or remove obligations. "
            "For causal_completeness, every named terminal truth must have all three links: "
            "a causal event output_truths entry, an evidence opportunity with that exact truth_id, "
            "and a realization route result_truths entry. The opportunity's route_id must point "
            "to a route that owns the opportunity and is bound to the revelation for that truth; "
            "if an existing route belongs to another revelation, add a matching route rather than "
            "leaving the truth on an unrelated route. For route_fairness, every named required "
            "revelation must have at least the profile minimum of distinct opportunity kinds across "
            "its own realization routes. Add independently owned opportunities and routes as needed; "
            "do not count routes assigned to a different revelation or duplicate one opportunity. "
            "For freytag_progression, gate_beat_ids are the beats at which a revelation becomes available. "
            "Every beat that lists a revelation in prerequisite_revelation_ids must come at or after every "
            "gate beat for that revelation in required-beat order; move the gate earlier or move the dependent "
            "beat later, while preserving the required Freytag phase order. Never use a later beat as the gate "
            "for a revelation required by an earlier beat. "
            f"Diagnostics: {json.dumps(diagnostics, sort_keys=True, separators=(',', ':'))}"
        )
    return (
        "Return one JSON object only for the STORY_BLUEPRINT_V2_JSON contract. "
        "Do not wrap it in a STORY_BLUEPRINT_V2_JSON key. Its top-level keys must be "
        "schema_version, id, version, provenance, genre, profile, title, premise, opening_truth_ids, "
        "truths, participants, locations, connected_routes, causal_events, timeline_constraints, "
        "evidence_opportunities, party_knowledge, knowledge_protections, revelations, realization_routes, "
        "required_outcomes, required_beats, optional_beats, suspect_hypotheses, and end_states. "
        "Use JSON primitives exactly: JSON booleans must be the unquoted literals true or false; "
        "integer fields must be JSON numbers; and every plural field must be a JSON array, never a string. "
        'schema_version must be the exact JSON string "story-blueprint-v2". '
        "profile must be the exact Source profile ID JSON string, never an object. "
        "Every ID is lowercase snake_case. Required nested collection shapes (fields with ? are optional): "
        'truths: [{"id":"lowercase_id","summary":"non-empty summary","roles":["profile_role"]?}]; '
        "participants: [{id,role}]; locations: [{id,role,initial_access}]; "
        "connected_routes: [{id,from_location_id,to_location_id,aliases,prerequisite_truths?}]; "
        "Every connected_routes[].prerequisite_truths value must be a declared truths[].id. Omit a prerequisite "
        "rather than inventing an access truth; include one only when the candidate already declares its truth. "
        "causal_events: [{id,actor_ids,location_id,input_truths?,output_truths,earliest,latest,"
        "prerequisite_event_ids?}]; "
        "timeline_constraints: [{before_event_id,after_event_id}]; "
        "evidence_opportunities: [{id,truth_id,kind,holder_id,location_id,route_id}]; "
        "party_knowledge: [{participant_id,truth_ids?}]; "
        "party_knowledge[].truth_ids may contain only values from truths[].id; never use an evidence opportunity ID, "
        "realization route ID, causal event ID, or participant ID in that field. "
        "knowledge_protections: [{truth_id,release_after_revelation_ids}]; "
        "revelations: [{id,truth_id,required?,gate_beat_ids?}]; "
        "realization_routes: [{id,revelation_id,opportunity_ids,result_truth_ids,failure_forward}], where "
        "failure_forward is {consequence_truth_ids,alternative_route_ids?}; "
        "Every failure_forward.consequence_truth_ids array must contain at least one declared truth ID. "
        "Every route's failure_forward must either establish at least one of that route's result_truth_ids or name an "
        "alternative realization route. "
        "evidence_opportunities[].route_id must equal a realization_routes[].id; it must never reference a "
        "connected_routes map-navigation ID. For each realization route, every ID in a realization route's "
        "opportunity_ids must name an evidence opportunity whose route_id equals that realization route's id. "
        "Treat opportunity ownership as a partition: do not list an opportunity on any other realization route, "
        "even when it supports the same revelation. Alternative-suspect supporting and exonerating opportunities "
        "must remain on that suspect's own playable routes; never add them to the actual culprit's terminal "
        "solution-synthesis routes. Preserve those alternative routes while repairing a terminal route. "
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
        "A revelation's gate_beat_ids identify beats at which that revelation becomes available. In required-beat "
        "order, every beat that lists that revelation in prerequisite_revelation_ids must be at or after every "
        "gate beat for it. Never gate a revelation at a later beat than a beat that requires it; move the gate "
        "earlier or move the dependent beat later while preserving required Freytag phase order. "
        "suspect_hypotheses: [{participant_id,supporting_truth_ids,exonerating_truth_ids}]; "
        "end_states: [{id,required_outcome_ids,required_truth_ids}], where every end state has at least one "
        "required_outcome_id and at least one required_truth_id; omit a nonviable end state rather than emitting "
        "empty arrays. "
        "For each timeline_constraint, before_event_id.latest must be less than or equal to "
        "after_event_id.earliest; do not declare a constraint for overlapping ranges. "
        "Timeline constraints must agree with causal_events[].prerequisite_event_ids: if an event lists another "
        "event as a prerequisite, the prerequisite must occur first and no timeline constraint may reverse that "
        "ordering. "
        "For every beat, pressure is an integer from 0 through 100, never a label. Required beats must include "
        "every required_freytag_phases value from the supplied genre profile. Optional-beat purpose is exactly one of "
        "alternative_satisfier, complication, relationship_development, or world_development. A required outcome "
        "may be assigned to an alternative_satisfier optional beat only when at least one required beat also names "
        "that outcome. It is mandatory on every optional beat whose purpose is alternative_satisfier; never omit "
        "required_outcome_id from one of those beats. A plausible alternative suspect is not automatically an "
        "alternative_satisfier: use complication or another appropriate optional purpose unless the beat truly "
        "provides an alternate way to satisfy a declared required outcome. Before responding, "
        "verify every required field and cross-reference against this guide. "
        "Compile immutable story-blueprint-v2 authoring data, never runtime facts or executable effects. "
        "Plan in order: establish terminal truths; enumerate causal events and timeline; work backward "
        "to evidence, testimony, and reachable opportunities; bind them to concrete locations; then assign "
        "revelation gates and Freytag beats. "
        "For every profile-required revelation declare independently realizable proof routes, distinguish proof "
        "from suspicion. For every required revelation, use at least the genre profile's minimum number of distinct "
        "evidence opportunity kinds across its realization routes. Classify each beat as required, "
        "optional/substitutable, or an alternative satisfier, "
        "and provide bounded failure-forward consequences without prescribing player actions. "
        "When the genre profile requires alternative suspects, declare that many distinct suspect_hypotheses. Each "
        "must name two or more playable supporting truths that make the participant seem culpable and separate "
        "playable exonerating truths that later disprove the hypothesis. These routes establish plausible false "
        "solutions; they are not additional proof of the terminal culprit solution. "
        "Every end_states[].required_truth_ids value must appear verbatim in at least one causal event output_truths, "
        "evidence opportunity truth_id, and realization route result_truth_ids. "
        "Hard constraints are non-negotiable: preserve every declared identity, event, causal fact, and required "
        "outcome; do not substitute alternative names, motives, methods, or resolutions. "
        "Authoring controls are instructions, never diegetic story content: do not make a blueprint, candidate, "
        "review, compiler, prompt, source provenance, or reviewed causal artifact into a fictional truth, clue, "
        "location, participant, route, or resolution. "
        "Include the supplied source provenance unchanged. Local validation is authoritative.\n"
        f"Genre profile: {profile}\nSource profile ID: {source_profile or ''}\n"
        f"Source provenance: {provenance}\nSource authoring context: {authoring_context}\n"
        f"Outline: {outline.strip()}{repair}"
    )
