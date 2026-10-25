"""Offline prompt builder and billed-run harness for the 1A boarding probe."""

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
DEFAULT_MAX_CALLS = 130
PROMPT_CASES = (
    ("P1", "outside_house", "Go to the truck."),
    ("P2", "outside_house", "Get in."),
    ("P3", "kitchen", "Go out to the truck."),
)


class CallCapExceeded(RuntimeError):
    """The run would exceed its explicit call cap."""


class QuotaExceeded(RuntimeError):
    """The worker reported a billed-call quota stop."""

    def __init__(self, code: str, raw_response: str = "") -> None:
        super().__init__(code)
        self.code = code
        self.raw_response = raw_response


class CallCounter:
    """Count attempted worker calls and detect quota responses."""

    def __init__(self, max_calls: int) -> None:
        self.max_calls = max_calls
        self.calls_made = 0
        self.stop_reason: str | None = None

    def before_call(self) -> None:
        if self.stop_reason is not None:
            raise QuotaExceeded(self.stop_reason)
        if self.calls_made >= self.max_calls:
            self.stop_reason = "MAX_CALLS_EXCEEDED"
            raise CallCapExceeded(f"max-calls exceeded ({self.max_calls})")
        self.calls_made += 1

    def inspect(self, text: str) -> None:
        for code in QUOTA_CODES:
            if code in text:
                self.stop_reason = code
                raise QuotaExceeded(code)


def _jsonable(value: Any) -> Any:
    if value is None or isinstance(value, (str, int, float, bool)):
        return value
    if isinstance(value, dict):
        return {str(key): _jsonable(item) for key, item in value.items()}
    if isinstance(value, (list, tuple, set)):
        return [_jsonable(item) for item in value]
    if hasattr(value, "model_dump"):
        return _jsonable(value.model_dump(mode="json"))
    return repr(value)


def _write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, ensure_ascii=False) + "\n")


def _state_at(package: Any, place_id: str) -> Any:
    from storygame.runtime.state import RuntimeState
    from storygame.runtime.world_model import world_for

    state = RuntimeState.bootstrap(package)
    result = world_for(package, state.facts).move(package.world.protagonist_id, place_id)
    if not result.ok:
        raise RuntimeError(f"could not move protagonist to {place_id}: {result.reason}")
    return state


def _boarding_ask(_state: object, questions: dict[str, object]) -> dict[str, dict[str, float]]:
    """Answer the two boarding classifier questions affirmatively."""

    return {key: {"noul": 1.0} for key in questions}


@contextmanager
def _stub_jev() -> Iterator[None]:
    from storygame.runtime.jev import JevClient

    original = JevClient.__dict__["from_environment"]
    JevClient.from_environment = classmethod(
        lambda cls: SimpleNamespace(ask=_boarding_ask)  # type: ignore[method-assign]
    )
    try:
        yield
    finally:
        JevClient.from_environment = original


@contextmanager
def _stub_item_facts() -> Iterator[None]:
    from storygame.runtime.cloudflare import CloudflareTurnProvider

    original = CloudflareTurnProvider._request_item_facts
    CloudflareTurnProvider._request_item_facts = lambda self, _payload: {  # type: ignore[method-assign]
        "refers": [],
        "same_as": {},
    }
    try:
        yield
    finally:
        CloudflareTurnProvider._request_item_facts = original


def _control_prompt(package: Any, place_id: str, command: str) -> dict[str, str]:
    from storygame.runtime.capture import WorldCapture, build_capture_provider
    from storygame.runtime.cloudflare import CloudflareTurnProvider

    state = _state_at(package, place_id)
    with _stub_jev(), _stub_item_facts():
        provider = build_capture_provider(state)

        # The product provider normally sends this optional matcher request. Its
        # valid empty result leaves the same dependency-selected feed as the
        # baseline's invalid/default stub, without opening a network boundary.
        provider._request_item_facts = lambda _payload: {"refers": [], "same_as": {}}
        captured: dict[str, str] = {}

        def dispatch(system: str, user: dict[str, object]) -> dict[str, object]:
            captured["system"] = system
            captured["user"] = provider._section_user_prompt(user)
            return {"segments": [], "selected_knowledge_ids": []}

        provider._dispatch = dispatch
        WorldCapture(provider, _boarding_ask).before_turn(command)
        # The product now answers a boarding-only turn with engine text and no narrator
        # call; the probe needs the narrator request that boarding used to send.
        CloudflareTurnProvider.__call__(provider, command)

    if "system" not in captured or "user" not in captured:
        raise RuntimeError(f"provider did not produce a narrator request for {place_id!r}")
    return captured


