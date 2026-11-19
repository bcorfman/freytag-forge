"""Tests for the offline evidence-penalty rubric."""

from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path

import pytest

from tests.story_source.helpers import compiled_story_copy

MODULE_PATH = Path(__file__).parents[1] / "bench/checks/penalty_rubric.py"
SPEC = importlib.util.spec_from_file_location("penalty_rubric", MODULE_PATH)
assert SPEC and SPEC.loader
penalty = importlib.util.module_from_spec(SPEC)
sys.modules["penalty_rubric"] = penalty
SPEC.loader.exec_module(penalty)


@pytest.fixture(scope="module")
def gaps(tmp_path_factory: pytest.TempPathFactory) -> dict[str, penalty.GapLine]:
    root = compiled_story_copy(tmp_path_factory.mktemp("compiled-story"))
    return penalty.load_gap_lines(root)


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


def score(run_dir: Path, gaps: dict[str, penalty.GapLine], expect: str | None = None) -> list[penalty.Score]:
    return penalty.run(run_dir, expect, gaps)


def test_clean_no_gap_run_passes(tmp_path: Path, gaps: dict[str, penalty.GapLine]) -> None:
    result = score(write_run(tmp_path, "case-none", [turn(1, "The corridor is quiet.")]), gaps)
    assert not result[0].failures


def test_no_gap_penalty_fails_q1(tmp_path: Path, gaps: dict[str, penalty.GapLine]) -> None:
    for index, narration in enumerate((gaps["processing"].sentence, "The files were left without a copy.")):
        parent = tmp_path / str(index)
        parent.mkdir()
        result = score(write_run(parent, "case-none", [turn(1, narration)]), gaps)
        assert any("Q1" in failure for failure in result[0].failures)


def test_expected_gap_missing_fails_q2(tmp_path: Path, gaps: dict[str, penalty.GapLine]) -> None:
    result = score(write_run(tmp_path, "case-processing", [turn(1, "The corridor is quiet.")]), gaps)
    assert any("Q2" in failure for failure in result[0].failures)


def test_doubled_line_fails_q7(tmp_path: Path, gaps: dict[str, penalty.GapLine]) -> None:
    line = gaps["processing"].sentence
    result = score(write_run(tmp_path, "case-processing", [turn(4, line), turn(5, line)]), gaps)
    assert any("Q7" in failure for failure in result[0].failures)


def test_michelle_says_fails_q6(tmp_path: Path, gaps: dict[str, penalty.GapLine]) -> None:
    line = gaps["processing"].sentence
    result = score(write_run(tmp_path, "case-processing", [turn(4, f"Michelle says: {line}")]), gaps)
    assert any("Q6" in failure for failure in result[0].failures)


def test_too_late_fails_q4(tmp_path: Path, gaps: dict[str, penalty.GapLine]) -> None:
    line = gaps["processing"].sentence
    result = score(write_run(tmp_path, "case-processing", [turn(4, f"{line} It is too late.")]), gaps)
    assert any("Q4" in failure for failure in result[0].failures)


def test_all_expects_processing_and_marked(tmp_path: Path, gaps: dict[str, penalty.GapLine]) -> None:
    turns = [turn(4, gaps["processing"].sentence), turn(10, gaps["marked"].sentence)]
    result = score(write_run(tmp_path, "case-all", turns), gaps)
    assert not result[0].failures
    assert result[0].answers["Q3"] == "info (processing=no, marked=no)"


def test_expect_override(tmp_path: Path, gaps: dict[str, penalty.GapLine]) -> None:
    result = score(write_run(tmp_path, "case-none", [turn(4, gaps["processing"].sentence)]), gaps, "processing")
    assert not result[0].failures


def test_real_pacing_has_four_distinct_keys(gaps: dict[str, penalty.GapLine]) -> None:
    assert set(gaps) == {"processing", "development", "marked"}
    assert len({line.key for line in gaps.values()}) == 3
