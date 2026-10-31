"""Report the deterministic gates for the T9h hidden-clues smoke run."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

ROUTE = "observe_park_bench_1b"
COMMANDS = (
    "inspect the park bench",
    "look under the park bench",
    "search the park bench",
    "check the park bench",
    "look under the park bench",
    "inspect the storm drain",
)
CLUES = ("transit_card", "number_sequence", "michelle_photograph")
RECOVERY_KNOWLEDGE = "k_sl_1b_d_r1"
RECOVERY_FACT = "bench_clues_recovered"
INTERPRETATION_KNOWLEDGE = {
    "k_sl_1b_a_r1": "transport_route_identified",
    "k_sl_1b_a_r2": "brandon_face_known",
    "k_sl_1b_b_r1": "brandon_identified",
}
INTERPRETATION_FACTS = tuple(INTERPRETATION_KNOWLEDGE.values())
DRAIN_COMMAND = "inspect the storm drain"
REQUEST_BUDGET = {"narration_attempts": 2, "verifier_requests": 2}
CLUE_WORDS = {
    "transit_card": ("transit_card", "transit card", "transit token"),
    "number_sequence": ("number_sequence", "number sequence", "handwritten number sequence"),
    "michelle_photograph": (
        "michelle_photograph",
        "michelle photograph",
        "michelle's photograph",
        "photograph",
        "photo",
    ),
}


def _load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def _turns(replicate: dict[str, Any]) -> list[dict[str, Any]]:
    value = replicate.get("turns")
    return [turn for turn in value if isinstance(turn, dict)] if isinstance(value, list) else []


def _command(turn: dict[str, Any]) -> str:
    value = turn.get("input")
    return value.casefold() if isinstance(value, str) else ""


def _selected(turn: dict[str, Any]) -> list[str]:
    value = turn.get("selected_knowledge_ids")
    return [item for item in value if isinstance(item, str)] if isinstance(value, list) else []


def _committed(turn: dict[str, Any]) -> bool:
    return turn.get("turn_outcome") == "committed" and turn.get("narration") is not None


def _world_clues(turn: dict[str, Any]) -> tuple[bool | None, dict[str, tuple[Any, Any]]]:
    world = turn.get("world_after")
    if not isinstance(world, dict):
        return None, {}
    result: dict[str, tuple[Any, Any]] = {}
    for clue in CLUES:
        value = world.get(clue)
        if not isinstance(value, dict) or "parent" not in value or "hidden" not in value:
            return None, result
        result[clue] = (value["parent"], value["hidden"])
    return True, result


def _facts_recorded(turn: dict[str, Any]) -> bool:
    return isinstance(turn.get("story_facts_after"), dict)


def _fact_evidence(turn: dict[str, Any], fact: str) -> bool:
    if fact in _selected(turn):
        return True
    facts = turn.get("story_facts_after")
    return isinstance(facts, dict) and facts.get(fact) is True


def _clues_recovered(turn: dict[str, Any]) -> bool:
    facts = turn.get("story_facts_after")
    return isinstance(facts, dict) and facts.get(RECOVERY_FACT) is True


def _payload_text(values: list[Any]) -> str:
    return json.dumps(values, ensure_ascii=False, sort_keys=True, default=str).casefold()


def _opening_and_turn_zero_text(replicate: dict[str, Any]) -> tuple[str, str]:
    opening = replicate.get("opening")
    opening_values = []
    if isinstance(opening, dict):
        for key in ("narration", "prompts", "provider_responses", "engine_steps"):
            opening_values.append(opening.get(key))
    turns = _turns(replicate)
    turn_values = []
    if turns:
        for key in ("narration", "prompts", "provider_responses", "engine_steps"):
            turn_values.append(turns[0].get(key))
    return _payload_text(opening_values), _payload_text(turn_values)


def _clue_hits(text: str) -> list[str]:
    return [clue for clue, words in CLUE_WORDS.items() if any(word in text for word in words)]


def _cap_exception(turn: dict[str, Any]) -> bool:
    outcome = turn.get("turn_outcome")
    if outcome == "stopped_call_cap":
        return True
    error = turn.get("error")
    return isinstance(error, str) and ("callcap" in error.casefold() or "max-calls" in error.casefold())


def _digest_evidence(turn: dict[str, Any]) -> tuple[bool, bool]:
    before = turn.get("state_digest_before")
    after = turn.get("state_digest_after")
    present = isinstance(before, str) and isinstance(after, str)
    return present, present and before == after


def _record_id(replicate_index: int, turn_index: int) -> str:
    return f"r{replicate_index}t{turn_index}"


def _world_text(placements: dict[str, tuple[Any, Any]]) -> str:
    return ", ".join(
        f"{clue}={parent}/{'visible' if hidden is False else 'hidden'}" for clue, (parent, hidden) in placements.items()
    )


def _gate_s1(rows: list[dict[str, Any]]) -> tuple[str, list[str]]:
    failures: list[str] = []
    missing: list[str] = []
    evidence_lines: list[str] = []
    for replicate_index, replicate in enumerate(rows):
        turns = _turns(replicate)
        if len(turns) <= 1:
            missing.append(f"r{replicate_index}: find turn missing")
            continue
        find = turns[1]
        reasons = []
        if _command(find) != COMMANDS[1]:
            reasons.append("turn 1 command")
        if not _committed(find):
            reasons.append("find not committed")
        if not _facts_recorded(find):
            missing.append(f"r{replicate_index}t1: story_facts_after")
        if not _clues_recovered(find):
            reasons.append("recovery assertion missing")
        digest_present, _unchanged = _digest_evidence(find)
        if not digest_present:
            missing.append(f"r{replicate_index}t1: state digest")
        elif _unchanged:
            reasons.append("find digest unchanged")
        else:
            evidence_lines.append(f"r{replicate_index}t1: state digest changed")
        for turn_index, turn in enumerate(turns[1:], start=1):
            if _command(turn) == DRAIN_COMMAND:
                continue
            evidence, placements = _world_clues(turn)
            if evidence is None:
                missing.append(f"{_record_id(replicate_index, turn_index)}: clue world evidence")
                continue
            evidence_lines.append(f"{_record_id(replicate_index, turn_index)}: {_world_text(placements)}")
            if any(parent != "kristin" or hidden is not False for parent, hidden in placements.values()):
                reasons.append(f"{_record_id(replicate_index, turn_index)}: clue custody/visibility")
        if reasons:
            failures.append(f"r{replicate_index}: " + "; ".join(reasons))
    if missing:
        return "insufficient evidence", [*failures, *evidence_lines, *missing]
    return ("PASS" if not failures else "FAIL"), [*failures, *evidence_lines]


def _gate_s2(rows: list[dict[str, Any]]) -> tuple[str, list[str]]:
    failures: list[str] = []
    missing: list[str] = []
    evidence_lines: list[str] = []
    for replicate_index, replicate in enumerate(rows):
        opening, turn_zero = _opening_and_turn_zero_text(replicate)
        if not isinstance(replicate.get("opening"), dict):
            missing.append(f"r{replicate_index}: opening")
        for label, text in (("opening", opening), ("turn 0", turn_zero)):
            hits = _clue_hits(text)
            evidence_lines.append(f"r{replicate_index} {label}: hits={hits or 'none'}")
            if hits:
                failures.append(f"r{replicate_index} {label}: {', '.join(hits)}")
    evidence_lines.append("S2 note: private selector traffic is not separable in these rows")
    if missing:
        return "insufficient evidence", [*failures, *evidence_lines, *missing]
    return ("PASS" if not failures else "FAIL"), [*failures, *evidence_lines]


def _gate_s3(rows: list[dict[str, Any]]) -> tuple[str, list[str]]:
    failures: list[str] = []
    missing: list[str] = []
    evidence_lines: list[str] = []
    for replicate_index, replicate in enumerate(rows):
        turns = _turns(replicate)
        fact_values = []
        for turn_index, turn in enumerate(turns):
            if not _facts_recorded(turn):
                missing.append(f"{_record_id(replicate_index, turn_index)}: story_facts_after")
            fact_values.append(_clues_recovered(turn))
            if not isinstance(turn.get("selected_knowledge_ids"), list):
                missing.append(f"{_record_id(replicate_index, turn_index)}: selected_knowledge_ids")
        assertions = [
            index
            for index, recovered in enumerate(fact_values)
            if recovered and (index == 0 or not fact_values[index - 1])
        ]
        evidence_lines.append(f"r{replicate_index}: recovery fact transitions at {assertions}")
        if assertions != [1]:
            failures.append(f"r{replicate_index}: recovery fact transitions at {assertions}")
        repeated = [index for index, turn in enumerate(turns[2:], start=2) if RECOVERY_KNOWLEDGE in _selected(turn)]
        if repeated:
            failures.append(f"r{replicate_index}: recovery delivery repeated at {repeated}")
        if len(turns) <= 1:
            missing.append(f"r{replicate_index}: turns after find")
            continue
        evidence, find_placements = _world_clues(turns[1])
        if evidence is None:
            missing.append(f"r{replicate_index}t1: clue world evidence")
            continue
        for turn_index, turn in enumerate(turns[2:], start=2):
            if _command(turn) == DRAIN_COMMAND:
                continue
            evidence, placements = _world_clues(turn)
            if evidence is None:
                missing.append(f"{_record_id(replicate_index, turn_index)}: clue world evidence")
            elif placements != find_placements:
                failures.append(f"{_record_id(replicate_index, turn_index)}: custody changed after find")
                evidence_lines.append(f"{_record_id(replicate_index, turn_index)}: custody changed")
            else:
                evidence_lines.append(f"{_record_id(replicate_index, turn_index)}: custody unchanged")
    if missing:
        return "insufficient evidence", [*failures, *evidence_lines, *missing]
    return ("PASS" if not failures else "FAIL"), [*failures, *evidence_lines]


def _gate_s4(rows: list[dict[str, Any]]) -> tuple[str, list[str]]:
    failures: list[str] = []
    missing: list[str] = []
    evidence_lines: list[str] = []
    for replicate_index, replicate in enumerate(rows):
        turns = _turns(replicate)
        if len(turns) <= 1:
            missing.append(f"r{replicate_index}: find turn")
            continue
        for turn_index, turn in enumerate(turns[:2]):
            if not _facts_recorded(turn):
                missing.append(f"{_record_id(replicate_index, turn_index)}: story_facts_after")
            selected = _selected(turn)
            found = []
            for knowledge_id, fact in INTERPRETATION_KNOWLEDGE.items():
                if knowledge_id in selected or _fact_evidence(turn, fact):
                    failures.append(f"{_record_id(replicate_index, turn_index)}: {fact}")
                    found.append(fact)
            evidence_lines.append(f"{_record_id(replicate_index, turn_index)}: interpretation facts={found or 'none'}")
        if not any(isinstance(turn.get("selected_knowledge_ids"), list) for turn in turns[:2]):
            missing.append(f"r{replicate_index}: find fact evidence")
    if missing:
        return "insufficient evidence", [*failures, *evidence_lines, *missing]
    return ("PASS" if not failures else "FAIL"), [*failures, *evidence_lines]


def _gate_s5(rows: list[dict[str, Any]]) -> tuple[str, list[str], list[str]]:
    failures: list[str] = []
    missing: list[str] = []
    caps: list[str] = []
    evidence_lines: list[str] = []
    for replicate_index, replicate in enumerate(rows):
        for turn_index, turn in enumerate(_turns(replicate)):
            record_id = _record_id(replicate_index, turn_index)
            if _command(turn) == DRAIN_COMMAND:
                continue
            if _cap_exception(turn):
                caps.append(record_id)
                continue
            if turn.get("turn_outcome") != "rejected":
                continue
            present, unchanged = _digest_evidence(turn)
            if not present:
                missing.append(f"{record_id}: state digest")
            elif "state_unchanged" not in turn:
                missing.append(f"{record_id}: state_unchanged")
            elif turn.get("state_unchanged") is not True or not unchanged:
                failures.append(f"{record_id}: rejected turn changed state")
                evidence_lines.append(f"{record_id}: rejected state_unchanged={turn.get('state_unchanged')}")
            else:
                evidence_lines.append(f"{record_id}: rejected state_unchanged=True digest_equal=True")
    if not evidence_lines and not missing and not failures:
        evidence_lines.append("ordinary rejected turns: none")
    if missing:
        return "insufficient evidence", [*failures, *evidence_lines, *missing], caps
    return ("PASS" if not failures else "FAIL"), [*failures, *evidence_lines], caps


def _latency_lines(rows: list[dict[str, Any]]) -> list[str]:
    lines = ["latency (10 s target; informational):"]
    for replicate_index, replicate in enumerate(rows):
        for turn_index, turn in enumerate(_turns(replicate)):
            value = turn.get("turn_elapsed_s")
            if not isinstance(value, (int, float)):
                lines.append(f"  {_record_id(replicate_index, turn_index)}: insufficient evidence")
            else:
                status = "over" if value > 10 else "within"
                lines.append(f"  {_record_id(replicate_index, turn_index)}: {value:.3f}s ({status})")
    return lines


def _request_budgets(turns: list[dict[str, Any]]) -> list[tuple[str, int]]:
    budgets = list(REQUEST_BUDGET.items())
    extra_fields = []
    for turn in turns:
        for key in turn:
            normalized = key.casefold().replace("-", "_") if isinstance(key, str) else ""
            if (
                key not in REQUEST_BUDGET
                and ("item" in normalized or "recovery" in normalized)
                and ("request" in normalized or "call" in normalized)
                and key not in extra_fields
            ):
                extra_fields.append(key)
    return [*budgets, *((key, 2) for key in extra_fields)]


def _request_lines(rows: list[dict[str, Any]]) -> tuple[str, list[str]]:
    turns = [turn for replicate in rows for turn in _turns(replicate) if _command(turn) != DRAIN_COMMAND]
    budgets = _request_budgets(turns)
    changed = False
    insufficient = False
    detail_lines = []
    for replicate_index, replicate in enumerate(rows):
        for turn_index, turn in enumerate(_turns(replicate)):
            if _command(turn) == DRAIN_COMMAND:
                continue
            values = [turn.get(key) for key, _limit in budgets]
            if not all(isinstance(value, (int, float)) for value in values):
                insufficient = True
                detail_lines.append(f"  {_record_id(replicate_index, turn_index)}: insufficient evidence")
                continue
            if any(value > limit for value, (_key, limit) in zip(values, budgets, strict=True)):
                changed = True
            detail_lines.append(
                f"  {_record_id(replicate_index, turn_index)}: "
                + ", ".join(f"{key}={turn[key]}/{limit}" for key, limit in budgets)
            )
    if not turns or not budgets:
        insufficient = True
    if changed:
        status = "FAIL"
    elif insufficient:
        status = "insufficient evidence"
    else:
        status = "PASS"
    lines = [
        f"S6: {status} | unchanged against prior smoke budget "
        + ", ".join(f"{key} <= {value}" for key, value in budgets)
    ]
    if len(budgets) == len(REQUEST_BUDGET):
        detail_lines.append("S6 note: item-facts and shared-recovery request counts are not recorded")
    return status, [*lines, *detail_lines]


def _drain_lines(rows: list[dict[str, Any]]) -> list[str]:
    lines = ["drain outcomes (turn 5; excluded from S1-S6):"]
    count = 0
    for replicate_index, replicate in enumerate(rows):
        for turn_index, turn in enumerate(_turns(replicate)):
            if _command(turn) != DRAIN_COMMAND:
                continue
            count += 1
            outcome = turn.get("turn_outcome")
            outcome_text = outcome if isinstance(outcome, str) and outcome in {"committed", "rejected"} else "(missing)"
            lines.append(
                f"  {_record_id(replicate_index, turn_index)}: "
                f"outcome={outcome_text} error={turn.get('error', '(none)')}"
            )
    if count == 0:
        lines.append("  none")
    return lines


def _incomplete(summary: dict[str, Any], rows: list[dict[str, Any]], expected_replicates: int) -> list[str]:
    reasons = []
    if "stopped_reason" not in summary:
        reasons.append("summary stopped_reason missing")
    elif summary.get("stopped_reason") is not None:
        reasons.append(f"stopped_reason={summary.get('stopped_reason')}")
    requested = summary.get("replicates_requested")
    if "replicates_requested" not in summary:
        reasons.append("replicates_requested: insufficient evidence")
    elif requested != expected_replicates:
        reasons.append(f"replicates_requested={requested}/{expected_replicates}")
    completed = summary.get("replicates_completed")
    if requested != expected_replicates or completed != expected_replicates:
        reasons.append("replicates incomplete")
    if completed != expected_replicates:
        reasons.append(f"replicates_completed={completed}/{expected_replicates}")
    if len(rows) != expected_replicates:
        reasons.append(f"rows={len(rows)}/{expected_replicates}")
    for replicate_index, replicate in enumerate(rows):
        if _route(replicate) != ROUTE:
            reasons.append(f"r{replicate_index}: route mismatch")
        if len(_turns(replicate)) != len(COMMANDS):
            reasons.append(f"r{replicate_index}: turns={len(_turns(replicate))}/6")
    return reasons


def _route(replicate: dict[str, Any]) -> str | None:
    value = replicate.get("route")
    return value if isinstance(value, str) else None


def _spend(rows_dir: Path) -> str:
    candidates = (rows_dir / "spent.json", rows_dir.parent / "spent.json")
    for path in candidates:
        if not path.is_file():
            continue
        value = _load_json(path)
        if isinstance(value, dict):
            spent = value.get("spent_micro_usd")
            maximum = value.get("max_usd")
            if isinstance(spent, (int, float)):
                result = f"${spent / 1_000_000:.6f}"
                if isinstance(maximum, (int, float)):
                    result += f" / cap ${maximum:.2f}"
                return result
    return "insufficient evidence"


def report(rows_dir: Path, expected_replicates: int = 3) -> tuple[str, bool]:
    rows = _load_json(rows_dir / "rows.json")
    summary = _load_json(rows_dir / "summary.json")
    if not isinstance(rows, list) or not all(isinstance(row, dict) for row in rows):
        raise TypeError("rows.json must contain a list of replicate objects")
    if not isinstance(summary, dict):
        raise TypeError("summary.json must contain an object")

    statuses = [_gate_s1(rows), _gate_s2(rows), _gate_s3(rows), _gate_s4(rows)]
    s5, s5_details, cap_rows = _gate_s5(rows)
    incomplete = _incomplete(summary, rows, expected_replicates)
    lines = [
        f"route: {summary.get('route', ROUTE)}",
        "replicates: "
        f"{summary.get('replicates_completed', len(rows))}/{expected_replicates}; "
        f"turns: {summary.get('turns_recorded', 'unknown')}",
    ]
    for number, (status, details) in enumerate(statuses, start=1):
        default = {
            1: "all three clues recovered and carried by Kristin",
            2: "no clue names in opening or turn 0 narration/payload",
            3: "one recovery assertion; custody unchanged after find",
            4: "no interpretation facts asserted by the find",
        }[number]
        lines.append(f"S{number}: {status} | " + ("; ".join(details) if details else default))
    lines.append(
        f"S5: {s5} | " + ("; ".join(s5_details) if s5_details else "ordinary rejected turns restored exact state")
    )
    lines.append(
        "call-cap exceptions (separate from ordinary rejections): " + (", ".join(cap_rows) if cap_rows else "none")
    )
    s6, s6_lines = _request_lines(rows)
    lines.extend(s6_lines)
    lines.extend(_drain_lines(rows))
    lines.extend(_latency_lines(rows))
    lines.append(f"spend: {_spend(rows_dir)}")
    if incomplete:
        lines.append("run: incomplete or stopped | " + "; ".join(incomplete))
    else:
        lines.append("run: complete")
    passed = not incomplete and all(
        status == "PASS" for status, _details in [*statuses, (s5, s5_details), (s6, s6_lines)]
    )
    return "\n".join(lines) + "\n", passed


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("rows_dir", nargs="?", type=Path)
    parser.add_argument("--rows", dest="rows_option", type=Path)
    parser.add_argument("--out", type=Path)
    parser.add_argument("--expected-replicates", type=int, default=3)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    rows_dir = args.rows_option or args.rows_dir
    if rows_dir is None:
        sys.stderr.write("rows directory is required\n")
        return 2
    try:
        text, passed = report(rows_dir, expected_replicates=args.expected_replicates)
        print(text, end="")
        if args.out is not None:
            args.out.parent.mkdir(parents=True, exist_ok=True)
            args.out.write_text(text, encoding="utf-8")
        return 0 if passed else 1
    except (OSError, TypeError, ValueError, json.JSONDecodeError) as exc:
        sys.stderr.write(f"Unable to build hidden-clues smoke report: {exc}\n")
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
