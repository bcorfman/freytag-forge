"Enrich saved hosted reports with outcome-contract turn telemetry."

from __future__ import annotations

from copy import deepcopy
from typing import Any

from factory.contract_scene import build_contract_scene
from factory.turn_telemetry import build_turn_telemetry, pacing_effects_by_event


def _ids(value: Any) -> list[str] | None:
    if not isinstance(value, list) or not all(isinstance(item, str) for item in value):
        return None
    return list(value)


def _neutral(turn: dict[str, Any]) -> dict[str, Any]:
    return {
        "turn": turn.get("turn"),
        "input": turn.get("input", turn.get("raw_input", "")),
        "text": str(turn.get("text", "")),
        "outcome": "rejected",
        "rejected": True,
        "game_break": None,
        "story_complete": False,
        "grounding_ids": [],
        "null_grounding_ids": [],
        "committed_facts": [],
        "candidates_offered": [],
        "matched_candidate": None,
        "transition_cause": "none",
        "pressure_event": False,
        "npc_move": False,
        "ending_latched": False,
        "grounding_source": {},
    }


def _enrich_run(run: dict[str, Any], package: Any) -> None:
    turns = run.get("turns")
    if not isinstance(turns, list):
        return
    scene = build_contract_scene(package, run["scene"])
    effects = pacing_effects_by_event(package)
    bundles = {
        item.get("turn"): item.get("attempt_bundle") for item in run.get("bundles", []) if isinstance(item, dict)
    }
    entry = run.get("entry_state") if isinstance(run.get("entry_state"), dict) else {}
    previous = _ids(entry.get("fired_pacing_event_ids"))
    gaps: list[str] = []
    for index, turn in enumerate(turns, start=1):
        if not isinstance(turn, dict):
            continue
        number = turn.get("turn", index)
        bundle = bundles.get(number)
        replay = turn.get("pacing_replay")
        replay_ids = _ids(replay.get("fired_event_ids")) if isinstance(replay, dict) else None
        null_ids = _ids(replay.get("null_grounding_ids")) if isinstance(replay, dict) else None
        after = _ids(turn.get("fired_pacing_event_ids"))
        rejected = turn.get("rejected") is True or turn.get("outcome") == "rejected"
        if rejected and bundle is None:
            turn.update(_neutral(turn))
            continue
        missing = None
        if not isinstance(bundle, dict):
            missing = "bundle"
        elif replay_ids is None or null_ids is None:
            missing = "pacing_replay"
        elif after is None:
            missing = "fired_pacing_event_ids"
        elif previous is None:
            missing = "entry_state"
        if missing is not None:
            gaps.append(f"turn {number}: missing {missing}")
            continue
        telemetry = build_turn_telemetry(
            turn=number,
            player_input=str(turn.get("input", turn.get("raw_input", ""))),
            text=str(turn.get("text", "")),
            bundle=bundle,
            grounding_ids=_ids(turn.get("grounding_ids")) or [],
            replay_fired_ids=replay_ids,
            null_grounding_ids=null_ids,
            fired_before=previous,
            fired_after=after,
            pacing_effects=effects,
            delivered_before=scene["delivered_before"],
        )
        turn.update(telemetry)
        previous = after
    if gaps:
        run["telemetry_gaps"] = gaps


def _walk(value: Any, package: Any) -> None:
    if not isinstance(value, dict):
        return
    if isinstance(value.get("turns"), list) and isinstance(value.get("scene"), str):
        _enrich_run(value, package)
    for child in value.get("scenes", []):
        _walk(child, package)


def enrich_report(report: dict, package: Any) -> dict:
    result = deepcopy(report)
    for row in result.get("replicates", []):
        _walk(row, package)
    return result
