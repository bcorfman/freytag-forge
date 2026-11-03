"""Offline-first 1A opening and truck-feedback probe, revision 2."""

from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path
from typing import Any

from scripts.ringer.opening_truck.probe import (
    _arm_one as _reference_arm_one,
)
from scripts.ringer.opening_truck.probe import (
    _canonical_hash,
    _diff,
    _jev_transport,
    _offline_worker_environment,
    _quota_row,
    _record,
    _scripted_jev,
)
from scripts.ringer.opening_truck.probe import (
    _opening_request as _reference_opening_request,
)
from scripts.ringer.opening_truck.probe import (
    _validate_live_guard as _reference_validate_live_guard,
)
from scripts.ringer.transcript_1a.boarding_probe import (
    CallCapExceeded,
    CallCounter,
    QuotaExceeded,
    _jsonable,
    _send_narrator,
    _write_json,
)

ROOT = Path(__file__).resolve().parents[3]
WORKER_PLACEHOLDER = "https://w.example"
DEFAULT_MAX_CALLS = 105
TOTAL_CALLS = 94
REACH_LINE = "- Kristin can reach anything inside Kristin's truck from where she sits."
OPENING_COMMANDS = ("head out to the truck", "go to the truck")
PHRASINGS = (
    "head out to {v}",
    "go out to {v}",
    "go to {v}",
    "get in {v}",
    "climb into {v}",
    "walk out to {v}",
    "walk up to {v}",
    "approach {v}",
    "look at {v}",
    "get out of {v}",
    "head over to {v}",
    "make for {v}",
)
VEHICLES = (("Kristin's truck", "the truck"), ("the van", "the van"))
EXPECTED_BY_INDEX = ("yes", "yes", "yes", "yes", "yes", "yes", "no", "no", "no", "no", "unscored", "unscored")


def _opening_request() -> dict[str, str]:
    """Return the shipped opening request built by the reference probe."""

    return _reference_opening_request()


def _new_product_replay(boarding_commands: tuple[str, ...]) -> tuple[Any, Any, Any, list[dict[str, str]]]:
    """Build the product replay while forcing narrator capture for boardings."""

    from storygame.runtime.capture import WorldCapture, build_capture_provider
    from storygame.runtime.engine import RuntimeEngine
    from storygame.runtime.state import RuntimeState
    from storygame.story_package.loader import load_story_package

    package_root = ROOT / "data/stories/continuity-initiative"
    package = load_story_package(package_root)
    state = RuntimeState.bootstrap(package)
    provider = build_capture_provider(state)
    provider.semantic_ask = _scripted_jev
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
                # Boarding may be completed by engine text. The probe needs the
                # narrator request that the product wiring would otherwise skip.
                self.provider.command_consumed = False
            return record

    capture = ProbeWorldCapture(provider, _scripted_jev)
    engine = RuntimeEngine(state, provider, capture=capture)
    return package, provider, engine, captured


def _control_request(command: str) -> dict[str, str]:
    with _offline_worker_environment():
        _package, _provider, engine, captured = _new_product_replay((command,))
        for route_command in ("open the drawer", "feel in the gap", command):
            engine.turn(route_command)
    matching = [prompt for prompt in captured if f"- {command}" in prompt["user"]]
    if not matching:
        raise RuntimeError(f"product replay did not produce the boarding narrator request for {command!r}")
    return matching[-1]


def _check_control(command: str, request: dict[str, str]) -> None:
    user = request["user"]
    if "Already done:" not in user:
        raise RuntimeError(f"control prompt for {command!r} is missing the 'Already done:' boarding marker")
    command_lines = [line for line in user.splitlines() if line == f"- {command}"]
    if len(command_lines) != 1:
        raise RuntimeError(f"control prompt for {command!r} must contain one raw command line")
    scene_lines = _scene_driver_lines(user)
    if len(scene_lines) != 1:
        raise RuntimeError(f"control prompt for {command!r} has no unique driver's-seat SCENE line")


def _scene_driver_lines(user: str) -> list[str]:
    lines = user.splitlines()
    try:
        start = lines.index("SCENE:") + 1
    except ValueError as error:
        raise RuntimeError("control prompt has no SCENE section") from error
    end = len(lines)
    for index in range(start, len(lines)):
        if lines[index].endswith(":") and not lines[index].startswith("-"):
            end = index
            break
    return [line for line in lines[start:end] if line.startswith("- ") and "driver's seat" in line]


