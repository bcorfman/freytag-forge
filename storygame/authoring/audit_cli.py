"""Operator command for repeatable, read-only candidate audits."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from pydantic import ValidationError

from storygame.authoring.blueprint_compiler import BlueprintCompilation
from storygame.authoring.candidate_audit import CandidateAuditReport, audit_candidate
from storygame.authoring.causal_profiles import CausalProfileRegistry
from storygame.authoring.spatial_audit import RuntimeProjectionAudit


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="storygame-blueprint-audit")
    parser.add_argument("--candidate", required=True, type=Path)
    parser.add_argument("--output", type=Path, help="optional report path")
    parser.add_argument("--format", choices=("markdown", "json"), default="markdown")
    parser.add_argument("--profile-root", type=Path, default=Path("data/genre_profiles"))
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    report = audit_candidate(args.candidate, CausalProfileRegistry.from_directory(args.profile_root))
    rendered = _render(report, args.format, _load_story(args.candidate))
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(rendered, encoding="utf-8")
    else:
        print(rendered, end="")
    return 0 if report.passed else 1


def _render(report: CandidateAuditReport, report_format: str, story: object | None = None) -> str:
    if report_format == "json":
        return report.model_dump_json(indent=2) + "\n"
    status = "PASS" if report.passed else "FAIL"
    lines = [
        f"# Story Blueprint Audit: {report.candidate_filename}",
        "",
        f"**Overall:** {status}",
        f"**SHA-256:** `{report.candidate_sha256 or 'unavailable'}`",
        "",
        "## Automated checks",
        "",
        "| Check | Status | Findings |",
        "| --- | --- | --- |",
    ]
    for check in report.checks:
        findings = "<br>".join(check.diagnostics) if check.diagnostics else "—"
        lines.append(f"| `{check.id}` | **{check.status.upper()}** | {findings} |")
    coverage = report.storylet_coverage
    lines.extend(
        [
            "",
            "## Storylet coverage",
            "",
            f"- By beat: {coverage.by_beat or '—'}",
            f"- By purpose: {coverage.by_purpose or '—'}",
            f"- By realization mode: {coverage.by_realization_mode or '—'}",
            f"- By route family: {coverage.by_route_family or '—'}",
            f"- Failure-forward chains: {coverage.failure_forward_chains or '—'}",
        ]
    )
    if report.runtime_projection is not None:
        lines.extend(_runtime_projection_lines(report.runtime_projection))
    if story is not None:
        lines[5:5] = _story_summary(story)
    lines.extend(
        [
            "",
            "## Human review",
            "",
            "Use the passing automated checks as evidence, then record every required editorial decision, including:",
            "",
            "- `terminal_roles`: Does the ending prove the intended solution or goal?",
            "- `knowledge_boundaries`: Is the opening spoiler-safe?",
            "- `route_diversity`: Are the alternative evidence routes meaningfully different?",
            "- `failure_forward`: Do failed attempts create pressure or another lead?",
            "- `map_and_custody`: Are clues reachable, plausible, and held sensibly?",
            "- `character_voice_distinction`: Do public profiles make the characters recognizably distinct?",
            "- `catchphrase_and_stereotype_safety`: Do profiles avoid stereotypes and repeated catchphrase gimmicks?",
            "",
            "This report is diagnostic evidence. It is not a reviewed or runtime artifact.",
            "",
        ]
    )
    return "\n".join(lines)


def _load_story(path: Path) -> object | None:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
        return BlueprintCompilation.model_validate(payload).story
    except (OSError, json.JSONDecodeError, ValidationError):
        return None


def _story_summary(story: object) -> list[str]:
    lines = [
        "## Story summary",
        "",
        f"**Title:** {story.title}",
        f"**Genre/profile:** `{story.genre}` / `{story.profile}`",
        "",
        story.premise,
        "",
        "### Opening boundary",
        "",
    ]
    truth_by_id = {truth.id: truth for truth in story.truths}
    for truth_id in story.opening_truth_ids:
        truth = truth_by_id[truth_id]
        lines.append(f"- **{truth.id}** — {truth.summary}")
    lines.extend(["", "### Cast", ""])
    for participant in story.participants:
        lines.append(f"- **{participant.id}** — {participant.role}")
    lines.extend(["", "### Locations and access", ""])
    for location in story.locations:
        access = "initially accessible" if location.initial_access else "initially locked"
        lines.append(f"- **{location.id}** ({access}) — {location.role}")
    lines.extend(
        ["", "### Causal timeline", "", "| Event | Window | Location | Outputs |", "| --- | --- | --- | --- |"]
    )
    for event in sorted(story.causal_events, key=lambda item: (item.earliest, item.id)):
        outputs = ", ".join(event.output_truths) or "—"
        lines.append(
            f"| `{event.id}` | {_clock(event.earliest)}–{_clock(event.latest)} | `{event.location_id}` | {outputs} |"
        )
    lines.extend(["", "### Evidence routes", ""])
    opportunities = {item.id: item for item in story.evidence_opportunities}
    participants = {item.id: item for item in story.participants}
    for route in story.realization_routes:
        lines.extend([f"#### `{route.id}` → `{route.revelation_id}`", ""])
        for opportunity_id in route.opportunity_ids:
            opportunity = opportunities[opportunity_id]
            holder = participants[opportunity.holder_id].id
            lines.append(
                f"- **{opportunity.id}** ({opportunity.kind}) — `{opportunity.location_id}`, "
                f"held by `{holder}`, supports `{opportunity.truth_id}`"
            )
        if route.failure_forward.alternative_route_ids:
            alternatives = ", ".join(f"`{item}`" for item in route.failure_forward.alternative_route_ids)
            lines.append(f"- Failure-forward alternatives: {alternatives}")
        lines.append("")
    lines.extend(["### Protected knowledge", ""])
    for protection in story.knowledge_protections:
        releases = ", ".join(f"`{item}`" for item in protection.release_after_revelation_ids)
        lines.append(f"- `{protection.truth_id}` releases after {releases}")
    lines.extend(["", "### End states", ""])
    for ending in story.end_states:
        lines.append(f"- **{ending.id}**")
        lines.append(f"  - Outcomes: {', '.join(f'`{item}`' for item in ending.required_outcome_ids)}")
        lines.append(f"  - Truths: {', '.join(f'`{item}`' for item in ending.required_truth_ids)}")
    lines.append("")
    return lines


def _runtime_projection_lines(projection: RuntimeProjectionAudit) -> list[str]:
    status = "COMPLETE" if projection.complete else "INCOMPLETE"
    coverages = (
        ("Participant placements", projection.participant_placements),
        ("Scene subjects", projection.scene_subjects),
        ("Evidence realization", projection.evidence_realization),
        ("Evidence custody", projection.evidence_custody),
        ("Group encounters", projection.group_encounters),
    )
    lines = ["", "## Phase 0 runtime projection", "", f"**Projection readiness:** {status}", ""]
    for label, coverage in coverages:
        lines.append(f"- {label}: **{coverage.fact_backed_count} / {coverage.declared_count}** fact-backed")
        if coverage.missing_ids:
            lines.append(f"  - Missing: {', '.join(f'`{identifier}`' for identifier in coverage.missing_ids)}")
    lines.extend(["", "### Unsupported opening suggestions", ""])
    lines.extend(f"- {action}" for action in projection.unsupported_suggested_actions)
    if not projection.unsupported_suggested_actions:
        lines.append("- None")
    lines.extend(
        [
            "",
            "This verifies the candidate's full fact-backed runtime projection without synthesizing targets or facts.",
            "",
        ]
    )
    return lines


def _clock(minutes: int) -> str:
    return f"{minutes // 60:02d}:{minutes % 60:02d}"