def build_control_prompts() -> list[dict[str, Any]]:
    """Build the three exact control narrator requests without network I/O."""

    from storygame.story_package.loader import load_story_package

    os.environ.setdefault("CLOUDFLARE_WORKER_URL", "https://worker.example/turn")
    package = load_story_package(PACKAGE_ROOT)
    prompts = []
    for prompt_id, place_id, command in PROMPT_CASES:
        prompt = _control_prompt(package, place_id, command)
        if not any(line.lstrip().startswith("- Just before this:") for line in prompt["user"].splitlines()):
            raise RuntimeError(f"{prompt_id} control prompt has no 'Just before this:' line")
        prompts.append(
            {
                "id": prompt_id,
                "place": place_id,
                "command": command,
                "control": prompt,
            }
        )
    return prompts


def _just_before_line(user: str) -> tuple[int, str]:
    for index, line in enumerate(user.splitlines()):
        stripped = line.lstrip()
        if stripped.startswith("- Just before this:"):
            return index, stripped[len("- Just before this:") :].strip()
        if stripped.startswith("Just before this:"):
            return index, stripped[len("Just before this:") :].strip()
    raise ValueError("control prompt has no 'Just before this:' line")


def _section_bounds(lines: list[str], heading: str) -> tuple[int, int]:
    start = next((i for i, line in enumerate(lines) if line == f"{heading}:"), None)
    if start is None:
        raise ValueError(f"control prompt has no {heading} section")
    end = len(lines)
    for index in range(start + 1, len(lines)):
        if lines[index].endswith(":") and not lines[index].startswith("-"):
            end = index
            break
    return start, end


def arm_user_text(control_user: str, arm: int, command: str | None = None) -> str:
    """Apply one preregistered user-text-only arm to a control prompt."""

    if arm not in (0, 1, 2, 3):
        raise ValueError(f"unknown arm: {arm}")
    if arm == 0:
        return control_user

    lines = control_user.splitlines()
    trailing_newline = control_user.endswith("\n")
    before_index, steps = _just_before_line(control_user)
    if arm == 1:
        del lines[before_index]
        player_start, player_end = _section_bounds(lines, "PLAYER")
        player_lines = [i for i in range(player_start + 1, player_end) if lines[i].startswith("-")]
        replacement = f"- {steps}"
        command_line = f"- {command}" if command else None
        command_index = next((i for i in player_lines if lines[i] == command_line), None)
        if command_index is not None:
            lines[command_index] = replacement
        elif player_lines and "Place:" not in lines[player_lines[-1]]:
            lines[player_lines[-1]] = replacement
        else:
            lines.insert(player_end, replacement)
        result = "\n".join(lines)
        return f"{result}\n" if trailing_newline else result

    if arm == 2:
        constraints_start, constraints_end = _section_bounds(lines, "CONSTRAINTS")
        addition = "- Show every thing named in the Just before this line."
        if addition in lines[constraints_start + 1 : constraints_end]:
            raise ValueError("control prompt already contains the arm 2 constraint")
        insert_at = constraints_end
        while insert_at > constraints_start + 1 and lines[insert_at - 1] == "":
            insert_at -= 1
        lines.insert(insert_at, addition)
    else:
        things_start, things_end = _section_bounds(lines, "THINGS")
        addition = "- Kristin's laptop. Place: passenger seat."
        if addition in lines[things_start + 1 : things_end]:
            raise ValueError("control prompt already contains the arm 3 THINGS line")
        thing_lines = [index for index in range(things_start + 1, things_end) if lines[index].startswith("- ")]
        if not thing_lines:
            raise ValueError("THINGS section has no list lines")
        lines.insert(thing_lines[-1] + 1, addition)
    result = "\n".join(lines)
    return f"{result}\n" if trailing_newline else result


