from __future__ import annotations

import json
from pathlib import Path

import pytest

from bench.pipeline_eval.__main__ import main
from bench.pipeline_eval.metrics import aggregate, clarification_unchanged, score_turn
from bench.pipeline_eval.model import EvalCase, Expectation, TurnObservation, load_cases
from bench.pipeline_eval.runner import PipelineArm, render_report
from storygame.runtime.state import RuntimeState
from storygame.story_package.loader import load_story_package

PACKAGE = load_story_package(Path("data/stories/continuity-initiative"))


def _case(**updates: object) -> EvalCase:
    values: dict[str, object] = {
        "id": "case-1",
        "category": "references",
        "split": "diagnostic",
        "scene": "1A",
        "setup_facts": (),
        "commands": ("Search the kitchen.",),
        "save_load_after": None,
        "expect": Expectation(),
    }
    values.update(updates)
    return EvalCase(**values)  # type: ignore[arg-type]


def test_loading_and_validation(tmp_path: Path) -> None:
    path = tmp_path / "cases.json"
    path.write_text(
        json.dumps(
            [
                {
                    "id": "one",
                    "category": "references",
                    "split": "held_out",
                    "scene": "1A",
                    "commands": ["Search the kitchen."],
                    "expect": {"prose_includes": ["kitchen"]},
                }
            ]
        ),
        encoding="utf-8",
    )
    cases = load_cases(path)
    assert cases[0].split == "held_out"
    for split in ("wrong",):
        invalid = _write_json(
            tmp_path,
            [
                {
                    "id": "x",
                    "category": "x",
                    "split": split,
                    "scene": "1A",
                    "commands": ["Search the kitchen."],
                }
            ],
        )
        with pytest.raises(ValueError, match="invalid split"):
            load_cases(invalid)
    duplicate = _write_json(
        tmp_path,
        [
            {"id": "same", "category": "x", "split": "diagnostic", "scene": "1A", "commands": ["Search the kitchen."]},
            {"id": "same", "category": "x", "split": "diagnostic", "scene": "1A", "commands": ["Open the drawer."]},
        ],
    )
    with pytest.raises(ValueError, match="duplicate"):
        load_cases(duplicate)
    empty = _write_json(
        tmp_path,
        [{"id": "empty", "category": "x", "split": "diagnostic", "scene": "1A", "commands": []}],
    )
    with pytest.raises(ValueError, match="non-empty"):
        load_cases(empty)


def _write_json(tmp_path: Path, payload: object) -> Path:
    path = tmp_path / f"case-{len(list(tmp_path.iterdir()))}.json"
    path.write_text(json.dumps(payload), encoding="utf-8")
    return path


def test_metrics_are_scored_independently() -> None:
    expectation = Expectation(
        reference="drawer",
        prose_includes=("drawer",),
        prose_excludes=("warehouse",),
        allowed_reveals=("known-cue",),
        creation="descriptive",
        forced_progress=False,
    )
    score = score_turn(
        expectation,
        TurnObservation(
            reference="drawer",
            prose="A warehouse appears.",
            revealed_ids=(),
            forced_progress=False,
            created=(("warehouse", "interactable"),),
        ),
    )
    assert score.reference_correct is True
    assert score.prose_correct is False
    assert score.false_reveal is False
    assert score.unauthorized_creation is True
    assert score.forced_progress is True


def test_false_reveal_is_independent_of_forced_progress() -> None:
    score = score_turn(
        Expectation(allowed_reveals=("cue",), forced_progress=False),
        TurnObservation(revealed_ids=("unknown",), forced_progress=False),
    )
    assert score.false_reveal is True
    assert score.forced_progress is True


def test_clarification_unchanged_uses_real_snapshots() -> None:
    state = RuntimeState.bootstrap(PACKAGE)
    before = state.snapshot()
    unchanged = state.snapshot()
    assert clarification_unchanged(before, unchanged)
    state.turn_index += 1
    assert not clarification_unchanged(before, state.snapshot())


def test_aggregate_has_no_combined_metric_keys() -> None:
    result = aggregate(
        [score_turn(Expectation(reference="x"), TurnObservation(reference="x"))],
        "stub",
    )

    def keys(value: object) -> set[str]:
        if isinstance(value, dict):
            return set(value) | {key for child in value.values() for key in keys(child)}
        return set()

    assert not keys(result) & {"overall", "accuracy", "total", "score", "capture_accuracy"}


def test_pipeline_arm_save_load_and_second_command() -> None:
    case = _case(commands=("Search the kitchen.", "Open the drawer."), save_load_after=0)
    calls: list[str] = []

    def narrator(command: str) -> dict[str, object]:
        calls.append(command)
        return {"segments": [{"kind": "narration", "text": f"You complete: {command}"}], "usage": 7}

    arm = PipelineArm(narrator)
    observations = arm.play(case, RuntimeState.bootstrap(PACKAGE))
    assert len(observations) == 2
    assert calls == list(case.commands)
    assert all(observation.state == {} for observation in observations)
    assert all(observation.tokens == 7 for observation in observations)


def test_render_report_lists_successes_and_held_out() -> None:
    cases = (
        _case(id="diagnostic", expect=Expectation(reference="drawer")),
        _case(id="held", split="held_out", expect=Expectation(reference="drawer")),
    )
    results = {
        "stub": {
            "diagnostic": [score_turn(cases[0].expect, TurnObservation(reference="drawer"))],
            "held": [score_turn(cases[1].expect, TurnObservation(reference="drawer"))],
        }
    }
    report = render_report(results, cases)
    assert "diagnostic [diagnostic] turn 1" in report
    assert "held [held_out] turn 1" in report
    assert "reference_correct=True" in report


def test_smoke_cli_main(capsys: pytest.CaptureFixture[str]) -> None:
    assert main(["smoke"]) == 0
    assert "Pipeline evaluation report" in capsys.readouterr().out
