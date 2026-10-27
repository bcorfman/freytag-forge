"""Probe Jev's scope-aware container-opening question on frozen commands."""

from __future__ import annotations

import argparse
import json
import os
import sys
import time
from pathlib import Path
from typing import Any

from scripts.ringer.environment_narration.under_question_probe import (
    _cases_bytes,
    _client_model,
    _redact,
    _sha256,
    _write_json,
)
from scripts.ringer.environment_narration.under_question_probe import (
    _status_stop_reason as _under_status_stop_reason,
)
from storygame.runtime.jev import JevClient
from storygame.runtime.jev_questions import opens_container, searches_underneath

REPO_DIR = Path(__file__).resolve().parents[3]
PROBE_DIR = Path(__file__).with_name("opens_probe")
CASES_PATH = PROBE_DIR / "cases.jsonl"
LOCK_PATH = PROBE_DIR / "cases.lock.json"
DEFAULT_SAMPLES = 2
DEFAULT_MAX_CALLS = 344
DEFAULT_MAX_USD = 0.01
COST_PER_MILLION_INPUT_TOKENS = 0.042
WILSON_Z = 1.6448536269514722
QUESTIONS = ("opens_container", "searches_underneath")
GROUPS = ("grid", "opening", "non-opening", "reported", "regression")

VERBS = ("Inspect", "Examine", "Search", "Check", "Look at")
CONTAINERS = ("cabinet", "chest", "locker", "toolbox")
UNDER_WORDS = ("under", "beneath", "underneath", "below")

OPENING_PHRASES = (
    ("Open the chest.", "chest"),
    ("Pull open the locker.", "locker"),
    ("Slide open the cabinet.", "cabinet"),
    ("Pull out the bottom drawer.", "bottom drawer"),
    ("Yank open the crate.", "crate"),
    ("Lift open the cooler.", "cooler"),
    ("Open the glove box.", "glove box"),
    ("Tug open the toolbox.", "toolbox"),
    ("Pull open the cabinet.", "cabinet"),
    ("Open up the chest.", "chest"),
    ("Open the top drawer.", "top drawer"),
    ("Pull out the file drawer.", "file drawer"),
    ("Look inside the locker.", "locker"),
    ("Feel inside the chest.", "chest"),
    ("Peek into the cooler.", "cooler"),
    ("Reach into the toolbox.", "toolbox"),
    ("Look in the cabinet.", "cabinet"),
    ("Search in the locker.", "locker"),
    ("Go through the chest.", "chest"),
    ("Rummage through the toolbox.", "toolbox"),
)

NON_OPENING_PHRASES = (
    ("Close the cabinet.", "cabinet"),
    ("Shut the chest.", "chest"),
    ("Push the bottom drawer shut.", "bottom drawer"),
    ("Slam the locker shut.", "locker"),
    ("Close the glove box.", "glove box"),
    ("Lock the locker.", "locker"),
    ("Touch the crate.", "crate"),
    ("Knock on the locker.", "locker"),
    ("Push the cabinet against the wall.", "cabinet"),
    ("Carry the toolbox.", "toolbox"),
    ("Lift the suitcase.", "suitcase"),
    ("Drag the chest to the door.", "chest"),
    ("Kick the cooler.", "cooler"),
    ("Tap the cabinet.", "cabinet"),
    ("Wipe the cabinet.", "cabinet"),
    ("Paint the chest.", "chest"),
    ("Read the label on the crate.", "crate"),
    ("Polish the toolbox.", "toolbox"),
    ("Look behind the cabinet.", "cabinet"),
    ("Check behind the locker.", "locker"),
    ("Look on top of the chest.", "chest"),
    ("Feel along the top of the crate.", "crate"),
)

REPORTED_PHRASES = (
    ("Study the chest.", "chest"),
    ("Glance at the crate.", "crate"),
    ("Admire the locker.", "locker"),
)

REGRESSION_PHRASES = (
    ("Open the drawer.", "drawer", True),
    ("Pull out the drawer.", "drawer", True),
    ("Look inside the drawer.", "drawer", True),
    ("Inspect the drawer.", "drawer", False),
    ("Examine the drawer.", "drawer", False),
    ("Search the drawer.", "drawer", False),
    ("Close the drawer.", "drawer", False),
)


