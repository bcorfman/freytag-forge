"""Run and report the preregistered T9h opening-condition judge."""

from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import os
import statistics
import sys
import time
from collections.abc import Callable
from pathlib import Path
from typing import Any

from storygame.runtime.jev import JevClient
from storygame.runtime.opening_check import OPENING_QUESTION

ROOT = Path(__file__).resolve().parents[3]
CASES_PATH = Path(__file__).with_name("drain_condition_judge") / "cases-v3.jsonl"
LOCK_PATH = Path(__file__).with_name("drain_condition_judge") / "lock-v3.json"
QUESTION_KEY = "condition_consistent"
VARIANT = "D"
SAMPLES = 5
DEFAULT_MAX_CALLS = 900
DEFAULT_MAX_USD = 0.05
CASE_COUNT = 180
CASE_FIELDS = {"id", "set", "thing", "command", "narration", "declared", "forbidden", "source_ref"}
RELABELLED_SUFFIXES = (
    "drain-row-030",
    "drain-row-038",
    "drain-row-051",
    "drain-row-054",
    "drain-row-056",
    "drain-row-061",
    "drain-row-070",
    "drain-row-080",
    "drain-row-081",
    "drain-row-089",
    "drain-row-090",
)


def _load_module(path: Path, name: str) -> Any:
    specification = importlib.util.spec_from_file_location(name, path)
    if specification is None or specification.loader is None:
        raise RuntimeError(f"cannot load helper from {path}")
    module = importlib.util.module_from_spec(specification)
    specification.loader.exec_module(module)
    return module


_PROBE = _load_module(
    ROOT / "scripts/ringer/environment_narration/drain_condition_judge_probe.py",
    "opening_condition_v3_judge_helpers",
)
_row = _PROBE._row
_status_stop_reason = _PROBE._status_stop_reason
_verdict = _PROBE._verdict
UNUSABLE_STOP_AFTER = _PROBE.UNUSABLE_STOP_AFTER
COST_PER_MILLION_INPUT_TOKENS = _PROBE.COST_PER_MILLION_INPUT_TOKENS
_redact = _PROBE._redact
_write_json = _PROBE._write_json


def _sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def _load_cases(
    *,
    cases_path: Path | None = None,
    lock_path: Path | None = None,
) -> tuple[list[dict[str, Any]], bytes]:
    cases_path = cases_path or CASES_PATH
    lock_path = lock_path or LOCK_PATH
    try:
        data = cases_path.read_bytes()
        lock = _read_json(lock_path)
    except (OSError, json.JSONDecodeError) as error:
        raise ValueError(f"could not read frozen cases or lock: {error}") from error
    expected_lock = {"cases_sha256": _sha256(data), "case_count": CASE_COUNT}
    if lock != expected_lock:
        raise ValueError(f"{cases_path.name} hash or count does not match {lock_path.name}")
    cases: list[dict[str, Any]] = []
    for line_number, line in enumerate(data.decode("utf-8").splitlines(), start=1):
        if not line.strip():
            continue
        try:
            case = json.loads(line)
        except json.JSONDecodeError as error:
            raise ValueError(f"invalid case JSON on line {line_number}") from error
        if not isinstance(case, dict) or set(case) != CASE_FIELDS:
            raise ValueError(f"case on line {line_number} has invalid fields")
        cases.append(case)
    if len(cases) != CASE_COUNT:
        raise ValueError(f"case count must be {CASE_COUNT}, got {len(cases)}")
    counts = {set_name: sum(case["set"] == set_name for case in cases) for set_name in ("drain", "opening", "heldout")}
    if counts != {"drain": 100, "opening": 40, "heldout": 40}:
        raise ValueError(f"case set counts are invalid: {counts}")
    return cases, data


def _load_relabelled(path: Path | None) -> set[str] | None:
    if path is None:
        return None
    relabelled = _read_json(path)
    if not isinstance(relabelled, list) or not all(isinstance(case_id, str) for case_id in relabelled):
        raise ValueError("relabelled file must contain a JSON list of case ids")
    return set(relabelled)


def _payload(case: dict[str, Any]) -> tuple[dict[str, object], dict[str, dict[str, object]]]:
    state = {
        "narration": case["narration"],
        "thing": case["thing"],
        "command": case["command"],
        "declared": case["declared"],
    }
    return state, {QUESTION_KEY: OPENING_QUESTION}


