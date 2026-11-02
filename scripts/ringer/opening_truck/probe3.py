"""Offline-first 1A opening and truck-feedback probe, revision 3."""

from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path
from typing import Any

from scripts.ringer.opening_truck.probe import (
    _canonical_hash,
    _diff,
    _offline_worker_environment,
    _opening_request,
    _quota_row,
    _record,
    _validate_live_guard,
)
from scripts.ringer.opening_truck.probe2 import (
    REACH_LINE,
    _arm_one_for_command,
    _assert_only_added,
    _check_control,
    _control_request,
    _insert_after_driver_seat,
)
from scripts.ringer.transcript_1a.boarding_probe import (
    CallCapExceeded,
    CallCounter,
    QuotaExceeded,
    _send_narrator,
    _write_json,
)

ROOT = Path(__file__).resolve().parents[3]
WORKER_PLACEHOLDER = "https://w.example"
DEFAULT_MAX_CALLS = 80
TOTAL_CALLS = 70
OPENING_COMMANDS = ("head out to the truck", "go to the truck")
Q1_ACTIONS = {
    "q1_arm3": "- Kristin looks around from the driver's seat.",
    "q1_arm4": "- Kristin takes in what she can see and reach from the driver's seat.",
}
Q2_TRUCK_LINE = "- Kristin's truck. Place: outside the house."
Q3_LINES = (
    "- Kristin has already stepped inside and stands in Michelle's kitchen, beside the forced back door.",
    "- The workstation is across the kitchen from the back door. Its chair lies on its side in front of it.",
    "- Michelle's phone lies on the kitchen floor.",
    "- The KMS cuts in the drawer front are pale and clean. They are Kristin's own initials, "
    "carved into Michelle's workstation.",
)


def _no_boarding_jev(_state: object, questions: object) -> dict[str, dict[str, float]]:
    """Use the product's other scripted routes while forcing every boarding false."""

    state = _state if isinstance(_state, dict) else {}
    command = str(state.get("command", "")).lower()
    answers: dict[str, dict[str, float]] = {}
    for key in questions if isinstance(questions, dict) else ():
        if key in {"boards_vehicle", "only_boards_vehicle"}:
            yes = False
        elif key == "searches_underneath":
            yes = "gap" in command
        elif key == "opens_container":
            yes = "open" in command and "drawer" in command
        else:
            yes = False
        answers[str(key)] = {"noul": 1.0 if yes else 0.0}
    return answers


def _new_product_replay(boarding_commands: tuple[str, ...]) -> tuple[Any, Any, Any, list[dict[str, str]]]:
    """Build a product replay with offline dispatch and no boarding answers."""

    from storygame.runtime.capture import WorldCapture, build_capture_provider
    from storygame.runtime.engine import RuntimeEngine
    from storygame.runtime.state import RuntimeState
    from storygame.story_package.loader import load_story_package

    package = load_story_package(ROOT / "data/stories/continuity-initiative")
    state = RuntimeState.bootstrap(package)
    provider = build_capture_provider(state)
    provider.semantic_ask = _no_boarding_jev
    provider._request_item_facts = lambda _payload: {"refers": [], "same_as": {}}
    captured: list[dict[str, str]] = []

    def dispatch(system: str, user: dict[str, object]) -> dict[str, object]:
        captured.append({"system": system, "user": provider._section_user_prompt(user)})
        return {
            "segments": [{"kind": "narration", "text": "Offline probe narration."}],
            "selected_knowledge_ids": [],
        }

    provider._dispatch = dispatch

    class ProbeWorldCapture(WorldCapture):
        def before_turn(self, command: str) -> dict[str, Any]:
            record = super().before_turn(command)
            if command in boarding_commands:
                self.provider.command_consumed = False
            return record

    capture = ProbeWorldCapture(provider, _no_boarding_jev)
    engine = RuntimeEngine(state, provider, capture=capture)
    return package, provider, engine, captured


def _q2_control_request() -> dict[str, str]:
    command = "go out to the truck"
    with _offline_worker_environment():
        _package, _provider, engine, captured = _new_product_replay((command,))
        for route_command in ("open the drawer", "feel in the gap", command):
            engine.turn(route_command)
    matching = [prompt for prompt in captured if f"- {command}" in prompt["user"]]
    if not matching:
        raise RuntimeError("product replay did not produce the unboarded narrator request")
    request = matching[-1]
    user = request["user"]
    if f"- {command}" not in user or "Already done:" in user:
        raise RuntimeError("Q2 control contains a boarding marker")
    if any(line.startswith("- Kristin's truck. Place") for line in user.splitlines()):
        raise RuntimeError("Q2 control unexpectedly contains a truck place line")
    return request


