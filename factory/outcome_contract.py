"""Story-agnostic core outcome classification."""

from __future__ import annotations

from collections.abc import Iterable
from typing import Any

_NEUTRAL_OUTCOMES = {"rejected", "noncommitted", "game_break"}


def _strings(value: Any) -> list[str] | None:
    if not isinstance(value, list) or not all(isinstance(item, str) for item in value):
        return None
    return value.copy()


def _scene_strings(scene: dict[str, Any], key: str) -> list[str]:
    value = scene.get(key)
    strings = _strings(value)
    return strings if strings is not None else []


def _turn_number(value: Any, fallback: int) -> int:
    return value if isinstance(value, int) and not isinstance(value, bool) else fallback


def _classify_action(turn: dict[str, Any], lists_valid: bool) -> str:
    if turn.get("game_break") is not None:
        return "game_break"
    if turn.get("rejected") is True or turn.get("outcome") == "rejected":
        return "rejected"
    if turn.get("outcome") != "committed":
        return "noncommitted"
    if not lists_valid:
        return "unknown_telemetry"
    if turn["committed_facts"]:
        return "world_changed"
    return "pending"


def _authored_recovery(turn: dict[str, Any]) -> bool:
    recovery = turn.get("recovery")
    return isinstance(recovery, dict) and recovery.get("cost_committed") is True and recovery.get("cost_shown") is True


def _stall_marks(
    classified: list[dict[str, Any]],
    candidates: list[list[str]],
    pacing_window: int | None,
) -> tuple[set[int], set[int]]:
    confirmed: set[int] = set()
    unresolved: set[int] = set()
    active: list[int] = []
    active_candidates = False

    def finish() -> None:
        nonlocal active, active_candidates
        if active:
            if pacing_window is None:
                unresolved.update(active)
            elif len(active) >= pacing_window and active_candidates:
                confirmed.update(active)
            elif len(active) >= pacing_window:
                unresolved.update(active)
        active = []
        active_candidates = False

    for item, offered in zip(classified, candidates, strict=True):
        outcome = item["action_outcome"]
        if outcome == "no_effect" and not item["authored_recovery"]:
            active.append(item["turn"])
            active_candidates = active_candidates or bool(offered)
        elif outcome in _NEUTRAL_OUTCOMES:
            continue
        else:
            finish()
    finish()
    return confirmed, unresolved


def _safe_union(values: Iterable[list[str]]) -> set[str]:
    result: set[str] = set()
    for value in values:
        result.update(value)
    return result


def _normalise_text(value: str) -> str:
    return " ".join(value.split())


def _quoted_segments(text: str) -> list[str]:
    segments: list[str] = []
    start: int | None = None
    closing: str | None = None
    for index, character in enumerate(text):
        if start is None:
            if character == '"':
                start, closing = index + 1, '"'
            elif character == "“":
                start, closing = index + 1, "”"
        elif character == closing:
            segments.append(text[start:index])
            start, closing = None, None
    if start is not None:
        segments.append(text[start:])
    return segments


def _provenance_flags(turns: list[Any], scene: dict[str, Any], delivered_before: set[str]) -> list[dict[str, Any]]:
    non_voiceable = [_normalise_text(value) for value in _scene_strings(scene, "non_voiceable_says")]
    unlearned: list[tuple[str, str]] = []
    raw_terms = scene.get("unlearned_terms")
    if isinstance(raw_terms, list):
        for entry in raw_terms:
            if (
                isinstance(entry, dict)
                and isinstance(entry.get("term"), str)
                and isinstance(entry.get("requires"), str)
            ):
                unlearned.append((_normalise_text(entry["term"]), entry["requires"]))

    prior_grounding = set(delivered_before)
    found: set[tuple[int | None, str, str]] = set()
    flags: list[tuple[int | None, str, str]] = []
    for index, raw_turn in enumerate(turns, start=1):
        turn = raw_turn if isinstance(raw_turn, dict) else {}
        number = _turn_number(turn.get("turn"), index) if isinstance(raw_turn, dict) else index
        text = turn.get("text")
        if isinstance(text, str):
            for segment in _quoted_segments(text):
                normalized_segment = _normalise_text(segment)
                for matched in non_voiceable:
                    if matched and matched in normalized_segment:
                        key = (number, "bookkeeping_voiced", matched)
                        if key not in found:
                            found.add(key)
                            flags.append(key)
                for term, requires in unlearned:
                    if term and term in normalized_segment and requires not in prior_grounding:
                        key = (number, "character_knowledge", term)
                        if key not in found:
                            found.add(key)
                            flags.append(key)
        grounding_ids = _strings(turn.get("grounding_ids"))
        if grounding_ids is not None:
            prior_grounding.update(grounding_ids)
    flags.sort(key=lambda item: (item[0] is None, item[0] if item[0] is not None else 0, item[1], item[2]))
    return [{"turn": turn, "kind": kind} for turn, kind, _ in flags]


