# ruff: noqa: E501  (spec strings are prose briefs for a worker)
"""Build the Ringer manifest for round 6h: port the four readers that still read the nine legacy story files (3 parallel tasks)."""

from __future__ import annotations

import json
from pathlib import Path

REPO = "/home/bcorfman/dev/freytag-forge"
WORK = "/home/bcorfman/dev/ringer-work/story-data-round6h"

COMMON = (
    "You are a Python engineer. Your current working directory IS a git worktree of "
    + REPO
    + " (detached at HEAD). Edit files here directly. NEVER git commit, never touch "
    + REPO
    + " itself, never run `uv`, never call a billed model or the network. FIRST run: [ -e .venv ] || ln -s "
    + REPO
    + """/.venv .venv ; run tests as `PYTHONPATH=$PWD:$PWD/packages/worldkeeper/src TMPDIR=/tmp .venv/bin/python -m pytest -q -p no:cacheprovider -n 0 <files>` (never pass --cov); ruff as `.venv/bin/python -m ruff check <files>` and `.venv/bin/python -m ruff format <files>` (line length 120, double quotes, Python 3.12).

BACKGROUND. The default story (data/stories/continuity-initiative/) moved from nine legacy files (plot.md, world.yaml, knowledge.yaml, pacing.yaml, storylets.md, storylet-routes.yaml, ...) to a source tree under source/ (catalog.yaml, story.yaml, scenes/<id>.yaml, scenes/<id>.match.yaml) compiled by `storygame.story_source.compile_source_tree`; `storygame.story_package.loader.load_story_package(root)` loads either form. Today both exist in the data dir; SOON the nine legacy files will be deleted and `ownership.yaml` added, and then any reader that opens a legacy file by name breaks. Your job is to port the reader named below so it works from a story root that has ONLY `ownership.yaml` + `source/` AND still works unchanged for roots that have the legacy files (fixture stories under tests/fixtures/stories/ stay legacy forever). To simulate the flipped story in tests use `tests/story_source/helpers.py::compiled_story_copy(tmp_path)` (copies source/ and writes ownership.yaml, no legacy files) and `load_compiled_copy`. The format is described by .plans/story-data-schema-contract.md (read only; never edit it). Prefer reading the already loaded `StoryPackage` (storygame/story_package/models.py: `.scenes[].prose`, `.knowledge`, `.pacing`, `.world`, `.storylets`, `.storylet_routes`, `.deliveries`) over re-reading files. World-only logic belongs in packages/worldkeeper; you are not changing that.

HARD LIMITS. Edit ONLY the files in your ownership list. Never edit docs/, data/, the contract, tests/shard_durations.json, or any other test. Never delete or skip a test and never weaken an assertion. Existing behaviour for legacy roots must be unchanged (their tests keep passing).
"""
)

