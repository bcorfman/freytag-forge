"""Report blind observation labels against verifier shadow records."""

import argparse
import json
import sys
from pathlib import Path
from typing import Any

VERDICTS = ("accept", "reject", "uncertain", "unavailable")
REFIND_COMMAND = "feel under the drawer"
SEAT_COMMAND = "inspect the passenger seat"


def _load_json(path: str) -> Any:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def _turn_id(replicate_index: int, turn_index: int) -> str:
    return f"r{replicate_index}t{turn_index}"


def _turns(rows: list[dict[str, Any]]):
    for replicate_index, replicate in enumerate(rows):
        for turn_index, turn in enumerate(replicate.get("turns", ())):
            yield _turn_id(replicate_index, turn_index), turn


def _observation_turns(rows: list[dict[str, Any]]):
    for turn_id, turn in _turns(rows):
        if turn.get("observation_relations") is not None and turn.get("error") is None:
            yield turn_id, turn


def _transition_turns(rows: list[dict[str, Any]]):
    for replicate_index, replicate in enumerate(rows):
        previous_scene = None
        has_previous = False
        for turn_index, turn in enumerate(replicate.get("turns", ())):
            scene = turn.get("scene")
            if has_previous and scene != previous_scene:
                yield _turn_id(replicate_index, turn_index), turn
            previous_scene = scene
            has_previous = True


def _relation_text(relation: dict[str, Any]) -> str:
    return " | ".join(str(relation.get(field) or "") for field in ("thing", "place", "holder"))


def _compact_json(value: Any) -> str:
    return json.dumps(value, separators=(",", ":"))


def _sheet(rows: list[dict[str, Any]]) -> str:
    blocks = ["# Blind observation sheet", ""]
    skipped = []
    for turn_id, turn in _turns(rows):
        relations = turn.get("observation_relations")
        if relations is None:
            skipped.append(turn_id)
        if relations is None or turn.get("error") is not None:
            continue
        request = turn.get("observation_request")
        request_kind = request.get("kind") if isinstance(request, dict) else None
        request_focus = request.get("focus") if isinstance(request, dict) else None
        blocks.extend(
            [
                f"## {turn_id}",
                "",
                f"Command: {turn.get('input', '')}",
                "",
                f"places_before: {_compact_json(turn.get('places_before'))}",
                f"places_after: {_compact_json(turn.get('places_after'))}",
                f"Request kind: {request_kind}",
                f"Request focus: {request_focus}",
                "",
                "Narration:",
                "",
                str(turn.get("narration") or ""),
                "",
                "Relations:",
                "",
            ]
        )
        if relations:
            blocks.extend(f"{number}. {_relation_text(relation)}" for number, relation in enumerate(relations, start=1))
        else:
            blocks.append("none")
        blocks.append("")
    blocks.extend(["## Skipped turns with no relations", ""])
    if skipped:
        blocks.extend(f"- {turn_id}" for turn_id in skipped)
    else:
        blocks.append("- None")
    blocks.append("")
    return "\n".join(blocks)


def _labels_template(rows: list[dict[str, Any]]) -> str:
    template = {
        turn_id: {
            **{str(number): None for number, _ in enumerate(turn["observation_relations"], 1)},
            "acceptable": None,
            "refind": None,
            "invented_object": None,
        }
        for turn_id, turn in _observation_turns(rows)
    }
    return json.dumps(template, indent=2) + "\n"


def _label_for(labels: dict[str, Any], turn_id: str, number: int) -> bool | None:
    turn_labels = labels.get(turn_id)
    if not isinstance(turn_labels, dict):
        return None
    value = turn_labels.get(str(number))
    return value if isinstance(value, bool) else None


def _acceptable_for(labels: dict[str, Any], turn_id: str) -> bool | None:
    turn_labels = labels.get(turn_id)
    if not isinstance(turn_labels, dict):
        return None
    value = turn_labels.get("acceptable")
    return value if isinstance(value, bool) else None


def _tag_for(labels: dict[str, Any], turn_id: str, name: str) -> bool | None:
    turn_labels = labels.get(turn_id)
    if not isinstance(turn_labels, dict):
        return None
    value = turn_labels.get(name)
    return value if isinstance(value, bool) else None


def _verdict_map(shadow: dict[str, Any] | None) -> dict[str, dict[str, Any]]:
    if not isinstance(shadow, dict):
        return {}
    result = {}
    for verdict in shadow.get("verdicts", ()):
        if isinstance(verdict, dict) and verdict.get("thing") is not None:
            result[str(verdict["thing"])] = verdict
    return result