def _grid_case(kind: str, index: int, command: str, container: str, expected: dict[str, bool]) -> dict[str, Any]:
    return {
        "id": f"g-{kind[0]}{index + 1:02d}",
        "command": command,
        "thing": container,
        "question": list(QUESTIONS),
        "expected": expected,
        "group": "grid",
        "kind": kind,
    }


def _grid_cases() -> list[dict[str, Any]]:
    cases: list[dict[str, Any]] = []
    for kind in ("bare", "under", "inside"):
        for verb_index, verb in enumerate(VERBS):
            for container_index, container in enumerate(CONTAINERS):
                under_word = UNDER_WORDS[(verb_index + container_index) % len(UNDER_WORDS)]
                if kind == "bare":
                    command = f"{verb} the {container}."
                elif kind == "under":
                    command = (
                        f"Look {under_word} the {container}."
                        if verb == "Look at"
                        else f"{verb} {under_word} the {container}."
                    )
                else:
                    command = (
                        f"Look inside the {container}." if verb == "Look at" else f"{verb} inside the {container}."
                    )
                expected = {
                    "opens_container": kind == "inside",
                    "searches_underneath": kind == "under",
                }
                cases.append(
                    _grid_case(kind, verb_index * len(CONTAINERS) + container_index, command, container, expected)
                )
    return cases


def _single_case(
    case_id: str, command: str, thing: str, expected: bool | None, group: str, kind: str
) -> dict[str, Any]:
    return {
        "id": case_id,
        "command": command,
        "thing": thing,
        "question": "opens_container",
        "expected": expected,
        "group": group,
        "kind": kind,
    }


def build_cases() -> list[dict[str, Any]]:
    cases = _grid_cases()
    cases.extend(
        _single_case(f"o{index:02d}", command, thing, True, "opening", "opening")
        for index, (command, thing) in enumerate(OPENING_PHRASES, start=1)
    )
    cases.extend(
        _single_case(f"n{index:02d}", command, thing, False, "non-opening", "non-opening")
        for index, (command, thing) in enumerate(NON_OPENING_PHRASES, start=1)
    )
    cases.extend(
        {
            **_single_case(f"x{index:02d}", command, thing, None, "reported", "reported"),
            "reported": True,
        }
        for index, (command, thing) in enumerate(REPORTED_PHRASES, start=1)
    )
    cases.extend(
        _single_case(f"r{index}", command, thing, expected, "regression", "regression")
        for index, (command, thing, expected) in enumerate(REGRESSION_PHRASES, start=1)
    )
    return cases


def _load_cases(path: Path | None = None) -> list[dict[str, Any]]:
    source = CASES_PATH if path is None else path
    try:
        lines = source.read_text(encoding="utf-8").splitlines()
    except FileNotFoundError as error:
        raise ValueError(f"cases.jsonl is missing: {source}") from error
    cases = []
    for line_number, line in enumerate(lines, start=1):
        if not line.strip():
            continue
        try:
            case = json.loads(line)
        except json.JSONDecodeError as error:
            raise ValueError(f"invalid case JSON on line {line_number}") from error
        if not isinstance(case, dict):
            raise ValueError(f"case on line {line_number} is not an object")
        cases.append(case)
    if not cases:
        raise ValueError(f"cases.jsonl has no cases: {source}")
    return cases


def _lock_matches(cases: list[dict[str, Any]]) -> bool:
    try:
        lock = json.loads(LOCK_PATH.read_text(encoding="utf-8"))
        data = CASES_PATH.read_bytes()
    except (OSError, json.JSONDecodeError):
        return False
    return lock == {"sha256": _sha256(data), "count": len(cases)}


def _recording_ask(client: object, records: list[dict[str, Any]]):
    def ask(state: object, questions: object) -> dict | None:
        raw_answer: dict | None = None
        try:
            raw_answer = client.ask(state, questions)
            return raw_answer
        finally:
            records.append(
                {
                    "raw_answer": raw_answer,
                    "jev_model": _client_model(client),
                    "status": getattr(client, "last_status", None),
                }
            )

    return ask


