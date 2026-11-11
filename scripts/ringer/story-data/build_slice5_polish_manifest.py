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

SPEC = f"""You are an implementation worker for the freytag-forge repository at {REPO}. Boundary: NO model call, NO network call, never git commit, never uv or bare python, never --cov. You own ONLY {MOD} and {TEST} (both exist; edit them). Read {DEPS} and {SCRIPT} but do not edit them. Touch nothing else.

CONTEXT. `{ENV} && {PY} {SCRIPT} <incident id>` prints the branch report for an incident. Run it for the incident whose scene id is 2C (find it via `load_story_package(...).incidents`, `scene_id == "2C"` ; its id appears in the tests) and read the output as the story author would. Three defects make it hard to read. Fix exactly these three, keep everything else, and keep the report story-agnostic ({MOD} contains no story names: no memory_card, kristin, patrol, laptop, k_sl_, t_1a, pursuit_1b, continuity, rebecca, brandon, michelle, even in comments). Use the word "result", never "flag".

DEFECT 1, repeated bridge text. In "Handoff analysis" the same authored bridge text is appended to every change line (twelve times per branch). Print the bridge text ONCE per handoff, on its own line ("Authored bridge text for this handoff: ..."), and keep each change line short (what changed, from where to where). If the transition has no bridge text, say once that none is authored. The "Evidence for judgment" section still prints the bridge text once as it does now.

DEFECT 2, scene setup listed as moves. Change lines for entities that had no earlier place before the next scene's entry (their place is "none" in the snapshot taken after the branch) are scene setup, not carried-over state. Split the handoff into two lists with plain headings: "Carried over from the branch" (entities that HAD a place or holder after the branch and whose place or holder is different after the next scene's entry; the protagonist arriving at the next location goes here as one line) and "Appears with the next scene" (entities with no earlier place that the entry places). Only the first list can contain a result: a loss of custody, an unexplained move of something that was somewhere, or a companion cleared. The second list is information, collapsed to one short line per entity with its place. The comparison section's last sentence about world moves or custody changes that differ across branches must consider only the first list. Keep the existing seeded tests' intent (loss of custody and clean variant) passing; update their assertions only where the wording or the list they look in changed, and say so in your final message.

DEFECT 3, wrong "read through nothing" wording. In the comparison section and in "Branch facts never read by the next scene or any later scene", a fact that the EXIT transition(s) of the incident's scene read (for example as a trigger) counts as read: it is consumed by the handoff. Compute this with `consumers()` from {DEPS} (a Consumer of kind 'gate' whose record is one of the exit transitions) or by looking at the exit transitions' trigger facts directly. Reword so the output is plain: "read by: <what reads it>" when something reads it and "read by: nothing after this scene" when nothing does; never write "through nothing". A fact read only by an exit transition should say it is read by that transition (name it). Do not change the logic that decides which declared costs or advantages are unread, except that a cost read only by an exit transition is read.

ADD TESTS in {TEST}: (1) the real 2C incident's report contains the bridge text exactly once per branch handoff (count occurrences inside each branch's handoff section, not in the evidence section) and does not contain the substring "through nothing"; (2) a seeded copy where the next scene places a new item not held before: it appears under "Appears with the next scene" and not under "Carried over from the branch", and an item the protagonist held that the entry moves appears under "Carried over from the branch" as a loss of custody; (3) a fact read only by the exit transition is reported as read by that transition (the real 2C package has one; pin that fact by id in the test only). Follow the seeded-copy style already used in {TEST}.

HOW TO RUN (from {REPO}): `{ENV} && {PY} -m pytest {TEST} {GTEST} {ITEST} {TTEST} -q --no-cov -p no:cacheprovider 2>&1 | tail -20`. Format and lint: `{PY} -m ruff format {MOD} {TEST} && {PY} -m ruff check {MOD} {TEST}` (if ruff format cannot write because the filesystem is read-only, run `ruff format --check` and say so). Finally print the real 2C report and read it: no line should repeat, and every sentence should make sense without knowing the code."""

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
n=$(echo "$OUT" | grep -c 'The purge clock was running')
echo "bridge text occurrences in whole report: $n (3 evidence + one per branch handoff expected at most 8)"
test "$n" -le 8 || {{ echo "BRIDGE TEXT STILL REPEATED"; exit 1; }}
echo "$OUT" | grep -q 'through nothing' && {{ echo "STILL SAYS through nothing"; exit 1; }}
echo "$OUT" | grep -q 'Carried over from the branch' || {{ echo "MISSING carried-over heading"; exit 1; }}
echo "$OUT" | grep -q 'Appears with the next scene' || {{ echo "MISSING appears-with heading"; exit 1; }}
echo "$OUT" | grep -q 'combined_broadcast_rescue_plan_known' || {{ echo "missing exit-read fact"; exit 1; }}
echo "$OUT" | sed -n '/^## Comparison/,$p'
"""

manifest = {
    "run_name": "story-data-impact-report",
    "workdir": "/home/bcorfman/dev/ringer-work/story-data-impact-report",
    "max_parallel": 1,
    "worktrees": False,
    "repo": REPO,
    "tasks": [
        {
            "key": "branch-report-polish",
            "task_type": "code-fix",
            "engine": "codex",
            "model": "gpt-5.6-luna",
            "engine_args": ["-c", "model_reasoning_effort=high"],
            "max_attempts": 2,
            "timeout_s": 2400,
            "check_timeout_s": 900,
            "ownership": [MOD, TEST],
            "expect_files": [MOD, TEST],
            "spec": SPEC,
            "check": CHECK,
            "verified": "the bridge text prints once per handoff, scene setup is separated from carried-over state, facts read by the exit transition are reported as read, and the earlier tests still pass",
        }
    ],
}
out = Path(__file__).with_name("slice5-polish-manifest.json")
out.write_text(json.dumps(manifest, indent=2) + "\n")
print(out)
