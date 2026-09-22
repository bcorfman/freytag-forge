import json
import sys
from pathlib import Path

from bench.calibration import check_calib


def test_skips_unlabelled_turn_and_scores_labelled_mismatch(tmp_path: Path, monkeypatch, capsys):
    labels = {
        "results_dir": str(tmp_path),
        "continuity": {"1:1": {"consistent": "yes"}, "1:2": {"consistent": "no"}},
        "fact": {"1:1": {"correct": "yes"}},
        "superseded": {"fact": {"1:2": {"correct": "no"}}},
    }
    records = {
        "runs": [
            {
                "replicate": 1,
                "turns": [{"turn_number": 1}, {"turn_number": 2}],
            }
        ]
    }
    continuity = {
        "judgments": [
            {
                "turns": [
                    {"turn": 1, "consistent": "yes"},
                    {"turn": 2, "consistent": "yes"},
                ]
            }
        ]
    }
    fact = {"judgments": [{"turns": [{"turn": 1, "correct": "yes"}]}]}

    def write_json(name: str, value: dict) -> None:
        (tmp_path / name).write_text(json.dumps(value))

    write_json("labels.json", labels)
    write_json("all-turn-records.json", records)
    write_json("continuity-judgments.json", continuity)
    write_json("fact-tracking-judgments.json", fact)

    monkeypatch.setattr(
        sys,
        "argv",
        [
            "check_calib.py",
            "--labels",
            str(tmp_path / "labels.json"),
            "--judgments",
            str(tmp_path),
            "--records",
            str(tmp_path / "all-turn-records.json"),
        ],
    )

    assert check_calib.main() == 1

    output = capsys.readouterr().out
    assert "unlabelled turns skipped: 1 (r1 t2)" in output
    assert "## continuity judge: 1/2 = 50.0%" in output
    assert "## fact judge: 1/1 = 100.0%" in output
    assert "superseded cells skipped: 1" in output
