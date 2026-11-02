"""Pure resolution of fact-qualified knowledge delivery text."""

from __future__ import annotations

from collections.abc import Collection

from storygame.runtime.facts import FactStore
from storygame.story_package.models import KnowledgeDefinition


class _AmbiguousDelivery:
    __slots__ = ()


AMBIGUOUS = _AmbiguousDelivery()


def true_fact_ids(facts: FactStore) -> frozenset[str]:
    """Return fact IDs whose stored assertion value is exactly ``"true"``."""

    return frozenset(
        fact.predicate for fact in facts.asserted if (fact.value if fact.value is not None else fact.object) == "true"
    )


def resolve_delivery_text(item: KnowledgeDefinition, true_fact_ids: Collection[str]) -> str | None | _AmbiguousDelivery:
    """Resolve one delivery sentence from the facts true at projection time."""

    variants = getattr(item, "delivery_variants", ())
    base_text = getattr(item, "delivery_text", None)
    if not variants:
        return base_text
    facts = set(true_fact_ids)
    matches = tuple(variant for variant in variants if set(variant.requires) <= facts)
    if len(matches) > 1:
        return AMBIGUOUS
    return matches[0].text if matches else base_text
