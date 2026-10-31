"""Build round 1 of the worldkeeper boundary moves: add World/WorldSchema helpers with tests, no callers changed."""

import json
from pathlib import Path

ROOT = "/home/bcorfman/dev/freytag-forge"
D = f"{ROOT}/scripts/ringer/worldkeeper-boundary"

METHODS = """\
Add these methods. Each must reproduce EXACTLY the behaviour of the storygame code it replaces (read that code first;
ordering, None handling and cycle safety included). Signatures are fixed by the check.

World (packages/worldkeeper/src/worldkeeper/model.py):
1. descendants(self, entity_id) -> tuple[str, ...]: every direct or indirect child once, breadth-first, direct
   contents visited in World.contents order, cycle-safe. Replaces storygame/runtime/capture.py `_descendants`
   (lines ~371-380, returns a set) and storygame/runtime/observation.py `_descendants` (lines ~183-190). If the two
   differ in order or membership, match observation.py and say so in the notes.
2. contains(self, ancestor_id, entity_id) -> bool: True when entity_id == ancestor_id or ancestor_id is in
   self.chain(entity_id). Replaces storygame/runtime/traversal.py `_contains` (lines ~18-24; note its argument order
   and give World.contains the order above) and the parent climb in storygame/runtime/item_facts.py
   `_observation_scope_is_empty` (lines ~693-697).
3. under_contents(self, entity_id) -> tuple[str, ...]: direct children whose relation is "under", in World.contents
   order. From item_facts.py `_observation_underside_is_exhausted` lines ~717-723 (only the world query).
4. open_state(self, entity_id) -> str | None: "open" or "closed" for an openable thing whose open axis holds one of
   those poles, else None (None for None/unknown ids). From capture.py `_focus_open_state` (lines ~69-73). Also read
   capture.py `_should_engine_open` (lines ~58-66): its world part (openable, currently closed, observer sees it) must
   be expressible with open_state + sees; do not add the command-kind test to World.
5. is_item(self, entity_id) -> bool: from observation.py `_is_item` (lines ~64-67), same is_a ancestry semantics.
6. observable_items(self, observer_id, focus_id) -> tuple[str, ...]: from observation.py `_candidate_ids`
   (lines ~162-180), identical results and order.
7. required_observations(self, observer_id, focus_id, visible_ids, kind="look") -> set[str]: from observation.py
   `_required_ids` (lines ~138-159), identical results.
8. moved_since(self, before_parents, excluded_ids=()) -> tuple[str, ...]: the pure part of capture.py
   `_moved_unrelated` (lines ~394-400): ids of things (same kind filter) not excluded whose parent now differs from
   before_parents[id], with the same None guards; return the SAME values in the same order the current code returns
   (read whether it returns ids or names; if it returns names, return ids sorted the same way and say in the notes
   how the caller maps ids to names).

WorldSchema (same file):
9. related_areas(self, area_id) -> frozenset[str]: from storygame/runtime/narration_safety.py
   `NarrationSafetyValidator._related_area_ids` (lines ~345-364), which walks the package's declared locations: the
   area, all area ancestors, all area descendants. Use the schema's declared area entities and parents.
10. area_ancestors(self, area_id) -> frozenset[str]: from narration_safety.py `_location_ancestor_ids`
    (lines ~367-376), excluding the area itself.
    Verify that WorldSchema.from_data(storygame.runtime.world_model.world_schema_data(package)) holds every
    package.world.locations entry with the same parent, so round 2 can call these from narration_safety; state the
    result in the notes.

OPTIONAL World methods (add each one if its world-only part can be extracted with identical behaviour; otherwise do
not add it and explain why in the notes under a line containing the backticked name):
11. current_seat(self, entity_id) -> str | None and the visible-seat part of storygame/runtime/seating.py
    `seat_before_use` lines ~46-63 (if that needs a second helper, fold it into visible_vehicle_seats or explain).
12. reachable_from_seat(self, seat_id, holder_id) -> tuple[str, ...]: seating.py `stand_before_leave` lines ~244-252.
13. takeable_items(self, item_ids, protagonist_id, fixed_ids=()) -> tuple[str, ...]: storygame/runtime/taking.py
    `take_before_put` lines ~29-45 (the package's item.fixed bits become the plain fixed_ids set).
14. fixed_visible_items(self, item_ids, protagonist_id, fixed_ids=(), scope_ids=None) -> tuple[str, ...]:
    storygame/runtime/fixed_refusal.py `refuse_fixed_move` lines ~46-64.
15. visible_vehicle_seats(self, vehicle_ids) -> tuple[tuple[str, tuple[str, ...]], ...]: seating.py `board_vehicle`
    lines ~135-146, consistent with World.seats.

NOT methods (round 2 will use existing World calls): the visible-seat pick in item_facts.py `_apply_move`
(lines ~1290-1300) equals sorted(world.seats(vehicle))[0]; confirm that in the notes. The companion filter in
item_facts.py `_fact_move_overrides` (lines ~1387-1391) stays a client comprehension over world.companions and
world.parent.
"""


