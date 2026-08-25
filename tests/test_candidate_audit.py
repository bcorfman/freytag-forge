"""Story-agnostic candidate audit coverage."""

from __future__ import annotations

import json
from pathlib import Path

from storygame.authoring.audit_cli import main as audit_main
from storygame.authoring.candidate_audit import audit_candidate
from storygame.authoring.causal_profiles import CausalProfileRegistry
from tests.test_causal_story_contract import _story


def _candidate(path: Path, *, mutate=None) -> None:
    story = _story()
    if mutate:
        story = mutate(story)
    path.write_text(
        json.dumps({"story": story, "request_count": 1, "validation_results": [], "accepted": True, "diagnostics": []}),
        encoding="utf-8",
    )


def _profiles() -> CausalProfileRegistry:
    return CausalProfileRegistry.from_directory(Path("data/genre_profiles"))


def test_audit_passes_without_story_specific_ids(tmp_path: Path) -> None:
    candidate = tmp_path / "generic.candidate.json"
    _candidate(candidate)

    report = audit_candidate(candidate, _profiles())

    assert report.passed
    assert [check.id for check in report.checks] == [
        "compiler_validation",
        "terminal_roles",
        "knowledge_boundaries",
        "route_diversity",
        "failure_forward",
        "map_and_custody",
    ]
    assert report.runtime_projection is not None
    assert report.runtime_projection.participant_placements.declared_count == 1
    assert report.runtime_projection.participant_placements.fact_backed_count == 0
    assert report.runtime_projection.evidence_realization.declared_count == 4
    assert not report.runtime_projection.complete


def test_audit_reports_route_and_failure_forward_defects(tmp_path: Path) -> None:
    candidate = tmp_path / "broken.candidate.json"

    def mutate(story: dict[str, object]) -> dict[str, object]:
        story["realization_routes"] = [
            {
                **story["realization_routes"][0],
                "failure_forward": {"alternative_route_ids": [], "consequence_truth_ids": []},
            }
        ]
        return story

    _candidate(candidate, mutate=mutate)
    report = audit_candidate(candidate, _profiles())

    assert not report.passed
    assert report.checks[0].status == "fail"
    assert all(check.status == "skipped" for check in report.checks[1:])


def test_audit_cli_writes_report_and_returns_failure_status(tmp_path: Path) -> None:
    candidate = tmp_path / "generic.candidate.json"
    output = tmp_path / "audit.json"
    _candidate(candidate)

    assert audit_main(["--candidate", str(candidate), "--format", "json", "--output", str(output)]) == 0
    report = json.loads(output.read_text(encoding="utf-8"))
    assert report["schema_version"] == "story-blueprint-audit-v1"
    assert report["candidate_filename"] == candidate.name
    assert report["runtime_projection"]["complete"] is False
    assert report["runtime_projection"]["suggested_actions"][0]["supported"] is False


def test_audit_cli_defaults_to_human_readable_markdown(tmp_path: Path, capsys) -> None:
    candidate = tmp_path / "generic.candidate.json"
    _candidate(candidate)

    assert audit_main(["--candidate", str(candidate)]) == 0
    output = capsys.readouterr().out
    assert "# Story Blueprint Audit" in output
    assert "## Story summary" in output
    assert "### Causal timeline" in output
    assert "### Evidence routes" in output
    assert "| `terminal_roles` | **PASS** |" in output
    assert "## Phase 0 runtime projection" in output
    assert "Participant placements: **0 / 1**" in output
    assert "Evidence realization: **0 / 4**" in output
    assert "## Human review" in output


def test_audit_cli_overwrites_existing_report(tmp_path: Path) -> None:
    candidate = tmp_path / "generic.candidate.json"
    output = tmp_path / "audit.md"
    _candidate(candidate)
    output.write_text("old report", encoding="utf-8")

    assert audit_main(["--candidate", str(candidate), "--output", str(output)]) == 0
    assert output.read_text(encoding="utf-8").startswith("# Story Blueprint Audit")
