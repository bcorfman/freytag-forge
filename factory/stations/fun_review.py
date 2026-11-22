"""Review a merge-bound story-data fix for scene-level fun and momentum."""

from __future__ import annotations

import json
import subprocess
from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any

from factory.followups import _safe_id
from factory.guard import Caps, ModelGuard, SpendLedger, guarded_call
from factory.line import StationHandler, StationResult
from factory.stations.deliver import (
    _atomic_json_write,
    _changed_paths,
    _default_runner,
    _diff_hash,
    _one_line,
    _record,
    _run,
)
from factory.stations.planner import _load_config, claude_call, extract_plan
from factory.stations.tree import ticket_tree


@dataclass(frozen=True)
class ReviewReply:
    """The reviewer's text and the provider-reported token count."""

    text: str
    tokens: int


FUN_REVIEW_BRIEF = (
    "You are the story editor for an interactive-fiction game whose scenes must stay fun.\n"
    "A fix was just made to the story data to repair turns where players got stuck. Read the diff and judge it.\n"
    "Answer these three yes/no questions:\n"
    "- fits_scene: does the new or changed text fit the scene's tone and only what the player knows at that point, "
    "with no contradiction of the nearby text shown?\n"
    "- gives_a_reason_to_act: does it give the player a clue, a hook or a choice, rather than filler or a dead end?\n"
    "- keeps_pace: does it avoid adding dead time, stacking two pressure moments within two turns of each other, "
    "or giving away a later reveal?\n\n"
    "Reply with ONE JSON object and nothing else:\n"
    '{"verdict": "pass" or "block", "checks": {"fits_scene": true, '
    '"gives_a_reason_to_act": true, "keeps_pace": true}, '
    '"reasons": "one to three plain sentences"}\n'
    "Block when any answer is no. A fix that only moves words around without a reason is a block."
)

_RUNNER = Callable[[list[str], Path], tuple[int, str]]
_RETRY_LINE = "Your last reply was not valid. Reply with the JSON object only."
_DIFF_LIMIT = 16000
FUN_REVIEW_MODEL_ID = "claude-opus-5-5"
FUN_REVIEW_EFFORT = "medium"


def _repository_root(root: Path | None) -> Path:
    return Path(root) if root is not None else Path(__file__).resolve().parents[2]


def _review_criteria(payload: dict[str, Any], tree: Path) -> str | None:
    value = payload.get("review_criteria_path")
    if not isinstance(value, str):
        return None
    path = Path(value).expanduser()
    if not path.is_absolute():
        path = tree / path
    try:
        if not path.is_file():
            return None
        return path.read_text(encoding="utf-8")[:6000]
    except (OSError, UnicodeError):
        return None


def _turn_evidence(payload: dict[str, Any]) -> list[dict[str, str]]:
    raw = payload.get("failing_turns")
    if not isinstance(raw, list):
        return []
    evidence: list[dict[str, str]] = []
    for packet in raw[:12]:
        if not isinstance(packet, dict):
            continue
        evidence.append(
            {
                "key": _one_line(str(packet.get("key", "")))[:200],
                "player_input": _one_line(str(packet.get("player_input", "")))[:200],
                "narration": _one_line(str(packet.get("narration", "")))[:200],
            }
        )
    return evidence


def build_review_prompt(
    scene_id: str,
    criteria_text: str | None,
    failing_turns: list[dict[str, str]],
    plan_reason: str | None,
    diff: str,
) -> str:
    """Build the complete, story-agnostic review packet in a fixed order."""

    sections = [FUN_REVIEW_BRIEF, f"Scene: {scene_id}"]
    if criteria_text:
        sections.append("Review criteria:\n" + criteria_text)
    evidence_lines = ["Failing-turn evidence:"]
    if failing_turns:
        evidence_lines.append(json.dumps(failing_turns, ensure_ascii=False, sort_keys=True))
    else:
        evidence_lines.append("[]")
    if plan_reason is not None:
        evidence_lines.append("Plan reason: " + _one_line(plan_reason))
    sections.append("\n".join(evidence_lines))
    sections.append("Diff:\n" + diff)
    return "\n\n".join(sections)


