from __future__ import annotations

import json
from pathlib import Path

import pytest

from bench.pipeline_eval.__main__ import main
from bench.pipeline_eval.metrics import aggregate, clarification_unchanged, score_turn
from bench.pipeline_eval.model import EvalCase, Expectation, TurnObservation, grounded_state, load_cases
from bench.pipeline_eval.runner import PipelineArm, render_report
from storygame.runtime.engine import RuntimeEngine
from storygame.runtime.fixed_refusal import fixed_refusal_text
from storygame.runtime.state import RuntimeState
from storygame.runtime.validation import ProposalValidationError
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

    unknown_state = _write_json(
        tmp_path,
        [
            {
                "id": "unknown-state",
                "category": "x",
                "split": "diagnostic",
                "scene": "1A",
                "commands": ["Search the drawer."],
                "expect": {"state": {"mystery": "value"}},
            }
        ],
    )
    with pytest.raises(ValueError, match="unknown state key"):
        load_cases(unknown_state)
    unknown_value = _write_json(
        tmp_path,
        [
            {
                "id": "unknown-value",
                "category": "x",
                "split": "diagnostic",
                "scene": "1A",
                "commands": ["Search the drawer."],
                "expect": {"state": {"memory_card": "floating"}},
            }
        ],
    )
    with pytest.raises(ValueError, match="invalid value for state"):
        load_cases(unknown_value)
    accepted_state = _write_json(
        tmp_path,
        [
            {
                "id": "accepted-state",
                "category": "x",
                "split": "diagnostic",
                "scene": "1A",
                "commands": ["Search the drawer."],
                "expect": {"state": {"memory_card": "beneath_michelle_drawer"}},
            }
        ],
    )
    assert load_cases(accepted_state)[0].expect.state == {"memory_card": "beneath_michelle_drawer"}


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


@pytest.mark.parametrize(
    ("name", "expectation", "observed", "score_name"),
    (
        ("reference", Expectation(reference="drawer"), TurnObservation(reference="drawer"), "reference_correct"),
        ("action", Expectation(action="search"), TurnObservation(action="search"), "action_correct"),
        (
            "state",
            Expectation(state={"memory_card": "with_kristin"}),
            TurnObservation(state={"memory_card": "with_kristin"}),
            "state_correct",
        ),
        ("prose", Expectation(prose_must_not_assert=("a claim",)), TurnObservation(prose="quiet"), "prose_correct"),
        ("false_reveal", Expectation(allowed_reveals=("cue",)), TurnObservation(revealed_ids=()), "false_reveal"),
        (
            "unauthorized_creation",
            Expectation(creation="descriptive"),
            TurnObservation(created=()),
            "unauthorized_creation",
        ),
        (
            "forced_progress",
            Expectation(forced_progress=False),
            TurnObservation(forced_progress=False),
            "forced_progress",
        ),
        (
            "clarification_asked",
            Expectation(clarification=False),
            TurnObservation(clarified=False),
            "clarification_asked",
        ),
    ),
)
def test_expected_metrics_are_unmeasured_only_when_their_observation_is_missing(
    name: str,
    expectation: Expectation,
    observed: TurnObservation,
    score_name: str,
) -> None:
    missing = score_turn(expectation, TurnObservation())
    observed_score = score_turn(
        expectation,
        observed,
        claim_judge=lambda _prose, _claim: False,
    )
    not_expected = score_turn(Expectation(), TurnObservation())

    assert getattr(missing, f"{name}_unmeasured") is True
    assert getattr(missing, score_name) is None
    assert getattr(observed_score, f"{name}_unmeasured") is False
    assert getattr(observed_score, score_name) is not None
    assert getattr(not_expected, f"{name}_unmeasured") is False


def test_grounded_state_mapping_gap_is_unmeasured() -> None:
    state = RuntimeState.bootstrap(PACKAGE)
    state.facts.asserted = {
        fact
        for fact in state.facts.asserted
        if not (fact.predicate == "wk_parent" and fact.subject == "kristin_laptop")
    }
    score = score_turn(
        Expectation(state={"kristin_laptop": "truck_passenger_seat"}),
        TurnObservation(state=grounded_state(state)),
    )
    assert score.state_unmeasured is True
    assert score.state_correct is None


def test_false_reveal_is_independent_of_forced_progress() -> None:
    score = score_turn(
        Expectation(allowed_reveals=("cue",), forced_progress=False),
        TurnObservation(revealed_ids=("unknown",), forced_progress=False),
    )
    assert score.false_reveal is True
    assert score.forced_progress is True


