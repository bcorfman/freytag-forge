"""Build the Ringer manifest that ports the hand-rolled strand test into a named gap rule."""

import json
from pathlib import Path

REPO = "/home/bcorfman/dev/freytag-forge"
MOD = f"{REPO}/storygame/story_package/gap_rules.py"
TEST = f"{REPO}/tests/test_gap_rules.py"
OLD = f"{REPO}/tests/test_canon_journey.py"
SCRIPT = f"{REPO}/scripts/gap_rules.py"
ENV = f"export TMPDIR=/tmp PYTHONPATH={REPO}:{REPO}/packages/worldkeeper/src"
PY = f"{REPO}/.venv/bin/python"

SPEC = f"""You are an implementation worker for the freytag-forge repository at {REPO}. Boundary: NO model call, NO network call, never git commit, never uv or bare python, never --cov. You own ONLY {MOD}, {TEST} and {OLD} (all exist). Do not touch {SCRIPT}, worldkeeper, story data, or any other file.

GOAL. {OLD} holds an older, hand-rolled check, `test_no_single_reveal_can_strand_a_scene_exit` plus its helper `_reachable_facts`, that walks the story package in the test file. Brandon wants overlapping older tests cleaned up when a named rule does the same job better. Port that check into the gap-rule registry as a fourth rule, prove the rule catches what the old test caught, then delete the old test and its helper.

STEP 1. Read the old test and `_reachable_facts` in {OLD} (about lines 239 to 300) and the registry in {MOD}. Add rule 'single_reveal_strand' to RULES (same signature as the others: (package, root, anchor, exits) -> list[Flag]). For each exit transition: required = its trigger fact ids; for each storylet route in package.storylet_routes.storylets whose scene_id equals the transition's source_scene_id, and each realization: committed = fact ids the realization asserts plus the route's activation_conditions facts with equals True; missing = required - reachable_facts(package, committed, {{route.id}}). Move the _reachable_facts algorithm into {MOD} as a private function, unchanged in behaviour. Emit one Flag per (route, realization) with missing facts: rule 'single_reveal_strand', subject '<route id>/<realization id>', summary 'Choosing <realization> of <route> permanently strands <facts>, which exit <transition> needs.', evidence: the realization and the transition with a source location ONLY where the line defines that record (use the module's existing citation helper and rules; no location otherwise), and a line naming which of the required facts it still sets. Update the module docstring and render text if they list the rules, and make the script's --rule choices include it automatically if they come from RULES (do not edit the script). HARD RULE: {MOD} contains no story names (no memory_card, kristin, patrol, laptop, k_sl_, t_1a, continuity), not even in comments.

STEP 2, tests in {TEST}. (a) Whole-package replacement for the old test: for every transition in the loaded continuity-initiative package, run_gap_rules(root, transition_id, rules=['single_reveal_strand']) returns no flags. This must cover every transition the old test covered. (b) Seeded defect: in a tmp_path copy of data/stories/continuity-initiative (shutil.copytree; edit YAML with yaml.safe_load/safe_dump like the existing tests do), make the smallest edit that still loads where one realization of a storylet in a transition's source scene no longer establishes the exit fact and no bridge event or delivery can set it either (for example point it at a different unlisted outcome), and assert the rule flags that realization. If every such edit is rejected by the loader, say so and use whichever valid edit still trips it; do not weaken the rule. (c) Clean variant: restoring the edit removes the flag.

STEP 3, parity evidence BEFORE deleting. Write a throwaway script in the scratchpad (not the repo) that runs the OLD test body against the seeded-defect copy from (b) by pointing its package at the copy, and run the new rule on the same copy; both must report the same (route, realization) set. Report the output in your final message. If they differ, stop, keep the old test, and report exactly how they differ.

STEP 4, only if parity holds: delete `test_no_single_reveal_can_strand_a_scene_exit` and `_reachable_facts` from {OLD}, plus any import that becomes unused. Leave every other test in that file untouched.

HOW TO RUN (from {REPO}): `{ENV} && {PY} -m pytest {TEST} {OLD} {REPO}/tests/test_situation_trace.py -q --no-cov -p no:cacheprovider 2>&1 | tail -20`. Format and lint: `{PY} -m ruff format {MOD} {TEST} {OLD} && {PY} -m ruff check {MOD} {TEST} {OLD}`."""

CHECK = f"""set -o pipefail
cd {REPO}
{ENV}
PY={PY}
$PY -m ruff check {MOD} {TEST} {OLD}
$PY -m ruff format --check {MOD} {TEST} {OLD}
if grep -n -i -E 'memory_card|kristin|patrol|laptop|k_sl_|t_1a|continuity' {MOD}; then echo 'STORY NAMES FOUND'; exit 1; fi
grep -q 'single_reveal_strand' {MOD}
if grep -n 'test_no_single_reveal_can_strand_a_scene_exit\\|def _reachable_facts' {OLD}; then echo 'old test or helper still present'; exit 1; fi
$PY -m pytest {TEST} {OLD} {REPO}/tests/test_situation_trace.py -q --no-cov -p no:cacheprovider 2>&1 | tail -12
$PY {SCRIPT} t_1a_1b --rule single_reveal_strand | head -8
$PY {SCRIPT} officer_presses_1a | grep -c '^### ' 
"""

manifest = {
    "run_name": "story-data-gap-rules",
    "workdir": "/home/bcorfman/dev/ringer-work/story-data-gap-rules",
    "max_parallel": 1,
    "worktrees": False,
    "repo": REPO,
    "tasks": [
        {
            "key": "port-strand-test",
            "task_type": "code-feature",
            "engine": "codex",
            "model": "gpt-5.6-luna",
            "engine_args": ["-c", "model_reasoning_effort=high"],
            "max_attempts": 2,
            "timeout_s": 1800,
            "check_timeout_s": 900,
            "ownership": [MOD, TEST, OLD],
            "expect_files": [MOD, TEST],
            "spec": SPEC,
            "check": CHECK,
            "verified": "the old hand-rolled strand test is replaced by a named rule that covers every transition and trips on a seeded defect, the old test and helper are gone, and the other gap rules still run",
        }
    ],
}
out = Path(__file__).with_name("slice2-strand-port-manifest.json")
out.write_text(json.dumps(manifest, indent=2) + "\n")
print(out)
