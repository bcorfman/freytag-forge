# ruff: noqa: E501  (spec strings are prose briefs for a worker)
"""Build the Ringer manifest for round 5e: the contract's known parity review entry and the derived knowledge-index rule (1 task)."""

from __future__ import annotations

import json
from pathlib import Path

REPO = "/home/bcorfman/dev/freytag-forge"
WORK = "/home/bcorfman/dev/ringer-work/story-data-round5e"
KEY = "r5e-review"

OWNED = [
    "storygame/story_source/parity.py",
    "tests/story_source/test_parity_core.py",
    "tests/story_source/test_parity_indexes.py",
    "tests/fixtures/parity/continuity-initiative/world.reviewed.yaml",
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

YOUR JOB: make `tests/story_source/test_parity_default.py` pass (you do NOT own it; never edit it). Read it first: it converts the legacy default story, compiles it, and runs `storygame.story_source.parity.check_parity` with the entries of every `tests/fixtures/parity/continuity-initiative/*.reviewed.yaml` file, and requires `summary["pass"]`. Read section 9 of `.plans/story-data-schema-contract.md` (parity spec, difference classes, review file format) and section 5 rows 1 and 5. Two differences remain, both anticipated by that contract:
(A) `world.facts`: legacy lists `processing_numbers_copied` twice (178 entries) and in a different order than the compiled 177 distinct facts. The contract lists this as a known review entry (class `dedupe`, plus one inverted order pair). Create `tests/fixtures/parity/continuity-initiative/world.reviewed.yaml` (schema 1, `scene` set to whatever scene string the report gives these entries, the differences list in the section 9 format) with ONE entry for path `world.facts`, whose class and both 12-hex digests are exactly what `check_parity` reports (compute them by running it; the digests are the `legacy` and `compiled` fields of the report entries), and a real `reason` saying: legacy has the duplicate id `processing_numbers_copied` and a different order; the compiled list is the 177 distinct ids in story order; the contract section 5 row 5 checked that fact order only matters for on-assert effects on one entity, and the single inverted pair is relay_open vs brandon_identified, accepted as a review entry. Verify that claim yourself before writing it: load both packages, confirm the sets are equal except for the duplicate, and list the pairs of facts whose on-assert effects touch the same entity whose relative order differs between legacy and compiled; put the exact pairs you found in the reason. If you find more than the one pair the contract names, do NOT review it: write the pairs in NOTES_r5e.txt and leave the difference failing.
(B) `knowledge_indexes`: the legacy and compiled indexes differ only because three claims (`k_sl_1a_b_r1`, `k_sl_2b_b_r4`, `k_sl_2b_b_r5`) list the same `establishes` assert operations in a different order, and that order change is already classified `op_order` on `knowledge[...].establishes` (reviewed automatically, no entry needed). Section 9 says a `knowledge_indexes` difference with NO upstream difference is a compiler bug and never reviewable, and the current checker fails the whole parity whenever the indexes differ at all. Change `parity.py` so that a `knowledge_indexes` difference that is fully explained by upstream `op_order` differences does not count: compare the indexes after putting each `establishes` operation list (inside the indexes) into a canonical order ONLY where the same `_operation_order_proof` that classifies `op_order` elsewhere holds for that list; if the canonicalized indexes are equal there is no `knowledge_indexes` difference and `knowledge_changed` stays false; if they still differ, report `knowledge_indexes` exactly as today (representation, never reviewable, summary fails). Write `tests/story_source/test_parity_indexes.py` with small synthetic package dumps (follow the style of `test_parity_core.py`) proving: (1) indexes that differ only by a provable operation reorder pass; (2) indexes that differ by a different fact set, a different asserted value, or a reorder where two facts affect one entity still fail and cannot be reviewed; (3) the existing behaviours in test_parity_core.py and test_f23_parity_classes.py are unchanged (run them).
Do not edit the compiler, converter, validator, legacy story data, the gate test or the contract; do not review any path other than `world.facts`; never make the checker ignore a difference it reports today other than the one case in (B).

TESTS: all of tests/story_source must pass; do not add tests beyond test_parity_indexes.py.

HARD LIMITS. Never edit existing tests, tests/shard_durations.json, docs/, the contract or any file in storygame/story_source/ that is not named above. If after real effort a defect needs a contract or compiler change, do NOT work around it: write it in NOTES_r5e.txt (worktree root, never committed) with the exact diagnostic and leave that diagnostic in place.
"""
)


def check() -> str:
    keep = " ".join(f"-e '^{p}$'" for p in OWNED)
    return f"""set -eo pipefail
[ -e .venv ] || ln -s {REPO}/.venv .venv
export PYTHONPATH=$PWD:$PWD/packages/worldkeeper/src TMPDIR=/tmp
out=$(mktemp)
rc=0
.venv/bin/python -m pytest -q -p no:cacheprovider -n 0 -rs tests/story_source/test_parity_default.py > "$out" 2>&1 || rc=$?
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
    "run_name": "story-data-round5e",
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
            "verified": "the converted default story passes parity with only the contract's world.facts review entry; knowledge_indexes differences explained by op_order no longer fail; tests/story_source green; ruff clean; only owned files changed.",
        }
    ],
}

if __name__ == "__main__":
    out = Path(__file__).with_name("round5e-manifest.json")
    out.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    print(out)