def test_claim_judge_controls_prose_assertion_and_is_called_per_claim() -> None:
    expectation = Expectation(prose_must_not_assert=("the truck leaves", "the truck reaches the park"))
    calls: list[tuple[str, str]] = []

    def judge(prose: str, claim: str) -> bool:
        calls.append((prose, claim))
        return claim == "the truck leaves"

    assert score_turn(expectation, TurnObservation(prose="The truck leaves."), claim_judge=judge).prose_correct is False
    assert calls == [
        ("The truck leaves.", "the truck leaves"),
        ("The truck leaves.", "the truck reaches the park"),
    ]
    calls.clear()
    assert (
        score_turn(
            expectation, TurnObservation(prose="The truck stays put."), claim_judge=lambda *_: False
        ).prose_correct
        is True
    )
    assert score_turn(expectation, TurnObservation(prose="The truck stays put.")).prose_correct is None


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

    assert {
        "arm",
        "turns",
        "reference_correct",
        "action_correct",
        "state_correct",
        "prose_correct",
        "false_reveal",
        "unauthorized_creation",
        "forced_progress",
        "clarification_asked",
        "latency_s",
        "requests",
        "tokens",
        "state_unmeasured",
    } <= set(result)
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
    expected_state = {
        "memory_card": "beneath_michelle_drawer",
        "kristin_truck": "away",
        "kristin_laptop": "truck_passenger_seat",
    }
    assert all(observation.state == expected_state for observation in observations)
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


def test_render_report_marks_claim_prose_without_judge() -> None:
    case = _case(expect=Expectation(prose_must_not_assert=("the truck leaves",)))
    results = {"stub": {case.id: [score_turn(case.expect, TurnObservation())]}}
    assert "prose unchecked (no claim judge)" in render_report(results, (case,))


def test_render_report_prints_unmeasured_counts_per_arm() -> None:
    expectation = Expectation(
        reference="drawer",
        action="search",
        prose_must_not_assert=("the truck leaves",),
        allowed_reveals=("cue",),
        creation="descriptive",
        forced_progress=False,
        clarification=False,
    )
    case = _case(expect=expectation)
    score = score_turn(expectation, TurnObservation())

    report = render_report({"stub": {case.id: [score]}}, (case,))

    assert "'reference_unmeasured': 1" in report
    assert "'action_unmeasured': 1" in report
    assert "'prose_unmeasured': 1" in report
    assert "'false_reveal_unmeasured': 1" in report
    assert "'unauthorized_creation_unmeasured': 1" in report
    assert "'forced_progress_unmeasured': 1" in report
    assert "'clarification_asked_unmeasured': 1" in report


def test_smoke_cli_main(capsys: pytest.CaptureFixture[str]) -> None:
    assert main(["smoke"]) == 0
    assert "Pipeline evaluation report" in capsys.readouterr().out


def test_pipeline_arm_counts_guard_retry_and_sums_tokens(monkeypatch: pytest.MonkeyPatch) -> None:
    case = _case(commands=("Search the gap beneath the drawer.",))

    class RetryEngine(RuntimeEngine):
        def __init__(self, state: RuntimeState, provider) -> None:  # type: ignore[no-untyped-def]
            super().__init__(state, provider)
            self.state.active_event_ids.add("SL-1A-E")
            original_validate = self.narration_validator.validate
            first_validation = True

            def validate(*args, **kwargs):  # type: ignore[no-untyped-def]
                nonlocal first_validation
                if first_validation:
                    first_validation = False
                    raise ProposalValidationError("test guard retry", code="test_guard_retry")
                return original_validate(*args, **kwargs)

            self.narration_validator.validate = validate

    monkeypatch.setattr("bench.pipeline_eval.runner.RuntimeEngine", RetryEngine)
    replies = iter(
        (
            {
                "segments": [
                    {
                        "kind": "narration",
                        "text": "Kristin finds Michelle's memory card taped beneath the drawer. "
                        "She takes it with her. Her laptop is in her truck outside.",
                        "grounding_ids": ["k_sl_1a_b_r0"],
                    }
                ],
                "selected_knowledge_ids": ["k_sl_1a_b_r0"],
                "usage": 5,
            },
            {
                "segments": [
                    {
                        "kind": "narration",
                        "text": "Kristin finds Michelle's memory card taped beneath the drawer. "
                        "She takes it with her. Her laptop is in her truck outside.",
                        "grounding_ids": ["k_sl_1a_b_r0"],
                    }
                ],
                "selected_knowledge_ids": ["k_sl_1a_b_r0"],
                "usage": 3,
            },
        )
    )

    observations = PipelineArm(lambda _command: next(replies)).play(case, RuntimeState.bootstrap(PACKAGE))

    assert observations[0].requests == 2
    assert observations[0].tokens == 8


