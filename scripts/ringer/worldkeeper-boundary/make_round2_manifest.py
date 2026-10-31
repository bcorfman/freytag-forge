"""Build round 2 of the worldkeeper boundary moves: switch storygame callers to the new World helpers."""

import json
from pathlib import Path

ROOT = "/home/bcorfman/dev/freytag-forge"
D = f"{ROOT}/scripts/ringer/worldkeeper-boundary"
WORK = "/home/bcorfman/dev/ringer-work/worldkeeper-boundary-round2"

COMMON = (
    "You are a code worker. Your current working directory IS a git worktree of the freytag-forge repository "
    "(branch worldkeeper-boundary-moves, detached at its HEAD); edit files here directly, never in "
    f"{ROOT}. Do NOT git commit, push, switch branches, stash or revert. Edit ONLY the files listed under OWNED "
    "FILES. Never edit packages/worldkeeper (round 1 already added and tested the helpers), tests/, docs/ or data/.\n\n"
    "WHY: a firm project rule says world-model logic (anything that reads or changes only world state) lives in "
    "packages/worldkeeper as World or WorldSchema methods; storygame only adapts and calls it. Round 1 added the "
    "helpers in packages/worldkeeper/src/worldkeeper/model.py with tests in "
    "packages/worldkeeper/tests/test_boundary_helpers.py. Read both, plus "
    "scripts/ringer/worldkeeper-boundary/round1-notes.md (which says exactly what each helper replaces and any "
    "argument-order or return-type difference) and the audit entries for your files in "
    "scripts/ringer/worldkeeper-boundary/audit-reports/*.json (their 'risks' fields).\n\n"
    "WHAT TO DO: replace the storygame tree walks named below with calls to the World/WorldSchema helpers and "
    "delete the storygame helpers that become unused. This is a pure refactor: behaviour, ordering, return types "
    "seen by callers, log lines and player-visible text must not change. Keep the story-, prose- and model-facing "
    "parts exactly where they are. Where a helper returns ids but the old code returned names or a set, convert at "
    "the call site. Do not add new tests and do not change existing ones; if an existing test fails, your change "
    "altered behaviour: fix the change, not the test.\n\n"
)

HOW = (
    "\n\nHOW TO RUN (never use `uv`; your sandbox cannot run it): Python is "
    f"`{ROOT}/.venv/bin/python` with `PYTHONPATH=$PWD TMPDIR=/tmp` from your worktree root. Ruff: "
    f"`{ROOT}/.venv/bin/python -m ruff format <your files> && {ROOT}/.venv/bin/python -m ruff check <your files>`.\n"
    "DONE WHEN, from your worktree root, "
    "`{ROOT}/.venv/bin/python {D}/check_round2.py {group} {WORK}/{group}.patch` prints PASS. It checks the old walks "
    "are gone and the helpers are called, that you changed only your owned files, ruff, and runs every test file "
    "that imports the eight affected modules plus the worldkeeper tests (about 1,300 tests, about 30 s with -n 8)."
)