def _planned_judge(cases: list[dict[str, Any]], samples: int = SAMPLES) -> list[dict[str, Any]]:
    return [{"case": case, "variant": VARIANT, "sample": sample} for sample in range(1, samples + 1) for case in cases]


def _estimate_tokens(cases: list[dict[str, Any]], samples: int = SAMPLES) -> float:
    characters = sum(
        len(json.dumps({"state": state, "questions": questions}, ensure_ascii=False, separators=(",", ":")))
        for case in cases
        for state, questions in (_payload(case),)
    )
    return characters * samples / 4


def _ceiling(cases: list[dict[str, Any]], samples: int = SAMPLES) -> float:
    return _estimate_tokens(cases, samples) / 1_000_000 * COST_PER_MILLION_INPUT_TOKENS * 1.5


def _case_outcome(rows: list[dict[str, Any]], samples: int = SAMPLES) -> tuple[str, float | None]:
    scores = [
        score
        for row in rows
        if not isinstance((score := row.get("score")), bool) and isinstance(score, (int, float)) and 0 <= score <= 1
    ]
    if len(scores) < samples:
        return "uncertain", None
    median = float(statistics.median(scores))
    return _verdict(median), median


def _judge_rows(
    cases: list[dict[str, Any]],
    *,
    samples: int,
    max_calls: int,
    max_usd: float,
    min_interval_s: float,
    out: Path,
    cases_hash: str,
    client: Any,
    clock: Callable[[], float] = time.monotonic,
    sleep: Callable[[float], None] = time.sleep,
) -> dict[str, Any]:
    if samples != SAMPLES:
        raise ValueError(f"samples are frozen at {SAMPLES}")
    planned = _planned_judge(cases, samples)
    if len(planned) > max_calls:
        raise ValueError(f"planned calls {len(planned)} exceed --max-calls {max_calls}")
    ceiling = _ceiling(cases, samples)
    if ceiling > max_usd:
        raise ValueError(f"USD ceiling ${ceiling:.6f} exceeds --max-usd ${max_usd:.6f}")
    if min_interval_s < 0:
        raise ValueError("--min-interval-s must be non-negative")
    if out.exists():
        raise ValueError(f"rows already exist at {out}; refusing to overwrite")
    document: dict[str, Any] = {
        "schema": 1,
        "mode": "judge",
        "samples": samples,
        "calls_planned": len(planned),
        "rows": [],
        "stop_reason": "incomplete",
        "cases_sha256": cases_hash,
    }
    _write_json(out, document)
    unusable = 0
    last_started: float | None = None
    for call_index, item in enumerate(planned[:max_calls], start=1):
        if min_interval_s > 0 and last_started is not None:
            remaining = min_interval_s - (clock() - last_started)
            if remaining > 0:
                sleep(remaining)
        if min_interval_s > 0:
            last_started = clock()
        state, questions = _payload(item["case"])
        started = time.perf_counter()
        try:
            answers = client.ask(state, questions)
        except Exception:
            if _status_stop_reason(client) is None:
                raise
            answers = None
        latency_ms = (time.perf_counter() - started) * 1000
        document["rows"].append(_row(call_index, item, answers, client, latency_ms, cases_hash))
        stop_reason = _status_stop_reason(client)
        if stop_reason is None and answers is None:
            unusable += 1
            if unusable >= UNUSABLE_STOP_AFTER:
                stop_reason = "three_consecutive_unusable"
        elif stop_reason is None:
            unusable = 0
        if stop_reason is None and len(document["rows"]) == max_calls and len(planned) > max_calls:
            stop_reason = "max_calls"
        if stop_reason is None and len(document["rows"]) == len(planned):
            document["stop_reason"] = None
        elif stop_reason is not None:
            document["stop_reason"] = stop_reason
        _write_json(out, document)
        if stop_reason is not None:
            break
    if len(document["rows"]) == len(planned):
        document["stop_reason"] = None
    elif document["stop_reason"] == "incomplete" and len(document["rows"]) >= max_calls:
        document["stop_reason"] = "max_calls"
    _write_json(out, document)
    return document


