"""Fact-derived, audience-scoped knowledge projections for shadow evaluation."""

from __future__ import annotations

import re
from collections.abc import Iterable

from pydantic import BaseModel, ConfigDict, Field

from storygame.runtime.reveal_eligibility import explain_reveal, together_or_unplaced
from storygame.runtime.state import RuntimeState
from storygame.runtime.world_model import world_for
from storygame.story_package.models import ActionContract, FactDelivery, KnowledgeDefinition, entity_surface_forms


class _KnowledgeModel(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)


class ProjectedKnowledge(_KnowledgeModel):
    id: str
    statement: str
    entity_ids: tuple[str, ...]


class RevealCandidate(_KnowledgeModel):
    id: str
    statement: str
    earn_when: str | None = None
    must_convey: tuple[tuple[str, ...], ...]
    action_evidence: tuple[tuple[str, ...], ...] = Field(default=(), exclude=True)
    delivery_text: str | None = Field(default=None, exclude=True)
    action_contract: ActionContract | None = Field(default=None, exclude=True)


class TurnKnowledgeContext(_KnowledgeModel):
    """The complete fact-derived provider contract for one audience.

    Moving knowledge stays committed for grounding and speech, but can be hidden from the scene text.
    """

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
    reveal_universe: tuple[RevealCandidate, ...] = ()
    handoff_deliveries: tuple[FactDelivery, ...] = ()
    scene_hidden_ids: tuple[str, ...] = ()

    def payload_size(self) -> int:
        return len(self.model_dump_json(exclude={"sayable_knowledge", "reveal_universe"}).encode())


def _entity_surface_forms(entity) -> tuple[str, ...]:
    """Every written form by which a player might name one entity.

    Surface forms come only from the authored world entity name and aliases.
    If a shorter player-facing form is useful, it belongs in world.yaml rather
    than being inferred from the name or from a knowledge item's aliases.
    """

    return entity_surface_forms(entity)


def _normalize_scoped_alias(value: str) -> str:
    value = value.strip().lower().rstrip(".,;:!? ").strip()
    for article in ("the", "my", "a", "an"):
        if value.startswith(article + " "):
            return value[len(article) + 1 :]
    return value


def _entity_in_scene_scope(scope_world, entity_id: str, *, scene, protagonist_id: str) -> bool:
    if scope_world.area(entity_id) is None:
        return False
    if entity_id in {protagonist_id, *scene.metadata.participant_ids, *scene.metadata.item_ids}:
        return True

    entity_area = scope_world.area(entity_id)
    scene_area = scope_world.area(scene.metadata.location_id)
    protagonist_area = scope_world.area(protagonist_id)

    def at_or_below(area_id, ancestor_id):
        return area_id == ancestor_id or ancestor_id in scope_world.chain(area_id)

    return any(
        ancestor_id is not None and at_or_below(entity_area, ancestor_id)
        for ancestor_id in (scene_area, protagonist_area)
    )


def scoped_alias_entity_ids(world, alias: str, *, scene, protagonist_id: str, scope_world=None) -> tuple[str, ...]:
    """Return the uniquely eligible group or item for one scoped alias."""

    scope_world = world if scope_world is None else scope_world
    wanted = _normalize_scoped_alias(alias)
    matches = [
        entity.id
        for entity in (*world.groups, *world.items)
        if any(_normalize_scoped_alias(candidate) == wanted for candidate in entity.scoped_aliases)
        and _entity_in_scene_scope(scope_world, entity.id, scene=scene, protagonist_id=protagonist_id)
    ]
    return tuple(matches) if len(matches) == 1 else ()


class KnowledgeGuards:
    """Shared fact-derived prerequisites for entity and prose protection.

    Callers retain their distinct scope, grounding and authored-text exceptions.
    """

    def __init__(self, state: RuntimeState) -> None:
        self.earned_ids = {
            item.id
            for item in state.package.knowledge.knowledge
            if KnowledgeProjector._established(item, state) and KnowledgeProjector._visible_to(item, "player")
        }
        self.true_fact_ids = {
            fact.predicate
            for fact in state.facts.asserted
            if (fact.value if fact.value is not None else fact.object) == "true"
        }
        self.guards_by_id = {guard.id: guard for guard in state.package.world.disclosure_guards}

    def unearned(self, knowledge_ids: Iterable[str]) -> bool:
        return not self.earned_ids.intersection(knowledge_ids)

    def disclosure_locked(self, guard_ids: Iterable[str]) -> bool:
        return not all(
            (guard.unlock_fact is not None and guard.unlock_fact in self.true_fact_ids)
            or (guard.unlock_knowledge_id is not None and guard.unlock_knowledge_id in self.earned_ids)
            for guard_id in guard_ids
            for guard in (self.guards_by_id[guard_id],)
        )


