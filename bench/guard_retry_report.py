"""Report guard-retry outcomes from saved bench turn records."""

from __future__ import annotations

import argparse
import json
import sys
from collections import defaultdict
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any

_EXCERPT_LENGTH = 200


def _empty_summary() -> dict[str, int | float | None]:
    return {
        "n_turns": 0,
        "n_first_pass_clean": 0,
        "n_retry_fired": 0,
        "n_rescued": 0,
        "n_failed_after_retry": 0,
        "rescue_rate": None,
        "n_second_reply_repeats_term": 0,
    }


def _summary(turns: Sequence[Mapping[str, Any]]) -> dict[str, int | float | None]:
    result = _empty_summary()
    result["n_turns"] = len(turns)
    result["n_first_pass_clean"] = sum(turn["outcome"] == "committed_clean" for turn in turns)
    result["n_retry_fired"] = sum(turn["retry_fired"] for turn in turns)
    result["n_rescued"] = sum(turn["outcome"] == "committed_after_retry" for turn in turns)
    result["n_failed_after_retry"] = sum(turn["outcome"] == "failed_after_retry" for turn in turns)
    result["n_second_reply_repeats_term"] = sum(turn["final_narration_repeats_term"] is True for turn in turns)
    retry_fired = result["n_retry_fired"]
    result["rescue_rate"] = result["n_rescued"] / retry_fired if retry_fired else None
    return result


def _guard_rejections(record: Mapping[str, Any]) -> list[Mapping[str, Any]]:
    rejections = record.get("guard_rejections", [])
    if not isinstance(rejections, list):
        return []
    return [rejection for rejection in rejections if isinstance(rejection, Mapping)]


def _quoted_term(message: object) -> str | None:
    if not isinstance(message, str):
        return None
    candidates: list[tuple[int, str]] = []
    for quote in ("'", '"'):
        first = message.find(quote)
        last = message.rfind(quote)
        if first >= 0 and last > first:
            candidates.append((first, message[first + 1 : last]))
    if not candidates:
        return None
    return min(candidates)[1]


def _narration_excerpt(narration: object) -> str:
    if not isinstance(narration, str):
        return ""
    excerpt = " ".join(narration.split())
    if len(excerpt) <= _EXCERPT_LENGTH:
        return excerpt
    return f"{excerpt[: _EXCERPT_LENGTH - 1].rstrip()}…"


def _turn_report(
    record: Mapping[str, Any],
    *,
    script: str,
    replicate: object,
    rejected: bool,
    ordinal: int,
) -> dict[str, Any]:
    rejections = _guard_rejections(record)
    retry_fired = bool(record.get("guard_retry_used")) or bool(rejections)
    first_rejection = rejections[0] if rejections else {}
    first_code = first_rejection.get("code")
    narration = record.get("narration")
    if rejected:
        outcome = (
            "failed_after_retry"
            if record.get("rejection_code") == "INVALID_PROPOSAL" and rejections
            else "failed_other"
        )
    else:
        outcome = "committed_after_retry" if retry_fired else "committed_clean"

    quoted_term = _quoted_term(first_rejection.get("message"))
    repeats_term: bool | str | None
    if rejected:
        repeats_term = None
    elif quoted_term is None:
        repeats_term = "unknown"
    else:
        repeats_term = quoted_term.casefold() in narration.casefold() if isinstance(narration, str) else False

    turn_number = record.get("turn_number", ordinal)
    return {
        "script": script,
        "replicate": replicate,
        "turn_number": turn_number,
        "typed_input": record.get("typed_input", record.get("player_input", "")),
        "outcome": outcome,
        "first_rejection_code": first_code,
        "final_narration_repeats_term": repeats_term,
        "narration_excerpt": _narration_excerpt(narration),
        "retry_fired": retry_fired,
    }


