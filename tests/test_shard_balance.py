from __future__ import annotations

import importlib.util
import json
from pathlib import Path

import pytest

ROOT = Path(__file__).parent
SHARD_COUNT = 6
_CONFTEST_SPEC = importlib.util.spec_from_file_location("shard_conftest", ROOT / "conftest.py")
assert _CONFTEST_SPEC is not None and _CONFTEST_SPEC.loader is not None
_SHARD_CONFTEST = importlib.util.module_from_spec(_CONFTEST_SPEC)
_CONFTEST_SPEC.loader.exec_module(_SHARD_CONFTEST)
assign_test_nodes_to_shards = _SHARD_CONFTEST.assign_test_nodes_to_shards


def _durations() -> dict[str, float]:
    report = json.loads((ROOT / "shard_durations.json").read_text(encoding="utf-8"))
    return {path: float(weight) for path, weight in report["files"].items()}


def _collected_files(request) -> dict[str, list[str]]:
    files: dict[str, list[str]] = {}
    for item in request.session.items:
        path = Path(str(item.fspath)).as_posix()
        path = path[path.index("tests/") :]
        files.setdefault(path, []).append(item.nodeid)
    return files


def _real_file_nodes() -> dict[str, list[str]]:
    return {f"tests/{path.name}": [f"tests/{path.name}::__representative__"] for path in sorted(ROOT.glob("test_*.py"))}


def _prediction_files(request) -> dict[str, list[str]]:
    files = _collected_files(request)
    if len(files) > 1:
        return files

    files = _real_file_nodes()
    heavy_path = max(files, key=lambda path: (_durations().get(path, 1.0), path))
    files[heavy_path] = [f"{heavy_path}::__representative__:{index}" for index in range(SHARD_COUNT)]
    return files


def test_real_collection_is_partitioned_once(request):
    files = _collected_files(request)
    assignments = assign_test_nodes_to_shards(files, SHARD_COUNT, _durations())

    assert set(assignments) == {nodeid for nodeids in files.values() for nodeid in nodeids}
    assert all(0 <= shard < SHARD_COUNT for shard in assignments.values())
    assert sum(shard == index for shard in assignments.values() for index in range(SHARD_COUNT)) == len(assignments)


def test_predicted_shard_weights_are_balanced(request):
    if request.config.getoption("--shard-count") > 1:
        pytest.skip("measure the complete collection, not an already-deselected shard")
    files = _prediction_files(request)
    durations = _durations()
    assignments = assign_test_nodes_to_shards(files, SHARD_COUNT, durations)
    weights = [0.0] * SHARD_COUNT
    for path, nodeids in files.items():
        shard_counts = {shard: sum(assignments[nodeid] == shard for nodeid in nodeids) for shard in range(SHARD_COUNT)}
        for shard, count in shard_counts.items():
            weights[shard] += durations.get(path, 1.0) * count / len(nodeids)
    assert (max(weights) - min(weights)) / min(weights) < 0.15


def test_file_absent_from_report_is_assigned():
    files = {"tests/test_missing_duration.py": ["tests/test_missing_duration.py::test_missing"]}
    assignments = assign_test_nodes_to_shards(files, SHARD_COUNT, _durations())

    assert assignments == {"tests/test_missing_duration.py::test_missing": 0}


def test_assignment_is_deterministic(request):
    files = _collected_files(request)
    durations = _durations()

    assert assign_test_nodes_to_shards(files, SHARD_COUNT, durations) == assign_test_nodes_to_shards(
        files, SHARD_COUNT, durations
    )


def test_workflow_shard_count_matches_tests():
    import yaml

    workflow = yaml.safe_load((ROOT.parent / ".github/workflows/test.yml").read_text(encoding="utf-8"))
    job = workflow["jobs"]["test-shard"]

    assert job["strategy"]["matrix"]["shard"] == list(range(SHARD_COUNT))
    assert any(f"--shard-count {SHARD_COUNT}" in step.get("run", "") for step in job["steps"])
