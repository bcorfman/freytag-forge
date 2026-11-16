"""Preregistered experiment arms and deterministic stopping decisions."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

KEEP_RULE = "all_replicates_pass"
STOP_RULE = "stop_on_first_fail"


def _is_int(value: Any) -> bool:
    return isinstance(value, int) and not isinstance(value, bool)


def validate_prereg(d: Any) -> list[str]:
    """Return human-readable validation errors for a preregistration mapping."""

    if not isinstance(d, dict):
        return ["preregistration must be a JSON object."]

    errors: list[str] = []

    if not isinstance(d.get("id"), str) or not d.get("id"):
        errors.append("id must be a non-empty string.")

    arms = d.get("arms")
    if not isinstance(arms, list) or not arms:
        errors.append("arms must be a non-empty list of strings.")
    elif any(not isinstance(arm, str) or not arm for arm in arms):
        errors.append("arms must contain only non-empty strings.")
    elif len(set(arms)) != len(arms):
        errors.append("arms must contain unique names.")

    sample_size = d.get("sample_size", 3)
    if not _is_int(sample_size) or sample_size <= 0:
        errors.append("sample_size must be a positive integer.")

    adoption_sample_size = d.get("adoption_sample_size", 12)
    if not _is_int(adoption_sample_size) or adoption_sample_size <= 0:
        errors.append("adoption_sample_size must be a positive integer.")
    elif _is_int(sample_size) and adoption_sample_size < sample_size:
        errors.append("adoption_sample_size must be at least sample_size.")

    if d.get("keep_rule") != KEEP_RULE:
        errors.append(f'keep_rule must be "{KEEP_RULE}".')

    if d.get("stop_rule") != STOP_RULE:
        errors.append(f'stop_rule must be "{STOP_RULE}".')

    return errors


@dataclass(frozen=True)
class Prereg:
    """A validated, immutable preregistration record."""

    id: str
    arms: tuple[str, ...]
    sample_size: int = 3
    adoption_sample_size: int = 12
    keep_rule: str = KEEP_RULE
    stop_rule: str = STOP_RULE

    def __post_init__(self) -> None:
        object.__setattr__(self, "arms", tuple(self.arms))

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> Prereg:
        errors = validate_prereg(d)
        if errors:
            raise ValueError("; ".join(errors))
        return cls(
            id=d["id"],
            arms=tuple(d["arms"]),
            sample_size=d.get("sample_size", 3),
            adoption_sample_size=d.get("adoption_sample_size", 12),
            keep_rule=d["keep_rule"],
            stop_rule=d["stop_rule"],
        )

    @classmethod
    def load(cls, path: str | Path) -> Prereg:
        with Path(path).open(encoding="utf-8") as file:
            return cls.from_dict(json.load(file))


def decide(prereg: Prereg, outcomes: list[bool], adoption: bool = False) -> str:
    """Decide whether one arm should continue, stop, or be kept."""

    target = prereg.adoption_sample_size if adoption else prereg.sample_size
    if len(outcomes) > target:
        raise ValueError("outcomes cannot exceed the preregistered sample size.")
    if any(outcome is False for outcome in outcomes):
        return "stop_fail"
    if len(outcomes) >= target:
        return "keep"
    return "continue"


def decide_all(prereg: Prereg, results: dict[str, list[bool]], adoption: bool = False) -> dict[str, str]:
    """Decide every preregistered arm, including arms with no outcomes yet."""

    unknown_arms = set(results) - set(prereg.arms)
    if unknown_arms:
        unknown = ", ".join(sorted(unknown_arms))
        raise ValueError(f"unknown arm name(s): {unknown}.")
    return {arm: decide(prereg, results.get(arm, []), adoption=adoption) for arm in prereg.arms}
