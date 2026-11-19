"""Monitor agreement between primary and secondary factory judges."""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
import sys
import tempfile
from collections.abc import Iterable
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class Pair:
    id: str
    primary: bool
    secondary: bool


def select_slice(ids: list[str], fraction: float = 0.1, salt: str = "", minimum: int = 20) -> list[str]:
    """Select a deterministic, order-independent slice and restore input order."""

    if not 0 < fraction <= 1:
        raise ValueError("fraction must be in (0, 1]")
    count = min(len(ids), max(minimum, math.ceil(fraction * len(ids))))
    ranked = sorted(
        range(len(ids)),
        key=lambda index: (hashlib.sha256(f"{salt}{ids[index]}".encode()).digest(), ids[index]),
    )
    selected = set(ranked[:count])
    return [item for index, item in enumerate(ids) if index in selected]


def disagreement_rate(pairs: Iterable[Pair]) -> float:
    """Return the proportion of pairs on which the judges disagree."""

    pairs = list(pairs)
    if not pairs:
        return 0.0
    return sum(pair.primary != pair.secondary for pair in pairs) / len(pairs)


@dataclass(frozen=True)
class Decision:
    status: str
    rate: float
    pairs: int
    paused: bool


def evaluate(pairs: Iterable[Pair], noise: float = 0.03, min_pairs: int = 20) -> Decision:
    """Classify agreement quality using the configured noise floor."""

    pairs = list(pairs)
    rate = disagreement_rate(pairs)
    count = len(pairs)
    if count < min_pairs:
        return Decision("insufficient", rate, count, False)
    paused = rate > noise
    return Decision("paused" if paused else "ok", rate, count, paused)


def stricter(primary: bool, secondary: bool) -> bool:
    """Use the conservative verdict when both judges must pass an item."""

    return primary and secondary


class MonitorState:
    """Persist judge pause state and the latest agreement measurement."""

    def __init__(self, path: Path | str):
        self.path = Path(path)
        if self.path.exists():
            self._records = json.loads(self.path.read_text(encoding="utf-8"))
        else:
            self._records = {}

    def _save(self) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        temporary_path: Path | None = None
        try:
            with tempfile.NamedTemporaryFile(
                mode="w", encoding="utf-8", dir=self.path.parent, prefix=f".{self.path.name}.", delete=False
            ) as temporary:
                temporary_path = Path(temporary.name)
                json.dump(self._records, temporary, indent=2, sort_keys=True)
                temporary.write("\n")
                temporary.flush()
                os.fsync(temporary.fileno())
            os.replace(temporary_path, self.path)
        except BaseException:
            if temporary_path is not None:
                temporary_path.unlink(missing_ok=True)
            raise

    def get(self, judge: str) -> dict:
        """Return a judge record, or the unpaused default record."""

        record = self._records.get(judge)
        if record is None:
            return {"paused": False, "last_rate": 0.0, "pairs": 0}
        return {
            "paused": bool(record["paused"]),
            "last_rate": float(record["last_rate"]),
            "pairs": int(record["pairs"]),
        }

    def record(self, judge: str, decision: Decision) -> None:
        """Save a measurement, keeping a previous pause until explicitly cleared."""

        self._records[judge] = {
            "paused": self.is_paused(judge) or decision.paused,
            "last_rate": decision.rate,
            "pairs": decision.pairs,
        }
        self._save()

    def clear(self, judge: str) -> None:
        """Clear a pause while retaining the latest measurement."""

        record = self.get(judge)
        record["paused"] = False
        self._records[judge] = record
        self._save()

    def is_paused(self, judge: str) -> bool:
        return self.get(judge)["paused"]

    def effective(self, judge: str, primary: bool, secondary: bool) -> bool:
        return stricter(primary, secondary) if self.is_paused(judge) else primary


DEFAULT_STATE = Path("factory/state/judge-monitor.json")


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--pairs", required=True, type=Path)
    parser.add_argument("--judge", required=True)
    parser.add_argument("--state", type=Path, default=DEFAULT_STATE)
    parser.add_argument("--noise", type=float, default=0.03)
    parser.add_argument("--min-pairs", type=int, default=20)
    return parser


def _read_pairs(path: Path) -> list[Pair]:
    data = json.loads(path.read_text(encoding="utf-8"))
    return [Pair(id=item["id"], primary=item["primary"], secondary=item["secondary"]) for item in data]


def main(argv: list[str] | None = None) -> int:
    """Evaluate a pairs file and record the decision."""

    options = _parser().parse_args(argv)
    try:
        pairs = _read_pairs(options.pairs)
    except (OSError, TypeError, ValueError, KeyError, json.JSONDecodeError):
        print(f"could not read pairs file: {options.pairs}", file=sys.stderr)
        return 2

    decision = evaluate(pairs, noise=options.noise, min_pairs=options.min_pairs)
    MonitorState(options.state).record(options.judge, decision)
    print(f"{options.judge}: {decision.status} {decision.rate:.2%} over {decision.pairs} pairs")
    return 1 if decision.paused else 0


if __name__ == "__main__":
    raise SystemExit(main())
