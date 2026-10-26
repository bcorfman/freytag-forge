"""Candidate observation verification and replayable billed-call answers."""

from __future__ import annotations

import copy
import json
from collections.abc import Callable
from dataclasses import dataclass


def _json_value(value: object) -> object:
    if isinstance(value, set):
        return sorted(value)
    if isinstance(value, (tuple, list)):
        return [_json_value(item) for item in value]
    if isinstance(value, dict):
        return {str(key): _json_value(item) for key, item in value.items()}
    return copy.deepcopy(value)


class CallMemo:
    """Memoize successful answers from billed calls using canonical JSON keys."""

    def __init__(self) -> None:
        self._answers: dict[tuple[str, str], object] = {}
        self.hits = 0
        self.misses = 0

    @staticmethod
    def _canonical_key(key: object) -> str:
        return json.dumps(key, sort_keys=True, default=str)

    def remember(self, kind: str, key: object, call: Callable[[], object]) -> object:
        memo_key = (kind, self._canonical_key(key))
        if memo_key in self._answers:
            self.hits += 1
            return copy.deepcopy(self._answers[memo_key])
        self.misses += 1
        answer = call()
        self._answers[memo_key] = copy.deepcopy(answer)
        return copy.deepcopy(answer)

    def to_json(self) -> dict:
        return {
            "answers": {f"{kind}|{key}": copy.deepcopy(answer) for (kind, key), answer in self._answers.items()},
            "hits": self.hits,
            "misses": self.misses,
        }

    @classmethod
    def from_json(cls, data: dict) -> CallMemo:
        memo = cls()
        for key, answer in data.get("answers", {}).items():
            kind, separator, canonical = str(key).partition("|")
            if not separator:
                raise ValueError("invalid call memo key")
            memo._answers[(kind, canonical)] = copy.deepcopy(answer)
        memo.hits = int(data.get("hits", 0))
        memo.misses = int(data.get("misses", 0))
        return memo


@dataclass(frozen=True)
class CandidatePreview:
    required: bool
    accepted: bool
    outcome: str
    failure: str | None
    verdicts: tuple[dict, ...]
    moved_unrelated: tuple[str, ...]
    changed: tuple[str, ...]
    facts_after: object
    command: str
    narration: str
    memo: CallMemo

    def to_json(self) -> dict:
        return {
            "required": self.required,
            "accepted": self.accepted,
            "outcome": self.outcome,
            "failure": self.failure,
            "verdicts": _json_value(self.verdicts),
            "moved_unrelated": _json_value(self.moved_unrelated),
            "changed": _json_value(self.changed),
            "facts_after": _json_value(self.facts_after),
            "command": self.command,
            "narration": self.narration,
            "memo": self.memo.to_json(),
        }

    @classmethod
    def from_json(cls, data: dict) -> CandidatePreview:
        return cls(
            required=bool(data["required"]),
            accepted=bool(data["accepted"]),
            outcome=str(data["outcome"]),
            failure=data.get("failure"),
            verdicts=tuple(copy.deepcopy(data.get("verdicts", ()))),
            moved_unrelated=tuple(data.get("moved_unrelated", ())),
            changed=tuple(data.get("changed", ())),
            facts_after=copy.deepcopy(data.get("facts_after")),
            command=str(data["command"]),
            narration=str(data["narration"]),
            memo=CallMemo.from_json(data.get("memo", {})),
        )
