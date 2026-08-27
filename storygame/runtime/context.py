"""Bounded, player-safe context for one scene-runtime model turn."""

from __future__ import annotations

import json
import re
from collections.abc import Iterable

from pydantic import BaseModel, ConfigDict

from storygame.runtime.contracts import TurnProposal
from storygame.runtime.facts import Fact
from storygame.runtime.state import RuntimeState
from storygame.story_package.models import Entity, StoryletRoute

_PRIVATE_PREDICATES = frozenset({"belief", "beliefs", "knowledge", "knows", "private_knowledge", "speaker_private"})


class _ContextModel(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)


class ContextEntity(_ContextModel):
    id: str
    name: str
    kind: str


class ContextFact(_ContextModel):
    predicate: str
    subject: str
    object: str | None = None
    value: str | None = None


class StoryletContext(_ContextModel):
    id: str
    title: str
    pacing_impact: str
    pressure_role: str
    realizations: tuple[StoryletRealizationContext, ...]


class RouteOperationContext(_ContextModel):
    operation: str
    predicate: str
    value: str | None


class StoryletRealizationContext(_ContextModel):
    id: str
    dramatic_intent: str
    operations: tuple[RouteOperationContext, ...]


class EntityReferenceResult(_ContextModel):
    matched_ids: tuple[str, ...] = ()
    ambiguous_names: tuple[str, ...] = ()


class SceneContext(_ContextModel):
    """The complete, deliberately small context sent to a narration provider."""

    scene_id: str
    freytag_phase: str
    objective: str
    entry_text: str
    plot_beats: str
    location: ContextEntity
    entities: tuple[ContextEntity, ...]
    facts: tuple[ContextFact, ...]
    active_storylets: tuple[StoryletContext, ...]
    active_event_ids: tuple[str, ...]
    pressure: str | None = None
    protected_boundaries: tuple[str, ...]
    referenced_history: tuple[ContextFact, ...]
    reference_resolution: EntityReferenceResult
    response_schema: dict[str, object]

    def prompt(self) -> str:
        """Render a JSON-sized provider input with an explicit change contract."""

        return json.dumps(
            {
                "instructions": (
                    "Narrate only from this player-safe scene context. Return one JSON TurnProposal "
                    "that conforms exactly to response_schema; never invent facts or reveal protected knowledge."
                ),
                "scene": self.model_dump(mode="json", exclude={"response_schema"}),
                "response_schema": self.response_schema,
            },
            separators=(",", ":"),
        )


