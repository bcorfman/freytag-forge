"""Immutable, typed validation projection for causal story candidates.

The projection is deliberately short-lived.  The Pydantic story remains the
authoring artifact; these objects only give semantic passes stable links to
the declarations they already validated.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TypeVar

from storygame.authoring.symbol_resolution import Namespace, Symbol, SymbolRegistry

T = TypeVar("T")


@dataclass(frozen=True)
class BoundSymbol[T]:
    symbol: Symbol
    declaration: T

    @property
    def id(self) -> str:
        return self.symbol.identifier


@dataclass(frozen=True)
class BoundConnectedRoute:
    declaration: object
    source: BoundSymbol[object]
    destination: BoundSymbol[object]
    prerequisites: tuple[BoundSymbol[object], ...]

    @property
    def id(self) -> str:
        return self.declaration.id


@dataclass(frozen=True)
class BoundCausalEvent:
    declaration: object
    actors: tuple[BoundSymbol[object], ...]
    location: BoundSymbol[object]
    inputs: tuple[BoundSymbol[object], ...]
    outputs: tuple[BoundSymbol[object], ...]
    prerequisites: tuple[BoundSymbol[object], ...]

    @property
    def id(self) -> str:
        return self.declaration.id


@dataclass(frozen=True)
class BoundTimelineConstraint:
    before: BoundCausalEvent
    after: BoundCausalEvent


@dataclass(frozen=True)
class BoundEvidenceOpportunity:
    declaration: object
    truth: BoundSymbol[object]
    holder: BoundSymbol[object]
    location: BoundSymbol[object]
    route: BoundSymbol[object]

    @property
    def id(self) -> str:
        return self.declaration.id

    @property
    def kind(self) -> str:
        return self.declaration.kind


@dataclass(frozen=True)
class BoundPartyKnowledge:
    declaration: object
    participant: BoundSymbol[object]
    truths: tuple[BoundSymbol[object], ...]


@dataclass(frozen=True)
class BoundProtection:
    declaration: object
    truth: BoundSymbol[object]
    revelations: tuple[BoundSymbol[object], ...]


@dataclass(frozen=True)
class BoundRevelation:
    declaration: object
    truth: BoundSymbol[object]
    gates: tuple[BoundSymbol[object], ...]

    @property
    def id(self) -> str:
        return self.declaration.id

    @property
    def required(self) -> bool:
        return self.declaration.required


@dataclass(frozen=True)
class BoundRealizationRoute:
    declaration: object
    revelation: BoundSymbol[object]
    opportunities: tuple[BoundEvidenceOpportunity, ...]
    prerequisites: tuple[BoundSymbol[object], ...]
    prerequisite_revelations: tuple[BoundSymbol[object], ...]
    results: tuple[BoundSymbol[object], ...]
    failure_consequences: tuple[BoundSymbol[object], ...]
    alternatives: tuple[BoundSymbol[object], ...]

    @property
    def id(self) -> str:
        return self.declaration.id


@dataclass(frozen=True)
class BoundBeat:
    declaration: object
    prerequisites: tuple[BoundSymbol[object], ...]
    outcome: BoundSymbol[object] | None

    @property
    def id(self) -> str:
        return self.declaration.id


@dataclass(frozen=True)
class BoundOutcome:
    declaration: object
    truth: BoundSymbol[object]

    @property
    def id(self) -> str:
        return self.declaration.id


@dataclass(frozen=True)
class BoundEndState:
    declaration: object
    outcomes: tuple[BoundOutcome, ...]
    truths: tuple[BoundSymbol[object], ...]

    @property
    def id(self) -> str:
        return self.declaration.id


@dataclass(frozen=True)
class BoundHypothesis:
    declaration: object
    participant: BoundSymbol[object]
    supporting_truths: tuple[BoundSymbol[object], ...]
    exonerating_truths: tuple[BoundSymbol[object], ...]


@dataclass(frozen=True)
class BoundBlueprint:
    """Read-only semantic view of one fully bound causal candidate."""

    story: object
    symbols: tuple[BoundSymbol[object], ...]
    opening_truths: tuple[BoundSymbol[object], ...]
    truths: tuple[BoundSymbol[object], ...]
    participants: tuple[BoundSymbol[object], ...]
    locations: tuple[BoundSymbol[object], ...]
    connected_routes: tuple[BoundConnectedRoute, ...]
    causal_events: tuple[BoundCausalEvent, ...]
    timeline_constraints: tuple[BoundTimelineConstraint, ...]
    evidence_opportunities: tuple[BoundEvidenceOpportunity, ...]
    party_knowledge: tuple[BoundPartyKnowledge, ...]
    protections: tuple[BoundProtection, ...]
    revelations: tuple[BoundRevelation, ...]
    realization_routes: tuple[BoundRealizationRoute, ...]
    outcomes: tuple[BoundOutcome, ...]
    required_beats: tuple[BoundBeat, ...]
    optional_beats: tuple[BoundBeat, ...]
    hypotheses: tuple[BoundHypothesis, ...]
    end_states: tuple[BoundEndState, ...]
    consequences: tuple[BoundSymbol[object], ...] = ()
    storylets: tuple[BoundSymbol[object], ...] = ()

    def ids(self, namespace: Namespace) -> tuple[str, ...]:
        return tuple(sorted(item.id for item in self.symbols if item.symbol.namespace is namespace))


def bind_blueprint(story: object) -> BoundBlueprint:
    """Bind a validated story once and construct its immutable semantic view."""

    registry = SymbolRegistry.from_story(story)
    registry.bind(SymbolRegistry.reference_sites(story))
    collections = {
        namespace: tuple(getattr(story, collection)) for collection, namespace in SymbolRegistry._COLLECTIONS
    }

    def declaration(namespace: Namespace, identifier: str) -> BoundSymbol[object]:
        symbol = registry.symbol(namespace, identifier)
        assert symbol is not None
        item = next(item for item in collections[namespace] if item.id == identifier)
        return BoundSymbol(symbol, item)

    def refs(namespace: Namespace, values: tuple[str, ...]) -> tuple[BoundSymbol[object], ...]:
        return tuple(declaration(namespace, value) for value in values)

    opportunities = tuple(
        BoundEvidenceOpportunity(
            item,
            declaration(Namespace.TRUTH, item.truth_id),
            declaration(Namespace.PARTICIPANT, item.holder_id),
            declaration(Namespace.LOCATION, item.location_id),
            declaration(Namespace.REALIZATION_ROUTE, item.route_id),
        )
        for item in story.evidence_opportunities
    )
    opportunities_by_id = {item.id: item for item in opportunities}
    outcomes = tuple(
        BoundOutcome(item, declaration(Namespace.TRUTH, item.truth_id)) for item in story.required_outcomes
    )
    outcomes_by_id = {item.id: item for item in outcomes}
    realizations = tuple(
        BoundRealizationRoute(
            item,
            declaration(Namespace.REVELATION, item.revelation_id),
            tuple(opportunities_by_id[value] for value in item.opportunity_ids),
            refs(Namespace.TRUTH, item.prerequisite_truths),
            refs(Namespace.REVELATION, item.prerequisite_revelation_ids),
            refs(Namespace.TRUTH, item.result_truth_ids),
            refs(Namespace.TRUTH, item.failure_forward.consequence_truth_ids),
            refs(Namespace.REALIZATION_ROUTE, item.failure_forward.alternative_route_ids),
        )
        for item in story.realization_routes
    )
    revelations = tuple(
        BoundRevelation(
            item,
            declaration(Namespace.TRUTH, item.truth_id),
            refs(Namespace.REQUIRED_BEAT, item.gate_beat_ids),
        )
        for item in story.revelations
    )

    def beats(items: tuple[object, ...]) -> tuple[BoundBeat, ...]:
        return tuple(
            BoundBeat(
                item,
                refs(Namespace.REVELATION, item.prerequisite_revelation_ids),
                outcomes_by_id.get(item.required_outcome_id) if item.required_outcome_id else None,
            )
            for item in items
        )

    required_beats = beats(story.required_beats)
    optional_beats = beats(story.optional_beats)
    causal_events = tuple(
        BoundCausalEvent(
            item,
            refs(Namespace.PARTICIPANT, item.actor_ids),
            declaration(Namespace.LOCATION, item.location_id),
            refs(Namespace.TRUTH, item.input_truths),
            refs(Namespace.TRUTH, item.output_truths),
            refs(Namespace.CAUSAL_EVENT, item.prerequisite_event_ids),
        )
        for item in story.causal_events
    )
    events_by_id = {item.id: item for item in causal_events}
    return BoundBlueprint(
        story,
        tuple(
            declaration(namespace, item.id)
            for collection, namespace in SymbolRegistry._COLLECTIONS
            for item in collections[namespace]
        ),
        refs(Namespace.TRUTH, story.opening_truth_ids),
        tuple(declaration(Namespace.TRUTH, item.id) for item in story.truths),
        tuple(declaration(Namespace.PARTICIPANT, item.id) for item in story.participants),
        tuple(declaration(Namespace.LOCATION, item.id) for item in story.locations),
        tuple(
            BoundConnectedRoute(
                item,
                declaration(Namespace.LOCATION, item.from_location_id),
                declaration(Namespace.LOCATION, item.to_location_id),
                refs(Namespace.TRUTH, item.prerequisite_truths),
            )
            for item in story.connected_routes
        ),
        causal_events,
        tuple(
            BoundTimelineConstraint(
                events_by_id[item.before_event_id],
                events_by_id[item.after_event_id],
            )
            for item in story.timeline_constraints
        ),
        opportunities,
        tuple(
            BoundPartyKnowledge(
                item,
                declaration(Namespace.PARTICIPANT, item.participant_id),
                refs(Namespace.TRUTH, item.truth_ids),
            )
            for item in story.party_knowledge
        ),
        tuple(
            BoundProtection(
                item,
                declaration(Namespace.TRUTH, item.truth_id),
                refs(Namespace.REVELATION, item.release_after_revelation_ids),
            )
            for item in story.knowledge_protections
        ),
        revelations,
        realizations,
        outcomes,
        required_beats,
        optional_beats,
        tuple(
            BoundHypothesis(
                item,
                declaration(Namespace.PARTICIPANT, item.participant_id),
                refs(Namespace.TRUTH, item.supporting_truth_ids),
                refs(Namespace.TRUTH, item.exonerating_truth_ids),
            )
            for item in story.suspect_hypotheses
        ),
        tuple(
            BoundEndState(
                item,
                tuple(outcomes_by_id[value] for value in item.required_outcome_ids),
                refs(Namespace.TRUTH, item.required_truth_ids),
            )
            for item in story.end_states
        ),
        tuple(declaration(Namespace.CONSEQUENCE, item.id) for item in story.consequences),
        tuple(declaration(Namespace.STORYLET, item.id) for item in story.storylets),
    )