def _plan_reason(workspace: Path, safe_id: str) -> str | None:
    value = _record(workspace / safe_id / "plan.json")
    reason = value.get("reason") if value is not None else None
    return reason if isinstance(reason, str) else None


def _review_diff(runner: _RUNNER, tree: Path, paths: list[str]) -> tuple[str | None, str | None]:
    passed, output = _run(runner, ["git", "merge-base", "HEAD", "origin/main"], tree)
    if not passed or not output.strip():
        return None, "could not inspect tree diff"
    merge_base = output.strip().splitlines()[-1]
    passed, output = _run(runner, ["git", "diff", "-U30", merge_base, "--", *paths], tree)
    if not passed:
        return None, _one_line(output) or "could not inspect tree diff"
    pieces = [output]
    passed, untracked_output = _run(runner, ["git", "ls-files", "--others", "--exclude-standard"], tree)
    if not passed:
        return None, _one_line(untracked_output) or "could not inspect untracked files"
    for path in untracked_output.splitlines():
        if not path.strip() or path not in paths:
            continue
        try:
            content = (tree / path).read_text(encoding="utf-8")
        except (OSError, UnicodeError) as error:
            return None, _one_line(str(error) or "could not read changed file")
        pieces.append(f"\n--- untracked: {path} ---\n{content}")
    value = "".join(pieces)
    if len(value) > _DIFF_LIMIT:
        marker = "[diff cut at 16000 characters]"
        value = value[: _DIFF_LIMIT - len(marker) - 1] + "\n" + marker
    return value, None


def _saved_result(saved: dict[str, Any], diff_hash: str) -> StationResult | None:
    if saved.get("diff_hash") != diff_hash:
        return None
    verdict = saved.get("verdict")
    checks = saved.get("checks")
    reasons = saved.get("reasons")
    if verdict not in {"pass", "block"} or not isinstance(checks, dict) or not isinstance(reasons, str):
        return None
    reasons = _one_line(reasons)
    if (
        verdict == "pass"
        and reasons
        and all(checks.get(key) is True for key in ("fits_scene", "gives_a_reason_to_act", "keeps_pace"))
    ):
        return StationResult(
            True,
            "fun_review",
            reasons,
            payload_updates={"fun_review": {"verdict": "pass", "diff_hash": diff_hash, "reasons": reasons}},
        )
    return StationResult(False, "fun_review", "fun review blocked the fix: " + reasons)


def default_reviewer(
    root: Path | None = None,
    *,
    run: Callable[..., subprocess.CompletedProcess] = subprocess.run,
    model_id: str = FUN_REVIEW_MODEL_ID,
) -> Callable[[Any, str, datetime], ReviewReply]:
    """Build the guarded Opus reviewer from the repository config files."""

    repository_root = _repository_root(root)
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
    guard = ModelGuard.from_file(allowlist)
    ledger = SpendLedger(resolve(paths["ledger"]))
    caps = Caps.from_dict(config["caps"])

    def review(ticket: Any, prompt: str, now: datetime) -> ReviewReply:
        result = guarded_call(
            guard=guard,
            ledger=ledger,
            caps=caps,
            station="fun_review",
            model_id=model_id,
            effort=FUN_REVIEW_EFFORT,
            scene=ticket.scene,
            ticket_id=ticket.id,
            now=now,
            fn=lambda: claude_call(
                prompt,
                model_id=model_id,
                effort=FUN_REVIEW_EFFORT,
                run=run,
            ),
        )
        return ReviewReply(result.output, result.tokens)

    return review


def _verdict(reply: ReviewReply) -> tuple[str, dict[str, Any], str] | None:
    value = extract_plan(reply.text)
    if value is None:
        return None
    verdict = value.get("verdict")
    checks = value.get("checks")
    if verdict not in {"pass", "block"} or not isinstance(checks, dict):
        return None
    reasons = value.get("reasons")
    if not isinstance(reasons, str) or not reasons.strip():
        return verdict, checks, ""
    return verdict, checks, _one_line(reasons)


