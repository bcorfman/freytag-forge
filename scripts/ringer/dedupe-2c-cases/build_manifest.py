# ruff: noqa: E501  (spec strings are prose briefs for a worker)
"""Build the one-task Ringer manifest that drops four duplicate parametrized cases in the 2C commitment test."""

from __future__ import annotations

import json
from pathlib import Path

REPO = "/home/bcorfman/dev/freytag-forge"
WORK = "/home/bcorfman/dev/ringer-work/dedupe-2c-cases"
OWNED = ["tests/test_recovery_after_choice.py"]
SPEC = (
    "You are a Python engineer. Your current working directory IS a git worktree of "
    + REPO
    + " (detached at HEAD). Edit files here directly. NEVER git commit, never touch "
    + REPO
    + " itself, never run `uv`, never call a billed model or the network. FIRST run: [ -e .venv ] || ln -s "
    + REPO
    + "/.venv .venv . Run tests as `PYTHONPATH=$PWD:$PWD/packages/worldkeeper/src TMPDIR=/tmp .venv/bin/python -m pytest -q -p no:cacheprovider -n 0 <files>` (never pass --cov); ruff as `.venv/bin/python -m ruff check <files>` and `.venv/bin/python -m ruff format <files>`."
    + """

TASK. In tests/test_recovery_after_choice.py, `test_2c_commitment_is_exclusive_and_late_commitment_is_honoured` is parametrized over commitment (k_sl_2c_d_r3, k_sl_2c_d_r4) x (commit_turn, timing) x read_observation (True, False). When read_observation is False the body never uses `commitment` (it drives `None` and only asserts that no commitment fact exists), so the False cases for r3 and r4 are exact duplicates of each other (same steps, same assertions) and run twice for nothing.
Change ONLY the parametrization so each distinct behaviour runs once: replace the separate `commitment` and `read_observation` parametrize decorators by one decorator over (read_observation, commitment) with exactly three cases: (True, "k_sl_2c_d_r3"), (True, "k_sl_2c_d_r4"), (False, None), with readable ids ("read-r3", "read-r4", "no-read"). Keep the (commit_turn, timing) decorator as is. Update the function signature type for `commitment` to `str | None`. Do not change the body logic or any assertion. That gives 12 cases instead of 16: the eight True cases are unchanged in behaviour and the four False cases remain once. Edit no other file; never weaken any other test.

DONE WHEN the owned file passes pytest, ruff check and ruff format --check are clean, and the test collects exactly 12 cases."""
)


def check() -> str:
    return f"""set -eo pipefail
[ -e .venv ] || ln -s {REPO}/.venv .venv
export PYTHONPATH=$PWD:$PWD/packages/worldkeeper/src TMPDIR=/tmp
F="{OWNED[0]}"
.venv/bin/python -m pytest -q -p no:cacheprovider -n 0 $F 2>&1 | tail -4
n=$(.venv/bin/python -m pytest --collect-only -q -p no:cacheprovider -n 0 $F 2>&1 | grep -c "test_2c_commitment_is_exclusive_and_late_commitment_is_honoured\\[" || true)
[ "$n" = "12" ] || {{ echo "expected 12 collected cases, got $n"; exit 1; }}
.venv/bin/python -m ruff check $F
.venv/bin/python -m ruff format --check $F
git add -A -- tests
bad=$(git diff --cached --name-only | grep -v -x -e {OWNED[0]} || true)
[ -z "$bad" ] || {{ echo "files outside ownership staged: $bad"; exit 1; }}
git diff --cached --binary > {WORK}/dedupe.patch
test -s {WORK}/dedupe.patch
"""


manifest = {
    "run_name": "dedupe-2c-cases",
    "workdir": WORK,
    "max_parallel": 1,
    "worktrees": True,
    "repo": REPO,
    "tasks": [
        {
            "key": "dedupe-2c-commitment-cases",
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
            "verified": "4 duplicate parametrized cases dropped (16 -> 12), behaviour of the 8 reading cases unchanged, only the one owned file changed.",
        }
    ],
}

if __name__ == "__main__":
    Path(WORK).mkdir(parents=True, exist_ok=True)
    out = Path(__file__).with_name("manifest.json")
    out.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    print(out)
