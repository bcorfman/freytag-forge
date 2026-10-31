"""Calibrate typed Jev questions for unsupported condition and contents claims."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import statistics
import sys
import time
from collections.abc import Callable
from numbers import Real
from pathlib import Path
from typing import Any

from scripts.ringer.environment_narration import j1_scope_probe as scope
from storygame.runtime.jev import JevClient

ACCEPT_ABOVE = 0.65
REJECT_BELOW = 0.35
COST_PER_MILLION_INPUT_TOKENS = scope.COST_PER_MILLION_INPUT_TOKENS
DEFAULT_MAX_CALLS = 2100
DEFAULT_MAX_USD = 0.06
DEFAULT_SAMPLES = 5
FIXED_SEED = scope.FIXED_SEED
UNUSABLE_STOP_AFTER = scope.UNUSABLE_STOP_AFTER
QUESTION_KEY = "condition_consistent"
VARIANTS = ("A", "B", "C")
CASE_FIELDS = {"id", "set", "thing", "command", "narration", "declared", "forbidden", "source_ref"}
FORBIDDEN_KINDS = (
    "opens_or_enters_drain",
    "invents_ajar_or_cover_state",
    "asserts_definite_contents",
)

CASES_PATH = Path(__file__).with_name("drain_condition_judge") / "cases.jsonl"
LOCK_PATH = Path(__file__).with_name("drain_condition_judge") / "lock.json"
DRAIN_SOURCE_PATH = Path("bench/results/environment-narration/t9h-drain-condition/corpus/corpus-adjudicated.json")

_redact = scope._redact
_write_json = scope._write_json


def _sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _noul_question(instructions: str, true: str, false: str) -> dict[str, object]:
    return {
        "type": "noul",
        "instructions": instructions,
        "criteria": {"true": true, "false": false},
    }


def _variant_a_question() -> dict[str, object]:
    return _noul_question(
        "Decide whether the narration stays inside what is declared for the thing named in the state. "
        "Treat a claim that the thing is open, ajar, lifted, covered, or entered, or a claim about what is inside it, including what can be seen, heard or smelled there, such as darkness, water, objects, sounds or smells, as a violation when the narration states it as fact.",  # noqa: E501
        "The narration does not state that the thing is open, ajar, lifted, covered, or entered, and does not state what is inside it, including what can be seen, heard or smelled there, such as darkness, water, objects, sounds or smells, as fact.",  # noqa: E501
        "The narration states that the thing is open, ajar, lifted, covered, or entered, or states what is inside it, including what can be seen, heard or smelled there, such as darkness, water, objects, sounds or smells, as fact.",  # noqa: E501
    )


def _variant_b_question() -> dict[str, object]:
    return _noul_question(
        "Decide whether the narration is consistent with the declared sentence for the thing named in the state. "
        "It is consistent when it does not state any open, ajar, lifted, covered, or entered condition, or state what is inside it, including what can be seen, heard or smelled there, such as darkness, water, objects, sounds or smells, unless the declared sentence supports it. "  # noqa: E501
        "The declared sentence says whether the engine opened the thing this turn, and an opening the engine performed is supported. Looking at, approaching, kneeling beside, touching the outside, or wondering what might be inside are consistent.",  # noqa: E501
        "The narration is consistent with the declared sentence. It does not state an unsupported open, ajar, lifted, covered, or entered condition or what is inside it, including what can be seen, heard or smelled there, such as darkness, water, objects, sounds or smells, as fact.",  # noqa: E501
        "The narration is not consistent with the declared sentence. It states an unsupported open, ajar, lifted, covered, or entered condition or what is inside it, including what can be seen, heard or smelled there, such as darkness, water, objects, sounds or smells, as fact.",  # noqa: E501
    )


def _variant_c_question() -> dict[str, object]:
    question = _variant_b_question()
    question["instructions"] = (
        str(question["instructions"])
        + " A condition or contents that the declared sentence does not mention is not supported."
    )
    return question


def variant_a_payload(case: dict[str, Any]) -> tuple[dict[str, object], dict[str, dict[str, object]]]:
    state = {"narration": case["narration"], "thing": case["thing"]}
    return state, {QUESTION_KEY: _variant_a_question()}


def variant_b_payload(case: dict[str, Any]) -> tuple[dict[str, object], dict[str, dict[str, object]]]:
    state = {
        "narration": case["narration"],
        "thing": case["thing"],
        "command": case["command"],
        "declared": case["declared"],
    }
    return state, {QUESTION_KEY: _variant_b_question()}


def variant_c_payload(case: dict[str, Any]) -> tuple[dict[str, object], dict[str, dict[str, object]]]:
    state, _ = variant_b_payload(case)
    return state, {QUESTION_KEY: _variant_c_question()}


def bare_payload(case: dict[str, Any]) -> tuple[dict[str, object], dict[str, dict[str, object]]]:
    return variant_a_payload(case)


def declared_state_payload(case: dict[str, Any]) -> tuple[dict[str, object], dict[str, dict[str, object]]]:
    return variant_b_payload(case)


def strict_declared_state_payload(case: dict[str, Any]) -> tuple[dict[str, object], dict[str, dict[str, object]]]:
    return variant_c_payload(case)


PAYLOAD_BUILDERS = {"A": variant_a_payload, "B": variant_b_payload, "C": variant_c_payload}


def _load_json(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        raise ValueError(f"could not read JSON source: {path}") from error
    if not isinstance(value, dict):
        raise ValueError(f"JSON source is not an object: {path}")
    return value


def _item_word(count: int) -> str:
    return "item" if count == 1 else "items"


def _declared_sentence(row: dict[str, Any]) -> str:
    state = row.get("declared_state")
    if not isinstance(state, dict):
        raise ValueError(f"held-out row has no declared_state: {row.get('id')}")
    open_state = state.get("open_state")
    if open_state not in {None, "closed", "open"}:
        raise ValueError(f"held-out row has an unknown open_state: {row.get('id')}")
    state_text = "has no open or closed value" if open_state is None else str(open_state)
    contents = state.get("declared_contents")
    if not isinstance(contents, list) or not all(isinstance(item, str) for item in contents):
        raise ValueError(f"held-out row has invalid declared_contents: {row.get('id')}")
    hidden = state.get("hidden_contents_present")
    fixed = state.get("fixed")
    engine_opened = row.get("engine_opened")
    if not isinstance(hidden, bool) or not isinstance(fixed, bool) or not isinstance(engine_opened, bool):
        raise ValueError(f"held-out row has invalid declaration flags: {row.get('id')}")
    hidden_text = ", some hidden" if hidden else ""
    fixed_text = "fixed in place" if fixed else "not fixed in place"
    opened_text = "did" if engine_opened else "did not"
    return (
        f"Declared before the turn: {row['thing']} was {state_text}; "
        f"{len(contents)} declared {_item_word(len(contents))}{hidden_text}; {fixed_text}. "
        f"The engine {opened_text} open it this turn."
    )


def _frozen_label(row: dict[str, Any], *, heldout: bool) -> bool:
    if heldout:
        value = row.get("forbidden")
        if not isinstance(value, bool):
            raise ValueError(f"held-out row has no frozen forbidden label: {row.get('id')}")
        return value
    label = row.get("final_label")
    if not isinstance(label, dict):
        raise ValueError(f"drain row has no final_label: {row.get('id')}")
    return any(label.get(kind) is True for kind in FORBIDDEN_KINDS)


def _case_from_row(row: dict[str, Any], *, set_name: str) -> dict[str, Any]:
    if not all(isinstance(row.get(field), str) and row[field] for field in ("id", "narration", "source_ref")):
        raise ValueError(f"source row has incomplete identity fields: {row.get('id')}")
    if set_name == "drain":
        thing = "storm drain"
        command = "inspect the storm drain"
        declared = "the storm drain has no open or closed value, no declared contents, and is fixed in place."
    else:
        thing = row.get("thing")
        command = row.get("command")
        if not isinstance(thing, str) or not thing or not isinstance(command, str) or not command:
            raise ValueError(f"held-out row has incomplete case fields: {row.get('id')}")
        declared = _declared_sentence(row)
    return {
        "id": f"{set_name}-{row['id']}",
        "set": set_name,
        "thing": thing,
        "command": command,
        "narration": row["narration"],
        "declared": declared,
        "forbidden": _frozen_label(row, heldout=set_name == "heldout"),
        "source_ref": row["source_ref"],
    }


def build_cases() -> list[dict[str, Any]]:
    corpus = _load_json(Path("bench/results/environment-narration/t9h-drain-condition/corpus/corpus-adjudicated.json"))
    heldout = _load_json(Path("bench/results/environment-narration/t9h-drain-condition/heldout/heldout-labeled.json"))
    drain_rows = corpus.get("rows")
    heldout_rows = heldout.get("rows")
    if not isinstance(drain_rows, list) or len(drain_rows) != 100:
        raise ValueError("drain source must contain exactly 100 rows")
    if not isinstance(heldout_rows, list) or len(heldout_rows) != 40:
        raise ValueError("held-out source must contain exactly 40 rows")
    cases = [_case_from_row(row, set_name="drain") for row in drain_rows]
    cases.extend(_case_from_row(row, set_name="heldout") for row in heldout_rows)
    return cases


def _case_lines(cases: list[dict[str, Any]]) -> bytes:
    return "".join(json.dumps(case, ensure_ascii=False, separators=(",", ":")) + "\n" for case in cases).encode()


def _write_cases_and_lock(cases_path: Path = CASES_PATH, lock_path: Path = LOCK_PATH) -> bytes:
    if cases_path.exists() or lock_path.exists():
        raise ValueError("frozen cases or lock already exists; refusing to overwrite")
    data = _case_lines(build_cases())
    cases_path.parent.mkdir(parents=True, exist_ok=True)
    cases_path.write_bytes(data)
    lock_path.write_text(
        json.dumps({"cases_sha256": _sha256(data), "case_count": data.count(b"\n")}, indent=2) + "\n",
        encoding="utf-8",
    )
    return data


def _load_cases(path: Path = CASES_PATH) -> tuple[list[dict[str, Any]], bytes]:
    try:
        data = path.read_bytes()
    except FileNotFoundError as error:
        raise ValueError(f"cases file is missing: {path}") from error
    cases = []
    for line_number, line in enumerate(data.decode("utf-8").splitlines(), start=1):
        if not line.strip():
            continue
        try:
            case = json.loads(line)
        except json.JSONDecodeError as error:
            raise ValueError(f"invalid cases JSON on line {line_number}") from error
        if not isinstance(case, dict):
            raise ValueError(f"case on line {line_number} is not an object")
        cases.append(case)
    return cases, data


def _validation_errors(cases: list[dict[str, Any]]) -> list[str]:
    errors = []
    seen: set[str] = set()
    for index, case in enumerate(cases, start=1):
        name = str(case.get("id", f"line {index}"))
        if set(case) != CASE_FIELDS:
            errors.append(f"{name}: fields must be exactly {sorted(CASE_FIELDS)}")
        if not isinstance(case.get("id"), str) or not case["id"]:
            errors.append(f"{name}: id must be non-empty")
        elif case["id"] in seen:
            errors.append(f"{name}: duplicate id")
        else:
            seen.add(case["id"])
        if case.get("set") not in {"drain", "heldout"}:
            errors.append(f"{name}: unknown set")
        for field in ("thing", "command", "narration", "declared", "source_ref"):
            if not isinstance(case.get(field), str) or not case[field]:
                errors.append(f"{name}: {field} must be non-empty")
        if not isinstance(case.get("forbidden"), bool):
            errors.append(f"{name}: forbidden must be boolean")
        if "open_state_after" in json.dumps(case, ensure_ascii=False):
            errors.append(f"{name}: open_state_after is forbidden")
    if len(cases) != 140:
        errors.append(f"case count must be 140, got {len(cases)}")
    for set_name, expected_count, expected_forbidden in (("drain", 100, 54), ("heldout", 40, 10)):
        selected = [case for case in cases if case.get("set") == set_name]
        if len(selected) != expected_count:
            errors.append(f"{set_name} count must be {expected_count}, got {len(selected)}")
        forbidden = sum(case.get("forbidden") is True for case in selected)
        if forbidden != expected_forbidden:
            errors.append(f"{set_name} forbidden count must be {expected_forbidden}, got {forbidden}")
    return errors


def _validated_cases() -> tuple[list[dict[str, Any]], bytes]:
    cases, data = _load_cases()
    errors = _validation_errors(cases)
    if errors:
        raise ValueError("cases validation failed: " + "; ".join(errors))
    return cases, data


def _lock_matches(data: bytes) -> bool:
    try:
        lock = json.loads(LOCK_PATH.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return False
    return lock == {"cases_sha256": _sha256(data), "case_count": 140}


def planned_calls(cases: list[dict[str, Any]], samples: int = DEFAULT_SAMPLES) -> list[dict[str, Any]]:
    if samples < 1:
        raise ValueError("sample count must be at least 1")
    return [
        {"case": case, "variant": variant, "sample": sample}
        for sample in range(samples)
        for case in cases
        for variant in VARIANTS
    ]


def planned_count(cases: list[dict[str, Any]], samples: int = DEFAULT_SAMPLES) -> int:
    return len(planned_calls(cases, samples))


def _payload(case: dict[str, Any], variant: str) -> tuple[dict[str, object], dict[str, dict[str, object]]]:
    try:
        return PAYLOAD_BUILDERS[variant](case)
    except KeyError as error:
        raise ValueError(f"unknown variant: {variant}") from error


def _estimate_tokens(cases: list[dict[str, Any]], samples: int) -> float:
    chars = sum(
        len(json.dumps(_payload(case, variant), ensure_ascii=False, separators=(",", ":")))
        for case in cases
        for variant in VARIANTS
    )
    return chars * samples / 4


def _ceiling(cases: list[dict[str, Any]], samples: int) -> float:
    return _estimate_tokens(cases, samples) / 1_000_000 * COST_PER_MILLION_INPUT_TOKENS * 1.5


def _verdict(score: float | None) -> str:
    if score is None:
        return "unavailable"
    if score > ACCEPT_ABOVE:
        return "accept"
    if score < REJECT_BELOW:
        return "reject"
    return "uncertain"


def _score(answers: object) -> tuple[float | None, str]:
    if not isinstance(answers, dict):
        return None, "ask_returned_none"
    answer = answers.get(QUESTION_KEY)
    if not isinstance(answer, dict):
        return None, f"missing_answer:{QUESTION_KEY}"
    value = answer.get("noul")
    if isinstance(value, bool) or not isinstance(value, Real) or not 0 <= value <= 1:
        return None, f"invalid_answer:{QUESTION_KEY}"
    return float(value), ""


def _status_stop_reason(client: object) -> str | None:
    status = getattr(client, "last_status", None)
    if not isinstance(status, int):
        return None
    if status == 402:
        return "quota_error"
    if status == 429 or status >= 500:
        return f"http_{status}"
    if status in {401, 403}:
        return "auth_error"
    return None


def _row(
    call_index: int,
    planned: dict[str, Any],
    answers: object,
    client: object,
    latency_ms: float,
    cases_hash: str,
) -> dict[str, Any]:
    score, score_failure = _score(answers)
    case = planned["case"]
    return {
        "call_index": call_index,
        "case_id": case["id"],
        "set": case["set"],
        "thing": case["thing"],
        "variant": planned["variant"],
        "sample": planned["sample"],
        "score": score,
        "verdict": _verdict(score),
        "outcome": "ok" if score is not None else "unavailable",
        "failure": score_failure or None,
        "latency_ms": latency_ms,
        "jev_model": getattr(client, "last_model", None),
        "jev_version": getattr(client, "last_version", None),
        "thresholds": {"accept_above": ACCEPT_ABOVE, "reject_below": REJECT_BELOW},
        "cases_sha256": cases_hash,
    }


def run_cases(
    cases: list[dict[str, Any]],
    *,
    samples: int,
    max_calls: int,
    out: Path,
    client: object,
    cases_hash: str,
    min_interval_s: float = 0.0,
    clock: Callable[[], float] = time.monotonic,
    sleep: Callable[[float], None] = time.sleep,
) -> dict[str, Any]:
    if min_interval_s < 0:
        raise ValueError("--min-interval-s must be non-negative")
    if out.exists():
        raise ValueError(f"rows already exist at {out}")
    calls = planned_calls(cases, samples)
    document: dict[str, Any] = {
        "schema": 1,
        "mode": "run",
        "samples": samples,
        "calls_planned": len(calls),
        "rows": [],
        "stop_reason": "incomplete",
        "cases_sha256": cases_hash,
    }
    _write_json(out, document)
    unusable = 0
    last_started: float | None = None
    try:
        for call_index, planned in enumerate(calls[:max_calls], start=1):
            state, questions = _payload(planned["case"], planned["variant"])
            if min_interval_s > 0 and last_started is not None:
                remaining = min_interval_s - (clock() - last_started)
                if remaining > 0:
                    sleep(remaining)
            if min_interval_s > 0:
                last_started = clock()
            started = time.perf_counter()
            try:
                answers = client.ask(state, questions)
            except Exception:
                if _status_stop_reason(client) is None:
                    raise
                answers = None
            latency_ms = (time.perf_counter() - started) * 1000
            document["rows"].append(_row(call_index, planned, answers, client, latency_ms, cases_hash))
            stop_reason = _status_stop_reason(client)
            if stop_reason is None and answers is None:
                unusable += 1
                if unusable >= UNUSABLE_STOP_AFTER:
                    stop_reason = "three_consecutive_unusable"
            elif stop_reason is None:
                unusable = 0
            if stop_reason is None and len(document["rows"]) >= max_calls and len(calls) > max_calls:
                stop_reason = "max_calls"
            if stop_reason is None and len(document["rows"]) == len(calls):
                document["stop_reason"] = None
            elif stop_reason is not None:
                document["stop_reason"] = stop_reason
            _write_json(out, document)
            if stop_reason is not None:
                break
        if len(document["rows"]) == len(calls):
            document["stop_reason"] = None
            _write_json(out, document)
        return document
    except Exception:
        document["stop_reason"] = "incomplete"
        _write_json(out, document)
        raise


def _case_outcome(rows: list[dict[str, Any]], case_id: str, samples: int) -> tuple[str, float | None]:
    scores = [row.get("score") for row in rows if isinstance(row.get("score"), (int, float))]
    if len(scores) != samples:
        return "uncertain", None
    median = float(statistics.median(scores))
    return _verdict(median), median


def _case_rows(rows: list[dict[str, Any]], variant: str, case_id: str) -> list[dict[str, Any]]:
    return [row for row in rows if row.get("variant") == variant and row.get("case_id") == case_id]


def _drain_kind_counts() -> dict[str, int]:
    try:
        rows = _load_json(DRAIN_SOURCE_PATH).get("rows")
    except ValueError:
        return {}
    if not isinstance(rows, list):
        return {}
    return {
        kind: sum(isinstance(row, dict) and row.get("final_label", {}).get(kind) is True for row in rows)
        for kind in FORBIDDEN_KINDS
    }


def _report_text(document: dict[str, Any], cases: list[dict[str, Any]]) -> tuple[str, bool]:
    rows = document.get("rows")
    if not isinstance(rows, list):
        raise ValueError("rows file has no rows list")
    samples = document.get("samples", DEFAULT_SAMPLES)
    complete = document.get("stop_reason") is None and len(rows) == document.get("calls_planned") == 2100
    lines = [
        "# T9h drain condition judge report",
        "",
        f"Rows rendered: {len(rows)}",
        f"Run completeness: {'complete' if complete else 'partial'}",
        "",
    ]
    variant_passes: dict[str, bool] = {}
    for variant in VARIANTS:
        results = {}
        for case in cases:
            results[case["id"]] = _case_outcome(_case_rows(rows, variant, case["id"]), case["id"], samples)
        lines.extend([f"## Variant {variant}", ""])
        for set_name in ("drain", "heldout"):
            selected = [case for case in cases if case["set"] == set_name]
            accepted = sum(results[case["id"]][0] == "accept" for case in selected)
            rejected = sum(results[case["id"]][0] == "reject" for case in selected)
            uncertain = sum(results[case["id"]][0] == "uncertain" for case in selected)
            lines.append(
                f"- {set_name}: cases={len(selected)} accepted={accepted} rejected={rejected} uncertain={uncertain}"
            )
        conditions = (
            ("drain forbidden rejected", "drain", True, "reject", 49, 54),
            ("drain clean accepted", "drain", False, "accept", 42, 46),
            ("held-out forbidden rejected", "heldout", True, "reject", 9, 10),
            ("held-out clean accepted", "heldout", False, "accept", 27, 30),
        )
        condition_results = []
        for label, set_name, forbidden, expected, minimum, denominator in conditions:
            selected = [case for case in cases if case["set"] == set_name and case["forbidden"] is forbidden]
            count = sum(results[case["id"]][0] == expected for case in selected)
            passed = count >= minimum and len(selected) == denominator
            condition_results.append(passed)
            lines.append(
                f"- {label}: {'PASS' if passed else 'FAIL'} — {count} of {len(selected)} "
                f"(gate {minimum} of {denominator})"
            )
        variant_passes[variant] = complete and all(condition_results)
        lines.extend(["", "### False accepts", ""])
        for case in cases:
            if case["forbidden"] and results[case["id"]][0] == "accept":
                lines.append(f"- {case['id']} {case['thing']}")
        lines.extend(["", "### False rejects", ""])
        for case in cases:
            if not case["forbidden"] and results[case["id"]][0] == "reject":
                lines.append(f"- {case['id']} {case['thing']}")
        lines.extend(["", "### Drain forbidden-kind breakdown", ""])
        for kind, count in _drain_kind_counts().items():
            lines.append(f"- {kind}: {count}")
        lines.append("")
    if not complete:
        lines.extend(["## Overall: INCONCLUSIVE", "", "The run is partial; no pass is claimed."])
        return "\n".join(lines), False
    if variant_passes["B"]:
        lines.extend(["## Overall: PASS", "", "Variant B passed the frozen gate."])
        return "\n".join(lines), True
    if variant_passes["A"] or variant_passes["C"]:
        lines.extend(
            [
                "## Overall: FAIL",
                "",
                "candidate failed; another variant passed, which is a finding for a new preregistration, not a pass",
            ]
        )
    else:
        lines.extend(["## Overall: FAIL", "", "Variant B failed the frozen gate."])
    return "\n".join(lines), False


def report_rows(rows_path: Path, out: Path) -> int:
    document = _load_json(rows_path)
    cases, cases_data = _validated_cases()
    if not _lock_matches(cases_data):
        raise ValueError("report requires a matching cases lock")
    if document.get("cases_sha256") != _sha256(cases_data):
        raise ValueError("rows file does not match the frozen cases")
    report, passed = _report_text(document, cases)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(_redact(report), encoding="utf-8")
    return 0 if passed else 1


def _print_dry_run(cases: list[dict[str, Any]], samples: int, min_interval_s: float) -> None:
    planned = planned_count(cases, samples)
    print(f"case count: {len(cases)}")
    print(f"planned calls: {planned} = {len(cases)} cases x 3 variants x {samples} samples")
    print(f"token estimate: {_estimate_tokens(cases, samples):.2f}")
    print(f"USD ceiling: ${_ceiling(cases, samples):.6f}")
    print(f"minimum interval: {min_interval_s:.6f} s")
    print(f"estimated minimum duration: {planned * min_interval_s:.2f} s")


def _error(message: str) -> int:
    print(_redact(f"drain condition judge: {message}"), file=sys.stderr)
    return 2


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    modes = parser.add_mutually_exclusive_group(required=True)
    modes.add_argument("--build-cases", action="store_true")
    modes.add_argument("--validate", action="store_true")
    modes.add_argument("--dry-run", action="store_true")
    modes.add_argument("--run", action="store_true")
    modes.add_argument("--report", action="store_true")
    parser.add_argument("--samples", type=int, default=DEFAULT_SAMPLES)
    parser.add_argument("--confirm", action="store_true")
    parser.add_argument("--max-calls", type=int, default=DEFAULT_MAX_CALLS)
    parser.add_argument("--max-usd", type=float, default=DEFAULT_MAX_USD)
    parser.add_argument("--min-interval-s", type=float, default=0.0)
    parser.add_argument("--rows", type=Path)
    parser.add_argument("--out", type=Path)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    try:
        if args.min_interval_s < 0:
            return _error("--min-interval-s must be non-negative")
        if args.build_cases:
            _write_cases_and_lock()
            print(f"built {_redact(str(CASES_PATH))}")
            print(f"locked {_redact(str(LOCK_PATH))}")
            return 0
        if args.report:
            if args.rows is None or args.out is None:
                return _error("--report requires --rows and --out")
            return report_rows(args.rows, args.out)
        cases, cases_data = _validated_cases()
        if args.validate:
            matching = _lock_matches(cases_data)
            print(f"case count: {len(cases)}")
            print(f"cases lock: {'matching' if matching else 'mismatch'}")
            return 0 if matching else 1
        if args.samples != DEFAULT_SAMPLES:
            return _error(f"samples are frozen at {DEFAULT_SAMPLES}")
        if not _lock_matches(cases_data):
            return _error("mode requires a matching cases lock")
        planned = planned_count(cases, args.samples)
        ceiling = _ceiling(cases, args.samples)
        if args.dry_run:
            if planned > args.max_calls:
                return _error(f"planned calls {planned} exceed --max-calls {args.max_calls}")
            if ceiling > args.max_usd:
                return _error(f"USD ceiling ${ceiling:.6f} exceeds --max-usd ${args.max_usd:.6f}")
            _print_dry_run(cases, args.samples, args.min_interval_s)
            return 0
        if not args.confirm:
            return _error("run mode requires --confirm")
        if args.out is None:
            return _error("run mode requires --out")
        if args.max_calls < 1:
            return _error("--max-calls must be at least 1")
        if planned > args.max_calls:
            return _error(f"planned calls {planned} exceed --max-calls {args.max_calls}")
        if ceiling > args.max_usd:
            return _error(f"USD ceiling ${ceiling:.6f} exceeds --max-usd ${args.max_usd:.6f}")
        if args.out.exists():
            return _error(f"rows already exist at {args.out}")
        if not os.environ.get("CLOUDFLARE_WORKER_URL", "").strip():
            return _error("run mode requires CLOUDFLARE_WORKER_URL")
        if not os.environ.get("CLOUDFLARE_WORKER_TOKEN", "").strip():
            return _error("run mode requires CLOUDFLARE_WORKER_TOKEN")
        document = run_cases(
            cases,
            samples=args.samples,
            max_calls=args.max_calls,
            out=args.out,
            client=JevClient.from_environment(),
            cases_hash=_sha256(cases_data),
            min_interval_s=args.min_interval_s,
        )
        print(f"{len(document['rows'])} rows written to {_redact(str(args.out))}")
        return 0
    except (OSError, ValueError, TypeError, json.JSONDecodeError) as error:
        if args.validate:
            print(_redact(f"drain condition judge: {error}"), file=sys.stderr)
            return 1
        return _error(str(error))


if __name__ == "__main__":
    raise SystemExit(main())
