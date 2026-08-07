from __future__ import annotations

import ast
import inspect
import json
import textwrap
import time
import urllib.request
from collections import Counter
from pathlib import Path
from typing import Any

import pytest

TIERS = ("unit", "component", "integration", "evaluation")
_EVALUATION_FILES = {"test_evaluation.py", "test_reproducibility.py", "test_if_output_contract.py"}
_INTEGRATION_FILES = {
    "test_cli.py", "test_cli_more.py", "test_savegame_sqlite.py", "test_web_api.py",
    "test_web_demo_api.py", "test_web_surface_parity.py", "test_vector_memory.py",
}
_COMPONENT_FILES = {
    "test_adapters.py", "test_freeform_unit.py", "test_llm_context.py", "test_narration_state.py",
    "test_world_builder.py", "test_world_presentation.py", "test_story_coherence.py",
}


def _tier_for_path(path: Path) -> str:
    if path.name in _EVALUATION_FILES:
        return "evaluation"
    if path.name in _INTEGRATION_FILES:
        return "integration"
    if path.name in _COMPONENT_FILES:
        return "component"
    return "unit"


def pytest_addoption(parser: pytest.Parser) -> None:
    group = parser.getgroup("test-suite-health")
    group.addoption("--tier-report", default="", help="Write tier, timing, and construction counts as JSON.")
    group.addoption("--expected-test-count", type=int, default=0, help="Fail collection when count differs.")
    group.addoption(
        "--strict-test-budgets", action="store_true", help="Fail when unit/component test budgets are exceeded."
    )


def _duplicate_definitions(path: Path) -> list[str]:
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    names = [node.name for node in ast.walk(tree) if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))]
    return sorted(name for name, count in Counter(names).items() if count > 1 and name.startswith("test_"))


def pytest_configure(config: pytest.Config) -> None:
    for tier in TIERS:
        config.addinivalue_line("markers", f"{tier}: test-suite performance tier")


def pytest_collection_modifyitems(config: pytest.Config, items: list[pytest.Item]) -> None:
    duplicate_errors: list[str] = []
    seen_paths: set[Path] = set()
    for item in items:
        path = Path(str(item.fspath))
        if path not in seen_paths:
            seen_paths.add(path)
            duplicates = _duplicate_definitions(path)
            if duplicates:
                duplicate_errors.append(f"{path}: {', '.join(duplicates)}")
        markers = [tier for tier in TIERS if item.get_closest_marker(tier) is not None]
        if not markers:
            item.add_marker(getattr(pytest.mark, _tier_for_path(path)))
        elif len(markers) != 1:
            duplicate_errors.append(f"{item.nodeid}: expected exactly one test tier, got {markers}")
    if duplicate_errors:
        raise pytest.UsageError("Test-suite collection guard failed:\n" + "\n".join(duplicate_errors))
    expected = config.getoption("--expected-test-count")
    if expected and len(items) != expected:
        raise pytest.UsageError(f"Expected {expected} tests, collected {len(items)}.")


def _source_construction_counts(item: pytest.Item) -> Counter[str]:
    """Count direct construction/orchestration calls without profiling every Python call."""

    try:
        source = inspect.getsource(item.obj)
    except (OSError, TypeError):
        return Counter()
    tree = ast.parse(textwrap.dedent(source))
    counts: Counter[str] = Counter()
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        if isinstance(node.func, ast.Name):
            name = node.func.id
        elif isinstance(node.func, ast.Attribute):
            name = node.func.attr
        else:
            name = ""
        if name in {"build_default_state", "run_turn", "TestClient", "SqliteSaveStore"}:
            counts[name] += 1
    return counts


@pytest.fixture(autouse=True)
def _record_test_health(request: pytest.FixtureRequest) -> Any:
    started = time.perf_counter()
    yield
    elapsed = time.perf_counter() - started
    counts = _source_construction_counts(request.node)
    request.node._test_health = {"seconds": elapsed, "constructions": dict(counts)}  # type: ignore[attr-defined]
    tier = next((name for name in TIERS if request.node.get_closest_marker(name)), "unknown")
    budgets = {"unit": (5, 1.0), "component": (30, 2.0)}
    if request.config.getoption("--strict-test-budgets") and tier in budgets:
        build_limit, seconds_limit = budgets[tier]
        builds = counts["build_default_state"]
        assert builds <= build_limit, f"{tier} test built {builds} full worlds (budget {build_limit})"
        assert elapsed <= seconds_limit, f"{tier} test took {elapsed:.2f}s (budget {seconds_limit:.2f}s)"


def pytest_sessionfinish(session: pytest.Session, exitstatus: int) -> None:
    report_path = str(session.config.getoption("--tier-report"))
    if not report_path:
        return
    records = getattr(session, "items", [])
    summary: dict[str, Any] = {
        "exit_status": exitstatus,
        "tests": len(records),
        "tiers": Counter(),
        "construction_counts": Counter(),
        "slowest": [],
    }
    timings: list[dict[str, Any]] = []
    for item in records:
        tier = next((name for name in TIERS if item.get_closest_marker(name)), "unknown")
        summary["tiers"][tier] += 1
        health = getattr(item, "_test_health", {})
        for name, count in health.get("constructions", {}).items():
            summary["construction_counts"][name] += count
        timings.append({"nodeid": item.nodeid, "tier": tier, "seconds": health.get("seconds", 0.0)})
    summary["tiers"] = dict(summary["tiers"])
    summary["construction_counts"] = dict(summary["construction_counts"])
    summary["slowest"] = sorted(timings, key=lambda row: row["seconds"], reverse=True)[:50]
    target = Path(report_path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(summary, indent=2, sort_keys=True) + "\n", encoding="utf-8")


@pytest.fixture(autouse=True)
def _block_outbound_network(monkeypatch: pytest.MonkeyPatch) -> None:
    def _blocked_urlopen(*args, **kwargs):  # noqa: ANN002, ANN003
        raise RuntimeError("Outbound network is disabled in tests. Mock urllib.request.urlopen in this test.")

    monkeypatch.setattr(urllib.request, "urlopen", _blocked_urlopen)
