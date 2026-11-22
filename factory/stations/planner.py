"""Propose one deterministic story-data fix plan under the factory guard."""

from __future__ import annotations

import json
import re
import subprocess
import time
from collections.abc import Callable, Iterable
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any

from factory.guard import (
    CallResult,
    Caps,
    ModelGuard,
    Overloaded,
    ProviderLimit,
    RateLimited,
    SpendLedger,
    guarded_call,
)
from factory.limits import LimitReport, read_claude_stream
from storygame.story_package.models import StoryPackage

from .fix_plan import build_evidence, lint_plan

PLANNER_BRIEF = """You are a story-data fixer for an interactive-fiction engine.
Read the evidence packet as the complete context for this ticket.
Choose exactly one fix from the two kinds listed in the evidence packet's fix_menu.
Prefer the smallest change that would have let the failing turns succeed.
Timing and wording are your decision, and nobody will be asked to choose them.
The evidence includes precedents: fixes the project proved, fixes that lost, and things that must never be done.
Try a proven technique first, and never choose a fix listed as lost or never do.
Begin reason with "Precedent: " followed by the proven technique you follow.
If none covers the case, begin reason with "Precedent: none"; list checks and the reason it does not apply.
Keep reason at 400 characters or fewer.
The evidence lists the cause of each failing turn and how many turns share each cause.
Choose the fix for the most common cause that a proven technique in the precedents can fix,
and name that cause in the reason.

Return one plan object with exactly this JSON shape.
The version field is an integer.
The ticket_id, scene, kind, and reason fields are strings.
The evidence_keys field is a list of strings.
The kind field is either "add_pacing_beat" or "set_text".
For add_pacing_beat, include only the beat object below.
The beat id is a string.
The beat at_turn is an integer.
The beat text is a string.
The beat verbatim and trailing fields are booleans.
The beat when and sets fields map string fact names to boolean values.
A beat must not set a fact another beat or claim sets unless its when guard pins that fact to the opposite value.
For set_text, include only the set_text object below.
The set_text address and text fields are strings.

The deterministic lint checks that a beat id uses the safe pattern and scene suffix.
It checks that the beat turn is inside the scene window and before the handoff.
It checks that every beat fact is declared.
It checks that a beat does not set an exit trigger or dependency.
It checks that authored text has 20 to 600 characters, uses plain words, and contains no ids or braces.
It checks that evidence_keys are taken from failing-turn packets.
Choose a beat only when its timing and predicates are supported by the evidence.
Choose set_text only when the evidence identifies a sentence that needs the smallest wording change.
Reply with ONE JSON object and nothing else.
When check output is shown, the plan was applied and the check failed, so reply with a revised plan \
that fixes the reason shown.

{
  "version": 1,
  "ticket_id": "string",
  "scene": "string",
  "kind": "add_pacing_beat or set_text",
  "reason": "string",
  "evidence_keys": ["string"],
  "beat": {
    "id": "string",
    "at_turn": 1,
    "text": "string",
    "verbatim": true,
    "trailing": false,
    "when": {"string": true},
    "sets": {"string": true}
  },
  "set_text": {"address": "string", "text": "string"}
}
"""


@dataclass(frozen=True)
class PlanOutcome:
    """The accepted plan, or the final deterministic problems after retries."""

    plan: dict | None
    tokens: int
    problems: list[str]
    attempts: int


def _compact_json(value: object) -> str:
    return json.dumps(value, ensure_ascii=False, separators=(",", ":"))


def build_prompt(
    evidence: dict,
    problems: list[str] | None = None,
    previous_plan: dict | None = None,
    check_output: str | None = None,
) -> str:
    """Compose the fixed brief, evidence, and optional verbatim retry verdicts."""

    sections = [PLANNER_BRIEF, _compact_json(evidence)]
    if previous_plan is not None:
        sections.append("Previous plan:\n" + _compact_json(previous_plan))
    if check_output is not None:
        sections.append("Check output (this plan was applied and the check failed):\n" + check_output)
    if problems is not None:
        sections.append("Lint problems:\n" + "\n".join(problems))
    return "\n\n".join(sections)


