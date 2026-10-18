from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path


def test_tier_report_collects_xdist_timings(tmp_path: Path) -> None:
    report_path = tmp_path / "tier-report.json"
    environment = {"PYTHONPATH": str(Path.cwd()), "TMPDIR": "/tmp"}
    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "pytest",
            "tests/test_shard_balance.py",
            "-n",
            "2",
            "-p",
            "no:cacheprovider",
            "--tier-report",
            str(report_path),
        ],
        cwd=Path.cwd(),
        env=environment,
        capture_output=True,
        text=True,
        timeout=15,
        check=False,
    )
    assert result.returncode == 0, result.stdout + result.stderr

    report = json.loads(report_path.read_text(encoding="utf-8"))
    assert report["tests"] > 0
    assert set(report["file_seconds"]) == {"tests/test_shard_balance.py"}
    assert report["file_seconds"]["tests/test_shard_balance.py"] > 0
    assert report["slowest"]
