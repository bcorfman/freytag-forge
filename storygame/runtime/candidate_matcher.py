"""High-precision action evidence matching for future candidate experiments.

This module deliberately has no dependency on runtime state, package loading,
or turn resolution. It cannot select knowledge, change facts, or influence a
prompt. Its only question is whether authored evidence identifies exactly one
candidate from a supplied set. Closed synonym classes expand authored action
groups, while the rest of the matching rules remain exact and conservative.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from storygame.runtime.knowledge import RevealCandidate


@dataclass(frozen=True)
class ActionEvidenceCandidate:
    """One candidate's complete, package-authored action evidence.

    Every group is required. A group holds declared phrases; one of them or a
    member of its closed synonym class must occur as a whole phrase.
    """

    id: str
    required_groups: tuple[tuple[str, ...], ...]


@dataclass(frozen=True)
class AuthoredHandoff:
    """One projected candidate and the delivery text authored for its handoff."""

    candidate: RevealCandidate
    delivery_text: str


_NEGATIONS = frozenset({"avoid", "cannot", "can't", "do", "don't", "never", "no", "not", "without"})

_SYNONYM_CLASSES = (
    frozenset(
        {
            "examine",
            "inspect",
            "search",
            "look",
            "check",
            "study",
            "investigate",
            "explore",
            "observe",
            "scan",
            "survey",
            "probe",
            "feel",
            "rummage",
            "look at",
            "look through",
            "look into",
            "go through",
            "rifle through",
            "sift through",
        }
    ),
    frozenset({"read", "review", "peruse", "go over", "study"}),
    frozenset({"take", "grab", "pick up", "retrieve", "remove", "pull", "peel off", "collect"}),
    frozenset(
        {
            "under",
            "beneath",
            "underneath",
            "underside",
            "below",
            "bottom of",
            "flip over",
            "turn over",
            "flip",
            "lift",
            "peel",
        }
    ),
    frozenset({"open", "pry open", "unlatch"}),
    frozenset({"talk", "ask", "question", "speak", "tell", "interrogate", "talk to", "speak to", "speak with"}),
)
_LOOK_OPERATIONS = frozenset({"flip over", "turn over"})


def uniquely_matched_candidate(
    player_input: str, candidates: tuple[ActionEvidenceCandidate, ...]
) -> ActionEvidenceCandidate | None:
    """Return one candidate only when all its evidence is present and unnegated.

    This is intentionally conservative. It does not rank partial matches or
    break ties. It expands authored phrases only within the fixed synonym
    classes above.
    """

    matches = [candidate for candidate in candidates if _matches_all(candidate.required_groups, player_input)]
    return matches[0] if len(matches) == 1 else None


def uniquely_matched_authored_handoff(
    player_input: str, candidates: tuple[RevealCandidate, ...]
) -> AuthoredHandoff | None:
    """Return one handoff only when exactly one projected candidate opts in.

    Delivery is eligible only when the projected candidate has both complete
    action evidence and non-blank authored text. The candidate list is already
    projected, so package knowledge that is protected or not currently offered
    cannot participate in the decision.
    """

    matches = []
    for candidate in candidates:
        delivery_text = candidate.delivery_text
        if not candidate.action_evidence or not isinstance(delivery_text, str) or not delivery_text.strip():
            continue
        if _matches_all(candidate.action_evidence, player_input):
            matches.append((candidate, delivery_text))
    if len(matches) != 1:
        return None
    candidate, delivery_text = matches[0]
    return AuthoredHandoff(candidate=candidate, delivery_text=delivery_text)


def _matches_all(groups: tuple[tuple[str, ...], ...], player_input: str) -> bool:
    action_words = _words(player_input)
    return (
        bool(groups)
        and not any(word in _NEGATIONS for word in action_words)
        and all(_matches_one_group(group, action_words) for group in groups)
    )


def _matches_one_group(phrases: tuple[str, ...], action_words: tuple[str, ...]) -> bool:
    accepted_phrases = set(phrases)
    for phrase in phrases:
        normalized_phrase = " ".join(_words(phrase))
        for synonym_class in _SYNONYM_CLASSES:
            if normalized_phrase in synonym_class:
                accepted_phrases.update(synonym_class)
                if synonym_class is _SYNONYM_CLASSES[0]:
                    accepted_phrases.update(_LOOK_OPERATIONS)
    return any(_phrase_is_present(_words(phrase), action_words) for phrase in accepted_phrases)


def _phrase_is_present(phrase: tuple[str, ...], action: tuple[str, ...]) -> bool:
    if not phrase or len(phrase) > len(action):
        return False
    width = len(phrase)
    for start in range(len(action) - width + 1):
        action_slice = action[start : start + width]
        if action_slice == phrase or (width == 1 and _singular_plural_match(phrase[0], action_slice[0])):
            return True
    return False


def _singular_plural_match(authored_word: str, action_word: str) -> bool:
    if len(authored_word) <= 3 or len(action_word) <= 3:
        return False
    return action_word in {authored_word + "s", authored_word + "es"} or authored_word in {
        action_word.removesuffix("s"),
        action_word.removesuffix("es"),
    }


def _words(value: str) -> tuple[str, ...]:
    return tuple(re.findall(r"[^\W_]+(?:'[^\W_]+)*", value.casefold()))