def _score(raw_answer: object, question: str) -> object:
    if not isinstance(raw_answer, dict):
        return None
    answer = raw_answer.get(question)
    return answer.get("noul") if isinstance(answer, dict) else None


def _status_stop_reason(client: object) -> str | None:
    for name in ("last_error_code", "error_code"):
        value = getattr(client, name, None)
        if isinstance(value, str) and "QUOTA" in value.upper():
            return "quota_code"
    return _under_status_stop_reason(client)


def _questions_for(case: dict[str, Any]) -> list[str]:
    question = case["question"]
    return list(question) if isinstance(question, list) else [question]


def _ask_question(question: str, ask: object, command: str, thing: str) -> bool | None:
    if question == "opens_container":
        return opens_container(ask, command, thing)
    if question == "searches_underneath":
        return searches_underneath(ask, command, thing)
    raise ValueError(f"unknown question: {question}")


def run_cases(
    cases: list[dict[str, Any]],
    *,
    samples: int,
    max_calls: int,
    out: Path,
    client: object,
) -> dict[str, Any]:
    if samples < 1:
        raise ValueError("--samples must be at least 1")
    if max_calls < 1:
        raise ValueError("--max-calls must be at least 1")
    calls = [
        (case, sample, question) for sample in range(samples) for case in cases for question in _questions_for(case)
    ]
    document: dict[str, Any] = {
        "schema": 1,
        "mode": "run",
        "calls_planned": len(calls),
        "rows": [],
        "stop_reason": None,
    }
    for call_index, (case, sample, question) in enumerate(calls[:max_calls], start=1):
        records: list[dict[str, Any]] = []
        started = time.perf_counter()
        returned = _ask_question(
            question,
            _recording_ask(client, records),
            case["command"],
            case["thing"],
        )
        latency_ms = (time.perf_counter() - started) * 1000
        record = records[-1] if records else {}
        raw_answer = record.get("raw_answer")
        score = _score(raw_answer, question)
        row = {
            "call_index": call_index,
            "case_id": case["id"],
            "command": case["command"],
            "thing": case["thing"],
            "question": question,
            "expected": case["expected"][question] if isinstance(case["expected"], dict) else case["expected"],
            "group": case["group"],
            "kind": case["kind"],
            "reported": case.get("reported", False),
            "sample": sample,
            "returned": returned,
            "answer": returned,
            "noul": score,
            "score": score,
            "raw_answer": raw_answer,
            "jev_model": record.get("jev_model"),
            "latency_ms": latency_ms,
        }
        document["rows"].append(row)
        stop_reason = _status_stop_reason(client)
        if stop_reason is None and len(document["rows"]) >= max_calls:
            stop_reason = "max_calls"
        if stop_reason is not None:
            document["stop_reason"] = stop_reason
        _write_json(out, document)
        if stop_reason is not None:
            break
    if document["stop_reason"] is None and len(document["rows"]) == len(calls):
        document["stop_reason"] = "completed"
        _write_json(out, document)
    return document


def _estimate_tokens(cases: list[dict[str, Any]], samples: int) -> float:
    calls = sum(len(_questions_for(case)) for case in cases) * samples
    chars = sum(
        len(json.dumps({"command": case["command"], "thing": case["thing"]}, ensure_ascii=False, separators=(",", ":")))
        * len(_questions_for(case))
        for case in cases
    )
    return chars * samples / 4 if calls else 0


def _ceiling(cases: list[dict[str, Any]], samples: int) -> float:
    return _estimate_tokens(cases, samples) / 1_000_000 * COST_PER_MILLION_INPUT_TOKENS * 1.5


def _print_dry_run(cases: list[dict[str, Any]], samples: int) -> None:
    if samples < 1:
        raise ValueError("--samples must be at least 1")
    print(f"case count: {len(cases)}")
    print(f"planned requests: {sum(len(_questions_for(case)) for case in cases) * samples}")
    print(f"token estimate: {_estimate_tokens(cases, samples):.2f}")
    print(f"USD ceiling: ${_ceiling(cases, samples):.6f}")


