"""Build a blind sheet and report the T9h J1c drain gates."""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import random
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[3]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.ringer.environment_narration import enforce_report  # noqa: E402

SHUFFLE_SEED = 917263
TAGS = ("opens_drain", "moves_drain", "gives_contents")
ROUTE = "observe_storm_drain_1b"


def _load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def _source_id(replicate_index: int, turn_index: int) -> str:
    return f"r{replicate_index}t{turn_index}"


def _records(rows: list[dict[str, Any]], arm: str) -> list[dict[str, Any]]:
    result = []
    for replicate_index, replicate in enumerate(rows):
        for turn_index, turn in enumerate(replicate.get("turns", ())):
            result.append(
                {
                    "arm": arm,
                    "replicate": replicate_index,
                    "turn_index": turn_index,
                    "source_id": f"{arm}-{_source_id(replicate_index, turn_index)}",
                    "turn": turn,
                }
            )
    return result


def _attempts(turn: dict[str, Any]) -> list[dict[str, Any]]:
    value = turn.get("enforce_attempts")
    return value if isinstance(value, list) else []


def _rejected(turn: dict[str, Any]) -> list[dict[str, Any]]:
    return [attempt for attempt in _attempts(turn) if isinstance(attempt, dict) and attempt.get("accepted") is not True]


def _committed(turn: dict[str, Any]) -> bool:
    return turn.get("narration") is not None


def _text(value: Any) -> str:
    return "(none)" if value is None else str(value)


def _sheet_block(opaque_id: str, turn: dict[str, Any]) -> str:
    lines = [f"## {opaque_id}", "", f"Command: {_text(turn.get('input'))}", ""]
    rejected = _rejected(turn)
    lines.append("Rejected attempts:")
    if rejected:
        for index, attempt in enumerate(rejected, start=1):
            lines.extend([f"- Attempt {index}:", f"  {_text(attempt.get('narration'))}"])
    else:
        lines.append("- (none)")
    lines.extend(["", "Committed narration:", _text(turn.get("narration"))])
    return "\n".join(lines)


def _blind_material(
    off_rows: list[dict[str, Any]], on_rows: list[dict[str, Any]]
) -> tuple[str, dict[str, Any], dict[str, Any]]:
    records = _records(off_rows, "off") + _records(on_rows, "on")
    shuffled = list(records)
    random.Random(SHUFFLE_SEED).shuffle(shuffled)
    key = {}
    blocks = []
    labels = {}
    for index, record in enumerate(shuffled, start=1):
        opaque_id = f"turn-{index:03d}"
        key[opaque_id] = {
            "arm": record["arm"],
            "replicate": record["replicate"],
            "turn_index": record["turn_index"],
            "source_id": record["source_id"],
        }
        turn = record["turn"]
        labels[opaque_id] = {
            "committed": {tag: None for tag in TAGS} if _committed(turn) else None,
            "rejected_attempts": [{"really_deficient": None} for _ in _rejected(turn)],
        }
        blocks.append(_sheet_block(opaque_id, turn))
    sheet = "\n".join(["# Blind observation sheet", "", f"Shuffle seed: {SHUFFLE_SEED}", "", *blocks, ""])
    return sheet, key, labels


def _write_sheets(off_rows: list[dict[str, Any]], on_rows: list[dict[str, Any]], output: Path) -> None:
    output.mkdir(parents=True, exist_ok=True)
    sheet, key, labels = _blind_material(off_rows, on_rows)
    (output / "blind_sheet.md").write_text(sheet, encoding="utf-8")
    (output / "blind_key.json").write_text(json.dumps(key, indent=2) + "\n", encoding="utf-8")
    (output / "labels_template.json").write_text(json.dumps(labels, indent=2) + "\n", encoding="utf-8")


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _wilson(successes: int, total: int) -> tuple[float | None, float | None]:
    if total == 0:
        return None, None
    z = 1.959963984540054
    rate = successes / total
    denominator = 1 + z * z / total
    centre = (rate + z * z / (2 * total)) / denominator
    spread = z * math.sqrt(rate * (1 - rate) / total + z * z / (4 * total * total)) / denominator
    return max(0.0, centre - spread), min(1.0, centre + spread)


