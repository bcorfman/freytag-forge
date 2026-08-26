"""Typed, assertable runtime facts and their small canonical store."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


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


@dataclass
class FactStore:
    """Mutable fact authority for the future scene runtime."""

    asserted: set[Fact] = field(default_factory=set)

    def has(self, predicate: str, subject: str, object: str | None = None, value: str | None = None) -> bool:
        return Fact(predicate=predicate, subject=subject, object=object, value=value) in self.asserted

    def matching(self, predicate: str, subject: str | None = None) -> tuple[Fact, ...]:
        return tuple(
            sorted(
                (
                    fact
                    for fact in self.asserted
                    if fact.predicate == predicate and (subject is None or fact.subject == subject)
                ),
                key=lambda fact: fact.key,
            )
        )

    def assert_fact(self, fact: Fact) -> None:
        self.asserted.add(fact)

    def retract_fact(self, fact: Fact) -> None:
        self.asserted.discard(fact)

    def as_json(self) -> list[dict[str, Any]]:
        return [fact.model_dump(mode="json") for fact in sorted(self.asserted, key=lambda item: item.key)]

    @classmethod
    def from_json(cls, values: object) -> FactStore:
        if not isinstance(values, list):
            raise ValueError("facts must be a list")
        return cls({Fact.model_validate(value) for value in values})
