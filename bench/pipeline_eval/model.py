"""Data contracts and JSON loading for pipeline evaluations.

``STATE_VOCABULARY`` is the contract arms report against. Mapping it to engine
facts is a Phase 5 task.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Literal

Split = Literal["diagnostic", "held_out"]
CreationKind = Literal["none", "descriptive", "interactable", "route_clue_person_capability"]

# This is the contract arms report against. Mapping these labels to engine facts
# is intentionally deferred to the Phase 5 task; the Phase 3 harness only
# accepts state claims that have been explicitly grounded here.
STATE_VOCABULARY: dict[str, tuple[str, ...]] = {
    "memory_card": ("beneath_michelle_drawer", "with_kristin", "not_with_kristin"),
    "kristin": ("truck_driver_seat",),
    "kristin_truck": ("at_workstation", "away"),
    "kristin_laptop": ("truck_passenger_seat",),
}


def _tuple(value: Any, field: str) -> tuple[Any, ...]:
    if value is None:
        return ()
    if not isinstance(value, list | tuple):
        raise ValueError(f"{field} must be a list")
    return tuple(value)


@dataclass(frozen=True)
class Expectation:
    reference: str | None = None
    action: str | None = None
    state: dict[str, str] | None = None
    prose_includes: tuple[str, ...] = ()
    prose_excludes: tuple[str, ...] = ()
    prose_must_not_assert: tuple[str, ...] = ()
    required_reveals: tuple[str, ...] = ()
    allowed_reveals: tuple[str, ...] = ()
    creation: CreationKind | None = None
    forced_progress: bool | None = None
    clarification: bool | None = None
    clarification_leaves_clock_unchanged: bool | None = None

    def __post_init__(self) -> None:
        if self.creation not in (None, "none", "descriptive", "interactable", "route_clue_person_capability"):
            raise ValueError("creation must be a supported creation kind")


@dataclass(frozen=True)
class EvalCase:
    id: str
    category: str
    split: Split
    scene: str
    setup_facts: tuple[str, ...]
    commands: tuple[str, ...]
    save_load_after: int | None
    expect: Expectation

    def __post_init__(self) -> None:
        if self.split not in ("diagnostic", "held_out"):
            raise ValueError(f"invalid split: {self.split}")
        if not self.commands:
            raise ValueError("commands must be non-empty")
        if self.save_load_after is not None and not 0 <= self.save_load_after < len(self.commands):
            raise ValueError("save_load_after must be a command index")


@dataclass(frozen=True)
class TurnObservation:
    reference: str | None = None
    action: str | None = None
    state: dict[str, str] | None = None
    prose: str = ""
    revealed_ids: tuple[str, ...] = ()
    created: tuple[tuple[str, CreationKind], ...] = ()
    forced_progress: bool = False
    clarified: bool = False
    latency_s: float = 0.0
    requests: int = 0
    tokens: int = 0

    def __post_init__(self) -> None:
        for _, kind in self.created:
            if kind not in ("none", "descriptive", "interactable", "route_clue_person_capability"):
                raise ValueError(f"invalid creation kind: {kind}")
            if kind == "none":
                raise ValueError("created entries cannot have kind 'none'")


def _expectation(raw: dict[str, Any]) -> Expectation:
    values = dict(raw)
    for key in (
        "prose_includes",
        "prose_excludes",
        "prose_must_not_assert",
        "required_reveals",
        "allowed_reveals",
    ):
        values[key] = _tuple(values.get(key), key)
    if values.get("state") is not None:
        if not isinstance(values["state"], dict):
            raise ValueError("expect.state must be an object")
        values["state"] = {str(key): str(value) for key, value in values["state"].items()}
        for key, value in values["state"].items():
            if key not in STATE_VOCABULARY:
                raise ValueError(f"unknown state key: {key}")
            if value not in STATE_VOCABULARY[key]:
                raise ValueError(f"invalid value for state {key}: {value}")
    return Expectation(**values)


def _case(raw: dict[str, Any]) -> EvalCase:
    if not isinstance(raw, dict):
        raise ValueError("each case must be an object")
    commands = tuple(str(command) for command in _tuple(raw.get("commands"), "commands"))
    return EvalCase(
        id=str(raw["id"]),
        category=str(raw["category"]),
        split=raw["split"],
        scene=str(raw["scene"]),
        setup_facts=tuple(str(fact) for fact in _tuple(raw.get("setup_facts"), "setup_facts")),
        commands=commands,
        save_load_after=raw.get("save_load_after"),
        expect=_expectation(raw.get("expect", {})),
    )


def load_cases(path: str | Path) -> tuple[EvalCase, ...]:
    """Load and validate a JSON array, or an object containing ``cases``."""

    payload = json.loads(Path(path).read_text(encoding="utf-8"))
    if isinstance(payload, dict):
        payload = payload.get("cases")
    if not isinstance(payload, list):
        raise ValueError("cases JSON must be an array or an object with cases")
    cases = tuple(_case(item) for item in payload)
    ids = [case.id for case in cases]
    if len(ids) != len(set(ids)):
        raise ValueError("duplicate case id")
    return cases


def by_split(cases: tuple[EvalCase, ...], split: Split) -> tuple[EvalCase, ...]:
    if split not in ("diagnostic", "held_out"):
        raise ValueError(f"invalid split: {split}")
    return tuple(case for case in cases if case.split == split)
