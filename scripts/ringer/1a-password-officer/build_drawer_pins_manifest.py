# ruff: noqa: E501
"""Small Ringer task: update four old test files whose setups predate the drawer_gap_rechecked rule. Causes are already diagnosed."""

import json
from pathlib import Path

R = "/home/bcorfman/dev/freytag-forge"
PY = f"{R}/.venv/bin/python"
ENV = f"export TMPDIR=/tmp PYTHONPATH={R}:{R}/packages/worldkeeper/src"
TESTS = [
    "test_drawer_gap_nudge.py",
    "test_knowledge_projection.py",
    "test_voiceable_knowledge.py",
    "test_place_scoped_feed.py",
]
FAILING = "tests/test_drawer_gap_nudge.py::test_gap_nudge_stays_eligible_after_delivery_and_storylet_spending tests/test_knowledge_projection.py::test_scene_1a_route_windows_preserve_the_recording_timeline tests/test_voiceable_knowledge.py::test_real_gap_prompt_omits_non_voiceable_player_actions_but_keeps_committed_knowledge tests/test_voiceable_knowledge.py::test_dialogue_grounding_rejects_quoted_gap_statement tests/test_place_scoped_feed.py::test_reach_scoped_committed_statements_follow_the_protagonist"
RUN = "tests/test_1a_drawer_close_gap.py tests/test_1a_phone_thread.py tests/test_audit_budget.py tests/test_1a_gap_pointer.py tests/test_drawer_gap_nudge.py tests/test_knowledge_projection.py tests/test_markdown_story_package.py tests/test_place_scoped_feed.py tests/test_voiceable_knowledge.py tests/test_recent_cue_unit.py tests/test_recent_cue_reference.py"

spec = f"""You are a test-update worker for the freytag-forge repository at {R}. Boundary: NO model call, NO network call, never git commit. You may edit ONLY these tests under {R}/tests: {", ".join(TESTS)}. Edit no data file, no other test, no fixture, no engine. These tests pin the OLD drawer behaviour that Brandon deliberately replaced, so update their setups and expectations narrowly to the new behaviour; never weaken or delete an assertion that still holds.

NEW BEHAVIOUR (already implemented in the data, do not change it): the knowledge record k_sl_1a_f_r2 (statement 'Kristin looks over the drawer.', bare examine/inspect/look at the drawer, repeatable) now requires memory_card_recovered false AND drawer_gap_pointed_out true, and establishes a new fact drawer_gap_rechecked true. So (a) before the gap is found (drawer_gap_pointed_out false) it is never offered; (b) once the gap is found it is offered; (c) its statement is only established, so only shown in prompts or counted as committed knowledge, after drawer_gap_rechecked is true. Opening the drawer now sets drawer_opened (k_sl_1a_f_r1), and closing it sets drawer_gap_pointed_out (k_sl_1a_f_r3).

THE FAILING TESTS AND THEIR CAUSES (all diagnosed; run only these first):
1. tests/test_drawer_gap_nudge.py::test_gap_nudge_stays_eligible_after_delivery_and_storylet_spending (16 params): its helper _state_after_gap_deliveries asserts drawer_gap_pointed_out only; where a test expects the f_r2 statement to appear in a rendered prompt, also assert drawer_gap_rechecked true in that state (or restructure so the handoff still proves f_r2 stays eligible after the gap is found).
2. tests/test_knowledge_projection.py::test_scene_1a_route_windows_preserve_the_recording_timeline: the expected offered-candidate sets for the first two steps contain k_sl_1a_f_r2, but f_r2 is no longer offered before the gap is found, so the freed slot goes to k_sl_1a_g_r1. Update only those two expected sets to what the engine now offers (print the actual sets, confirm the only differences are f_r2 out and g_r1 in), and keep the rest.
3. tests/test_voiceable_knowledge.py::test_real_gap_prompt_omits_non_voiceable_player_actions_but_keeps_committed_knowledge and ::test_dialogue_grounding_rejects_quoted_gap_statement[k_sl_1a_f_r2]: their states assert drawer_gap_pointed_out but not drawer_gap_rechecked, so f_r2 is not committed or sayable-checkable. Add drawer_gap_rechecked true to their state helper where f_r2 must be established.
4. tests/test_place_scoped_feed.py::test_reach_scoped_committed_statements_follow_the_protagonist: add the drawer_gap_rechecked true fact next to the drawer_gap_pointed_out fact it already asserts so 'Kristin looks over the drawer.' appears inside the house and the outside check still holds. Do NOT touch test_in_scene_prompts_are_byte_identical_to_baselines (it must keep the exact byte comparison).
After the edits run `{PY} -m ruff format {" ".join("tests/" + t for t in TESTS)}`.
HOW TO RUN (from {R}; never bare python, never uv): first `{ENV} {PY} -m pytest {FAILING} -q -p no:cacheprovider 2>&1 | tail -20`, then once at the end `{ENV} {PY} -m pytest {RUN} -q -p no:cacheprovider 2>&1 | tail -20`. If a failure remains that these causes do not explain, do not edit data: write its name and failure to {R}/bench/results/1a-passcode-round2/drawer-pins-failures.txt and stop."""

check = f"""set -o pipefail
cd {R}
{ENV}
{PY} -m ruff format --check {" ".join("tests/" + t for t in TESTS)}
! grep -n 'replace("- Kristin looks over the drawer' tests/test_place_scoped_feed.py
{PY} -m pytest {RUN} -q -p no:cacheprovider 2>&1 | tail -20
"""
task = {
    "key": "update-drawer-pins",
    "task_type": "code-fix",
    "engine": "codex",
    "model": "gpt-5.6-luna",
    "engine_args": ["-c", "model_reasoning_effort=medium"],
    "max_attempts": 2,
    "timeout_s": 1200,
    "check_timeout_s": 900,
    "ownership": [f"{R}/tests/{t}" for t in TESTS],
    "expect_files": [f"{R}/tests/{TESTS[0]}"],
    "spec": spec,
    "check": check,
    "verified": "the four old test files match the new drawer behaviour and the drawer, phone-thread, budget and cue suites pass",
}
m = {
    "run_name": "1a-drawer-close-pins",
    "workdir": "/home/bcorfman/dev/ringer-work/1a-drawer-close-pins",
    "max_parallel": 1,
    "worktrees": False,
    "repo": R,
    "tasks": [task],
}
p = Path(f"{R}/scripts/ringer/1a-password-officer/drawer-pins-manifest.json")
p.write_text(json.dumps(m, indent=2) + "\n")
print(p)
