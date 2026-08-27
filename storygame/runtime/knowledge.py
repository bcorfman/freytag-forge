"""Fact-derived, audience-scoped knowledge projections for shadow evaluation."""

from __future__ import annotations

from collections.abc import Iterable

from pydantic import BaseModel, ConfigDict

from storygame.runtime.state import RuntimeState
from storygame.runtime.validation import predicate_matches
from storygame.story_package.models import KnowledgeDefinition


class _KnowledgeModel(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)


class ProjectedKnowledge(_KnowledgeModel):
    id: str
    statement: str
    entity_ids: tuple[str, ...]


class RevealCandidate(_KnowledgeModel):
    id: str
    statement: str


class TurnKnowledgeContext(_KnowledgeModel):
    """The complete fact-derived provider contract for one audience."""

    scene_id: str
    phase: str
    scene_frame: str
    pressure: str
    audience_id: str
    committed_knowledge: tuple[ProjectedKnowledge, ...]
    sayable_knowledge: tuple[ProjectedKnowledge, ...]
    established_entity_ids: tuple[str, ...]
    referenced_entity_ids: tuple[str, ...]
    continuity_ids: tuple[str, ...]
    candidates: tuple[RevealCandidate, ...]

    def payload_size(self) -> int:
        return len(self.model_dump_json(exclude={"sayable_knowledge"}).encode())

    def observability(self) -> dict[str, object]:
        """Safe metrics: IDs and counts only, never prose or player input."""

        return {
            "scene_id": self.scene_id,
            "audience_id": self.audience_id,
            "committed_ids": tuple(item.id for item in self.committed_knowledge),
            "candidate_ids": tuple(item.id for item in self.candidates),
            "payload_bytes": self.payload_size(),
        }


class KnowledgeProjector:
    """Projects immutable package knowledge from the canonical fact store."""

    def __init__(self, *, max_candidates: int = 4, max_continuity_records: int = 12) -> None:
        if max_candidates < 1:
            raise ValueError("max_candidates must be positive")
        self.max_candidates = max_candidates
        self.max_continuity_records = max_continuity_records

    def project(self, state: RuntimeState, audience_id: str, player_input: str) -> TurnKnowledgeContext:
        frame = next(
            frame for frame in state.package.knowledge.scene_frames if frame.scene_id == state.current_scene_id
        )
        committed = tuple(
            self._projected(item)
            for item in state.package.knowledge.knowledge
            if self._established(item, state) and self._visible_to(item, audience_id)
        )
        established_ids = tuple(sorted({entity_id for item in committed for entity_id in item.entity_ids}))
        referenced_ids = self._referenced_established_ids(state, player_input, established_ids)
        candidates = self._candidates(state, audience_id, referenced_ids)
        return TurnKnowledgeContext(
            scene_id=state.current_scene_id,
            phase=state.phase,
            scene_frame=frame.situation,
            pressure=frame.pressure,
            audience_id=audience_id,
            committed_knowledge=committed,
            sayable_knowledge=committed,
            established_entity_ids=established_ids,
            referenced_entity_ids=referenced_ids,
            continuity_ids=tuple(record.id for record in state.turn_records[-self.max_continuity_records :]),
            candidates=candidates,
        )

    @staticmethod
    def _projected(item: KnowledgeDefinition) -> ProjectedKnowledge:
        return ProjectedKnowledge(id=item.id, statement=item.statement, entity_ids=item.entity_ids)

    @staticmethod
    def _established(item: KnowledgeDefinition, state: RuntimeState) -> bool:
        def effect_matches(effect: object) -> bool:
            expected = str(effect.value).lower() if isinstance(effect.value, bool) else str(effect.value)
            matched = any(
                (fact.value if fact.value is not None else fact.object) == expected
                for fact in state.facts.matching(effect.fact_id)
            )
            return matched if effect.op == "assert" else not matched

        return all(effect_matches(effect) for effect in item.establishes)

    @staticmethod
    def _visible_to(item: KnowledgeDefinition, audience_id: str) -> bool:
        if item.audience.kind == "world_only":
            return False
        if audience_id == "player":
            return item.audience.player_visible
        return item.audience.kind == "public" or audience_id in item.audience.character_ids

    def _referenced_established_ids(
        self, state: RuntimeState, player_input: str, established_ids: Iterable[str]
    ) -> tuple[str, ...]:
        world = state.package.world
        names = {
            entity.id: entity.name.casefold()
            for entities in (world.locations, world.npcs, world.items)
            for entity in entities
        }
        input_folded = player_input.casefold()
        return tuple(sorted(entity_id for entity_id in established_ids if names.get(entity_id, "") in input_folded))

    def _candidates(
        self, state: RuntimeState, audience_id: str, referenced_ids: tuple[str, ...]
    ) -> tuple[RevealCandidate, ...]:
        candidates: list[KnowledgeDefinition] = []
        for knowledge_id in state.package.knowledge_indexes.scene_to_candidates[state.current_scene_id]:
            item = state.package.knowledge_indexes.by_id[knowledge_id]
            if self._established(item, state) or not self._visible_to(item, audience_id):
                continue
            if item.source.storylet_id in state.fired_event_ids:
                continue
            if not all(predicate_matches(predicate, state.facts) for predicate in item.requires):
                continue
            if item.source.kind != "storylet_realization" or item.source.storylet_id not in state.active_event_ids:
                continue
            candidates.append(item)
        referenced = set(referenced_ids)
        candidates.sort(
            key=lambda item: (
                not bool(referenced & set((*item.entity_ids, *item.relevance.entity_ids))),
                -item.relevance.priority,
                item.id,
            )
        )
        return tuple(self._candidate(item) for item in candidates[: self.max_candidates])

    @staticmethod
    def _candidate(item: KnowledgeDefinition) -> RevealCandidate:
        """Expose only the player-safe selection affordance to the provider."""

        return RevealCandidate(id=item.id, statement=item.statement)