def _runs(records: Mapping[str, Any] | Sequence[Mapping[str, Any]]) -> list[Mapping[str, Any]]:
    values = records.get("runs") if isinstance(records, Mapping) else records
    if not isinstance(values, list):
        raise ValueError("input records must contain a 'runs' list")
    if not all(isinstance(run, Mapping) for run in values):
        raise ValueError("each run must be an object")
    return values


def compute_report(records: Mapping[str, Any] | Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    """Compute guard-retry telemetry without performing any I/O or network calls."""

    turns: list[dict[str, Any]] = []
    by_script: defaultdict[str, list[dict[str, Any]]] = defaultdict(list)
    for run_index, run in enumerate(_runs(records), start=1):
        script = str(run.get("script", ""))
        replicate = run.get("replicate", run_index)
        successful = run.get("turns", [])
        rejected = run.get("rejected_turns", [])
        if not isinstance(successful, list) or not isinstance(rejected, list):
            raise ValueError("each run's turns and rejected_turns values must be lists")
        entries: list[tuple[int, int, Mapping[str, Any], bool]] = []
        for ordinal, entry in enumerate(successful, start=1):
            if isinstance(entry, Mapping):
                entries.append((entry.get("turn_number", ordinal), ordinal, entry, False))
        offset = len(successful)
        for ordinal, entry in enumerate(rejected, start=1):
            if isinstance(entry, Mapping):
                entries.append((entry.get("turn_number", offset + ordinal), offset + ordinal, entry, True))
        entries.sort(key=lambda item: (item[0] if isinstance(item[0], int) else item[1], item[1]))
        for _, ordinal, entry, is_rejected in entries:
            turn = _turn_report(
                entry,
                script=script,
                replicate=replicate,
                rejected=is_rejected,
                ordinal=ordinal,
            )
            turns.append(turn)
            by_script[script].append(turn)

    per_script = {
        script: {"summary": _summary(script_turns), "turns": script_turns} for script, script_turns in by_script.items()
    }
    return {"summary": _summary(turns), "turns": turns, "per_script": per_script}


def _load_input(path: Path) -> Mapping[str, Any]:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ValueError(f"could not parse input JSON '{path}': {exc}") from exc
    if not isinstance(data, Mapping):
        raise ValueError(f"input JSON '{path}' must contain an object")
    return data


def _markdown_turn(turn: Mapping[str, Any]) -> str:
    values = (
        turn["replicate"],
        turn["typed_input"],
        turn["outcome"],
        turn["first_rejection_code"] or "",
        turn["final_narration_repeats_term"] if turn["final_narration_repeats_term"] is not None else "",
        turn["narration_excerpt"],
    )
    return "| " + " | ".join(str(value).replace("|", "\\|") for value in values) + " |"


def _write_markdown(path: Path, report: Mapping[str, Any]) -> None:
    lines = ["# Guard Retry Report", "", "## Overall", ""]
    overall = report["summary"]
    lines.extend(f"- {key}: {overall[key]}" for key in overall)
    for script, script_report in report["per_script"].items():
        lines.extend(
            [
                "",
                f"## Script: {script}",
                "",
                "| Replicate | Typed input | Outcome | First rejection code | Final narration repeats term "
                "| Narration excerpt |",
                "| --- | --- | --- | --- | --- | --- |",
            ]
        )
        lines.extend(_markdown_turn(turn) for turn in script_report["turns"])
        lines.append("")
        lines.extend(f"- {key}: {script_report['summary'][key]}" for key in script_report["summary"])
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Report guard retry benchmark metrics.")
    parser.add_argument("--in", dest="input_paths", action="append", required=True, type=Path)
    parser.add_argument("--out-json", required=True, type=Path)
    parser.add_argument("--out-md", required=True, type=Path)
    args = parser.parse_args(argv)

    try:
        runs: list[Mapping[str, Any]] = []
        for path in args.input_paths:
            runs.extend(_runs(_load_input(path)))
        report = compute_report(runs)
        args.out_json.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
        _write_markdown(args.out_md, report)
    except (OSError, ValueError) as exc:
        print(f"guard retry report: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