def _arm_one_for_command(control_user: str, command: str) -> tuple[str, str]:
    if command == OPENING_COMMANDS[0]:
        return _reference_arm_one(control_user)
    lines = control_user.splitlines(keepends=True)
    target = f"- {command}"
    indexes = [index for index, line in enumerate(lines) if line.rstrip("\r\n") == target]
    if len(indexes) != 1:
        raise RuntimeError(f"control prompt must contain exactly one raw command line {target!r}")
    arm_lines = lines[: indexes[0]] + lines[indexes[0] + 1 :]
    if [line for index, line in enumerate(lines) if index != indexes[0]] != arm_lines:
        raise RuntimeError("arm 1 changed a line other than the raw command")
    arm_user = "".join(arm_lines)
    return arm_user, _diff(control_user, arm_user)


def _insert_after_driver_seat(user: str) -> str:
    lines = user.splitlines(keepends=True)
    scene_start = next(index for index, line in enumerate(lines) if line.rstrip("\r\n") == "SCENE:") + 1
    scene_end = next(
        (
            index
            for index in range(scene_start, len(lines))
            if lines[index].rstrip("\r\n").endswith(":") and not lines[index].startswith("-")
        ),
        len(lines),
    )
    indexes = [
        index
        for index in range(scene_start, scene_end)
        if lines[index].startswith("- ") and "driver's seat" in lines[index]
    ]
    if len(indexes) != 1:
        raise RuntimeError("arm 2 needs exactly one SCENE line containing driver's seat")
    index = indexes[0]
    newline = "\r\n" if lines[index].endswith("\r\n") else "\n"
    lines.insert(index + 1, f"{REACH_LINE}{newline}")
    return "".join(lines)


def _assert_only_added(diff: str, expected_line: str, label: str) -> None:
    added = [line for line in diff.splitlines() if line.startswith("+") and not line.startswith("+++")]
    removed = [line for line in diff.splitlines() if line.startswith("-") and not line.startswith("---")]
    if added != [f"+{expected_line}"] or removed:
        raise RuntimeError(f"{label} diff is not exactly one added line")


def _opening_arm_one(opening_user: str) -> tuple[str, str]:
    additions = (
        "- Kristin is in Michelle's kitchen, just inside the forced back door.",
        "- The workstation stands in the kitchen. Its chair lies overturned beside it.",
        "- Michelle is Kristin's best friend, and Kristin knows this house. It is far too quiet.",
        "- The KMS initials on the drawer are fresh cuts: Kristin's own initials on Michelle's furniture. "
        "Kristin cannot explain them.",
    )
    lines = opening_user.splitlines(keepends=True)
    indexes = [index for index, line in enumerate(lines) if line.startswith("- Kristin Schweitzer's objective is")]
    if len(indexes) != 1:
        raise RuntimeError("shipped opening must contain one Kristin objective line")
    index = indexes[0]
    newline = "\r\n" if lines[index].endswith("\r\n") else "\n"
    arm_lines = lines[: index + 1] + [f"{line}{newline}" for line in additions] + lines[index + 1 :]
    arm_user = "".join(arm_lines)
    diff = _diff(opening_user, arm_user)
    added = [line[1:] for line in diff.splitlines() if line.startswith("+") and not line.startswith("+++")]
    if added != list(additions):
        raise RuntimeError("opening arm O1 diff is not exactly the four registered SCENE lines")
    return arm_user, diff


def _shipped_boards_vehicle_payload(
    command: str, vehicle_name: str
) -> tuple[dict[str, str], dict[str, dict[str, object]]]:
    from storygame.runtime.jev_questions import boards_vehicle_payload

    return boards_vehicle_payload(command, vehicle_name)


