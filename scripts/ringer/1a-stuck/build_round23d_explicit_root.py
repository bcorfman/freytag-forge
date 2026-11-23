"""Round 23d: state_from_snapshot takes its story root explicitly (no guessing)."""

import json
from pathlib import Path

import build_round23a_entry_state_foundation as a

SPEC = a.COMMON + (
    "\n\nYou may edit ONLY: storygame/runtime/entry_snapshots.py, storygame/web_demo.py, "
    "tests/test_entry_snapshots.py, tests/test_start_scene_session.py.\n\n"
    "PROBLEM. `state_from_snapshot(package, snapshot)` in storygame/runtime/entry_snapshots.py finds the package's "
    "source root with `_package_root(package)`, which imports the private `storygame.story_source.lookup."
    "_source_trees` and falls back to `Path.cwd() / 'data' / 'stories' / story_id`. In the full test suite another "
    "test clears that registry and the guess raises `EntrySnapshotError: cannot determine the source root` "
    "(tests/test_start_scene_session.py::test_canonical_default_session_matches_snapshot_and_accepts_turn fails in "
    "the full run but passes alone). Guessing a root is a latent production bug too.\n\n"
    "CHANGE. Delete `_package_root` and its private import. `state_from_snapshot(package, snapshot, story_root)` "
    "takes the root as a required third argument (a `Path`), uses it for the fingerprint comparison, and nothing "
    "else changes. Update every caller: web_demo.py already knows each package's root (`package_roots_by_id`), "
    "`check_entry_snapshots`, `write_entry_snapshots` and any helper in entry_snapshots.py that called "
    "`_package_root` or `_package_fingerprint` pass the root they already have; update all tests. Add a test in "
    "tests/test_entry_snapshots.py proving there is no ambient lookup: clear any module-level source-tree cache "
    "you can reach (or run in a subprocess started in a temporary working directory) and show "
    "`state_from_snapshot` still works with an explicit root and raises `EntrySnapshotError` (not a different "
    "error) when the root's files do not match the snapshot fingerprint. Run: tests/test_entry_snapshots.py "
    "tests/test_start_scene_session.py tests/test_web_demo.py tests/test_canonical_entry_path.py "
    "tests/test_world_model.py packages/worldkeeper/tests, then ALSO the whole `tests/` directory once "
    "(`.venv/bin/python -m pytest -q -p no:cacheprovider -n 8 tests`; about 3 minutes) and report its result in "
    "NOTES.txt."
)

OWNED = r"storygame/runtime/entry_snapshots\.py|storygame/web_demo\.py|tests/test_entry_snapshots\.py|tests/test_start_scene_session\.py"
BODY = """.venv/bin/python -m pytest -q -p no:cacheprovider -n 8 tests packages/worldkeeper/tests
.venv/bin/python -m storygame.runtime.entry_snapshots check
if grep -n "_source_trees\\|_package_root" storygame/runtime/entry_snapshots.py; then echo 'root guessing remains'; exit 1; fi"""

manifest = {
    "run_name": "entry-snapshot-explicit-root",
    "workdir": a.WORK,
    "max_parallel": 1,
    "worktrees": True,
    "repo": a.REPO,
    "tasks": [
        {
            "key": "explicit-root",
            "task_type": "code-fix",
            "engine": "codex",
            "engine_args": ["-c", "model_reasoning_effort=high"],
            "max_attempts": 2,
            "timeout_s": 2400,
            "check_timeout_s": 900,
            "ownership": [
                "storygame/runtime/entry_snapshots.py",
                "storygame/web_demo.py",
                "tests/test_entry_snapshots.py",
                "tests/test_start_scene_session.py",
            ],
            "spec": SPEC,
            "check": a.check(OWNED, BODY, "explicit-root", 600),
            "expect_files": [],
            "verified": "state_from_snapshot never guesses its root, and the full suite passes.",
        }
    ],
}
Path(__file__).with_name("round23d-explicit-root-manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")
