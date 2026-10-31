"""Jev check for unsupported state or contents on an engine opening."""

from __future__ import annotations

import copy
from collections.abc import Mapping
from dataclasses import dataclass
from numbers import Real

OPENING_QUESTION_KEY = "condition_consistent"
OPENING_KIND = "opening"
OPENING_QUESTION = {
    "type": "noul",
    "instructions": (
        "Decide whether the narration is consistent with the declared sentence for the thing named in the state. "
        "It is consistent when it does not state any open, ajar, lifted, covered, or entered condition, or state what "
        "is inside it, including what can be seen, heard or smelled there, such as darkness, water, objects, sounds "
        "or smells, unless the declared sentence supports it. The declared sentence says whether the engine opened the "
        "thing this turn, and an opening the engine performed is supported. Looking at, approaching, kneeling beside, "
        "touching the outside, or wondering what might be inside are consistent."
    ),
    "criteria": {
        "true": (
            "The narration is consistent with the declared sentence. It does not state an unsupported open, ajar, "
            "lifted, covered, or entered condition or what is inside it, including what can be seen, heard or smelled "
            "there, such as darkness, water, objects, sounds or smells, as fact."
        ),
        "false": (
            "The narration is not consistent with the declared sentence. It states an unsupported open, ajar, lifted, "
            "covered, or entered condition or what is inside it, including what can be seen, heard or smelled there, "
            "such as darkness, water, objects, sounds or smells, as fact."
        ),
    },
}


@dataclass(frozen=True)
class OpeningVerdict:
    thing: str
    verdict: str
    score: float | None


def opening_state(narration: str, thing: str, command: str) -> dict[str, str]:
    """Build the measured Variant B state for one declared opening."""
    return {
        "narration": narration,
        "thing": thing,
        "command": command,
        "declared": f"the {thing} has no open or closed value, no declared contents, and is fixed in place.",
    }


def opening_payload(narration: str, thing: str, command: str) -> tuple[dict[str, str], dict[str, dict[str, object]]]:
    return opening_state(narration, thing, command), {
        OPENING_QUESTION_KEY: copy.deepcopy(OPENING_QUESTION),
    }


def opening_verdict(
    thing: str,
    answers: object,
    *,
    accept_above: float = 0.65,
    reject_below: float = 0.35,
) -> OpeningVerdict:
    score = _score_for(answers)
    if score is None:
        return OpeningVerdict(thing, "unavailable", None)
    if score > accept_above:
        verdict = "accept"
    elif score < reject_below:
        verdict = "reject"
    else:
        verdict = "uncertain"
    return OpeningVerdict(thing, verdict, score)


def _score_for(answers: object) -> float | None:
    if not isinstance(answers, Mapping):
        return None
    answer = answers.get(OPENING_QUESTION_KEY)
    if not isinstance(answer, Mapping):
        return None
    score = answer.get("noul")
    if isinstance(score, bool) or not isinstance(score, Real) or not 0 <= score <= 1:
        return None
    return float(score)
