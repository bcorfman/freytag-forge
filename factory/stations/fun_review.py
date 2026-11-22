"""Review a merge-bound story-data fix for scene-level fun and momentum."""

from __future__ import annotations

import hashlib
import json
import re
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
from storygame.story_package.loader import load_story_package

from .wiring import _story_root


@dataclass(frozen=True)
class ReviewReply:
    """The reviewer's text and the provider-reported token count."""

    text: str
    tokens: int


FUN_REVIEW_CHECKS = (
    "fits_scene",
    "gives_a_reason_to_act",
    "keeps_pace",
    "fits_freytag_phase",
    "characters_in_character",
    "continuity_within_scene",
    "continuity_between_scenes",
)

FUN_REVIEW_BRIEF = (
    "You are the story editor for an interactive-fiction game whose scenes must stay fun.\n"
    "A fix was just made to the story data to repair turns where players got stuck. Read the diff and judge it.\n"
    "Fun for the player means three things together: Freytag story pacing, quality characters, and continuity in and "
    "between scenes.\n"
    "Answer these seven yes/no questions:\n"
    "- fits_scene: does the new or changed text fit the scene's tone and objective?\n"
    "- gives_a_reason_to_act: does it give the player a clue, a hook or a choice, rather than filler or a dead end?\n"
    "- keeps_pace: does it avoid dead time, avoid stacking two pressure moments within two turns of each other, and "
    "avoid giving away a later reveal?\n"
    "- fits_freytag_phase: given the scene's Freytag phase and the phases of the scenes around it in the arc shown, "
    "does the change do the job of that phase: exposition orients and invites, rising action adds pressure or "
    "complication, crisis and climax sharpen the stakes, and falling action and resolution release and close; and "
    "does it avoid jumping ahead of the arc or releasing tension too early?\n"
    "- characters_in_character: do the characters in the changed text act and speak in keeping with their biographies, "
    "personalities and motives shown, and does nobody know or do something they have not learned or would not choose?\n"
    "- continuity_within_scene: is there no contradiction with the places, objects, facts and what the player knows in "
    "the nearby text and in the scene context shown?\n"
    "- continuity_between_scenes: is it consistent with how the previous scene hands over, the bridge text, and what "
    "the next scene expects, without changing what the player carries or knows into or out of the scene or pre-empting "
    "the next scene's entry?\n\n"
    "Reply with ONE JSON object and nothing else:\n"
    '{"verdict": "pass" or "block", "checks": {"fits_scene": true, '
    '"gives_a_reason_to_act": true, "keeps_pace": true, "fits_freytag_phase": true, '
    '"characters_in_character": true, "continuity_within_scene": true, "continuity_between_scenes": true}, '
    '"reasons": "one to three plain sentences"}\n'
    "Block when any answer is no or missing. A fix that only moves words around without a reason is a block."
)

FUN_REVIEW_BRIEF_HASH = hashlib.sha256(
    "\n".join((FUN_REVIEW_BRIEF, *sorted(FUN_REVIEW_CHECKS))).encode("utf-8")
).hexdigest()[:16]

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
    scene_context: dict | None = None,
) -> str:
    """Build the complete, story-agnostic review packet in a fixed order."""

    sections = [FUN_REVIEW_BRIEF, f"Scene: {scene_id}"]
    if criteria_text:
        sections.append("Review criteria:\n" + criteria_text)
    if scene_context is not None:
        sections.append("Scene context:\n" + _compact_json(scene_context))
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


def _compact_json(value: object) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def _cut(value: str, limit: int) -> str:
    return value[:limit]


def _context_string_locations(value: object) -> list[tuple[object, object, str]]:
    locations: list[tuple[object, object, str]] = []
    if isinstance(value, dict):
        for key, child in value.items():
            if isinstance(child, str):
                locations.append((value, key, child))
            else:
                locations.extend(_context_string_locations(child))
    elif isinstance(value, list):
        for index, child in enumerate(value):
            if isinstance(child, str):
                locations.append((value, index, child))
            else:
                locations.extend(_context_string_locations(child))
    return locations


def _fit_scene_context(context: dict[str, Any]) -> dict[str, Any]:
    while len(_compact_json(context)) > 6000:
        locations = _context_string_locations(context)
        if not locations:
            break
        container, key, current = max(locations, key=lambda item: len(item[2]))
        excess = len(_compact_json(context)) - 6000
        new_length = max(0, len(current) - max(1, excess))
        if new_length == len(current):
            new_length -= 1
        container[key] = current[:new_length]  # type: ignore[index]
    return context


def _neighbor_context(scene: Any, bridge_text: object) -> dict[str, Any]:
    metadata = scene.metadata
    return {
        "scene_id": metadata.scene_id,
        "freytag_phase": metadata.freytag_phase,
        "objective": metadata.objective,
        "entry_text": _cut(metadata.entry_text, 400),
        "bridge_text": [_cut(str(value), 400) for value in list(bridge_text)[:3]],
    }


