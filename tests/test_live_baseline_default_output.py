from __future__ import annotations

import importlib.util
import json
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts/ringer/transcript_1a/live_baseline.py"


def _module():
    module_spec = importlib.util.spec_from_file_location("live_baseline", SCRIPT)
    module = importlib.util.module_from_spec(module_spec)
    assert module_spec.loader is not None
    module_spec.loader.exec_module(module)
    return module


def _run(module, output: Path) -> tuple[dict, list[dict]]:
    assert (
        module.main(
            [
                "--dry-run",
                "--route",
                "observe",
                "--replicates",
                "1",
                "--turns",
                "13",
                "--out",
                str(output),
            ]
        )
        == 0
    )
    return (
        json.loads((output / "summary.json").read_text()),
        json.loads((output / "rows.json").read_text()),
    )


@pytest.mark.nightly
def test_default_run_preserves_legacy_output_and_marks_enforcement_off(tmp_path: Path) -> None:
    module = _module()
    first_summary, first_rows = _run(module, tmp_path / "first")
    second_summary, second_rows = _run(module, tmp_path / "second")

    assert first_rows == second_rows
    assert first_summary == second_summary
    assert first_summary["enforce"] is False
    assert all("observation_enforce" not in turn for turn in first_rows[0]["turns"])
