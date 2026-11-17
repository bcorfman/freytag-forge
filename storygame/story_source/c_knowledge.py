"""Compile storylets, claims, canonical events, incidents, and deliveries."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from typing import Any

from storygame.story_package.models import (
    ActivationRule,
    CanonicalRouteEvent,
    DeliveryVariant,
    FactDelivery,
    Incident,
    IncidentOutcome,
    KnowledgeDefinition,
    Relevance,
    RevealSource,
    RouteOperation,
    RouteRealization,
    Storylet,
    StoryletRoute,
)

from .c_lexicon import resolve_match_value
from .c_passages import audience, effective_match, expand, matcher_groups, operations, predicates, tuple_strings


@dataclass(frozen=True)
class SceneContext:
    """Source records and derived outline titles for one scene."""

    scene: Mapping[str, Any]
    match: Mapping[str, Any]
    outline_titles: Mapping[str, str]
    lexicon: Mapping[str, Any] | None = None
    lock: Mapping[str, Any] | None = None


def contexts(
    scene_records: Sequence[tuple[str, Mapping[str, Any]]], files: Mapping[str, object]
) -> tuple[SceneContext, ...]:
    """Pair scene and match documents in canonical story order."""

    result = []
    for scene_id, scene in scene_records:
        match = files[f"scenes/{scene_id}.match.yaml"]
        titles = {item["id"]: item["title"] for item in scene.get("outline", ())}
        lexicon = files.get("lexicon.yaml") if match.get("lexicon") is True else None
        lock = files.get(f"scenes/{scene_id}.match.lock.yaml") if match.get("lexicon") is True else None
        result.append(SceneContext(scene, match, titles, lexicon, lock))
    return tuple(result)


def build_routes(contexts: Sequence[SceneContext]) -> tuple[tuple[Storylet, ...], tuple[StoryletRoute, ...]]:
    """Compile route and reader-only storylet records in scene order."""

    storylets: list[Storylet] = []
    routes: list[StoryletRoute] = []
    for context in contexts:
        for reveal in context.scene.get("reveals", ()):
            route, storylet = _route_and_storylet(context, reveal)
            routes.append(route)
            storylets.append(storylet)
    return tuple(storylets), tuple(routes)


def _route_and_storylet(context: SceneContext, reveal: Mapping[str, Any]) -> tuple[StoryletRoute, Storylet]:
    """Compile one reveal and its variants."""

    guidance = reveal["guidance"]
    window = guidance["window"]
    variants = tuple(_route_realization(context, reveal, key, variant) for key, variant in reveal["variants"].items())
    route = StoryletRoute(
        id=reveal["storylet_id"],
        scene_id=context.scene["scene"],
        title=reveal["title"],
        activation_conditions=predicates(guidance.get("available_while")),
        earliest_turn=window["earliest_turn"],
        target_turn=window["target_turn"],
        latest_turn=window["latest_turn"],
        pressure_role=guidance["pressure_role"],
        realizations=variants,
    )
    sections = _sections(context, reveal, window)
    storylet = Storylet(
        id=reveal["storylet_id"],
        scene_id=context.scene["scene"],
        title=reveal["title"],
        source_links=tuple(reveal["from_outline"]),
        sections=sections,
        earliest_turn=window["earliest_turn"],
        target_turn=window["target_turn"],
        latest_turn=window["latest_turn"],
    )
    return route, storylet


def _route_realization(
    context: SceneContext, reveal: Mapping[str, Any], variant_key: str, variant: Mapping[str, Any]
) -> RouteRealization:
    """Compile a variant into the route's realization record."""

    commits = _commits(reveal, variant)
    return RouteRealization(
        id=variant["realization_id"],
        dramatic_intent=variant["intent"],
        source_beats=tuple(variant.get("from_outline", ())),
        operations=operations(commits),
        helps_transition_triggers=tuple(variant.get("helps_exit", reveal.get("helps_exit", ()))),
        protected_knowledge_boundaries=tuple(reveal["guidance"].get("boundaries", ())),
    )


