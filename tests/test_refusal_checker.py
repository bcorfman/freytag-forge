"""Hermetic regression tests for the billed refusal-measurement checker."""

from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path

import pytest

HELPER_PATH = Path(__file__).parents[1] / "scripts/ringer/astra/refusal_summary.py"
SPEC = importlib.util.spec_from_file_location("refusal_summary", HELPER_PATH)
assert SPEC and SPEC.loader
refusal_summary = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = refusal_summary
SPEC.loader.exec_module(refusal_summary)


def write_records(tmp_path: Path, turns: list[dict[str, object]]) -> Path:
    path = tmp_path / "all-turn-records.json"
    path.write_text(json.dumps({"runs": [{"turns": turns}]}), encoding="utf-8")
    return path


def test_engine_refusal_counts_as_refused(tmp_path: Path) -> None:
    path = write_records(
        tmp_path,
        [{"engine_refusal": "The workstation stays put.", "narrator_called": False}],
    )

    summary = refusal_summary.summarize_file(path, "engine", "k1", emit=False)

    assert summary.refused == 1
    assert summary.narrator_called == 0
    assert summary.narrator_not_called == 1


def test_legacy_refused_place_marker_still_counts(tmp_path: Path) -> None:
    path = write_records(tmp_path, [{"capture_issues": ["refused place: workstation"]}])

    assert refusal_summary.summarize_file(path, "legacy", "k1", emit=False).refused == 1


def test_expected_turn_count_mismatch_fails(tmp_path: Path, monkeypatch, capsys) -> None:
    out = tmp_path / "out"
    records_dir = out / "arm" / "k1"
    records_dir.mkdir(parents=True)
    write_records(records_dir, [{"narrator_called": True}, {"narrator_called": True}])
    monkeypatch.setenv("EXPECT_TURNS", "3")
    monkeypatch.setattr(refusal_summary, "write_provenance", lambda *_args: out / "provenance.json")
    monkeypatch.setattr(refusal_summary, "check_dirty", lambda _repo: None)

    assert refusal_summary.main([str(out), "arm", "k1", "--repo", str(tmp_path)]) == 1
    assert "FAIL expected 3 turns" in capsys.readouterr().out


def test_expected_refusal_minimum_not_met_fails(tmp_path: Path, monkeypatch, capsys) -> None:
    out = tmp_path / "out"
    records_dir = out / "inactive" / "k1"
    records_dir.mkdir(parents=True)
    write_records(records_dir, [{"narrator_called": True}])
    monkeypatch.setenv("EXPECT_REFUSED_MIN", "1")
    monkeypatch.setattr(refusal_summary, "write_provenance", lambda *_args: out / "provenance.json")
    monkeypatch.setattr(refusal_summary, "check_dirty", lambda _repo: None)

    assert refusal_summary.main([str(out), "inactive", "k1", "--repo", str(tmp_path)]) == 1
    assert "FAIL treatment inactive" in capsys.readouterr().out


def test_normal_narrated_turn_counts_zero_refused(tmp_path: Path) -> None:
    path = write_records(tmp_path, [{"narrator_called": True, "fixed_refusal_steps": []}])

    summary = refusal_summary.summarize_file(path, "normal", "k1", emit=False)

    assert summary.refused == 0
    assert summary.narrator_called == 1


def test_saved_engine_refusal_record_counts_if_available() -> None:
    path = Path("/home/bcorfman/dev/ringer-work/astra-p4-2-measure/fe4-full-fe4eng/fe4eng/k1/all-turn-records.json")
    if not path.exists():
        pytest.skip("saved refusal record is not available")

    assert refusal_summary.summarize_file(path, "saved", "k1", emit=False).refused >= 1