def _insert_player_action(user: str, action_line: str) -> str:
    lines = user.splitlines(keepends=True)
    player_headers = [index for index, line in enumerate(lines) if line.rstrip("\r\n") == "PLAYER:"]
    if len(player_headers) != 1:
        raise RuntimeError("Q1 arm needs one PLAYER section")
    player_start = player_headers[0] + 1
    player_end = len(lines)
    for index in range(player_start, len(lines)):
        if lines[index].rstrip("\r\n").endswith(":") and not lines[index].startswith("-"):
            player_end = index
            break
    place_indexes = [
        index
        for index in range(player_start, player_end)
        if lines[index].rstrip("\r\n") == "- Kristin. Place: driver's seat."
    ]
    already_indexes = [index for index in range(player_start, player_end) if lines[index].startswith("- Already done:")]
    if len(place_indexes) != 1 or len(already_indexes) != 1 or place_indexes[0] >= already_indexes[0]:
        raise RuntimeError("Q1 arm needs an ordered driver's-seat place and Already done line")
    index = place_indexes[0]
    newline = "\r\n" if lines[index].endswith("\r\n") else "\n"
    lines.insert(index + 1, f"{action_line}{newline}")
    result = "".join(lines)
    result_lines = result.splitlines()
    if not (
        result_lines.index("- Kristin. Place: driver's seat.")
        < result_lines.index(action_line)
        < next(index for index, line in enumerate(result_lines) if line.startswith("- Already done:"))
    ):
        raise RuntimeError("Q1 action line is not between place and Already done")
    return result


def _insert_things_line(user: str) -> tuple[str, str]:
    lines = user.splitlines(keepends=True)
    things_indexes = [index for index, line in enumerate(lines) if line.rstrip("\r\n") == "THINGS:"]
    if len(things_indexes) > 1:
        raise RuntimeError("Q2 control has multiple THINGS sections")
    newline = "\r\n" if any(line.endswith("\r\n") for line in lines) else "\n"
    if things_indexes:
        start = things_indexes[0] + 1
        end = len(lines)
        for index in range(start, len(lines)):
            if lines[index].rstrip("\r\n").endswith(":") and not lines[index].startswith("-"):
                end = index
                break
        insert_at = end
        while insert_at > start and not lines[insert_at - 1].strip():
            insert_at -= 1
        lines.insert(insert_at, f"{Q2_TRUCK_LINE}{newline}")
    else:
        constraints = [index for index, line in enumerate(lines) if line.rstrip("\r\n") == "CONSTRAINTS:"]
        if len(constraints) != 1:
            raise RuntimeError("Q2 control needs one CONSTRAINTS section")
        index = constraints[0]
        lines[index:index] = [f"THINGS:{newline}", f"{Q2_TRUCK_LINE}{newline}", newline]
    result = "".join(lines)
    return result, _diff(user, result)


def _assert_exact_added(diff: str, expected_lines: list[str], label: str) -> None:
    added = [line[1:] for line in diff.splitlines() if line.startswith("+") and not line.startswith("+++")]
    removed = [line for line in diff.splitlines() if line.startswith("-") and not line.startswith("---")]
    if added != expected_lines or removed:
        raise RuntimeError(f"{label} diff is not exactly the registered added lines")


def _opening_arm_o2(opening_user: str) -> tuple[str, str]:
    lines = opening_user.splitlines(keepends=True)
    indexes = [index for index, line in enumerate(lines) if line.startswith("- Kristin Schweitzer's objective is")]
    if len(indexes) != 1:
        raise RuntimeError("shipped opening must contain one Kristin objective line")
    index = indexes[0]
    newline = "\r\n" if lines[index].endswith("\r\n") else "\n"
    arm_lines = lines[: index + 1] + [f"{line}{newline}" for line in Q3_LINES] + lines[index + 1 :]
    arm_user = "".join(arm_lines)
    diff = _diff(opening_user, arm_user)
    _assert_exact_added(diff, list(Q3_LINES), "Q3 arm O2")
    return arm_user, diff