class SceneContextBuilder:
    """Projects canonical facts into a scene-local, reference-aware prompt."""

    def build(
        self,
        state: RuntimeState,
        player_input: str,
        *,
        active_storylet_ids: Iterable[str] = (),
    ) -> SceneContext:
        scene = next(item for item in state.package.scenes if item.metadata.scene_id == state.current_scene_id)
        entities = self._entities(state)
        entity_by_id = {entity.id: entity for entity, _ in entities}
        location = entity_by_id[scene.metadata.location_id]
        local_ids = {
            state.package.protagonist_id,
            scene.metadata.location_id,
            *scene.metadata.participant_ids,
            *scene.metadata.item_ids,
        }
        active_storylets = self._active_storylets(state, active_storylet_ids)
        local_ids.update(self._storylet_entity_ids(active_storylets, entities))
        facts = tuple(fact for fact in state.facts.asserted if self._is_safe_fact(fact, state))
        local_ids = self._expand_related_entity_ids(facts, local_ids, entity_by_id)
        references = self.resolve_references(player_input, entities)
        local_ids.update(references.matched_ids)
        local_facts = self._related_facts(facts, local_ids)
        referenced_ids = set(references.matched_ids) - {location.id}
        referenced_history = self._related_facts(facts, referenced_ids)
        return SceneContext(
            scene_id=scene.metadata.scene_id,
            freytag_phase=scene.metadata.freytag_phase,
            objective=scene.metadata.objective,
            entry_text=scene.metadata.entry_text,
            plot_beats=scene.prose,
            location=self._context_entity(location, "location"),
            entities=tuple(
                self._context_entity(entity, kind)
                for entity, kind in entities
                if entity.id in local_ids and entity.id != location.id
            ),
            facts=local_facts,
            active_storylets=tuple(self._storylet_context(item, state) for item in active_storylets),
            active_event_ids=tuple(sorted(state.active_event_ids)),
            pressure=self._pressure(state),
            protected_boundaries=("Do not reveal protected future knowledge.",),
            referenced_history=referenced_history,
            reference_resolution=references,
            response_schema=TurnProposal.model_json_schema(),
        )

    def resolve_references(self, player_input: str, entities: Iterable[tuple[Entity, str]]) -> EntityReferenceResult:
        """Resolve explicit public names/aliases, withholding ambiguous matches."""

        lowered = player_input.casefold()
        matches: dict[str, set[str]] = {}
        for entity, _kind in entities:
            for name in (entity.name, *entity.aliases):
                normalized = name.casefold()
                if re.search(rf"(?<!\w){re.escape(normalized)}(?!\w)", lowered):
                    matches.setdefault(normalized, set()).add(entity.id)
        ambiguous = tuple(sorted(name for name, ids in matches.items() if len(ids) > 1))
        matched = tuple(sorted({next(iter(ids)) for ids in matches.values() if len(ids) == 1}))
        return EntityReferenceResult(matched_ids=matched, ambiguous_names=ambiguous)

    @staticmethod
    def _entities(state: RuntimeState) -> tuple[tuple[Entity, str], ...]:
        world = state.package.world
        groups = (("location", world.locations), ("npc", world.npcs), ("item", world.items))
        return tuple((entity, kind) for kind, group in groups for entity in group)

    def _active_storylets(self, state: RuntimeState, requested_ids: Iterable[str]) -> tuple[StoryletRoute, ...]:
        requested = set(requested_ids)
        known = {
            item.id: item for item in state.package.storylet_routes.storylets if item.scene_id == state.current_scene_id
        }
        unknown = requested - known.keys()
        if unknown:
            raise ValueError("active storylets must belong to the current scene")
        return tuple(known[storylet_id] for storylet_id in sorted(requested))

    def _storylet_entity_ids(
        self, storylets: Iterable[StoryletRoute], entities: Iterable[tuple[Entity, str]]
    ) -> set[str]:
        # Route logic deliberately contains no cast list; plot metadata remains the scene-local entity authority.
        return set()

    @staticmethod
    def _context_entity(entity: Entity, kind: str) -> ContextEntity:
        return ContextEntity(id=entity.id, name=entity.name, kind=kind)

    def _is_safe_fact(self, fact: Fact, state: RuntimeState) -> bool:
        if fact.predicate in _PRIVATE_PREDICATES:
            return False
        protected = {term.casefold() for term in state.package.world.protected_knowledge}
        values = (fact.predicate, fact.subject, fact.object or "", fact.value or "")
        return not any(value.casefold() in protected for value in values)

    @staticmethod
    def _related_facts(facts: Iterable[Fact], entity_ids: set[str]) -> tuple[ContextFact, ...]:
        return tuple(
            ContextFact(**fact.model_dump())
            for fact in sorted(facts, key=lambda item: item.key)
            if fact.subject in entity_ids or fact.object in entity_ids
        )

    @staticmethod
    def _expand_related_entity_ids(facts: Iterable[Fact], local_ids: set[str], entities: dict[str, Entity]) -> set[str]:
        """Include public entities directly connected to a scene-local fact."""

        expanded = set(local_ids)
        for fact in facts:
            if fact.subject in expanded and fact.object in entities:
                expanded.add(fact.object)
            if fact.object in expanded and fact.subject in entities:
                expanded.add(fact.subject)
        return expanded

    @staticmethod
    def _pressure(state: RuntimeState) -> str | None:
        elapsed = state.facts.matching("story_elapsed_seconds", "story")
        total = int(elapsed[-1].value) if elapsed and elapsed[-1].value else 0
        window = next(item for item in state.package.pacing.scenes if item.scene_id == state.current_scene_id)
        if total >= window.latest_seconds:
            return "deadline pressure is active; introduce an observable, scene-local complication"
        if total >= window.target_seconds:
            return "pressure is rising; keep the scene active while making urgency felt"
        return None

    def _storylet_context(self, storylet: StoryletRoute, state: RuntimeState) -> StoryletContext:
        return StoryletContext(
            id=storylet.id,
            title=storylet.title,
            pacing_impact="scene_guidance",
            pressure_role=storylet.pressure_role,
            realizations=tuple(
                StoryletRealizationContext(
                    id=item.id,
                    dramatic_intent=item.dramatic_intent,
                    operations=tuple(
                        RouteOperationContext(
                            operation=operation.op,
                            predicate=operation.fact_id,
                            value=str(operation.value).lower() if operation.value is not None else None,
                        )
                        for operation in item.operations
                    ),
                )
                for item in storylet.realizations
            ),
        )
