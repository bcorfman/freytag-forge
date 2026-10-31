from __future__ import annotations

import importlib.util
import json
from pathlib import Path

SCRIPT = Path(__file__).parents[1] / "scripts" / "regen_shard_durations.py"
SPEC = importlib.util.spec_from_file_location("regen_shard_durations", SCRIPT)
assert SPEC and SPEC.loader
regen = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(regen)


def test_building_from_report_writes_sorted_manifest(tmp_path: Path) -> None:
    durations_path = tmp_path / "shard_durations.json"
    report_path = tmp_path / "tier-report.json"
    report_path.write_text(json.dumps({"file_seconds": {"tests/test_z.py": 2.345, "tests/test_a.py": 1.234}}))

    regen.write_payload(regen._report_seconds(report_path), durations_path)

    assert json.loads(durations_path.read_text()) == {
        "version": 1,
        "files": {"tests/test_a.py": 1.23, "tests/test_z.py": 2.35},
    }
    assert list(json.loads(durations_path.read_text())["files"]) == ["tests/test_a.py", "tests/test_z.py"]


def test_missing_only_merge_keeps_adds_and_drops_entries(tmp_path: Path) -> None:
    root = tmp_path
    (root / "tests").mkdir()
    (root / "tests" / "test_new.py").write_text("")
    (root / "tests" / "test_kept.py").write_text("")
    durations = {"tests/test_kept.py": 2.0, "tests/test_stale.py": 9.0}

    merged = regen.merge_missing(
        durations,
        {"tests/test_new.py": 3.456},
        root=root,
    )

    assert merged == {"tests/test_kept.py": 2.0, "tests/test_new.py": 3.456}


def test_real_manifest_covers_test_files() -> None:
    on_disk = regen.test_files()
    recorded = set(regen.load_payload(regen.DURATIONS_PATH))
    offending = sorted((on_disk - recorded) | (recorded - on_disk))
    assert not offending, (
        "Shard duration manifest is out of date for: "
        + ", ".join(offending)
        + ". Fix with: uv run python scripts/regen_shard_durations.py --missing-only"
    )
