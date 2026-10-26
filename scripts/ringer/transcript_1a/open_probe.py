"""Build and run the 1A open narrator probe."""

from __future__ import annotations

import argparse
import difflib
import json
import os
import sys
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path
from types import SimpleNamespace
from typing import Any
from urllib.error import HTTPError
from urllib.request import Request

ROOT = Path(__file__).resolve().parents[3]
PACKAGE_ROOT = ROOT / "data/stories/continuity-initiative"
QUOTA_CODES = ("AI_QUOTA_EXCEEDED", "AI_DAILY_BUDGET_EXCEEDED")
DEFAULT_MAX_CALLS = 100
PROBLEM_ORDER = ("P1", "P2", "P3")
PROBLEM_ARMS = {
    "P1": ("control", "drop", "past"),
    "P2": ("control", "where", "place"),
    "P3": ("control", "view", "rule"),
}
REPLAYS = {
    "P1": ("reported", 5),
    "P2": ("witnessed", 3),
    "P3": ("movement", 7),
}
CARD_STATEMENT = "Kristin finds Michelle's memory card taped beneath the drawer and pockets it."
CARD_PREFIX = "Dr. Michelle McGehee may say this aloud: "
P1_CARD_LINE = f"- {CARD_PREFIX}{CARD_STATEMENT}"
P1_PAST_LINE = "- " + CARD_PREFIX + "Kristin already took Michelle's memory card from beneath the drawer."
P2_SCENE_LINE = "- Kristin is inside the house."
P2_PLACE_LINE = "- Kristin. Place: inside Michelle's house."
P2_OLD_PLACE_LINE = "- Kristin. Place: Michelle's house."
P3_SCENE_PREFIX = "- Michelle's house stands behind a low gate."
P3_VIEW_SUFFIX = (
    " From the curb she can see the gate, the front of the house, the truck, the street, "
    "and the lights on the next street."
)
P3_RULE_LINE = "- Describe only the things in THINGS and SCENE."


class CallCapExceeded(RuntimeError):
    """The requested billed calls exceed the configured cap."""


class QuotaExceeded(RuntimeError):
    """The worker reported a daily billed-call quota stop."""

    def __init__(self, code: str, raw_response: str = "") -> None:
        super().__init__(code)
        self.code = code
        self.raw_response = raw_response


def _write_json(path: Path, value: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, ensure_ascii=False) + "\n")


def _jev_answers(_state: object, _questions: dict[str, object]) -> None:
    """Stub Jev as the fail-closed dry replay does."""

    return None


@contextmanager
def _stub_jev() -> Iterator[None]:
    from storygame.runtime.jev import JevClient

    original = JevClient.__dict__["from_environment"]
    JevClient.from_environment = classmethod(  # type: ignore[method-assign]
        lambda cls: SimpleNamespace(ask=_jev_answers)
    )
    try:
        yield
    finally:
        JevClient.from_environment = original


def _section_bounds(lines: list[str], heading: str) -> tuple[int, int]:
    start = next((index for index, line in enumerate(lines) if line == f"{heading}:"), None)
    if start is None:
        raise ValueError(f"missing {heading} section")
    end = len(lines)
    for index in range(start + 1, len(lines)):
        if lines[index].endswith(":") and not lines[index].startswith("-"):
            end = index
            break
    return start, end


def _replace_in_section(lines: list[str], heading: str, expected: str, replacement: str) -> None:
    start, end = _section_bounds(lines, heading)
    matches = [index for index in range(start + 1, end) if lines[index] == expected]
    if len(matches) != 1:
        raise ValueError(f"expected exactly one {heading} line, missing or ambiguous: {expected}")
    lines[matches[0]] = replacement


def _remove_in_section(lines: list[str], heading: str, expected: str) -> None:
    start, end = _section_bounds(lines, heading)
    matches = [index for index in range(start + 1, end) if lines[index] == expected]
    if len(matches) != 1:
        raise ValueError(f"expected exactly one {heading} line, missing or ambiguous: {expected}")
    del lines[matches[0]]


def _with_newline(lines: list[str], had_newline: bool) -> str:
    text = "\n".join(lines)
    return text + ("\n" if had_newline else "")


