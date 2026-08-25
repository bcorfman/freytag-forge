"""Namespace-aware symbol collection and reference binding for authoring.

The registry is a validation projection only.  It never changes the authored
candidate and deliberately stores IDs rather than mutable model objects.
"""

from __future__ import annotations

from collections import defaultdict
from collections.abc import Iterable, Mapping
from dataclasses import dataclass
from enum import StrEnum


class Namespace(StrEnum):
    """The symbol namespaces exposed by a causal story candidate."""

    TRUTH = "truth"
    PARTICIPANT = "participant"
    NPC_PERFORMANCE_PROFILE = "npc_performance_profile"
    LOCATION = "location"
    CONNECTED_ROUTE = "connected_route"
    CAUSAL_EVENT = "causal_event"
    EVIDENCE_OPPORTUNITY = "evidence_opportunity"
    MOVEMENT_PLAN = "movement_plan"
    SCENE_SUBJECT = "scene_subject"
    EVIDENCE_REALIZATION = "evidence_realization"
    GROUP_ENCOUNTER = "group_encounter"
    REALIZATION_ROUTE = "realization_route"
    REVELATION = "revelation"
    REQUIRED_OUTCOME = "required_outcome"
    REQUIRED_BEAT = "required_beat"
    OPTIONAL_BEAT = "optional_beat"
    CONSEQUENCE = "consequence"
    STORYLET = "storylet"
    INTERACTION_FRAME = "interaction_frame"
    END_STATE = "end_state"


@dataclass(frozen=True)
class Symbol:
    """One declared ID and its namespace."""

    namespace: Namespace
    identifier: str
    related_identifier: str | None = None


@dataclass(frozen=True)
class ReferenceSite:
    """A candidate field and the namespace in which its value must resolve."""

    path: str
    expected_namespace: Namespace
    supplied_id: str


@dataclass(frozen=True)
class BindingDiagnostic:
    """A deterministic, provider-safe binding diagnostic."""

    code: str
    path: str
    expected_namespace: Namespace
    supplied_id: str
    supplied_namespace: Namespace | None = None
    suggestion: str | None = None

    def render(self) -> str:
        detail = f"{self.path}: expected {self.expected_namespace.value}, supplied '{self.supplied_id}'"
        if self.supplied_namespace is not None:
            detail += f" ({self.supplied_namespace.value} namespace)"
            if self.supplied_namespace is Namespace.EVIDENCE_OPPORTUNITY:
                detail += " (is evidence opportunity ID)"
        if self.suggestion is not None:
            detail += (
                f"; use truth_id '{self.suggestion}'"
                if self.expected_namespace is Namespace.TRUTH
                else f"; use '{self.suggestion}'"
            )
        return detail


class SymbolResolutionError(ValueError):
    """Grouped duplicate-definition or unbound-reference failures."""

    def __init__(self, diagnostics: Iterable[BindingDiagnostic]) -> None:
        self.diagnostics = tuple(diagnostics)
        super().__init__("; ".join(diagnostic.render() for diagnostic in self.diagnostics))


