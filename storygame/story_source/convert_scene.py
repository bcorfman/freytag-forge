"""Convert package scene records into declarative scene and match documents."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from typing import Any

from storygame.story_package.models import StoryPackage


@dataclass(frozen=True)
class SceneResult:
    """The scene-owned documents produced by the legacy package converter."""

    scene_docs: dict[str, dict]
    match_docs: dict[str, dict]


def _plain(value: Any) -> Any:
    """Turn package models and tuples into ordinary nested Python values."""

    if hasattr(value, "model_dump"):
        return _plain(value.model_dump(mode="python"))
    if isinstance(value, Mapping):
        return {key: _plain(item) for key, item in value.items()}
    if isinstance(value, (tuple, list)):
        return [_plain(item) for item in value]
    return value


def _predicates(values: Sequence[Any]) -> dict[str, Any]:
    """Encode ordered package predicates in the source mapping form."""

    return {item.fact_id: item.equals for item in values}


def _operations(values: Sequence[Any]) -> dict[str, Any]:
    """Encode ordered route operations in the compiler's mapping form."""

    return {item.fact_id: "retract" if item.op == "retract" else item.value for item in values}


def _outline(scene: Any) -> list[dict[str, Any]]:
    """Copy the reader outline required to reconstruct ``Scene.beats``."""

    return [
        {"id": beat.id, "anchor": beat.anchor, "title": beat.title, "details": list(beat.details), "prose": beat.prose}
        for beat in scene.beats.values()
    ]


def _brief(scene: Any) -> str:
    """Copy the plot prose before the first beat heading for exact rendering."""

    marker = f"### Scene {scene.opening_beat.id} — {scene.opening_beat.title}"
    brief, separator, _ = scene.prose.partition(marker)
    return brief.rstrip() if separator else scene.prose


def _entry_additions(scene: Any) -> list[dict[str, Any]]:
    """Copy entry text additions as compiler predicates and text."""

    return [{"when": list(item.requires), "text": item.text} for item in scene.metadata.entry_variants]


def _pacing_beat(event: Any) -> dict[str, Any]:
    """Copy one pacing event, including every realization and effect."""

    record: dict[str, Any] = {
        "id": event.id,
        "at_turn": event.at_turn,
        "sets": _predicates(event.effects),
        "say": [
            {
                **({"when": _predicates(realization.when)} if realization.when else {}),
                "text": realization.text,
                "verbatim": realization.verbatim,
            }
            for realization in event.realizations
        ],
    }
    if event.when:
        record["when"] = _predicates(event.when)
    if event.trailing:
        record["trailing"] = True
    if event.transition_id is not None:
        record["exit"] = event.transition_id
    if not event.realizations:
        record.pop("say")
    return record


def _claim_record(claim: Any, *, commits_subset: Mapping[str, Any] | None = None) -> dict[str, Any]:
    """Copy package claim fields that the source knowledge compiler consumes."""

    record: dict[str, Any] = {
        "claim_id": claim.id,
        "says": claim.statement,
        "entities": list(claim.entity_ids),
        "reach": list(claim.reach_entity_ids),
        "relevance": {"entity_ids": list(claim.relevance.entity_ids), "priority": claim.relevance.priority},
        "audience": _plain(claim.audience),
        "voiceable": claim.voiceable,
        "repeatable": claim.repeatable,
    }
    if claim.earn_when is not None:
        record["earn_when"] = claim.earn_when
    if claim.delivery_text is not None:
        record["text"] = claim.delivery_text
    if claim.delivery_variants:
        record["text_when"] = [{"when": list(item.requires), "text": item.text} for item in claim.delivery_variants]
    if claim.speaker_text:
        record["speaker_text"] = dict(claim.speaker_text)
    if commits_subset is not None:
        record["commits_subset"] = dict(commits_subset)
    return record


def _match_record(claim: Any) -> dict[str, Any]:
    """Expand one package claim's matcher fields into a match-file entry."""

    record: dict[str, Any] = {"aliases": list(claim.aliases)}
    if claim.action_evidence:
        record["action_evidence"] = [list(group) for group in claim.action_evidence]
    if claim.must_convey:
        record["must_convey"] = [list(group) for group in claim.must_convey]
    if claim.leak_terms is not None:
        record["leak_terms"] = list(claim.leak_terms)
    return record