def _revised_boards_vehicle_payload(
    command: str, vehicle_name: str
) -> tuple[dict[str, str], dict[str, dict[str, object]]]:
    from storygame.runtime.jev_questions import _noul_question

    instructions = (
        "Decide whether the command has the player go to the vehicle in order to get in it. "
        "Going to, going out to, or heading out to a vehicle means the player gets in. "
        "Getting in, climbing in, sitting in, or driving it also counts."
    )
    true = "The command has the player go to, go out to, head out to, get into, sit in, or drive the vehicle."
    false = (
        "The command only looks at, touches, or talks about the vehicle, or only walks up to it or stands beside it. "
        "It is not boarding if it leaves the vehicle."
    )
    return {"command": command, "vehicle": vehicle_name}, {"boards_vehicle": _noul_question(instructions, true, false)}


def _part1_plan() -> list[dict[str, object]]:
    plan: list[dict[str, object]] = []
    for phrasing_index, phrasing in enumerate(PHRASINGS):
        for vehicle_name, command_vehicle in VEHICLES:
            command = phrasing.format(v=command_vehicle)
            expected = EXPECTED_BY_INDEX[phrasing_index]
            for arm in ("S", "R"):
                plan.append(
                    {
                        "part": "part1",
                        "classifier": "boards_vehicle",
                        "sample": 1,
                        "arm": arm,
                        "phrasing": phrasing,
                        "command": command,
                        "vehicle_name": vehicle_name,
                        "expected": expected,
                    }
                )
    return plan


def _part2_plan(arms: dict[str, dict[str, dict[str, str]]]) -> list[dict[str, object]]:
    plan: list[dict[str, object]] = []
    head_arms = arms["head out to the truck"]
    for sample in range(1, 13):
        prompt = head_arms["2"]
        plan.append(
            {
                "part": "part2",
                "sample": sample,
                "arm": 2,
                "variant": "arm2",
                "command": "head out to the truck",
                "system": prompt["system"],
                "user": prompt["user"],
            }
        )
    go_arms = arms["go to the truck"]
    for sample in range(1, 9):
        for arm_number, variant in ((0, "control"), (1, "arm1"), (2, "arm2")):
            prompt = go_arms[str(arm_number)]
            plan.append(
                {
                    "part": "part2",
                    "sample": sample,
                    "arm": arm_number,
                    "variant": variant,
                    "command": "go to the truck",
                    "system": prompt["system"],
                    "user": prompt["user"],
                }
            )
    return plan


def _part3_plan(opening_arm: dict[str, str]) -> list[dict[str, object]]:
    return [
        {
            "part": "part3",
            "sample": sample,
            "arm": "O1",
            "variant": "O1",
            "system": opening_arm["system"],
            "user": opening_arm["user"],
        }
        for sample in range(1, 11)
    ]


def build_document() -> dict[str, Any]:
    """Build prompts and the complete 94-call plan without network I/O."""

    opening = _opening_request()
    opening_user, opening_diff = _opening_arm_one(opening["user"])
    control_requests: dict[str, dict[str, str]] = {}
    arms: dict[str, dict[str, dict[str, str]]] = {}
    diffs: dict[str, Any] = {"opening": {"O1": opening_diff}}
    for command in OPENING_COMMANDS:
        control = _control_request(command)
        _check_control(command, control)
        arm_one_user, arm_one_diff = _arm_one_for_command(control["user"], command)
        arm_two_user = _insert_after_driver_seat(arm_one_user)
        arm_two_diff = _diff(arm_one_user, arm_two_user)
        _assert_only_added(arm_two_diff, REACH_LINE, f"{command!r} arm 2")
        control_requests[command] = control
        arms[command] = {
            "0": {"system": control["system"], "user": control["user"]},
            "1": {"system": control["system"], "user": arm_one_user},
            "2": {"system": control["system"], "user": arm_two_user},
        }
        diffs[command] = {"arm_1": arm_one_diff, "arm_2": arm_two_diff}

    opening_arm = {"system": opening["system"], "user": opening_user}
    part1 = _part1_plan()
    part2 = _part2_plan(arms)
    part3 = _part3_plan(opening_arm)
    document: dict[str, Any] = {
        "mode": "dry",
        "opening_request": opening,
        "opening_arms": {"O1": opening_arm},
        "control_requests": control_requests,
        "arms": arms,
        "diffs": diffs,
        "plan": {"part1": part1, "part2": part2, "part3": part3},
        "totals": {"part1": len(part1), "part2": len(part2), "part3": len(part3), "total": TOTAL_CALLS},
    }
    if document["totals"]["total"] != TOTAL_CALLS:
        raise RuntimeError("probe 2 plan total is not 94 calls")
    document["document_hash"] = _canonical_hash(document)
    return document


