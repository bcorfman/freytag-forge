from __future__ import annotations

import importlib.util
import json
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts/ringer/transcript_1a/live_baseline.py"


def _module():
    module_spec = importlib.util.spec_from_file_location("live_baseline_enforce", SCRIPT)
    module = importlib.util.module_from_spec(module_spec)
    assert module_spec.loader is not None
    module_spec.loader.exec_module(module)
    return module


def _run(module, tmp_path: Path, *flags: str) -> tuple[dict, list[dict]]:
    out = tmp_path / "run"
    arguments = [
        "--dry-run",
        "--route",
        "observe",
        "--replicates",
        "1",
        "--turns",
        "13",
        *flags,
        "--out",
        str(out),
    ]
    assert module.main(arguments) == 0
    return json.loads((out / "summary.json").read_text()), json.loads((out / "rows.json").read_text())


def test_enforce_and_shadow_are_mutually_exclusive(capsys: pytest.CaptureFixture[str], tmp_path: Path) -> None:
    module = _module()

    with pytest.raises(SystemExit) as raised:
        module.main(["--dry-run", "--shadow", "--enforce", "--out", str(tmp_path / "invalid")])

    assert raised.value.code == 2
    assert "not allowed with argument" in capsys.readouterr().err


def test_enforce_records_observation_data_counts_and_summary(tmp_path: Path) -> None:
    module = _module()
    summary, rows = _run(module, tmp_path, "--enforce")
    turns = rows[0]["turns"]

    assert summary["enforce"] is True
    assert all("observation_enforce" in turn for turn in turns)
    assert all("narration_attempts" in turn for turn in turns)
    assert all("verifier_requests" in turn for turn in turns)
    assert all(
        value is None or set(value) <= {"observation_preview", "observation_diverged"}
        for value in (turn["observation_enforce"] for turn in turns)
    )


def test_enforce_clears_observation_for_engine_authored_moves(tmp_path: Path) -> None:
    module = _module()
    _summary, rows = _run(module, tmp_path, "--enforce")

    turns = rows[0]["turns"]
    for command in ("go outside", "go inside"):
        row = next(turn for turn in turns if turn["input"] == command)
        assert row["narrator_called"] is False
        assert row["observation_enforce"] is None


def test_enforce_off_preserves_rows_and_sets_false_summary(tmp_path: Path) -> None:
    module = _module()
    first_summary, first_rows = _run(module, tmp_path / "first")
    second_summary, second_rows = _run(module, tmp_path / "second")

    assert first_rows == second_rows
    assert first_summary == second_summary
    assert first_summary["enforce"] is False
    assert all("observation_enforce" not in turn for turn in first_rows[0]["turns"])
