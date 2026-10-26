"""Offline-first, explicitly confirmed Jev boarding-classifier probe."""

from __future__ import annotations

import argparse
import json
import os
import statistics
import sys
import time
from pathlib import Path
from typing import Any

from storygame.runtime.jev import JevClient, noul_yes
from storygame.runtime.jev_questions import boards_vehicle

VEHICLE = "Kristin's truck"
DEFAULT_SAMPLES = 2
DEFAULT_MAX_CALLS = 100
UNUSABLE_STOP_AFTER = 3

COMMANDS: tuple[tuple[str, bool], ...] = (
    ("Go out to my truck.", True),
    ("Go to my truck.", True),
    ("Head to my truck.", True),
    ("Get in my truck.", True),
    ("Climb into my truck.", True),
    ("Sit in my truck.", True),
    ("Drive my truck to town.", True),
    ("Go out to the truck.", True),
    ("Go to the truck.", True),
    ("Get into the truck.", True),
    ("Drive the truck to the house.", True),
    ("Start my truck.", True),
    ("Walk over to my truck.", False),
    ("Walk up to my truck.", False),
    ("Approach my truck.", False),
    ("Step up to my truck.", False),
    ("Walk over to the truck.", False),
    ("Look through the truck window.", False),
    ("Examine my truck.", False),
    ("Open the truck door.", False),
    ("Touch the hood of my truck.", False),
    ("Check the tires on my truck.", False),
    ("Look at the passenger seat of my truck.", False),
    ("Leave my truck.", False),
    ("Get out of my truck.", False),
)

OLD_QUESTION: dict[str, Any] = {
    "boards_vehicle": {
        "type": "noul",
        "instructions": (
            "Decide whether the command has the player go to the vehicle, get into it, sit in it, or drive it."
        ),
        "criteria": {
            "true": "The command means going to the vehicle, getting into it, sitting in it, or driving it.",
            "false": "The command only looks at, touches, or talks about the vehicle, or leaves it.",
        },
    }
}


def _credential_values() -> tuple[str, ...]:
    return tuple(value for value in (os.environ.get("CLOUDFLARE_WORKER_TOKEN", "").strip(),) if value)


def _redact(value: str) -> str:
    for secret in _credential_values():
        value = value.replace(secret, "[REDACTED]")
    return value


