"""Summarize refusal-measurement records and enforce billed-run integrity gates."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any


class CheckFailure(RuntimeError):
    """A refusal-check input or validity gate failed."""


@dataclass(frozen=True)
class ArmSummary:
    arm: str
    turns: int = 0
    refused: int = 0
    extra_calls: int = 0
    fallbacks: int = 0
    narrator_called: int = 0
    narrator_not_called: int = 0


def _issues(turn: dict[str, Any]) -> list[str]:
    return [str(issue) for issue in (turn.get("capture_issues") or []) + (turn.get("item_facts_issues") or [])]


def _is_refused(turn: dict[str, Any]) -> bool:
    if isinstance(turn.get("engine_refusal"), str) and turn["engine_refusal"].strip():
        return True
    issues = _issues(turn)
    if any("refused place" in issue for issue in issues):
        return True
    steps = turn.get("fixed_refusal_steps")
    return bool(steps) and turn.get("narrator_called") is False


def _extra_calls(turn: dict[str, Any]) -> int:
    value = turn.get("refusal_extra_calls", 0) or 0
    return value if isinstance(value, int) else 0


def _turns(records: dict[str, Any]) -> list[dict[str, Any]]:
    runs = records.get("runs")
    if not isinstance(runs, list) or not runs:
        raise CheckFailure("records have no runs")
    turns: list[dict[str, Any]] = []
    for run in runs:
        if not isinstance(run, dict):
            raise CheckFailure("records contain a non-object run")
        run_turns = run.get("turns", [])
        if not isinstance(run_turns, list):
            raise CheckFailure("records contain a run with non-list turns")
        for turn in run_turns:
            if not isinstance(turn, dict):
                raise CheckFailure("records contain a non-object turn")
            turns.append(turn)
    return turns


def summarize_records(
    records: dict[str, Any],
    arm: str = "",
    script: str = "",
    *,
    emit: bool = True,
) -> ArmSummary:
    """Summarize one all-turn-records document using all known refusal markers."""

    summary = ArmSummary(arm=arm)
    for turn in _turns(records):
        refused = _is_refused(turn)
        issues = _issues(turn)
        extra_calls = _extra_calls(turn)
        narrator_called = turn.get("narrator_called") is True
        narrator_not_called = turn.get("narrator_called") is False
        summary = ArmSummary(
            arm=arm,
            turns=summary.turns + 1,
            refused=summary.refused + int(refused),
            extra_calls=summary.extra_calls + extra_calls,
            fallbacks=summary.fallbacks + int(any("re-narration failed" in issue for issue in issues)),
            narrator_called=summary.narrator_called + int(narrator_called),
            narrator_not_called=summary.narrator_not_called + int(narrator_not_called),
        )
        if emit:
            print(
                f"== {arm} {script} refused={refused} extra_calls={turn.get('refusal_extra_calls')} "
                f"narrator_called={turn.get('narrator_called')}"
            )
            print(f"  notes: {[issue for issue in issues if 'refusal' in issue]}")
            print(f"  narr: {(turn.get('narration') or '').replace(chr(10), ' ')}")
    return summary


def summarize_file(path: Path, arm: str, script: str, *, emit: bool = True) -> ArmSummary:
    """Load and summarize one required records file."""

    if not path.is_file() or path.stat().st_size == 0:
        raise CheckFailure(f"no records or empty records: {path}")
    try:
        records = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise CheckFailure(f"cannot read records {path}: {exc}") from exc
    if not isinstance(records, dict):
        raise CheckFailure(f"records are not an object: {path}")
    return summarize_records(records, arm, script, emit=emit)


def combine_summaries(arm: str, summaries: list[ArmSummary]) -> ArmSummary:
    """Combine script-level summaries into the required per-arm totals."""

    return ArmSummary(
        arm=arm,
        turns=sum(summary.turns for summary in summaries),
        refused=sum(summary.refused for summary in summaries),
        extra_calls=sum(summary.extra_calls for summary in summaries),
        fallbacks=sum(summary.fallbacks for summary in summaries),
        narrator_called=sum(summary.narrator_called for summary in summaries),
        narrator_not_called=sum(summary.narrator_not_called for summary in summaries),
    )


def validate_gates(
    summaries: list[ArmSummary],
    *,
    expected_turns: int | None = None,
    expected_refused_min: int = 0,
) -> None:
    """Raise a clear failure for turn-count or treatment-activation mismatches."""

    for summary in summaries:
        if expected_turns is not None and summary.turns != expected_turns:
            raise CheckFailure(f"expected {expected_turns} turns for arm {summary.arm}, found {summary.turns}")
        if summary.refused < expected_refused_min:
            raise CheckFailure(
                f"treatment inactive for arm {summary.arm}: expected at least "
                f"{expected_refused_min} refusals, found {summary.refused}"
            )


def _integer_setting(name: str, value: str | None, *, default: int | None = None) -> int | None:
    if value is None or value == "":
        return default
    try:
        parsed = int(value)
    except ValueError as exc:
        raise CheckFailure(f"invalid {name}={value!r}; expected a non-negative integer") from exc
    if parsed < 0:
        raise CheckFailure(f"invalid {name}={value!r}; expected a non-negative integer")
    return parsed


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def write_provenance(out: Path, repo: Path, arms: list[str]) -> Path:
    """Write the source revision and every scheduled arm's variation identity."""

    try:
        git_sha = subprocess.check_output(
            ["git", "-C", str(repo), "rev-parse", "HEAD"], text=True, stderr=subprocess.STDOUT
        ).strip()
    except (OSError, subprocess.CalledProcessError) as exc:
        raise CheckFailure(f"cannot determine git HEAD for {repo}: {exc}") from exc

    variations = []
    for arm in arms:
        path = repo / "bench" / "variations" / f"astra-p4-refusal-{arm}.json"
        if not path.is_file() or path.stat().st_size == 0:
            raise CheckFailure(f"variation missing or empty for arm {arm}: {path}")
        variations.append(
            {
                "arm": arm,
                "path": str(path.relative_to(repo)),
                "sha256": _sha256(path),
            }
        )

    provenance = {"git_sha": git_sha, "variations": variations}
    destination = out / "provenance.json"
    try:
        out.mkdir(parents=True, exist_ok=True)
        destination.write_text(json.dumps(provenance, indent=2) + "\n", encoding="utf-8")
    except OSError as exc:
        raise CheckFailure(f"cannot write provenance {destination}: {exc}") from exc
    print(f"PROVENANCE {json.dumps(provenance, sort_keys=True)}")
    return destination