def _event_records(event: Any, kind: str, claims_by_event: Mapping[str, list[Any]]) -> list[dict[str, Any]]:
    """Copy one canonical event once per claim so every legacy claim remains sourceable."""

    record: dict[str, Any] = {
        "id": event.id,
        "kind": kind,
        "when": list(event.activation.all_facts_true),
        "commits": _operations(event.operations),
        "realized_by": [_handle(storylet_id) for storylet_id in event.realization_storylets],
    }
    if event.activation.any_of:
        record["when_any"] = list(event.activation.any_of)
    if event.activation.at_least:
        record["at_least"] = event.activation.at_least
    if event.fallback_text is not None:
        record["fallback_text"] = event.fallback_text
    if event.delivery_text is not None:
        record["delivery_text"] = event.delivery_text
    claims = claims_by_event.get(event.id, [])
    if not claims:
        return [record]
    return [
        {
            **record,
            **({} if index == 0 else {"id": f"{event.id}_claim_{claim.id}"}),
            "claim": _claim_record(claim, commits_subset=_operations(claim.establishes)),
        }
        for index, claim in enumerate(claims)
    ]


def _incident_record(incident: Any, outcome_claims: Mapping[tuple[str, str], str]) -> dict[str, Any]:
    """Copy one incident using source reveal handles and variant keys."""

    return {
        "id": incident.id,
        "reveal": _handle(incident.outcomes[0].storylet_id),
        "outcomes": [_variant_key(outcome.storylet_id, outcome.realization_id) for outcome in incident.outcomes],
        "recovery": _handle(incident.recovery_storylet_id),
        "missed_window": incident.missed_window_event_id,
        "observed_by": _observed_claims(incident, outcome_claims),
        **({"successor": incident.successor_transition_id} if incident.successor_transition_id else {}),
        **({} if incident.completes_scene else {"completes_scene": False}),
    }


def _observed_claims(incident: Any, outcome_claims: Mapping[tuple[str, str], str]) -> list[str]:
    """Keep legacy observation order and append any omitted outcome claims."""

    observed = list(incident.observation_knowledge_ids)
    for outcome in incident.outcomes:
        claim_id = outcome_claims.get((outcome.storylet_id, outcome.realization_id))
        if claim_id is not None and claim_id not in observed:
            observed.append(claim_id)
    return observed


def _handle(storylet_id: str) -> str:
    """Convert a legacy storylet ID into the contract's authoring handle."""

    return storylet_id.lower().replace("-", "_")


def _variant_key(storylet_id: str, realization_id: str) -> str:
    """Convert a legacy realization ID into its reveal-local variant key."""

    prefix = f"{storylet_id}-"
    suffix = realization_id[len(prefix) :] if realization_id.startswith(prefix) else realization_id
    return suffix.lower().replace("-", "_")


def _exit_record(transition: Any) -> dict[str, Any] | None:
    """Copy a scene transition in the declarative exit shape."""

    if transition is None:
        return None
    return {
        "id": transition.id,
        "to": transition.target_scene_id,
        "priority": transition.priority,
        "when_all": [trigger.fact_id for trigger in transition.triggers],
        "needs": [{"item": item, "relation": "exists"} for item in transition.required_dependencies],
    }


def _ending_record(ending: Any) -> dict[str, Any]:
    """Copy the sole package ending into the final scene document."""

    return {
        "when": _predicates(ending.when),
        "text": ending.text,
        "additions": [{"when": list(item.requires), "text": item.text} for item in ending.variants],
        "marker": ending.marker,
    }


def _owned_claims(package: StoryPackage) -> tuple[set[str], dict[str, Any]]:
    """Find entry, canonical-event, and incident-outcome claims owned here."""

    events = (*package.storylet_routes.bridge_events, *package.storylet_routes.resolution_events)
    event_ids = {event.id for event in events}
    outcomes = {
        (outcome.storylet_id, outcome.realization_id) for incident in package.incidents for outcome in incident.outcomes
    }
    owned: set[str] = set()
    claims: dict[str, Any] = {}
    for claim in package.knowledge.knowledge:
        source = claim.source
        if (
            source.kind == "scene_entry"
            or (source.kind == "canonical_route_event" and source.canonical_event_id in event_ids)
            or (source.kind == "storylet_realization" and (source.storylet_id, source.realization_id) in outcomes)
        ):
            owned.add(claim.id)
        if claim.id in owned:
            claims[claim.id] = claim
    return owned, claims


