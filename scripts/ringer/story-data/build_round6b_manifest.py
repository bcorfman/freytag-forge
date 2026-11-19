# ruff: noqa: E501  (spec strings are prose briefs for a worker)
"""Build the Ringer manifest for round 6b: the loader compiles the source tree when ownership.yaml says so (1 task)."""

from __future__ import annotations

import json
from pathlib import Path

REPO = "/home/bcorfman/dev/freytag-forge"
WORK = "/home/bcorfman/dev/ringer-work/story-data-round6b"
KEY = "r6b-loader"

OWNED = [
    "storygame/story_package/loader.py",
    "tests/test_loader_source_dispatch.py",
]

SPEC = (
    "You are a Python engineer. Your current working directory IS a git worktree of "
    + REPO
    + " (detached at HEAD). Edit files here directly. NEVER git commit, never touch "
    + REPO
    + " itself, never run `uv`, never call a billed model or the network. FIRST run: [ -e .venv ] || ln -s "
    + REPO
    + """/.venv .venv ; run tests as `PYTHONPATH=$PWD:$PWD/packages/worldkeeper/src TMPDIR=/tmp .venv/bin/python -m pytest -q -p no:cacheprovider -n 0 <files>` (never pass --cov); ruff as `.venv/bin/python -m ruff check <files>` and `.venv/bin/python -m ruff format <files>` (line length 120, double quotes, Python 3.12, no new dependencies).

BACKGROUND. The default story's data is moving from nine legacy files (plot.md, storylets.md, world.yaml, ...) per story package root to a source tree compiled by `storygame.story_source.compile_source_tree(source_root)` into the same `StoryPackage`. The converted tree is committed at data/stories/continuity-initiative/source/ and holds parity with the legacy package. `storygame/story_source/compiler.py` already imports `storygame.story_package.loader` (it calls private loader validators), so the loader must import the compiler lazily INSIDE a function, never at module top, or you create an import cycle. The contract is .plans/story-data-schema-contract.md section 2 (read it; never edit it): a package root may hold `ownership.yaml` (keys `schema`, `catalog`, `scenes`; each value `legacy` or `compiled`; absent file means everything is legacy) and `source/`. The source tree validator (`storygame/story_source/l1_root.py`) already checks ownership.yaml's shape.

YOUR JOB, in `load_story_package` / `_load_story_package_uncached` of storygame/story_package/loader.py (use Serena or read it first; keep the fingerprint cache working; the fingerprint already hashes every file under the root):
1. When `<root>/ownership.yaml` exists and says `catalog: compiled` AND every scene listed is `compiled` AND the list covers every scene in `<root>/source/story.yaml`'s `scenes`, load by returning `compile_source_tree(<root>/source)` and never read the legacy files (they may be absent).
2. When ownership.yaml exists but mixes legacy and compiled (catalog or any scene), or is malformed, raise `StoryPackageError` with a message that says mixed ownership is not supported yet and names the offending entries. When ownership.yaml is absent, behaviour is exactly as today.
3. Add a public `load_legacy_story_package(root: Path) -> StoryPackage` that loads the legacy files only, ignoring ownership.yaml and source/ (cached the same way, with a cache key that cannot collide with the dispatching loader's). Do not change any other caller.
Do not add ownership.yaml to data/stories/continuity-initiative; the real story stays on legacy loading in this round (a later round flips it). Compiler diagnostics must surface as the compiler already raises them.

TESTS: write tests/test_loader_source_dispatch.py (a flat file, like the other tests/test_*.py files). Each test copies data/stories/continuity-initiative to tmp_path with shutil.copytree: (a) no ownership.yaml: result equals the legacy load, `model_dump()` equal; (b) ownership.yaml all compiled, legacy files deleted from the copy: result's `model_dump()` equals `compile_source_tree(copy/source).model_dump()`; (c) all compiled with the legacy files still present, and a legacy file deliberately corrupted: still loads (proves legacy files unread); (d) mixed ownership raises StoryPackageError mentioning "mixed"; (e) `load_legacy_story_package` on the all-compiled copy with the legacy files present returns the legacy package, equal to test (a)'s; (f) editing the copy's source/ file changes the result (cache fingerprint). Write the ownership.yaml in tests with yaml.safe_dump. Keep tests few and fast.

HARD LIMITS. Never edit existing tests, tests/shard_durations.json, docs/, data/, the contract or any other file under storygame/. After your change the existing suite must still pass: the check runs tests/story_source, tests/story_package* and a sample of loader tests. If after real effort a defect needs a change outside the ownership list, write it in NOTES_r6b.txt (worktree root, never committed) and leave it.
"""
)


def check() -> str:
    keep = " ".join(f"-e '^{p}$'" for p in OWNED + ["tests/_unused_placeholder"])
    return f"""set -eo pipefail
[ -e .venv ] || ln -s {REPO}/.venv .venv
export PYTHONPATH=$PWD:$PWD/packages/worldkeeper/src TMPDIR=/tmp
out=$(mktemp)
rc=0
.venv/bin/python -m pytest -q -p no:cacheprovider -n 0 -rs tests/test_loader_source_dispatch.py > "$out" 2>&1 || rc=$?
tail -30 "$out"
[ "$rc" -eq 0 ] || exit "$rc"
if grep -E "SKIPPED" "$out"; then echo "a gate test skips"; exit 1; fi
n=$(grep -cE "^def test_" tests/test_loader_source_dispatch.py)
[ "$n" -ge 6 ] || {{ echo "expected at least 6 tests, found $n"; exit 1; }}
rc=0
.venv/bin/python -m pytest -q -p no:cacheprovider -n 4 tests/story_source $(ls tests/test_*loader*.py tests/test_*story_package*.py 2>/dev/null) > "$out" 2>&1 || rc=$?
tail -15 "$out"
[ "$rc" -eq 0 ] || exit "$rc"
.venv/bin/python -m ruff check storygame/story_package/loader.py tests/test_loader_source_dispatch.py
.venv/bin/python -m ruff format --check storygame/story_package/loader.py tests/test_loader_source_dispatch.py
git add -A -- storygame tests data
bad=$(git diff --cached --name-only | grep -v {keep} || true)
[ -z "$bad" ] || {{ echo "files outside ownership staged: $bad"; exit 1; }}
git diff --cached > {WORK}/{KEY}.patch
test -s {WORK}/{KEY}.patch
"""


manifest = {
    "run_name": "story-data-round6",
    "workdir": WORK,
    "max_parallel": 1,
    "worktrees": True,
    "repo": REPO,
    "tasks": [
        {
            "key": KEY,
            "task_type": "code-feature",
            "engine": "codex",
            "engine_args": ["-c", "model_reasoning_effort=high"],
            "max_attempts": 2,
            "timeout_s": 3600,
            "check_timeout_s": 1200,
            "ownership": OWNED,
            "spec": SPEC,
            "check": check(),
            "expect_files": [],
            "verified": "load_story_package compiles source/ when ownership.yaml marks everything compiled, raises on mixed ownership, is unchanged without ownership.yaml; load_legacy_story_package ignores both; new tests pass; only owned files changed; ruff clean.",
        }
    ],
}

if __name__ == "__main__":
    out = Path(__file__).with_name("round6b-manifest.json")
    out.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    print(out)