def spec() -> str:
    return (
        f"You are a code worker in the freytag-forge repository at {ROOT}, branch worldkeeper-boundary-moves, already "
        "checked out. Do NOT git commit, push, switch branches, stash or revert. Edit ONLY "
        "packages/worldkeeper/src/worldkeeper/model.py (add methods; never change an existing method's behaviour), "
        "create packages/worldkeeper/tests/test_boundary_helpers.py, and write "
        "scripts/ringer/worldkeeper-boundary/round1-notes.md. Never edit storygame/, tests/, docs/ or data/: round 2 "
        "switches the storygame callers later.\n\n"
        "WHY: a new firm project rule says world-model logic (anything that reads or changes only world state: "
        "parents, containment, kinds, reach, visibility, seats, companions, axes) lives in packages/worldkeeper as "
        "World or WorldSchema methods with tests there; storygame only adapts and calls it. A read-only audit found "
        "storygame code that walks the world tree itself; its reports are in "
        f"{D}/audit-reports/*.json (read the entries for the functions named below, especially their risks).\n"
        "worldkeeper must stay story-agnostic: never import storygame or use any story's ids or vocabulary in "
        "model.py. Tests may build small schemas inline with WorldSchema.from_data and MemoryBackend (see the "
        "package README and existing tests in packages/worldkeeper/tests/ for the style).\n\n"
        + METHODS
        + "\nTESTS FIRST: write the tests in test_boundary_helpers.py before each method, covering ordering, None or "
        "unknown ids, cycles where a walk is involved, hidden/unplaced things, under versus on/in relations, nested "
        "areas, and seats/companions where relevant. Every added method must be called in that file. For each method, "
        "also check by hand (a throwaway snippet, not committed) that it returns the same result as the storygame "
        "function it replaces on the real package: bootstrap "
        "`RuntimeState.bootstrap(load_story_package(Path('data/stories/continuity-initiative')))` and compare on a few "
        "real entity ids; report what you compared in the notes.\n\n"
        "NOTES FILE round1-notes.md: one short section per method: what it replaces, any behaviour difference found "
        "and how you resolved it, the parity comparison, and the confirmations asked for above; plus every optional "
        "method you skipped, with the backticked name and the reason.\n\n"
        "HOW TO RUN (never use `uv`; your sandbox cannot run it): Python is "
        f"`{ROOT}/.venv/bin/python` with `PYTHONPATH=$PWD TMPDIR=/tmp`; tests: "
        "`.venv/bin/python -m pytest -q packages/worldkeeper/tests tests/test_world_model.py`; Ruff: "
        "`.venv/bin/python -m ruff check packages/worldkeeper && "
        ".venv/bin/python -m ruff format packages/worldkeeper`.\n"
        f"DONE WHEN `bash {D}/check_round1.sh` prints PASS round 1."
    )


manifest = {
    "run_name": "worldkeeper-boundary",
    "workdir": "/home/bcorfman/dev/ringer-work/worldkeeper-boundary-round1",
    "max_parallel": 1,
    "worktrees": False,
    "repo": ROOT,
    "tasks": [
        {
            "task_type": "code-feature",
            "engine": "codex",
            "model": "gpt-5.6-luna",
            "engine_args": ["-c", "model_reasoning_effort=high"],
            "full_access": True,
            "max_attempts": 2,
            "timeout_s": 3600,
            "check_timeout_s": 600,
            "key": "world-helpers",
            "ownership": [
                f"{ROOT}/packages/worldkeeper/src/worldkeeper/model.py",
                f"{ROOT}/packages/worldkeeper/tests/test_boundary_helpers.py",
                f"{D}/round1-notes.md",
            ],
            "expect_files": [f"{ROOT}/packages/worldkeeper/tests/test_boundary_helpers.py", f"{D}/round1-notes.md"],
            "verified": "executed check: every core helper exists on World/WorldSchema and is called in the new tests, "
            "skipped optional helpers are explained, storygame and tests untouched, worldkeeper and world-model "
            "suites pass, ruff clean",
            "spec": spec(),
            "check": f"bash {D}/check_round1.sh",
        }
    ],
}
out = Path(D) / "round1-manifest.json"
out.write_text(json.dumps(manifest, indent=2) + "\n")
print(out)