def _diff(control: str, variant: str, arm: int) -> str:
    def diff_lines(text: str) -> list[str]:
        lines = text.splitlines(keepends=True)
        return [line if line.endswith("\n") else f"{line}\n" for line in lines]

    return "".join(
        difflib.unified_diff(
            diff_lines(control),
            diff_lines(variant),
            fromfile="control",
            tofile=f"arm-{arm}",
        )
    )


def _with_arms(prompt: dict[str, Any]) -> dict[str, Any]:
    control = prompt["control"]
    arms = {
        str(arm): {
            "system": control["system"],
            "user": arm_user_text(control["user"], arm, prompt.get("command")),
        }
        for arm in range(4)
    }
    return {
        **prompt,
        "arms": arms,
        "diffs": {str(arm): _diff(control["user"], arms[str(arm)]["user"], arm) for arm in (1, 2, 3)},
    }


def _distinct_prompt_groups(prompts: list[dict[str, Any]]) -> list[dict[str, Any]]:
    groups: list[dict[str, Any]] = []
    by_key: dict[tuple[str, str], dict[str, Any]] = {}
    for prompt in prompts:
        control = prompt["control"]
        key = (control["system"], control["user"])
        group = by_key.get(key)
        if group is None:
            group = {
                "prompt": prompt,
                "prompt_ids": [prompt["id"]],
                "collapsed_prompt_ids": [],
            }
            by_key[key] = group
            groups.append(group)
        else:
            group["prompt_ids"].append(prompt["id"])
            group["collapsed_prompt_ids"].append(prompt["id"])
    return groups


def dry_document(prompts: list[dict[str, Any]]) -> dict[str, Any]:
    enriched = [_with_arms(prompt) for prompt in prompts]
    return {
        "mode": "dry",
        "prompts": enriched,
        "prompts_identical": len({(prompt["control"]["system"], prompt["control"]["user"]) for prompt in prompts}) == 1,
        "system_identical": all(
            len({prompt["control"]["system"], *(prompt["arms"][str(arm)]["system"] for arm in range(4))}) == 1
            for prompt in enriched
        ),
    }


def _narration_from_reply(raw_response: str) -> tuple[str | None, str, bool]:
    try:
        outer = json.loads(raw_response)
        raw_reply = (
            outer["narration"] if isinstance(outer, dict) and isinstance(outer.get("narration"), str) else raw_response
        )
        payload = json.loads(raw_reply) if isinstance(raw_reply, str) else raw_reply
        segments = payload["segments"] if isinstance(payload, dict) else None
        if not isinstance(segments, list):
            raise ValueError("reply has no segments list")
        texts = [
            segment["text"]
            for segment in segments
            if isinstance(segment, dict) and isinstance(segment.get("text"), str)
        ]
        if len(texts) != len(segments):
            raise ValueError("reply has an invalid segment")
    except (KeyError, TypeError, ValueError, json.JSONDecodeError):
        return None, raw_response, False
    return " ".join(texts).strip(), raw_reply, True


def _body_from_http_error(error: HTTPError) -> str:
    try:
        body = error.read()
    except Exception:
        return ""
    return body.decode(errors="replace") if isinstance(body, bytes) else str(body)


def _quota_code(text: str) -> str | None:
    return next((code for code in QUOTA_CODES if code in text), None)


def _send_narrator(
    system: str,
    user: str,
    url: str,
    counter: CallCounter,
) -> dict[str, Any]:
    import storygame.runtime.cloudflare as cloudflare

    counter.before_call()
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
    request = Request(
        url,
        data=json.dumps(payload).encode(),
        headers=headers,
        method="POST",
    )
    try:
        with cloudflare.urlopen(request, timeout=float(os.environ.get("CLOUDFLARE_TIMEOUT", "15"))) as response:
            raw_response = response.read().decode(errors="replace")
            status = getattr(response, "status", 200)
        quota_code = _quota_code(raw_response)
        if quota_code is not None:
            counter.stop_reason = quota_code
            raise QuotaExceeded(quota_code, raw_response)
    except QuotaExceeded:
        raise
    except HTTPError as error:
        raw_response = _body_from_http_error(error)
        header_text = str(getattr(error, "headers", ""))
        quota_code = _quota_code(f"{header_text}\n{raw_response}")
        if quota_code is not None:
            counter.stop_reason = quota_code
            raise QuotaExceeded(quota_code, raw_response) from error
        status = error.code
        return {
            "status": status,
            "raw_response": raw_response,
            "raw_reply": raw_response,
            "narration": None,
            "usable": False,
            "error": f"HTTPError: {error}",
        }
    except Exception as error:
        return {
            "status": None,
            "raw_response": "",
            "raw_reply": "",
            "narration": None,
            "usable": False,
            "error": f"{type(error).__name__}: {error}",
        }

    narration, raw_reply, usable = _narration_from_reply(raw_response)
    return {
        "status": status,
        "raw_response": raw_response,
        "raw_reply": raw_reply,
        "narration": narration,
        "usable": usable,
        "error": None if usable else "unparseable narration reply",
    }