def _number(value: float | None) -> str:
    return "n/a" if value is None else f"{value:.3f}"


def _label(labels: dict[str, Any], opaque_id: str) -> dict[str, Any]:
    value = labels.get(opaque_id)
    return value if isinstance(value, dict) else {}


def _committed_tag(labels: dict[str, Any], opaque_id: str, tag: str) -> bool | None:
    committed = _label(labels, opaque_id).get("committed")
    if not isinstance(committed, dict):
        return None
    value = committed.get(tag)
    return value if isinstance(value, bool) else None


def _rejected_label(labels: dict[str, Any], opaque_id: str, index: int) -> bool | None:
    attempts = _label(labels, opaque_id).get("rejected_attempts")
    if not isinstance(attempts, list) or index >= len(attempts) or not isinstance(attempts[index], dict):
        return None
    value = attempts[index].get("really_deficient")
    return value if isinstance(value, bool) else None


def _missing_labels(records: list[dict[str, Any]], labels: dict[str, Any]) -> list[str]:
    missing = []
    for record in records:
        opaque_id = record["opaque_id"]
        turn = record["turn"]
        entry = _label(labels, opaque_id)
        if _committed(turn):
            committed = entry.get("committed")
            for tag in TAGS:
                if not isinstance(committed, dict) or not isinstance(committed.get(tag), bool):
                    missing.append(f"{opaque_id} committed {tag}")
        rejected_labels = entry.get("rejected_attempts")
        rejected = _rejected(turn)
        if not isinstance(rejected_labels, list) or len(rejected_labels) < len(rejected):
            missing.append(f"{opaque_id} rejected_attempts")
        else:
            for index in range(len(rejected)):
                if _rejected_label(labels, opaque_id, index) is None:
                    missing.append(f"{opaque_id} rejected {index + 1} really_deficient")
    return missing


def _first_accepted(turn: dict[str, Any]) -> bool:
    attempts = _attempts(turn)
    return bool(attempts) and attempts[0].get("accepted") is True


def _scene_state_violations(records: list[dict[str, Any]], expected: bool) -> int:
    return sum(
        attempt.get("scene_state") is not expected for record in records for attempt in _attempts(record["turn"])
    )


def _failed_turn(turn: dict[str, Any]) -> bool:
    return not _committed(turn)


def _logical_narration_attempts(turn: dict[str, Any]) -> int | float | None:
    if "narration_attempts" in turn:
        value = turn["narration_attempts"]
        return value if isinstance(value, (int, float)) and not isinstance(value, bool) else None
    attempts = turn.get("enforce_attempts")
    return len(attempts) if isinstance(attempts, list) else None


def _d5_violations(records: list[dict[str, Any]]) -> tuple[int, bool]:
    violations = 0
    insufficient = False
    for record in records:
        turn = record["turn"]
        if _failed_turn(turn) and (
            turn.get("places_after") != turn.get("places_before")
            or not isinstance(turn.get("error"), str)
            or not turn.get("error")
            or turn.get("narration") is not None
        ):
            violations += 1
        narration_attempts = _logical_narration_attempts(turn)
        verifier_requests = turn.get("verifier_requests")
        if narration_attempts is None:
            insufficient = True
        elif narration_attempts > 2:
            violations += 1
        if not isinstance(verifier_requests, (int, float)) or isinstance(verifier_requests, bool):
            insufficient = True
        elif verifier_requests > 2:
            violations += 1
    return violations, insufficient


