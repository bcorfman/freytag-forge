"""Matcher and continuation helpers for the standardized fresh 2B state."""

from __future__ import annotations

import copy
from typing import Any

import yaml

from storygame.runtime.candidate_matcher import _matches_all
from storygame.runtime.cloudflare import NarrationProviderError
from storygame.runtime.engine import RuntimeEngine
from storygame.runtime.reveal_eligibility import explain_reveal

ROOT = __import__("pathlib").Path(__file__).resolve().parents[3]


def action_groups(
    path=ROOT / "data/stories/continuity-initiative/knowledge.yaml",
) -> dict[str, tuple[tuple[str, ...], ...]]:
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    return {
        e["id"]: tuple(tuple(g) for g in e["action_evidence"])
        for e in data["knowledge"]
        if "2B" in (e.get("available_in_scenes") or []) and e.get("action_evidence")
    }


def eligible_groups(state: Any, command: str) -> dict[str, Any]:
    groups = {}
    for entry in state.package.knowledge.knowledge:
        if "2B" not in (entry.available_in_scenes or ()) or not entry.action_evidence:
            continue
        eligibility = explain_reveal(state, "player", entry)
        groups[entry.id] = {
            "evidence": tuple(tuple(g) for g in entry.action_evidence),
            "eligible": bool(eligibility.eligible),
            "reason": getattr(eligibility, "reason", None),
            "matched": bool(eligibility.eligible)
            and _matches_all(tuple(tuple(g) for g in entry.action_evidence), command),
        }
    return groups


def matched_ids(groups: dict[str, Any], command: str) -> list[str]:
    return sorted(
        identifier for identifier, value in groups.items() if value.get("eligible", True) and value["matched"]
    )


def state_snapshot(state: Any) -> Any:
    return copy.deepcopy(state)


def committed_reveals(before: Any, after: Any) -> list[str]:
    old = {identifier for record in before.turn_records for identifier in record.reveal_ids}
    new = {identifier for record in after.turn_records for identifier in record.reveal_ids}
    return sorted(new - old)


def fact_keys(state: Any) -> list[str]:
    return sorted("|".join(str(part) for part in fact.key) for fact in state.facts.asserted)


def score_command(
    engine: RuntimeEngine,
    state: Any,
    command: str,
    *,
    target_reveal: str | None = None,
    clarifies: str | None = None,
    clarification_round: int = 0,
    already_committed: frozenset[str] = frozenset(),
) -> dict[str, Any]:
    """Score one turn, using raw command text when no resolved command is exposed."""

    before = state.snapshot()
    groups = eligible_groups(state, command)
    eligible = sorted(identifier for identifier, value in groups.items() if value["eligible"])
    matched = matched_ids(groups, command)
    record: dict[str, Any] = {
        "command": command,
        "eligible": eligible,
        "matched": matched,
        "evidence": {key: value["evidence"] for key, value in groups.items()},
        "eligibility": {
            key: {"eligible": value["eligible"], "reason": value["reason"]} for key, value in groups.items()
        },
        "before_facts": fact_keys(state),
        "status": "unearned",
    }
    if target_reveal is not None:
        record.update({"target_reveal": target_reveal, "target_committed": False})
    try:
        turn_kwargs = {}
        if clarifies is not None:
            turn_kwargs = {"clarifies": clarifies, "clarification_round": clarification_round}
        response = engine.turn(command, **turn_kwargs)
    except NarrationProviderError:
        raise
    except Exception as error:
        record.update({"response": getattr(error, "message", str(error)), "status": "rejected", "error": str(error)})
        state.restore_snapshot(before)
        record["after_facts"] = fact_keys(state)
        return record
    after = state.snapshot()
    committed = committed_reveals(before, after)
    resolved_command = getattr(getattr(engine, "last_reference_resolution", None), "command", None) or command
    post_groups = eligible_groups(state, resolved_command)
    eligible_post = sorted(identifier for identifier, value in post_groups.items() if value["eligible"])
    matched_post = matched_ids(post_groups, resolved_command)
    is_clarification = hasattr(response, "clarification")
    target_committed = target_reveal is not None and target_reveal in committed
    already_established = target_reveal is not None and target_reveal in already_committed
    earned = (
        target_committed and not already_established
        if target_reveal is not None
        else len(matched) == 1 and committed == matched
    )
    record.update(
        {
            "response": response.narration,
            "status": (
                "clarification"
                if is_clarification
                else "already_established"
                if already_established
                else "earned"
                if earned
                else "rejected"
                if getattr(response, "game_break", None)
                else "unearned"
            ),
            "committed_reveals": committed,
            "eligible_post": eligible_post,
            "matched_post": matched_post,
            "after_facts": fact_keys(state),
            "rejection": getattr(engine.last_attempt.rejection, "model_dump", lambda: None)()
            if engine.last_attempt and engine.last_attempt.rejection
            else None,
        }
    )
    if target_reveal is not None:
        record.update({"target_reveal": target_reveal, "target_committed": target_committed})
    if is_clarification:
        record["clarification_question"] = response.narration
    return record