def _display(value: object) -> str:
    if value is None:
        return "null"
    if isinstance(value, bool):
        return str(value).lower()
    return str(value)


def _wilson_upper(successes: int, trials: int) -> float | None:
    if trials < 1:
        return None
    proportion = successes / trials
    adjustment = WILSON_Z * WILSON_Z / trials
    numerator = (
        proportion
        + adjustment / 2
        + WILSON_Z * (proportion * (1 - proportion) / trials + adjustment * adjustment / 4) ** 0.5
    )
    return numerator / (1 + adjustment)


def _rows_for(
    rows: list[dict[str, Any]],
    cases: list[dict[str, Any]],
    group: str,
    kind: str | None = None,
    question: str | None = None,
):
    ids = {case["id"] for case in cases if case["group"] == group and (kind is None or case["kind"] == kind)}
    return [row for row in rows if row.get("case_id") in ids and (question is None or row.get("question") == question)]


def _miss_lines(rows: list[dict[str, Any]], include_verb: bool = False) -> list[str]:
    lines = []
    for row in rows:
        label = f"{row.get('case_id')} sample {row.get('sample')}"
        if include_verb:
            label += f" verb {row.get('command', '').split(' ', 1)[0]}"
        lines.append(f"- {label}: score {_display(row.get('score', row.get('noul')))}")
    return lines


