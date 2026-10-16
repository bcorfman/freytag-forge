"""Short-lived, fact-derived referents for exact action evidence matching."""

from __future__ import annotations

import re

from storygame.runtime.candidate_matcher import _SYNONYM_CLASSES, _words
from storygame.runtime.knowledge import _entity_surface_forms

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


def recent_cue_referent_text(state, player_input: str) -> str:
    """Return one committed cue owner for evidence matching, or an empty string."""

    record = _current_scene_record(state)
    if record is None or not record.reveal_ids:
        return ""

    entries = [
        state.package.knowledge_indexes.by_id[reveal_id]
        for reveal_id in record.reveal_ids
        if reveal_id in state.package.knowledge_indexes.by_id
    ]
    entries = [entry for entry in entries if isinstance(entry.delivery_text, str) and entry.delivery_text.strip()]
    if not entries:
        return ""

    protagonist_id = state.package.world.protagonist_id
    named_ids = _named_entity_ids(state, player_input)
    owner_ids = {
        entity_id
        for entry in entries
        for entity_id in entry.entity_ids
        if entity_id != protagonist_id and entity_id not in named_ids
    }
    if len(owner_ids) != 1:
        return ""

    delivery_words = set().union(*(_content_words(entry.delivery_text) for entry in entries))
    if not delivery_words.intersection(_content_words(player_input)):
        return ""

    owner_id = next(iter(owner_ids))
    owner = next((entity for entity in _entities(state) if entity.id == owner_id), None)
    return owner.name if owner is not None else ""
