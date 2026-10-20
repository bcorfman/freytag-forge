from __future__ import annotations

import json
import shutil
import sys
import tempfile
from pathlib import Path

import yaml

from storygame.runtime.engine import RuntimeEngine
from storygame.runtime.facts import Fact, FactStore
from storygame.runtime.state import RuntimeState
from storygame.runtime.world_model import apply_scene_placements, world_for
from storygame.story_package.loader import load_story_package

ROOT = Path(__file__).resolve().parents[3]
SOURCE = ROOT / "data/stories/continuity-initiative"
REPORT = ROOT / "bench/results/stage7-3c-surface-binding/report.json"
ENTRY_FACTS = ("broadcast_started", "brandon_confession_available", "detention_locations_secured")
COMMANDS = {
    "k_sl_3c_c_r1": "Restore the drainage pumps.",
    "k_sl_3c_c_r2": "Open the surface gates.",
}
ORDERS = (
    ("k_sl_3c_c_r1", "k_sl_3c_c_r2"),
    ("k_sl_3c_c_r2", "k_sl_3c_c_r1"),
)


def state_3c(package, *, turn_index=0):
    state = RuntimeState(package=package, current_scene_id="3C", phase="resolution")
    state._assert_scene_entry_fact("3C")
    for fact_id in ENTRY_FACTS:
        state.facts.assert_fact(Fact(predicate=fact_id, subject="story", value="true"))
    state.turn_index = turn_index
    world_for(package, state.facts).seed()
    apply_scene_placements(package, state.facts, "3C")
    return state


def reveal(engine, package, knowledge_id, command):
    knowledge = package.knowledge_indexes.by_id[knowledge_id]
    text = knowledge.delivery_text or knowledge.statement
    engine.provider = lambda _command: {
        "segments": [{"kind": "narration", "text": text, "grounding_ids": [knowledge_id]}],
        "selected_knowledge_ids": [knowledge_id],
    }
    engine.turn(command)
    engine._activate_pacing()


def locations(package, story_path):
    world = world_for(package, FactStore())
    members = tuple(world.members("captives"))
    # ``captives`` is authored as an aggregate group in this story, without
    # separately modeled child entities. Keep the aggregate observable in the
    # member-parent record instead of allowing an empty record to make the
    # custody assertion vacuous.
    if not members:
        members = ("captives",)
    world_yaml = story_path / "world.yaml"
    document = yaml.safe_load(world_yaml.read_text())
    ids = tuple(item["id"] for item in document["npcs"] if item.get("id") in {"kristin", "brandon", "michelle"})
    if set(ids) != {"kristin", "brandon", "michelle"}:
        raise RuntimeError("world.yaml did not contain all expected person entities")
    return members, ids


def snapshot(engine, package, story_path):
    world = world_for(package, engine.state.facts)
    members, people = locations(package, story_path)
    return {
        "fact_asserted": any(
            f.predicate == "captives_reaching_surface" and str(f.value).lower() == "true"
            for f in engine.state.facts.asserted
        ),
        "captives_parent": world.parent("captives"),
        "captive_member_parents": {member: world.parent(member) for member in members},
        "person_parents": {person: world.parent(person) for person in people},
    }


def run_arm(package, story_path, arm, order):
    engine = RuntimeEngine(state_3c(package), None)
    rows = []
    value = snapshot(engine, package, story_path)
    value.update({"arm": arm, "order": [*order], "step": 0, "knowledge_id": None, "command": None})
    rows.append(value)
    reveal(engine, package, "k_sl_3c_a_r1", "Send the evidence package.")
    reveal(engine, package, "k_sl_3c_b_r1", "Take the Portable data case from Rebecca.")
    for index, knowledge_id in enumerate(order, 1):
        reveal(engine, package, knowledge_id, COMMANDS[knowledge_id])
        value = snapshot(engine, package, story_path)
        value.update(
            {
                "arm": arm,
                "order": [*order],
                "step": index,
                "knowledge_id": knowledge_id,
                "command": COMMANDS[knowledge_id],
            }
        )
        rows.append(value)
    return rows


def run_deadline(package, story_path, arm):
    handoff = next(window for window in package.pacing.scenes if window.scene_id == "3C").handoff_after_turns
    engine = RuntimeEngine(state_3c(package, turn_index=handoff - 1), None)
    engine.provider = lambda _command: {
        "segments": [{"kind": "narration", "text": "The broadcast continues."}],
        "selected_knowledge_ids": [],
    }
    result = engine.turn("Get everyone to the surface.")
    value = snapshot(engine, package, story_path)
    value.update(
        {
            "arm": arm,
            "order": None,
            "step": None,
            "deadline_turn": handoff,
            "command": "Get everyone to the surface.",
            "narration": " ".join(segment.text for segment in result.segments),
        }
    )
    return value


