from __future__ import annotations

import json
from pathlib import Path

import pytest

import factory.checks.carry_matrix as carry_matrix_module
from storygame.runtime.facts import Fact, FactStore
from storygame.runtime.state import CueStage, RuntimeState, TurnRecord
from storygame.story_package.loader import load_story_package
from storygame.story_package.models import FactPredicate
from storygame.story_source import compile_source_tree
from tests.story_source.helpers import copy_fixture

ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture
def mini_package(tmp_path: Path):
    """Compile the valid two-scene fixture; it is small enough for every unit search."""

    return compile_source_tree(copy_fixture("mini_ok", tmp_path / "mini"))


def test_mini_fixture_is_playable_by_the_offline_search(mini_package) -> None:
    report = carry_matrix_module.carry_matrix(mini_package, workers=1, search_budget=40)

    assert report.entry_states["1A"] == 1
    assert report.searches > 0
    assert report.turns > 0


def _identity(package, reveals: tuple[str, ...], *, different: str | None = None) -> tuple:
    state = RuntimeState.bootstrap(package)
    state.turn_index = 4
    state.cue_stages = (CueStage(fact_id="cue", stage=2, last_turn=3, visit_entered_at=0),)
    earlier = [
        TurnRecord(id="turn_1", reveal_ids=reveals),
        TurnRecord(id="turn_2", reveal_ids=(different or "same_b",)),
        TurnRecord(id="turn_3", reveal_ids=("same_c",)),
        TurnRecord(id="turn_4", reveal_ids=("same_d",)),
    ]
    state.turn_records = earlier
    return carry_matrix_module._identity_key(
        state,
        "1A",
        carry_matrix_module.forward_reads(package, "1A"),
        carry_matrix_module._transition_targets(package),
    )


def test_point_identity_merges_orders_but_separates_a_different_pick(mini_package) -> None:
    first_order = _identity(mini_package, ("same_a",), different="same_b")
    second_order = _identity(mini_package, ("same_b",), different="same_a")
    different_pick = _identity(mini_package, ("different",), different="same_b")

    assert first_order == second_order
    assert first_order != different_pick


def test_state_key_drops_unread_flag_and_keeps_world_parent(mini_package) -> None:
    base = RuntimeState.bootstrap(mini_package)
    base.facts = FactStore(asserted={Fact(predicate="read_flag", subject="story", value="true")})
    unread = base.model_copy(deep=True)
    unread.facts.assert_fact(Fact(predicate="unread_flag", subject="story", value="true"))
    world_changed = base.model_copy(deep=True)
    world_changed.facts.assert_fact(Fact(predicate="wk_parent", subject="item", object="truck"))
    read_ids = frozenset({"read_flag"})

    assert carry_matrix_module.state_key(base, read_ids) == carry_matrix_module.state_key(unread, read_ids)
    assert carry_matrix_module.state_key(base, read_ids) != carry_matrix_module.state_key(world_changed, read_ids)


def test_seeded_transition_defect_reports_main_no_path(mini_package) -> None:
    impossible = "carry_matrix_never_produced"
    transitions = tuple(
        transition.model_copy(
            update={"triggers": tuple(FactPredicate(fact_id=impossible, equals=True) for _ in transition.triggers)}
        )
        if transition.source_scene_id == "1A"
        else transition
        for transition in mini_package.pacing.transitions
    )
    defect = mini_package.model_copy(
        update={"pacing": mini_package.pacing.model_copy(update={"transitions": transitions})}
    )

    report = carry_matrix_module.carry_matrix(defect, scenes=["1A"], workers=1, search_budget=40)

    assert any(
        cell.scene == "1A" and cell.label == "main" and cell.reason in {"no_path", "budget"} for cell in report.stuck
    )


def test_default_budget_bounds_seeded_stuck_search(mini_package) -> None:
    impossible = "carry_matrix_never_produced"
    transitions = tuple(
        transition.model_copy(
            update={"triggers": tuple(FactPredicate(fact_id=impossible, equals=True) for _ in transition.triggers)}
        )
        if transition.source_scene_id == "1A"
        else transition
        for transition in mini_package.pacing.transitions
    )
    defect = mini_package.model_copy(
        update={"pacing": mini_package.pacing.model_copy(update={"transitions": transitions})}
    )
    package = carry_matrix_module._legacy_package(defect)
    state = RuntimeState.bootstrap(package)
    worker = carry_matrix_module._SearchWorker(
        package,
        "1A",
        carry_matrix_module.forward_reads(package, "1A"),
        carry_matrix_module.DEFAULT_SEARCH_BUDGET,
    )

    result = worker.search(carry_matrix_module._Point(state.snapshot()))

    assert result.points_used <= carry_matrix_module.DEFAULT_SEARCH_BUDGET
    report = carry_matrix_module.carry_matrix(defect, workers=1)

    assert report.search_budget == (carry_matrix_module.DEFAULT_SEARCH_BUDGET)
    assert report.not_run == [mini_package.pacing.scenes[1].scene_id]