def run_samples(document: dict[str, Any], samples: int, max_calls: int, out: Path) -> dict[str, Any]:
    groups = _distinct_prompt_groups(document["prompts"])
    total = len(groups) * 4 * samples
    if total > max_calls:
        raise CallCapExceeded(f"requested {total} calls exceeds max-calls {max_calls}")
    url = os.environ.get("CLOUDFLARE_WORKER_URL", "").strip()
    if not url:
        raise ValueError("live mode requires CLOUDFLARE_WORKER_URL")

    result: dict[str, Any] = {
        "mode": "run",
        "samples_requested": samples,
        "max_calls": max_calls,
        "calls_requested": total,
        "calls_made": 0,
        "stop_reason": None,
        "distinct_prompt_count": len(groups),
        "prompt_collapses": {
            group["prompt"]["id"]: group["collapsed_prompt_ids"] for group in groups if group["collapsed_prompt_ids"]
        },
        "rows": [],
    }
    counter = CallCounter(max_calls)
    _write_json(out, result)
    for sample in range(samples):
        for arm in range(4):
            for group in groups:
                prompt = group["prompt"]
                arm_prompt = prompt["arms"][str(arm)]
                row = {
                    "sample": sample + 1,
                    "arm": arm,
                    "prompt_id": prompt["id"],
                    "system": arm_prompt["system"],
                    "user": arm_prompt["user"],
                }
                try:
                    row.update(_send_narrator(arm_prompt["system"], arm_prompt["user"], url, counter))
                except QuotaExceeded as error:
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
                    result["rows"].append(row)
                    result["calls_made"] = counter.calls_made
                    result["stop_reason"] = error.code
                    _write_json(out, result)
                    return result
                except CallCapExceeded as error:
                    result["stop_reason"] = "MAX_CALLS_EXCEEDED"
                    result["calls_made"] = counter.calls_made
                    _write_json(out, result)
                    raise error
                result["rows"].append(row)
                result["calls_made"] = counter.calls_made
                _write_json(out, result)
    return result


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser()
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--dry", action="store_true")
    mode.add_argument("--run", action="store_true")
    parser.add_argument("--samples", type=int, default=30)
    parser.add_argument("--max-calls", type=int, default=DEFAULT_MAX_CALLS)
    parser.add_argument("--confirm", action="store_true")
    parser.add_argument("--out", required=True, type=Path)
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = _build_parser()
    args = parser.parse_args(argv)
    if args.samples < 0 or args.max_calls < 0:
        parser.error("samples and max-calls must be non-negative")
    if args.run and (not args.confirm or not os.environ.get("CLOUDFLARE_WORKER_URL", "").strip()):
        print("live mode requires --confirm and CLOUDFLARE_WORKER_URL", file=sys.stderr)
        return 2
    if args.dry:
        os.environ.setdefault("CLOUDFLARE_WORKER_URL", "https://worker.example/turn")
    try:
        document = dry_document(build_control_prompts())
        if args.dry:
            _write_json(args.out, document)
            distinct_count = len(_distinct_prompt_groups(document["prompts"]))
            diff_count = len(document["prompts"]) * 3
            print(
                f"dry: {len(document['prompts'])} prompts built, {distinct_count} distinct, "
                f"4 arms, {diff_count} diffs, 0 calls"
            )
            return 0
        try:
            result = run_samples(document, args.samples, args.max_calls, args.out)
        except CallCapExceeded as error:
            print(str(error), file=sys.stderr)
            return 2
        print(f"run: recorded {result['calls_made']} calls; stop={result['stop_reason'] or 'completed'}")
        return 0
    except Exception as error:
        print(f"boarding probe failed: {error}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