def fun_review_handler(
    root: Path | None = None,
    *,
    reviewer: Callable[[Any, str, datetime], ReviewReply] | None = None,
    runner: _RUNNER | None = None,
) -> StationHandler:
    """Return the lazy station-10 fun review handler."""

    repository_root = _repository_root(root)
    invoke = runner or _default_runner
    resolved_reviewer = reviewer

    def handle(ticket: Any, now: datetime) -> StationResult:
        nonlocal resolved_reviewer
        payload = ticket.payload
        if payload.get("merge_to_main") is not True:
            return StationResult(False, "fun_review", "ticket is not authorized to merge to main")
        workspace_value = payload.get("workspace")
        if not isinstance(workspace_value, str):
            return StationResult(False, "fun_review", "missing payload key: workspace")
        tree = ticket_tree(payload, ticket.id, repository_root)
        if tree is None:
            return StationResult(False, "fun_review", "ticket tree not found")
        workspace = Path(workspace_value).expanduser()
        paths, error = _changed_paths(invoke, tree)
        if error:
            return StationResult(False, "fun_review", _one_line(error))
        assert paths is not None
        if not paths:
            return StationResult(False, "fun_review", "empty diff against origin/main")
        diff_hash, error = _diff_hash(invoke, tree, paths)
        if error or diff_hash is None:
            return StationResult(False, "fun_review", _one_line(error or "could not hash tree diff"))

        review_path = workspace / _safe_id(ticket.id) / "review.json"
        saved = _record(review_path) if review_path.exists() else None
        if saved is not None:
            reused = _saved_result(saved, diff_hash)
            if reused is not None:
                return reused

        diff, error = _review_diff(invoke, tree, paths)
        if error or diff is None:
            return StationResult(False, "fun_review", _one_line(error or "could not inspect tree diff"))
        prompt = build_review_prompt(
            ticket.scene,
            _review_criteria(payload, tree),
            _turn_evidence(payload),
            _plan_reason(workspace, _safe_id(ticket.id)),
            diff,
        )
        if resolved_reviewer is None:
            resolved_reviewer = default_reviewer(repository_root)

        total_tokens = 0
        parsed: tuple[str, dict[str, Any], str] | None = None
        for attempt in range(2):
            reply = resolved_reviewer(ticket, prompt if attempt == 0 else prompt + "\n\n" + _RETRY_LINE, now)
            total_tokens += reply.tokens
            parsed = _verdict(reply)
            if parsed is not None:
                break
        if parsed is None:
            return StationResult(False, "fun_review", "no usable verdict from the reviewer", tokens=total_tokens)

        verdict, checks, reasons = parsed
        passed = (
            verdict == "pass"
            and bool(reasons)
            and all(checks.get(key) is True for key in ("fits_scene", "gives_a_reason_to_act", "keeps_pace"))
        )
        if not reasons:
            reasons = "reviewer blocked the fix"
        record = {
            "diff_hash": diff_hash,
            "verdict": "pass" if passed else "block",
            "reasons": reasons,
            "checks": checks,
            "reviewed_at": now.isoformat(),
        }
        _atomic_json_write(review_path, record)
        if passed:
            return StationResult(
                True,
                "fun_review",
                reasons,
                tokens=total_tokens,
                payload_updates={"fun_review": {"verdict": "pass", "diff_hash": diff_hash, "reasons": reasons}},
            )
        return StationResult(False, "fun_review", "fun review blocked the fix: " + reasons, tokens=total_tokens)

    return handle


__all__ = [
    "FUN_REVIEW_BRIEF",
    "FUN_REVIEW_EFFORT",
    "FUN_REVIEW_MODEL_ID",
    "ReviewReply",
    "build_review_prompt",
    "default_reviewer",
    "fun_review_handler",
]