def _epilogue(turns: list[Any], scene: dict[str, Any], exit_value: str) -> tuple[dict[str, bool], bool]:
    candidates = set(_scene_strings(scene, "epilogue_candidates"))
    if not candidates:
        return {"offered": False, "taken": False}, False
    latch_index = next(
        (
            index
            for index, raw_turn in enumerate(turns)
            if isinstance(raw_turn, dict) and raw_turn.get("ending_latched") is True
        ),
        None,
    )
    if latch_index is None:
        return {"offered": False, "taken": False}, False
    offered = False
    taken = False
    for raw_turn in turns[latch_index:]:
        if not isinstance(raw_turn, dict):
            continue
        offered_values = _strings(raw_turn.get("candidates_offered")) or []
        if candidates.intersection(offered_values):
            offered = True
        if isinstance(raw_turn.get("matched_candidate"), str) and raw_turn["matched_candidate"] in candidates:
            taken = True
    return {"offered": offered, "taken": taken and offered}, exit_value == "ending" and not offered


def _pacing(classified: list[dict[str, Any]], turns: list[Any]) -> dict[str, Any]:
    first_pressure: int | None = None
    first_pressure_index: int | None = None
    for index, raw_turn in enumerate(turns):
        if isinstance(raw_turn, dict) and raw_turn.get("pressure_event") is True:
            first_pressure = classified[index]["turn"]
            first_pressure_index = index
            break
    quiet_stretch = 0
    if first_pressure_index is not None:
        current = 0
        for item, raw_turn in zip(
            classified[first_pressure_index + 1 :], turns[first_pressure_index + 1 :], strict=True
        ):
            turn = raw_turn if isinstance(raw_turn, dict) else {}
            if item["knowledge_progress"] is True or turn.get("pressure_event") is True or turn.get("npc_move") is True:
                current = 0
            else:
                current += 1
                quiet_stretch = max(quiet_stretch, current)
    scene_length = len(turns)
    explored = sum(item["action_outcome"] == "explored" for item in classified)
    earned_reveals = sum(item["knowledge_progress"] is True for item in classified)
    return {
        "scene_length": scene_length,
        "turns_to_first_pressure": first_pressure,
        "quiet_stretch": quiet_stretch,
        "exploration_share": round(explored / scene_length, 4) if scene_length else 0.0,
        "earned_reveals": earned_reveals,
    }