def entity_is_protected(state: RuntimeState, entity_id: str) -> bool:
    """Return whether the narration guard still blocks this entity's authored terms."""

    indexes = state.package.knowledge_indexes
    scene = next(scene for scene in state.package.scenes if scene.metadata.scene_id == state.current_scene_id)
    fixed_scene_item = entity_id in scene.metadata.item_ids and any(
        item.id == entity_id and item.fixed is True for item in state.package.world.items
    )
    guards = KnowledgeGuards(state)
    entity_terms = {term for term, entity_ids in indexes.entity_alias_to_entities.items() if entity_id in entity_ids}
    leak_knowledge_ids = {
        knowledge_id for term in entity_terms for knowledge_id in indexes.leak_term_to_knowledge.get(term, ())
    }
    if not fixed_scene_item and leak_knowledge_ids and guards.unearned(leak_knowledge_ids):
        return True

    entity_forms = {
        form.casefold()
        for entity in (*state.package.world.locations, *state.package.world.npcs, *state.package.world.items)
        if entity.id == entity_id
        for form in (entity.name, *entity.aliases)
    }
    guard_ids = {guard_id for form in entity_forms for guard_id in indexes.disclosure_guards.get(form, ())}
    if guards.disclosure_locked(guard_ids):
        return True

    protected_knowledge_ids = {
        knowledge_id
        for term in entity_terms & set(indexes.protected_terms)
        for knowledge_id in indexes.term_to_knowledge.get(term, ())
    }
    return bool(protected_knowledge_ids and guards.unearned(protected_knowledge_ids))


def _input_referenced_entity_ids(
    world,
    player_input: str,
    *,
    scope_world=None,
    scene=None,
    protagonist_id: str | None = None,
) -> frozenset[str]:
    """Find the world entities the player named in their own words."""

    folded_input = player_input.casefold()
    referenced = {
        entity.id
        for entities in (world.locations, world.npcs, world.groups, world.items)
        for entity in entities
        if any(re.search(rf"(?<!\w){re.escape(form)}(?!\w)", folded_input) for form in _entity_surface_forms(entity))
    }
    if scope_world is None or scene is None or protagonist_id is None:
        return frozenset(referenced)
    for entity in (*world.groups, *world.items):
        for alias in entity.scoped_aliases:
            normalized_alias = _normalize_scoped_alias(alias)
            if re.search(rf"(?<!\w){re.escape(normalized_alias)}(?!\w)", folded_input):
                referenced.update(
                    scoped_alias_entity_ids(
                        world,
                        alias,
                        scene=scene,
                        protagonist_id=protagonist_id,
                        scope_world=scope_world,
                    )
                )
    return frozenset(referenced)