def extract_plan(text: str) -> dict | None:
    """Return the first parseable balanced top-level JSON object in text."""

    decoder = json.JSONDecoder()
    for index, character in enumerate(text):
        if character != "{":
            continue
        try:
            value, _end = decoder.raw_decode(text[index:])
        except (json.JSONDecodeError, TypeError):
            continue
        if isinstance(value, dict):
            return value
    return None


def _as_text(value: object) -> str:
    if isinstance(value, bytes):
        return value.decode(errors="replace")
    return "" if value is None else str(value)


def _stream_events(lines: Iterable[str]) -> tuple[list[dict[str, Any]], str | None]:
    events: list[dict[str, Any]] = []
    result_text: str | None = None
    for line in lines:
        try:
            event = json.loads(line)
        except (json.JSONDecodeError, TypeError):
            continue
        if not isinstance(event, dict):
            continue
        events.append(event)
        if event.get("type") == "result" and isinstance(event.get("result"), str):
            result_text = event["result"]
    return events, result_text


def _assistant_text(events: Iterable[dict[str, Any]]) -> str:
    blocks: list[str] = []
    for event in events:
        if event.get("type") != "assistant":
            continue
        message = event.get("message")
        content = message.get("content") if isinstance(message, dict) else event.get("content")
        if not isinstance(content, list):
            continue
        for block in content:
            if isinstance(block, dict) and isinstance(block.get("text"), str):
                blocks.append(block["text"])
    return "".join(blocks)


def _usage_tokens(events: Iterable[dict[str, Any]]) -> int:
    for event in events:
        if event.get("type") != "result":
            continue
        usage = event.get("usage")
        if not isinstance(usage, dict):
            return 0
        input_tokens = usage.get("input_tokens", 0)
        output_tokens = usage.get("output_tokens", 0)
        if not isinstance(input_tokens, (int, float)) or isinstance(input_tokens, bool):
            input_tokens = 0
        if not isinstance(output_tokens, (int, float)) or isinstance(output_tokens, bool):
            output_tokens = 0
        # Cache input tokens are deliberately excluded from the billed token count.
        return int(input_tokens + output_tokens)
    return 0


def _total_cost(events: Iterable[dict[str, Any]]) -> float | None:
    for event in events:
        if event.get("type") != "result":
            continue
        value = event.get("total_cost_usd")
        if isinstance(value, (int, float)) and not isinstance(value, bool):
            return float(value)
        return None
    return None


def _rejected(report: LimitReport | None) -> bool:
    return report is not None and any(window.rejected for window in report.windows)


def _failure_tail(output: str, limit: int = 4000) -> str:
    return output[-limit:].strip()


def claude_call(
    prompt: str,
    *,
    model_id: str,
    effort: str,
    run: Callable[..., subprocess.CompletedProcess] = subprocess.run,
    timeout: int = 900,
) -> CallResult:
    """Run Claude Code without tools or slash commands and parse its stream."""

    argv = [
        "claude",
        "-p",
        "--model",
        model_id,
        "--effort",
        effort,
        "--output-format",
        "stream-json",
        "--verbose",
        "--tools",
        "",
        "--disable-slash-commands",
        "--no-session-persistence",
    ]
    completed = run(argv, input=prompt, text=True, capture_output=True, timeout=timeout)
    stdout = _as_text(getattr(completed, "stdout", ""))
    stderr = _as_text(getattr(completed, "stderr", ""))
    stream = stdout.splitlines()
    events, result_text = _stream_events(stream)
    limits = read_claude_stream(stream)
    output = stdout + stderr
    lowered = output.lower()
    if getattr(completed, "returncode", 0) != 0:
        if "429" in lowered or "rate limit" in lowered:
            raise RateLimited()
        if "overloaded" in lowered:
            raise Overloaded()
    if _rejected(limits) or re.search(r"usage limit(?: was)? reached", lowered):
        raise ProviderLimit(None, limits)
    if getattr(completed, "returncode", 0) != 0:
        raise RuntimeError(_failure_tail(output) or f"claude exited with status {completed.returncode}")

    answer = result_text if result_text is not None else _assistant_text(events)
    return CallResult(answer, _usage_tokens(events), _total_cost(events), limits)