def test_seeded_deviation_trap_is_reported_with_its_label(mini_package, monkeypatch) -> None:
    original = carry_matrix_module._SearchWorker.deviations

    def trap_one_deviation(worker, path):
        results = list(original(worker, path))
        if results:
            first = results[0]
            results[0] = carry_matrix_module._DeviationResult(first.label, "no_path", first.turns)
        return tuple(results)

    monkeypatch.setattr(carry_matrix_module._SearchWorker, "deviations", trap_one_deviation)
    report = carry_matrix_module.carry_matrix(mini_package, scenes=["1A"], workers=1, search_budget=40)

    assert any(cell.label.startswith("t") and cell.reason == "no_path" for cell in report.stuck)
    assert not any(cell.label == "main" for cell in report.stuck)


def test_second_search_reuses_good_memo_without_new_turns(mini_package) -> None:
    package = carry_matrix_module._legacy_package(mini_package)
    state = RuntimeState.bootstrap(package)
    worker = carry_matrix_module._SearchWorker(package, "1A", carry_matrix_module.forward_reads(package, "1A"), 40)
    point = carry_matrix_module._Point(state.snapshot())

    first = worker.search(point)
    turns = worker.stats.turns
    second = worker.search(point)

    assert first.outcome == "earned"
    assert second.outcome == "earned"
    assert worker.stats.turns == turns
    assert worker.stats.memo_hits >= 1


def test_carry_matrix_too_large_is_explicit(mini_package, monkeypatch) -> None:
    monkeypatch.setattr(carry_matrix_module, "state_key", lambda *_args: object())

    with pytest.raises(carry_matrix_module.CarryMatrixTooLarge):
        carry_matrix_module.carry_matrix(mini_package, max_states_per_scene=1, workers=1, search_budget=40)


def test_one_branch_entry_choices_are_default_or_one_choice(mini_package) -> None:
    report = carry_matrix_module.carry_matrix(mini_package, mode="one_branch", workers=1, search_budget=40)

    assert all(len(choice) <= 1 for choices in report.entry_choices.values() for choice in choices)


@pytest.mark.nightly
def test_pairwise_two_scene_fixture_is_marked_nightly_until_a_three_scene_fixture_exists(mini_package) -> None:
    """The accepted fixture has two scenes, so a length-two carry needs a three-scene fixture."""

    report = carry_matrix_module.carry_matrix(mini_package, mode="pairwise", workers=1, search_budget=40)
    assert all(len(choice) <= 2 for choices in report.entry_choices.values() for choice in choices)


def test_cli_exit_codes_and_json_shape(tmp_path: Path, monkeypatch, capsys) -> None:
    clean = carry_matrix_module.CarryReport("one_branch", {}, {}, 0, 0, 0, [], 0.01, {})
    stuck = carry_matrix_module.CarryReport(
        "one_branch",
        {"1A": 1},
        {"1A": 1},
        1,
        1,
        0,
        [carry_matrix_module.StuckCell("1A", 0, (), "main", "no_path", 0, ())],
        0.01,
        {"1A": 0.01},
    )
    monkeypatch.setattr(carry_matrix_module, "load_story_package", lambda _path: object())
    reports = iter((clean, stuck))
    monkeypatch.setattr(carry_matrix_module, "carry_matrix", lambda *_args, **_kwargs: next(reports))
    output = tmp_path / "report.json"

    assert carry_matrix_module.main(["--scene", "1A", "--json", str(output)]) == 0
    assert carry_matrix_module.main(["--scene", "1A", "--json", str(output)]) == 1
    assert {
        "mode",
        "entry_states",
        "branches",
        "searches",
        "turns",
        "memo_hits",
        "stuck",
        "seconds",
        "seconds_by_scene",
        "search_budget",
        "max_search_points",
        "not_run",
        "entry_choices",
    } == set(json.loads(output.read_text(encoding="utf-8")))
    assert (
        "TOTAL entry_states=1 searches=1 turns=1 memo_hits=0 "
        f"search_budget={carry_matrix_module.DEFAULT_SEARCH_BUDGET} "
        "max_search_points=0 stuck=1"
    ) in capsys.readouterr().out


@pytest.mark.nightly
def test_whole_real_story_has_a_reachable_entry_state_for_every_scene() -> None:
    package = load_story_package(ROOT / "data/stories/continuity-initiative")
    report = carry_matrix_module.carry_matrix(package, mode="one_branch")

    assert all(report.entry_states.get(window.scene_id, 0) >= 1 for window in package.pacing.scenes)
