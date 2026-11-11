"""Build the Ringer manifest that removes the hard-coded absolute story path from two scripts."""

import json
from pathlib import Path

REPO = "/home/bcorfman/dev/freytag-forge"
GAPS = f"{REPO}/scripts/gap_rules.py"
TRACE = f"{REPO}/scripts/situation_trace.py"
GUARD = f"{REPO}/tests/test_story_review_scripts.py"
REF = f"{REPO}/scripts/impact_report.py"
GTEST = f"{REPO}/tests/test_gap_rules.py"
TTEST = f"{REPO}/tests/test_situation_trace.py"
ENV = f"export TMPDIR=/tmp PYTHONPATH={REPO}:{REPO}/packages/worldkeeper/src"
PY = f"{REPO}/.venv/bin/python"

SPEC = f"""You are an implementation worker for the freytag-forge repository at {REPO}. Boundary: NO model call, NO network call, never git commit, never uv or bare python, never --cov. You own ONLY {GAPS}, {TRACE} and {GUARD} (new). Touch nothing else.

PROBLEM. CI failed because {GAPS} and {TRACE} default their `--root` to an absolute path on one developer's machine (`/home/bcorfman/dev/freytag-forge/data/stories/...`). {GAPS} even builds the story folder name from character codes. On the CI runner that path does not exist, so `main([...])` returns 2 and `tests/test_gap_rules.py::test_script_main_returns_zero_with_flags_and_two_for_unknown_anchor` fails.

FIX. Make both scripts derive the default root from the script's own location, exactly as {REF} does: `_STORIES = Path(__file__).resolve().parents[1] / "data" / "stories"` and `DEFAULT_ROOT = next(path for path in sorted(_STORIES.iterdir()) if path.is_dir())`. Remove the character-code name construction and any story name from {GAPS} and {TRACE}. Change nothing else in them (argument parsing, exit codes and output stay exactly as they are).

GUARD TEST in {GUARD}: for each of scripts/gap_rules.py, scripts/situation_trace.py, scripts/impact_report.py and scripts/branch_report.py, import the module by path (importlib.util.spec_from_file_location, so no packaging is needed), assert its `DEFAULT_ROOT` is an existing directory that lies under the repository root computed from the test file's own location (`Path(__file__).resolve().parents[1]`), and assert the script's source text contains no `/home/` substring. A fifth assertion: running each script's `main` with an unknown anchor and its default root returns 2 (not an exception). Keep it hermetic and fast. Existing tests {GTEST} and {TTEST} must still pass.

HOW TO RUN (from {REPO}): `{ENV} && {PY} -m pytest {GUARD} {GTEST} {TTEST} -q --no-cov -p no:cacheprovider 2>&1 | tail -15`. Format and lint: `{PY} -m ruff format {GAPS} {TRACE} {GUARD} && {PY} -m ruff check {GAPS} {TRACE} {GUARD}` (if ruff format cannot write because the filesystem is read-only, run `ruff format --check` and say so)."""

CHECK = f"""set -o pipefail
cd {REPO}
{ENV}
PY={PY}
$PY -m ruff check {GAPS} {TRACE} {GUARD}
$PY -m ruff format --check {GAPS} {TRACE} {GUARD}
if grep -n '/home/' {GAPS} {TRACE}; then echo 'ABSOLUTE PATH STILL PRESENT'; exit 1; fi
$PY -m pytest {GUARD} {GTEST} {TTEST} -q --no-cov -p no:cacheprovider 2>&1 | tail -12
# prove the fix works from a different checkout location
TMP=$(mktemp -d)
mkdir -p $TMP/scripts $TMP/data
cp {REPO}/scripts/*.py $TMP/scripts/
cp -r {REPO}/data/stories $TMP/data/stories
ln -s {REPO}/storygame $TMP/storygame
ln -s {REPO}/packages $TMP/packages
cd $TMP
for s in gap_rules situation_trace; do
  PYTHONPATH=$TMP:$TMP/packages/worldkeeper/src $PY scripts/$s.py officer_presses_1a > $TMP/out.txt || {{ cat $TMP/out.txt; exit 1; }}; head -3 $TMP/out.txt
done
PYTHONPATH=$TMP:$TMP/packages/worldkeeper/src $PY scripts/gap_rules.py no_such_anchor; test $? -eq 2 || {{ echo "expected exit 2"; exit 1; }}
"""

manifest = {
    "run_name": "story-data-impact-report",
    "workdir": "/home/bcorfman/dev/ringer-work/story-data-impact-report",
    "max_parallel": 1,
    "worktrees": False,
    "repo": REPO,
    "tasks": [
        {
            "key": "script-default-root-fix",
            "task_type": "code-fix",
            "engine": "codex",
            "model": "gpt-5.6-luna",
            "engine_args": ["-c", "model_reasoning_effort=medium"],
            "max_attempts": 2,
            "timeout_s": 900,
            "check_timeout_s": 600,
            "ownership": [GAPS, TRACE, GUARD],
            "expect_files": [GAPS, TRACE, GUARD],
            "spec": SPEC,
            "check": CHECK,
            "verified": "both scripts find the story from their own location (proved from a copy in another directory), and a guard test keeps any review script from hard-coding an absolute path",
        }
    ],
}
out = Path(__file__).with_name("ci-path-fix-manifest.json")
out.write_text(json.dumps(manifest, indent=2) + "\n")
print(out)
