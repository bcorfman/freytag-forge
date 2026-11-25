"""Build the Step 6 structural coverage ledger."""

from __future__ import annotations

import argparse
import multiprocessing
import sys
from collections.abc import Iterable
from pathlib import Path
from typing import Any

ROOT = Path("data/stories/continuity-initiative")
REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))
SCENES = ("1A", "1B", "1C", "2A", "2B", "2C", "3A", "3B", "3C")
KNOWN_UNREACHABLE: dict[str, str] = {}
APPROVED_IDS: set[str] = set()


def _facts(items: Iterable[Any]) -> list[str]:
    return sorted({item.fact_id for item in items})


def _scene_reads(package: Any, scene: str) -> list[str]:
    reads = [
        predicate
        for storylet in package.storylet_routes.storylets
        if storylet.scene_id == scene
        for predicate in _facts(storylet.activation_conditions)
    ]
    reads.extend(
        predicate.fact_id
        for transition in package.pacing.transitions
        if transition.source_scene_id == scene
        for predicate in transition.triggers
    )
    return sorted(set(reads))


def static_ledger(package: Any, known_unreachable: dict[str, str], approved_ids: Iterable[str]) -> dict:
    """Return deterministic, package-only coverage; never runs a journey."""
    approved = set(approved_ids)
    entries: dict[str, list[dict[str, Any]]] = {scene: [] for scene in SCENES}
    for item in sorted(package.knowledge.knowledge, key=lambda value: value.id):
        if item.source.kind != "storylet_realization":
            continue
        scene = item.available_in_scenes[0]
        player = item.audience.kind == "public" and item.audience.player_visible
        if not player:
            status = "observer_only"
        elif item.id in known_unreachable and item.id in approved:
            status = "retired_or_unreachable"
        elif item.id in approved:
            status = "UNACCOUNTED"
        elif player:
            status = "reachable_by_nightly_journey"
        else:
            status = "UNACCOUNTED"
        row = {"id": item.id, "status": status}
        if status == "retired_or_unreachable":
            row["decision"] = known_unreachable[item.id]
        entries.setdefault(scene, []).append(row)
    scenes: dict[str, dict[str, Any]] = {}
    for scene in SCENES:
        exits = [t for t in package.pacing.transitions if t.source_scene_id == scene]
        scenes[scene] = {
            "storylets": entries[scene],
            "earned_exits": [{"id": t.id, "target": t.target_scene_id} for t in exits],
            "pressure_responses": [
                {"id": event.id, "status": "not exercised"}
                for event in package.pacing.events
                if event.scene_id == scene
            ],
            "entry_state_classes": [{"facts": _scene_reads(package, scene), "journeys": 0}],
            "action_classes": ["not recorded"],
        }
    unaccounted = sorted(row["id"] for values in entries.values() for row in values if row["status"] == "UNACCOUNTED")
    counts = {scene: len(values) for scene, values in entries.items()}
    return {
        "header": {
            "mode": "nightly journey contract (journeys not run)",
            "realization_counts": counts,
        },
        "scenes": scenes,
        "unaccounted": unaccounted,
        "ending": {"scene": package.pacing.ending.scene_id, "status": "reached by default journey"},
    }


def _run(preferred: tuple[str, ...]) -> tuple[str, Any]:
    from tests.test_game_path_journeys import play

    return preferred[-1] if preferred else "default", play(preferred)


def journey_evidence(preferred_runs: Iterable[Any]) -> dict:
    """Summarize Journey objects (or ``(journey_id, Journey)`` pairs)."""
    result: dict[str, Any] = {"realizations": {}, "scenes": {scene: {} for scene in SCENES}}
    for item in preferred_runs:
        journey_id, journey = item if isinstance(item, tuple) and len(item) == 2 else ("default", item)
        turns = {
            reveal: int(record.id.rsplit("_", 1)[-1])
            for record in journey.state.turn_records
            for reveal in record.reveal_ids
        }
        for realization in journey.picked:
            result["realizations"].setdefault(realization, []).append(
                {"journey": journey_id, "turn": turns.get(realization)}
            )
        fired = {event for record in journey.state.turn_records for event in record.deadline_event_ids}
        final_facts = {
            fact.predicate for fact in journey.state.facts.asserted if getattr(fact, "value", None) == "true"
        }
        for scene in set(journey.scenes):
            data = result["scenes"].setdefault(scene, {})
            data.setdefault("deadline_events", set()).update(fired)
            data.setdefault("fact_classes", []).append(final_facts)
            data.setdefault("left_targets", set()).update(
                journey.scenes[index + 1] for index, current in enumerate(journey.scenes[:-1]) if current == scene
            )
            data.setdefault("transitions", set()).update(
                record.transition_id for record in journey.state.turn_records if record.transition_id
            )
    return result


