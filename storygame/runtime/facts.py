"""Typed, assertable runtime facts and their small canonical store."""

from __future__ import annotations

from collections.abc import Callable, Iterable, Mapping
from typing import Any, Self

from pydantic import BaseModel, ConfigDict, Field, PrivateAttr


class Fact(BaseModel):
    """One canonical assertion; projections must never be used as its authority."""

    model_config = ConfigDict(extra="forbid", frozen=True)
    predicate: str = Field(pattern=r"^[a-z][a-z0-9_]*$", max_length=64)
    subject: str = Field(min_length=1, max_length=120)
    object: str | None = Field(default=None, max_length=120)
    value: str | None = Field(default=None, max_length=1200)

    @property
    def key(self) -> tuple[str, str, str | None, str | None]:
        return self.predicate, self.subject, self.object, self.value


class _FactSet(set[Fact]):
    def __init__(self, values: Iterable[Fact] = (), on_change: Callable[[], None] | None = None) -> None:
        super().__init__(values)
        self._on_change = on_change

    def __deepcopy__(self, memo: dict[int, Any]) -> _FactSet:
        copied = _FactSet(self)
        memo[id(self)] = copied
        return copied

    def _changed(self) -> None:
        if self._on_change is not None:
            self._on_change()

    def add(self, element: Fact) -> None:
        super().add(element)
        self._changed()

    def discard(self, element: Fact) -> None:
        super().discard(element)
        self._changed()

    def remove(self, element: Fact) -> None:
        super().remove(element)
        self._changed()

    def pop(self) -> Fact:
        element = super().pop()
        self._changed()
        return element

    def clear(self) -> None:
        super().clear()
        self._changed()

    def update(self, *others: Iterable[Fact]) -> None:
        try:
            super().update(*others)
        finally:
            self._changed()

    def intersection_update(self, *others: Iterable[Fact]) -> None:
        try:
            super().intersection_update(*others)
        finally:
            self._changed()

    def difference_update(self, *others: Iterable[Fact]) -> None:
        try:
            super().difference_update(*others)
        finally:
            self._changed()

    def symmetric_difference_update(self, other: Iterable[Fact]) -> None:
        try:
            super().symmetric_difference_update(other)
        finally:
            self._changed()

    def __ior__(self, other: Iterable[Fact]) -> _FactSet:
        self.update(other)
        return self

    def __iand__(self, other: Iterable[Fact]) -> _FactSet:
        self.intersection_update(other)
        return self

    def __isub__(self, other: Iterable[Fact]) -> _FactSet:
        self.difference_update(other)
        return self

    def __ixor__(self, other: Iterable[Fact]) -> _FactSet:
        self.symmetric_difference_update(other)
        return self


class FactStore(BaseModel):
    """Mutable fact authority for the future scene runtime."""

    model_config = ConfigDict(extra="forbid", validate_assignment=True)
    asserted: set[Fact] = Field(default_factory=set)
    _by_predicate: dict[str, set[Fact]] = PrivateAttr(default_factory=dict)
    _version: int = PrivateAttr(default=0)
    _knowledge_guards_cache: tuple[int, int, Any] | None = PrivateAttr(default=None)

    def model_post_init(self, __context: Any) -> None:
        object.__setattr__(self, "asserted", _FactSet(self.asserted, self._on_asserted_mutation))
        self._rebuild_index()

    def __setattr__(self, name: str, value: Any) -> None:
        super().__setattr__(name, value)
        if name == "asserted" and "asserted" in self.__dict__:
            object.__setattr__(self, "asserted", _FactSet(self.asserted, self._on_asserted_mutation))
            self._rebuild_index()
            self._version += 1
            self._knowledge_guards_cache = None

    def _on_asserted_mutation(self) -> None:
        self._rebuild_index()
        self._version += 1
        self._knowledge_guards_cache = None

    def _rebuild_index(self) -> None:
        by_predicate: dict[str, list[Fact]] = {}
        for fact in self.asserted:
            by_predicate.setdefault(fact.predicate, []).append(fact)
        self._by_predicate = {predicate: set(facts) for predicate, facts in by_predicate.items()}

    @property
    def version(self) -> int:
        """Monotonic version for caches derived from the asserted facts."""

        return self._version

    def matching(self, predicate: str, subject: str | None = None) -> tuple[Fact, ...]:
        candidates = self._by_predicate.get(predicate, ())
        if subject is not None:
            candidates = (fact for fact in candidates if fact.subject == subject)
        return tuple(sorted(candidates, key=lambda fact: fact.key))

    def __eq__(self, other: object) -> bool:
        if isinstance(other, FactStore):
            return self.asserted == other.asserted
        return super().__eq__(other)

    def assert_fact(self, fact: Fact) -> None:
        self.asserted.add(fact)

    def retract_fact(self, fact: Fact) -> None:
        self.asserted.discard(fact)

    def model_copy(self, *, update: Mapping[str, Any] | None = None, deep: bool = False) -> Self:
        copied = super().model_copy(update=update, deep=deep)
        copied.asserted = set(copied.asserted)
        return copied

    def __deepcopy__(self, memo: dict[int, Any]) -> Self:
        copied = super().__deepcopy__(memo)
        copied.asserted = set(copied.asserted)
        return copied

    def clone(self) -> FactStore:
        """Return an independent candidate store for all-or-nothing turns."""

        return FactStore(asserted=set(self.asserted))