def _count_summary(values: list[Any]) -> str:
    if not values:
        return "n/a"
    if any(not isinstance(value, (int, float)) or isinstance(value, bool) for value in values):
        return "insufficient evidence"
    numeric = [float(value) for value in values]
    return f"mean={sum(numeric) / len(numeric):.3f} range={min(numeric):.0f}–{max(numeric):.0f}"


def _http_prompt_values(records: list[dict[str, Any]]) -> list[Any] | None:
    if not any("narration_http_prompts" in record["turn"] for record in records):
        return None
    return [record["turn"].get("narration_http_prompts") for record in records]


def _d6_false_rejects(records: list[dict[str, Any]], labels: dict[str, Any]) -> int:
    count = 0
    for record in records:
        rejected = _rejected(record["turn"])
        if rejected and _rejected_label(labels, record["opaque_id"], 0) is False:
            count += 1
    return count


def _scores(records: list[dict[str, Any]]) -> list[float]:
    values = []
    for record in records:
        for attempt in _attempts(record["turn"]):
            for verdict in attempt.get("verdicts", ()):
                if isinstance(verdict, dict) and isinstance(verdict.get("score"), (int, float)):
                    values.append(float(verdict["score"]))
    return values


def _arm_records(
    off_rows: list[dict[str, Any]], on_rows: list[dict[str, Any]], key: dict[str, Any]
) -> dict[str, list[dict[str, Any]]]:
    records = {"off": _records(off_rows, "off"), "on": _records(on_rows, "on")}
    by_source = {record["source_id"]: record for values in records.values() for record in values}
    for opaque_id, value in key.items():
        by_source[value["source_id"]]["opaque_id"] = opaque_id
    return records


def _rate(successes: int, total: int) -> str:
    return f"{successes}/{total} ({successes / total:.3f})" if total else "0/0 (n/a)"


def _timing_lines(records: list[dict[str, Any]], arm: str) -> list[str]:
    timed = [
        (record["opaque_id"], record["turn"])
        for record in records
        if isinstance(record["turn"].get("call_timings"), list)
    ]
    if not timed:
        return []
    lines = [f"call timing ({arm.upper()}):"]
    for line in enforce_report._call_timing_information(timed):
        lines.append(f"  {line}" if line else "")
    return lines


