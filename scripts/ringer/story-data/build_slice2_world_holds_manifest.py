"""Build the Ringer manifest for slice 2, task 1: World.holds."""

import json
from pathlib import Path

REPO = "/home/bcorfman/dev/freytag-forge"
MODEL_FILE = f"{REPO}/packages/worldkeeper/src/worldkeeper/model.py"
TEST_FILE = f"{REPO}/packages/worldkeeper/tests/test_holds.py"

SPEC = f"""You are an implementation worker for the freytag-forge repository at {REPO}. Boundary: NO model call, NO network call, never git commit. You own ONLY these two files: {MODEL_FILE} (edit: add one method) and {TEST_FILE} (create). Touch nothing else.

GOAL. Add a world-state-only method to class World in {MODEL_FILE}, placed right after the existing method `holder` (which returns the containing character, if held):

    def holds(self, holder_id, entity_id):
        \"\"\"Return whether a character holds an entity, directly or nested in what it holds.\"\"\"

It returns True exactly when `self.holder(entity_id) == holder_id` and holder_id is not None; it returns False for an unplaced entity, an entity in an area with no character above it, and an entity held by a different character. It must not raise for an unknown entity id if `holder` does not raise for it (mirror `holder`). Do not change any other method.

TESTS. Create {TEST_FILE} (pytest, module-level functions, compact). Copy the schema/world setup style from {REPO}/packages/worldkeeper/tests/test_people_alongside.py (WorldSchema.from_data, World(schema, MemoryBackend()), world.seed(), world.move(...)). Entities needed: an area, two characters, an item (kind "item"), a container (kind "container") holding an item. Cases: item moved to character A -> holds(A, item) True and holds(B, item) False; item in the area -> False for both; item inside a container that is moved to A -> holds(A, item) True; after moving the item to B -> holds(A, item) False and holds(B, item) True; holder_id None -> False. Check the kinds your setup uses exist in the schema (see how the other tests or model.py declare the item and container kinds; use whatever kinds `is_item` accepts).

HOW TO RUN (from {REPO}; never bare python, never uv; never --cov): `export TMPDIR=/tmp PYTHONPATH={REPO}:{REPO}/packages/worldkeeper/src && {REPO}/.venv/bin/python -m pytest {TEST_FILE} -q --no-cov -p no:cacheprovider 2>&1 | tail -30`. Format and lint: `{REPO}/.venv/bin/python -m ruff format {MODEL_FILE} {TEST_FILE} && {REPO}/.venv/bin/python -m ruff check {MODEL_FILE} {TEST_FILE}`. Also run the existing worldkeeper tests to prove nothing else changed: `{REPO}/.venv/bin/python -m pytest {REPO}/packages/worldkeeper/tests -q --no-cov -p no:cacheprovider 2>&1 | tail -5`."""

CHECK = f"""set -o pipefail
cd {REPO}
export TMPDIR=/tmp PYTHONPATH={REPO}:{REPO}/packages/worldkeeper/src
PY={REPO}/.venv/bin/python
$PY -m ruff check {MODEL_FILE} {TEST_FILE}
$PY -m ruff format --check {MODEL_FILE} {TEST_FILE}
grep -n "def holds" {MODEL_FILE}
$PY -m pytest {TEST_FILE} -q --no-cov -p no:cacheprovider 2>&1 | tail -15
$PY -m pytest {REPO}/packages/worldkeeper/tests -q --no-cov -p no:cacheprovider 2>&1 | tail -5
# only the two owned files may differ from the base for these paths
git diff --stat -- packages/worldkeeper
"""

manifest = {
    "run_name": "story-data-gap-rules",
    "workdir": "/home/bcorfman/dev/ringer-work/story-data-gap-rules",
    "max_parallel": 1,
    "worktrees": False,
    "repo": REPO,
    "tasks": [
        {
            "key": "world-holds",
            "task_type": "code-feature",
            "engine": "codex",
            "model": "gpt-5.6-luna",
            "engine_args": ["-c", "model_reasoning_effort=medium"],
            "max_attempts": 2,
            "timeout_s": 1200,
            "check_timeout_s": 600,
            "ownership": [MODEL_FILE, TEST_FILE],
            "expect_files": [TEST_FILE],
            "spec": SPEC,
            "check": CHECK,
            "verified": "the new World.holds method exists, its tests pass, lint is clean, and all existing worldkeeper tests still pass",
        }
    ],
}

out = Path(__file__).with_name("slice2-world-holds-manifest.json")
out.write_text(json.dumps(manifest, indent=2) + "\n")
print(out)