def _prompt(
    system: str,
    user: str,
    *,
    part: str,
    question: str,
    variant: str,
    command: str | None,
    sample: int,
) -> dict[str, object]:
    return {
        "part": part,
        "question": question,
        "variant": variant,
        "command": command,
        "sample": sample,
        "system": system,
        "user": user,
    }


def build_document() -> dict[str, Any]:
    """Build all prompt arms and the complete 70-call narrator plan offline."""

    q1_controls: dict[str, dict[str, str]] = {}
    q1_arms: dict[str, dict[str, dict[str, str]]] = {}
    diffs: dict[str, Any] = {"q1": {}, "q2": {}, "q3": {}}
    for command in OPENING_COMMANDS:
        control = _control_request(command)
        _check_control(command, control)
        arm_one_user, _arm_one_diff = _arm_one_for_command(control["user"], command)
        arm_two_user = _insert_after_driver_seat(arm_one_user)
        arm_two_diff = _diff(arm_one_user, arm_two_user)
        _assert_only_added(arm_two_diff, REACH_LINE, f"{command!r} arm 2")
        arms: dict[str, dict[str, str]] = {}
        q1_diffs: dict[str, str] = {}
        for variant, action in Q1_ACTIONS.items():
            arm_user = _insert_player_action(arm_two_user, action)
            arm_diff = _diff(arm_two_user, arm_user)
            _assert_only_added(arm_diff, action, f"{command!r} {variant}")
            arms[variant] = {"system": control["system"], "user": arm_user}
            q1_diffs[variant] = arm_diff
        q1_controls[command] = control
        q1_arms[command] = arms
        diffs["q1"][command] = {
            "arm_1": _arm_one_diff,
            "arm_2": arm_two_diff,
            **q1_diffs,
        }

    q2_control = _q2_control_request()
    q2_t1_user, q2_t1_diff = _insert_things_line(q2_control["user"])
    if "THINGS:" in q2_control["user"]:
        _assert_only_added(q2_t1_diff, Q2_TRUCK_LINE, "Q2 arm T1")
    else:
        _assert_exact_added(q2_t1_diff, ["THINGS:", Q2_TRUCK_LINE, ""], "Q2 arm T1")
    diffs["q2"]["T1"] = q2_t1_diff

    opening = _opening_request()
    q3_o2_user, q3_o2_diff = _opening_arm_o2(opening["user"])
    diffs["q3"]["O2"] = q3_o2_diff

    q1_plan: list[dict[str, object]] = []
    for sample in range(1, 11):
        for command in OPENING_COMMANDS:
            for variant in ("q1_arm3", "q1_arm4"):
                arm = q1_arms[command][variant]
                q1_plan.append(
                    _prompt(
                        arm["system"],
                        arm["user"],
                        part="q1",
                        question="Q1",
                        variant=variant,
                        command=command,
                        sample=sample,
                    )
                )

    q2_plan: list[dict[str, object]] = []
    for sample in range(1, 11):
        q2_plan.extend(
            [
                _prompt(
                    q2_control["system"],
                    q2_control["user"],
                    part="q2",
                    question="Q2",
                    variant="q2_control",
                    command="go out to the truck",
                    sample=sample,
                ),
                _prompt(
                    q2_control["system"],
                    q2_t1_user,
                    part="q2",
                    question="Q2",
                    variant="q2_t1",
                    command="go out to the truck",
                    sample=sample,
                ),
            ]
        )

    q3_plan = [
        _prompt(opening["system"], q3_o2_user, part="q3", question="Q3", variant="q3_o2", command=None, sample=sample)
        for sample in range(1, 11)
    ]
    document: dict[str, Any] = {
        "mode": "dry",
        "opening_request": opening,
        "control_requests": {"q1": q1_controls, "q2": q2_control},
        "q1_controls": q1_controls,
        "q1_arms": q1_arms,
        "q2_control": q2_control,
        "q2_t1": {"system": q2_control["system"], "user": q2_t1_user},
        "q3_arms": {"q3_o2": {"system": opening["system"], "user": q3_o2_user}},
        "opening_arms": {"O2": {"system": opening["system"], "user": q3_o2_user}},
        "diffs": diffs,
        "plan": {"q1": q1_plan, "q2": q2_plan, "q3": q3_plan},
        "totals": {"q1": len(q1_plan), "q2": len(q2_plan), "q3": len(q3_plan), "total": TOTAL_CALLS},
    }
    if document["totals"] != {"q1": 40, "q2": 20, "q3": 10, "total": 70}:
        raise RuntimeError("probe 3 plan total is not 70 calls")
    document["document_hash"] = _canonical_hash(document)
    return document


