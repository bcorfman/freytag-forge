"Enrich saved hosted reports with outcome-contract turn telemetry."

from __future__ import annotations

import argparse
import json
from copy import deepcopy
from pathlib import Path
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


def _derive_entry_state(run: dict[str, Any], package: Any, story_root: Path | None) -> None:
    if isinstance(run.get("entry_state"), dict):
        run["entry_state_source"] = "reported"
        return
    if story_root is None:
        return
    try:
        mode = run.get("entry", {}).get("mode")
        scene = run["scene"]
        if mode == "start":
            run["entry_state"] = {
                "scene_id": scene,
                "turn_index": 0,
                "fired_pacing_event_ids": [],
            }
            run["entry_state_source"] = "derived_start"
        elif mode == "seeded":
            from storygame.runtime.entry_snapshots import load_entry_snapshot, state_from_snapshot

            snapshot = load_entry_snapshot(story_root, scene)
            state = state_from_snapshot(package, snapshot, story_root)
            event_ids = {event.id for event in package.pacing.events if event.id in state.fired_event_ids}
            run["entry_state"] = {
                "scene_id": state.current_scene_id,
                "turn_index": state.turn_index,
                "fired_pacing_event_ids": sorted(event_ids),
            }
            run["entry_state_source"] = "derived_snapshot"
    except Exception:
        return


def _enrich_run(run: dict[str, Any], package: Any, story_root: Path | None) -> None:
    turns = run.get("turns")
    if not isinstance(turns, list):
        return
    _derive_entry_state(run, package, story_root)
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


def _walk(
    value: Any,
    package: Any,
    story_root: Path | None,
    bundles: dict[tuple[Any, str], list[Any]],
    replicate: Any = None,
) -> None:
    if not isinstance(value, dict):
        return
    current_replicate = value.get("replicate", replicate)
    if isinstance(value.get("scene"), str) and not isinstance(value.get("bundles"), list):
        matching = bundles.get((current_replicate, value["scene"]))
        if matching is not None:
            value["bundles"] = deepcopy(matching)
    if isinstance(value.get("turns"), list) and isinstance(value.get("scene"), str):
        _enrich_run(value, package, story_root)
    for child in value.get("scenes", []):
        _walk(child, package, story_root, bundles, current_replicate)


def enrich_report(
    report: dict,
    package: Any,
    *,
    bundles_report: dict | None = None,
    story_root: Path | None = None,
) -> dict:
    result = deepcopy(report)
    bundle_map: dict[tuple[Any, str], list[Any]] = {}
    if isinstance(bundles_report, dict):
        for replicate in bundles_report.get("replicates", []):
            if not isinstance(replicate, dict):
                continue
            number = replicate.get("replicate")
            for scene in replicate.get("scenes", []):
                if (
                    isinstance(scene, dict)
                    and isinstance(scene.get("scene"), str)
                    and isinstance(scene.get("bundles"), list)
                ):
                    bundle_map[(number, scene["scene"])] = scene["bundles"]
    for row in result.get("replicates", []):
        _walk(row, package, story_root, bundle_map)
    return result


def _iter_runs(value: Any):
    if not isinstance(value, dict):
        return
    if isinstance(value.get("turns"), list) and isinstance(value.get("scene"), str):
        yield value
    for child in value.get("scenes", []):
        yield from _iter_runs(child)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("report", type=Path)
    parser.add_argument("--bundles", type=Path, required=True)
    parser.add_argument("--story-root", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args(argv)
    try:
        report = json.loads(args.report.read_text())
        bundles = json.loads(args.bundles.read_text())
        from storygame.story_package.loader import load_story_package

        package = load_story_package(args.story_root)
    except (OSError, ValueError, TypeError, RuntimeError):
        return 2
    enriched = enrich_report(report, package, bundles_report=bundles, story_root=args.story_root)
    try:
        args.out.write_text(json.dumps(enriched, indent=1) + "\n")
    except OSError:
        return 2
    failed = False
    for row in enriched.get("replicates", []):
        for run in _iter_runs(row):
            gaps = run.get("telemetry_gaps", [])
            print(
                f"{run['scene']} {run.get('replicate', row.get('replicate'))}: "
                f"{len(run['turns'])} turns, {len(gaps)} gaps, "
                f"entry {run.get('entry_state_source', 'unknown')}"
            )
            failed |= bool(gaps)
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