def _verdict(shadow: dict[str, Any] | None, relation: dict[str, Any]) -> tuple[str, Any]:
    verdict_data = _verdict_map(shadow).get(str(relation.get("thing")))
    if verdict_data is None:
        return "unavailable", None
    verdict = verdict_data.get("verdict")
    if verdict not in VERDICTS:
        return "unavailable", verdict_data.get("score")
    return verdict, verdict_data.get("score")


def _percentile(values: list[float], fraction: float) -> float | None:
    if not values:
        return None
    ordered = sorted(values)
    position = (len(ordered) - 1) * fraction
    lower = int(position)
    upper = min(lower + 1, len(ordered) - 1)
    weight = position - lower
    return ordered[lower] + (ordered[upper] - ordered[lower]) * weight


def _number(value: Any) -> str:
    if value is None:
        return "None"
    return str(value)


def _normalise_command(value: Any) -> str:
    if not isinstance(value, str):
        return ""
    command = value.casefold().strip()
    if command.endswith("."):
        command = command[:-1].rstrip()
    return command


def _seat_is_empty(turn: dict[str, Any]) -> bool:
    places_before = turn.get("places_before")
    request = turn.get("observation_request")
    focus = request.get("focus") if isinstance(request, dict) else None
    if isinstance(places_before, dict) and focus is not None:
        return not any(parent == focus for parent in places_before.values())
    # If the placement map or focus is unavailable, the recorded empty-seat
    # outcome is the zero-relation observation.
    return turn.get("observation_relations") == []


def _defect_status(count: int, true_count: int, minimum: int) -> str:
    if count < minimum:
        return "INCONCLUSIVE"
    return "PASS" if true_count <= 1 else "FAIL"