TASKS = {
    "r6h-audit": {
        "owned": ["storygame/audit.py", "tests/test_package_audit.py"],
        "task_type": "code-feature",
        "spec": COMMON
        + """
YOUR READER: storygame/audit.py `audit_package(root)` reads plot.md, knowledge.yaml, world.yaml, pacing.yaml, storylet-routes.yaml and storylets.md straight from disk and runs lexical checks (owned-thing mentions, unattested details against the plot text, source links, ...). Make `audit_package` accept a compiled root (no plot.md, but `ownership.yaml` + `source/`): load the package with `load_story_package` and build the same inputs the legacy path parses. `Scene.prose` is the plot scene body (its first line should be the scene heading; check what the converter keeps, see storygame/story_source/convert_scene.py and c_scene.py, and rebuild the "## Scene 1A <title>" heading blocks so `_plot_scenes` and `_scene_item_ids` etc. work, or refactor those helpers to take the package). Legacy roots keep their old path byte for byte.

THE KEY REQUIREMENT, which the check enforces: while the legacy files still exist, `audit_package(Path("data/stories/continuity-initiative"))` (legacy path) and `audit_package(compiled_story_copy(tmp)/...)` (compiled path) must return EQUAL reports (the same dict). If a difference is a faithful consequence of the source format (for example the source-link check reading `plot.md#anchor` links that the compiled route keeps as notes or renders another way), keep the findings equal by deriving the same inputs; if you truly cannot, write the exact difference and why in NOTES_r6h-audit.txt (worktree root) and make the compiled report differ only there. Port tests/test_package_audit.py so the two tests that audit the continuity story run on `compiled_story_copy` (keep every assertion; where one counts or names findings it must give the same answer). Add one new test asserting legacy-vs-compiled report equality on the default story (it reads the real data dir, which still has the legacy files today; mark nothing as skip).
""",
        "tests": ["tests/test_package_audit.py", "tests/test_audit_unbound_item.py", "tests/test_audit_budget.py"],
        "extra": """
cat > /tmp/r6h_equal_$$.py <<'PY'
import sys, tempfile
from pathlib import Path
sys.path.insert(0, ".")
from storygame.audit import audit_package
from tests.story_source.helpers import compiled_story_copy
legacy = audit_package(Path("data/stories/continuity-initiative"))
with tempfile.TemporaryDirectory() as tmp:
    compiled = audit_package(compiled_story_copy(Path(tmp)))
if legacy != compiled:
    import json
    a, b = json.dumps(legacy, indent=1, sort_keys=True).splitlines(), json.dumps(compiled, indent=1, sort_keys=True).splitlines()
    import difflib
    print("\\n".join(list(difflib.unified_diff(a, b, "legacy", "compiled", lineterm=""))[:60]))
    sys.exit("audit reports differ between the legacy and compiled routes")
print("audit reports equal")
PY
.venv/bin/python /tmp/r6h_equal_$$.py
""",
    },
    "r6h-bench-readers": {
        "owned": [
            "bench/checks/penalty_rubric.py",
            "scripts/generate_spine_expected_reveals.py",
            "tests/test_penalty_rubric.py",
            "tests/test_spine_expected_reveals.py",
        ],
        "task_type": "code-fix",
        "spec": COMMON
        + """
YOUR READERS: (1) bench/checks/penalty_rubric.py `load_gap_lines` opens `data/stories/continuity-initiative/pacing.yaml` and reads the four evidence-gap realizations; (2) scripts/generate_spine_expected_reveals.py `knowledge_items()` opens `knowledge.yaml` and indexes claims by id. Port both to read from `load_story_package(<story root>)` (pacing events / realizations and `package.knowledge` respectively), keeping their outputs identical to today's: capture today's outputs FIRST (run the functions on the unmodified tree, save to a scratch file outside the repo) and compare after. Keep the `path` / root parameters working. Update tests/test_penalty_rubric.py and tests/test_spine_expected_reveals.py only as needed so they do not read legacy files (use compiled_story_copy where they need a story root); do not weaken assertions. Both modules must contain no reference to the legacy file names `pacing.yaml` / `knowledge.yaml` as files they open when done (comments naming history are fine, but the check greps for `open`, `read_text` and `Path(...)/ "<name>"` forms).
""",
        "tests": ["tests/test_penalty_rubric.py", "tests/test_spine_expected_reveals.py", "tests/test_evidence_penalty.py"],
        "extra": """
if grep -nE '(/|")(pacing|knowledge)\\.yaml"' bench/checks/penalty_rubric.py scripts/generate_spine_expected_reveals.py; then echo "legacy file still opened"; exit 1; fi
""",
    },
    "r6h-impact-report": {
        "owned": ["storygame/story_package/impact_report.py", "tests/test_impact_report.py"],
        "task_type": "code-fix",
        "spec": COMMON
        + """
YOUR READER: storygame/story_package/impact_report.py has a table (around line 48) mapping record kinds ('fact', 'claim', 'pacing event', 'transition', 'canonical route event', 'storylet realization', 'guard', ...) to the legacy file that holds them (knowledge.yaml, pacing.yaml, storylet-routes.yaml, world.yaml). For a story root that has `source/` and `ownership.yaml` compiled, the report must name the real source file instead: for a record that belongs to a scene, `source/scenes/<SCENE>.yaml` (or `.match.yaml` for matcher lists if the report lists matchers), for world things `source/catalog.yaml`, story-level pieces `source/story.yaml`; decide each kind by reading the contract (.plans/story-data-schema-contract.md section 2 and 4) and the converter (storygame/story_source/convert_*.py) which says where each legacy record landed. Legacy roots keep the legacy names. Read how the report is built from the package and how it finds the root; do not rewrite its logic. Update tests/test_impact_report.py to cover the compiled root via `compiled_story_copy` (keep every existing assertion) with at least two new assertions that the file names are source-tree paths and that no legacy name appears for a compiled root.
""",
        "tests": ["tests/test_impact_report.py"],
        "extra": "",
    },
}


