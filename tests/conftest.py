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
from fastapi.testclient import TestClient

from storygame.test_metrics import begin_test, end_test

TIERS = ("unit", "component", "integration", "evaluation")
_HEALTH: dict[str, dict[str, Any]] = {}
_SESSION_WALL = 0.0
_SESSION_CPU = 0.0


def _orchestration_class(nodeid: str, runtime: dict[str, int]) -> str | None:
    """Classify complete-turn tests by the boundary they prove."""

    if "complete_turn" not in runtime:
        return None
    lowered = nodeid.lower()
    if "evaluation" in lowered or "reproducibility" in lowered:
        return "evaluation"
    if "savegame" in lowered or "save_and_load" in lowered or "persistence" in lowered:
        return "persistence"
    if any(token in lowered for token in ("dialogue", "npc", "conversation", "speaker")):
        return "dialogue boundary"
    if any(token in lowered for token in ("confirmation", "impact", "replan", "recovery")):
        return "recovery/confirmation"
    if any(token in lowered for token in ("inventory", "direction", "navigation", "take_path", "affordance")):
        return "deterministic affordance"
    if any(token in lowered for token in ("output", "narration", "debug", "editor", "parity")):
        return "output contract"
    return "proposal/commit contract"


_EVALUATION_FILES = {"test_staging_evaluation.py"}
_INTEGRATION_FILES = {
    "test_hosted_demo_e2e.py",
    "test_web_demo_v2.py",
}
_COMPONENT_FILES = {
    "test_cloudflare_turn_model.py",
}
_ORCHESTRATION_RETENTION_REASONS: dict[str, str] = {}


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


def pytest_sessionstart(session: pytest.Session) -> None:
    global _SESSION_WALL, _SESSION_CPU
    _SESSION_WALL = time.perf_counter()
    _SESSION_CPU = time.process_time()


def pytest_runtest_setup(item: pytest.Item) -> None:
    begin_test()
    _HEALTH[item.nodeid] = {"setup_seconds": time.perf_counter()}


@pytest.hookimpl(hookwrapper=True)
def pytest_runtest_call(item: pytest.Item) -> Any:
    record = _HEALTH[item.nodeid]
    setup_started = float(record["setup_seconds"])
    record["setup_seconds"] = time.perf_counter() - setup_started
    call_started = time.perf_counter()
    outcome = yield
    record["call_seconds"] = time.perf_counter() - call_started
    outcome.get_result()


@pytest.hookimpl(hookwrapper=True)
def pytest_runtest_teardown(item: pytest.Item, nextitem: pytest.Item | None) -> Any:
    if item.nodeid not in _HEALTH:
        yield
        return
    record = _HEALTH[item.nodeid]
    record["teardown_started"] = time.perf_counter()
    outcome = yield
    teardown_started = record.pop("teardown_started", None)
    if teardown_started is not None:
        record["teardown_seconds"] = time.perf_counter() - float(teardown_started)
    record["runtime"] = end_test()
    outcome.get_result()


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
        "runtime_counts": Counter(),
        "runtime_counts_by_tier": {},
        "timing": {
            "wall_seconds": time.perf_counter() - _SESSION_WALL,
            "cpu_seconds": time.process_time() - _SESSION_CPU,
        },
        "slowest": [],
        "top20_by_call_time": [],
        "top20_by_setup_time": [],
    }
    timings: list[dict[str, Any]] = []
    for item in records:
        tier = next((name for name in TIERS if item.get_closest_marker(name)), "unknown")
        summary["tiers"][tier] += 1
        health = getattr(item, "_test_health", {})
        for name, count in health.get("constructions", {}).items():
            summary["construction_counts"][name] += count
        measured = _HEALTH.get(item.nodeid, {})
        runtime = measured.get("runtime", {})
        tier_runtime = summary["runtime_counts_by_tier"].setdefault(tier, Counter())
        for name, count in runtime.items():
            if "." not in name:
                summary["runtime_counts"][name] += count
                tier_runtime[name] += count
        timings.append(
            {
                "nodeid": item.nodeid,
                "tier": tier,
                "setup_seconds": measured.get("setup_seconds", 0.0),
                "call_seconds": measured.get("call_seconds", 0.0),
                "teardown_seconds": measured.get("teardown_seconds", 0.0),
                "seconds": health.get("seconds", 0.0),
                "constructions": health.get("constructions", {}),
                "runtime": {name: count for name, count in runtime.items() if "." not in name},
                "orchestration_class": _orchestration_class(item.nodeid, runtime),
                "orchestration_retention_reason": (
                    _ORCHESTRATION_RETENTION_REASONS.get(_orchestration_class(item.nodeid, runtime))
                    if _orchestration_class(item.nodeid, runtime)
                    else None
                ),
                "commands": [
                    name.removeprefix("complete_turn.command.")
                    for name in runtime
                    if name.startswith("complete_turn.command.")
                ],
            }
        )
    summary["tiers"] = dict(summary["tiers"])
    summary["construction_counts"] = dict(summary["construction_counts"])
    summary["runtime_counts"] = dict(summary["runtime_counts"])
    summary["runtime_counts_by_tier"] = {
        tier: dict(counts) for tier, counts in summary["runtime_counts_by_tier"].items()
    }
    summary["orchestration_classes"] = dict(
        Counter(row["orchestration_class"] for row in timings if row["orchestration_class"])
    )
    summary["slowest"] = sorted(timings, key=lambda row: row["seconds"], reverse=True)[:50]
    summary["top20_by_call_time"] = sorted(timings, key=lambda row: row["call_seconds"], reverse=True)[:20]
    summary["top20_by_setup_time"] = sorted(timings, key=lambda row: row["setup_seconds"], reverse=True)[:20]
    target = Path(report_path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(summary, indent=2, sort_keys=True) + "\n", encoding="utf-8")


@pytest.fixture(autouse=True)
def _block_outbound_network(request: pytest.FixtureRequest, monkeypatch: pytest.MonkeyPatch) -> None:
    if request.node.get_closest_marker("live_e2e"):
        return

    def _blocked_urlopen(*args, **kwargs):  # noqa: ANN002, ANN003
        raise RuntimeError("Outbound network is disabled in tests. Mock urllib.request.urlopen in this test.")

    monkeypatch.setattr(urllib.request, "urlopen", _blocked_urlopen)


@pytest.fixture(autouse=True)
def _record_runtime_adapter_constructions(monkeypatch: pytest.MonkeyPatch) -> None:
    """Record actual client construction without sharing mutable app state."""

    original_init = TestClient.__init__

    def _recording_init(self: TestClient, *args: Any, **kwargs: Any) -> None:
        from storygame.test_metrics import record

        record("test_client")
        original_init(self, *args, **kwargs)

    monkeypatch.setattr(TestClient, "__init__", _recording_init)