def run_save_load(package, story_path, arm, order):
    engine = RuntimeEngine(state_3c(package), None)
    reveal(engine, package, "k_sl_3c_a_r1", "Send the evidence package.")
    reveal(engine, package, "k_sl_3c_b_r1", "Take the Portable data case from Rebecca.")
    for knowledge_id in order:
        reveal(engine, package, knowledge_id, COMMANDS[knowledge_id])
    saved = snapshot(engine, package, story_path)
    reloaded_state = state_3c(package)
    reloaded_state.restore_snapshot(engine.state.snapshot())
    reloaded = snapshot(RuntimeEngine(reloaded_state, None), package, story_path)
    return {
        "arm": arm,
        "order": [*order],
        "pre_save": saved,
        "after_reload": reloaded,
    }


def main() -> int:
    control_package = load_story_package(SOURCE)
    with tempfile.TemporaryDirectory(prefix="stage7-3c-") as temp:
        copied = Path(temp) / SOURCE.name
        shutil.copytree(SOURCE, copied)
        world_path = copied / "world.yaml"
        text = world_path.read_text()
        old = "- captives_reaching_surface\n"
        if text.count(old) != 1:
            raise SystemExit("replacement text did not match exactly once")
        world_path.write_text(
            text.replace(
                old, "- id: captives_reaching_surface\n  on_assert: [{move: captives, parent: facility_escape}]\n"
            )
        )
        binding_package = load_story_package(copied)

        steps = []
        deadline = []
        save_load = []
        for arm, package in (("control", control_package), ("binding", binding_package)):
            for order in ORDERS:
                story_path = SOURCE if arm == "control" else copied
                steps.extend(run_arm(package, story_path, arm, order))
                save_load.append(run_save_load(package, story_path, arm, order))
            deadline.append(run_deadline(package, story_path, arm))

    differences = []
    for order in ORDERS:
        control = [x for x in steps if x["arm"] == "control" and x["order"] == list(order)]
        binding = [x for x in steps if x["arm"] == "binding" and x["order"] == list(order)]
        for c, b in zip(control, binding, strict=False):
            for key in ("fact_asserted", "captives_parent", "captive_member_parents", "person_parents"):
                if c[key] != b[key]:
                    differences.append(
                        {"order": list(order), "step": c["step"], "field": key, "control": c[key], "binding": b[key]}
                    )

    failures = []
    for row in steps:
        if row["captives_parent"] is None or any(parent is None for parent in row["captive_member_parents"].values()):
            failures.append("captives or captive member parent was None")
        if any(parent is None for parent in row["person_parents"].values()):
            failures.append("non-captive person parent was None")
        if row["arm"] == "control" and row["captives_parent"] != "maintenance_network":
            failures.append("control captives were not in maintenance_network")
        if row["arm"] == "binding":
            if row["step"] in (0, 1) and (row["fact_asserted"] or row["captives_parent"] == "facility_escape"):
                failures.append("binding moved captives after one C part")
            if row["step"] == 2 and (not row["fact_asserted"] or row["captives_parent"] != "facility_escape"):
                failures.append("binding did not move captives after both C parts")
        if row["arm"] == "binding" and row["person_parents"] != next(
            x["person_parents"]
            for x in steps
            if x["arm"] == "control" and x["order"] == row["order"] and x["step"] == row["step"]
        ):
            failures.append("binding changed a non-captive person parent")

    control_deadline = next(row for row in deadline if row["arm"] == "control")
    binding_deadline = next(row for row in deadline if row["arm"] == "binding")
    if not binding_deadline["fact_asserted"] or binding_deadline["captives_parent"] != "facility_escape":
        failures.append("binding did not move captives after the resolution deadline")
    if binding_deadline["person_parents"] != control_deadline["person_parents"]:
        failures.append("binding changed a non-captive person parent at the resolution deadline")
    for case in save_load:
        if case["pre_save"] != case["after_reload"]:
            failures.append("save/load changed a parent")
        if case["arm"] == "binding":
            control_case = next(
                item for item in save_load if item["arm"] == "control" and item["order"] == case["order"]
            )
            if case["pre_save"]["person_parents"] != control_case["pre_save"]["person_parents"]:
                failures.append("binding changed a non-captive person parent after save/load")

    report = {
        "arms": ["control", "binding"],
        "orders": [list(x) for x in ORDERS],
        "steps": steps,
        "deadline": deadline,
        "save_load": save_load,
        "differences": differences,
        "failures": failures,
    }
    REPORT.parent.mkdir(parents=True, exist_ok=True)
    REPORT.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n")
    if failures:
        print(json.dumps({"failures": failures}, indent=2), file=sys.stderr)
        return 1
    print(REPORT)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