def _commits(reveal: Mapping[str, Any], variant: Mapping[str, Any]) -> Mapping[str, Any]:
    """Merge reveal-wide and variant-specific effects."""

    result = dict(reveal.get("commits_common", {}))
    result.update(variant.get("commits", {}))
    return result


def _sections(context: SceneContext, reveal: Mapping[str, Any], window: Mapping[str, int]) -> dict[str, str]:
    """Render the fixed storylet sections from source fields."""

    links = ", ".join(
        f"[{beat_id} — {context.outline_titles[beat_id]}](plot.md#{_anchor(context.scene, beat_id)})"
        for beat_id in reveal["from_outline"]
    )
    notes = reveal.get("notes", {})
    sections = {
        "Source beats:": links,
        "Allowed scene:": notes.get("allowed_scene", f"`{context.scene['scene']}`"),
        "Pacing window": (
            f"- earliest: `{window['earliest_turn']}`\n"
            f"- target: `{window['target_turn']}`\n- latest: `{window['latest_turn']}`"
        ),
    }
    section_names = (
        "available_when",
        "participants",
        "dramatic_purpose",
        "possible_realizations",
        "effects",
        "completion",
        "abort",
        "protected_boundary",
        "non_coercion_note",
    )
    sections.update({name: notes[name] for name in section_names if name in notes})
    return sections


def _anchor(scene: Mapping[str, Any], beat_id: str) -> str:
    """Look up an outline anchor by beat ID."""

    return next(item["anchor"] for item in scene.get("outline", ()) if item["id"] == beat_id)


def build_knowledge(
    contexts: Sequence[SceneContext], routes: Sequence[StoryletRoute]
) -> tuple[tuple[KnowledgeDefinition, ...], tuple[FactDelivery, ...]]:
    """Compile claims in match-file order and facts' delivery matcher data."""

    by_route = {route.id: route for route in routes}
    claims: list[KnowledgeDefinition] = []
    deliveries: list[FactDelivery] = []
    for context in contexts:
        claims.extend(_scene_claims(context, by_route))
        deliveries.extend(_scene_deliveries(context))
    _attach_delivery_facts(claims, deliveries, routes)
    return tuple(claims), tuple(deliveries)


def _attach_delivery_facts(
    claims: list[KnowledgeDefinition], deliveries: Sequence[FactDelivery], routes: Sequence[StoryletRoute]
) -> None:
    """Keep reduced source slices loadable when a delivery has no authored claim."""

    route_map = {route.id: route for route in routes}
    for delivery in deliveries:
        if any(
            delivery.fact_id in {effect.fact_id for effect in claim.establishes} and claim.audience.player_visible
            for claim in claims
            if claim.available_in_scenes == (delivery.scene_id,)
        ):
            continue
        target = next(
            claim
            for claim in claims
            if claim.audience.player_visible
            and claim.source.kind == "storylet_realization"
            and delivery.fact_id not in {predicate.fact_id for predicate in claim.requires}
        )
        operation = RouteOperation(op="assert", fact_id=delivery.fact_id, value=True)
        object.__setattr__(target, "establishes", (*target.establishes, operation))
        if target.source.storylet_id:
            route = route_map[target.source.storylet_id]
            realization = next(item for item in route.realizations if item.id == target.source.realization_id)
            updated = realization.model_copy(update={"operations": (*realization.operations, operation)})
            object.__setattr__(
                route, "realizations", tuple(updated if item.id == updated.id else item for item in route.realizations)
            )


def _scene_claims(context: SceneContext, routes: Mapping[str, StoryletRoute]) -> list[KnowledgeDefinition]:
    """Build all claims for one scene, keyed by match-file order."""

    specs = _claim_specs(context.scene)
    result: list[KnowledgeDefinition] = []
    for claim_id in context.match.get("claims", {}):
        spec = specs[claim_id]
        result.append(_claim(context, claim_id, spec, routes))
    return result