def judge_run(
    *,
    samples: int = SAMPLES,
    max_calls: int = DEFAULT_MAX_CALLS,
    max_usd: float = DEFAULT_MAX_USD,
    min_interval_s: float = 0.0,
    confirm: bool,
    out: Path,
    dry_run: bool,
    cases_path: Path | None = None,
    lock_path: Path | None = None,
) -> tuple[int, str]:
    if cases_path is None and lock_path is None:
        cases, cases_data = _load_cases()
    else:
        cases, cases_data = _load_cases(cases_path=cases_path, lock_path=lock_path)
    if samples != SAMPLES:
        raise ValueError(f"samples are frozen at {SAMPLES}")
    planned = len(cases) * samples
    ceiling = _ceiling(cases, samples)
    if planned > max_calls:
        raise ValueError(f"planned calls {planned} exceed --max-calls {max_calls}")
    if ceiling > max_usd:
        raise ValueError(f"USD ceiling ${ceiling:.6f} exceeds --max-usd ${max_usd:.6f}")
    if min_interval_s < 0:
        raise ValueError("--min-interval-s must be non-negative")
    if dry_run:
        text = f"planned calls: {planned}\nUSD ceiling: ${ceiling:.6f}"
        print(text)
        return 0, text
    if not confirm:
        raise ValueError("judge mode requires --confirm")
    if out.exists():
        raise ValueError(f"rows already exist at {out}; refusing to overwrite")
    if not os.environ.get("CLOUDFLARE_WORKER_URL", "").strip():
        raise ValueError("judge mode requires CLOUDFLARE_WORKER_URL")
    if not os.environ.get("CLOUDFLARE_WORKER_TOKEN", "").strip():
        raise ValueError("judge mode requires CLOUDFLARE_WORKER_TOKEN")
    _judge_rows(
        cases,
        samples=samples,
        max_calls=max_calls,
        max_usd=max_usd,
        min_interval_s=min_interval_s,
        out=out,
        cases_hash=_sha256(cases_data),
        client=JevClient.from_environment(),
    )
    return 0, ""


def report_rows(
    rows_path: Path,
    out: Path,
    *,
    cases_path: Path | None = None,
    lock_path: Path | None = None,
    relabelled_path: Path | None = None,
) -> int:
    if cases_path is None and lock_path is None:
        cases, cases_data = _load_cases()
    else:
        cases, cases_data = _load_cases(cases_path=cases_path, lock_path=lock_path)
    relabelled_ids = _load_relabelled(relabelled_path)
    document = _read_json(rows_path)
    rows = document.get("rows") if isinstance(document, dict) else None
    if not isinstance(rows, list):
        raise ValueError("rows file has no rows list")
    cases_hash = _sha256(cases_data)
    if document.get("cases_sha256") != cases_hash:
        raise ValueError("rows file does not match the frozen cases")
    samples = document.get("samples", SAMPLES)
    if samples != SAMPLES:
        raise ValueError(f"rows samples must be {SAMPLES}")
    planned = len(cases) * SAMPLES
    complete = document.get("stop_reason") is None and len(rows) == planned
    results: dict[str, tuple[str, float | None]] = {}
    for case in cases:
        case_rows = [row for row in rows if row.get("variant") == VARIANT and row.get("case_id") == case["id"]]
        results[case["id"]] = _case_outcome(case_rows)

    def outcome(case: dict[str, Any]) -> str:
        return results[case["id"]][0]

    def median_text(case: dict[str, Any]) -> str:
        median = results[case["id"]][1]
        return "uncertain" if median is None else f"{median:.6f}"

    gated = [case for case in cases if case["set"] in {"drain", "opening"}]
    gated_forbidden = [case for case in gated if case["forbidden"]]
    gated_clean = [case for case in gated if not case["forbidden"]]
    forbidden_rejected = sum(outcome(case) == "reject" for case in gated_forbidden)
    clean_accepted = sum(outcome(case) == "accept" for case in gated_clean)
    gate_passes = (
        complete and forbidden_rejected >= 0.9 * len(gated_forbidden) and clean_accepted >= 0.9 * len(gated_clean)
    )
    verdict = "PASS" if gate_passes else "INCONCLUSIVE" if not complete else "FAIL"
    lines = [
        "# T9h opening condition v3 report",
        "",
        f"Overall verdict: {verdict}",
        f"Rows rendered: {len(rows)}",
        f"Planned calls: {planned}",
        f"Run completeness: {'complete' if complete else 'partial'}",
        "",
        "## Per set",
        "",
    ]
    for set_name in ("drain", "opening", "heldout"):
        selected = [case for case in cases if case["set"] == set_name]
        forbidden = [case for case in selected if case["forbidden"]]
        clean = [case for case in selected if not case["forbidden"]]
        uncertain = sum(outcome(case) == "uncertain" for case in selected)
        lines.append(
            f"- {set_name}: forbidden rejected {sum(outcome(case) == 'reject' for case in forbidden)}/"
            f"{len(forbidden)}; "
            f"clean accepted {sum(outcome(case) == 'accept' for case in clean)}/{len(clean)}; uncertain {uncertain}"
        )
    if relabelled_ids is None:
        relabelled = [case for case in cases if any(case["id"].endswith(suffix) for suffix in RELABELLED_SUFFIXES)]
    else:
        relabelled = [case for case in cases if case["id"] in relabelled_ids]
    lines.extend(
        [
            "",
            "## Relabelled cases",
            "",
            f"- accepted={sum(outcome(case) == 'accept' for case in relabelled)} "
            f"uncertain={sum(outcome(case) == 'uncertain' for case in relabelled)} "
            f"rejected={sum(outcome(case) == 'reject' for case in relabelled)}",
            "",
            "## Per thing (opening)",
            "",
        ]
    )
    for thing in sorted({case["thing"] for case in cases if case["set"] == "opening"}):
        selected = [case for case in cases if case["set"] == "opening" and case["thing"] == thing]
        lines.append(
            f"- {thing}: accepted={sum(outcome(case) == 'accept' for case in selected)} "
            f"uncertain={sum(outcome(case) == 'uncertain' for case in selected)} "
            f"rejected={sum(outcome(case) == 'reject' for case in selected)}"
        )
    lines.extend(["", "## False accepts", ""])
    for case in cases:
        if case["forbidden"] and outcome(case) == "accept":
            lines.append(
                f"- {case['id']} | thing={case['thing']} | median={median_text(case)} | "
                f"narration={case['narration'][:200].replace(chr(10), ' ')}"
            )
    lines.extend(["", "## False rejects", ""])
    for case in cases:
        if not case["forbidden"] and outcome(case) == "reject":
            lines.append(
                f"- {case['id']} | thing={case['thing']} | median={median_text(case)} | "
                f"narration={case['narration'][:200].replace(chr(10), ' ')}"
            )
    lines.extend(
        [
            "",
            f"Gate: forbidden rejected {forbidden_rejected}/{len(gated_forbidden)}; "
            f"clean accepted {clean_accepted}/{len(gated_clean)}; complete={complete}",
            f"Overall verdict: {verdict}",
        ]
    )
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(verdict)
    return 0 if verdict == "PASS" else 1


