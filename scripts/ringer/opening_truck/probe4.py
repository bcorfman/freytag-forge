"""Offline-first 1A opening and truck-feedback probe, revision 4."""

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
    _quota_row,
    _record,
    _scripted_jev,
    _validate_live_guard,
)
from scripts.ringer.opening_truck.probe3 import _insert_player_action
from scripts.ringer.transcript_1a.boarding_probe import (
    CallCapExceeded,
    CallCounter,
    QuotaExceeded,
    _send_narrator,
    _write_json,
)

ROOT = Path(__file__).resolve().parents[3]
WORKER_PLACEHOLDER = "https://w.example"
DEFAULT_MAX_CALLS = 48
TOTAL_CALLS = 40
OPENING_COMMANDS = ("head out to the truck", "go to the truck")
REACH_LINE = "- Kristin can reach anything inside Kristin's truck from the driver's seat."
PLAYER_ACTION = "- Kristin takes in what she can see and reach from the driver's seat."


def _new_product_replay(boarding_commands: tuple[str, ...]) -> tuple[Any, Any, Any, list[dict[str, str]]]:
    """Build a product-wired replay with a narrator capture on boardings."""

    from storygame.runtime.capture import WorldCapture, build_capture_provider
    from storygame.runtime.engine import RuntimeEngine
    from storygame.runtime.state import RuntimeState
    from storygame.story_package.loader import load_story_package

    package = load_story_package(ROOT / "data/stories/continuity-initiative")
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
                # Preserve the product-built boarding prompt even when the
                # engine can complete the pure boarding action itself.
                self.provider.command_consumed = False
            return record

    capture = ProbeWorldCapture(provider, _scripted_jev)
    engine = RuntimeEngine(state, provider, capture=capture)
    return package, provider, engine, captured


def _control_request(command: str) -> dict[str, str]:
    """Capture the shipped boarding-turn narrator request for ``command``."""

    with _offline_worker_environment():
        _package, _provider, engine, captured = _new_product_replay((command,))
        for route_command in ("open the drawer", "feel in the gap", command):
            engine.turn(route_command)
    matching = [prompt for prompt in captured if "Already done:" in prompt["user"]]
    if not matching:
        raise RuntimeError(f"product replay did not produce the boarding narrator request for {command!r}")
    return matching[-1]


def _check_control(command: str, request: dict[str, str]) -> None:
    user_lines = request["user"].splitlines()
    if REACH_LINE not in user_lines:
        raise RuntimeError(f"control prompt for {command!r} is missing the committed reach bullet")
    if not any(line.startswith("- Already done:") for line in user_lines):
        raise RuntimeError(f"control prompt for {command!r} is missing the 'Already done:' marker")
    if "- Kristin. Place: driver's seat." not in user_lines:
        raise RuntimeError(f"control prompt for {command!r} is missing the driver's-seat place line")
    if f"- {command}" in user_lines:
        raise RuntimeError(f"control prompt for {command!r} still contains the raw movement line")


def _assert_only_added(diff: str, expected_line: str, label: str) -> None:
    added = [line[1:] for line in diff.splitlines() if line.startswith("+") and not line.startswith("+++")]
    removed = [line for line in diff.splitlines() if line.startswith("-") and not line.startswith("---")]
    if added != [expected_line] or removed:
        raise RuntimeError(f"{label} diff is not exactly one added line")


def _plan(requests: dict[str, dict[str, dict[str, str]]]) -> list[dict[str, object]]:
    plan: list[dict[str, object]] = []
    for sample in range(1, 11):
        for command in OPENING_COMMANDS:
            for variant in ("A", "B"):
                prompt = requests[command][variant]
                plan.append(
                    {
                        "command": command,
                        "variant": variant,
                        "sample": sample,
                        "system": prompt["system"],
                        "user": prompt["user"],
                    }
                )
    return plan


def build_document() -> dict[str, Any]:
    """Build the product-captured arms and complete 40-call narrator plan."""

    requests: dict[str, dict[str, dict[str, str]]] = {}
    diffs: dict[str, dict[str, str]] = {}
    for command in OPENING_COMMANDS:
        arm_a = _control_request(command)
        _check_control(command, arm_a)
        arm_b_user = _insert_player_action(arm_a["user"], PLAYER_ACTION)
        arm_b_diff = _diff(arm_a["user"], arm_b_user)
        _assert_only_added(arm_b_diff, PLAYER_ACTION, f"{command!r} arm B")
        requests[command] = {
            "A": {"system": arm_a["system"], "user": arm_a["user"]},
            "B": {"system": arm_a["system"], "user": arm_b_user},
        }
        diffs[command] = {"A": "", "B": arm_b_diff}

    plan = _plan(requests)
    if len(plan) != TOTAL_CALLS:
        raise RuntimeError(f"probe 4 plan total is not {TOTAL_CALLS} calls")
    document: dict[str, Any] = {
        "mode": "dry",
        "requests": requests,
        "diffs": diffs,
        "plan": plan,
        "totals": {"total": len(plan)},
    }
    document["document_hash"] = _canonical_hash(document)
    return document


def _smoke_plan(document: dict[str, Any]) -> list[dict[str, object]]:
    wanted = (("head out to the truck", "A"), ("go to the truck", "B"))
    return [
        next(
            spec
            for spec in document["plan"]
            if spec["command"] == command and spec["variant"] == variant and spec["sample"] == 1
        )
        for command, variant in wanted
    ]


def run(document: dict[str, Any], *, mode: str, max_calls: int, out: Path) -> dict[str, Any]:
    if mode not in {"run", "smoke"}:
        raise ValueError(f"billed run mode must be run or smoke, not {mode!r}")
    _validate_live_guard()
    planned = 2 if mode == "smoke" else TOTAL_CALLS
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
    plan = _smoke_plan(document) if mode == "smoke" else document["plan"]
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
            print("dry: document built, 40 planned calls, 0 calls")
            return 0
        mode = "smoke" if args.smoke else "run"
        result = run(document, mode=mode, max_calls=args.max_calls, out=args.out)
        print(f"{mode}: recorded {result['calls_made']} calls; stop={result['stop_reason'] or 'completed'}")
        return 0
    except CallCapExceeded as error:
        print(str(error), file=sys.stderr)
        return 2
    except Exception as error:
        print(f"opening/truck probe 4 failed: {error}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