def build_scene_context(package: Any, scene_id: str) -> dict[str, Any]:
    """Build a bounded, story-package-only context packet for one scene."""

    scene = next((item for item in package.scenes if item.metadata.scene_id == scene_id), None)
    if scene is None:
        return {"scene": {"id": scene_id}}

    metadata = scene.metadata
    pacing = next((item for item in package.pacing.scenes if item.scene_id == scene_id), None)
    scene_context: dict[str, Any] = {
        "scene": {
            "id": metadata.scene_id,
            "freytag_phase": metadata.freytag_phase,
            "objective": metadata.objective,
            "entry_text": _cut(metadata.entry_text, 600),
        },
        "arc": [],
        "position": None,
        "cast": [],
        "previous": None,
        "next": None,
    }
    if pacing is not None:
        scene_context["scene"].update(
            {
                "min_turns": pacing.min_turns,
                "nudge_after_turns": pacing.nudge_after_turns,
                "handoff_after_turns": pacing.handoff_after_turns,
            }
        )

    scene_by_id = {item.metadata.scene_id: item for item in package.scenes}
    chain = list(package.storylet_routes.canonical_scene_chain)
    scene_context["arc"] = [
        {
            "scene_id": chain_scene_id,
            "freytag_phase": scene_by_id[chain_scene_id].metadata.freytag_phase,
        }
        for chain_scene_id in chain
    ]
    if scene_id in chain:
        position = chain.index(scene_id)
        scene_context["position"] = [position + 1, len(chain)]
        if position:
            previous_scene = scene_by_id[chain[position - 1]]
            scene_context["previous"] = _neighbor_context(previous_scene, previous_scene.metadata.bridge_text.values())
        if position + 1 < len(chain):
            next_scene = scene_by_id[chain[position + 1]]
            scene_context["next"] = _neighbor_context(next_scene, metadata.bridge_text.values())

    character_by_id = {character.id: character for character in package.characters}
    participant_ids = list(dict.fromkeys((*metadata.participant_ids, *metadata.companions)))
    for character_id in participant_ids:
        character = character_by_id.get(character_id)
        if character is None:
            scene_context["cast"].append({"id": character_id})
        else:
            scene_context["cast"].append({"id": character.id, "name": character.name, "bio": _cut(character.bio, 500)})

    return _fit_scene_context(scene_context)


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


def _first_failing_check(checks: dict[str, Any]) -> str | None:
    return next((key for key in FUN_REVIEW_CHECKS if checks.get(key) is not True), None)


def _review_reason(reasons: str, checks: dict[str, Any]) -> str:
    value = _one_line(reasons)
    if not value:
        value = "reviewer blocked the fix"
    value = " ".join(re.split(r"(?<=[.!?])\s+", value)[:3])
    first_failing = _first_failing_check(checks)
    if first_failing is not None and first_failing not in value:
        value = f"{first_failing}: {value}"
    return value


def _evaluate_review(
    verdict: str,
    checks: dict[str, Any],
    reasons: str,
    diff_hash: str,
    *,
    tokens: int = 0,
) -> tuple[bool, str, StationResult]:
    normalized_reasons = _review_reason(reasons, checks)
    passed = verdict == "pass" and bool(reasons.strip()) and _first_failing_check(checks) is None
    if passed:
        result = StationResult(
            True,
            "fun_review",
            normalized_reasons,
            tokens=tokens,
            payload_updates={"fun_review": {"verdict": "pass", "diff_hash": diff_hash, "reasons": normalized_reasons}},
        )
    else:
        result = StationResult(
            False,
            "fun_review",
            "fun review blocked the fix: " + normalized_reasons,
            tokens=tokens,
        )
    return passed, normalized_reasons, result


def _saved_result(saved: dict[str, Any], diff_hash: str) -> StationResult | None:
    if saved.get("diff_hash") != diff_hash or saved.get("brief_hash") != FUN_REVIEW_BRIEF_HASH:
        return None
    verdict = saved.get("verdict")
    checks = saved.get("checks")
    reasons = saved.get("reasons")
    if verdict not in {"pass", "block"} or not isinstance(checks, dict) or not isinstance(reasons, str):
        return None
    return _evaluate_review(verdict, checks, reasons, diff_hash)[2]


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
    package_loader: Callable[[Path], Any] | None = None,
) -> StationHandler:
    """Return the lazy station-10 fun review handler."""

    repository_root = _repository_root(root)
    invoke = runner or _default_runner
    resolved_reviewer = reviewer
    resolved_package_loader = package_loader or load_story_package

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
        try:
            package = resolved_package_loader(_story_root(tree))
            scene_context = build_scene_context(package, ticket.scene)
        except Exception:
            return StationResult(False, "fun_review", "could not load the story package for the review")
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
            scene_context,
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
        passed, reasons, review_result = _evaluate_review(
            verdict,
            checks,
            reasons,
            diff_hash,
            tokens=total_tokens,
        )
        record = {
            "brief_hash": FUN_REVIEW_BRIEF_HASH,
            "diff_hash": diff_hash,
            "verdict": "pass" if passed else "block",
            "reasons": reasons,
            "checks": checks,
            "reviewed_at": now.isoformat(),
        }
        _atomic_json_write(review_path, record)
        return review_result

    return handle


__all__ = [
    "FUN_REVIEW_BRIEF",
    "FUN_REVIEW_CHECKS",
    "FUN_REVIEW_EFFORT",
    "FUN_REVIEW_MODEL_ID",
    "ReviewReply",
    "build_scene_context",
    "build_review_prompt",
    "default_reviewer",
    "fun_review_handler",
]
