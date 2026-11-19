from __future__ import annotations

import json
from pathlib import Path

import pytest

from factory.judges.calibration import load_error_rates, main, measure, write_error_rates
from factory.judges.stats import ErrorRates, corrected_lower_bound, gate_passes, wilson_interval


def test_wilson_interval_known_values_and_empty_sample() -> None:
    assert wilson_interval(0, 0) == (0.0, 1.0)
    assert wilson_interval(10, 10)[0] > 0.7
    assert wilson_interval(10, 10)[1] == pytest.approx(1.0)
    assert wilson_interval(50, 100) == pytest.approx((0.4038, 0.5962), abs=0.001)


def test_wilson_interval_rejects_out_of_range_successes() -> None:
    with pytest.raises(ValueError):
        wilson_interval(-1, 10)
    with pytest.raises(ValueError):
        wilson_interval(11, 10)


def test_corrected_lower_bound_accounts_for_imperfect_judge() -> None:
    imperfect = ErrorRates(80, 100, 80, 100)
    corrected = corrected_lower_bound(50, 100, imperfect)
    raw_lower = wilson_interval(50, 100)[0]

    assert corrected < raw_lower
    assert corrected_lower_bound(50, 100, ErrorRates(10_000, 10_000, 10_000, 10_000)) == pytest.approx(
        raw_lower, abs=0.005
    )
    assert corrected_lower_bound(50, 100, ErrorRates(1, 2, 1, 2)) == 0.0
    assert 0.0 <= corrected_lower_bound(100, 100, imperfect) <= 1.0


def test_gate_passes_uses_the_corrected_lower_bound() -> None:
    rates = ErrorRates(10_000, 10_000, 10_000, 10_000)

    assert gate_passes(90, 100, 0.8, rates)
    assert not gate_passes(50, 100, 0.5, rates)


def _write_corpus(tmp_path: Path) -> tuple[Path, Path, Path]:
    judgments_dir = tmp_path / "judgments"
    judgments_dir.mkdir()
    labels_path = tmp_path / "labels.json"
    records_path = tmp_path / "all-turn-records.json"
    labels = {
        "results_dir": str(tmp_path),
        "continuity": {
            "1:1": {"positive": "yes", "negative": "no"},
            "1:3": {"positive": "yes", "negative": "no"},
            "1:4": {"opaque": "maybe"},
            "1:5": {"positive": "yes"},
        },
        "fact": {
            "1:1": {"positive": "yes", "negative": "no"},
            "1:3": {"positive": "yes", "negative": "no"},
            "1:5": {"positive": "yes"},
        },
        "superseded": {"continuity": {"1:5": {"positive": "old label"}}},
    }
    records = {
        "runs": [
            {
                "replicate": 1,
                "turns": [{"turn_number": number} for number in range(1, 6)],
            }
        ]
    }
    judgment = {
        "judgments": [
            {
                "replicate": 1,
                "turns": [
                    {"turn": 1, "positive": "yes", "negative": "yes"},
                    {"turn": 2, "positive": "yes", "negative": "no"},
                    {"turn": 3, "positive": "no", "negative": "no"},
                    {"turn": 4, "opaque": "maybe"},
                    {"turn": 5, "positive": "no"},
                ],
            }
        ]
    }
    labels_path.write_text(json.dumps(labels), encoding="utf-8")
    records_path.write_text(json.dumps(records), encoding="utf-8")
    (judgments_dir / "continuity-judgments.json").write_text(json.dumps(judgment), encoding="utf-8")
    (judgments_dir / "fact-tracking-judgments.json").write_text(json.dumps(judgment), encoding="utf-8")
    return labels_path, judgments_dir, records_path


def test_measure_counts_confusion_and_skips_unlabelled_and_superseded(tmp_path: Path) -> None:
    labels_path, judgments_dir, records_path = _write_corpus(tmp_path)
    before = sorted(path.name for path in judgments_dir.iterdir())

    measures = measure(labels_path, judgments_dir, records_path)

    continuity = measures["continuity"]
    assert (continuity.agree, continuity.total) == (3, 5)
    assert continuity.labels["positive"].__dict__ == {
        "label": "positive",
        "agree": 1,
        "total": 2,
        "tp": 1,
        "fn": 1,
        "tn": 0,
        "fp": 0,
    }
    assert continuity.labels["negative"].__dict__ == {
        "label": "negative",
        "agree": 1,
        "total": 2,
        "tp": 0,
        "fn": 0,
        "tn": 1,
        "fp": 1,
    }
    assert continuity.labels["opaque"].tp == 0
    assert continuity.error_rates() == ErrorRates(1, 2, 1, 2)
    assert sorted(path.name for path in judgments_dir.iterdir()) == before


def test_error_rate_json_round_trip(tmp_path: Path) -> None:
    labels_path, judgments_dir, records_path = _write_corpus(tmp_path)
    output = tmp_path / "nested" / "error_rates.json"

    write_error_rates(measure(labels_path, judgments_dir, records_path), output)

    assert load_error_rates(output) == {
        "continuity": ErrorRates(1, 2, 1, 2),
        "fact": ErrorRates(1, 3, 1, 2),
    }


def test_cli_exit_codes_raw_mode_and_missing_file(tmp_path: Path, capsys) -> None:
    labels_path, judgments_dir, records_path = _write_corpus(tmp_path)
    output = tmp_path / "rates.json"

    assert (
        main(
            [
                "--labels",
                str(labels_path),
                "--judgments",
                str(judgments_dir),
                "--records",
                str(records_path),
                "--bar",
                "0.0",
                "--out",
                str(output),
            ]
        )
        == 0
    )
    assert output.exists()
    capsys.readouterr()

    assert (
        main(
            [
                "--labels",
                str(labels_path),
                "--judgments",
                str(judgments_dir),
                "--records",
                str(records_path),
                "--bar",
                "0.3",
            ]
        )
        == 1
    )
    capsys.readouterr()
    assert (
        main(
            [
                "--labels",
                str(labels_path),
                "--judgments",
                str(judgments_dir),
                "--records",
                str(records_path),
                "--bar",
                "0.3",
                "--raw",
            ]
        )
        == 0
    )
    capsys.readouterr()

    assert main(["--labels", str(tmp_path / "missing.json")]) == 2
    assert "missing file" in capsys.readouterr().err


def test_measure_missing_judgment_raises(tmp_path: Path) -> None:
    labels_path, judgments_dir, records_path = _write_corpus(tmp_path)
    (judgments_dir / "fact-tracking-judgments.json").unlink()

    with pytest.raises(FileNotFoundError):
        measure(labels_path, judgments_dir, records_path)
