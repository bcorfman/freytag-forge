"""Build the Ringer manifest that fixes the three output defects in the first branch report."""

import json
from pathlib import Path

REPO = "/home/bcorfman/dev/freytag-forge"
MOD = f"{REPO}/storygame/story_package/branch_report.py"
TEST = f"{REPO}/tests/test_branch_report.py"
DEPS = f"{REPO}/storygame/story_package/dependencies.py"
SCRIPT = f"{REPO}/scripts/branch_report.py"
GTEST = f"{REPO}/tests/test_gap_rules.py"
ITEST = f"{REPO}/tests/test_impact_report.py"
TTEST = f"{REPO}/tests/test_situation_trace.py"
ENV = f"export TMPDIR=/tmp PYTHONPATH={REPO}:{REPO}/packages/worldkeeper/src"
PY = f"{REPO}/.venv/bin/python"
NAMES = "memory_card|kristin|patrol|laptop|k_sl_|t_1a|continuity|pursuit_1b|rebecca|brandon|michelle"

SPEC = f"""You are an implementation worker for the freytag-forge repository at {REPO}. Boundary: NO model call, NO network call, never git commit, never uv or bare python, never --cov. You own ONLY {MOD} and {TEST} (both exist; edit them). Touch nothing else. {MOD} must contain no story names (no memory_card, kristin, patrol, laptop, k_sl_, t_1a, pursuit_1b, continuity, rebecca, brandon, michelle) and never the word flag; use "result".

CONTEXT. `{ENV} && {PY} {SCRIPT} <incident id>` prints the branch report for an incident (the real one for scene 2C is `i_2c_rebecca_corridor`). A recent change made facts that the incident scene's own exit transition reads count as "read", which is right for the "read by:" wording. But the final comparison line "Branches that leave no trace in any later scene:" now uses the same notion, so a branch whose only reader is the exit transition (which belongs to the incident's own scene, not a later scene) wrongly counts as having left a trace. On the real 2C incident that line used to list the transmit branch, the recovery branch and the missed-window branch, and now lists only the missed-window branch.

FIX. A branch leaves a trace in a later scene only if at least one fact it sets (or one declared advantage or cost it sets) is read by a record whose scene is the NEXT scene or any scene after it (Consumer.scene_id, compared with the incident's scene and the next scene's id; a consumer with scene_id equal to the incident's own scene, and the exit transition itself, do not count). Keep the per-fact "read by:" wording as it is. Make the two ideas separate in the code: one helper for "read by anything, including this scene's exit transition" and one for "read in a later scene". If the order of scenes is needed, derive it from the package's scene list order or the pacing transitions graph; do not hard-code ids. Expected on the real 2C incident: the line lists the transmit branch, the recovery branch (`SL-2C-E`) and the missed-window branch (`purge_window_2c`), and does NOT list the rescue branch.

FORMAT FIX. In "Handoff analysis" the two headings "Carried over from the branch:" and "Appears with the next scene:" are bare lines between list items. Render them as list items with nested bullets beneath, matching the style of the "Entry variants that apply" block, and put a blank line before the "Handoff from ..." line.

ADD TESTS in {TEST}: the real 2C incident's report names exactly those three branches in the no-trace line and not the rescue branch (pin by id in the test only); a seeded copy where a branch's only reader is the exit transition still counts as leaving no trace; a seeded copy where the next scene gains an entry variant requiring a fact that branch sets makes the branch leave a trace. Existing tests must keep passing.

HOW TO RUN (from {REPO}): `{ENV} && {PY} -m pytest {TEST} {GTEST} {ITEST} {TTEST} -q --no-cov -p no:cacheprovider 2>&1 | tail -20`. Format and lint: `{PY} -m ruff format {MOD} {TEST} && {PY} -m ruff check {MOD} {TEST}` (if ruff format cannot write because the filesystem is read-only, run `ruff format --check` and say so)."""

CHECK = f"""set -o pipefail
cd {REPO}
{ENV}
PY={PY}
$PY -m ruff check {MOD} {TEST}
$PY -m ruff format --check {MOD} {TEST}
if grep -n -i -E '{NAMES}' {MOD}; then echo 'STORY NAMES FOUND'; exit 1; fi
if grep -n -i -w 'flag' {MOD}; then echo 'USE THE WORD RESULT, NOT FLAG'; exit 1; fi
$PY -m pytest {TEST} {GTEST} {ITEST} {TTEST} -q --no-cov -p no:cacheprovider 2>&1 | tail -12
OUT=$($PY {SCRIPT} i_2c_rebecca_corridor) || {{ echo "script failed"; echo "$OUT"; exit 1; }}
LINE=$(echo "$OUT" | grep 'leave no trace')
echo "$LINE"
for b in committed_to_transmit SL-2C-E purge_window_2c; do echo "$LINE" | grep -q "$b" || {{ echo "NO-TRACE LINE MISSING $b"; exit 1; }}; done
echo "$LINE" | grep -q 'committed_to_rescue' && {{ echo "RESCUE BRANCH WRONGLY LISTED"; exit 1; }}
echo "$OUT" | grep -q 'through nothing' && {{ echo "STILL SAYS through nothing"; exit 1; }}
echo "$OUT" | sed -n '/Handoff analysis/,/Entry variants that apply/p' | head -30
"""

manifest = {
    "run_name": "story-data-impact-report",
    "workdir": "/home/bcorfman/dev/ringer-work/story-data-impact-report",
    "max_parallel": 1,
    "worktrees": False,
    "repo": REPO,
    "tasks": [
        {
            "key": "branch-report-trace-fix",
            "task_type": "code-fix",
            "engine": "codex",
            "model": "gpt-5.6-luna",
            "engine_args": ["-c", "model_reasoning_effort=high"],
            "max_attempts": 2,
            "timeout_s": 1800,
            "check_timeout_s": 900,
            "ownership": [MOD, TEST],
            "expect_files": [MOD, TEST],
            "spec": SPEC,
            "check": CHECK,
            "verified": "the no-trace line counts only reads in the next scene or later, the real 2C report lists the transmit, recovery and missed-window branches, and the earlier tests still pass",
        }
    ],
}
out = Path(__file__).with_name("slice5-trace-fix-manifest.json")
out.write_text(json.dumps(manifest, indent=2) + "\n")
print(out)
