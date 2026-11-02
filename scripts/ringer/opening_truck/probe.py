"""Offline-first 1A opening and truck-feedback probe harness."""

from __future__ import annotations

import argparse
import difflib
import hashlib
import json
import os
import sys
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path
from typing import Any
from urllib.error import HTTPError

from scripts.ringer.transcript_1a.boarding_probe import (
    CallCapExceeded,
    CallCounter,
    QuotaExceeded,
    _jsonable,
    _quota_code,
    _send_narrator,
    _write_json,
)

ROOT = Path(__file__).resolve().parents[3]
PACKAGE_ROOT = ROOT / "data/stories/continuity-initiative"
WORKER_PLACEHOLDER = "https://w.example"
DEFAULT_MAX_CALLS = 85
TOTAL_CALLS = 74

PHRASINGS = (
    "head out to {v}",
    "go out to {v}",
    "go to {v}",
    "get in {v}",
    "climb into {v}",
    "walk up to {v}",
    "look at {v}",
    "get out of {v}",
)
VEHICLES = (("Kristin's truck", "the truck"), ("the van", "the van"))
OPENING_COMMAND = "head out to the truck"


def _canonical_hash(value: object) -> str:
    encoded = json.dumps(value, sort_keys=True, ensure_ascii=False, separators=(",", ":")).encode()
    return hashlib.sha256(encoded).hexdigest()


def _diff(before: str, after: str) -> str:
    def lines(text: str) -> list[str]:
        return [line if line.endswith("\n") else f"{line}\n" for line in text.splitlines(keepends=True)]

    return "".join(difflib.unified_diff(lines(before), lines(after), fromfile="control", tofile="arm-1"))


def _scripted_jev(_state: object, questions: object) -> dict[str, dict[str, float]]:
    """Return affirmative answers for the product-wiring replay."""

    state = _state if isinstance(_state, dict) else {}
    command = str(state.get("command", "")).lower()
    answers: dict[str, dict[str, float]] = {}
    for key in questions if isinstance(questions, dict) else ():
        if key in {"boards_vehicle", "only_boards_vehicle"}:
            yes = "truck" in command
        elif key == "searches_underneath":
            yes = "gap" in command
        elif key == "opens_container":
            yes = "open" in command and "drawer" in command
        else:
            yes = False
        answers[str(key)] = {"noul": 1.0 if yes else 0.0}
    return answers


@contextmanager
def _offline_worker_environment() -> Iterator[None]:
    original = os.environ.get("CLOUDFLARE_WORKER_URL")
    if not original or not original.strip():
        os.environ["CLOUDFLARE_WORKER_URL"] = WORKER_PLACEHOLDER
    from storygame.runtime.cloudflare import CloudflareTurnProvider

    original_item_facts = CloudflareTurnProvider._request_item_facts
    CloudflareTurnProvider._request_item_facts = lambda self, _payload: {  # type: ignore[method-assign]
        "refers": [],
        "same_as": {},
    }
    try:
        yield
    finally:
        CloudflareTurnProvider._request_item_facts = original_item_facts
        if original is None:
            os.environ.pop("CLOUDFLARE_WORKER_URL", None)
        else:
            os.environ["CLOUDFLARE_WORKER_URL"] = original


def _capturing_dispatch(provider: Any, captured: list[dict[str, str]]):
    def dispatch(system: str, user: dict[str, object]) -> dict[str, object]:
        captured.append({"system": system, "user": provider._section_user_prompt(user)})
        return {
            "segments": [{"kind": "narration", "text": "Offline probe narration."}],
            "selected_knowledge_ids": [],
        }

    return dispatch


def _new_product_replay() -> tuple[Any, Any, Any, list[dict[str, str]]]:
    from storygame.runtime.capture import WorldCapture, build_capture_provider
    from storygame.runtime.engine import RuntimeEngine
    from storygame.runtime.state import RuntimeState
    from storygame.story_package.loader import load_story_package

    package = load_story_package(PACKAGE_ROOT)
    state = RuntimeState.bootstrap(package)
    provider = build_capture_provider(state)
    provider.semantic_ask = _scripted_jev
    provider._request_item_facts = lambda _payload: {"refers": [], "same_as": {}}
    captured: list[dict[str, str]] = []
    provider._dispatch = _capturing_dispatch(provider, captured)

    class ProbeWorldCapture(WorldCapture):
        def before_turn(self, command: str) -> dict[str, Any]:
            record = super().before_turn(command)
            if command == OPENING_COMMAND:
                # The product normally completes this pure boarding action with
                # engine text. The probe records the narrator request used by
                # the boarding turn, while leaving the product wiring attached.
                self.provider.command_consumed = False
            return record

    capture = ProbeWorldCapture(provider, _scripted_jev)
    engine = RuntimeEngine(state, provider, capture=capture)
    return package, provider, engine, captured


