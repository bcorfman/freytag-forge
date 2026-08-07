from __future__ import annotations

import ast
from pathlib import Path

import pytest

from storygame.test_metrics import begin_test, end_test, record, reset_totals, totals
from tests.conftest import _orchestration_class
from tests.fast_fixtures import (
    clone_runtime_state,
    make_cached_story_state,
    make_tiny_package,
    make_tiny_state,
)


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


def test_fast_runtime_fixture_is_fact_backed_and_isolated() -> None:
    package = make_tiny_package()
    first = make_tiny_state(package=package)
    second = clone_runtime_state(first)

    second.player.flags["changed"] = True
    second.world.rooms[package.room_id].item_ids = ()
    second.world_facts.assert_fact("flag", "player", "changed")

    assert first.player.flags == {"started": True}
    assert first.world.rooms[package.room_id].item_ids == (package.item_id,)
    assert not first.world_facts.holds("flag", "player", "changed")
    assert first.world_facts.holds("room_item", package.room_id, package.item_id)

    cached_first = make_cached_story_state(seed=12, genre="mystery")
    cached_second = make_cached_story_state(seed=13, genre="mystery")
    cached_second.player.flags["isolated"] = True
    assert cached_first.seed == 12
    assert "isolated" not in cached_first.player.flags


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
    examples = {
        "tests/test_savegame_sqlite.py::test_load_resume": "persistence",
        "tests/test_cli.py::test_run_turn_direction_alias": "deterministic affordance",
        "tests/test_cli.py::test_run_turn_dialogue_boundary": "dialogue boundary",
        "tests/test_cli.py::test_run_turn_confirmation": "recovery/confirmation",
        "tests/test_cli.py::test_run_turn_output_contract": "output contract",
        "tests/test_evaluation.py::test_replay": "evaluation",
        "tests/test_cli.py::test_run_turn_novel_action": "proposal/commit contract",
    }
    assert all(
        _orchestration_class(nodeid, {"complete_turn": 1}) == expected
        for nodeid, expected in examples.items()
    )


@pytest.mark.parametrize("tier", ("unit", "component", "integration", "evaluation"))
def test_tier_names_are_stable(tier: str) -> None:
    assert tier in {"unit", "component", "integration", "evaluation"}