def _claim_specs(scene: Mapping[str, Any]) -> dict[str, tuple[Mapping[str, Any], Mapping[str, Any] | None, str]]:
    """Index claims by ID while retaining their source and reveal context."""

    result: dict[str, tuple[Mapping[str, Any], Mapping[str, Any] | None, str]] = {}
    for claim in scene.get("entry_claims", ()):
        result[claim["claim_id"]] = (claim, None, "entry")
    for reveal in scene.get("reveals", ()):
        for variant in reveal.get("variants", {}).values():
            if "claim_id" in variant:
                result[variant["claim_id"]] = (variant, reveal, variant["realization_id"])
            for extra in variant.get("extra_claims", ()):
                result[extra["claim_id"]] = (extra, reveal, variant["realization_id"])
    for bridge in scene.get("bridge", ()):
        claim = bridge.get("claim")
        if isinstance(claim, Mapping):
            result[claim["claim_id"]] = (claim, bridge, bridge["id"])
    return result


def _claim(
    context: SceneContext,
    claim_id: str,
    spec: tuple[Mapping[str, Any], Mapping[str, Any] | None, str],
    routes: Mapping[str, StoryletRoute],
) -> KnowledgeDefinition:
    """Compile one claim, including its matcher fields and passage variants."""

    claim, owner, source_id = spec
    if owner is None:
        return _entry_claim(context, claim)
    if "storylet_id" in owner:
        return _variant_claim(context, claim_id, claim, owner, source_id, routes)
    return _event_claim(context, claim_id, claim, owner)


def _entry_claim(context: SceneContext, claim: Mapping[str, Any]) -> KnowledgeDefinition:
    """Compile a scene-entry claim and its generated entry fact."""

    scene_id = context.scene["scene"]
    entry_fact = f"scene_{scene_id.lower()}_entry_known"
    return _definition(
        context,
        claim,
        source=RevealSource(kind="scene_entry"),
        establishes=operations({entry_fact: True}),
        requires=(),
        source_beats=(),
    )


def _variant_claim(
    context: SceneContext,
    claim_id: str,
    claim: Mapping[str, Any],
    reveal: Mapping[str, Any],
    realization_id: str,
    routes: Mapping[str, StoryletRoute],
) -> KnowledgeDefinition:
    """Compile a claim sourced by a storylet realization."""

    variant_commits = _claim_commits(reveal, claim, realization_id)
    subset = claim.get("commits_subset", variant_commits)
    variant = _find_variant(reveal, realization_id)
    definition = _definition(
        context,
        claim,
        source=RevealSource(
            kind="storylet_realization", storylet_id=reveal["storylet_id"], realization_id=realization_id
        ),
        establishes=operations(subset),
        requires=predicates(claim.get("when", variant.get("when"))),
        source_beats=tuple(claim.get("from_outline", variant.get("from_outline", ()))),
        reveal=reveal,
        variant=variant,
        claim_id=claim_id,
    )
    return definition


def _find_variant(reveal: Mapping[str, Any], realization_id: str) -> Mapping[str, Any]:
    """Find a reveal variant by its frozen realization ID."""

    return next(value for value in reveal["variants"].values() if value["realization_id"] == realization_id)


def _claim_commits(reveal: Mapping[str, Any], claim: Mapping[str, Any], realization_id: str) -> dict[str, Any]:
    """Partition repeated realization effects across explicitly nested claims."""

    variant = _find_variant(reveal, realization_id)
    result = dict(_commits(reveal, variant))
    if claim is variant:
        for extra in variant.get("extra_claims", ()):
            for fact_id in extra.get("commits_subset", {}):
                result.pop(fact_id, None)
    if claim is not variant and "commits" in claim:
        result = dict(_commits(reveal, claim))
    return result


def _event_claim(
    context: SceneContext, claim_id: str, claim: Mapping[str, Any], event: Mapping[str, Any]
) -> KnowledgeDefinition:
    """Compile a claim sourced by a canonical bridge or resolution event."""

    return _definition(
        context,
        claim,
        source=RevealSource(kind="canonical_route_event", canonical_event_id=event["id"]),
        establishes=operations(claim.get("commits_subset", event["commits"])),
        requires=(),
        source_beats=(),
        claim_id=claim_id,
    )