class KnowledgeProjector:
    """Projects immutable package knowledge from the canonical fact store."""

    def __init__(
        self,
        *,
        max_candidates: int = 4,
        max_continuity_records: int = 12,
        max_committed_knowledge: int = 24,
        max_sayable_knowledge: int = 8,
    ) -> None:
        if max_candidates < 1:
            raise ValueError("max_candidates must be positive")
        if max_committed_knowledge < 1:
            raise ValueError("max_committed_knowledge must be positive")
        if max_sayable_knowledge < 1:
            raise ValueError("max_sayable_knowledge must be positive")
        self.max_candidates = max_candidates
        self.max_continuity_records = max_continuity_records
        self.max_committed_knowledge = max_committed_knowledge
        self.max_sayable_knowledge = max_sayable_knowledge

    def project(self, state: RuntimeState, audience_id: str, player_input: str) -> TurnKnowledgeContext:
        frame = next(
            frame for frame in state.package.knowledge.scene_frames if frame.scene_id == state.current_scene_id
        )
        scene = next(scene for scene in state.package.scenes if scene.metadata.scene_id == state.current_scene_id)
        world = world_for(state.package, state.facts)
        protagonist_id = state.package.world.protagonist_id
        committed = self._committed_for(state, audience_id, player_input)
        scene_hidden_ids = self._effect_item_ids(state)
        protagonist_moving_facts = {
            fact_id
            for fact_id, effects in state.package.world.fact_effects.items()
            if any(effect.move == state.package.world.protagonist_id for effect in effects)
        }
        hides_protagonist_move = any(
            item.id in scene_hidden_ids
            and any(
                operation.op == "assert" and operation.fact_id in protagonist_moving_facts
                for operation in item.establishes
            )
            for item in state.package.knowledge.knowledge
        )
        # What a speaker may say aloud is a tighter, scene-focused slice than the
        # grounding basis; they are not the same list.
        sayable = self._established_for(state, audience_id, self.max_sayable_knowledge)
        established_ids = tuple(sorted({entity_id for item in committed for entity_id in item.entity_ids}))
        referenced_ids = self._referenced_established_ids(state, player_input, established_ids)
        reveal_universe = self._candidates(state, audience_id, referenced_ids)
        return TurnKnowledgeContext(
            scene_id=state.current_scene_id,
            phase=state.phase,
            scene_frame=(
                ""
                if hides_protagonist_move
                else self._scene_frame(state, frame.situation, scene, world, protagonist_id, player_input)
            ),
            pressure=frame.pressure,
            audience_id=audience_id,
            committed_knowledge=committed,
            sayable_knowledge=sayable,
            established_entity_ids=established_ids,
            referenced_entity_ids=referenced_ids,
            continuity_ids=tuple(record.id for record in state.turn_records[-self.max_continuity_records :]),
            candidates=reveal_universe[: self.max_candidates],
            reveal_universe=reveal_universe,
            handoff_deliveries=tuple(
                delivery for delivery in state.package.deliveries if delivery.fact_id in state.staged_handoff_fact_ids
            ),
            scene_hidden_ids=scene_hidden_ids,
        )

    @staticmethod
    def _scene_frame(state, situation, scene, world, protagonist_id: str, player_input: str) -> str:
        if not player_input or together_or_unplaced(world, protagonist_id, scene.metadata.location_id):
            return situation
        area_ids = (world.area(protagonist_id), *world.chain(protagonist_id))
        descriptions = {location.id: location.description for location in state.package.world.locations}
        return next(
            (descriptions[area_id] for area_id in area_ids if area_id in descriptions and descriptions[area_id]),
            "",
        )

    def _effect_item_ids(self, state: RuntimeState) -> tuple[str, ...]:
        """Return established current-scene claims with any world effect."""

        effect_facts = set(state.package.world.fact_effects)
        return tuple(
            item.id
            for item in state.package.knowledge.knowledge
            if state.current_scene_id in item.available_in_scenes
            and self._established(item, state)
            and any(operation.op == "assert" and operation.fact_id in effect_facts for operation in item.establishes)
        )

    def _established_for(self, state: RuntimeState, audience_id: str, limit: int) -> tuple[ProjectedKnowledge, ...]:
        """Project established knowledge, bounded so a long story cannot outgrow one turn.

        Committed knowledge accumulates for the whole playthrough, so an unbounded
        projection makes every later turn slower than the last until the narration
        call times out and the player loses the turn. Only knowledge available in
        the current scene is projected, then the numeric cap keeps that scene bounded.

        The resolver validates segment grounding against this same projection, so
        the provider is never asked to ground on knowledge it was not shown.
        """

        established = [
            item
            for item in state.package.knowledge.knowledge
            if state.current_scene_id in item.available_in_scenes
            and self._established(item, state)
            and self._visible_to(item, audience_id)
            # Scene framing belongs in context, not in a character's dialogue.
            and not (item.source.kind == "scene_entry" and item.audience.kind == "public")
        ]
        world = world_for(state.package, state.facts)
        protagonist_id = state.package.world.protagonist_id
        established = [item for item in established if self._within_reach(item, world, protagonist_id)]
        if len(established) <= limit:
            return tuple(self._projected(item) for item in established)
        return tuple(self._projected(item) for item in established[-limit:])

    def _committed_for(
        self, state: RuntimeState, audience_id: str, player_input: str
    ) -> tuple[ProjectedKnowledge, ...]:
        """Project the scene's own knowledge, plus outside knowledge the player asked about.

        Nothing is scoped away. The whole store stays searchable on every turn:
        what the current scene's beats describe is always sent, because it is
        what the turn is about, and everything else reaches the narrator only
        when the player's own words reach for it. An earlier scene nobody
        mentions therefore costs no tokens, while a player who raises it gets
        continuity instead of a blank. Scene-entry framing is not recalled
        outside its own scene because it describes that scene's opening. This
        is retrieval on reference, not a
        ranked cut to a budget; the numeric bound below is only a backstop
        against a pathological package, never the selection mechanism.
        Naming a person alone does not recall knowledge from an earlier scene.

        The resolver validates segment grounding against this same projection,
        so the provider is never asked to ground on knowledge it was not shown.
        """

        visible = [
            item
            for item in state.package.knowledge.knowledge
            if self._established(item, state) and self._visible_to(item, audience_id)
        ]
        world = world_for(state.package, state.facts)
        protagonist_id = state.package.world.protagonist_id
        visible = [item for item in visible if self._within_reach(item, world, protagonist_id)]
        in_scene = [item for item in visible if state.current_scene_id in item.available_in_scenes]
        scene_ids = {item.id for item in in_scene}
        referenced_entity_ids = _input_referenced_entity_ids(
            state.package.world,
            player_input,
            scope_world=world_for(state.package, state.facts),
            scene=next(scene for scene in state.package.scenes if scene.metadata.scene_id == state.current_scene_id),
            protagonist_id=state.package.world.protagonist_id,
        )
        character_ids = {entity.id for entity in state.package.world.npcs}
        character_ids.add(state.package.world.protagonist_id)
        recalled = [
            item
            for item in visible
            if item.id not in scene_ids
            and item.source.kind != "scene_entry"
            and self._player_refers_to(item, referenced_entity_ids, frozenset(character_ids))
        ]
        selected = [*in_scene, *recalled][: self.max_committed_knowledge]
        return tuple(self._projected(item) for item in selected)

    @staticmethod
    def _within_reach(item: KnowledgeDefinition, world, protagonist_id: str) -> bool:
        return not item.reach_entity_ids or all(
            together_or_unplaced(world, protagonist_id, entity_id) for entity_id in item.reach_entity_ids
        )

    @staticmethod
    def _player_refers_to(
        item: KnowledgeDefinition,
        referenced_entity_ids: frozenset[str],
        character_ids: frozenset[str],
    ) -> bool:
        """Decide whether the player's own words reach for one out-of-scene claim."""

        non_character_ids = referenced_entity_ids - character_ids
        return bool(non_character_ids & {*item.entity_ids, *item.relevance.entity_ids})

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
        referenced = _input_referenced_entity_ids(
            state.package.world,
            player_input,
            scope_world=world_for(state.package, state.facts),
            scene=next(scene for scene in state.package.scenes if scene.metadata.scene_id == state.current_scene_id),
            protagonist_id=state.package.world.protagonist_id,
        )
        return tuple(sorted(entity_id for entity_id in established_ids if entity_id in referenced))

    def _candidates(
        self, state: RuntimeState, audience_id: str, referenced_ids: tuple[str, ...]
    ) -> tuple[RevealCandidate, ...]:
        candidates: list[KnowledgeDefinition] = []
        for knowledge_id in state.package.knowledge_indexes.scene_to_candidates[state.current_scene_id]:
            item = state.package.knowledge_indexes.by_id[knowledge_id]
            if not explain_reveal(state, audience_id, item).eligible:
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
        return tuple(self._candidate(item) for item in candidates)

    @staticmethod
    def _candidate(item: KnowledgeDefinition) -> RevealCandidate:
        """Expose only the player-safe selection affordance to the provider."""

        return RevealCandidate(
            id=item.id,
            statement=item.statement,
            earn_when=item.earn_when,
            must_convey=item.must_convey,
            action_evidence=item.action_evidence,
            delivery_text=item.delivery_text,
            action_contract=item.action_contract,
        )
