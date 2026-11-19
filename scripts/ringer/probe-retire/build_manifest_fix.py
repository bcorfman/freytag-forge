# ruff: noqa: E501  (spec strings are prose briefs for a worker)
"""Build the one-task Ringer manifest that removes two tests of a deleted probe manifest."""

from __future__ import annotations

import json
from pathlib import Path

REPO = "/home/bcorfman/dev/freytag-forge"
WORK = "/home/bcorfman/dev/ringer-work/probe-retire-fix"
OWNED = ["tests/test_t9h_run_manifests.py"]
SPEC = (
    "You are a Python engineer. Your current working directory IS a git worktree of "
    + REPO
    + " (detached at HEAD). Edit files here directly. NEVER git commit, never touch "
    + REPO
    + " itself, never run `uv`, never call a billed model or the network. FIRST run: [ -e .venv ] || ln -s "
    + REPO
    + "/.venv .venv ; then run `git apply "
    + WORK
    + "/state.patch` (it brings the worktree to the owner's branch, in which the probe scripts and the file scripts/ringer/environment_narration/run-t9h-probe-live.json and make_t9h_probe_run_manifest.py are already deleted; the patch is not yours to edit). Run tests as `PYTHONPATH=$PWD:$PWD/packages/worldkeeper/src TMPDIR=/tmp .venv/bin/python -m pytest -q -p no:cacheprovider -n 0 tests/test_t9h_run_manifests.py` (never pass --cov); ruff as `.venv/bin/python -m ruff check tests/test_t9h_run_manifests.py` and `.venv/bin/python -m ruff format tests/test_t9h_run_manifests.py`."
    + """

TASK. The probe experiment scripts were retired. tests/test_t9h_run_manifests.py has two tests that exist only to check the deleted probe run manifest, and they now fail with FileNotFoundError: `test_generated_t9h_probe_manifest_matches_committed_json` and `test_t9h_probe_manifest_has_request_cap_and_integrity_check`. Delete exactly those two test functions. Then remove any import, constant or helper in the file that only they used (for example `shutil`, `tempfile`, `subprocess`, `json`, `os` if nothing else in the file still uses them; check each, do not guess). Never touch the other tests in the file, never weaken one, edit no other file.

DONE WHEN the remaining tests in tests/test_t9h_run_manifests.py all pass, ruff check and ruff format --check are clean on the file, and the file defines neither of the two deleted tests."""
)
CHECK = f"""set -eo pipefail
[ -e .venv ] || ln -s {REPO}/.venv .venv
export PYTHONPATH=$PWD:$PWD/packages/worldkeeper/src TMPDIR=/tmp
.venv/bin/python -m pytest -q -p no:cacheprovider -n 0 tests/test_t9h_run_manifests.py 2>&1 | tail -6
.venv/bin/python -m ruff check tests/test_t9h_run_manifests.py
.venv/bin/python -m ruff format --check tests/test_t9h_run_manifests.py
! grep -q "def test_generated_t9h_probe_manifest_matches_committed_json\\|def test_t9h_probe_manifest_has_request_cap_and_integrity_check" tests/test_t9h_run_manifests.py
grep -c "^def test" tests/test_t9h_run_manifests.py | grep -qx 4
bad=$(git status --porcelain | grep -v "tests/test_t9h_run_manifests.py" | grep -v "^D \\|^ D\\|^A \\|^M " || true)
git diff --stat -- tests/test_t9h_run_manifests.py | tail -1
git diff -- tests/test_t9h_run_manifests.py > {WORK}/fix.patch
test -s {WORK}/fix.patch
"""
manifest = {
    "run_name": "probe-retire-fix",
    "workdir": WORK,
    "max_parallel": 1,
    "worktrees": True,
    "repo": REPO,
    "tasks": [
        {
            "key": "drop-t9h-probe-manifest-tests",
            "task_type": "code-fix",
            "engine": "codex",
            "engine_args": ["-c", "model_reasoning_effort=low"],
            "max_attempts": 2,
            "timeout_s": 900,
            "check_timeout_s": 300,
            "ownership": OWNED,
            "spec": SPEC,
            "check": CHECK,
            "expect_files": [],
            "verified": "the two tests of the deleted probe manifest are gone, the file's other four tests pass, and nothing else changed.",
        }
    ],
}
if __name__ == "__main__":
    Path(WORK).mkdir(parents=True, exist_ok=True)
    out = Path(__file__).with_name("manifest_fix.json")
    out.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    print(out)