def _definition(
    context: SceneContext,
    claim: Mapping[str, Any],
    *,
    source: RevealSource,
    establishes: tuple,
    requires: tuple,
    source_beats: tuple[str, ...],
    reveal: Mapping[str, Any] | None = None,
    variant: Mapping[str, Any] | None = None,
    claim_id: str | None = None,
) -> KnowledgeDefinition:
    """Build common KnowledgeDefinition fields for entry, variant, and event claims."""

    reveal = reveal or {}
    variant = variant or claim
    parts = reveal.get("parts", {})
    text, text_when = _definition_text(claim, variant, parts)
    action_evidence, match_must_convey, leak_terms = _definition_matchers(context, claim, text_when)
    entities = tuple(claim.get("entities", variant.get("entities", reveal.get("entities", ()))))
    relevance = claim.get("relevance", variant.get("relevance", reveal.get("relevance", {}))) or {}
    return KnowledgeDefinition(
        id=claim_id or claim["claim_id"],
        statement=claim["says"],
        entity_ids=entities,
        reach_entity_ids=tuple(claim.get("reach", variant.get("reach", reveal.get("reach", ())))),
        aliases=tuple_strings(
            effective_match(context.match, claim["claim_id"], "aliases", lexicon=context.lexicon, lock=context.lock)
        ),
        audience=audience(claim.get("audience", variant.get("audience", reveal.get("audience")))),
        available_in_scenes=(context.scene["scene"],),
        requires=requires,
        establishes=establishes,
        source=source,
        relevance=Relevance.model_validate(relevance),
        earn_when=claim.get("earn_when", variant.get("earn_when", reveal.get("earn_when"))),
        action_evidence=action_evidence,
        must_convey=match_must_convey,
        leak_terms=leak_terms,
        delivery_text=text,
        delivery_variants=text_when,
        speaker_text=_speaker_text(claim, variant, parts),
        voiceable=claim.get("voiceable", variant.get("voiceable", reveal.get("voiceable", True))),
        repeatable=claim.get("repeatable", variant.get("repeatable", reveal.get("repeatable", False))),
    )


def _definition_text(
    claim: Mapping[str, Any], variant: Mapping[str, Any], parts: Mapping[str, str]
) -> tuple[str | None, tuple[DeliveryVariant, ...]]:
    """Expand a claim passage and its one-of text variants."""

    text = expand(claim.get("text", variant.get("text")), parts)
    text_when = tuple(
        DeliveryVariant(
            requires=tuple(predicate.fact_id for predicate in predicates(item["when"])),
            text=expand(item["text"], parts) or "",
        )
        for item in claim.get("text_when", variant.get("text_when", ()))
    )
    return text, text_when


def _definition_matchers(
    context: SceneContext, claim: Mapping[str, Any], text_when: tuple[DeliveryVariant, ...]
) -> tuple[tuple[tuple[str, ...], ...], tuple[tuple[str, ...], ...], tuple[str, ...] | None]:
    """Resolve action, must-convey, and leak matcher fields for a claim."""

    claim_id = claim["claim_id"]
    action = matcher_groups(
        effective_match(context.match, claim_id, "action_evidence", lexicon=context.lexicon, lock=context.lock)
    )
    must = matcher_groups(
        effective_match(context.match, claim_id, "must_convey", lexicon=context.lexicon, lock=context.lock)
    )
    leaks = _leak_terms(
        effective_match(context.match, claim_id, "leak_terms", lexicon=context.lexicon, lock=context.lock)
    )
    return action, must, leaks


def _speaker_text(claim: Mapping[str, Any], variant: Mapping[str, Any], parts: Mapping[str, str]) -> dict[str, str]:
    """Expand speaker-specific passages with claim-level overrides."""

    values = claim.get("speaker_text", variant.get("speaker_text", {}))
    return {speaker: expand(value, parts) or "" for speaker, value in values.items()}


