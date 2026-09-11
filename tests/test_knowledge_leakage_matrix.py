"""Phase 5 deterministic checks for progressive knowledge projection."""

from __future__ import annotations

import json
from dataclasses import dataclass
from functools import cache
from hashlib import sha256
from pathlib import Path

from storygame.runtime.facts import Fact
from storygame.runtime.knowledge import KnowledgeProjector, TurnKnowledgeContext
from storygame.runtime.narration_safety import NarrationSafetyValidator
from storygame.runtime.state import RuntimeState
from storygame.story_package.loader import load_story_package

PACKAGE = load_story_package(Path("data/stories/continuity-initiative"))
MAX_PROJECTION_PAYLOAD_BYTES = 8_192


@dataclass(frozen=True)
class _MatrixObservation:
    scene_id: str
    audience_id: str
    knowledge_id: str
    context: TurnKnowledgeContext
    visible: bool
    step: str


def _scene_entity_ids(scene: object) -> set[str]:
    metadata = scene.metadata  # type: ignore[union-attr]
    entity_ids = {metadata.location_id, *metadata.participant_ids, *metadata.item_ids}
    entity_ids.update(
        entity_id
        for item in PACKAGE.knowledge.knowledge
        if metadata.scene_id in item.available_in_scenes
        for entity_id in (*item.entity_ids, *item.relevance.entity_ids)
    )
    return entity_ids


def _establish(state: RuntimeState, knowledge_id: str) -> None:
    item = PACKAGE.knowledge_indexes.by_id[knowledge_id]
    for effect in item.establishes:
        value = str(effect.value).lower() if isinstance(effect.value, bool) else str(effect.value)
        state.facts.assert_fact(Fact(predicate=effect.fact_id, subject="story", value=value))


def _positioned_state(scene: object, local_storylets: tuple[object, ...]) -> RuntimeState:
    state = RuntimeState.bootstrap(PACKAGE)
    metadata = scene.metadata  # type: ignore[union-attr]
    state.current_scene_id = metadata.scene_id
    state.phase = metadata.freytag_phase
    state.active_event_ids.update(
        item.source.storylet_id
        for item in local_storylets
        if item.source.storylet_id is not None  # type: ignore[union-attr]
    )
    return state


def _timeline_positions() -> dict[str, int]:
    return {scene.metadata.scene_id: index for index, scene in enumerate(PACKAGE.scenes)}


def _future_knowledge_ids(scene_index: int, positions: dict[str, int]) -> set[str]:
    return {
        item.id
        for item in PACKAGE.knowledge.knowledge
        if all(positions[scene_id] > scene_index for scene_id in item.available_in_scenes)
    }


def _entity_first_positions(positions: dict[str, int]) -> dict[str, int]:
    first_positions = {
        entity.id: len(PACKAGE.scenes)
        for group in (PACKAGE.world.locations, PACKAGE.world.npcs, PACKAGE.world.items)
        for entity in group
    }
    for index, scene in enumerate(PACKAGE.scenes):
        for entity_id in _scene_entity_ids(scene):
            first_positions[entity_id] = min(first_positions[entity_id], index)
    return first_positions


def _future_terms(scene_index: int) -> tuple[str, ...]:
    positions = _timeline_positions()
    scene_id = PACKAGE.scenes[scene_index].metadata.scene_id
    future_ids = _future_knowledge_ids(scene_index, positions)
    reachable_ids = {
        item.id
        for item in PACKAGE.knowledge.knowledge
        if any(positions[scene_id] <= scene_index for scene_id in item.available_in_scenes)
    }
    reachable_aliases = {
        NarrationSafetyValidator._normalize(alias)
        for item in PACKAGE.knowledge.knowledge
        if item.id in reachable_ids
        for alias in item.aliases
    }
    reachable_entity_ids = {
        entity_id
        for item in PACKAGE.knowledge.knowledge
        if item.id in reachable_ids
        for entity_id in (*item.entity_ids, *item.relevance.entity_ids)
    }
    reachable_entity_forms = {
        NarrationSafetyValidator._normalize(form)
        for form, entity_ids in PACKAGE.knowledge_indexes.entity_alias_to_entities.items()
        if reachable_entity_ids & set(entity_ids)
    }
    reachable_forms = reachable_aliases | reachable_entity_forms
    current_scene_text = " ".join(
        [
            *(frame.situation for frame in PACKAGE.knowledge.scene_frames if frame.scene_id == scene_id),
            *(frame.pressure for frame in PACKAGE.knowledge.scene_frames if frame.scene_id == scene_id),
            *(item.statement for item in PACKAGE.knowledge.knowledge if scene_id in item.available_in_scenes),
        ]
    )
    terms: set[str] = set()

    for term, owner_ids in PACKAGE.knowledge_indexes.term_to_knowledge.items():
        owners = set(owner_ids)
        normalized_term = NarrationSafetyValidator._normalize(term)
        # Single-word terms are common vocabulary, not leak signals.
        if (
            len(term.split()) > 1
            and future_ids & owners
            and normalized_term not in reachable_forms
            and not NarrationSafetyValidator._contains(current_scene_text, normalized_term)
        ):
            terms.add(normalized_term)

    first_positions = _entity_first_positions(positions)
    for form, entity_ids in PACKAGE.knowledge_indexes.entity_alias_to_entities.items():
        entity_positions = {first_positions[entity_id] for entity_id in entity_ids}
        if any(position > scene_index for position in entity_positions) and not any(
            position <= scene_index for position in entity_positions
        ):
            terms.add(NarrationSafetyValidator._normalize(form))

    return tuple(sorted(term for term in terms if term))


