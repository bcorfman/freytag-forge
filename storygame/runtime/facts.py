"""Typed, assertable runtime facts and their small canonical store."""

from __future__ import annotations

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


class FactStore(BaseModel):
    """Mutable fact authority for the future scene runtime."""

    model_config = ConfigDict(extra="forbid")
    asserted: set[Fact] = Field(default_factory=set)

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

    def clone(self) -> FactStore:
        """Return an independent candidate store for all-or-nothing turns."""

        return FactStore(asserted=set(self.asserted))