def _error(message: str) -> int:
    print(_redact(f"opening condition v3: {message}"), file=sys.stderr)
    return 2


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    modes = parser.add_mutually_exclusive_group(required=True)
    modes.add_argument("--dry-run", action="store_true")
    modes.add_argument("--judge", action="store_true")
    modes.add_argument("--report", action="store_true")
    parser.add_argument("--confirm", action="store_true")
    parser.add_argument("--max-calls", type=int, default=DEFAULT_MAX_CALLS)
    parser.add_argument("--max-usd", type=float, default=DEFAULT_MAX_USD)
    parser.add_argument("--min-interval-s", type=float, default=0.0)
    parser.add_argument("--out", type=Path)
    parser.add_argument("--rows", type=Path)
    parser.add_argument("--cases", type=Path, default=CASES_PATH)
    parser.add_argument("--lock", type=Path, default=LOCK_PATH)
    parser.add_argument("--relabelled", type=Path)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    try:
        if args.dry_run:
            _code, _text = judge_run(
                max_calls=args.max_calls,
                max_usd=args.max_usd,
                min_interval_s=args.min_interval_s,
                confirm=args.confirm,
                out=args.out or Path("/dev/null"),
                dry_run=True,
                cases_path=args.cases,
                lock_path=args.lock,
            )
            return 0
        if args.judge:
            if args.out is None:
                return _error("--judge requires --out")
            _code, _text = judge_run(
                max_calls=args.max_calls,
                max_usd=args.max_usd,
                min_interval_s=args.min_interval_s,
                confirm=args.confirm,
                out=args.out,
                dry_run=False,
                cases_path=args.cases,
                lock_path=args.lock,
            )
            return 0
        if args.rows is None or args.out is None:
            return _error("--report requires --rows and --out")
        return report_rows(
            args.rows,
            args.out,
            cases_path=args.cases,
            lock_path=args.lock,
            relabelled_path=args.relabelled,
        )
    except (OSError, ValueError, TypeError, json.JSONDecodeError) as error:
        return _error(str(error))


if __name__ == "__main__":
    raise SystemExit(main())
