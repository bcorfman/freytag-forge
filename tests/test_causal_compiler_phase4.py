from __future__ import annotations

import json
from pathlib import Path

import pytest

from storygame.authoring.causal_profiles import CausalProfileRegistry
from storygame.authoring.compiler import CompilationError
from storygame.authoring.evaluation import (
    Phase4Evaluation,
    evaluate_corpus,
    write_evaluation,
)
from storygame.authoring.sources import StorySourceLoader
from tests.test_causal_story_contract import _story


class _Transport:
    def __init__(self, source, *, repair: bool = False) -> None:
        self.calls = 0
        self.source = source
        self.repair = repair

    def generate(self, prompt: str, *, json_object: bool) -> dict[str, object]:
        self.calls += 1
        candidate = _story()
        candidate["provenance"] = self.source.provenance()
        if self.calls == 1 and self.repair:
            candidate["revelations"][0]["gate_beat_ids"] = ["resolution"]
        return candidate


def _source():
    return StorySourceLoader(Path("data/story_outlines.yaml"), Path("data/genre_profiles")).select_outline("122")


def test_phase4_evaluation_records_first_pass_repair_diagnostics_and_diff():
    transport = _Transport(_source(), repair=True)
    report = evaluate_corpus(
        (_source(),),
        lambda: transport,
        CausalProfileRegistry.from_directory(Path("data/genre_profiles")),
        provider="test",
        model="fixture",
    )

    assert report.schema_version == "causal-compiler-phase4-evaluation-v1"
    assert report.summary.cases == 1
    assert report.summary.repair_attempts == 1
    assert report.cases[0].structural_diff
    assert report.cases[0].diagnostic_codes
    assert report.baseline.schema_version == "story-blueprint-phase0-baseline-v1"


def test_phase4_evaluation_records_exhaustion_without_fabricating_success():
    source = _source()

    def factory():
        class Failing:
            def generate(self, prompt: str, *, json_object: bool):
                raise CompilationError("PROVIDER_DOWN", "offline")

        return Failing()

    report = evaluate_corpus(
        (source,),
        factory,
        CausalProfileRegistry.from_directory(Path("data/genre_profiles")),
        provider="test",
        model="fixture",
    )

    case = report.cases[0]
    assert case.accepted is False
    assert case.error_code == "BLUEPRINT_COMPILATION_EXHAUSTED"
    assert report.summary.budget_exhaustions == 1


def test_phase4_report_write_is_immutable_and_json_round_trips(tmp_path: Path):
    report = Phase4Evaluation(schema_version="causal-compiler-phase4-evaluation-v1", cases=(), summary={})
    output = tmp_path / "phase4.evaluation.json"
    write_evaluation(output, report)
    assert json.loads(output.read_text(encoding="utf-8"))["schema_version"] == report.schema_version
    with pytest.raises(CompilationError, match="EVALUATION_OUTPUT_EXISTS"):
        write_evaluation(output, report)
