from __future__ import annotations

import shlex
import subprocess
from pathlib import Path

from factory.checks.canary import canary_check
from factory.checks.library import (
    compose,
    gap_delta_check,
    journey_reachability_check,
    json_check,
    node_syntax_check,
    ownership_check,
    probe_unsatisfiable,
    pytest_check,
    ruff_check,
)
from factory.manifests import lint_check


def test_builders_quote_paths_and_lint() -> None:
    path = "tests/a weird'path.py"
    quoted = shlex.quote(path)

    scripts = [
        pytest_check([path], timeout_note="short note"),
        ruff_check([path, "config/a file.json"]),
        json_check(["config/a file.json"]),
        node_syntax_check(["frontend/a weird'file.js"]),
        ownership_check([path, "config/a file.json"], "tmp/a patch.diff"),
        gap_delta_check("data/a story", "tmp/a baseline.json", ["anchor one"]),
        canary_check("token'with-space"),
    ]

    assert all(lint_check(script) == [] for script in scripts)
    assert quoted in scripts[0]
    assert quoted in scripts[1]
    assert "config/a file.json" not in scripts[1]
    assert shlex.quote("frontend/a weird'file.js") in scripts[3]
    assert shlex.quote("tmp/a patch.diff") in scripts[4]
    assert shlex.quote("data/a story") in scripts[5]


def test_compose_stops_at_first_failure(tmp_path: Path) -> None:
    marker = tmp_path / "marker"
    script = compose(
        "echo first\nfalse",
        f"echo second > {shlex.quote(str(marker))}",
    )
    result = subprocess.run(["/bin/sh", "-c", script], cwd=tmp_path, check=False, capture_output=True, text=True)

    assert result.returncode != 0
    assert not marker.exists()


def test_probe_unsatisfiable_distinguishes_failure_and_success(tmp_path: Path) -> None:
    assert probe_unsatisfiable("set -e\nfalse", tmp_path)
    assert not probe_unsatisfiable("set -e\ntrue", tmp_path)


def test_journey_reachability_check_is_bounded_and_linted() -> None:
    script = journey_reachability_check(budget_s=17)

    assert "--run-nightly" in script
    assert "date +%s" in script
    assert "SECONDS" not in script
    assert "17" in script
    assert lint_check(script) == []


def test_journey_reachability_check_reports_fake_pytest_failure(tmp_path: Path) -> None:
    python = tmp_path / ".venv" / "bin" / "python"
    python.parent.mkdir(parents=True)
    python.write_text("#!/bin/sh\nexit 0\n", encoding="utf-8")
    python.chmod(0o755)
    script = journey_reachability_check(budget_s=17)

    passed = subprocess.run(["/bin/sh", "-c", script], cwd=tmp_path, capture_output=True, text=True, check=False)
    assert passed.returncode == 0

    python.write_text("#!/bin/sh\nexit 1\n", encoding="utf-8")
    failed = subprocess.run(["/bin/sh", "-c", script], cwd=tmp_path, capture_output=True, text=True, check=False)
    assert failed.returncode != 0
    assert "a story realization is unreachable or the ratchet was broken" in failed.stderr