def _markdown(ledger: dict) -> str:
    counts = ", ".join(f"{scene}: {count}" for scene, count in ledger["header"]["realization_counts"].items())
    out = [
        "# Nine-scene coverage ledger",
        "",
        f"Mode: {ledger['header']['mode']}.",
        f"Realization counts: {counts}.",
        "",
    ]
    for scene, data in ledger["scenes"].items():
        out += [f"## {scene}", "", "### STORYLETS", ""]
        for row in data["storylets"]:
            suffix = f" — {row['decision']}" if "decision" in row else ""
            out.append(f"- `{row['id']}`: **{row['status']}**{suffix}")
        out += ["", "### EARNED EXITS", ""]
        out += [
            f"- `{row['id']}` -> {row['target']}: {row.get('status', 'not exercised')}" for row in data["earned_exits"]
        ] or ["- none"]
        out += ["", "### PRESSURE RESPONSES", ""]
        out += [f"- `{row['id']}`: {row['status']}" for row in data["pressure_responses"]] or ["- none"]
        out += ["", "### ENTRY-STATE CLASSES", ""]
        for entry_class in data["entry_state_classes"]:
            reads = ", ".join(entry_class["facts"]) or "none"
            out.append(f"- facts: {reads}; journeys: {entry_class['journeys']}")
        out += ["", "### ACTION CLASSES", "", "- not recorded", ""]
    out += [
        "## UNEXAMINED",
        "",
        "Pairwise deviations are not covered.",
        "Custody/location changes are not covered.",
        "Free-text discovery by a blind player is not covered.",
        "State merging is not covered.",
        "",
        "Terminal ending: scene 3C reached by the default journey.",
    ]
    if ledger["unaccounted"]:
        out += ["", "UNACCOUNTED: " + ", ".join(ledger["unaccounted"])]
    return "\n".join(out) + "\n"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--journeys", action="store_true")
    parser.add_argument("--write", type=Path)
    args = parser.parse_args(argv)
    import json

    from tests.test_game_path_journeys import CHAINS, KNOWN_UNREACHABLE, PACKAGE, PLAYER_REALIZATIONS

    approved = json.loads(Path("tests/fixtures/known_unreachable_approved.json").read_text())["ids"]
    ledger = static_ledger(PACKAGE, KNOWN_UNREACHABLE, approved)
    if args.journeys:
        ids = [item.values[0] if hasattr(item, "values") else item for item in PLAYER_REALIZATIONS]
        preferences = [CHAINS.get(item_id, (item_id,)) for item_id in ids]
        with multiprocessing.Pool(min(4, max(1, len(preferences)))) as pool:
            runs = pool.map(_run, preferences)
        evidence = journey_evidence(runs)
        for scene in SCENES:
            ledger["scenes"][scene]["action_classes"] = ["not recorded"]
            evidence_scene = evidence["scenes"].get(scene, {})
            reads = set(ledger["scenes"][scene]["entry_state_classes"][0]["facts"])
            classes: dict[tuple[str, ...], int] = {}
            for facts in evidence_scene.get("fact_classes", []):
                key = tuple(sorted(reads & facts))
                classes[key] = classes.get(key, 0) + 1
            if classes:
                ledger["scenes"][scene]["entry_state_classes"] = [
                    {"facts": list(key), "journeys": count} for key, count in sorted(classes.items())
                ]
            for exit_row in ledger["scenes"][scene]["earned_exits"]:
                exit_row["status"] = (
                    "earned" if exit_row["target"] in evidence_scene.get("left_targets", set()) else "not exercised"
                )
            for pressure_row in ledger["scenes"][scene]["pressure_responses"]:
                pressure_row["status"] = (
                    "fired" if pressure_row["id"] in evidence_scene.get("deadline_events", set()) else "not exercised"
                )
        for row in (row for values in ledger["scenes"].values() for row in values["storylets"]):
            if row["id"] in evidence["realizations"]:
                row["status"] = "reachable"
                row["journeys"] = evidence["realizations"][row["id"]]
        ledger["header"]["mode"] = "journey evidence (one journey per player-visible realization)"
    if ledger["unaccounted"]:
        if args.write:
            args.write.write_text(_markdown(ledger), encoding="utf-8")
        return 1
    if args.write:
        args.write.write_text(_markdown(ledger), encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