def classify_run(run: dict, scene: dict) -> dict:
    """Classify one run without mutating input or raising on malformed data."""
    run_data = run if isinstance(run, dict) else {}
    scene_data = scene if isinstance(scene, dict) else {}
    raw_turns = run_data.get("turns")
    turns = raw_turns if isinstance(raw_turns, list) else []
    reveal_ids = set(_scene_strings(scene_data, "reveal_ids"))
    delivered_before = set(_scene_strings(scene_data, "delivered_before"))
    pacing_window = scene_data.get("pacing_window")
    if not isinstance(pacing_window, int) or isinstance(pacing_window, bool) or pacing_window < 1:
        pacing_window = None

    classified: list[dict[str, Any]] = []
    offered: list[list[str]] = []
    all_grounding: set[str] = set()
    seen_numbers: set[int] = set()
    committed_facts: list[list[str]] = []

    for index, raw_turn in enumerate(turns, start=1):
        turn = raw_turn if isinstance(raw_turn, dict) else {}
        number = _turn_number(turn.get("turn"), index)
        duplicate_or_missing = (
            not isinstance(raw_turn, dict)
            or not isinstance(raw_turn.get("turn"), int)
            or isinstance(raw_turn.get("turn"), bool)
            or number in seen_numbers
        )
        seen_numbers.add(number)
        grounding_ids = _strings(turn.get("grounding_ids"))
        null_grounding_ids = _strings(turn.get("null_grounding_ids"))
        facts = _strings(turn.get("committed_facts"))
        candidates = _strings(turn.get("candidates_offered"))
        lists_valid = (
            grounding_ids is not None
            and null_grounding_ids is not None
            and facts is not None
            and candidates is not None
        )
        action = _classify_action(turn, lists_valid and not duplicate_or_missing)
        if duplicate_or_missing:
            action = "unknown_telemetry"
        knowledge_progress: bool | None = None
        if action not in _NEUTRAL_OUTCOMES and action != "game_break" and action != "unknown_telemetry":
            assert grounding_ids is not None and null_grounding_ids is not None
            attributed = set(grounding_ids) - set(null_grounding_ids)
            new_ids = attributed - delivered_before - all_grounding
            knowledge_progress = bool(new_ids & reveal_ids)
            if action == "pending":
                action = "explored" if new_ids else "no_effect"
        if grounding_ids is not None:
            all_grounding.update(grounding_ids)
        if facts is not None:
            committed_facts.append(facts)
        classified.append(
            {
                "turn": number,
                "action_outcome": action,
                "knowledge_progress": knowledge_progress,
                "authored_recovery": _authored_recovery(turn),
            }
        )
        offered.append(candidates if candidates is not None else [])

    if raw_turns is not None and not isinstance(raw_turns, list):
        classified.append(
            {"turn": 0, "action_outcome": "unknown_telemetry", "knowledge_progress": None, "authored_recovery": False}
        )
        offered.append([])

    confirmed, unresolved = _stall_marks(classified, offered, pacing_window)
    for item in classified:
        if item["action_outcome"] == "unknown_telemetry":
            unresolved.add(item["turn"])

    completed = any(isinstance(turn, dict) and turn.get("story_complete") is True for turn in turns)
    if completed:
        requirements = set(_scene_strings(scene_data, "ending_requires"))
        entry_facts = set(_scene_strings(run_data, "entry_facts"))
        has_ending = scene_data.get("terminal") is True and requirements <= (entry_facts | _safe_union(committed_facts))
        exit_value = "ending" if has_ending else "unknown"
    else:
        exit_value = "none"
        for raw_turn in reversed(turns):
            if isinstance(raw_turn, dict) and raw_turn.get("transition_cause") != "none":
                exit_value = {"earned": "earned", "play": "earned", "forced": "forced", "timer": "timer"}.get(
                    raw_turn.get("transition_cause"), "unknown"
                )
                break

    provenance_flags = _provenance_flags(turns, scene_data, delivered_before)
    epilogue, epilogue_not_offered = _epilogue(turns, scene_data, exit_value)
    if epilogue_not_offered:
        provenance_flags.append({"turn": None, "kind": "epilogue_not_offered"})
        provenance_flags.sort(
            key=lambda item: (item["turn"] is None, item["turn"] if item["turn"] is not None else 0, item["kind"])
        )
    pacing = _pacing(classified, turns)
    status = "unresolved" if unresolved else "stuck" if confirmed else "flagged" if provenance_flags else "healthy"
    return {
        "turns": classified,
        "confirmed_stuck": sorted(confirmed),
        "unresolved": sorted(unresolved),
        "provenance_flags": provenance_flags,
        "exit": exit_value,
        "status": status,
        "pacing": pacing,
        "epilogue": epilogue,
        "contract_version": "v1",
    }