def _write_json(path: Path, document: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    text = json.dumps(document, ensure_ascii=False, indent=2, sort_keys=True) + "\n"
    path.write_text(_redact(text), encoding="utf-8")


def _plan(samples: int) -> list[dict[str, Any]]:
    if samples < 1:
        raise ValueError("--samples must be at least 1")
    calls: list[dict[str, Any]] = []
    call_index = 1
    for command, expected in COMMANDS:
        for sample in range(samples):
            for arm in ("old", "current"):
                calls.append(
                    {
                        "call_index": call_index,
                        "arm": arm,
                        "command": command,
                        "expected": expected,
                        "sample": sample,
                        "state": {"command": command, "vehicle": VEHICLE},
                    }
                )
                call_index += 1
    return calls


def _raw_noul(answers: object) -> object:
    if not isinstance(answers, dict):
        return None
    board_answer = answers.get("boards_vehicle")
    if not isinstance(board_answer, dict) or "noul" not in board_answer:
        return None
    return board_answer["noul"]


def _ask(client: JevClient, call: dict[str, Any]) -> tuple[object, bool | None, float]:
    state = {"command": call["command"], "vehicle": VEHICLE}
    captured: dict[str, Any] = {}

    def ask(raw_state: object, questions: object) -> dict | None:
        answers = client.ask(raw_state, questions)
        captured["answers"] = answers
        return answers

    started = time.perf_counter()
    if call["arm"] == "old":
        answers = client.ask(state, OLD_QUESTION)
        predicted = noul_yes({"noul": _raw_noul(answers)}) if _raw_noul(answers) is not None else None
    else:
        predicted = boards_vehicle(ask, call["command"], VEHICLE)
        answers = captured.get("answers")
        raw_value = _raw_noul(answers)
        predicted = noul_yes({"noul": raw_value}) if raw_value is not None else None
    latency_ms = (time.perf_counter() - started) * 1000
    return _raw_noul(answers), predicted, latency_ms


def _status_stop_reason(client: JevClient) -> str | None:
    status = getattr(client, "last_status", None)
    if not isinstance(status, int) or status < 400:
        return None
    if status == 429:
        return "http_429"
    return f"http_{status}"


def _run(calls: list[dict[str, Any]], out: Path) -> dict[str, Any]:
    client = JevClient.from_environment()
    document: dict[str, Any] = {
        "schema": 1,
        "mode": "run",
        "calls_planned": len(calls),
        "rows": [],
        "stop_reason": None,
    }
    consecutive_unusable = 0
    for call in calls:
        raw_noul, predicted, latency_ms = _ask(client, call)
        row = {
            "call_index": call["call_index"],
            "arm": call["arm"],
            "command": call["command"],
            "expected": call["expected"],
            "sample": call["sample"],
            "raw_noul": raw_noul,
            "predicted": predicted,
            "correct": None if predicted is None else predicted == call["expected"],
            "latency_ms": latency_ms,
        }
        document["rows"].append(row)
        _write_json(out, document)

        status_reason = _status_stop_reason(client)
        if status_reason is not None:
            document["stop_reason"] = status_reason
            _write_json(out, document)
            break
        if predicted is None:
            consecutive_unusable += 1
            if consecutive_unusable >= UNUSABLE_STOP_AFTER:
                document["stop_reason"] = "three_consecutive_unusable"
                _write_json(out, document)
                break
        else:
            consecutive_unusable = 0
    return document


def _print_plan(calls: list[dict[str, Any]]) -> None:
    print(f"{len(calls)} calls")
    for call in calls:
        print(
            f"{call['call_index']:03d}: {call['arm']} {call['command']} "
            f"expected={call['expected']} sample={call['sample']}"
        )


def _latency(rows: list[dict[str, Any]]) -> str:
    values = [float(row["latency_ms"]) for row in rows if isinstance(row.get("latency_ms"), (int, float))]
    if not values:
        return "n/a"
    return f"min {min(values):.2f} / median {statistics.median(values):.2f} / max {max(values):.2f} ms"


def _accuracy(rows: list[dict[str, Any]], expected: bool) -> str:
    usable = [row for row in rows if row.get("expected") is expected and row.get("correct") is not None]
    correct = sum(row.get("correct") is True for row in usable)
    percentage = 100 * correct / len(usable) if usable else 0
    return f"{correct} / {len(usable)} ({percentage:.1f}%)"


def _answer_text(row: dict[str, Any] | None) -> str:
    if row is None or row.get("predicted") is None:
        return "unusable"
    return "yes" if row["predicted"] else "no"


def _report(rows_path: Path, out: Path) -> None:
    document = json.loads(rows_path.read_text(encoding="utf-8"))
    rows = document.get("rows", [])
    if not isinstance(rows, list):
        raise ValueError("rows file has no rows list")
    lines = ["# Jev boarding probe report", "", f"Rows rendered: {len(rows)}", ""]
    for arm in ("old", "current"):
        arm_rows = [row for row in rows if row.get("arm") == arm]
        correct = sum(row.get("correct") is True for row in arm_rows)
        unusable = sum(row.get("correct") is None for row in arm_rows)
        lines.extend(
            [
                f"## {arm}",
                "",
                f"- {arm}: {correct} / {len(arm_rows)} correct / total",
                f"- Unusable: {unusable}",
                f"- Expected True accuracy (on expected-True): {_accuracy(arm_rows, True)}",
                f"- Expected False accuracy (on expected-False): {_accuracy(arm_rows, False)}",
                f"- Latency: {_latency(arm_rows)}",
                "",
            ]
        )

    samples = sorted({row.get("sample") for row in rows if isinstance(row.get("sample"), int)})
    lines.extend(
        [
            "## Command answers",
            "",
            "| Command | Expected | "
            + " | ".join(f"{arm} s{sample}" for sample in samples for arm in ("old", "current"))
            + " |",
            "| --- | --- | " + " | ".join("---" for _ in samples for _ in ("old", "current")) + " |",
        ]
    )
    for command, expected in COMMANDS:
        cells = []
        for sample in samples:
            for arm in ("old", "current"):
                match = next(
                    (
                        row
                        for row in rows
                        if row.get("command") == command and row.get("sample") == sample and row.get("arm") == arm
                    ),
                    None,
                )
                cells.append(_answer_text(match))
        lines.append(f"| {command} | {str(expected).lower()} | " + " | ".join(cells) + " |")
    lines.append("")

    lines.extend(["## All rows", ""])
    for row in rows:
        lines.extend(
            [
                f"### Call {row.get('call_index')}",
                "",
                f"- Arm / command / sample: {row.get('arm')} / {row.get('command')} / {row.get('sample')}",
                f"- Expected / raw_noul / predicted / correct: {row.get('expected')} / {row.get('raw_noul')} / "
                f"{row.get('predicted')} / {row.get('correct')}",
                f"- Latency: {row.get('latency_ms')} ms",
                "",
            ]
        )

    lines.extend(["## Wrong or unusable rows", ""])
    problem_rows = [row for row in rows if row.get("correct") is not True]
    if problem_rows:
        for row in problem_rows:
            lines.append(
                f"- Call {row.get('call_index')}: {row.get('arm')} — {row.get('command')} "
                f"expected={row.get('expected')} raw_noul={row.get('raw_noul')} "
                f"predicted={row.get('predicted')} correct={row.get('correct')}"
            )
    else:
        lines.append("- None")
    lines.append("")
    if document.get("stop_reason"):
        lines.extend([f"Stop reason: {document['stop_reason']}", ""])
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(_redact("\n".join(lines)), encoding="utf-8")


def _error(message: str) -> int:
    print(f"jev boarding probe: {_redact(message)}", file=sys.stderr)
    return 2


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    modes = parser.add_mutually_exclusive_group(required=True)
    modes.add_argument("--dry", action="store_true")
    modes.add_argument("--run", action="store_true")
    modes.add_argument("--report", action="store_true")
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--rows", type=Path)
    parser.add_argument("--samples", type=int, default=DEFAULT_SAMPLES)
    parser.add_argument("--confirm", action="store_true")
    parser.add_argument("--max-calls", type=int, default=DEFAULT_MAX_CALLS)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    try:
        if args.report:
            if args.rows is None:
                return _error("--report requires --rows")
            _report(args.rows, args.out)
            print(f"report: {_redact(str(args.out))}")
            return 0

        calls = _plan(args.samples)
        if args.dry:
            _write_json(args.out, {"schema": 1, "mode": "dry", "calls": calls})
            _print_plan(calls)
            return 0
        if not args.confirm:
            return _error("run mode requires --confirm")
        if args.max_calls < len(calls):
            return _error(f"planned calls {len(calls)} exceed --max-calls {args.max_calls}")
        if not os.environ.get("CLOUDFLARE_WORKER_URL", "").strip():
            return _error("run mode requires CLOUDFLARE_WORKER_URL")
        if not os.environ.get("CLOUDFLARE_WORKER_TOKEN", "").strip():
            return _error("run mode requires CLOUDFLARE_WORKER_TOKEN")
        document = _run(calls, args.out)
        print(f"{len(document['rows'])} rows written to {_redact(str(args.out))}")
        return 0
    except (OSError, ValueError, TypeError, json.JSONDecodeError) as error:
        return _error(str(error))


if __name__ == "__main__":
    raise SystemExit(main())