def transform_user(problem: str, arm: str, control_user: str) -> str:
    """Apply one exact, section-scoped user-text arm to a control prompt."""

    if arm == "control":
        if arm not in PROBLEM_ARMS.get(problem, ()):
            raise ValueError(f"unknown arm {arm!r} for {problem}")
        return control_user
    if arm not in PROBLEM_ARMS.get(problem, ()):
        raise ValueError(f"unknown arm {arm!r} for {problem}")

    lines = control_user.splitlines()
    had_newline = control_user.endswith("\n")
    if problem == "P1" and arm == "drop":
        _remove_in_section(lines, "CONSTRAINTS", P1_CARD_LINE)
    elif problem == "P1" and arm == "past":
        _replace_in_section(lines, "CONSTRAINTS", P1_CARD_LINE, P1_PAST_LINE)
    elif problem == "P2" and arm == "where":
        start, end = _section_bounds(lines, "SCENE")
        bullet = next((index for index in range(start + 1, end) if lines[index].startswith("- ")), None)
        if bullet is None:
            raise ValueError("missing first SCENE bullet")
        lines.insert(bullet, P2_SCENE_LINE)
    elif problem == "P2" and arm == "place":
        _replace_in_section(lines, "THINGS", P2_OLD_PLACE_LINE, P2_PLACE_LINE)
    elif problem == "P3" and arm == "view":
        start, end = _section_bounds(lines, "SCENE")
        matches = [index for index in range(start + 1, end) if lines[index].startswith(P3_SCENE_PREFIX)]
        if len(matches) != 1:
            raise ValueError("expected exactly one house SCENE bullet")
        if P3_VIEW_SUFFIX.strip() in lines[matches[0]]:
            raise ValueError("P3 view arm is already present")
        lines[matches[0]] += P3_VIEW_SUFFIX
    elif problem == "P3" and arm == "rule":
        start, end = _section_bounds(lines, "CONSTRAINTS")
        if P3_RULE_LINE in lines[start + 1 : end]:
            raise ValueError("P3 rule arm is already present")
        last_bullet = next(
            (index for index in range(end - 1, start, -1) if lines[index].startswith("- ")),
            None,
        )
        if last_bullet is None:
            raise ValueError("missing last CONSTRAINTS line")
        lines.insert(last_bullet + 1, P3_RULE_LINE)
    else:
        raise ValueError(f"unsupported arm {problem}/{arm}")
    return _with_newline(lines, had_newline)


def _diff(control: str, variant: str, arm: str) -> str:
    def normalized_lines(text: str) -> list[str]:
        return [line if line.endswith("\n") else f"{line}\n" for line in text.splitlines(keepends=True)]

    return "".join(
        difflib.unified_diff(
            normalized_lines(control),
            normalized_lines(variant),
            fromfile="control",
            tofile=f"arm-{arm}",
        )
    )


def _replay_control(package: Any, route: str, inputs: tuple[str, ...]) -> dict[str, str]:
    import storygame.runtime.cloudflare as cloudflare
    import storygame.runtime.jev as jev
    from scripts.ringer.transcript_1a import live_baseline

    counter = live_baseline.CallCounter(1000, True)
    original_cloudflare_urlopen = cloudflare.urlopen
    original_jev_urlopen = jev.urlopen
    live_baseline._wire(counter, True)
    record: dict[str, Any] = {"route": route, "opening": None, "turns": []}
    try:
        with _stub_jev():
            live_baseline._replicate(counter, package, route, inputs, record)
    finally:
        cloudflare.urlopen = original_cloudflare_urlopen
        jev.urlopen = original_jev_urlopen
    prompts = record["turns"][-1].get("prompts", []) if record.get("turns") else []
    narrator_prompts = [prompt for prompt in prompts if prompt["system"].startswith("You are the narrator")]
    if not narrator_prompts:
        raise RuntimeError(f"route {route!r} did not produce a narrator request on its last input")
    return narrator_prompts[-1]


def _validate_control(problem: str, prompt: dict[str, str]) -> None:
    user = prompt["user"]
    if problem == "P1" and "Michelle's memory card. Held by: Kristin" not in user:
        raise RuntimeError("P1 control user text does not show the card held by Kristin")
    if problem == "P2":
        lines = user.splitlines()
        scene_start, scene_end = _section_bounds(lines, "SCENE")
        things_start, things_end = _section_bounds(lines, "THINGS")
        scene = "\n".join(lines[scene_start:scene_end])
        things = "\n".join(lines[things_start:things_end])
        if "KMS initials carved in drawer" not in scene:
            raise RuntimeError("P2 control SCENE lacks KMS initials carved in drawer")
        if "Place: Michelle's house" not in things:
            raise RuntimeError("P2 control THINGS lacks Kristin's house place")
    if problem == "P3":
        lines = user.splitlines()
        scene_start, scene_end = _section_bounds(lines, "SCENE")
        scene = "\n".join(lines[scene_start:scene_end])
        if "Kristin is outside the house." not in scene:
            raise RuntimeError("P3 control SCENE lacks Kristin is outside the house")