def _report_text(rows: list[dict[str, Any]], rows_sha256: str) -> tuple[str, bool]:
    cases = build_cases()
    case_by_id = {case["id"]: case for case in cases}
    grid_bare_open = _rows_for(rows, cases, "grid", "bare", "opens_container")
    grid_under_open = _rows_for(rows, cases, "grid", "under", "opens_container")
    grid_inside_open = _rows_for(rows, cases, "grid", "inside", "opens_container")
    grid_bare_under = _rows_for(rows, cases, "grid", "bare", "searches_underneath")
    grid_under_under = _rows_for(rows, cases, "grid", "under", "searches_underneath")
    grid_inside_under = _rows_for(rows, cases, "grid", "inside", "searches_underneath")
    opening_rows = _rows_for(rows, cases, "opening", question="opens_container")
    non_opening_rows = _rows_for(rows, cases, "non-opening", question="opens_container")
    regression_rows = _rows_for(rows, cases, "regression", question="opens_container")
    reported_rows = _rows_for(rows, cases, "reported", question="opens_container")

    def true_count(items: list[dict[str, Any]]) -> int:
        return sum(row.get("returned") is True for row in items)

    def misses(items: list[dict[str, Any]], expected: bool) -> list[dict[str, Any]]:
        return [row for row in items if row.get("returned") is not expected]

    j1_rows = grid_bare_open + grid_under_open
    j1_true = true_count(j1_rows)
    j1 = len(j1_rows) == 80 and j1_true == 0
    j1_bound = _wilson_upper(j1_true, len(j1_rows))
    j1b = len(grid_inside_open) == 40 and true_count(grid_inside_open) >= 36
    j2_bare = len(grid_bare_under) == 40 and true_count(grid_bare_under) <= 4
    j2_under = len(grid_under_under) == 40 and true_count(grid_under_under) >= 36
    j2_inside = len(grid_inside_under) == 40 and true_count(grid_inside_under) <= 4
    j2 = j2_bare and j2_under and j2_inside
    j3 = len(opening_rows) == 40 and true_count(opening_rows) >= 36
    j4 = len(non_opening_rows) == 44 and true_count(non_opening_rows) == 0
    regression_true = [row for row in regression_rows if case_by_id[row["case_id"]]["expected"] is True]
    regression_false = [row for row in regression_rows if case_by_id[row["case_id"]]["expected"] is False]
    r = (
        len(regression_true) == 6
        and len(regression_false) == 8
        and all(row.get("returned") is True for row in regression_true)
        and all(row.get("returned") is False for row in regression_false)
    )
    null_answers = sum(row.get("returned") is None for row in rows)

    lines = [
        "# Opens-container probe report",
        "",
        f"Rows sha256: {rows_sha256}",
        f"Rows rendered: {len(rows)}",
        f"null answers: {null_answers}",
        "",
        "## Per-case results",
        "",
        "| Case | Command | Question | Expected | Sample answers and scores |",
        "| --- | --- | --- | ---: | --- |",
    ]
    for case in cases:
        case_rows = sorted(
            (row for row in rows if row.get("case_id") == case["id"]),
            key=lambda row: (row.get("question", ""), row.get("sample", 0)),
        )
        samples_text = (
            ", ".join(
                f"{row.get('question')} sample {row.get('sample')}: "
                f"{_display(row.get('returned'))} ({_display(row.get('score', row.get('noul')))})"
                for row in case_rows
            )
            or "—"
        )
        lines.append(
            f"| {case['id']} | {case['command']} | {_display(case['question'])} | "
            f"{_display(case['expected'])} | {samples_text} |"
        )

    j1_misses = [row for row in j1_rows if row.get("returned") is True]
    j1b_misses = misses(grid_inside_open, True)
    j2_misses = misses(grid_bare_under, False) + misses(grid_under_under, True) + misses(grid_inside_under, False)
    j3_misses = misses(opening_rows, True)
    j4_misses = [row for row in non_opening_rows if row.get("returned") is True]
    r_misses = [row for row in regression_rows if row.get("returned") is not case_by_id[row["case_id"]]["expected"]]
    bound_text = "n/a" if j1_bound is None else f"{j1_bound * 100:.2f}%"
    lines.extend(
        [
            "",
            "## Gate P",
            "",
            f"- J1: {'PASS' if j1 else 'FAIL'} — true opens_container answers among bare and under grid samples: "
            f"{j1_true} of {len(j1_rows)}; one-sided 95% Wilson upper bound: {bound_text}",
            f"- J1b: {'PASS' if j1b else 'FAIL'} — true opens_container answers among inside grid samples: "
            f"{true_count(grid_inside_open)} of {len(grid_inside_open)} (required at least 36)",
            f"- J2: {'PASS' if j2 else 'FAIL'} — bare false: "
            f"{len(grid_bare_under) - true_count(grid_bare_under)} of {len(grid_bare_under)}; "
            f"under true: {true_count(grid_under_under)} of {len(grid_under_under)}; "
            f"inside false: {len(grid_inside_under) - true_count(grid_inside_under)} of {len(grid_inside_under)}",
            f"- J3: {'PASS' if j3 else 'FAIL'} — opening positives true: "
            f"{true_count(opening_rows)} of {len(opening_rows)} (required at least 36)",
            f"- J4: {'PASS' if j4 else 'FAIL'} — non-opening negatives true: "
            f"{true_count(non_opening_rows)} of {len(non_opening_rows)}",
            f"- R: {'PASS' if r else 'FAIL'} — regression labels correct: "
            f"{len(regression_rows) - len(r_misses)} of {len(regression_rows)}",
            "",
            "### J1 true answers",
            "",
        ]
    )
    lines.extend(_miss_lines(j1_misses) or ["- none"])
    lines.extend(["", "### J1b misses by case id and verb", ""])
    lines.extend(_miss_lines(j1b_misses, include_verb=True) or ["- none"])
    lines.extend(["", "### J2 misses", ""])
    lines.extend(_miss_lines(j2_misses) or ["- none"])
    lines.extend(["", "### J3 misses", ""])
    lines.extend(_miss_lines(j3_misses) or ["- none"])
    lines.extend(["", "### J4 true answers", ""])
    lines.extend(_miss_lines(j4_misses) or ["- none"])
    lines.extend(["", "### Regression misses", ""])
    lines.extend(_miss_lines(r_misses) or ["- none"])
    lines.extend(["", "## Reported phrases (no gate)", ""])
    for row in reported_rows:
        lines.append(
            f"- {row.get('case_id')} sample {row.get('sample')}: "
            f"{_display(row.get('returned'))} (score {_display(row.get('score', row.get('noul')))})"
        )
    passed = j1 and j1b and j2 and j3 and j4 and r
    lines.extend(["", f"probe gate: {'PASS' if passed else 'FAIL'}", ""])
    return "\n".join(lines), passed


