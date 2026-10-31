from __future__ import annotations

import importlib.util
import json
from pathlib import Path

SCRIPT = Path(__file__).parents[1] / "scripts" / "quick_suite.py"
SPEC = importlib.util.spec_from_file_location("quick_suite", SCRIPT)
assert SPEC and SPEC.loader
quick_suite = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(quick_suite)


def write_durations(tmp_path: Path, files: dict[str, float]) -> Path:
    path = tmp_path / "shard_durations.json"
    path.write_text(json.dumps({"version": 1, "files": files}))
    return path


def test_threshold_is_inclusive_and_missing_files_are_selected(tmp_path: Path) -> None:
    durations = write_durations(
        tmp_path,
        {
            "tests/test_3c_carried_start.py": 15,
            "tests/test_game_path_journeys.py": 14.999,
        },
    )

    selected, skipped = quick_suite.select_test_files(durations_path=durations)

    selected_relative = {path.relative_to(quick_suite.ROOT) for path in selected}
    skipped_relative = {(path.relative_to(quick_suite.ROOT), seconds) for path, seconds in skipped}
    assert Path("tests/test_3c_carried_start.py") not in selected_relative
    assert (Path("tests/test_3c_carried_start.py"), 15.0) in skipped_relative
    assert Path("tests/test_game_path_journeys.py") in selected_relative
    assert Path("tests/test_quick_suite.py") in selected_relative


def test_also_reincludes_heavy_file_and_accepts_any_test_path(tmp_path: Path) -> None:
    durations = write_durations(tmp_path, {"tests/test_3c_carried_start.py": 15})

    selected, skipped = quick_suite.select_test_files(
        durations_path=durations,
        also=["tests/test_3c_carried_start.py", "tests/test_game_path_journeys.py"],
    )

    selected_relative = {path.relative_to(quick_suite.ROOT) for path in selected}
    skipped_relative = {path.relative_to(quick_suite.ROOT) for path, _ in skipped}
    assert Path("tests/test_3c_carried_start.py") in selected_relative
    assert Path("tests/test_3c_carried_start.py") not in skipped_relative
    assert Path("tests/test_game_path_journeys.py") in selected_relative


def test_list_reports_selected_skipped_and_predicted_cpu(tmp_path: Path, capsys) -> None:
    durations = write_durations(tmp_path, {"tests/test_3c_carried_start.py": 15})
    assert quick_suite.main(["--list"], durations_path=durations) == 0

    output = capsys.readouterr().out
    assert "SELECTED tests/test_game_path_journeys.py" in output
    assert "SKIPPED tests/test_3c_carried_start.py (15.000s)" in output
    assert "Predicted quick-tier CPU seconds:" in output


def test_list_warns_about_missing_durations_and_prints_fix(tmp_path: Path, capsys) -> None:
    durations = write_durations(tmp_path, {"tests/test_3c_carried_start.py": 15})

    assert quick_suite.main(["--list"], durations_path=durations) == 0

    output = capsys.readouterr().out
    assert "WARNING:" in output
    assert "selected test files are missing from shard durations" in output
    assert "tests/test_quick_suite.py" in output
    assert "uv run python scripts/regen_shard_durations.py --missing-only" in output
