from __future__ import annotations

import ast
from pathlib import Path

import pytest

from storygame.test_metrics import begin_test, end_test, record, reset_totals, totals
from tests.conftest import _orchestration_class


def test_all_collected_tests_have_one_declared_performance_tier(request: pytest.FixtureRequest) -> None:
    item = request.node
    tiers = [name for name in ("unit", "component", "integration", "evaluation") if item.get_closest_marker(name)]
    assert len(tiers) == 1


def test_test_modules_have_no_duplicate_test_definitions() -> None:
    duplicates: list[str] = []
    for path in sorted(Path(__file__).parent.glob("test_*.py")):
        tree = ast.parse(path.read_text(encoding="utf-8"))
        names = [node.name for node in ast.walk(tree) if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))]
        for name in sorted({name for name in names if name.startswith("test_")}):
            if names.count(name) > 1:
                duplicates.append(f"{path.name}:{name}")
    assert duplicates == []


def test_runtime_metrics_are_scoped_and_keep_process_totals() -> None:
    reset_totals()
    begin_test()
    record("complete_turn", command="look")
    record("full_world_build", genre="fixture")
    assert end_test() == {
        "complete_turn": 1,
        "complete_turn.command.look": 1,
        "full_world_build": 1,
        "full_world_build.genre.fixture": 1,
    }
    assert totals() == {"complete_turn": 1, "full_world_build": 1}
    assert end_test() == {}
    classification = _orchestration_class("tests/test_web_demo_v2.py::test_turn", {"complete_turn": 1})
    assert classification == "proposal/commit contract"


@pytest.mark.parametrize("tier", ("unit", "component", "integration", "evaluation"))
def test_tier_names_are_stable(tier: str) -> None:
    assert tier in {"unit", "component", "integration", "evaluation"}


def test_active_test_commands_do_not_pin_a_fragile_collection_count() -> None:
    root = Path(__file__).resolve().parents[1]
    active_paths = [root / "README.md", *sorted((root / ".github" / "workflows").glob("*.yml"))]

    stale_commands = [path for path in active_paths if "--expected-test-count" in path.read_text(encoding="utf-8")]

    assert stale_commands == []
