"""Convert package storylet routes and knowledge claims to source documents."""

from __future__ import annotations

from collections import defaultdict
from collections.abc import Mapping
from dataclasses import dataclass

from storygame.story_package.models import KnowledgeDefinition, RouteRealization, StoryPackage


@dataclass(frozen=True)
class RevealsResult:
    """The scene and matcher documents owned by the reveals converter."""

    scene_docs: dict[str, dict]
    match_docs: dict[str, dict]


def _operation_map(operations: tuple) -> dict[str, object]:
    """Render route operations in the mapping form consumed by the compiler."""

    result: dict[str, object] = {}
    for operation in operations:
        result[operation.fact_id] = "retract" if operation.op == "retract" else operation.value
    return result


def _predicate_map(predicates: tuple) -> dict[str, object]:
    """Render ordered package predicates as an explicit source mapping."""

    return {predicate.fact_id: predicate.equals for predicate in predicates}


def _audience(value) -> dict[str, object]:
    """Render every audience field because the compact public form is lossy."""

    return {
        "kind": value.kind,
        "character_ids": list(value.character_ids),
        "player_visible": value.player_visible,
    }


def _relevance(value) -> dict[str, object]:
    """Render relevance without deriving its entities from another field."""

    return {"entity_ids": list(value.entity_ids), "priority": value.priority}


def _delivery_variants(claim: KnowledgeDefinition) -> list[dict[str, object]]:
    """Render delivery alternatives using the compiler's all-true list form."""

    return [{"when": list(item.requires), "text": item.text} for item in claim.delivery_variants]


def _claim_fields(claim: KnowledgeDefinition, route_commits: Mapping[str, object]) -> dict[str, object]:
    """Render the claim fields which the reveal compiler reads."""

    fields: dict[str, object] = {
        "claim_id": claim.id,
        "says": claim.statement,
        "entities": list(claim.entity_ids),
        "reach": list(claim.reach_entity_ids),
        "relevance": _relevance(claim.relevance),
        "audience": _audience(claim.audience),
        "voiceable": claim.voiceable,
        "repeatable": claim.repeatable,
    }
    if claim.requires:
        fields["when"] = _predicate_map(claim.requires)
    if claim.delivery_text is not None:
        fields["text"] = claim.delivery_text
    if claim.delivery_variants:
        fields["text_when"] = _delivery_variants(claim)
    if claim.speaker_text:
        fields["speaker_text"] = dict(claim.speaker_text)
    if claim.earn_when is not None:
        fields["earn_when"] = claim.earn_when
    establishes = _operation_map(claim.establishes)
    if establishes != dict(route_commits):
        fields["commits_subset"] = establishes
    return fields


def _skipped_claim_ids(package: StoryPackage) -> set[str]:
    """Return incident observation claims owned by the incidents worker."""

    return {claim_id for incident in package.incidents for claim_id in incident.observation_knowledge_ids}


def _claims_by_source(package: StoryPackage, skipped: set[str]) -> dict[tuple[str, str], list[KnowledgeDefinition]]:
    """Group eligible realization claims while retaining package claim order."""

    grouped: dict[tuple[str, str], list[KnowledgeDefinition]] = defaultdict(list)
    for claim in package.knowledge.knowledge:
        source = claim.source
        if source.kind == "storylet_realization" and claim.id not in skipped:
            grouped[(source.storylet_id, source.realization_id)].append(claim)
    return grouped


def _variant(
    realization: RouteRealization,
    claims: list[KnowledgeDefinition],
) -> dict[str, object]:
    """Render one realization and its primary and extra claim records."""

    commits = _operation_map(realization.operations)
    result: dict[str, object] = {
        "realization_id": realization.id,
        "intent": realization.dramatic_intent,
        "commits": commits,
        "from_outline": list(realization.source_beats),
        "helps_exit": list(realization.helps_transition_triggers),
    }
    if claims:
        result.update(_claim_fields(claims[0], commits))
        if len(claims) > 1:
            result["extra_claims"] = [_claim_fields(claim, commits) for claim in claims[1:]]
    return result


def _reveal(route, storylet, claims: Mapping[tuple[str, str], list[KnowledgeDefinition]]) -> dict[str, object]:
    """Render one reveal from its route, reader record, and realization claims."""

    first_boundaries = list(route.realizations[0].protected_knowledge_boundaries)
    guidance: dict[str, object] = {
        "pressure_role": route.pressure_role,
        "window": {
            "earliest_turn": route.earliest_turn,
            "target_turn": route.target_turn,
            "latest_turn": route.latest_turn,
        },
        "available_while": _predicate_map(route.activation_conditions),
        "boundaries": first_boundaries,
    }
    variants = {
        realization.id: _variant(
            realization,
            claims.get((route.id, realization.id), []),
        )
        for realization in route.realizations
    }
    return {
        "id": route.id,
        "storylet_id": route.id,
        "title": route.title,
        "guidance": guidance,
        "from_outline": list(storylet.source_links),
        "variants": variants,
    }


def _match_claim(claim: KnowledgeDefinition) -> dict[str, object]:
    """Render expanded matcher values for one knowledge claim."""

    result: dict[str, object] = {
        "aliases": list(claim.aliases),
        "action_evidence": [list(group) for group in claim.action_evidence],
        "must_convey": [list(group) for group in claim.must_convey],
    }
    if claim.leak_terms is not None:
        result["leak_terms"] = list(claim.leak_terms)
    return result


def _match_documents(package: StoryPackage, route_by_id: Mapping[str, object], skipped: set[str]) -> dict[str, dict]:
    """Build match documents in package knowledge and delivery order."""

    claims_by_scene: dict[str, dict[str, dict[str, object]]] = defaultdict(dict)
    for claim in package.knowledge.knowledge:
        source = claim.source
        if source.kind != "storylet_realization" or claim.id in skipped:
            continue
        route = route_by_id[source.storylet_id]
        claims_by_scene[route.scene_id][claim.id] = _match_claim(claim)

    deliveries_by_scene: dict[str, dict[str, dict[str, object]]] = defaultdict(dict)
    for delivery in package.deliveries:
        deliveries_by_scene[delivery.scene_id][delivery.fact_id] = {
            "must_convey": [list(group) for group in delivery.must_convey]
        }

    result: dict[str, dict] = {}
    for scene in package.scenes:
        scene_id = scene.metadata.scene_id
        document: dict[str, object] = {"schema": 1, "scene": scene_id, "claims": claims_by_scene[scene_id]}
        if deliveries_by_scene[scene_id]:
            document["deliveries"] = deliveries_by_scene[scene_id]
        result[scene_id] = document
    return result


def convert_reveals(package: StoryPackage) -> RevealsResult:
    """Convert runtime storylets, realizations, claims, and matchers to source data."""

    storylets = {storylet.id: storylet for storylet in package.storylets}
    routes = {route.id: route for route in package.storylet_routes.storylets}
    skipped = _skipped_claim_ids(package)
    claims = _claims_by_source(package, skipped)
    scene_docs: dict[str, dict] = {scene.metadata.scene_id: {"reveals": []} for scene in package.scenes}
    for route in package.storylet_routes.storylets:
        scene_docs[route.scene_id]["reveals"].append(_reveal(route, storylets[route.id], claims))
    return RevealsResult(
        scene_docs=scene_docs,
        match_docs=_match_documents(package, routes, skipped),
    )
