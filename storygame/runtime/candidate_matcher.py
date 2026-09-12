"""High-precision action evidence matching for future candidate experiments.

This module deliberately has no dependency on runtime state, package loading,
or turn resolution.  It cannot select knowledge, change facts, or influence a
prompt.  Its only question is whether authored evidence identifies exactly one
candidate from a supplied set.
"""

from __future__ import annotations

import re
from dataclasses import dataclass


@dataclass(frozen=True)
class ActionEvidenceCandidate:
    """One candidate's complete, package-authored action evidence.

    Every group is required. A group holds equivalent declared phrases; one of
    them must occur as a whole phrase in the player action.
    """

    id: str
    required_groups: tuple[tuple[str, ...], ...]


_NEGATIONS = frozenset({"avoid", "cannot", "can't", "do", "don't", "never", "no", "not", "without"})


def uniquely_matched_candidate(
    player_input: str, candidates: tuple[ActionEvidenceCandidate, ...]
) -> ActionEvidenceCandidate | None:
    """Return one candidate only when all its evidence is present and unnegated.

    This is intentionally conservative. It does not infer synonyms, rank
    partial matches, or break ties. Package authors must provide every accepted
    phrasing explicitly.
    """

    matches = [candidate for candidate in candidates if _matches_all(candidate.required_groups, player_input)]
    return matches[0] if len(matches) == 1 else None


def _matches_all(groups: tuple[tuple[str, ...], ...], player_input: str) -> bool:
    action_words = _words(player_input)
    return (
        bool(groups)
        and not any(word in _NEGATIONS for word in action_words)
        and all(_matches_one_group(group, action_words) for group in groups)
    )


def _matches_one_group(phrases: tuple[str, ...], action_words: tuple[str, ...]) -> bool:
    return any(_phrase_is_present(_words(phrase), action_words) for phrase in phrases)


def _phrase_is_present(phrase: tuple[str, ...], action: tuple[str, ...]) -> bool:
    if not phrase or len(phrase) > len(action):
        return False
    width = len(phrase)
    for start in range(len(action) - width + 1):
        if action[start : start + width] != phrase:
            continue
        return True
    return False


def _words(value: str) -> tuple[str, ...]:
    return tuple(re.findall(r"[^\W_]+(?:'[^\W_]+)*", value.casefold()))