class SymbolRegistry:
    """Collect declarations once and bind every declared reference site."""

    _COLLECTIONS: tuple[tuple[str, Namespace], ...] = (
        ("truths", Namespace.TRUTH),
        ("participants", Namespace.PARTICIPANT),
        ("npc_performance_profiles", Namespace.NPC_PERFORMANCE_PROFILE),
        ("locations", Namespace.LOCATION),
        ("connected_routes", Namespace.CONNECTED_ROUTE),
        ("causal_events", Namespace.CAUSAL_EVENT),
        ("evidence_opportunities", Namespace.EVIDENCE_OPPORTUNITY),
        ("movement_plans", Namespace.MOVEMENT_PLAN),
        ("scene_subjects", Namespace.SCENE_SUBJECT),
        ("evidence_realizations", Namespace.EVIDENCE_REALIZATION),
        ("group_encounters", Namespace.GROUP_ENCOUNTER),
        ("realization_routes", Namespace.REALIZATION_ROUTE),
        ("revelations", Namespace.REVELATION),
        ("required_outcomes", Namespace.REQUIRED_OUTCOME),
        ("required_beats", Namespace.REQUIRED_BEAT),
        ("optional_beats", Namespace.OPTIONAL_BEAT),
        ("consequences", Namespace.CONSEQUENCE),
        ("storylets", Namespace.STORYLET),
        ("interaction_frames", Namespace.INTERACTION_FRAME),
        ("end_states", Namespace.END_STATE),
    )

    def __init__(self, symbols: Mapping[Namespace, Mapping[str, Symbol]]) -> None:
        self._symbols = {namespace: dict(values) for namespace, values in symbols.items()}

    @classmethod
    def from_story(cls, story: object) -> SymbolRegistry:
        return cls._from_declarations(
            (collection, tuple(getattr(story, collection, ()))) for collection, _namespace in cls._COLLECTIONS
        )

    @classmethod
    def from_payload(cls, payload: Mapping[str, object]) -> SymbolRegistry:
        """Collect a ledger from a parseable candidate without validating it."""

        return cls._from_declarations(
            (collection, tuple(payload.get(collection, ()))) for collection, _namespace in cls._COLLECTIONS
        )

    @classmethod
    def _from_declarations(cls, declarations: Iterable[tuple[str, Iterable[object]]]) -> SymbolRegistry:
        symbols: dict[Namespace, dict[str, Symbol]] = defaultdict(dict)
        duplicates: list[BindingDiagnostic] = []
        namespaces = dict(cls._COLLECTIONS)
        for collection, values in declarations:
            namespace = namespaces[collection]
            for index, declaration in enumerate(values):
                identifier = (
                    declaration.get("id") if isinstance(declaration, Mapping) else getattr(declaration, "id", None)
                )
                if not isinstance(identifier, str):
                    continue
                if identifier in symbols[namespace]:
                    duplicates.append(
                        BindingDiagnostic(
                            "DUPLICATE_SYMBOL",
                            f"{collection}[{index}].id",
                            namespace,
                            identifier,
                        )
                    )
                else:
                    related_identifier = None
                    if namespace is Namespace.EVIDENCE_OPPORTUNITY:
                        related_identifier = (
                            declaration.get("truth_id")
                            if isinstance(declaration, Mapping)
                            else getattr(declaration, "truth_id", None)
                        )
                    symbols[namespace][identifier] = Symbol(namespace, identifier, related_identifier)
        registry = cls(symbols)
        if duplicates:
            raise SymbolResolutionError(duplicates)
        return registry

    def ids(self, namespace: Namespace) -> tuple[str, ...]:
        """Return declared IDs in deterministic order."""

        return tuple(sorted(self._symbols.get(namespace, {})))

    def symbol(self, namespace: Namespace, identifier: str) -> Symbol | None:
        return self._symbols.get(namespace, {}).get(identifier)

    def _foreign_namespace(self, identifier: str, expected: Namespace) -> Namespace | None:
        matches = [
            namespace for namespace, values in self._symbols.items() if namespace != expected and identifier in values
        ]
        return matches[0] if len(matches) == 1 else None

    def bind(self, sites: Iterable[ReferenceSite]) -> tuple[Symbol, ...]:
        """Bind all sites, reporting every failure in path order."""

        bound: list[Symbol] = []
        diagnostics: list[BindingDiagnostic] = []
        for site in sorted(sites, key=lambda item: item.path):
            symbol = self.symbol(site.expected_namespace, site.supplied_id)
            if symbol is not None:
                bound.append(symbol)
                continue
            foreign = self._foreign_namespace(site.supplied_id, site.expected_namespace)
            suggestion = None
            if site.expected_namespace is Namespace.TRUTH and foreign is Namespace.EVIDENCE_OPPORTUNITY:
                opportunity = self.symbol(Namespace.EVIDENCE_OPPORTUNITY, site.supplied_id)
                suggestion = self._opportunity_truth_id(opportunity)
            diagnostics.append(
                BindingDiagnostic(
                    "WRONG_NAMESPACE" if foreign is not None else "UNKNOWN_REFERENCE",
                    site.path,
                    site.expected_namespace,
                    site.supplied_id,
                    foreign,
                    suggestion,
                )
            )
        if diagnostics:
            raise SymbolResolutionError(diagnostics)
        return tuple(bound)

    @staticmethod
    def _opportunity_truth_id(opportunity: Symbol | None) -> str | None:
        # The registry stores only IDs; the special suggestion is supplied by
        # ``reference_sites`` where the typed opportunity is available.
        return opportunity.related_identifier if opportunity is not None else None

    @staticmethod
    def reference_sites(story: object) -> tuple[ReferenceSite, ...]:
        """Describe all reference-bearing fields in the causal contract."""

        sites: list[ReferenceSite] = []

        def add(path: str, namespace: Namespace, values: Iterable[str]) -> None:
            sites.extend(ReferenceSite(f"{path}[{index}]", namespace, value) for index, value in enumerate(values))

        def add_one(path: str, namespace: Namespace, value: str) -> None:
            sites.append(ReferenceSite(path, namespace, value))

        add("opening_truth_ids", Namespace.TRUTH, story.opening_truth_ids)
        for index, participant in enumerate(story.participants):
            if participant.performance_profile_id is not None:
                add_one(
                    f"participants[{index}].performance_profile_id",
                    Namespace.NPC_PERFORMANCE_PROFILE,
                    participant.performance_profile_id,
                )
            add(f"participants[{index}].movement_plan_ids", Namespace.MOVEMENT_PLAN, participant.movement_plan_ids)
        for index, profile in enumerate(story.npc_performance_profiles):
            add_one(
                f"npc_performance_profiles[{index}].participant_id",
                Namespace.PARTICIPANT,
                profile.participant_id,
            )
        for index, route in enumerate(story.connected_routes):
            add_one(f"connected_routes[{index}].from_location_id", Namespace.LOCATION, route.from_location_id)
            add_one(f"connected_routes[{index}].to_location_id", Namespace.LOCATION, route.to_location_id)
            add(f"connected_routes[{index}].prerequisite_truths", Namespace.TRUTH, route.prerequisite_truths)
        for index, event in enumerate(story.causal_events):
            add(f"causal_events[{index}].actor_ids", Namespace.PARTICIPANT, event.actor_ids)
            add_one(f"causal_events[{index}].location_id", Namespace.LOCATION, event.location_id)
            add(f"causal_events[{index}].input_truths", Namespace.TRUTH, event.input_truths)
            add(f"causal_events[{index}].output_truths", Namespace.TRUTH, event.output_truths)
            add(f"causal_events[{index}].prerequisite_event_ids", Namespace.CAUSAL_EVENT, event.prerequisite_event_ids)
        for index, constraint in enumerate(story.timeline_constraints):
            add_one(
                f"timeline_constraints[{index}].before_event_id",
                Namespace.CAUSAL_EVENT,
                constraint.before_event_id,
            )
            add_one(f"timeline_constraints[{index}].after_event_id", Namespace.CAUSAL_EVENT, constraint.after_event_id)
        for index, opportunity in enumerate(story.evidence_opportunities):
            add_one(f"evidence_opportunities[{index}].truth_id", Namespace.TRUTH, opportunity.truth_id)
            add_one(f"evidence_opportunities[{index}].holder_id", Namespace.PARTICIPANT, opportunity.holder_id)
            add_one(f"evidence_opportunities[{index}].location_id", Namespace.LOCATION, opportunity.location_id)
            add_one(f"evidence_opportunities[{index}].route_id", Namespace.REALIZATION_ROUTE, opportunity.route_id)
        for index, plan in enumerate(story.movement_plans):
            add_one(f"movement_plans[{index}].participant_id", Namespace.PARTICIPANT, plan.participant_id)
            add_one(f"movement_plans[{index}].source_location_id", Namespace.LOCATION, plan.source_location_id)
            add_one(
                f"movement_plans[{index}].destination_location_id",
                Namespace.LOCATION,
                plan.destination_location_id,
            )
            add(f"movement_plans[{index}].activation_truth_ids", Namespace.TRUTH, plan.activation_truth_ids)
            add(f"movement_plans[{index}].abort_truth_ids", Namespace.TRUTH, plan.abort_truth_ids)
        for index, subject in enumerate(story.scene_subjects):
            add_one(f"scene_subjects[{index}].location_id", Namespace.LOCATION, subject.location_id)
            add(
                f"scene_subjects[{index}].evidence_opportunity_ids",
                Namespace.EVIDENCE_OPPORTUNITY,
                subject.evidence_opportunity_ids,
            )
        for index, realization in enumerate(story.evidence_realizations):
            add_one(
                f"evidence_realizations[{index}].evidence_opportunity_id",
                Namespace.EVIDENCE_OPPORTUNITY,
                realization.evidence_opportunity_id,
            )
            add_one(f"evidence_realizations[{index}].location_id", Namespace.LOCATION, realization.location_id)
            if realization.custody_holder_id is not None:
                add_one(
                    f"evidence_realizations[{index}].custody_holder_id",
                    Namespace.PARTICIPANT,
                    realization.custody_holder_id,
                )
            if realization.scene_subject_id is not None:
                add_one(
                    f"evidence_realizations[{index}].scene_subject_id",
                    Namespace.SCENE_SUBJECT,
                    realization.scene_subject_id,
                )
        for index, encounter in enumerate(story.group_encounters):
            add_one(f"group_encounters[{index}].location_id", Namespace.LOCATION, encounter.location_id)
            add(f"group_encounters[{index}].participant_ids", Namespace.PARTICIPANT, encounter.participant_ids)
            add(f"group_encounters[{index}].introduction_truth_ids", Namespace.TRUTH, encounter.introduction_truth_ids)
        if story.opening is not None:
            for index, suggestion in enumerate(story.opening.first_action_suggestions):
                namespaces = {
                    "participant": Namespace.PARTICIPANT,
                    "scene_subject": Namespace.SCENE_SUBJECT,
                    "evidence_realization": Namespace.EVIDENCE_REALIZATION,
                    "group_encounter": Namespace.GROUP_ENCOUNTER,
                }
                add_one(
                    f"opening.first_action_suggestions[{index}].target_id",
                    namespaces[suggestion.target_kind],
                    suggestion.target_id,
                )
        for index, knowledge in enumerate(story.party_knowledge):
            add_one(f"party_knowledge[{index}].participant_id", Namespace.PARTICIPANT, knowledge.participant_id)
            add(f"party_knowledge[{index}].truth_ids", Namespace.TRUTH, knowledge.truth_ids)
        for index, protection in enumerate(story.knowledge_protections):
            add_one(f"knowledge_protections[{index}].truth_id", Namespace.TRUTH, protection.truth_id)
            add(
                f"knowledge_protections[{index}].release_after_revelation_ids",
                Namespace.REVELATION,
                protection.release_after_revelation_ids,
            )
        for index, revelation in enumerate(story.revelations):
            add_one(f"revelations[{index}].truth_id", Namespace.TRUTH, revelation.truth_id)
            add(f"revelations[{index}].gate_beat_ids", Namespace.REQUIRED_BEAT, revelation.gate_beat_ids)
        for index, route in enumerate(story.realization_routes):
            add_one(f"realization_routes[{index}].revelation_id", Namespace.REVELATION, route.revelation_id)
            add(f"realization_routes[{index}].opportunity_ids", Namespace.EVIDENCE_OPPORTUNITY, route.opportunity_ids)
            add(f"realization_routes[{index}].prerequisite_truths", Namespace.TRUTH, route.prerequisite_truths)
            add(
                f"realization_routes[{index}].prerequisite_revelation_ids",
                Namespace.REVELATION,
                route.prerequisite_revelation_ids,
            )
            add(f"realization_routes[{index}].result_truth_ids", Namespace.TRUTH, route.result_truth_ids)
            add(
                f"realization_routes[{index}].failure_forward.consequence_truth_ids",
                Namespace.TRUTH,
                route.failure_forward.consequence_truth_ids,
            )
            add(
                f"realization_routes[{index}].failure_forward.alternative_route_ids",
                Namespace.REALIZATION_ROUTE,
                route.failure_forward.alternative_route_ids,
            )
        for index, outcome in enumerate(story.required_outcomes):
            add_one(f"required_outcomes[{index}].truth_id", Namespace.TRUTH, outcome.truth_id)
        for collection, _namespace in (
            ("required_beats", Namespace.REQUIRED_BEAT),
            ("optional_beats", Namespace.OPTIONAL_BEAT),
        ):
            for index, beat in enumerate(getattr(story, collection)):
                add(
                    f"{collection}[{index}].prerequisite_revelation_ids",
                    Namespace.REVELATION,
                    beat.prerequisite_revelation_ids,
                )
                if beat.required_outcome_id is not None:
                    add_one(
                        f"{collection}[{index}].required_outcome_id",
                        Namespace.REQUIRED_OUTCOME,
                        beat.required_outcome_id,
                    )
        if getattr(story, "dramatic_spine", None) is not None:
            add("dramatic_spine.completion_truth_ids", Namespace.TRUTH, story.dramatic_spine.completion_truth_ids)
        for index, consequence in enumerate(getattr(story, "consequences", ())):
            add(f"consequences[{index}].assert_truth_ids", Namespace.TRUTH, consequence.assert_truth_ids)
            add(f"consequences[{index}].retract_truth_ids", Namespace.TRUTH, consequence.retract_truth_ids)
        for index, storylet in enumerate(getattr(story, "storylets", ())):
            add_one(f"storylets[{index}].beat_id", Namespace.REQUIRED_BEAT, storylet.beat_id)
            add(
                f"storylets[{index}].availability.required_truth_ids",
                Namespace.TRUTH,
                storylet.availability.required_truth_ids,
            )
            add(
                f"storylets[{index}].availability.absent_truth_ids",
                Namespace.TRUTH,
                storylet.availability.absent_truth_ids,
            )
            add(
                f"storylets[{index}].availability.participant_ids",
                Namespace.PARTICIPANT,
                storylet.availability.participant_ids,
            )
            add(f"storylets[{index}].availability.location_ids", Namespace.LOCATION, storylet.availability.location_ids)
            add(f"storylets[{index}].consequence_ids", Namespace.CONSEQUENCE, storylet.consequence_ids)
            add_one(f"storylets[{index}].activation_truth_id", Namespace.TRUTH, storylet.activation_truth_id)
            add_one(f"storylets[{index}].completion_truth_id", Namespace.TRUTH, storylet.completion_truth_id)
            add(f"storylets[{index}].abort_truth_ids", Namespace.TRUTH, storylet.abort_truth_ids)
            add(
                f"storylets[{index}].failure_forward_storylet_ids",
                Namespace.STORYLET,
                storylet.failure_forward_storylet_ids,
            )
            add(
                f"storylets[{index}].interaction_frame_ids",
                Namespace.INTERACTION_FRAME,
                storylet.interaction_frame_ids,
            )
        for index, frame in enumerate(story.interaction_frames):
            add_one(f"interaction_frames[{index}].storylet_id", Namespace.STORYLET, frame.storylet_id)
            add_one(f"interaction_frames[{index}].initiator_id", Namespace.PARTICIPANT, frame.initiator_id)
            add(f"interaction_frames[{index}].participant_ids", Namespace.PARTICIPANT, frame.participant_ids)
            add(f"interaction_frames[{index}].location_ids", Namespace.LOCATION, frame.location_ids)
            add(
                f"interaction_frames[{index}].permitted_movement_plan_ids",
                Namespace.MOVEMENT_PLAN,
                frame.permitted_movement_plan_ids,
            )
            for field in (
                "activation_truth_id",
                "continuation_truth_id",
                "completion_truth_id",
                "recent_use_truth_id",
            ):
                add_one(f"interaction_frames[{index}].{field}", Namespace.TRUTH, getattr(frame, field))
            add(f"interaction_frames[{index}].abort_truth_ids", Namespace.TRUTH, frame.abort_truth_ids)
            add(
                f"interaction_frames[{index}].failure_forward_frame_ids",
                Namespace.INTERACTION_FRAME,
                frame.failure_forward_frame_ids,
            )
        for index, hypothesis in enumerate(story.suspect_hypotheses):
            add_one(f"suspect_hypotheses[{index}].participant_id", Namespace.PARTICIPANT, hypothesis.participant_id)
            add(f"suspect_hypotheses[{index}].supporting_truth_ids", Namespace.TRUTH, hypothesis.supporting_truth_ids)
            add(f"suspect_hypotheses[{index}].exonerating_truth_ids", Namespace.TRUTH, hypothesis.exonerating_truth_ids)
        for index, end_state in enumerate(story.end_states):
            add(f"end_states[{index}].required_outcome_ids", Namespace.REQUIRED_OUTCOME, end_state.required_outcome_ids)
            add(f"end_states[{index}].required_truth_ids", Namespace.TRUTH, end_state.required_truth_ids)
        return tuple(sites)