def build_control_prompts() -> list[dict[str, Any]]:
    """Replay each approved route and capture its final product narrator request."""

    from scripts.ringer.transcript_1a.live_baseline import ROUTES
    from storygame.story_package.loader import load_story_package

    os.environ.setdefault("CLOUDFLARE_WORKER_URL", "https://worker.example/turn")
    package = load_story_package(PACKAGE_ROOT)
    prompts = []
    with _stub_jev():
        for problem in PROBLEM_ORDER:
            route, count = REPLAYS[problem]
            inputs = ROUTES[route][:count]
            control = _replay_control(package, route, inputs)
            _validate_control(problem, control)
            prompts.append(
                {
                    "id": problem,
                    "route": route,
                    "input_count": count,
                    "last_input": inputs[-1],
                    "control": control,
                }
            )
    return prompts


def _enrich_prompt(prompt: dict[str, Any]) -> dict[str, Any]:
    control = prompt["control"]
    arms = {
        arm: {
            "system": control["system"],
            "user": transform_user(prompt["id"], arm, control["user"]),
        }
        for arm in PROBLEM_ARMS[prompt["id"]]
    }
    return {
        **prompt,
        "arms": arms,
        "diffs": {
            arm: _diff(control["user"], arms[arm]["user"], arm)
            for arm in PROBLEM_ARMS[prompt["id"]]
            if arm != "control"
        },
    }


def build_document() -> dict[str, Any]:
    return {"mode": "dry", "problems": [_enrich_prompt(prompt) for prompt in build_control_prompts()]}


def _selected_problems(document: dict[str, Any], problem: str) -> list[dict[str, Any]]:
    if problem == "all":
        return list(document["problems"])
    if problem not in PROBLEM_ORDER:
        raise ValueError(f"unknown problem {problem!r}")
    selected = [entry for entry in document["problems"] if entry["id"] == problem]
    if not selected:
        raise ValueError(f"document has no {problem}")
    return selected


def _quota_code(text: str) -> str | None:
    return next((code for code in QUOTA_CODES if code in text), None)


def _http_error_body(error: HTTPError) -> str:
    try:
        body = error.read()
    except Exception:
        return ""
    return body.decode(errors="replace") if isinstance(body, bytes) else str(body)


def _parse_reply(raw_response: str) -> tuple[str | None, str, bool, object]:
    try:
        outer = json.loads(raw_response)
        outer_item_facts = outer.get("item_facts") if isinstance(outer, dict) else None
        raw_reply = outer.get("narration") if isinstance(outer, dict) else None
        if not isinstance(raw_reply, str):
            raw_reply = raw_response
        payload = json.loads(raw_reply)
        if not isinstance(payload, dict) or not isinstance(payload.get("segments"), list):
            raise ValueError("reply has no segments list")
        segments = payload["segments"]
        if any(not isinstance(segment, dict) or not isinstance(segment.get("text"), str) for segment in segments):
            raise ValueError("reply has an invalid segment")
        narration = " ".join(segment["text"] for segment in segments).strip()
        item_facts = payload.get("item_facts")
        if not isinstance(item_facts, dict):
            item_facts = outer_item_facts
        return narration, raw_reply, True, item_facts if isinstance(item_facts, dict) else None
    except (TypeError, ValueError, json.JSONDecodeError):
        return None, raw_response, False, None


def _send_narrator(system: str, user: str, url: str) -> dict[str, Any]:
    import storygame.runtime.cloudflare as cloudflare

    payload = {
        "system": system,
        "user": user,
        "max_tokens": 1024,
        "response_format": {"type": "json_object"},
    }
    headers = {"Content-Type": "application/json", "User-Agent": cloudflare.BROWSER_USER_AGENT}
    token = os.environ.get("CLOUDFLARE_WORKER_TOKEN", "").strip()
    if token:
        headers["Authorization"] = f"Bearer {token}"
    request = Request(url, data=json.dumps(payload).encode(), headers=headers, method="POST")
    try:
        with cloudflare.urlopen(request, timeout=float(os.environ.get("CLOUDFLARE_TIMEOUT", "15"))) as response:
            raw_response = response.read().decode(errors="replace")
            status = getattr(response, "status", 200)
    except HTTPError as error:
        raw_response = _http_error_body(error)
        quota = _quota_code(f"{getattr(error, 'headers', '')}\n{raw_response}")
        if quota is not None:
            raise QuotaExceeded(quota, raw_response) from error
        return {
            "status": error.code,
            "raw_response": raw_response,
            "raw_reply": raw_response,
            "narration": None,
            "usable": False,
            "item_facts": None,
            "error": f"HTTPError: {error}",
        }
    except Exception as error:
        return {
            "status": None,
            "raw_response": "",
            "raw_reply": "",
            "narration": None,
            "usable": False,
            "item_facts": None,
            "error": f"{type(error).__name__}: {error}",
        }
    quota = _quota_code(raw_response)
    if quota is not None:
        raise QuotaExceeded(quota, raw_response)
    narration, raw_reply, usable, item_facts = _parse_reply(raw_response)
    return {
        "status": status,
        "raw_response": raw_response,
        "raw_reply": raw_reply,
        "narration": narration,
        "usable": usable,
        "item_facts": item_facts,
        "error": None if usable else "unparseable narration reply",
    }