def _opening_request() -> dict[str, str]:
    with _offline_worker_environment():
        _package, _provider, engine, captured = _new_product_replay()
        engine.opening()
    if not captured:
        raise RuntimeError("product provider did not produce the 1A opening narrator request")
    return captured[-1]


def _control_request() -> dict[str, str]:
    with _offline_worker_environment():
        _package, _provider, engine, captured = _new_product_replay()
        for command in ("open the drawer", "feel in the gap", OPENING_COMMAND):
            engine.turn(command)
    matching = [prompt for prompt in captured if OPENING_COMMAND in prompt["user"]]
    if not matching:
        raise RuntimeError("product replay did not produce the boarding narrator request")
    return matching[-1]


def _arm_one(control_user: str) -> tuple[str, str]:
    lines = control_user.splitlines(keepends=True)
    command_lines = [line for line in lines if line.rstrip("\r\n") == f"- {OPENING_COMMAND}"]
    if len(command_lines) != 1:
        raise RuntimeError(
            "control prompt must contain exactly one raw command line "
            f"'- {OPENING_COMMAND}', found {len(command_lines)}"
        )
    arm_lines = [line for line in lines if line.rstrip("\r\n") != f"- {OPENING_COMMAND}"]
    arm_user = "".join(arm_lines)
    if arm_user.splitlines(keepends=True) != [line for line in lines if line not in command_lines]:
        raise RuntimeError("arm 1 changed a line other than the raw command")
    return arm_user, _diff(control_user, arm_user)


def _part1_plan() -> list[dict[str, object]]:
    plan: list[dict[str, object]] = []
    for phrasing in PHRASINGS:
        for vehicle_name, command_vehicle in VEHICLES:
            for sample in (1, 2):
                plan.append(
                    {
                        "part": "part1",
                        "classifier": "boards_vehicle",
                        "sample": sample,
                        "phrasing": phrasing,
                        "command": phrasing.format(v=command_vehicle),
                        "vehicle_name": vehicle_name,
                    }
                )
    for phrasing in PHRASINGS[:4]:
        for sample in (1, 2):
            plan.append(
                {
                    "part": "part1",
                    "classifier": "only_boards_vehicle",
                    "sample": sample,
                    "phrasing": phrasing,
                    "command": phrasing.format(v="the truck"),
                    "vehicle_name": "Kristin's truck",
                }
            )
    return plan


def build_document() -> dict[str, Any]:
    """Build all prompts and the complete call plan without network I/O."""

    opening = _opening_request()
    control = _control_request()
    if "Already done:" not in control["user"]:
        raise RuntimeError("control prompt is missing the 'Already done:' boarding marker")
    if f"- {OPENING_COMMAND}" not in control["user"]:
        raise RuntimeError("control prompt is missing the raw boarding command line")
    if not any(line.startswith("- ") and "driver's seat" in line for line in control["user"].splitlines()):
        raise RuntimeError("control prompt has no SCENE line placing Kristin in the driver's seat")

    arm_user, arm_diff = _arm_one(control["user"])
    arm = {"system": control["system"], "user": arm_user}
    part1 = _part1_plan()
    part2 = [
        {
            "part": "part2",
            "sample": sample,
            "arm": arm_number,
            "variant": "control" if arm_number == 0 else "arm1",
            "system": control["system"],
            "user": control["user"] if arm_number == 0 else arm_user,
        }
        for sample in range(1, 13)
        for arm_number in (0, 1)
    ]
    part3 = [
        {"part": "part3", "sample": sample, "system": opening["system"], "user": opening["user"]}
        for sample in range(1, 11)
    ]
    document: dict[str, Any] = {
        "mode": "dry",
        "opening_request": opening,
        "control_request": control,
        "arm_1": arm,
        "diffs": {"arm_1": arm_diff},
        "plan": {"part1": part1, "part2": part2, "part3": part3},
        "totals": {"part1": len(part1), "part2": len(part2), "part3": len(part3), "total": TOTAL_CALLS},
    }
    if document["totals"]["total"] != TOTAL_CALLS:
        raise RuntimeError("probe plan total is not 74 calls")
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


def _body_from_http_error(error: HTTPError) -> str:
    try:
        body = error.read()
    except Exception:
        return ""
    return body.decode(errors="replace") if isinstance(body, bytes) else str(body)