def _smoke_plan(document: dict[str, Any]) -> list[dict[str, object]]:
    wanted = (
        ("q1_arm3", "head out to the truck"),
        ("q1_arm4", "go to the truck"),
        ("q2_control", "go out to the truck"),
        ("q2_t1", "go out to the truck"),
        ("q3_o2", None),
    )
    all_specs = document["plan"]["q1"] + document["plan"]["q2"] + document["plan"]["q3"]
    return [
        next(
            spec
            for spec in all_specs
            if spec["variant"] == variant and spec["command"] == command and spec["sample"] == 1
        )
        for variant, command in wanted
    ]


def run(document: dict[str, Any], *, mode: str, max_calls: int, out: Path) -> dict[str, Any]:
    if mode not in {"run", "smoke"}:
        raise ValueError(f"billed run mode must be run or smoke, not {mode!r}")
    _validate_live_guard()
    planned = 5 if mode == "smoke" else TOTAL_CALLS
    if planned > max_calls:
        raise CallCapExceeded(f"requested {planned} calls exceeds max-calls {max_calls}")

    result: dict[str, Any] = {
        "mode": mode,
        "document_hash": document["document_hash"],
        "planned_calls": planned,
        "max_calls": max_calls,
        "calls_made": 0,
        "stop_reason": None,
        "rows": [],
    }
    counter = CallCounter(max_calls)
    _write_json(out, result)
    plan = (
        _smoke_plan(document)
        if mode == "smoke"
        else document["plan"]["q1"] + document["plan"]["q2"] + document["plan"]["q3"]
    )
    url = os.environ.get("CLOUDFLARE_WORKER_URL", "").strip()
    for spec in plan:
        row: dict[str, object] = dict(spec)
        try:
            reply = _send_narrator(str(spec["system"]), str(spec["user"]), url, counter)
            if reply.get("status") == 429:
                counter.stop_reason = "HTTP_429"
                raise QuotaExceeded("HTTP_429", str(reply.get("raw_response", "")))
            row.update(reply)
        except QuotaExceeded as error:
            _record(result, _quota_row(row, error), out, counter)
            result["stop_reason"] = error.code
            _write_json(out, result)
            return result
        except CallCapExceeded:
            result["stop_reason"] = "MAX_CALLS_EXCEEDED"
            result["calls_made"] = counter.calls_made
            _write_json(out, result)
            raise
        _record(result, row, out, counter)
    return result


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser()
    modes = parser.add_mutually_exclusive_group(required=True)
    modes.add_argument("--dry", action="store_true")
    modes.add_argument("--smoke", action="store_true")
    modes.add_argument("--run", action="store_true")
    parser.add_argument("--out", required=True, type=Path)
    parser.add_argument("--max-calls", type=int, default=DEFAULT_MAX_CALLS)
    parser.add_argument("--confirm", action="store_true")
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = _build_parser()
    args = parser.parse_args(argv)
    if args.max_calls < 0:
        parser.error("max-calls must be non-negative")
    billed = args.smoke or args.run
    if billed and not args.confirm:
        print("billed mode requires --confirm; no calls were made", file=sys.stderr)
        return 2
    if billed:
        try:
            _validate_live_guard()
        except ValueError as error:
            print(str(error), file=sys.stderr)
            return 2
    try:
        document = build_document()
        if args.dry:
            _write_json(args.out, document)
            print("dry: document built, 70 planned calls, 0 calls")
            return 0
        mode = "smoke" if args.smoke else "run"
        result = run(document, mode=mode, max_calls=args.max_calls, out=args.out)
        print(f"{mode}: recorded {result['calls_made']} calls; stop={result['stop_reason'] or 'completed'}")
        return 0
    except CallCapExceeded as error:
        print(str(error), file=sys.stderr)
        return 2
    except Exception as error:
        print(f"opening/truck probe 3 failed: {error}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
