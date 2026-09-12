"""Deterministic pre-commit checks for provider-authored narration."""

from __future__ import annotations

import re

from storygame.runtime.contracts import NarrationSegment, ResolvedTurnProposal
from storygame.runtime.knowledge import KnowledgeProjector, TurnKnowledgeContext
from storygame.runtime.state import RuntimeState
from storygame.runtime.validation import ProposalValidationError

_WORD_BOUNDARY = r"(?<!\w){form}(?!\w)"


class NarrationSafetyValidator:
    """Reject prose that outruns the cloned, audience-scoped candidate state."""

    def validate(
        self,
        state: RuntimeState,
        candidate_state: RuntimeState,
        proposal: ResolvedTurnProposal,
        projector: KnowledgeProjector,
        player_input: str,
    ) -> TurnKnowledgeContext:
        post_projection = projector.project(candidate_state, "player", player_input)
        self._validate_selection_backing(state, proposal)
        self._validate_segments(state, candidate_state, proposal.segments, post_projection, projector, player_input)
        return post_projection

    def _validate_selection_backing(self, state: RuntimeState, proposal: ResolvedTurnProposal) -> None:
        selected = tuple(proposal.selected_knowledge_ids)
        if not selected:
            if proposal.events:
                raise ProposalValidationError(
                    "an event must be backed by the selected knowledge", code="selection_source_mismatch"
                )
            return
        if len(proposal.events) != 1:
            raise ProposalValidationError(
                "selected knowledge must resolve to one package source", code="selection_source_mismatch"
            )
        event = proposal.events[0]
        if event.knowledge_ids != selected:
            raise ProposalValidationError(
                "resolved event does not match the selected knowledge", code="selection_source_mismatch"
            )
        source_key = f"storylet:{event.event_id}:{event.realization_id}"
        source_ids = state.package.knowledge_indexes.source_to_knowledge.get(source_key, ())
        if not source_ids or selected[0] not in source_ids:
            raise ProposalValidationError(
                "resolved event source does not match the selected knowledge", code="selection_source_mismatch"
            )
        expected = tuple(
            sorted(
                (operation.op, operation.fact_id, self._normalize(str(operation.value)))
                for knowledge_id in source_ids
                for operation in state.package.knowledge_indexes.by_id[knowledge_id].establishes
            )
        )
        actual = tuple(
            sorted(
                (operation.operation, operation.fact.predicate, self._normalize(str(operation.fact.value)))
                for operation in event.operations
            )
        )
        if actual != expected:
            raise ProposalValidationError(
                "resolved event effects do not match the package source", code="selection_source_mismatch"
            )

    def _validate_segments(
        self,
        state: RuntimeState,
        candidate_state: RuntimeState,
        segments: tuple[NarrationSegment, ...],
        post_projection: TurnKnowledgeContext,
        projector: KnowledgeProjector,
        player_input: str,
    ) -> None:
        indexes = state.package.knowledge_indexes
        allowed_knowledge = {item.id for item in post_projection.committed_knowledge}
        allowed_entities = set(post_projection.established_entity_ids)
        scene = next(
            item for item in state.package.scenes if item.metadata.scene_id == candidate_state.current_scene_id
        )
        allowed_entities.update((scene.metadata.location_id, *scene.metadata.participant_ids, *scene.metadata.item_ids))
        npc_ids = {npc.id for npc in state.package.world.npcs}
        known_terms = {
            term.casefold()
            for terms in indexes.audience_to_known_terms.values()
            for term in terms
            if len(term.split()) > 1 and term.casefold() in indexes.term_to_knowledge
        }
        handoff_terms = {
            term.casefold()
            for delivery in state.package.deliveries
            if delivery.fact_id in candidate_state.staged_handoff_fact_ids
            for group in delivery.must_convey
            for term in group
            if len(term.split()) > 1
        }
        handoff_committed_ids = {
            item.id
            for item in state.package.knowledge.knowledge
            if KnowledgeProjector._established(item, candidate_state) and KnowledgeProjector._visible_to(item, "player")
        }
        handoff_text = " ".join(
            delivery.fallback_text
            for delivery in state.package.deliveries
            if delivery.fact_id in candidate_state.staged_handoff_fact_ids
        ).casefold()
        projected_beat_text = self._projected_beat_text(state)

        for segment in segments:
            grounding = set(segment.grounding_ids)
            unknown = grounding - set(indexes.by_id)
            if unknown:
                raise ProposalValidationError(
                    "segment grounding names unknown knowledge", code="unknown_grounding_reference"
                )
            invisible = grounding - allowed_knowledge
            if invisible:
                raise ProposalValidationError(
                    "segment grounding is not visible in the post-candidate projection",
                    code="invisible_grounding_reference",
                )
            if segment.kind == "dialogue" and segment.speaker_id is None:
                raise ProposalValidationError("dialogue segments require a speaker", code="dialogue_speaker_missing")
            if segment.speaker_id is not None:
                if segment.speaker_id not in npc_ids:
                    raise ProposalValidationError("dialogue names an unknown speaker", code="unknown_dialogue_speaker")
                speaker_projection = projector.project(candidate_state, segment.speaker_id, player_input)
                sayable = {item.id for item in speaker_projection.sayable_knowledge}
                if grounding - sayable:
                    raise ProposalValidationError(
                        "dialogue grounding is not sayable by its speaker",
                        code="dialogue_grounding_not_sayable",
                    )

            text = self._normalize(segment.text)
            for form, entity_ids in indexes.entity_alias_to_entities.items():
                if not self._contains(text, form):
                    continue
                entity_set = set(entity_ids)
                statement_covers_entity = any(
                    grounding_id in indexes.by_id
                    and any(
                        self._contains(indexes.by_id[grounding_id].statement.casefold(), entity_form)
                        for entity_form in (form,)
                    )
                    for grounding_id in grounding
                )
                if (
                    not entity_set & allowed_entities
                    and not statement_covers_entity
                    and not self._contains(handoff_text, form)
                ):
                    raise ProposalValidationError(
                        f"narration mentions an unavailable entity '{form}'", code="narration_known_term_leak"
                    )

            for form in known_terms:
                if not self._contains(text, form):
                    continue
                knowledge_ids = set(indexes.term_to_knowledge.get(form, ()))
                if any(self._contains(handoff_form, form) for handoff_form in handoff_terms) or (
                    candidate_state.staged_handoff_fact_ids and knowledge_ids & handoff_committed_ids
                ):
                    continue
                statement_covers_term = any(
                    grounding_id in indexes.by_id
                    and self._contains(indexes.by_id[grounding_id].statement.casefold(), form)
                    for grounding_id in grounding
                )
                if not knowledge_ids & allowed_knowledge:
                    if statement_covers_term:
                        continue
                    if self._contains(projected_beat_text, form):
                        continue
                    raise ProposalValidationError(
                        f"narration mentions unavailable knowledge '{form}'",
                        code="narration_known_term_leak",
                    )
                if not knowledge_ids & grounding and not statement_covers_term:
                    raise ProposalValidationError(
                        f"narration does not ground the knowledge term '{form}'",
                        code="uncited_knowledge",
                    )

            for form in indexes.protected_terms:
                if self._contains(text, form):
                    knowledge_ids = set(indexes.term_to_knowledge.get(form, ()))
                    statement_covers_term = any(
                        grounding_id in indexes.by_id
                        and self._contains(indexes.by_id[grounding_id].statement.casefold(), form)
                        for grounding_id in grounding
                    )
                    if (not knowledge_ids or not knowledge_ids & grounding) and not statement_covers_term:
                        raise ProposalValidationError(
                            f"narration mentions protected knowledge '{form}'",
                            code="protected_narration_leak",
                        )

    @staticmethod
    def _contains(text: str, form: str) -> bool:
        normalized_text = NarrationSafetyValidator._normalize(text)
        normalized_form = NarrationSafetyValidator._normalize(form)
        return bool(re.search(_WORD_BOUNDARY.format(form=re.escape(normalized_form)), normalized_text))

    @staticmethod
    def _normalize(value: str) -> str:
        return " ".join(value.casefold().split())

    @staticmethod
    def _projected_beat_text(state: RuntimeState) -> str:
        """Return only the prose and details of beats sent on this turn."""

        projected = set(state.last_turn_delivery.beats_projected)
        return " ".join(
            " ".join((beat.prose, *beat.details))
            for scene in state.package.scenes
            for anchor, beat in scene.beats.items()
            if anchor in projected
        )