def _jev_transport(client: Any, state: object, questions: dict[str, object], counter: CallCounter) -> dict | None:
    counter.before_call()
    try:
        answers = client.ask(state, questions)
    except HTTPError as error:
        raw = _body_from_http_error(error)
        code = _quota_code(f"{getattr(error, 'headers', '')}\n{raw}")
        if code or error.code == 429:
            stop = code or "HTTP_429"
            counter.stop_reason = stop
            raise QuotaExceeded(stop, raw) from error
        raise
    if getattr(client, "last_status", None) == 429:
        counter.stop_reason = "HTTP_429"
        raise QuotaExceeded("HTTP_429")
    return answers


def _part1_row(spec: dict[str, object], client: Any, counter: CallCounter) -> dict[str, object]:
    classifier = str(spec["classifier"])
    command = str(spec["command"])
    vehicle_name = str(spec["vehicle_name"])
    captured: dict[str, object] = {}

    def asking(state: object, questions: object) -> dict | None:
        captured["state"] = state
        captured["question"] = questions
        if not isinstance(questions, dict):
            captured["error"] = "questions were not a mapping"
            return None
        try:
            answers = _jev_transport(client, state, questions, counter)
        except Exception as error:
            captured["error"] = f"{type(error).__name__}: {error}"
            captured["transport_error"] = error
            return None
        captured["answers"] = answers
        return answers

    try:
        if classifier == "boards_vehicle":
            from storygame.runtime.jev import noul_yes
            from storygame.runtime.jev_questions import boards_vehicle_payload

            state, questions = boards_vehicle_payload(command, vehicle_name)
            captured["state"] = state
            captured["question"] = questions
            answers = _jev_transport(client, state, questions, counter)
            captured["answers"] = answers
            answer = answers.get("boards_vehicle") if isinstance(answers, dict) else None
            is_yes = noul_yes(answer)
        elif classifier == "only_boards_vehicle":
            from storygame.runtime.jev_questions import only_boards_vehicle

            is_yes = only_boards_vehicle(asking, command, vehicle_name)
            answer_map = captured.get("answers")
            answer = answer_map.get("only_boards_vehicle") if isinstance(answer_map, dict) else None
        else:
            raise ValueError(f"unknown Jev classifier {classifier!r}")
        transport_error = captured.get("transport_error")
        if isinstance(transport_error, QuotaExceeded):
            raise transport_error
        return {
            **spec,
            "state": _jsonable(captured.get("state")),
            "question": _jsonable(captured.get("question")),
            "answer": _jsonable(answer),
            "raw_answer": _jsonable(answer),
            "is_yes": is_yes,
            "error": captured.get("error"),
        }
    except QuotaExceeded:
        raise
    except Exception as error:
        return {
            **spec,
            "state": _jsonable(captured.get("state")),
            "question": _jsonable(captured.get("question")),
            "answer": _jsonable(captured.get("answer")),
            "raw_answer": _jsonable(captured.get("answer")),
            "is_yes": None,
            "error": f"{type(error).__name__}: {error}",
        }


def _smoke_part1_plan(document: dict[str, Any]) -> list[dict[str, object]]:
    wanted = ("head out to the truck", "get in the truck", "walk up to the truck")
    return [
        {
            **next(
                spec
                for spec in document["plan"]["part1"]
                if spec["classifier"] == "boards_vehicle" and spec["command"] == command and spec["sample"] == 1
            )
        }
        for command in wanted
    ]


def _quota_row(row: dict[str, object], error: QuotaExceeded) -> dict[str, object]:
    row.update(
        {
            "status": 429,
            "raw_response": error.raw_response,
            "raw_reply": error.raw_response,
            "narration": None,
            "usable": False,
            "error": str(error),
        }
    )
    return row


def _record(result: dict[str, Any], row: dict[str, object], out: Path, counter: CallCounter) -> None:
    result["rows"].append(_jsonable(row))
    result["calls_made"] = counter.calls_made
    _write_json(out, result)


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
            row = {
                **spec,
                "state": None,
                "question": None,
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

    narrator_plan: list[dict[str, object]] = document["plan"]["part2"] + document["plan"]["part3"]
    if mode == "smoke":
        narrator_plan = [document["plan"]["part2"][0], document["plan"]["part3"][0]]
    url = _live_url()
    for spec in narrator_plan:
        row: dict[str, object] = {
            "part": spec["part"],
            "sample": spec["sample"],
            "arm": spec.get("arm"),
            "variant": spec.get("variant"),
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
            print("dry: document built, 74 planned calls, 0 calls")
            return 0
        mode = "smoke" if args.smoke else "run"
        result = run(document, mode=mode, max_calls=args.max_calls, out=args.out)
        print(f"{mode}: recorded {result['calls_made']} calls; stop={result['stop_reason'] or 'completed'}")
        return 0
    except CallCapExceeded as error:
        print(str(error), file=sys.stderr)
        return 2
    except Exception as error:
        print(f"opening/truck probe failed: {error}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
