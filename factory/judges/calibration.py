"""Measure saved factory judge outputs against labelled calibration turns."""

from __future__ import annotations

import argparse
import json
import sys
from dataclasses import asdict, dataclass, field
from pathlib import Path

from factory.judges.stats import ErrorRates, wilson_interval

_BLOCK_FILES = {
    "continuity": "continuity-judgments.json",
    "fact": "fact-tracking-judgments.json",
}


@dataclass
class LabelMeasure:
    """Agreement and confusion counts for one judge label."""

    label: str
    agree: int = 0
    total: int = 0
    tp: int = 0
    fn: int = 0
    tn: int = 0
    fp: int = 0

    @property
    def rate(self) -> float:
        return self.agree / self.total if self.total else 0.0

    @property
    def wilson_low(self) -> float:
        return wilson_interval(self.agree, self.total)[0]


@dataclass
class JudgeMeasure:
    """Agreement and aggregate label measures for one judge block."""

    block: str
    agree: int = 0
    total: int = 0
    labels: dict[str, LabelMeasure] = field(default_factory=dict)

    @property
    def rate(self) -> float:
        return self.agree / self.total if self.total else 0.0

    @property
    def wilson_low(self) -> float:
        return wilson_interval(self.agree, self.total)[0]

    def error_rates(self) -> ErrorRates:
        labels = self.labels.values()
        tp = sum(item.tp for item in labels)
        fn = sum(item.fn for item in labels)
        tn = sum(item.tn for item in labels)
        fp = sum(item.fp for item in labels)
        return ErrorRates(tp, tp + fn, tn, tn + fp)


def _superseded_labels(superseded: object, key: str) -> set[str] | None:
    if not isinstance(superseded, dict) or key not in superseded:
        return set()
    cell = superseded[key]
    if isinstance(cell, dict):
        return {str(label) for label in cell}
    if isinstance(cell, (list, tuple, set)):
        return {str(label) for label in cell}
    return None


def _measure_block(
    block: str,
    labels: dict,
    records: dict,
    judgment_data: dict,
) -> JudgeMeasure:
    measure = JudgeMeasure(block)
    superseded_data = labels.get("superseded") or {}
    superseded = superseded_data.get(block, {}) if isinstance(superseded_data, dict) else {}
    for run, judgment in zip(records["runs"], judgment_data["judgments"], strict=True):
        by_turn = {verdict["turn"]: verdict for verdict in judgment["turns"]}
        for turn in run["turns"]:
            key = f"{run['replicate']}:{turn['turn_number']}"
            wanted = labels[block].get(key)
            if wanted is None:
                continue
            verdict = by_turn.get(turn["turn_number"])
            for label, expected in wanted.items():
                superseded_labels = _superseded_labels(superseded, key)
                if superseded_labels is None or label in superseded_labels:
                    continue
                measure.total += 1
                label_measure = measure.labels.setdefault(label, LabelMeasure(label))
                label_measure.total += 1
                actual = verdict.get(label) if verdict else None
                if actual == expected:
                    measure.agree += 1
                    label_measure.agree += 1
                if expected == "yes":
                    if actual == "yes":
                        label_measure.tp += 1
                    elif actual == "no":
                        label_measure.fn += 1
                elif expected == "no":
                    if actual == "no":
                        label_measure.tn += 1
                    elif actual == "yes":
                        label_measure.fp += 1
    return measure


def measure(
    labels_path: Path,
    judgments_dir: Path | None = None,
    records_path: Path | None = None,
) -> dict[str, JudgeMeasure]:
    """Measure continuity and fact judgments against the saved labels."""

    labels_path = Path(labels_path)
    labels = json.loads(labels_path.read_text(encoding="utf-8"))
    results_dir = Path(labels["results_dir"])
    judgments_dir = Path(judgments_dir) if judgments_dir is not None else results_dir
    records_path = Path(records_path) if records_path is not None else results_dir / "all-turn-records.json"
    records = json.loads(records_path.read_text(encoding="utf-8"))

    measures = {}
    for block, filename in _BLOCK_FILES.items():
        judgment_data = json.loads((judgments_dir / filename).read_text(encoding="utf-8"))
        measures[block] = _measure_block(block, labels, records, judgment_data)
    return measures


def write_error_rates(measures: dict[str, JudgeMeasure], path: Path) -> None:
    """Write measured error-rate counts as JSON keyed by judge block."""

    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = {block: asdict(measure.error_rates()) for block, measure in measures.items()}
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def load_error_rates(path: Path) -> dict[str, ErrorRates]:
    """Load error-rate counts written by :func:`write_error_rates`."""

    data = json.loads(Path(path).read_text(encoding="utf-8"))
    return {str(block): ErrorRates(**values) for block, values in data.items()}


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--labels", required=True, type=Path)
    parser.add_argument("--judgments", type=Path)
    parser.add_argument("--records", type=Path)
    parser.add_argument("--bar", type=float, default=0.9)
    parser.add_argument("--raw", action="store_true")
    parser.add_argument("--out", type=Path)
    return parser


def main(argv: list[str] | None = None) -> int:
    """Run calibration, print measures, and optionally save error rates."""

    options = _parser().parse_args(argv)
    try:
        measures = measure(options.labels, options.judgments, options.records)
    except FileNotFoundError as exc:
        print(f"missing file: {exc.filename or exc}", file=sys.stderr)
        return 2

    for block, block_measure in measures.items():
        print(
            f"{block}: {block_measure.agree}/{block_measure.total} = "
            f"{block_measure.rate:.3f} (Wilson low {block_measure.wilson_low:.3f})"
        )
        for label, label_measure in sorted(block_measure.labels.items()):
            print(
                f"  {label}: {label_measure.agree}/{label_measure.total} = "
                f"{label_measure.rate:.3f} (Wilson low {label_measure.wilson_low:.3f})"
            )

    if options.out is not None:
        write_error_rates(measures, options.out)

    if options.raw:
        passed = all(block_measure.rate >= options.bar for block_measure in measures.values())
    else:
        passed = all(block_measure.wilson_low >= options.bar for block_measure in measures.values())
    return 0 if passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
