# ruff: noqa: E501  (spec strings are prose briefs for a worker)
"""Build the Ringer manifest for round 6c-2: migrate tests off the legacy continuity files (one task per test file).

Usage: build_round6c2_manifest.py <name> <tests/test_a.py> [<tests/test_b.py> ...]
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

REPO = "/home/bcorfman/dev/freytag-forge"

LEGACY = "plot.md, storylets.md, world.yaml, knowledge.yaml, storylet-routes.yaml, handoffs.yaml, incidents.yaml, pacing.yaml, connections.yaml"


def spec(test: str) -> str:
    return (
        "You are a Python test engineer. Your current working directory IS a git worktree of "
        + REPO
        + " (detached at HEAD). Edit files here directly. NEVER git commit, never touch "
        + REPO
        + " itself, never run `uv`, never call a billed model or the network. FIRST run: [ -e .venv ] || ln -s "
        + REPO
        + f"""/.venv .venv ; run tests as `PYTHONPATH=$PWD:$PWD/packages/worldkeeper/src TMPDIR=/tmp .venv/bin/python -m pytest -q -p no:cacheprovider -n 0 {test}` (never pass --cov); ruff as `.venv/bin/python -m ruff check {test}` and `.venv/bin/python -m ruff format {test}` (line length 120, double quotes, Python 3.12, no new dependencies).

BACKGROUND. The default story (data/stories/continuity-initiative) is being moved off its nine legacy files ({LEGACY}) onto a committed source tree, data/stories/continuity-initiative/source/ (story.yaml, catalog.yaml, scenes/<id>.yaml, scenes/<id>.match.yaml), compiled by `storygame.story_source.compile_source_tree`. Those legacy files WILL BE DELETED in a later round, so no test may read or write them any more. `storygame.story_package.loader.load_story_package(root)` already compiles source/ when `<root>/ownership.yaml` marks everything compiled. The loaded `StoryPackage` (storygame/story_package/models.py) holds everything the legacy files held, in typed form.

Read first: tests/story_source/helpers.py (`compiled_story_copy(tmp_path)` copies only source/ plus ownership.yaml, no legacy files; `load_compiled_copy(root)`; `patch_source(root, "scenes/1A.yaml", "address.with.key[id_or_index]", value)` edits one YAML value), tests/test_loader_source_dispatch.py (an example), and `.plans/story-data-schema-contract.md` sections 3 and 4 (where each legacy field lives in the source tree: claims, reveals and variants, facts, placements, beats, pacing, incidents, connections; and the compiled-field mapping tables). You can list ids and locate fields with `PYTHONPATH=$PWD python -m storygame.story_cli show <kind>:<id>` and by reading the scene files in source/.

YOUR JOB: migrate ONLY {test} so it passes without ever touching a legacy file, keeping what the test PROVES unchanged:
- A test that copies the package directory and rewrites a legacy file (text replace or yaml load/dump) must build its copy with `compiled_story_copy(tmp_path)`, apply the same change to the matching source file with `patch_source` (or by loading and dumping that YAML with the same DuplicateKeyLoader-free approach if the change adds a whole record), and load with `load_story_package(copy)`. The change must be the same change in meaning: same fact, claim, text or condition, found by record id.
- A test that reads a legacy file directly (yaml.safe_load of knowledge.yaml / world.yaml / pacing.yaml / storylet-routes.yaml, or read_text of plot.md / storylets.md) must read the loaded package instead (`load_story_package(Path("data/stories/continuity-initiative"))`, fields such as `package.knowledge`, `package.world`, `package.pacing`, `package.routes`, `package.scenes`), or the source tree under data/stories/continuity-initiative/source/ when the test is about authored text that the package does not keep.
- Assertions keep their meaning. If an expected loader error message or a value differs because the source compiler words it differently or orders it differently, change the expectation to the compiler's actual text ONLY when the meaning is identical, and list every such change in NOTES_<key>.txt (worktree root, never committed). If the meaning cannot be preserved, do not weaken the test: write why in NOTES_<key>.txt and leave the test failing.
- Never mark a test skip/xfail, never delete a test, never loosen an assertion, and never add new tests.
- The test file must contain none of these strings when you are done: {LEGACY}, and no `shutil.copytree` of the legacy package root (copying source/ via the helper is fine).

HARD LIMITS. Edit only {test}. Never edit other tests, tests/shard_durations.json, tests/conftest.py, docs/, data/ or storygame/. Other tests in the repo are being migrated in parallel by other workers.
"""
    )


def check(test: str, key: str, work: str) -> str:
    legacy_pattern = "plot\\.md|storylets\\.md|world\\.yaml|knowledge\\.yaml|storylet-routes|handoffs\\.yaml|incidents\\.yaml|pacing\\.yaml|connections\\.yaml"
    return f"""set -eo pipefail
[ -e .venv ] || ln -s {REPO}/.venv .venv
export PYTHONPATH=$PWD:$PWD/packages/worldkeeper/src TMPDIR=/tmp
out=$(mktemp)
rc=0
.venv/bin/python -m pytest -q -p no:cacheprovider -n 0 -rs {test} > "$out" 2>&1 || rc=$?
tail -25 "$out"
[ "$rc" -eq 0 ] || exit "$rc"
if grep -E "SKIPPED|XFAIL|xfailed" "$out"; then echo "a test skips or xfails"; exit 1; fi
if grep -nE "{legacy_pattern}" {test}; then echo "the test still names a legacy file"; exit 1; fi
before=$(git show HEAD:{test} | grep -cE "^\\s*(async )?def test_" || true)
after=$(grep -cE "^\\s*(async )?def test_" {test} || true)
[ "$after" -ge "$before" ] || {{ echo "tests removed: $before -> $after"; exit 1; }}
.venv/bin/python -m ruff check {test}
.venv/bin/python -m ruff format --check {test}
git add -A -- storygame tests data
bad=$(git diff --cached --name-only | grep -v -x -e '{test}' || true)
[ -z "$bad" ] || {{ echo "files outside ownership staged: $bad"; exit 1; }}
git diff --cached > {work}/{key}.patch
test -s {work}/{key}.patch
"""


def build(name: str, tests: list[str]) -> dict:
    work = f"/home/bcorfman/dev/ringer-work/story-data-round6c2-{name}"
    tasks = []
    for test in tests:
        key = "m-" + Path(test).stem.removeprefix("test_")
        tasks.append(
            {
                "key": key,
                "task_type": "code-fix",
                "engine": "codex",
                "engine_args": ["-c", "model_reasoning_effort=medium"],
                "max_attempts": 2,
                "timeout_s": 2400,
                "check_timeout_s": 900,
                "ownership": [test],
                "spec": spec(test).replace("<key>", key),
                "check": check(test, key, work),
                "expect_files": [],
                "verified": f"{test} passes without naming any legacy continuity file, with no test removed, skipped or loosened; only that file changed; ruff clean.",
            }
        )
    return {
        "run_name": "story-data-round6-tests",
        "workdir": work,
        "max_parallel": 3,
        "worktrees": True,
        "repo": REPO,
        "tasks": tasks,
    }


if __name__ == "__main__":
    name, *tests = sys.argv[1:]
    out = Path(__file__).with_name(f"round6c2-{name}-manifest.json")
    out.write_text(json.dumps(build(name, tests), indent=2) + "\n", encoding="utf-8")
    print(out)