def _scene_doc(
    package: StoryPackage,
    scene: Any,
    event_claims: Mapping[str, list[Any]],
    outcome_claims: Mapping[tuple[str, str], str],
    ending: Any,
) -> dict:
    """Build one scene document in the contract's key order."""

    scene_id = scene.metadata.scene_id
    pacing = next(item for item in package.pacing.scenes if item.scene_id == scene_id)
    frame = next(item for item in package.knowledge.scene_frames if item.scene_id == scene_id)
    transition = next((item for item in package.pacing.transitions if item.source_scene_id == scene_id), None)
    bridges = [
        record
        for event in package.storylet_routes.bridge_events
        if event.scene_id == scene_id
        for record in _event_records(event, "bridge", event_claims)
    ]
    bridges.extend(
        record
        for event in package.storylet_routes.resolution_events
        if event.scene_id == scene_id
        for record in _event_records(event, "resolution", event_claims)
    )
    entry_claims = [
        _claim_record(claim)
        for claim in package.knowledge.knowledge
        if claim.source.kind == "scene_entry" and claim.available_in_scenes == (scene_id,)
    ]
    incidents = [_incident_record(item, outcome_claims) for item in package.incidents if item.scene_id == scene_id]
    document: dict[str, Any] = {
        "scene": scene_id,
        "location": scene.metadata.location_id,
        "objective": scene.metadata.objective,
        "freytag_phase": scene.metadata.freytag_phase,
        "situation": frame.situation,
        "pressure": frame.pressure,
        "turns": {"min": pacing.min_turns, "nudge": pacing.nudge_after_turns, "handoff": pacing.handoff_after_turns},
        "scripted_opening": scene.metadata.scripted_opening,
        "companions": list(scene.metadata.companions),
        "participants": list(scene.metadata.participant_ids),
        "items": list(scene.metadata.item_ids),
        "setting": list(scene.metadata.setting_facts),
        "prop_pool": list(scene.metadata.prop_pool),
        "entry": scene.metadata.entry_text,
        "entry_additions": _entry_additions(scene),
        "brief": _brief(scene),
        "outline": _outline(scene),
        "beats": [_pacing_beat(event) for event in package.pacing.events if event.scene_id == scene_id],
        "bridge": bridges,
        "incidents": incidents,
        "entry_claims": entry_claims,
    }
    if transition is not None:
        document["exit"] = {**_exit_record(transition), "bridge": scene.metadata.bridge_text[transition.id]}
    if ending is not None and ending.scene_id == scene_id:
        document["ending"] = _ending_record(ending)
    return document


def convert_scenes(package: StoryPackage) -> SceneResult:
    """Convert all package-owned scene records and matcher entries."""

    _, claims = _owned_claims(package)
    event_claims: dict[str, list[Any]] = {}
    for claim in claims.values():
        if claim.source.kind == "canonical_route_event":
            event_claims.setdefault(claim.source.canonical_event_id, []).append(claim)
    outcome_claims = {
        (claim.source.storylet_id, claim.source.realization_id): claim.id
        for claim in claims.values()
        if claim.source.kind == "storylet_realization"
        and any(
            (claim.source.storylet_id, claim.source.realization_id) == (outcome.storylet_id, outcome.realization_id)
            for incident in package.incidents
            for outcome in incident.outcomes
        )
    }
    scene_docs = {
        scene.metadata.scene_id: _scene_doc(package, scene, event_claims, outcome_claims, package.pacing.ending)
        for scene in package.scenes
    }
    match_docs: dict[str, dict] = {}
    for claim in claims.values():
        scene_id = claim.available_in_scenes[0]
        match_docs.setdefault(scene_id, {"claims": {}})["claims"][claim.id] = _match_record(claim)
    return SceneResult(scene_docs=scene_docs, match_docs=match_docs)
