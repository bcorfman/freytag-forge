# ruff: noqa: E501  (spec strings are prose briefs for a worker)
"""Fix the flaky test_find_codex_session_prefers_latest_nested_match: one Luna task, one test file.

Usage: build_flaky_codex_session_manifest.py
"""

from __future__ import annotations

import json
from pathlib import Path

REPO = "/home/bcorfman/dev/freytag-forge"
WORK = "/home/bcorfman/dev/ringer-work/flaky-codex-session"
TEST = "tests/test_factory_limits.py"

SPEC = """You are a Python engineer. Your current working directory IS a git worktree of @REPO@ (detached at HEAD). Edit files here directly. NEVER git commit, never touch @REPO@ itself, never run `uv`, never call a model or the network. FIRST run: [ -e .venv ] || ln -s @REPO@/.venv .venv . Ruff: `.venv/bin/python -m ruff check <files>` and `.venv/bin/python -m ruff format <files>`. Never pass --cov to pytest. Run tests as `PYTHONPATH=$PWD:$PWD/packages/worldkeeper/src TMPDIR=/tmp .venv/bin/python -m pytest -q -p no:cacheprovider -n 0 tests/test_factory_limits.py`.

PROBLEM. `tests/test_factory_limits.py::test_find_codex_session_prefers_latest_nested_match` is flaky in CI. It writes two session files and calls `.touch()` on each back to back, then expects `find_codex_session("thread", tmp_path)` (in `factory/limits.py`, it returns `max(matches, key=mtime)`) to return the second file. On a filesystem with a coarse clock both files get the same mtime, `max` returns the first match, and the test fails (it did on CI on 2026-11-20: it returned `2026/01/a-thread.jsonl` instead of `2026/02/b-thread.jsonl`). The production code is correct; the test does not control the thing it asserts.

YOUR TASK. Edit ONLY `@TEST@`, ONLY that one test function. Replace the two `.touch()` calls with explicit, clearly different modification times set through `os.utime` (add `import os` in the file's import block if it is missing), for example the first file at a fixed earlier time and the second 100 seconds later, so the result does not depend on the clock. Keep the file order (second is the newer one), the names, and both assertions, including the `find_codex_session("missing", tmp_path) is None` line. Do NOT edit `factory/limits.py`, do not add a sleep, a skip, an xfail or a retry, and do not touch any other test. Then run the test file and ruff.
"""

CHECK = """set -e
WORK=@WORK@
mkdir -p "$WORK/out"
export PYTHONPATH=$PWD:$PWD/packages/worldkeeper/src TMPDIR=/tmp
[ -e .venv ] || ln -s @REPO@/.venv .venv
git add -A -- factory tests
bad=$(git diff --cached --name-only | grep -vxF -e @TEST@ || true)
[ -z "$bad" ] || { echo "files outside ownership staged: $bad"; exit 1; }
[ -n "$(git diff --cached --name-only)" ] || { echo "no change made"; exit 1; }
git diff --cached -U0 | grep -E '^\\+' | grep -E 'os\\.utime' >/dev/null || { echo "the fix must use os.utime"; exit 1; }
if git diff --cached -U0 | grep -E '^\\+' | grep -E 'sleep|skip|xfail|retry'; then echo "no sleep, skip, xfail or retry allowed"; exit 1; fi
start=$(date +%s)
.venv/bin/python -m pytest -q -p no:cacheprovider -n 0 @TEST@
t=@TEST@::test_find_codex_session_prefers_latest_nested_match
i=0
while [ $i -lt 30 ]; do
  .venv/bin/python -m pytest -q -p no:cacheprovider -n 0 "$t" >/dev/null 2>&1 || { echo "target test failed on repeat $i"; exit 1; }
  i=$((i+1))
done
took=$(( $(date +%s) - start ))
echo "tests took $took s (budget 60 s)"
[ "$took" -le 60 ] || { echo "over the 60 s budget"; exit 1; }
# the fixed test must still catch a wrong pick: make the code return the oldest match and expect the test to fail
cp factory/limits.py "$WORK/out/limits.py.orig"
sed -i 's/return max(matches, key=lambda path: path.stat().st_mtime, default=None)/return min(matches, key=lambda path: path.stat().st_mtime, default=None)/' factory/limits.py
if cmp -s factory/limits.py "$WORK/out/limits.py.orig"; then echo "mutation did not apply"; exit 1; fi
if .venv/bin/python -m pytest -q -p no:cacheprovider -n 0 "$t" >/dev/null 2>&1; then cp "$WORK/out/limits.py.orig" factory/limits.py; echo "test still passes when the code picks the oldest file"; exit 1; fi
cp "$WORK/out/limits.py.orig" factory/limits.py
git status --short factory | grep . && { echo "factory/limits.py not restored"; exit 1; }
.venv/bin/python -m ruff check @TEST@
.venv/bin/python -m ruff format --check @TEST@
git diff --cached > $WORK/out/flaky.patch
test -s $WORK/out/flaky.patch
"""


def build() -> dict:
    return {
        "run_name": "flaky-codex-session",
        "workdir": WORK,
        "max_parallel": 1,
        "worktrees": True,
        "repo": REPO,
        "tasks": [
            {
                "key": "fix-flaky-test",
                "task_type": "code-fix",
                "engine": "codex",
                "model": "gpt-5.6-luna",
                "engine_args": ["-c", "model_reasoning_effort=high"],
                "max_attempts": 2,
                "timeout_s": 900,
                "check_timeout_s": 300,
                "ownership": [TEST],
                "spec": SPEC.replace("@REPO@", REPO).replace("@TEST@", TEST),
                "check": CHECK.replace("@REPO@", REPO).replace("@WORK@", WORK).replace("@TEST@", TEST),
                "expect_files": [],
                "verified": "Only the one test file changes, using os.utime; the test passes 30 times in a row; it fails when the code is mutated to pick the oldest file; ruff clean; under a 60 s budget.",
            }
        ],
    }


if __name__ == "__main__":
    out = Path(__file__).with_name("flaky-codex-session-manifest.json")
    out.write_text(json.dumps(build(), indent=2) + "\n", encoding="utf-8")
    print(out)
