import json
import subprocess

import pytest

from factory.manifests import TaskSpec, build_check, build_manifest, lint_check, write_manifest


def task(**overrides) -> TaskSpec:
    values = {
        "key": "prereg",
        "spec_body": "Implement the feature.",
        "ownership": ["factory/prereg.py"],
        "tests": ["tests/test_factory_prereg.py"],
    }
    values.update(overrides)
    return TaskSpec(**values)


@pytest.mark.parametrize(
    "check",
    [
        "echo PASS",
        "set -e\necho PASS\ntrue\nexit 0",
        "set -e\necho PASS\npytest | tail -n 1",
        "set -eo pipefail\necho ${PIPESTATUS[0]}",
        "set -eo pipefail\nrm -f .venv",
        "set -eo pipefail\npytest --cov",
    ],
)
def test_lint_check_flags_unsafe_checks(check: str) -> None:
    assert lint_check(check)


def test_lint_check_accepts_failing_check() -> None:
    assert lint_check("set -eo pipefail\nfalse\n") == []


def test_build_check_is_linted_and_sh_syntax_is_valid(tmp_path) -> None:
    check = build_check(task(), "/repo", str(tmp_path))
    assert lint_check(check) == []
    assert check.startswith("set -eo pipefail\n")
    assert "PIPESTATUS" not in check
    assert "git add -A\n" not in check
    script = tmp_path / "check.sh"
    script.write_text(check, encoding="utf-8")
    subprocess.run(["sh", "-n", str(script)], check=True)


def test_build_check_contains_safe_pytest_and_staging(tmp_path) -> None:
    check = build_check(task(ownership=["factory/prereg.py", "tests/test_factory_prereg.py"]), "/repo", str(tmp_path))
    assert "PYTHONPATH=$PWD TMPDIR=/tmp .venv/bin/python -m pytest -q -p no:cacheprovider -n 0" in check
    assert "pytest_status=$?" in check
    assert 'tail -n 80 "$pytest_output"' in check
    assert "git add -A -- factory/prereg.py tests/test_factory_prereg.py" in check
    assert str(tmp_path / "prereg.patch") in check


def test_build_manifest_rejects_duplicate_keys() -> None:
    with pytest.raises(ValueError, match="duplicate"):
        build_manifest("run", "/repo", "/tmp", [task(), task(ownership=["other.py"])])


def test_build_manifest_rejects_empty_ownership() -> None:
    with pytest.raises(ValueError, match="at least one"):
        build_manifest("run", "/repo", "/tmp", [task(ownership=[])])


def test_build_manifest_rejects_overlapping_ownership() -> None:
    with pytest.raises(ValueError, match="overlap"):
        build_manifest("run", "/repo", "/tmp", [task(), task(key="other", ownership=["factory/prereg.py"])])


def test_built_manifest_round_trips_through_json(tmp_path) -> None:
    manifest = build_manifest("run", "/repo", str(tmp_path), [task()])
    path = tmp_path / "manifest.json"
    write_manifest(manifest, path)
    assert json.loads(path.read_text(encoding="utf-8")) == manifest
