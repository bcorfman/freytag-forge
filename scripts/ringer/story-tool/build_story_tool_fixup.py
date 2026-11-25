# ruff: noqa: E501
"""Follow-up to build_story_tool.py after review (2026-11-24).

st-fixup: (1) the wiring worker runs under Codex `--sandbox workspace-write`, so it cannot write hand_edits.json next to
plan.json (outside its worktree); it writes it at its worktree root and the check copies it out. (2) Two new wiring tests
pass only when PYTHONPATH is exported. (3) cmd_fmt's single-scene path duplicates format_source_tree's loop.
"""

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from build_story_tool import CORES, REPO, WORK, check_for, common  # noqa: E402

OWNED = ["factory/stations/wiring.py", "tests/test_factory_wiring.py", "storygame/story_cmds/cmd_fmt.py"]
TESTS = "tests/test_factory_wiring.py tests/test_factory_claim_edit.py tests/story_source/test_cmd_fmt.py tests/test_factory_stations.py"
SPEC = (
    common(OWNED)
    + "TODAY (read the code; all of this is committed at HEAD). factory/stations/wiring.py builds a brief (wiring_spec) for a Codex worker that applies one story fix in its own git worktree, "
    "and a check script (_check_extra) that Ringer runs in that worktree. The brief tells the worker to write `hand_edits.json` 'in the same directory as plan.json', and _check_extra reads it from "
    "plan_path.parent; the handler then reads ticket_dir/hand_edits.json and reports `hand edits: N`. storygame/story_cmds/cmd_fmt.py has format_source_tree(root, *, check) and a run() whose "
    "single-scene branch repeats the same loop.\n\n"
    "THREE FIXES.\n"
    "1. The worker runs under Codex `--sandbox workspace-write`: it can write only inside its worktree (its working directory), so it cannot create a file next to plan.json. Change the brief to "
    "say: write hand_edits.json in the root of your working directory (the worktree), as a JSON list, [] when there were none, same entry keys as today. Change _check_extra to read "
    "./hand_edits.json from the worktree root (its working directory), validate it exactly as today, and then copy it to plan_path.parent / 'hand_edits.json', where the handler already reads it. "
    "The ownership check in _check_extra must allow that one untracked file, and it must never reach the delivered patch: find how the station exports and applies the worker's patch (the "
    "manifest from build_manifest/TaskSpec and the handler's apply step) and make sure hand_edits.json is excluded; prove it with a test. The handler side stays as it is.\n"
    "2. tests/test_factory_wiring.py's tests that run the _check_extra script in a subprocess (test_check_extra_rejects_missing_hand_edit_log and test_check_extra_rejects_malformed_hand_edit_log, "
    "and any like them) fail with `ModuleNotFoundError: No module named 'factory'` when PYTHONPATH is not exported, which is how the suite runs in a normal checkout and in CI. Make them hermetic: "
    "give the subprocess the repository root and packages/worldkeeper/src on PYTHONPATH (and any working directory it needs) inside the test. Update them for fix 1.\n"
    "3. In cmd_fmt.py remove the duplicate loop: one private helper formats a given list of paths and returns (changed, refused); format_source_tree and both branches of run() use it. Output, "
    "messages and exit codes of `story_cli fmt` stay exactly as they are (tests/story_source/test_cmd_fmt.py must pass unchanged).\n\n"
    f"HOW TO TEST, exactly as the check does, WITHOUT PYTHONPATH: `env -u PYTHONPATH PYTEST_XDIST_AUTO_NUM_WORKERS={CORES} TMPDIR=/tmp timeout 900 .venv/bin/python -m pytest -q -n {CORES} -p no:cacheprovider {TESTS}`. "
    "All must pass within 600 seconds."
)
PROBE = r"""
from pathlib import Path

from factory.stations import wiring

plan = {"kind": "set_text", "scene": "1A", "set_text": {"address": "x", "text": "y"}}
for kind in ("add_pacing_beat", "edit_claim_evidence", "set_text"):
    brief = wiring.wiring_spec(dict(plan, kind=kind), "data/stories/continuity-initiative")
    assert "hand_edits.json" in brief, f"{kind}: brief lacks hand_edits.json"
    assert "same directory as plan.json" not in brief, f"{kind}: brief still puts hand_edits.json beside plan.json"
extra = wiring._check_extra(Path("/tmp/ticket/plan.json"), "data/stories/continuity-initiative", ["a"])
assert "hand_edits.json" in extra and "plan_path.parent" in extra, "_check_extra does not copy hand_edits.json to plan.json's directory"
print("fixup probe ok")
"""
CHECK = check_for("x", OWNED, "fixup", TESTS, PROBE, 600).replace(
    f"PYTEST_XDIST_AUTO_NUM_WORKERS={CORES} timeout 900",
    f"env -u PYTHONPATH PYTEST_XDIST_AUTO_NUM_WORKERS={CORES} timeout 900",
)
assert "env -u PYTHONPATH" in CHECK

manifest = {
    "run_name": "story-tool-only-edits",
    "workdir": WORK,
    "max_parallel": 1,
    "worktrees": True,
    "repo": REPO,
    "tasks": [
        {
            "key": "st-fixup",
            "task_type": "code-fix",
            "engine": "codex",
            "engine_args": ["-c", "model_reasoning_effort=high"],
            "max_attempts": 2,
            "ownership": OWNED,
            "spec": SPEC,
            "check": CHECK,
            "expect_files": [],
            "timeout_s": 3600,
            "check_timeout_s": 1200,
            "verified": "wiring and fmt tests pass without PYTHONPATH; briefs put hand_edits.json in the worktree; the check copies it beside plan.json",
        }
    ],
}
out = Path(__file__).with_name("story-tool-fixup-manifest.json")
out.write_text(json.dumps(manifest, indent=2) + "\n")
print(out)
