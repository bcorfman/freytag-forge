# ruff: noqa: E501  (spec strings are prose briefs for a worker)
"""Build the one-task Ringer manifest that splits the 88 s golden-corpus test by scene so xdist can spread it."""

from __future__ import annotations

import json
from pathlib import Path

REPO = "/home/bcorfman/dev/freytag-forge"
WORK = "/home/bcorfman/dev/ringer-work/corpus-by-scene"
OWNED = ["tests/test_narration_corpus.py"]
SPEC = (
    "You are a Python engineer. Your current working directory IS a git worktree of "
    + REPO
    + " (detached at HEAD). Edit files here directly. NEVER git commit, never touch "
    + REPO
    + " itself, never run `uv`, never call a billed model or the network. FIRST run: [ -e .venv ] || ln -s "
    + REPO
    + "/.venv .venv . Run tests as `PYTHONPATH=$PWD:$PWD/packages/worldkeeper/src TMPDIR=/tmp .venv/bin/python -m pytest -q -p no:cacheprovider -n 0 <files>` (never pass --cov); ruff as `.venv/bin/python -m ruff check <files>` and `.venv/bin/python -m ruff format <files>`."
    + """

TASK. In tests/test_narration_corpus.py, `test_golden_ok_entries_remain_accepted` loops over all 479 corpus entries in one test (88 s), so a parallel pytest run cannot spread it. Split it by scene without losing any check:
- Parametrize it over the scene ids present in the corpus: `sorted({entry["scene"] for entry in load_corpus()})` (nine scenes today), with the scene id as the test id and a `scene` parameter.
- For each scene it checks only the corpus entries of that scene whose golden verdict is "ok", with exactly the same offender collection and the same assertion message as now.
- Add one small separate test `test_corpus_scenes_all_have_a_prepared_state` asserting every scene id in the corpus is a key of `_SCENE_STATES` (so a new scene cannot silently skip).
- Keep every other test and helper unchanged. Edit no other file; never weaken any other test.

DONE WHEN the owned file passes, ruff check and ruff format --check are clean, and the golden test collects 9 cases."""
)


def check() -> str:
    return f"""set -eo pipefail
[ -e .venv ] || ln -s {REPO}/.venv .venv
export PYTHONPATH=$PWD:$PWD/packages/worldkeeper/src TMPDIR=/tmp
F="{OWNED[0]}"
.venv/bin/python -m pytest -q -p no:cacheprovider -n 4 $F 2>&1 | tail -4
n=$(.venv/bin/python -m pytest --collect-only -q -p no:cacheprovider -n 0 $F 2>&1 | grep -c "test_golden_ok_entries_remain_accepted\\[" || true)
[ "$n" = "9" ] || {{ echo "expected 9 collected golden cases, got $n"; exit 1; }}
.venv/bin/python -m ruff check $F
.venv/bin/python -m ruff format --check $F
git add -A -- tests
bad=$(git diff --cached --name-only | grep -v -x -e {OWNED[0]} || true)
[ -z "$bad" ] || {{ echo "files outside ownership staged: $bad"; exit 1; }}
git diff --cached --binary > {WORK}/corpus.patch
test -s {WORK}/corpus.patch
"""


manifest = {
    "run_name": "corpus-by-scene",
    "workdir": WORK,
    "max_parallel": 1,
    "worktrees": True,
    "repo": REPO,
    "tasks": [
        {
            "key": "split-corpus-by-scene",
            "task_type": "code-fix",
            "engine": "codex",
            "engine_args": ["-c", "model_reasoning_effort=low"],
            "max_attempts": 2,
            "timeout_s": 900,
            "check_timeout_s": 400,
            "ownership": OWNED,
            "spec": SPEC,
            "check": check(),
            "expect_files": [],
            "verified": "the 88 s golden-corpus test is nine per-scene cases with identical checks, plus a guard that every scene has a prepared state.",
        }
    ],
}

if __name__ == "__main__":
    Path(WORK).mkdir(parents=True, exist_ok=True)
    out = Path(__file__).with_name("manifest.json")
    out.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    print(out)