def test_pipeline_arm_counts_real_engine_refusal_without_narration(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("CLOUDFLARE_WORKER_URL", "https://worker.invalid/turn")
    case = _case(commands=("Carry the workstation to the truck.",))
    classifier_calls: list[object] = []
    narrator_calls: list[str] = []

    def ask(_state: object, questions: object) -> dict[str, object]:
        classifier_calls.append(questions)
        key = next(iter(questions))
        return {key: {"noul": 0.0 if key == "names_other_action" else 1.0}}

    def narrator(command: str) -> dict[str, object]:
        narrator_calls.append(command)
        return {}

    state = RuntimeState.bootstrap(PACKAGE)
    before = state.snapshot()
    observation = PipelineArm(narrator, refusal_ask=ask).play(case, state)[0]

    assert narrator_calls == []
    assert observation.requests == len(classifier_calls) >= 1
    assert observation.tokens == 0
    assert observation.state == grounded_state(state)
    assert state.snapshot() == before
    assert observation.prose == fixed_refusal_text(PACKAGE, ("workstation",), False)


def test_pipeline_arm_refusal_classifier_and_narrator_requests_share_turn_accounting(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("CLOUDFLARE_WORKER_URL", "https://worker.invalid/turn")
    case = _case(commands=("Search the kitchen.",))
    classifier_calls: list[object] = []
    narrator_calls: list[str] = []

    def ask(_state: object, questions: object) -> dict[str, object]:
        classifier_calls.append(questions)
        key = next(iter(questions))
        return {key: {"noul": 0.0}}

    def narrator(command: str) -> dict[str, object]:
        narrator_calls.append(command)
        return {"segments": [{"kind": "narration", "text": "Kristin searches the kitchen."}], "usage": 3}

    observation = PipelineArm(narrator, refusal_ask=ask).play(case, RuntimeState.bootstrap(PACKAGE))[0]

    assert narrator_calls == list(case.commands)
    assert observation.requests == len(classifier_calls) + 1
    assert observation.tokens == 3


def test_pipeline_arm_real_refusal_save_load_keeps_followup_working(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("CLOUDFLARE_WORKER_URL", "https://worker.invalid/turn")
    case = _case(commands=("Carry the workstation to the truck.", "Search the kitchen."), save_load_after=0)
    narrator_calls: list[str] = []

    def ask(_state: object, questions: object) -> dict[str, object]:
        key = next(iter(questions))
        return {key: {"noul": 0.0 if key == "names_other_action" else 1.0}}

    def narrator(command: str) -> dict[str, object]:
        narrator_calls.append(command)
        return {"segments": [{"kind": "narration", "text": "Kristin searches the kitchen."}]}

    observations = PipelineArm(narrator, refusal_ask=ask).play(case, RuntimeState.bootstrap(PACKAGE))

    assert len(observations) == 2
    assert observations[0].prose == fixed_refusal_text(PACKAGE, ("workstation",), False)
    assert observations[0].state == observations[1].state
    assert narrator_calls == ["Search the kitchen."]


def test_pipeline_arm_reports_state_after_real_world_effect(monkeypatch: pytest.MonkeyPatch) -> None:
    case = _case(commands=("Search the gap beneath the drawer.",))

    class MemoryRecoveryEngine(RuntimeEngine):
        def __init__(self, state: RuntimeState, provider) -> None:  # type: ignore[no-untyped-def]
            super().__init__(state, provider)
            self.state.active_event_ids.add("SL-1A-E")

    monkeypatch.setattr("bench.pipeline_eval.runner.RuntimeEngine", MemoryRecoveryEngine)

    def narrator(_command: str) -> dict[str, object]:
        return {
            "segments": [
                {
                    "kind": "narration",
                    "text": "Kristin finds Michelle's memory card taped beneath the drawer. "
                    "She takes it with her. Her laptop is in her truck outside.",
                    "grounding_ids": ["k_sl_1a_b_r0"],
                }
            ],
            "selected_knowledge_ids": ["k_sl_1a_b_r0"],
        }

    observation = PipelineArm(narrator).play(case, RuntimeState.bootstrap(PACKAGE))[0]
    score = score_turn(Expectation(state={"memory_card": "with_kristin"}), observation)

    assert observation.state["memory_card"] == "with_kristin"
    assert score.state_correct is True


def test_ungrounded_state_is_unmeasured_and_reported() -> None:
    state = RuntimeState.bootstrap(PACKAGE)
    state.facts.asserted = {
        fact
        for fact in state.facts.asserted
        if not (fact.predicate == "wk_parent" and fact.subject == "kristin_laptop")
    }
    observation = TurnObservation(state=grounded_state(state), requests=2)
    expectation = Expectation(state={"kristin_laptop": "truck_passenger_seat"})
    score = score_turn(expectation, observation)
    cases = (_case(expect=expectation),)
    report = render_report({"stub": {cases[0].id: [score]}}, cases)

    assert "kristin_laptop" not in observation.state
    assert score.state_correct is None
    assert score.state_unmeasured is True
    assert "'requests': {'mean': 2" in report
    assert "'state_unmeasured': 1" in report