def _join(rows: list[dict[str, Any]], labels: dict[str, Any]) -> tuple[str, list[str]]:
    observations = list(_observation_turns(rows))
    missing = []
    for turn_id, turn in observations:
        if _acceptable_for(labels, turn_id) is None:
            missing.append(f"{turn_id} acceptable")
        for number, _ in enumerate(turn["observation_relations"], start=1):
            if _label_for(labels, turn_id, number) is None:
                missing.append(f"{turn_id} relation {number}")
    if missing:
        return "", missing

    confusion = {(verdict, label): 0 for verdict in VERDICTS for label in (True, False)}
    false_accepts = []
    strict_rejections = 0
    true_labels = 0
    relation_count = 0
    good_turns = 0
    good_turn_rejections = 0
    mixed_turns = 0
    mixed_turn_rejections = 0
    acceptable_turns = 0
    acceptable_turn_rejections = 0
    acceptable_rejected_turns = []
    turns_without_shadow = 0
    elapsed = []
    requests = 0

    for turn_id, turn in observations:
        relations = turn["observation_relations"]
        shadow = turn.get("observation_shadow")
        if not isinstance(shadow, dict):
            turns_without_shadow += 1
        else:
            elapsed_value = shadow.get("elapsed_s")
            if isinstance(elapsed_value, (int, float)):
                elapsed.append(float(elapsed_value))
            request_value = shadow.get("requests")
            if isinstance(request_value, (int, float)):
                requests += request_value

        turn_would_reject = bool(relations) and (not isinstance(shadow, dict) or shadow.get("outcome") != "ok")
        acceptable_rejections = []
        all_true = True
        for number, relation in enumerate(relations, start=1):
            label = _label_for(labels, turn_id, number)
            verdict, score = _verdict(shadow, relation)
            confusion[(verdict, label)] += 1
            relation_count += 1
            if label:
                true_labels += 1
                if verdict != "accept":
                    strict_rejections += 1
            else:
                all_true = False
                if verdict == "accept":
                    false_accepts.append((turn_id, turn.get("input", ""), relation.get("thing", ""), score))
            if verdict != "accept":
                turn_would_reject = True
                if _acceptable_for(labels, turn_id) is True:
                    acceptable_rejections.append((str(relation.get("thing") or ""), score))
        acceptable = _acceptable_for(labels, turn_id)
        if acceptable is True:
            if (
                relations
                and (not isinstance(shadow, dict) or shadow.get("outcome") != "ok")
                and not acceptable_rejections
            ):
                outcome = shadow.get("outcome") if isinstance(shadow, dict) else "missing"
                acceptable_rejections.append((f"shadow outcome {outcome}", None))
            acceptable_turns += 1
            if acceptable_rejections:
                acceptable_turn_rejections += 1
                acceptable_rejected_turns.append((turn_id, turn.get("input", ""), acceptable_rejections))
        if all_true:
            good_turns += 1
            if turn_would_reject:
                good_turn_rejections += 1
        else:
            mixed_turns += 1
            if turn_would_reject:
                mixed_turn_rejections += 1

    p50 = _percentile(elapsed, 0.50)
    p95 = _percentile(elapsed, 0.95)
    good_rate = good_turn_rejections / good_turns if good_turns else 0.0
    strict_rate = strict_rejections / true_labels if true_labels else 0.0
    false_rate = len(false_accepts) / relation_count if relation_count else 0.0
    acceptable_rate = acceptable_turn_rejections / acceptable_turns if acceptable_turns else None
    upper_bound = 1 - 0.05 ** (1 / relation_count) if relation_count else None
    upper_bound_text = "n/a" if upper_bound is None else f"{upper_bound:.6f}"
    acceptable_rate_text = "n/a" if acceptable_rate is None else f"{acceptable_rate:.6f}"

    failures = []
    if false_accepts:
        failures.append("false accepts == 0")
    if not good_turns or good_rate > 0.10:
        failures.append("good-turn strict reject rate <= 0.10")
    if acceptable_rate is not None and acceptable_rate > 0.10:
        failures.append("2b acceptable-turn enforcement reject rate <= 0.10")
    if p95 is None or p95 > 2.0:
        failures.append("verifier p95 elapsed_s <= 2.0")
    if relation_count < 30:
        failures.append("at least 30 labelled relations")

    transition_turns = list(_transition_turns(rows))
    transition_failures = []
    for turn_id, turn in transition_turns:
        shadow = turn.get("observation_shadow")
        if shadow is not None and not (
            isinstance(shadow, dict)
            and shadow.get("requirement_dropped") == "scene_or_area_changed"
            and shadow.get("requests") == 0
        ):
            transition_failures.append(turn_id)
    if transition_failures:
        failures.append("5 scene-transition turns drop the requirement")

    held_item_counts = {True: 0, False: 0}
    for turn_id, turn in observations:
        for number, relation in enumerate(turn["observation_relations"], start=1):
            if relation.get("holder") not in (None, ""):
                held_item_counts[_label_for(labels, turn_id, number)] += 1

    refind_count = 0
    refind_true = 0
    invented_count = 0
    invented_true = 0
    for turn_id, turn in observations:
        command = _normalise_command(turn.get("input"))
        if command == REFIND_COMMAND:
            tag = _tag_for(labels, turn_id, "refind")
            if tag is not None:
                refind_count += 1
                refind_true += tag
        if command == SEAT_COMMAND and _seat_is_empty(turn):
            tag = _tag_for(labels, turn_id, "invented_object")
            if tag is not None:
                invented_count += 1
                invented_true += tag
    refind_status = _defect_status(refind_count, refind_true, 15)
    invented_status = _defect_status(invented_count, invented_true, 6)
    verifier_status = "FAIL" if failures else "PASS"
    product_status = (
        "FAIL"
        if "FAIL" in (refind_status, invented_status)
        else ("INCONCLUSIVE" if "INCONCLUSIVE" in (refind_status, invented_status) else "PASS")
    )

    lines = ["# Joined observation report", "", "## Gate", ""]
    lines.append("GATE: PASS" if not failures else f"GATE: FAIL ({'; '.join(failures)})")
    if acceptable_turns == 0:
        lines.append("2b: INCONCLUSIVE (n=0 acceptable turns)")
    elif acceptable_rate <= 0.10:
        lines.append(f"2b: PASS ({acceptable_turn_rejections}/{acceptable_turns} = {acceptable_rate_text} <= 0.10)")
    else:
        lines.append(f"2b: FAIL ({acceptable_turn_rejections}/{acceptable_turns} = {acceptable_rate_text} > 0.10)")
    lines.extend(
        [
            "",
            "## Rates",
            "",
            f"false accepts: {len(false_accepts)}",
            f"strict rejections: {strict_rejections}",
            f"false accept rate: {len(false_accepts)}/{relation_count} = {false_rate:.6f} (n={relation_count})",
            f"strict reject rate: {strict_rejections}/{true_labels} = {strict_rate:.6f} (n={true_labels})",
            f"good-turn strict reject rate: {good_turn_rejections}/{good_turns} = {good_rate:.6f} (n={good_turns})",
            (
                f"2b acceptable-turn enforcement reject rate: "
                f"{acceptable_turn_rejections}/{acceptable_turns} = "
                f"{acceptable_rate_text} (n={acceptable_turns})"
            ),
            f"zero-false-accept upper bound: {upper_bound_text} using 1 - 0.05**(1/n), n={relation_count}",
            "",
            "## Confusion",
            "",
            "| verdict | label true | label false |",
            "| --- | ---: | ---: |",
        ]
    )
    lines.extend(
        f"| {verdict} | {confusion[(verdict, True)]} | {confusion[(verdict, False)]} |" for verdict in VERDICTS
    )
    lines.extend(["", "## FALSE ACCEPTS", ""])
    if false_accepts:
        lines.extend(
            f"- {turn_id}: command={command}; thing={thing}; score={_number(score)}"
            for turn_id, command, thing, score in false_accepts
        )
    else:
        lines.append("- None")
    lines.extend(
        [
            "",
            "## ACCEPTABLE TURNS REJECTED BY ENFORCEMENT",
            "",
            "| id | command | rejected things with scores |",
            "| --- | --- | --- |",
        ]
    )
    if acceptable_rejected_turns:
        lines.extend(
            f"| {turn_id} | {command} | {', '.join(f'{thing} ({_number(score)})' for thing, score in rejected)} |"
            for turn_id, command, rejected in acceptable_rejected_turns
        )
    else:
        lines.append("- None")
    lines.extend(
        [
            "",
            "## Turn outcomes",
            "",
            f"good turns would_reject: {good_turn_rejections}/{good_turns} (n={good_turns})",
            f"mixed turns would_reject: {mixed_turn_rejections}/{mixed_turns} (n={mixed_turns})",
            f"turns without shadow record: {turns_without_shadow}",
            "",
            "## Verifier timing",
            "",
            f"p50 elapsed_s: {_number(p50) if p50 is None else f'{p50:.3f}'}",
            f"p95 elapsed_s: {_number(p95) if p95 is None else f'{p95:.3f}'}",
            f"requests: {requests}",
            f"labelled relations: {relation_count}",
            "",
        ]
    )
    lines.extend(
        [
            "## Sample 2 clauses",
            "",
            (
                "5 scene-transition turns drop the requirement: "
                + (
                    "INCONCLUSIVE (n=0)"
                    if not transition_turns
                    else (
                        f"FAIL ({', '.join(transition_failures)})"
                        if transition_failures
                        else f"PASS ({len(transition_turns)}/{len(transition_turns)})"
                    )
                )
            ),
            "",
            "## 6 held-item mention relations",
            "",
            "| hand label | count |",
            "| --- | ---: |",
            f"| true | {held_item_counts[True]} |",
            f"| false | {held_item_counts[False]} |",
            "",
            (f"7 re-find of the held card: {refind_status} (n={refind_count}, refind true={refind_true})"),
            (
                f"8 invented object on the empty seat: {invented_status} "
                f"(n={invented_count}, invented_object true={invented_true})"
            ),
            "",
            f"verifier gate (clauses 1 to 6): {verifier_status}",
            f"product-defect gate (clauses 7 and 8): {product_status}",
            "",
        ]
    )
    return "\n".join(lines), []


def _write_or_print(text: str, output_path: str | None) -> None:
    if output_path is None:
        sys.stdout.write(text)
    else:
        Path(output_path).write_text(text, encoding="utf-8")


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="command", required=True)

    sheet = subparsers.add_parser("sheet")
    sheet.add_argument("rows_json")
    sheet.add_argument("--out")

    template = subparsers.add_parser("labels-template")
    template.add_argument("rows_json")

    join = subparsers.add_parser("join")
    join.add_argument("rows_json")
    join.add_argument("labels_json")
    join.add_argument("--out")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    try:
        rows = _load_json(args.rows_json)
        if args.command == "sheet":
            _write_or_print(_sheet(rows), args.out)
            return 0
        if args.command == "labels-template":
            _write_or_print(_labels_template(rows), None)
            return 0
        labels = _load_json(args.labels_json)
        report, missing = _join(rows, labels)
        if missing:
            sys.stderr.write("Missing or null labels: " + ", ".join(missing) + "\n")
            return 2
        _write_or_print(report, args.out)
        return 0
    except (OSError, TypeError, ValueError, KeyError, json.JSONDecodeError) as exc:
        sys.stderr.write(f"Unable to build report: {exc}\n")
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