def report_rows(rows_path: Path, out: Path) -> int:
    document = json.loads(rows_path.read_text(encoding="utf-8"))
    rows = document.get("rows")
    if not isinstance(rows, list):
        raise ValueError("rows file has no rows list")
    report, passed = _report_text(rows, _sha256(rows_path.read_bytes()))
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(_redact(report), encoding="utf-8")
    return 0 if passed else 1


def _error(message: str) -> int:
    print(_redact(f"opens-container probe: {message}"), file=sys.stderr)
    return 2


def _check_corpus() -> int:
    cases = _load_cases()
    literal_matches = cases == build_cases()
    lock_matches = _lock_matches(cases)
    print(f"case count: {len(cases)}")
    print(f"corpus literal: {'PASS' if literal_matches else 'FAIL'}")
    print(f"corpus lock: {'PASS' if lock_matches else 'FAIL'}")
    return 0 if literal_matches and lock_matches else 1


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    modes = parser.add_mutually_exclusive_group(required=True)
    modes.add_argument("--build-cases", action="store_true")
    modes.add_argument("--check-corpus", action="store_true")
    modes.add_argument("--dry-run", action="store_true")
    modes.add_argument("--run", action="store_true")
    modes.add_argument("--report", action="store_true")
    parser.add_argument("--samples", type=int, default=DEFAULT_SAMPLES)
    parser.add_argument("--confirm", action="store_true")
    parser.add_argument("--max-calls", type=int)
    parser.add_argument("--max-usd", type=float, default=DEFAULT_MAX_USD)
    parser.add_argument("--rows", type=Path)
    parser.add_argument("--out", type=Path)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    try:
        if args.build_cases:
            cases = build_cases()
            data = _cases_bytes(cases)
            CASES_PATH.parent.mkdir(parents=True, exist_ok=True)
            CASES_PATH.write_bytes(data)
            _write_json(LOCK_PATH, {"sha256": _sha256(data), "count": len(cases)})
            print(f"built {len(cases)} cases at {_redact(str(CASES_PATH))}")
            return 0
        if args.check_corpus:
            return _check_corpus()
        if args.report:
            if args.rows is None or args.out is None:
                return _error("--report requires --rows and --out")
            return report_rows(args.rows, args.out)
        cases = _load_cases()
        if args.dry_run:
            _print_dry_run(cases, args.samples)
            return 0
        if not args.confirm:
            return _error("run mode requires --confirm")
        if args.out is None:
            return _error("run mode requires --out")
        max_calls = args.max_calls if args.max_calls is not None else DEFAULT_MAX_CALLS
        if max_calls < 1:
            return _error("--max-calls must be at least 1")
        ceiling = _ceiling(cases, args.samples)
        if ceiling > args.max_usd:
            return _error(f"USD ceiling ${ceiling:.6f} exceeds --max-usd ${args.max_usd:.6f}")
        if not _lock_matches(cases):
            return _error("run mode requires a matching lock")
        if not os.environ.get("CLOUDFLARE_WORKER_URL", "").strip():
            return _error("run mode requires CLOUDFLARE_WORKER_URL")
        if not os.environ.get("CLOUDFLARE_WORKER_TOKEN", "").strip():
            return _error("run mode requires CLOUDFLARE_WORKER_TOKEN")
        client = JevClient.from_environment()
        document = run_cases(cases, samples=args.samples, max_calls=max_calls, out=args.out, client=client)
        print(f"{len(document['rows'])} rows written to {_redact(str(args.out))}")
        if document.get("stop_reason"):
            print(f"stop reason: {_redact(str(document['stop_reason']))}")
        return 0
    except (OSError, ValueError, TypeError, json.JSONDecodeError) as error:
        return _error(str(error))


if __name__ == "__main__":
    raise SystemExit(main())