@cache
def _build_leakage_matrix() -> tuple[_MatrixObservation, ...]:
    observations: list[_MatrixObservation] = []
    projector = KnowledgeProjector()

    for _scene_index, scene in enumerate(PACKAGE.scenes):
        scene_id = scene.metadata.scene_id
        local_storylets = tuple(
            item
            for item in PACKAGE.knowledge.knowledge
            if scene_id in item.available_in_scenes and item.source.kind == "storylet_realization"
        )
        npc_ids = {npc.id for npc in PACKAGE.world.npcs}
        audience_ids = ("player", *(npc_id for npc_id in scene.metadata.participant_ids if npc_id in npc_ids))
        for audience_id in dict.fromkeys(audience_ids):
            state = _positioned_state(scene, local_storylets)
            for item in local_storylets:
                before = projector.project(state, audience_id, "Inspect the immediate situation.")
                observations.append(
                    _MatrixObservation(
                        scene_id=scene_id,
                        audience_id=audience_id,
                        knowledge_id=item.id,
                        context=before,
                        visible=KnowledgeProjector._visible_to(item, audience_id),
                        step=f"before:{item.id}",
                    )
                )
                if KnowledgeProjector._visible_to(item, audience_id):
                    _establish(state, item.id)
                after = projector.project(state, audience_id, "Inspect the immediate situation.")
                observations.append(
                    _MatrixObservation(
                        scene_id=scene_id,
                        audience_id=audience_id,
                        knowledge_id=item.id,
                        context=after,
                        visible=KnowledgeProjector._visible_to(item, audience_id),
                        step=f"after:{item.id}",
                    )
                )

    return tuple(observations)


def _assert_future_terms_absent(observation: _MatrixObservation, scene_index: int) -> None:
    payload = observation.context.model_dump_json()
    for term in _future_terms(scene_index):
        assert not NarrationSafetyValidator._contains(payload, term), (
            f"{observation.scene_id}/{observation.audience_id}/{observation.step} contains future term {term!r}"
        )


def _redacted_knowledge(ids: set[str]) -> list[dict[str, int | str]]:
    return [
        {
            "id": knowledge_id,
            "statement_sha256": sha256(
                PACKAGE.knowledge_indexes.by_id[knowledge_id].statement.encode("utf-8")
            ).hexdigest(),
            "character_count": len(PACKAGE.knowledge_indexes.by_id[knowledge_id].statement),
        }
        for knowledge_id in sorted(ids)
    ]


def test_leakage_matrix_omits_every_future_known_term() -> None:
    positions = _timeline_positions()
    observations = _build_leakage_matrix()

    for observation in observations:
        _assert_future_terms_absent(observation, positions[observation.scene_id])
        if observation.step.startswith("after:") and observation.visible:
            assert observation.knowledge_id in {item.id for item in observation.context.committed_knowledge}, (
                f"{observation.scene_id}/{observation.audience_id}/{observation.step} did not commit its reveal"
            )