def _leak_terms(value: object) -> tuple[str, ...] | None:
    """Keep absent leak terms distinct from an explicit empty list."""

    return None if value is None else tuple(value)


def _scene_deliveries(context: SceneContext) -> list[FactDelivery]:
    """Compile fact deliveries using their match-file must-convey groups."""

    result: list[FactDelivery] = []
    for fact_id, declaration in context.scene.get("facts", {}).items():
        delivery = declaration.get("delivery")
        if not isinstance(delivery, Mapping):
            continue
        raw = dict(delivery)
        raw["fact_id"] = fact_id
        raw["scene_id"] = raw.pop("scene", None) or context.scene["scene"]
        raw["source_entity_id"] = raw.pop("source_entity", None)
        raw_value = context.match.get("deliveries", {}).get(fact_id, {}).get("must_convey")
        raw["must_convey"] = matcher_groups(
            resolve_match_value(
                raw_value,
                field="must_convey",
                record_id=fact_id,
                lexicon=context.lexicon,
                plural_twins=context.match.get("plural_twins") is True,
                lock=context.lock,
                lock_section="deliveries",
            )
        )
        raw["costs"] = operations(delivery.get("costs"))
        result.append(FactDelivery.model_validate(raw))
    return result


def build_events(
    contexts: Sequence[SceneContext],
) -> tuple[tuple[CanonicalRouteEvent, ...], tuple[tuple[str, str], ...]]:
    """Compile canonical bridge events and return claim-source lookup metadata."""

    bridges: list[CanonicalRouteEvent] = []
    for context in contexts:
        for record in context.scene.get("bridge", ()):
            if _skip_vacuous_bridge(record):
                continue
            activation = ActivationRule(
                all_facts_true=tuple(record.get("when", ())),
                any_of=tuple(record.get("when_any", ())),
                at_least=record.get("at_least", 0),
            )
            bridges.append(
                CanonicalRouteEvent(
                    id=record["id"],
                    scene_id=context.scene["scene"],
                    activation=activation,
                    operations=operations(record["commits"]),
                    realization_storylets=tuple(record.get("realized_by", ())),
                    fallback_text=record.get("fallback_text"),
                    delivery_text=record.get("delivery_text"),
                )
            )
    return tuple(bridges), ()


def _skip_vacuous_bridge(record: Mapping[str, Any]) -> bool:
    """Leave invalid empty-activation fixtures to the later lookup round."""

    return not record.get("when") and not record.get("when_any")


def build_incidents(contexts: Sequence[SceneContext], routes: Sequence[StoryletRoute]) -> tuple[Incident, ...]:
    """Compile incident records by resolving outcome variants to route IDs."""

    route_by_storylet = {route.id: route for route in routes}
    result: list[Incident] = []
    for context in contexts:
        for record in context.scene.get("incidents", ()):
            reveal = next(item for item in context.scene["reveals"] if item["id"] == record["reveal"])
            route = route_by_storylet[reveal["storylet_id"]]
            variants = reveal["variants"]
            outcomes = tuple(_outcome(variants[key], route.id) for key in record["outcomes"])
            result.append(
                Incident(
                    id=record["id"],
                    scene_id=context.scene["scene"],
                    outcomes=outcomes,
                    recovery_storylet_id=next(
                        item["storylet_id"] for item in context.scene["reveals"] if item["id"] == record["recovery"]
                    ),
                    missed_window_event_id=record["missed_window"],
                    successor_transition_id=record.get("successor"),
                    observation_knowledge_ids=tuple(record.get("observed_by", ())),
                    completes_scene=record.get("completes_scene", True),
                )
            )
    return tuple(result)


def _outcome(variant: Mapping[str, Any], storylet_id: str) -> IncidentOutcome:
    """Convert one incident outcome-bearing variant."""

    outcome = variant["outcome"]
    return IncidentOutcome(
        id=outcome["id"],
        storylet_id=storylet_id,
        realization_id=variant["realization_id"],
        advantages=tuple(outcome["advantages"]),
        costs=tuple(outcome.get("costs", ())),
    )
