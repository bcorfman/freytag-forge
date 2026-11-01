"""Short-lived, fact-derived referents for exact action evidence matching."""

from __future__ import annotations

import re
from collections.abc import Iterable

from storygame.runtime.candidate_matcher import _SYNONYM_CLASSES, _words
from storygame.runtime.delivery_text import resolve_delivery_text
from storygame.runtime.knowledge import _entity_surface_forms
from storygame.runtime.reveal_eligibility import explain_reveal

_STOPWORDS = frozenset(
    {
        "a",
        "an",
        "and",
        "at",
        "along",
        "by",
        "for",
        "from",
        "her",
        "his",
        "i",
        "in",
        "into",
        "is",
        "it",
        "its",
        "my",
        "of",
        "on",
        "over",
        "that",
        "the",
        "their",
        "them",
        "this",
        "to",
        "through",
        "with",
        "you",
    }
)
_SYNONYM_WORDS = frozenset(
    word for synonym_class in _SYNONYM_CLASSES for phrase in synonym_class for word in _words(phrase)
)


def _entities(state):
    world = state.package.world
    return (*world.locations, *world.npcs, *world.groups, *world.items)


def _named_entity_ids(state, player_input: str) -> frozenset[str]:
    folded_input = player_input.casefold()
    return frozenset(
        entity.id
        for entity in _entities(state)
        if any(re.search(rf"(?<!\w){re.escape(form)}(?!\w)", folded_input) for form in _entity_surface_forms(entity))
    )


def _content_words(value: str) -> frozenset[str]:
    return frozenset(word for word in _words(value) if word not in _STOPWORDS and word not in _SYNONYM_WORDS)


def _current_scene_record(state):
    """Return the latest accepted non-transition turn after the current scene entry."""

    if not state.turn_records:
        return None
    record = state.turn_records[-1]
    if state.turn_index <= state.scene_entered_at_turn or getattr(record, "transition_id", None) is not None:
        return None
    return record


def _referent_from_evidence(state, player_input: str, evidence: Iterable[tuple[object, str]]) -> str:
    evidence = tuple((entry, text) for entry, text in evidence if isinstance(text, str) and text.strip())
    if not evidence:
        return ""

    protagonist_id = state.package.world.protagonist_id
    named_ids = _named_entity_ids(state, player_input)
    owner_ids = {
        entity_id
        for entry, _text in evidence
        for entity_id in (getattr(entry, "reach_entity_ids", ()) or entry.entity_ids)
        if entity_id != protagonist_id and entity_id not in named_ids
    }
    if len(owner_ids) != 1:
        return ""

    evidence_words = set().union(*(_content_words(text) for _entry, text in evidence))
    if not evidence_words.intersection(_content_words(player_input)):
        return ""

    owner_id = next(iter(owner_ids))
    owner = next((entity for entity in _entities(state) if entity.id == owner_id), None)
    return owner.name if owner is not None else ""


def _staged_cue_evidence(state) -> tuple[tuple[object, str], ...]:
    if state.turn_index <= state.scene_entered_at_turn:
        return ()

    evidence: list[tuple[object, str]] = []
    for stage in getattr(state, "cue_stages", ()):
        if (
            stage.fact_id not in state.delivered_cue_ids
            or stage.last_turn != state.turn_index - 1
            or stage.visit_entered_at != state.scene_entered_at_turn
        ):
            continue
        delivery = next(
            (
                delivery
                for delivery in state.package.deliveries
                if delivery.fact_id == stage.fact_id and delivery.scene_id == state.current_scene_id
            ),
            None,
        )
        if delivery is None:
            continue
        cue_text = delivery.escalation_text if stage.stage == 2 else delivery.cue_text
        if not cue_text:
            continue
        fact_ids = {delivery.fact_id, *(cost.fact_id for cost in delivery.costs if cost.op == "assert")}
        knowledge_ids = {
            knowledge_id
            for fact_id in fact_ids
            for knowledge_id in state.package.knowledge_indexes.facts_to_knowledge.get(fact_id, ())
        }
        for knowledge_id in knowledge_ids:
            entry = state.package.knowledge_indexes.by_id[knowledge_id]
            if state.current_scene_id in entry.available_in_scenes and explain_reveal(state, "player", entry).eligible:
                evidence.append((entry, cue_text))
    return tuple(evidence)


def recent_cue_referent_text(state, player_input: str) -> str:
    """Return one recent reveal or cue owner for evidence matching, or empty string."""

    record = _current_scene_record(state)
    if record is None:
        return ""

    facts = getattr(state, "facts", None)
    true_fact_ids = {fact.predicate for fact in getattr(facts, "asserted", ()) if str(fact.value).lower() == "true"}
    evidence = []
    for reveal_id in record.reveal_ids:
        entry = state.package.knowledge_indexes.by_id.get(reveal_id)
        if entry is None:
            continue
        text = resolve_delivery_text(entry, true_fact_ids)
        if isinstance(text, str) and text.strip():
            evidence.append((entry, text))
    evidence.extend(_staged_cue_evidence(state))
    return _referent_from_evidence(state, player_input, evidence)
