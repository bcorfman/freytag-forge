# ruff: noqa: E501
"""One narrow Ringer task: undo the shortcuts the drawer-close data task took (review findings 1 to 4)."""

import json
from pathlib import Path

R = "/home/bcorfman/dev/freytag-forge"
PKG = f"{R}/data/stories/continuity-initiative"
PY = f"{R}/.venv/bin/python"
ENV = f"export TMPDIR=/tmp PYTHONPATH={R}:{R}/packages/worldkeeper/src"
NOTES = f"{R}/bench/results/1a-passcode-round2/drawer-close-review-notes.txt"
TESTS = [
    "test_place_scoped_feed.py",
    "test_knowledge_projection.py",
    "test_markdown_story_package.py",
    "test_voiceable_knowledge.py",
    "test_recent_cue_unit.py",
    "test_recent_cue_reference.py",
    "test_drawer_avoidance_repro.py",
]
RUN = f"tests/test_1a_drawer_close_gap.py tests/test_1a_phone_thread.py tests/test_audit_budget.py tests/test_1a_gap_pointer.py tests/test_drawer_gap_nudge.py {' '.join('tests/' + t for t in TESTS)}"

spec = f"""You are a repair worker for the freytag-forge repository at {R}. Boundary: NO model call, NO network call, never git commit. Do NOT edit tests/test_1a_drawer_close_gap.py, tests/test_1a_phone_thread.py, tests/test_audit_budget.py or tests/fixtures/deep_turn_budget.json. You may edit {PKG}/knowledge.yaml and {PKG}/storylet-routes.yaml, and these tests: {", ".join(TESTS)} (under {R}/tests). A previous worker made the drawer-close change and took four shortcuts. Undo them WITHOUT raising any budget pin.

1. DUMMY EFFECT AND TEST STRIP. In knowledge.yaml, record k_sl_1a_f_r2 has `establishes: [{{op: retract, fact_id: reyes_watched_text, value: false}}]`, a dummy that is true in every state, so its statement 'Kristin looks over the drawer.' leaks into every scene 1A prompt (even the opening). Restore its establishes to `[{{op: assert, fact_id: drawer_gap_pointed_out, value: true}}]` (it already requires drawer_gap_pointed_out true, so it is only established after the gap is found). In tests/test_place_scoped_feed.py::test_in_scene_prompts_are_byte_identical_to_baselines restore the exact original comparison `assert prompt["user"] == expected["user"]` (remove the .replace strip). The byte comparison to the recorded baselines must pass with NO stripping; if a baseline legitimately differs, write the exact diff to {NOTES} and stop.
2. PRIORITY. Records k_sl_1a_j_r1, r2 and r3 have relevance priority 10, so they crowd the four offered candidates on unrelated commands. Set their relevance priority to -1 (ambient; they still surface when the command's action evidence matches, as docs/markdown-story-authoring/knowledge-and-disclosure.md explains). Then restore the original expected candidate sets in tests/test_knowledge_projection.py (git diff shows what was changed; remove the k_sl_1a_j_r1 additions and put back the original k_sl_1a_a_r1/k_sl_1a_f_r2/k_sl_1a_g_r1 members) unless the original set is no longer correct because of the open-then-close drawer change, in which case change only the drawer ids and say why in {NOTES}.
3. SPECIAL CASE. tests/test_markdown_story_package.py discards michelle_abduction_suspicion for SL-1A-J realizations when comparing knowledge effects with route operations. Make the DATA consistent instead: k_sl_1a_j_r1 and k_sl_1a_j_r2 also establish michelle_abduction_suspicion true (as their route operations do), and restore the original `assert effects == set(realization.operations)` with no discard and no RouteOperation import.
4. FLIPPED ASSERTIONS. (a) tests/test_voiceable_knowledge.py::test_real_recovery_prompt_omits_non_voiceable_player_action_but_keeps_officer_line was flipped from `in` to `not in` for the officer line 'may say this aloud: An officer saw Kristin take Michelle's memory card'. Find out why that line disappeared (compare `git diff HEAD -- {PKG}` for the records involved; the budget task also trimmed statements). If the loss is a regression caused by a trimmed statement or changed fact, FIX THE DATA and restore the original assertion. If it is a legitimate consequence of the new order, keep the change and explain it in {NOTES}. (b) tests/test_recent_cue_unit.py and test_recent_cue_reference.py: one assertion changed recent_cue_owner from 'drawer' to None. Find out whether, after 'Open the drawer.' then 'Close the drawer.' (the new delivery of the gap), a follow-up like 'Search the gap.' still resolves through the recent cue to the drawer. If the cue no longer resolves, that is a regression: fix the data or the test setup so the cue works after the close delivery and restore 'drawer'; otherwise explain in {NOTES}.
Also run `{PY} -m ruff format` on the tests you edited (tests/test_drawer_avoidance_repro.py has a mis-indented block).
Write a short {NOTES} listing for each of the four items what you found and what you changed. Keep every other byte unchanged. Typography: straight apostrophes.
HOW TO RUN (from {R}; never bare python, never uv; run ONLY these, not the whole suite): `{ENV} {PY} -m pytest {RUN} -q -p no:cacheprovider -x -q 2>&1 | tail -30`."""

check = f"""set -o pipefail
cd {R}
{ENV}
test -s {NOTES}
! grep -n "retract" -B3 -A3 {PKG}/knowledge.yaml | grep -q "reyes_watched_text"
! grep -n 'replace("- Kristin looks over the drawer' tests/test_place_scoped_feed.py
{PY} -m ruff format --check {" ".join("tests/" + t for t in TESTS)}
{PY} -m pytest {RUN} -q -p no:cacheprovider 2>&1 | tail -20
"""
task = {
    "key": "repair-drawer-close-shortcuts",
    "task_type": "code-fix",
    "engine": "codex",
    "model": "gpt-5.6-luna",
    "engine_args": ["-c", "model_reasoning_effort=medium"],
    "max_attempts": 2,
    "timeout_s": 1800,
    "check_timeout_s": 1200,
    "ownership": [f"{PKG}/knowledge.yaml", f"{PKG}/storylet-routes.yaml"] + [f"{R}/tests/{t}" for t in TESTS] + [NOTES],
    "expect_files": [NOTES],
    "spec": spec,
    "check": check,
    "verified": "no dummy effect, no prompt strip, ambient priorities, consistent effects, and the flipped assertions explained or restored",
}
m = {
    "run_name": "1a-drawer-close-review-fix",
    "workdir": "/home/bcorfman/dev/ringer-work/1a-drawer-close-review-fix",
    "max_parallel": 1,
    "worktrees": False,
    "repo": R,
    "tasks": [task],
}
p = Path(f"{R}/scripts/ringer/1a-password-officer/drawer-review-fix-manifest.json")
p.write_text(json.dumps(m, indent=2) + "\n")
print(p)