def check(key: str, item: dict) -> str:
    owned = item["owned"]
    keep = " ".join(f"-e '^{p}$'" for p in owned)
    tests = " ".join(item["tests"])
    py = " ".join(p for p in owned if p.endswith(".py"))
    return f"""set -eo pipefail
[ -e .venv ] || ln -s {REPO}/.venv .venv
export PYTHONPATH=$PWD:$PWD/packages/worldkeeper/src TMPDIR=/tmp
out=$(mktemp)
rc=0
.venv/bin/python -m pytest -q -p no:cacheprovider -n 0 -rs {tests} > "$out" 2>&1 || rc=$?
tail -30 "$out"
[ "$rc" -eq 0 ] || exit "$rc"
if grep -E "SKIPPED" "$out"; then echo "a test skips"; exit 1; fi
if git diff -U0 -- tests | grep -E "^\\+.*(pytest\\.(skip|xfail)|raises\\(Exception)"; then echo "forbidden skip/xfail"; exit 1; fi
{item["extra"]}
rc=0
.venv/bin/python -m pytest -q -p no:cacheprovider -n 4 tests/story_source tests/test_loader_source_dispatch.py > "$out" 2>&1 || rc=$?
tail -5 "$out"
[ "$rc" -eq 0 ] || exit "$rc"
.venv/bin/python -m ruff check {py}
.venv/bin/python -m ruff format --check {py}
git add -A -- storygame tests data bench scripts
bad=$(git diff --cached --name-only | grep -v {keep} || true)
[ -z "$bad" ] || {{ echo "files outside ownership staged: $bad"; exit 1; }}
git diff --cached > {WORK}/{key}.patch
test -s {WORK}/{key}.patch
[ ! -e NOTES_{key}.txt ] || cp NOTES_{key}.txt {WORK}/NOTES_{key}.txt
"""


def build() -> dict:
    tasks = []
    for key, item in TASKS.items():
        tasks.append(
            {
                "key": key,
                "task_type": item["task_type"],
                "engine": "codex",
                "engine_args": ["-c", "model_reasoning_effort=high"],
                "max_attempts": 2,
                "timeout_s": 3600,
                "check_timeout_s": 1200,
                "ownership": item["owned"],
                "spec": item["spec"],
                "check": check(key, item),
                "expect_files": [],
                "verified": "reader works from a compiled root with no legacy files and unchanged on legacy roots; its tests pass; tests/story_source green; ruff clean; only owned files changed.",
            }
        )
    return {
        "run_name": "story-data-round6-checks",
        "workdir": WORK,
        "max_parallel": 3,
        "worktrees": True,
        "repo": REPO,
        "tasks": tasks,
    }


if __name__ == "__main__":
    out = Path(__file__).with_name("round6h-manifest.json")
    out.write_text(json.dumps(build(), indent=2) + "\n", encoding="utf-8")
    print(out)
