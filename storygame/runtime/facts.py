"""Typed, assertable runtime facts and their small canonical store."""

from __future__ import annotations

from collections.abc import Mapping
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


class FactStore(BaseModel):
    """Mutable fact authority for the future scene runtime."""

    model_config = ConfigDict(extra="forbid")
    asserted: set[Fact] = Field(default_factory=set)
    _by_predicate: dict[str, set[Fact]] = PrivateAttr(default_factory=dict)
    _version: int = PrivateAttr(default=0)
    _knowledge_guards_cache: tuple[int, int, Any] | None = PrivateAttr(default=None)

    def model_post_init(self, __context: Any) -> None:
        self._rebuild_index()

    def __setattr__(self, name: str, value: Any) -> None:
        super().__setattr__(name, value)
        if name == "asserted" and "asserted" in self.__dict__:
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
        self._rebuild_index()
        self._version += 1
        self._knowledge_guards_cache = None

    def retract_fact(self, fact: Fact) -> None:
        self.asserted.discard(fact)
        self._rebuild_index()
        self._version += 1
        self._knowledge_guards_cache = None

    def model_copy(self, *, update: Mapping[str, Any] | None = None, deep: bool = False) -> Self:
        copied = super().model_copy(update=update, deep=deep)
        copied.asserted = set(copied.asserted)
        return copied

    def clone(self) -> FactStore:
        """Return an independent candidate store for all-or-nothing turns."""

        return FactStore(asserted=set(self.asserted))