def run_samples(document: dict[str, Any], samples: int, problem: str, max_calls: int, out: Path) -> dict[str, Any]:
    if samples < 0 or max_calls < 0:
        raise ValueError("samples and max-calls must be non-negative")
    selected = _selected_problems(document, problem)
    requested = sum(len(PROBLEM_ARMS[prompt["id"]]) for prompt in selected) * samples
    if requested > max_calls:
        raise CallCapExceeded(f"requested {requested} calls exceeds max-calls {max_calls}")
    url = os.environ.get("CLOUDFLARE_WORKER_URL", "").strip()
    if not url:
        raise ValueError("live mode requires CLOUDFLARE_WORKER_URL")
    result: dict[str, Any] = {
        "mode": "run",
        "problem": problem,
        "samples_requested": samples,
        "max_calls": max_calls,
        "calls_requested": requested,
        "calls_made": 0,
        "stop_reason": None,
        "rows": [],
    }
    _write_json(out, result)
    try:
        for sample in range(1, samples + 1):
            for arm in ("control", "drop", "past", "where", "place", "view", "rule"):
                for prompt in selected:
                    if arm not in PROBLEM_ARMS[prompt["id"]]:
                        continue
                    arm_prompt = prompt["arms"][arm]
                    row: dict[str, Any] = {
                        "problem": prompt["id"],
                        "arm": arm,
                        "sample": sample,
                        "system": arm_prompt["system"],
                        "user": arm_prompt["user"],
                    }
                    try:
                        row.update(_send_narrator(arm_prompt["system"], arm_prompt["user"], url))
                    except QuotaExceeded as error:
                        row.update(
                            {
                                "status": 429,
                                "raw_response": error.raw_response,
                                "raw_reply": error.raw_response,
                                "narration": None,
                                "usable": False,
                                "item_facts": None,
                                "error": str(error),
                            }
                        )
                        result["rows"].append(row)
                        result["calls_made"] += 1
                        result["stop_reason"] = error.code
                        _write_json(out, result)
                        return result
                    result["rows"].append(row)
                    result["calls_made"] += 1
                    _write_json(out, result)
    except CallCapExceeded:
        result["stop_reason"] = "MAX_CALLS_EXCEEDED"
        _write_json(out, result)
        raise
    return result


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser()
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--dry", action="store_true")
    mode.add_argument("--run", action="store_true")
    parser.add_argument("--problem", choices=("P1", "P2", "P3", "all"), default="all")
    parser.add_argument("--samples", type=int, default=10)
    parser.add_argument("--max-calls", type=int, default=DEFAULT_MAX_CALLS)
    parser.add_argument("--confirm", action="store_true")
    parser.add_argument("--out", required=True, type=Path)
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = _parser()
    args = parser.parse_args(argv)
    if args.samples < 0 or args.max_calls < 0:
        parser.error("samples and max-calls must be non-negative")
    if args.run and (not args.confirm or not os.environ.get("CLOUDFLARE_WORKER_URL", "").strip()):
        print("live mode requires --confirm and CLOUDFLARE_WORKER_URL", file=sys.stderr)
        return 2
    try:
        document = build_document()
        if args.dry:
            _write_json(args.out, document)
            diffs = sum(len(problem["diffs"]) for problem in document["problems"])
            print(f"dry: {len(document['problems'])} problems, 3 arms each, {diffs} diffs, 0 calls")
            return 0
        result = run_samples(document, args.samples, args.problem, args.max_calls, args.out)
        print(f"run: recorded {result['calls_made']} calls; stop={result['stop_reason'] or 'completed'}")
        return 0
    except CallCapExceeded as error:
        print(str(error), file=sys.stderr)
        return 2
    except Exception as error:
        print(f"open probe failed: {error}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
