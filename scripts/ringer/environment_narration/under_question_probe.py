"""Probe Jev's scope-aware underneath-search question on frozen player commands."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
import time
from pathlib import Path
from typing import Any

from storygame.runtime.jev import JevClient
from storygame.runtime.jev_questions import searches_underneath

REPO_DIR = Path(__file__).resolve().parents[3]
PROBE_DIR = Path(__file__).with_name("under_probe")
CASES_PATH = PROBE_DIR / "cases.jsonl"
LOCK_PATH = PROBE_DIR / "cases.lock.json"
DEFAULT_SAMPLES = 2
DEFAULT_MAX_CALLS = 98
DEFAULT_MAX_USD = 0.01
COST_PER_MILLION_INPUT_TOKENS = 0.042
WILSON_Z = 1.6448536269514722

FROZEN_CASES = [
    {"id": "u-p01", "command": "Feel under the drawer.", "thing": "drawer", "expected": True},
    {"id": "u-p02", "command": "Search beneath the drawer.", "thing": "drawer", "expected": True},
    {"id": "u-p03", "command": "Look under the drawer.", "thing": "drawer", "expected": True},
    {"id": "u-p04", "command": "Check below the drawer.", "thing": "drawer", "expected": True},
    {"id": "u-p05", "command": "Run my hand under the drawer.", "thing": "drawer", "expected": True},
    {"id": "u-p06", "command": "Reach beneath the drawer.", "thing": "drawer", "expected": True},
    {"id": "u-p07", "command": "Feel under the passenger seat.", "thing": "passenger seat", "expected": True},
    {"id": "u-p08", "command": "Look under the passenger seat.", "thing": "passenger seat", "expected": True},
    {"id": "u-p09", "command": "Search beneath the passenger seat.", "thing": "passenger seat", "expected": True},
    {"id": "u-p10", "command": "Check under the driver's seat.", "thing": "driver's seat", "expected": True},
    {"id": "u-p11", "command": "Feel under the desk.", "thing": "desk", "expected": True},
    {"id": "u-p12", "command": "Search under the bed.", "thing": "bed", "expected": True},
    {"id": "u-p13", "command": "Look beneath the tray.", "thing": "telescope tray", "expected": True},
    {"id": "u-p14", "command": "Feel under the telescope tray.", "thing": "telescope tray", "expected": True},
    {"id": "u-p15", "command": "Check under the bench.", "thing": "skiff bench", "expected": True},
    {"id": "u-p16", "command": "Reach under the locker.", "thing": "locker", "expected": True},
    {"id": "u-p17", "command": "Search below the workbench.", "thing": "workbench", "expected": True},
    {"id": "u-p18", "command": "Look under the crate.", "thing": "crate", "expected": True},
    {"id": "u-p19", "command": "Feel beneath the table.", "thing": "table", "expected": True},
    {"id": "u-p20", "command": "Slide my hand under the shelf.", "thing": "shelf", "expected": True},
    {"id": "u-n01", "command": "Inspect the drawer.", "thing": "drawer", "expected": False},
    {"id": "u-n02", "command": "Open the drawer.", "thing": "drawer", "expected": False},
    {"id": "u-n03", "command": "Pull out the drawer.", "thing": "drawer", "expected": False},
    {"id": "u-n04", "command": "Search the drawer.", "thing": "drawer", "expected": False},
    {"id": "u-n05", "command": "Feel inside the drawer.", "thing": "drawer", "expected": False},
    {"id": "u-n06", "command": "Look inside the drawer.", "thing": "drawer", "expected": False},
    {"id": "u-n07", "command": "Close the drawer.", "thing": "drawer", "expected": False},
    {"id": "u-n08", "command": "Look behind the drawer.", "thing": "drawer", "expected": False},
    {"id": "u-n09", "command": "Check the top of the drawer.", "thing": "drawer", "expected": False},
    {"id": "u-n10", "command": "Take the pens from the drawer.", "thing": "drawer", "expected": False},
    {"id": "u-n11", "command": "Inspect the passenger seat.", "thing": "passenger seat", "expected": False},
    {"id": "u-n12", "command": "Sit on the passenger seat.", "thing": "passenger seat", "expected": False},
    {"id": "u-n13", "command": "Search the passenger seat.", "thing": "passenger seat", "expected": False},
    {"id": "u-n14", "command": "Put my laptop on the passenger seat.", "thing": "passenger seat", "expected": False},
    {"id": "u-n15", "command": "Look at the driver's seat.", "thing": "driver's seat", "expected": False},
    {"id": "u-n16", "command": "Inspect the telescope tray.", "thing": "telescope tray", "expected": False},
    {"id": "u-n17", "command": "Look in the locker.", "thing": "locker", "expected": False},
    {"id": "u-n18", "command": "Open the crate.", "thing": "crate", "expected": False},
    {"id": "u-n19", "command": "Examine the bench.", "thing": "skiff bench", "expected": False},
    {"id": "u-n20", "command": "Search the table.", "thing": "table", "expected": False},
    {"id": "u-n21", "command": "Clear the desk.", "thing": "desk", "expected": False},
    {"id": "u-n22", "command": "Check on top of the shelf.", "thing": "shelf", "expected": False},
    {"id": "u-n23", "command": "Look behind the bed.", "thing": "bed", "expected": False},
    {"id": "u-n24", "command": "Search the workbench.", "thing": "workbench", "expected": False},
    {"id": "u-n25", "command": "Wipe the table.", "thing": "table", "expected": False},
    {"id": "u-n26", "command": "Push the chair under the desk.", "thing": "chair", "expected": False, "hard": True},
    {"id": "u-n27", "command": "Slide the tray under the telescope.", "thing": "tray", "expected": False, "hard": True},
    {"id": "u-n28", "command": "Lift the crate.", "thing": "crate", "expected": False},
    {"id": "u-n29", "command": "Read the label on the locker.", "thing": "locker", "expected": False},
]


def _credential_values() -> tuple[str, ...]:
    names = (
        "CLOUDFLARE_WORKER_TOKEN",
        "CLOUDFLARE_AI_TOKEN",
        "CLOUDFLARE_ACCOUNT_ID",
        "OPENAI_API_KEY",
        "RAILWAY_TOKEN",
        "RAILWAY_PROJECT_ID",
        "FREYTAG_TEST_CLOCK_TOKEN",
    )
    values = [os.environ.get(name, "").strip() for name in names]
    return tuple(sorted({value for value in values if value}, key=len, reverse=True))


def _redact(value: str) -> str:
    for secret in _credential_values():
        value = value.replace(secret, "[REDACTED]")
    return value


def _write_json(path: Path, document: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    text = json.dumps(document, ensure_ascii=False, indent=2) + "\n"
    path.write_text(_redact(text), encoding="utf-8")


def _sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _cases_bytes(cases: list[dict[str, Any]] | tuple[dict[str, Any], ...]) -> bytes:
    return "".join(json.dumps(case, ensure_ascii=False, separators=(",", ":")) + "\n" for case in cases).encode("utf-8")


def build_cases() -> list[dict[str, Any]]:
    """Return the preregistered cases from the literal frozen list."""
    return [dict(case) for case in FROZEN_CASES]


def _write_cases(cases: list[dict[str, Any]]) -> None:
    data = _cases_bytes(cases)
    CASES_PATH.parent.mkdir(parents=True, exist_ok=True)
    CASES_PATH.write_bytes(data)
    _write_json(LOCK_PATH, {"sha256": _sha256(data), "count": len(cases)})


def _load_cases(path: Path | None = None) -> list[dict[str, Any]]:
    source = CASES_PATH if path is None else path
    try:
        lines = source.read_text(encoding="utf-8").splitlines()
    except FileNotFoundError as error:
        raise ValueError(f"cases.jsonl is missing: {source}") from error
    cases: list[dict[str, Any]] = []
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


def _lock_matches(cases: list[dict[str, Any]], cases_path: Path | None = None, lock_path: Path | None = None) -> bool:
    source = CASES_PATH if cases_path is None else cases_path
    lock_source = LOCK_PATH if lock_path is None else lock_path
    try:
        lock = json.loads(lock_source.read_text(encoding="utf-8"))
        data = source.read_bytes()
    except (OSError, json.JSONDecodeError):
        return False
    return lock == {"sha256": _sha256(data), "count": len(cases)}


def recording_ask(client: object, records: list[dict[str, Any]]):
    """Wrap a Jev client ask while preserving its raw answer and response metadata."""

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


def _client_model(client: object) -> str | None:
    for name in ("last_model", "model", "model_header"):
        value = getattr(client, name, None)
        if isinstance(value, str) and value:
            return value
    return None


def _score(raw_answer: object) -> object:
    if not isinstance(raw_answer, dict):
        return None
    answer = raw_answer.get("searches_underneath")
    return answer.get("noul") if isinstance(answer, dict) else None


def _status_stop_reason(client: object) -> str | None:
    status = getattr(client, "last_status", None)
    if not isinstance(status, int):
        return None
    if status == 429:
        return "http_429"
    if status in {401, 403}:
        return "auth_failure"
    if status >= 500:
        return f"http_{status}"
    if status >= 400:
        return f"http_{status}"
    return None


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
    calls = [(case, sample) for sample in range(samples) for case in cases]
    document: dict[str, Any] = {
        "schema": 1,
        "mode": "run",
        "calls_planned": len(calls),
        "rows": [],
        "stop_reason": None,
    }
    for call_index, (case, sample) in enumerate(calls[:max_calls], start=1):
        records: list[dict[str, Any]] = []
        started = time.perf_counter()
        returned = searches_underneath(
            recording_ask(client, records),
            case["command"],
            case["thing"],
        )
        latency_ms = (time.perf_counter() - started) * 1000
        record = records[-1] if records else {}
        raw_answer = record.get("raw_answer")
        row = {
            "call_index": call_index,
            "case_id": case["id"],
            "command": case["command"],
            "thing": case["thing"],
            "expected": case["expected"],
            "sample": sample,
            "returned": returned,
            "answer": returned,
            "noul": _score(raw_answer),
            "score": _score(raw_answer),
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
    chars = sum(
        len(json.dumps({"command": case["command"], "thing": case["thing"]}, ensure_ascii=False, separators=(",", ":")))
        for case in cases
    )
    return chars * samples / 4


def _ceiling(cases: list[dict[str, Any]], samples: int) -> float:
    return _estimate_tokens(cases, samples) / 1_000_000 * COST_PER_MILLION_INPUT_TOKENS * 1.5


def _print_dry_run(cases: list[dict[str, Any]], samples: int) -> None:
    if samples < 1:
        raise ValueError("--samples must be at least 1")
    print(f"case count: {len(cases)}")
    print(f"planned requests: {len(cases) * samples}")
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


def _report_text(rows: list[dict[str, Any]], rows_sha256: str) -> tuple[str, bool]:
    frozen = {case["id"]: case for case in FROZEN_CASES}
    by_case: dict[str, list[dict[str, Any]]] = {}
    for row in rows:
        by_case.setdefault(str(row.get("case_id")), []).append(row)
    negative_rows = [row for row in rows if frozen.get(row.get("case_id"), {}).get("expected") is False]
    positive_rows = [row for row in rows if frozen.get(row.get("case_id"), {}).get("expected") is True]
    negative_true = sum(row.get("returned") is True for row in negative_rows)
    positive_true = sum(row.get("returned") is True for row in positive_rows)
    null_answers = sum(row.get("returned") is None for row in rows)
    j1 = len(negative_rows) == 58 and negative_true == 0
    j2 = len(positive_rows) == 40 and positive_true >= 36
    bound = _wilson_upper(negative_true, len(negative_rows))
    bound_text = "n/a" if bound is None else f"{bound * 100:.2f}%"

    lines = [
        "# Under question probe report",
        "",
        f"Rows sha256: {rows_sha256}",
        f"Rows rendered: {len(rows)}",
        f"null answers: {null_answers}",
        "",
        "## Per-case results",
        "",
        "| Case | Command | Expected | Sample answers and scores |",
        "| --- | --- | ---: | --- |",
    ]
    for case in FROZEN_CASES:
        case_rows = sorted(by_case.get(case["id"], []), key=lambda row: row.get("sample", 0))
        samples_text = (
            ", ".join(
                f"{row.get('sample')}: {_display(row.get('returned'))} ({_display(row.get('noul'))})"
                for row in case_rows
            )
            or "—"
        )
        lines.append(f"| {case['id']} | {case['command']} | {_display(case['expected'])} | {samples_text} |")

    missed_positive = [row for row in positive_rows if row.get("returned") is not True]
    true_negative = [row for row in negative_rows if row.get("returned") is True]
    lines.extend(
        [
            "",
            "## Gate P",
            "",
            f"- J1: {'PASS' if j1 else 'FAIL'} — true answers among negative samples: {negative_true} of 58; "
            f"one-sided 95% Wilson upper bound: {bound_text}",
            f"- J2: {'PASS' if j2 else 'FAIL'} — true answers among positive samples: {positive_true} of 40 "
            "(required at least 36)",
            "",
            "### Missed positives",
            "",
        ]
    )
    if missed_positive:
        lines.extend(
            f"- {row.get('case_id')} sample {row.get('sample')}: score {_display(row.get('noul'))}"
            for row in missed_positive
        )
    else:
        lines.append("- none")
    lines.extend(["", "### True negatives", ""])
    if true_negative:
        lines.extend(
            f"- {row.get('case_id')} sample {row.get('sample')}: score {_display(row.get('noul'))}"
            for row in true_negative
        )
    else:
        lines.append("- none")
    lines.extend(["", f"probe gate: {'PASS' if j1 and j2 else 'FAIL'}", ""])
    return "\n".join(lines), j1 and j2


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
    print(_redact(f"under question probe: {message}"), file=sys.stderr)
    return 2


def _check_corpus() -> int:
    cases = _load_cases()
    literal_matches = cases == FROZEN_CASES
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
    parser.add_argument("--max-calls", type=int, default=DEFAULT_MAX_CALLS)
    parser.add_argument("--max-usd", type=float, default=DEFAULT_MAX_USD)
    parser.add_argument("--rows", type=Path)
    parser.add_argument("--out", type=Path)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    try:
        if args.build_cases:
            cases = build_cases()
            _write_cases(cases)
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
        if args.max_calls < 1:
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
        document = run_cases(cases, samples=args.samples, max_calls=args.max_calls, out=args.out, client=client)
        print(f"{len(document['rows'])} rows written to {_redact(str(args.out))}")
        if document.get("stop_reason"):
            print(f"stop reason: {_redact(str(document['stop_reason']))}")
        return 0
    except (OSError, ValueError, TypeError, json.JSONDecodeError) as error:
        return _error(str(error))


if __name__ == "__main__":
    raise SystemExit(main())