def check_dirty(repo: Path) -> None:
    """Reject source changes in the measured runtime or bench harness."""

    try:
        dirty = subprocess.check_output(
            [
                "git",
                "-C",
                str(repo),
                "status",
                "--porcelain",
                "--untracked-files=all",
                "--",
                "storygame/",
                "bench/",
            ],
            text=True,
            stderr=subprocess.STDOUT,
        ).strip()
    except (OSError, subprocess.CalledProcessError) as exc:
        raise CheckFailure(f"cannot inspect git status for {repo}: {exc}") from exc
    if dirty and os.environ.get("ALLOW_DIRTY") != "1":
        raise CheckFailure(f"working tree dirty under storygame/ or bench/:\n{dirty}")
    if dirty:
        print(f"DIRTY allowed by ALLOW_DIRTY=1:\n{dirty}")


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("out", type=Path)
    parser.add_argument("arms")
    parser.add_argument("scripts")
    parser.add_argument("--repo", type=Path, default=Path.cwd())
    parser.add_argument("--expect-turns")
    parser.add_argument("--expect-refused-min")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    try:
        expected_turns = _integer_setting("EXPECT_TURNS", args.expect_turns or os.environ.get("EXPECT_TURNS"))
        expected_refused_min = _integer_setting(
            "EXPECT_REFUSED_MIN",
            args.expect_refused_min or os.environ.get("EXPECT_REFUSED_MIN"),
            default=0,
        )
        arms = args.arms.split()
        scripts = args.scripts.split()
        if not arms:
            raise CheckFailure("no arms were scheduled")
        if not scripts:
            raise CheckFailure("no scripts were scheduled")

        totals = []
        for arm in arms:
            script_summaries = []
            for script in scripts:
                records_path = args.out / arm / script / "all-turn-records.json"
                summary = summarize_file(records_path, arm, script)
                summary_json = args.out / arm / script / "summary.json"
                if summary_json.is_file() and summary_json.stat().st_size:
                    fact_tracking = json.loads(summary_json.read_text(encoding="utf-8")).get("fact_tracking") or {}
                    print(f"  judge[{arm} {script}]: {json.dumps(fact_tracking)[:400]}")
                script_summaries.append(summary)
            total = combine_summaries(arm, script_summaries)
            totals.append(total)
            print(
                f"SUMMARY arm={arm} turns={total.turns} refused={total.refused} "
                f"extra_calls={total.extra_calls} fallbacks={total.fallbacks} "
                f"narrator_called={total.narrator_called} "
                f"narrator_not_called={total.narrator_not_called}"
            )

        write_provenance(args.out, args.repo, arms)
        check_dirty(args.repo)
        validate_gates(
            totals,
            expected_turns=expected_turns,
            expected_refused_min=expected_refused_min or 0,
        )
    except (CheckFailure, OSError, json.JSONDecodeError) as exc:
        print(f"FAIL {exc}")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
