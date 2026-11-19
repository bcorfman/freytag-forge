# ruff: noqa: E501  (spec strings are prose briefs for a worker)
"""Build the Ringer manifest for round 6c-1: a compiled-story copy helper for tests (1 task)."""

from __future__ import annotations

import json
from pathlib import Path

REPO = "/home/bcorfman/dev/freytag-forge"
WORK = "/home/bcorfman/dev/ringer-work/story-data-round6c1"
KEY = "r6c1-helper"

OWNED = [
    "tests/story_source/helpers.py",
    "tests/story_source/test_compiled_story_copy.py",
]

SPEC = (
    "You are a Python test engineer. Your current working directory IS a git worktree of "
    + REPO
    + " (detached at HEAD). Edit files here directly. NEVER git commit, never touch "
    + REPO
    + " itself, never run `uv`, never call a billed model or the network. FIRST run: [ -e .venv ] || ln -s "
    + REPO
    + """/.venv .venv ; run tests as `PYTHONPATH=$PWD:$PWD/packages/worldkeeper/src TMPDIR=/tmp .venv/bin/python -m pytest -q -p no:cacheprovider -n 0 <files>` (never pass --cov); ruff as `.venv/bin/python -m ruff check <files>` and `.venv/bin/python -m ruff format <files>` (line length 120, double quotes, Python 3.12, no new dependencies).

BACKGROUND. The default story (data/stories/continuity-initiative) is moving off its nine legacy files (plot.md, storylets.md, world.yaml, knowledge.yaml, storylet-routes.yaml, handoffs.yaml, incidents.yaml, pacing.yaml, connections.yaml) onto a committed source tree in data/stories/continuity-initiative/source/ that `storygame.story_source.compile_source_tree` compiles. `storygame.story_package.loader.load_story_package(root)` already compiles source/ instead of the legacy files when `<root>/ownership.yaml` exists with `schema: 1`, `catalog: compiled` and every scene (1A 1B 1C 2A 2B 2C 3A 3B 3C) set to `compiled` (read loader.py `_load_story_package_uncached` and tests/test_loader_source_dispatch.py first). About 49 existing tests build a modified copy of the story by copying the package directory and rewriting legacy file text; they will be migrated one by one to edit the source tree instead. They need one shared helper first. That is your job.

YOUR JOB: in tests/story_source/helpers.py (existing file; read all of it; keep every existing name and behaviour) add

    def compiled_story_copy(tmp_path: Path, story: str = "continuity-initiative") -> Path:

which copies ONLY `source/` from data/stories/<story> (resolved relative to the repo root via Path(__file__), not the working directory) into `<tmp_path>/<story>/source/`, writes `<tmp_path>/<story>/ownership.yaml` (`schema: 1`, `catalog: compiled`, `scenes:` mapping every scene id found in source/story.yaml's `scenes` list to `compiled`), and returns `<tmp_path>/<story>`. No legacy file is copied, so a test using this copy can only edit the source tree, and `load_story_package(returned_root)` returns the compiled package. Also add `def load_compiled_copy(root: Path)` returning `storygame.story_package.loader.load_story_package(root)` (import inside the function to avoid import cycles). Document both in one short docstring each, and add this sentence to the module docstring or a comment near patch_source: addresses are `key`, `key[<list id or index>]` joined with dots, files are paths relative to the root such as `scenes/1A.yaml`.

TESTS: tests/story_source/test_compiled_story_copy.py with a few fast tests: (a) the copy has source/ and ownership.yaml and none of plot.md, storylets.md, world.yaml, knowledge.yaml, storylet-routes.yaml, handoffs.yaml, incidents.yaml, pacing.yaml, connections.yaml; (b) the loaded copy's `model_dump()` equals the real default story's `model_dump()` loaded through load_story_package on data/stories/continuity-initiative once the legacy loader differences are reviewed: compare against `compile_source_tree(data/stories/continuity-initiative/source).model_dump()` instead, which must be exactly equal; (c) after `patch_source(root, "scenes/1A.yaml", <an address of a prose string you find in that file, e.g. the first reveal's text or a header field>, "PATCHED")` the loaded package contains the string "PATCHED" somewhere in its `model_dump()` JSON (use `json.dumps(..., default=str)`), proving edits reach the compiled package; (d) editing twice in two different tmp copies does not leak between them (cache key is the directory fingerprint).

HARD LIMITS. Never edit any other file, existing tests, tests/shard_durations.json, docs/, data/ or storygame/. If a test cannot pass without such an edit, write why in NOTES_r6c1.txt (worktree root, never committed) and leave it failing.
"""
)


def check() -> str:
    keep = " ".join(f"-e '^{p}$'" for p in OWNED)
    return f"""set -eo pipefail
[ -e .venv ] || ln -s {REPO}/.venv .venv
export PYTHONPATH=$PWD:$PWD/packages/worldkeeper/src TMPDIR=/tmp
out=$(mktemp)
rc=0
.venv/bin/python -m pytest -q -p no:cacheprovider -n 0 -rs tests/story_source/test_compiled_story_copy.py > "$out" 2>&1 || rc=$?
tail -30 "$out"
[ "$rc" -eq 0 ] || exit "$rc"
if grep -E "SKIPPED" "$out"; then echo "a gate test skips"; exit 1; fi
n=$(grep -cE "^def test_" tests/story_source/test_compiled_story_copy.py)
[ "$n" -ge 4 ] || {{ echo "expected at least 4 tests, found $n"; exit 1; }}
rc=0
.venv/bin/python -m pytest -q -p no:cacheprovider -n 4 tests/story_source > "$out" 2>&1 || rc=$?
tail -10 "$out"
[ "$rc" -eq 0 ] || exit "$rc"
.venv/bin/python -m ruff check tests/story_source/helpers.py tests/story_source/test_compiled_story_copy.py
.venv/bin/python -m ruff format --check tests/story_source/helpers.py tests/story_source/test_compiled_story_copy.py
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
            "engine_args": ["-c", "model_reasoning_effort=medium"],
            "max_attempts": 2,
            "timeout_s": 1800,
            "check_timeout_s": 900,
            "ownership": OWNED,
            "spec": SPEC,
            "check": check(),
            "expect_files": [],
            "verified": "compiled_story_copy and load_compiled_copy exist, tests prove the copy has no legacy files, compiles equal to the source tree, and source edits reach the package; tests/story_source green; ruff clean; only owned files changed.",
        }
    ],
}

if __name__ == "__main__":
    out = Path(__file__).with_name("round6c1-manifest.json")
    out.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    print(out)
