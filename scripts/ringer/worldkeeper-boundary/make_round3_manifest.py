"""Build round 3 of the worldkeeper boundary moves: remove the taking.py fallback walk and make
World.reachable_from_seat return ids."""

import json
from pathlib import Path

ROOT = "/home/bcorfman/dev/freytag-forge"
D = f"{ROOT}/scripts/ringer/worldkeeper-boundary"
OWNED = [
    "storygame/runtime/taking.py",
    "tests/test_taking.py",
    "storygame/runtime/seating.py",
    "packages/worldkeeper/src/worldkeeper/model.py",
    "packages/worldkeeper/tests/test_boundary_helpers.py",
]

SPEC = f"""You are a code worker in the freytag-forge repository at {ROOT}, branch worldkeeper-boundary-moves, \
already checked out. Do NOT git commit, push, switch branches, stash or revert. Edit ONLY: {", ".join(OWNED)}.

BACKGROUND: a firm project rule says world-model logic (anything that reads or changes only world state) lives in \
packages/worldkeeper as World methods with tests there; storygame only adapts and calls them. The last two commits \
(git show HEAD~1 and HEAD) moved storygame tree walks into new World helpers. Two leftovers break the rule:

1. storygame/runtime/taking.py `take_before_put` calls `world.takeable_items(...)` but keeps a copy of the old walk \
behind `if hasattr(world, "takeable_items")`. It exists only because tests/test_taking.py builds a hand-written fake \
`class World`. Remove the fallback so take_before_put always calls world.takeable_items. Rewrite tests/test_taking.py \
to use the real worldkeeper World: build a small schema with `WorldSchema.from_data({{...}})` and \
`World(schema, MemoryBackend())`, call `seed()`, and use `place`/`move` (see packages/worldkeeper/README.md and \
packages/worldkeeper/tests/ for style), with entities that reproduce each existing test's scenario (fixed items, \
vehicles, held items, other areas, the protagonist). Keep every existing test and the meaning of its assertions on \
take_before_put's result (commands, prose, refusals); the Item/NPC/package stand-ins for the story package may stay. \
Player commands in tests stay imperative first-person, as they are now.

2. World.reachable_from_seat in packages/worldkeeper returns NAMES (its docstring says "legacy seat-reach names"). \
A World method returns ids. Make it return entity ids in the same order (World.entity_ids order), rewrite its \
docstring without the word "legacy", update its tests in packages/worldkeeper/tests/test_boundary_helpers.py, and in \
storygame/runtime/seating.py `stand_before_leave` map the ids to names with world.name at the call site so \
needs_to_stand receives exactly the same names as before.

Behaviour seen by the game must not change. HOW TO RUN (never use uv; your sandbox cannot run it): Python is \
{ROOT}/.venv/bin/python with PYTHONPATH set to the repo root and TMPDIR=/tmp. Ruff: \
.venv/bin/python -m ruff format FILES, then .venv/bin/python -m ruff check FILES.
DONE WHEN `bash {D}/check_round3.sh` prints PASS round 3 (it checks the fallback and fake World are gone, test count \
did not drop, reachable_from_seat returns ids, and runs about 1,300 focused tests plus ruff)."""

manifest = {
    "run_name": "worldkeeper-boundary",
    "workdir": "/home/bcorfman/dev/ringer-work/worldkeeper-boundary-round3",
    "max_parallel": 1,
    "worktrees": False,
    "repo": ROOT,
    "tasks": [
        {
            "task_type": "code-fix",
            "engine": "codex",
            "model": "gpt-5.6-luna",
            "engine_args": ["-c", "model_reasoning_effort=high"],
            "full_access": True,
            "max_attempts": 2,
            "timeout_s": 2400,
            "check_timeout_s": 600,
            "key": "cleanup",
            "ownership": [f"{ROOT}/{path}" for path in OWNED],
            "expect_files": [f"{ROOT}/tests/test_taking.py"],
            "verified": "executed check: no fallback walk in taking.py, test_taking uses the real worldkeeper World "
            "with no fewer tests, reachable_from_seat returns ids, ~1,300 focused tests pass, ruff clean",
            "spec": SPEC,
            "check": f"bash {D}/check_round3.sh",
        }
    ],
}
out = Path(D) / "round3-manifest.json"
out.write_text(json.dumps(manifest, indent=2) + "\n")
print(out)