def _live_url() -> str:
    return os.environ.get("CLOUDFLARE_WORKER_URL", "").strip()


def _validate_live_guard() -> None:
    url = _live_url()
    if not url:
        raise ValueError("billed mode requires CLOUDFLARE_WORKER_URL")
    if url.rstrip("/") == WORKER_PLACEHOLDER:
        raise ValueError(f"billed mode refuses placeholder CLOUDFLARE_WORKER_URL={WORKER_PLACEHOLDER}")
    _reference_validate_live_guard()


def _payload_for_spec(spec: dict[str, object]) -> tuple[dict[str, str], dict[str, dict[str, object]]]:
    if spec["arm"] == "S":
        return _shipped_boards_vehicle_payload(str(spec["command"]), str(spec["vehicle_name"]))
    return _revised_boards_vehicle_payload(str(spec["command"]), str(spec["vehicle_name"]))


def _part1_row(spec: dict[str, object], client: Any, counter: CallCounter) -> dict[str, object]:
    from storygame.runtime.jev import noul_yes

    state, questions = _payload_for_spec(spec)
    try:
        answers = _jev_transport(client, state, questions, counter)
        answer = answers.get("boards_vehicle") if isinstance(answers, dict) else None
        return {
            **spec,
            "state": _jsonable(state),
            "question": _jsonable(questions),
            "answer": _jsonable(answer),
            "raw_answer": _jsonable(answer),
            "is_yes": noul_yes(answer),
            "error": None,
        }
    except QuotaExceeded:
        raise
    except Exception as error:
        return {
            **spec,
            "state": _jsonable(state),
            "question": _jsonable(questions),
            "answer": None,
            "raw_answer": None,
            "is_yes": None,
            "error": f"{type(error).__name__}: {error}",
        }


def _smoke_part1_plan(document: dict[str, Any]) -> list[dict[str, object]]:
    wanted = ("head out to the truck", "go out to the truck", "walk up to the truck")
    return [
        next(
            spec
            for spec in document["plan"]["part1"]
            if spec["arm"] == "R" and spec["command"] == command and spec["vehicle_name"] == "Kristin's truck"
        )
        for command in wanted
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

    from storygame.runtime.jev import JevClient

    client = JevClient.from_environment()
    part1_plan = _smoke_part1_plan(document) if mode == "smoke" else document["plan"]["part1"]
    for spec in part1_plan:
        try:
            row = _part1_row(spec, client, counter)
        except QuotaExceeded as error:
            state, questions = _payload_for_spec(spec)
            row = {
                **spec,
                "state": _jsonable(state),
                "question": _jsonable(questions),
                "answer": None,
                "raw_answer": None,
                "is_yes": None,
                "error": str(error),
            }
            _record(result, row, out, counter)
            result["stop_reason"] = error.code
            _write_json(out, result)
            return result
        except CallCapExceeded:
            result["stop_reason"] = "MAX_CALLS_EXCEEDED"
            result["calls_made"] = counter.calls_made
            _write_json(out, result)
            raise
        _record(result, row, out, counter)

    narrator_plan = document["plan"]["part2"] + document["plan"]["part3"]
    if mode == "smoke":
        narrator_plan = [document["plan"]["part2"][0], document["plan"]["part3"][0]]
    url = _live_url()
    for spec in narrator_plan:
        row: dict[str, object] = {
            "part": spec["part"],
            "sample": spec["sample"],
            "arm": spec.get("arm"),
            "variant": spec.get("variant"),
            "command": spec.get("command"),
            "system": spec["system"],
            "user": spec["user"],
        }
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
            print("dry: document built, 94 planned calls, 0 calls")
            return 0
        mode = "smoke" if args.smoke else "run"
        result = run(document, mode=mode, max_calls=args.max_calls, out=args.out)
        print(f"{mode}: recorded {result['calls_made']} calls; stop={result['stop_reason'] or 'completed'}")
        return 0
    except CallCapExceeded as error:
        print(str(error), file=sys.stderr)
        return 2
    except Exception as error:
        print(f"opening/truck probe 2 failed: {error}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