GROUPS = {
    "item-facts": (
        ["storygame/runtime/item_facts.py"],
        "In storygame/runtime/item_facts.py:\n"
        "- `_observation_scope_is_empty`: replace the manual parent climb (around lines 693-697) with "
        "`world.contains(ancestor_id, entity_id)` (note its argument order).\n"
        "- `_observation_underside_is_exhausted`: replace the direct under-contents query (around lines 717-723) with "
        "`world.under_contents(focus_id)`; the authored-candidate part from the story package stays.\n"
        "- `_apply_move`: replace the visible-seat enumeration (around lines 1290-1300, the comprehension testing "
        "`seat_for == place_parent` and is_visible, then sorted, first) with `sorted(world.seats(place_parent))` and "
        "take the first; round 1 confirmed this is identical.\n"
        "- `_fact_move_overrides` stays as it is (a client comprehension over existing World calls).",
    ),
    "capture-observation": (
        ["storygame/runtime/capture.py", "storygame/runtime/observation.py"],
        "In storygame/runtime/capture.py:\n"
        "- delete `_descendants`; callers use `world.descendants(root_id)` (wrap in set() where the old set was "
        "relied on).\n"
        "- delete `_focus_open_state`; callers use `world.open_state(focus_id)`.\n"
        "- `_should_engine_open`: keep the function (the command-kind and `opens is True` tests are storygame "
        'concerns) but express its world part with `world.open_state(focus_id) == "closed"` and `world.sees(...)` '
        "exactly as round1-notes.md describes; behaviour must not change.\n"
        "- `_moved_unrelated`: keep building the exclusions here; replace the parent-comparison loop with "
        "`world.moved_since(before_parents, excluded_ids)` and map ids to names as round1-notes.md says, so the "
        "function returns the same values in the same order.\n"
        "In storygame/runtime/observation.py:\n"
        "- delete `_is_item`, `_candidate_ids`, `_required_ids` and `_descendants`; callers use `world.is_item`, "
        "`world.observable_items`, `world.required_observations` and `world.descendants`.",
    ),
    "seating-misc": (
        [
            "storygame/runtime/traversal.py",
            "storygame/runtime/narration_safety.py",
            "storygame/runtime/seating.py",
            "storygame/runtime/taking.py",
            "storygame/runtime/fixed_refusal.py",
        ],
        "- storygame/runtime/traversal.py: delete `_contains(entity_id, ancestor_id)`; callers use "
        "`world.contains(ancestor_id, entity_id)` (argument order swapped).\n"
        "- storygame/runtime/narration_safety.py: delete `NarrationSafetyValidator._related_area_ids` and "
        "`_location_ancestor_ids` (NOT the unrelated text helper `_contains`). Callers use "
        "`schema.related_areas(area_id)` and `schema.area_ancestors(area_id)` on a WorldSchema built once per call "
        "with `WorldSchema.from_data(world_schema_data(package))` (`world_schema_data` is in "
        "storygame/runtime/world_model.py; round 1 confirmed it holds every package location with the same parent). "
        "Keep set semantics where callers expect a mutable set. If the validator runs per segment, build the schema "
        "once per validate call, not per lookup.\n"
        "- storygame/runtime/seating.py: `seat_before_use` uses `world.current_seat(...)` for the seat and its "
        "visible-seat setup; `stand_before_leave` uses `world.reachable_from_seat(seat_id, holder_id)` for its "
        "reachability set; `board_vehicle` uses `world.visible_vehicle_seats(vehicle_ids)` for its visible "
        "vehicle/seat options. Questions, callbacks, package text and returned commands stay.\n"
        "- storygame/runtime/taking.py: `take_before_put` uses `world.takeable_items(item_ids, protagonist_id, "
        "fixed_ids)` with the package's item.fixed bits turned into a plain set of ids.\n"
        "- storygame/runtime/fixed_refusal.py: `refuse_fixed_move` uses `world.fixed_visible_items(item_ids, "
        "protagonist_id, fixed_ids, scope_ids)` with the in-scope override as a plain id set.\n"
        "Read round1-notes.md for each helper's exact contract before switching.",
    ),
}

tasks = []
for group, (files, body) in GROUPS.items():
    patch = f"{WORK}/{group}.patch"
    tasks.append(
        {
            "task_type": "code-feature",
            "engine": "codex",
            "model": "gpt-5.6-luna",
            "engine_args": ["-c", "model_reasoning_effort=high"],
            "full_access": True,
            "max_attempts": 2,
            "timeout_s": 3600,
            "check_timeout_s": 900,
            "key": group,
            "ownership": files,
            "expect_files": [patch],
            "verified": "executed check: old tree walks removed, World helpers called, only owned files changed, "
            "ruff clean, ~1,300 focused tests pass; patch exported",
            "spec": COMMON
            + "OWNED FILES: "
            + ", ".join(files)
            + "\n\n"
            + body
            + HOW.replace("{ROOT}", ROOT).replace("{D}", D).replace("{group}", group).replace("{WORK}", WORK),
            "check": f"{ROOT}/.venv/bin/python {D}/check_round2.py {group} {patch}",
        }
    )

manifest = {
    "run_name": "worldkeeper-boundary",
    "workdir": WORK,
    "max_parallel": 3,
    "worktrees": True,
    "repo": ROOT,
    "tasks": tasks,
}
out = Path(D) / "round2-manifest.json"
out.write_text(json.dumps(manifest, indent=2) + "\n")
print(out)
