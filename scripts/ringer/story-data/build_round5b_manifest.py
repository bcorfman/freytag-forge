# ruff: noqa: E501  (spec strings are prose briefs for a worker)
"""Build the Ringer manifest for round 5b: the converter assembler and the first valid pilot tree (1 task)."""

from __future__ import annotations

import json
from pathlib import Path

REPO = "/home/bcorfman/dev/freytag-forge"
WORK = "/home/bcorfman/dev/ringer-work/story-data-round5b"
KEY = "r5b-assemble"

OWNED = [
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

YOUR JOB: (1) write the assembler `storygame/story_source/convert.py` with `convert_package(package) -> dict[str, dict]` (a map from relative path, such as `story.yaml`, `catalog.yaml`, `scenes/1A.yaml`, `scenes/1A.match.yaml`, to a document; every document starts with `schema: 1` and uses the contract's key order) and `write_source_tree(package, root: Path) -> None` (writes those documents as YAML with `yaml.safe_dump(sort_keys=False, allow_unicode=True, width=1000)`; deterministic; no timestamps). Merge the pieces' scene docs (their keys are meant to be disjoint; raise if they collide) and merge the match docs from `convert_reveals` and `convert_scene` into one `scenes/<id>.match.yaml` per scene. (2) Make the whole converted tree valid: `check_source_tree(root)` must return no diagnostics and `compile_source_tree(root)` must succeed (which also runs every loader check). You OWN `convert.py`, the four `convert_*.py` pieces and their four `tests/story_source/test_convert_*.py` files, and may edit them freely to make the pieces agree; you may not edit anything else.

KNOWN DEFECTS from a first throwaway assembly (412 diagnostics), to fix in the pieces, not papered over: (a) reveal handles and variant keys must match `^[a-z][a-z0-9_]*$`: the reveals piece used the legacy ids (`SL-1A-A`, `SL-1A-A-R1`) as handles; derive the handle from the storylet id (lowercase, hyphens to underscores, for example `sl_1a_a`) and the variant key from the realization id with the reveal prefix removed (for example `r1`), while `storylet_id`, `realization_id` and `claim_id` keep the legacy ids exactly; the handle must stay unique story-wide. (b) `from_outline` values must be outline beat ids as the scene piece writes them (`1A.1`), not anchors: map each anchor to its beat id; every reveal needs at least one and a variant with none must omit the key (contract 4.8). (c) every document needs `schema: 1`. (d) the scene piece emitted `outline`, so its ids and the reveals' `from_outline` must agree; if the package gives no beat id for a link, say so in NOTES_r5b.txt. (e) incident `observed_by` and `observation_knowledge_ids` reference claims (`k_sl_1c_b_r1`, `k_sl_1c_c_copy_numbers`) that do not resolve or are not observed: find out whether the claims were skipped by the reveals piece or the incident piece builds the wrong list, and fix it at the source. (f) `L2.match_coverage`: a match entry `k_sl_2a_c_r5` has no scene claim, and others: find the claim kinds the reveals piece skipped (the scene piece owns entry, bridge, ending and incident claims; `extra_claims` belong to the reveals piece) and make exactly one piece own every claim. More defects will show once these are fixed: keep running `check_source_tree` and `compile_source_tree` on the converted package and fix the next defect until both are clean. Fix defects in the pieces (the package-reading code), never by editing the output after the fact and never by weakening a validator. Compilation must reproduce the legacy records; you are NOT asked to reach parity yet, but where a field is clearly lost (a claim or realization that disappears from the compiled package) fix it now.

TESTS: add `tests/story_source/test_convert_tree.py` with: the converted tree of the default story has an empty `check_source_tree`; `compile_source_tree` succeeds; the compiled package has the same scene ids, claim ids, storylet ids, realization ids, delivery fact ids, pacing event ids, incident ids and fact ids as the legacy package (as sets, with the differing ids printed in the assertion message); conversion is deterministic (two runs, byte-identical files). Use `tmp_path` for output.

HARD LIMITS. Never edit existing tests, tests/shard_durations.json, docs/, the contract or any file in storygame/story_source/ that is not named above. If after real effort a defect needs a contract or compiler change, do NOT work around it: write it in NOTES_r5b.txt (worktree root, never committed) with the exact diagnostic and leave that diagnostic in place.
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
    "run_name": "story-data-round5b",
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
    out = Path(__file__).with_name("round5b-manifest.json")
    out.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    print(out)