def make_planner(
    *,
    guard: ModelGuard,
    ledger: SpendLedger,
    caps: Caps,
    run: Callable[..., subprocess.CompletedProcess] = subprocess.run,
    sleep: Callable[[float], None] = time.sleep,
    max_attempts: int = 3,
    model_id: str = "claude-sonnet-5-5",
    effort: str = "high",
) -> Callable[..., PlanOutcome]:
    """Build a guarded planner callable for one wiring ticket."""

    def planner(
        ticket: Any,
        package: StoryPackage,
        now: datetime,
        *,
        feedback_plan: dict | None = None,
        check_output: str | None = None,
    ) -> PlanOutcome:
        evidence = build_evidence(ticket.payload, package)
        ticket_payload = dict(ticket.payload)
        ticket_payload.setdefault("scene", ticket.scene)
        total_tokens = 0
        attempts = 0
        problems: list[str] = []
        previous_plan: dict | None = feedback_plan

        for _attempt in range(max_attempts):
            prompt = build_prompt(
                evidence,
                problems if attempts else None,
                previous_plan,
                check_output if not attempts else None,
            )
            result = guarded_call(
                guard=guard,
                ledger=ledger,
                caps=caps,
                station="wiring",
                model_id=model_id,
                effort=effort,
                scene=ticket.scene,
                ticket_id=ticket.id,
                now=now,
                fn=lambda prompt=prompt: claude_call(prompt, model_id=model_id, effort=effort, run=run),
                sleep=sleep,
            )
            attempts += 1
            total_tokens += result.tokens
            plan = extract_plan(result.output) if isinstance(result.output, str) else None
            if plan is None:
                problems = ["plan.shape no JSON object in the reply"]
            else:
                plan["ticket_id"] = ticket.id
                plan["scene"] = ticket.scene
                problems = lint_plan(plan, ticket_payload, package)
                if not problems:
                    return PlanOutcome(plan, total_tokens, [], attempts)
                previous_plan = plan
            if total_tokens >= ticket.token_budget:
                break

        return PlanOutcome(None, total_tokens, problems, attempts)

    return planner


def _load_config(root: Path) -> tuple[dict[str, Any], Path]:
    config_root = root
    config_path = config_root / "factory/config/factory.json"
    if not config_path.is_file():
        config_root = Path(__file__).resolve().parents[2]
        config_path = config_root / "factory/config/factory.json"
    return json.loads(config_path.read_text(encoding="utf-8")), config_root


def default_planner(root: Path | None = None):
    """Build the wiring planner from the repository's guard and budget files."""

    repository_root = Path(root) if root is not None else Path(__file__).resolve().parents[2]
    config, config_root = _load_config(repository_root)
    paths = config["paths"]

    def resolve(value: object) -> Path:
        if not isinstance(value, (str, Path)):
            raise ValueError("path must be a string")
        path = Path(value)
        return path if path.is_absolute() else repository_root / path

    allowlist = resolve(paths["allowlist"])
    if not allowlist.is_file():
        allowlist = config_root / paths["allowlist"]
    return make_planner(
        guard=ModelGuard.from_file(allowlist),
        ledger=SpendLedger(resolve(paths["ledger"])),
        caps=Caps.from_dict(config["caps"]),
    )


__all__ = [
    "PLANNER_BRIEF",
    "PlanOutcome",
    "build_prompt",
    "claude_call",
    "default_planner",
    "extract_plan",
    "make_planner",
]
