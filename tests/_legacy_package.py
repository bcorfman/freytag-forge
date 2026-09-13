from __future__ import annotations

from collections.abc import Iterable
from typing import Any


def legacy_package(package: Any, knowledge_ids: Iterable[str], *, strip_must_convey: bool = False) -> Any:
    """Return a package copy whose selected authored candidates are legacy."""

    legacy_ids = set(knowledge_ids)

    def update_item(item: Any) -> Any:
        if item.id not in legacy_ids:
            return item
        updates = {"delivery_text": None}
        if strip_must_convey:
            updates["must_convey"] = ()
        return item.model_copy(update=updates)

    catalog = package.knowledge.model_copy(
        update={
            "knowledge": tuple(update_item(item) for item in package.knowledge.knowledge),
        }
    )
    indexes = package.knowledge_indexes.model_copy(
        update={
            "by_id": {
                **package.knowledge_indexes.by_id,
                **{item_id: update_item(package.knowledge_indexes.by_id[item_id]) for item_id in legacy_ids},
            }
        }
    )
    return package.model_copy(update={"knowledge": catalog, "knowledge_indexes": indexes})
