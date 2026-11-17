# ruff: noqa: E501  (spec strings are prose briefs for a worker)
"""Build the Ringer manifest for round 5c: compiler fixes so the converted default story compiles (1 task)."""

from __future__ import annotations

import json
from pathlib import Path

REPO = "/home/bcorfman/dev/freytag-forge"
WORK = "/home/bcorfman/dev/ringer-work/story-data-round5c"
KEY = "r5c-compile"

OWNED = [
    "storygame/story_source/c_world.py",
    "storygame/story_source/c_knowledge.py",
    "tests/story_source/test_f12_passage_rules.py",
    "storygame/story_source/convert.py",
    "storygame/story_source/convert_catalog.py",
    "storygame/story_source/convert_facts.py",
    "storygame/story_source/convert_reveals.py",
    "storygame/story_source/convert_scene.py",
    "tests/story_source/test_convert_catalog.py",
    "tests/story_source/test_convert_facts.py",
    "tests/story_source/test_convert_reveals.py",
    "tests/story_source/test_convert_scene.py",
    "tests/story_source/test_convert_tree.py",
]

SPEC = (
    "You are a Python engineer. Your current working directory IS a git worktree of "
    + REPO
    + " (detached at HEAD). Edit files here directly. NEVER git commit, never touch "
    + REPO
    + " itself, never run `uv`, never call a billed model or the network. FIRST run: [ -e .venv ] || ln -s "
    + REPO
    + """/.venv .venv ; run tests as `PYTHONPATH=$PWD:$PWD/packages/worldkeeper/src TMPDIR=/tmp .venv/bin/python -m pytest -q -p no:cacheprovider -n 0 <files>` (never pass --cov); ruff as `.venv/bin/python -m ruff check <files>` and `.venv/bin/python -m ruff format <files>` (line length 120, double quotes, Python 3.12, PyYAML and pydantic only, no new dependencies).

BACKGROUND. The game's story data is moving from nine legacy files per story to a declarative source tree that `storygame.story_source.compile_source_tree` compiles to the same `StoryPackage` (storygame/story_package/models.py). The format is fixed by the contract .plans/story-data-schema-contract.md (read it; never edit it); `.plans/story-data-1a-draft-edited.md` is a hand-written sample. `storygame/story_source/` holds the reader, validator (`check_source_tree`), compiler (`compile_source_tree`), parity checker (`parity.py`) and lookup; never edit those. Four converter pieces already exist, written in parallel and never run together: `convert_catalog.py` (`convert_story`, `convert_catalog`), `convert_facts.py` (`convert_facts`: `scene_docs` with `facts` and `placements`, plus `unplaced_facts`), `convert_reveals.py` (`convert_reveals`: `scene_docs` with `reveals`, plus `match_docs`) and `convert_scene.py` (`convert_scenes`: `scene_docs` with header, outline, beats, bridge, incidents, entry_claims, exit, ending, plus `match_docs`). Each takes the legacy-loaded `StoryPackage` (`from storygame.story_package.loader import load_story_package`, root `data/stories/continuity-initiative`) and returns plain dicts.

YOUR JOB: the converted default story (`write_source_tree` in `storygame/story_source/convert.py`, test `tests/story_source/test_convert_tree.py`) passes `check_source_tree` but `compile_source_tree` fails. Make it compile and make the compiled package carry every legacy id (the test in test_convert_tree.py already asserts this; it is your gate). Two compiler defects are already known, both in the pass 1 compiler written one round earlier, and you now OWN `storygame/story_source/c_world.py` and `c_knowledge.py` to fix them: (1) `build_connections` in c_world.py passes `Connection(id=identifier, **data)` while the record already carries `id` (the helper `_records` injects it), so every non-empty `connections` map fails with `multiple values for keyword argument 'id'`; the fixtures never had connections. (2) `_definition_matchers` in c_knowledge.py drops a claim's `must_convey` whenever the claim has `text_when`, but the legacy package keeps `must_convey` on claims with delivery variants and the inherited loader REQUIRES it for a selectable claim that establishes a scene-transition trigger (`k_sl_2c_d_r3`: "selectable knowledge ... establishes a scene-transition trigger but has no must_convey"). Compile whatever `must_convey` the match file gives, with or without `text_when`. Removing the suppression makes `tests/story_source/test_f12_passage_rules.py` fail; that test was written against the wrong assumption: read why it fails and fix the TEST (you own it) so it asserts the corrected behaviour and still checks first-say-wins, AMBIGUOUS and appended additions, and put one `# NOTE:` line at its top saying what changed and why. More compile errors may follow (they will name the next incompatibility, either another compiler defect in the files you own or a converter defect in the `convert_*.py` pieces, which you also own): keep compiling the converted package and fix the next one at its source until `test_convert_tree.py` passes with no skips. Never weaken an inherited loader check, never edit the output tree by hand, never drop legacy data to make it compile. The complete list of files you may edit is the ownership list in this manifest; everything else is read-only. If a defect truly needs another file, stop, write it in NOTES_r5c.txt with the exact error, and leave it failing.

TESTS: `tests/story_source/test_convert_tree.py` already exists (you own it; extend it only if needed). Do not weaken its assertions.

HARD LIMITS. Never edit existing tests, tests/shard_durations.json, docs/, the contract or any file in storygame/story_source/ that is not named above. If after real effort a defect needs a contract or compiler change, do NOT work around it: write it in NOTES_r5c.txt (worktree root, never committed) with the exact diagnostic and leave that diagnostic in place.
"""
)


def check() -> str:
    keep = " ".join(f"-e '^{p}$'" for p in OWNED)
    return f"""set -eo pipefail
[ -e .venv ] || ln -s {REPO}/.venv .venv
export PYTHONPATH=$PWD:$PWD/packages/worldkeeper/src TMPDIR=/tmp
out=$(mktemp)
rc=0
.venv/bin/python -m pytest -q -p no:cacheprovider -n 0 -rs tests/story_source/test_convert_tree.py > "$out" 2>&1 || rc=$?
tail -40 "$out"
[ "$rc" -eq 0 ] || exit "$rc"
if grep -E "SKIPPED" "$out"; then echo "a gate test skips"; exit 1; fi
rc=0
.venv/bin/python -m pytest -q -p no:cacheprovider -n 0 tests/story_source > "$out" 2>&1 || rc=$?
tail -15 "$out"
[ "$rc" -eq 0 ] || exit "$rc"
.venv/bin/python -m ruff check storygame/story_source tests/story_source
.venv/bin/python -m ruff format --check storygame/story_source tests/story_source
git add -A -- storygame tests
bad=$(git diff --cached --name-only | grep -v {keep} || true)
[ -z "$bad" ] || {{ echo "files outside ownership staged: $bad"; exit 1; }}
git diff --cached > {WORK}/{KEY}.patch
test -s {WORK}/{KEY}.patch
"""


manifest = {
    "run_name": "story-data-round5c",
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
            "verified": "the converted default story passes check_source_tree with no diagnostics and compiles; ids match the legacy package; deterministic; ruff clean; only owned files changed.",
        }
    ],
}

if __name__ == "__main__":
    out = Path(__file__).with_name("round5c-manifest.json")
    out.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    print(out)
