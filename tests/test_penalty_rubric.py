"""Tests for the offline evidence-penalty rubric."""

from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path

import pytest

MODULE_PATH = Path(__file__).parents[1] / "bench/checks/penalty_rubric.py"
SPEC = importlib.util.spec_from_file_location("penalty_rubric", MODULE_PATH)
assert SPEC and SPEC.loader
penalty = importlib.util.module_from_spec(SPEC)
sys.modules["penalty_rubric"] = penalty
SPEC.loader.exec_module(penalty)


GAPS = penalty.load_gap_lines()


def write_run(tmp_path: Path, name: str, turns: list[dict], replicate: int = 1) -> Path:
    run_dir = tmp_path / name
    run_dir.mkdir()
    (run_dir / "all-turn-records.json").write_text(
        json.dumps({"runs": [{"replicate": replicate, "turns": turns}]}), encoding="utf-8"
    )
    return run_dir


def turn(number: int, narration: str, player_input: str = "Check the evidence.") -> dict:
    return {
        "turn_number": number,
        "player_input": player_input,
        "narration": narration,
        "complication_text": "",
    }


def score(run_dir: Path, expect: str | None = None) -> list[penalty.Score]:
    return penalty.run(run_dir, expect, GAPS)


def test_clean_no_gap_run_passes(tmp_path: Path) -> None:
    result = score(write_run(tmp_path, "case-none", [turn(1, "The corridor is quiet.")]))
    assert not result[0].failures


@pytest.mark.parametrize("narration", [GAPS["processing"].sentence, "The files were left without a copy."])
def test_no_gap_penalty_fails_q1(tmp_path: Path, narration: str) -> None:
    result = score(write_run(tmp_path, "case-none", [turn(1, narration)]))
    assert any("Q1" in failure for failure in result[0].failures)


def test_expected_gap_missing_fails_q2(tmp_path: Path) -> None:
    result = score(write_run(tmp_path, "case-processing", [turn(1, "The corridor is quiet.")]))
    assert any("Q2" in failure for failure in result[0].failures)


def test_doubled_line_fails_q7(tmp_path: Path) -> None:
    line = GAPS["processing"].sentence
    result = score(write_run(tmp_path, "case-processing", [turn(4, line), turn(5, line)]))
    assert any("Q7" in failure for failure in result[0].failures)


def test_michelle_says_fails_q6(tmp_path: Path) -> None:
    line = GAPS["processing"].sentence
    result = score(write_run(tmp_path, "case-processing", [turn(4, f"Michelle says: {line}")]))
    assert any("Q6" in failure for failure in result[0].failures)


def test_too_late_fails_q4(tmp_path: Path) -> None:
    line = GAPS["processing"].sentence
    result = score(write_run(tmp_path, "case-processing", [turn(4, f"{line} It is too late.")]))
    assert any("Q4" in failure for failure in result[0].failures)


def test_all_expects_processing_and_marked(tmp_path: Path) -> None:
    turns = [turn(4, GAPS["processing"].sentence), turn(10, GAPS["marked"].sentence)]
    result = score(write_run(tmp_path, "case-all", turns))
    assert not result[0].failures
    assert result[0].answers["Q3"] == "info (processing=no, marked=no)"


def test_expect_override(tmp_path: Path) -> None:
    result = score(write_run(tmp_path, "case-none", [turn(4, GAPS["processing"].sentence)]), "processing")
    assert not result[0].failures


def test_real_pacing_has_four_distinct_keys() -> None:
    assert set(GAPS) == {"processing", "development", "marked", "copycheck"}
    assert len({line.key for line in GAPS.values()}) == 4