def test_leakage_matrix_context_snapshot_stays_within_the_declared_payload_budget() -> None:
    observations = _build_leakage_matrix()
    snapshot: list[dict[str, object]] = []

    for observation in observations:
        committed_ids = sorted(item.id for item in observation.context.committed_knowledge)
        candidate_ids = sorted(item.id for item in observation.context.candidates)
        snapshot.append(
            {
                "scene_id": observation.scene_id,
                "audience_id": observation.audience_id,
                "step": observation.step,
                "committed_ids": committed_ids,
                "candidate_ids": candidate_ids,
                "payload_bytes": observation.context.payload_size(),
                "redacted_knowledge": _redacted_knowledge(set(committed_ids) | set(candidate_ids)),
            }
        )

    artifact_dir = Path("artifacts")
    artifact_dir.mkdir(exist_ok=True)
    (artifact_dir / "phase5-knowledge-leakage-matrix.json").write_text(
        json.dumps(snapshot, indent=2) + "\n", encoding="utf-8"
    )

    for observation in observations:
        assert observation.context.payload_size() < MAX_PROJECTION_PAYLOAD_BYTES, (
            f"projection payload regressed at {observation.scene_id}/{observation.audience_id}/"
            f"{observation.step}: {observation.context.payload_size()} bytes"
        )

    grouped: dict[tuple[str, str], list[_MatrixObservation]] = {}
    for observation in observations:
        grouped.setdefault((observation.scene_id, observation.audience_id), []).append(observation)
    for (scene_id, audience_id), entries in grouped.items():
        for before, after in zip(entries[::2], entries[1::2], strict=True):
            before_ids = {item.id for item in before.context.committed_knowledge}
            after_ids = {item.id for item in after.context.committed_knowledge}
            added_ids = after_ids - before_ids
            if not before.visible:
                assert added_ids == set(), (
                    f"committed diff regressed at {scene_id}/{audience_id}/{before.step}: "
                    f"expected no additions, got {sorted(added_ids)}"
                )
                continue

            if before.knowledge_id not in before_ids:
                assert before.knowledge_id in added_ids, (
                    f"committed diff regressed at {scene_id}/{audience_id}/{before.step}: "
                    f"expected targeted reveal {before.knowledge_id!r}, got {sorted(added_ids)}"
                )
            else:
                assert before.knowledge_id in after_ids, (
                    f"committed diff regressed at {scene_id}/{audience_id}/{before.step}: "
                    f"targeted reveal {before.knowledge_id!r} was not retained in {sorted(after_ids)}"
                )
            expected_establishes = PACKAGE.knowledge_indexes.by_id[before.knowledge_id].establishes
            expected_effects = {
                (
                    effect.op,
                    effect.fact_id,
                    str(effect.value).lower() if isinstance(effect.value, bool) else str(effect.value),
                )
                for effect in expected_establishes
            }
            unexplained_extra_ids = {
                knowledge_id
                for knowledge_id in added_ids - {before.knowledge_id}
                if not {
                    (
                        effect.op,
                        effect.fact_id,
                        str(effect.value).lower() if isinstance(effect.value, bool) else str(effect.value),
                    )
                    for effect in PACKAGE.knowledge_indexes.by_id[knowledge_id].establishes
                }
                <= expected_effects
            }
            assert not unexplained_extra_ids, (
                f"committed diff regressed at {scene_id}/{audience_id}/{before.step}: "
                f"unexplained extra ids {sorted(unexplained_extra_ids)} in {sorted(added_ids)}"
            )


def test_leakage_matrix_rejects_player_input_naming_every_future_entity() -> None:
    first_scene = PACKAGE.scenes[0]
    first_scene_id = first_scene.metadata.scene_id
    first_scene_entities = _scene_entity_ids(first_scene)
    first_scene_entities.update(
        entity_id
        for item in PACKAGE.knowledge.knowledge
        if first_scene_id in item.available_in_scenes
        for entity_id in (*item.entity_ids, *item.relevance.entity_ids)
    )
    world_entities = {
        entity.id for group in (PACKAGE.world.npcs, PACKAGE.world.locations, PACKAGE.world.items) for entity in group
    }
    projector = KnowledgeProjector()
    future_entity_ids = world_entities - first_scene_entities
    future_entity_terms = {
        NarrationSafetyValidator._normalize(form)
        for group in (PACKAGE.world.npcs, PACKAGE.world.locations, PACKAGE.world.items)
        for entity in group
        if entity.id in future_entity_ids
        for form in (entity.name, *entity.aliases)
    }

    for scene in PACKAGE.scenes[1:]:
        introduced_ids = _scene_entity_ids(scene) - first_scene_entities
        candidates = [
            entity
            for group in (PACKAGE.world.npcs, PACKAGE.world.locations, PACKAGE.world.items)
            for entity in group
            if entity.id in introduced_ids and entity.id in world_entities
        ]
        assert candidates, f"scene {scene.metadata.scene_id} introduced no probeable future entity"
        entity = candidates[0]
        player_input = f"Inspect {entity.name}."
        state = RuntimeState.bootstrap(PACKAGE)
        state.current_scene_id = first_scene_id
        state.phase = first_scene.metadata.freytag_phase
        projection = projector.project(state, "player", player_input)

        assert set(projection.referenced_entity_ids) <= first_scene_entities
        payload = projection.model_dump_json()
        for term in future_entity_terms:
            assert not NarrationSafetyValidator._contains(payload, term), (
                f"future entity probe for {scene.metadata.scene_id} leaked term {term!r}"
            )