def _report(
    off_rows: list[dict[str, Any]],
    on_rows: list[dict[str, Any]],
    labels: dict[str, Any],
    key: dict[str, Any],
    labels_sha256: str,
) -> tuple[str, bool]:
    arms = _arm_records(off_rows, on_rows, key)
    all_records = [*arms["off"], *arms["on"]]
    missing = _missing_labels(all_records, labels)
    if missing:
        raise ValueError("MISSING LABELS: " + ", ".join(missing))

    on = arms["on"]
    off = arms["off"]
    applicable = len(on_rows) == 20 and len(off_rows) == 20
    on_committed = sum(_committed(record["turn"]) for record in on)
    off_committed = sum(_committed(record["turn"]) for record in off)
    on_first = sum(_first_accepted(record["turn"]) for record in on)
    off_first = sum(_first_accepted(record["turn"]) for record in off)
    low, high = _wilson(on_committed, len(on))
    d3 = sum(
        any(_committed_tag(labels, record["opaque_id"], tag) is True for tag in TAGS)
        for record in on
        if _committed(record["turn"])
    )
    d4_on = _scene_state_violations(on, True)
    d4_off = _scene_state_violations(off, False)
    d5_on, d5_on_insufficient = _d5_violations(on)
    d5_off, d5_off_insufficient = _d5_violations(off)
    d6 = _d6_false_rejects(on, labels)
    d1_status = "PASS" if on_committed >= 18 else "FAIL"
    d2_status = "PASS" if on_first >= 16 else "FAIL"
    d3_status = "PASS" if d3 == 0 else "FAIL"
    d4_status = "PASS" if d4_on == 0 and d4_off == 0 else "FAIL"
    d5_status = (
        "insufficient evidence" if d5_on_insufficient or d5_off_insufficient else ("PASS" if d5_on == 0 else "FAIL")
    )
    d5_off_status = "insufficient evidence" if d5_off_insufficient else ("PASS" if d5_off == 0 else "FAIL")
    d6_status = "PASS" if d6 <= 1 else "FAIL"
    lines = [
        f"labels sha256: {labels_sha256}",
        "",
        f"D1: ON {d1_status} ({on_committed}/{len(on)} committed; "
        f"Wilson 95% interval {_number(low)}–{_number(high)}) | OFF {_rate(off_committed, len(off))}",
        f"D2: ON {d2_status} ({on_first}/{len(on)} first-attempt accepted) | OFF {_rate(off_first, len(off))}",
        f"D3: ON {d3_status} ({d3} committed narrations tagged with a drain change) | OFF n/a",
        f"D4: ON {d4_status} ({d4_on} scene-state violations) | OFF {d4_off} scene-state violations",
        f"D5: ON {d5_status} ({d5_on} violations) | OFF {d5_off_status} ({d5_off} violations)",
        f"D6: ON {d6_status} ({d6} rejected first attempts labelled not really deficient; limit 1) | OFF n/a",
        "",
        f"OFF commit rate: {_rate(off_committed, len(off))}",
        f"OFF first-attempt rate: {_rate(off_first, len(off))}",
    ]
    if not applicable:
        statuses = (d1_status, d2_status, d3_status, d4_status, d5_status, d6_status)
        smoke_lines = []
        for line in lines:
            updated = line
            for index, status in enumerate(statuses, start=1):
                prefix = f"D{index}: ON {status}"
                if line.startswith(prefix):
                    updated = line.replace(prefix, f"D{index}: ON not applicable (smoke) ({status})", 1)
                    break
            smoke_lines.append(updated)
        lines = smoke_lines
    for arm, records in (("off", off), ("on", on)):
        values = _scores(records)
        score_text = "n/a" if not values else f"n={len(values)} range={min(values):.3f}–{max(values):.3f}"
        logical_values = [_logical_narration_attempts(record["turn"]) for record in records]
        lines.extend(
            [
                f"verdict scores {arm.upper()}: {score_text}",
                f"logical narration attempts {arm.upper()}: {_count_summary(logical_values)}",
            ]
        )
        http_values = _http_prompt_values(records)
        if http_values is not None:
            lines.append(f"narration_http_prompts {arm.upper()}: {_count_summary(http_values)}")
        lines.extend(_timing_lines(records, arm))
    return "\n".join(lines) + "\n", all(
        status == "PASS" for status in (d1_status, d2_status, d3_status, d4_status, d5_status, d6_status)
    ) if applicable else True


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--sheets", action="store_true")
    mode.add_argument("--report", action="store_true")
    parser.add_argument("--rows-off", required=True, type=Path)
    parser.add_argument("--rows-on", required=True, type=Path)
    parser.add_argument("--labels", type=Path)
    parser.add_argument("--out", required=True, type=Path)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    try:
        off_rows = _load_json(args.rows_off)
        on_rows = _load_json(args.rows_on)
        if not isinstance(off_rows, list) or not isinstance(on_rows, list):
            raise TypeError("rows files must contain lists")
        if args.sheets:
            _write_sheets(off_rows, on_rows, args.out)
            return 0
        if args.labels is None:
            raise ValueError("--labels is required with --report")
        key_path = args.labels.parent / "blind_key.json"
        key = _load_json(key_path)
        labels = _load_json(args.labels)
        report, passed = _report(off_rows, on_rows, labels, key, _sha256(args.labels))
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(report, encoding="utf-8")
        return 0 if passed else 1
    except FileNotFoundError as exc:
        sys.stderr.write(f"Unable to build drain report: {exc}\n")
        return 2
    except (OSError, TypeError, ValueError, KeyError, json.JSONDecodeError) as exc:
        sys.stderr.write(f"Unable to build drain report: {exc}\n")
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
