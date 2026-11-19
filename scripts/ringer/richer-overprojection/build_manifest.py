# ruff: noqa: E501  (spec strings are prose briefs for a worker)
"""Build the one-task Ringer manifest that folds five copied overprojection tests into one parametrized test."""

from __future__ import annotations

import json
from pathlib import Path

REPO = "/home/bcorfman/dev/freytag-forge"
WORK = "/home/bcorfman/dev/ringer-work/richer-overprojection"
SCENES = {"1C": 0, "2A": 2, "2B": 5, "2C": 4, "3A": 1}
SOURCES = [f"tests/test_richer_{scene.lower()}.py" for scene in SCENES]
NEW = "tests/test_richer_overprojection.py"
OWNED = SOURCES + [NEW]
SPEC = (
    "You are a Python engineer. Your current working directory IS a git worktree of "
    + REPO
    + " (detached at HEAD). Edit files here directly. NEVER git commit, never touch "
    + REPO
    + " itself, never run `uv`, never call a billed model or the network. FIRST run: [ -e .venv ] || ln -s "
    + REPO
    + "/.venv .venv . Run tests as `PYTHONPATH=$PWD:$PWD/packages/worldkeeper/src TMPDIR=/tmp .venv/bin/python -m pytest -q -p no:cacheprovider -n 0 <files>` (never pass --cov); ruff as `.venv/bin/python -m ruff check <files>` and `.venv/bin/python -m ruff format <files>`."
    + """

TASK. Five test files each hold a copy of `test_the_richer_scene_adds_no_beat_overprojection`, identical except for the scene id and the allowed count (and the count's comment). They are in tests/test_richer_1c.py (scene 1C, cap 0), test_richer_2a.py (2A, cap 2), test_richer_2b.py (2B, cap 5), test_richer_2c.py (2C, cap 4), test_richer_3a.py (3A, cap 1). Fold them into ONE parametrized test:
1. Create tests/test_richer_overprojection.py. It imports `audit_package` from storygame.audit, defines ROOT = Path("data/stories/continuity-initiative") and a module-scoped pytest fixture that calls `audit_package(ROOT)["findings"]` ONCE and returns the list. One test `test_the_richer_scene_adds_no_beat_overprojection(scene_id, cap, findings)` parametrized over [("1C", 0), ("2A", 2), ("2B", 5), ("2C", 4), ("3A", 1)] with ids "1C", "2A", "2B", "2C", "3A" keeps EXACTLY the original assertions: the filter of findings with check == "beat_overprojection" and scene_id == scene_id; the non-vacuity assertion that some 1A beat_overprojection finding exists (keep its comment: "The 1A findings are known and older; use them to prove this filter is non-vacuous."); and `len(overprojection) <= cap`. Put a one-line module docstring saying each cap is the count measured before that scene's richer data change.
2. In each of the five source files delete that one test function (and its now-orphaned comment). Then remove anything in that file only that test used (the `audit_package` import is expected to become unused; check `Path`, `ROOT` and every other name with a search of the file before removing it).
3. Edit no other file. Never weaken another test, never change a cap.

DONE WHEN the six owned files pass pytest, ruff check and ruff format --check are clean on them, the old function name exists in exactly one file (the new one), and the new test collects 5 cases."""
)


def check() -> str:
    return f"""set -eo pipefail
[ -e .venv ] || ln -s {REPO}/.venv .venv
export PYTHONPATH=$PWD:$PWD/packages/worldkeeper/src TMPDIR=/tmp
F="{" ".join(OWNED)}"
.venv/bin/python -m pytest -q -p no:cacheprovider -n 0 $F 2>&1 | tail -4
.venv/bin/python -m pytest --collect-only -q -p no:cacheprovider -n 0 {NEW} 2>&1 | grep -c "test_the_richer_scene_adds_no_beat_overprojection\\[" | grep -x 5
c=$(git grep -l "def test_the_richer_scene_adds_no_beat_overprojection" -- tests | tr '\\n' ' ')
[ "$c" = "{NEW} " ] || {{ echo "old test name found in: $c"; exit 1; }}
.venv/bin/python -m ruff check $F
.venv/bin/python -m ruff format --check $F
git add -A -- tests
bad=$(git diff --cached --name-only | grep -v -x {" ".join("-e " + p for p in OWNED)} || true)
[ -z "$bad" ] || {{ echo "files outside ownership staged: $bad"; exit 1; }}
git diff --cached --binary > {WORK}/overprojection.patch
test -s {WORK}/overprojection.patch
"""


manifest = {
    "run_name": "richer-overprojection",
    "workdir": WORK,
    "max_parallel": 1,
    "worktrees": True,
    "repo": REPO,
    "tasks": [
        {
            "key": "fold-overprojection-tests",
            "task_type": "code-fix",
            "engine": "codex",
            "engine_args": ["-c", "model_reasoning_effort=low"],
            "max_attempts": 2,
            "timeout_s": 900,
            "check_timeout_s": 300,
            "ownership": OWNED,
            "spec": SPEC,
            "check": check(),
            "expect_files": [],
            "verified": "five copied tests folded into one parametrized test with one audit call; only the six owned files changed.",
        }
    ],
}

if __name__ == "__main__":
    Path(WORK).mkdir(parents=True, exist_ok=True)
    out = Path(__file__).with_name("manifest.json")
    out.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    print(out)
