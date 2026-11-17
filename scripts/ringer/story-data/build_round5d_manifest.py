# ruff: noqa: E501  (spec strings are prose briefs for a worker)
"""Build the Ringer manifest for round 5d: converter and compiler fixes until the converted default story has parity (1 task)."""

from __future__ import annotations

import json
from pathlib import Path

REPO = "/home/bcorfman/dev/freytag-forge"
WORK = "/home/bcorfman/dev/ringer-work/story-data-round5d"
KEY = "r5d-parity"

OWNED = [
    "storygame/story_source/compiler.py",
    "storygame/story_source/c_world.py",
    "storygame/story_source/c_knowledge.py",
    "storygame/story_source/c_scene.py",
    "storygame/story_source/c_passages.py",
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

BACKGROUND. The game's story data is moving from nine legacy files per story to a declarative source tree that `storygame.story_source.compile_source_tree` compiles to the same `StoryPackage` (storygame/story_package/models.py). The format is fixed by the contract .plans/story-data-schema-contract.md (read it; never edit it); `.plans/story-data-1a-draft-edited.md` is a hand-written sample. `storygame/story_source/` holds the reader, validator (`check_source_tree`), compiler (`compile_source_tree`), parity checker (`parity.py`) and lookup; never edit those except the files named in the ownership list. Four converter pieces already exist, written in parallel and never run together: `convert_catalog.py` (`convert_story`, `convert_catalog`), `convert_facts.py` (`convert_facts`: `scene_docs` with `facts` and `placements`, plus `unplaced_facts`), `convert_reveals.py` (`convert_reveals`: `scene_docs` with `reveals`, plus `match_docs`) and `convert_scene.py` (`convert_scenes`: `scene_docs` with header, outline, beats, bridge, incidents, entry_claims, exit, ending, plus `match_docs`). Each takes the legacy-loaded `StoryPackage` (`from storygame.story_package.loader import load_story_package`, root `data/stories/continuity-initiative`) and returns plain dicts.

YOUR JOB: make `tests/story_source/test_parity_default.py` pass (you do NOT own it; never edit it). It writes the converted default story with `write_source_tree`, compiles it, and runs `storygame.story_source.parity.check_parity(legacy, compiled)` with no review file; it needs `summary["unreviewed"] == 0`. Today it reports 103 open differences, from six causes. In each report entry `legacy` and `compiled` are only digests, so to see real values load both packages and compare `package.model_dump(mode="json")` yourself (`load_story_package(Path("data/stories/continuity-initiative"))` against `compile_source_tree(<tree>)`), reading `parity.py` for the path syntax. The compiled package must equal the legacy one: fix the converter or compiler so the compiled value reproduces the legacy value; never edit parity.py, never add review files, never drop or rewrite legacy data. The six causes seen so far, in order of likely size:
(1) storylet ids in `storylet_routes.bridge_events[*].realization_storylets` and `resolution_events`: legacy `SL-1A-B`, compiled `sl_1a_b` (a lowercased, underscored form leaked into the compiled package; the legacy id must survive the round trip, the contract says how storylet ids are carried).
(2) `source_beats` on about 60 realizations: legacy holds slugs such as `scene-1a1--michelle-is-gone`, compiled holds `1A.1`.
(3) `SL-1A-A-R1.operations`: the compiled operations hold two extra asserts (`processing_numbers_copied`, `service_level_access_known`) that the legacy realization does not have.
(4) `scenes.<id>.prose` for all nine scenes: legacy is the plot.md scene text (starting `**Setting:**`), compiled is assembled from the beat outline (starting `### Scene 1A.1`). Check how the contract carries scene prose and make the converter write it so the compiled value is identical.
(5) `world.fact_effects[...]` (18 entries, e.g. `alarm_log_read`): legacy is an empty list, compiled is null. Also `world.facts` (a dedupe difference), `incidents.i_1c_freight_transfer.observation_knowledge_ids`, and the derived `knowledge_indexes` digest: the last one should follow once the others are fixed.
(6) Anything the six above uncover once they are fixed. Re-run the gate after each fix and fix the next remaining difference at its source.
Fix causes at the converter when the legacy value is simply not carried into the tree, and at the compiler when the tree carries it and the compiler drops or rewrites it. If a legacy value truly has no home in the contract (the contract is fixed), do NOT work around it: write the exact path and legacy value in NOTES_r5d.txt (worktree root, never committed) and leave that difference failing.

TESTS: existing tests in tests/story_source (about 150) must keep passing. If a converter test you own asserts the old, wrong output, fix the test to assert the corrected output and put one `# NOTE:` line at its top saying what changed and why; never weaken a test whose expectation was right. Do not add tests beyond what a changed behaviour needs.

HARD LIMITS. Never edit existing tests, tests/shard_durations.json, docs/, the contract or any file in storygame/story_source/ that is not named above. If after real effort a defect needs a contract or compiler change, do NOT work around it: write it in NOTES_r5d.txt (worktree root, never committed) with the exact diagnostic and leave that diagnostic in place.
"""
)


def check() -> str:
    keep = " ".join(f"-e '^{p}$'" for p in OWNED)
    return f"""set -eo pipefail
[ -e .venv ] || ln -s {REPO}/.venv .venv
export PYTHONPATH=$PWD:$PWD/packages/worldkeeper/src TMPDIR=/tmp
out=$(mktemp)
rc=0
.venv/bin/python -m pytest -q -p no:cacheprovider -n 0 -rs tests/story_source/test_parity_default.py tests/story_source/test_convert_tree.py > "$out" 2>&1 || rc=$?
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
    "run_name": "story-data-round5d",
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
            "verified": "the compiled converted default story has 0 unreviewed parity differences against the legacy package; test_convert_tree still passes; tests/story_source green; ruff clean; only owned files changed.",
        }
    ],
}

if __name__ == "__main__":
    out = Path(__file__).with_name("round5d-manifest.json")
    out.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    print(out)
