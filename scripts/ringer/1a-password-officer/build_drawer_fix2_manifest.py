# ruff: noqa: E501
"""Second, small repair task for the drawer-close and phone-thread data: three named defects, targeted tests."""

import json
from pathlib import Path

R = "/home/bcorfman/dev/freytag-forge"
PKG = f"{R}/data/stories/continuity-initiative"
PY = f"{R}/.venv/bin/python"
ENV = f"export TMPDIR=/tmp PYTHONPATH={R}:{R}/packages/worldkeeper/src"
RUN = "tests/test_1a_drawer_close_gap.py tests/test_1a_phone_thread.py tests/test_audit_budget.py tests/test_1a_gap_pointer.py tests/test_drawer_gap_nudge.py tests/test_knowledge_projection.py tests/test_markdown_story_package.py tests/test_place_scoped_feed.py tests/test_voiceable_knowledge.py tests/test_recent_cue_unit.py tests/test_recent_cue_reference.py"

spec = f"""You are a story-data repair worker for the freytag-forge repository at {R}. Boundary: NO model call, NO network call, never git commit. You own ONLY {PKG}/knowledge.yaml, {PKG}/storylet-routes.yaml and {PKG}/world.yaml. Do not edit any test, fixture, doc, engine or other data file. Fix exactly these three defects (all causes are already diagnosed):

1. DRAWER EXAMINE FIRES TOO EARLY. Record k_sl_1a_f_r2 (bare examine of the drawer, repeatable) must only be offered after Kristin found the gap. It currently has requires [memory_card_recovered equals false] only, because the loader rejects a record that establishes a fact it also requires ('establishes its own prerequisite') and it establishes drawer_gap_pointed_out. Fix: add `- fact_id: drawer_gap_pointed_out, equals: true` to its requires, and change its establishes to assert a NEW fact drawer_gap_rechecked true. Declare drawer_gap_rechecked ('Kristin has looked the drawer over again after finding the gap.') in the knowledge.yaml facts list, the world.yaml facts list and storylet-routes.yaml new_fact_ids (used_by_storylets [SL-1A-F]), and change the SL-1A-F-R2 realization operations in storylet-routes.yaml to assert drawer_gap_rechecked true (not drawer_gap_pointed_out). Keep the loader's other rules: the knowledge effects of each F record must equal its route operations exactly (SL-1A-F-R1 asserts drawer_opened, R3 asserts drawer_gap_pointed_out). Do not touch k_sl_1a_f_r1, r3 or b_r0w.
2. ROUTE/KNOWLEDGE MISMATCH. In storylet-routes.yaml SL-1A-J-R1 and SL-1A-J-R2 assert michelle_abduction_suspicion true; knowledge records k_sl_1a_j_r1 and k_sl_1a_j_r2 also establish it. The protected test tests/test_1a_phone_thread.py requires these records to establish ONLY michelle_text_read (R2 also reyes_watched_text). Remove michelle_abduction_suspicion from BOTH the route operations and the two knowledge records so route and knowledge match and the test passes.
3. PHONE THREAD CROWDS OTHER REVEALS. k_sl_1a_j_r1, r2 and r3 list `michelle` in entity_ids, so any command that mentions Michelle ranks them above the kitchen reveals (the candidate order sorts on referenced entities before priority) and they displace k_sl_1a_g_r1 in tests/test_knowledge_projection.py::test_scene_1a_route_windows_preserve_the_recording_timeline. Set their entity_ids to [kristin, michelle_phone]. Keep priority -1 and every other field.
Keep every other byte unchanged. Straight apostrophes.
HOW TO RUN (from {R}; never bare python, never uv; run ONLY these): `{ENV} {PY} -m pytest {RUN} -q -p no:cacheprovider 2>&1 | tail -25`. Everything in that list must pass. If a test outside your three files still fails, do NOT edit it: write its name and failure to {R}/bench/results/1a-passcode-round2/drawer-fix2-failures.txt and stop."""

check = f"""set -o pipefail
cd {R}
{ENV}
{PY} -m pytest {RUN} -q -p no:cacheprovider 2>&1 | tail -20
"""
task = {
    "key": "repair-drawer-and-phone-data",
    "task_type": "code-fix",
    "engine": "codex",
    "model": "gpt-5.6-luna",
    "engine_args": ["-c", "model_reasoning_effort=medium"],
    "max_attempts": 2,
    "timeout_s": 1200,
    "check_timeout_s": 900,
    "ownership": [f"{PKG}/knowledge.yaml", f"{PKG}/storylet-routes.yaml", f"{PKG}/world.yaml"],
    "expect_files": [f"{PKG}/knowledge.yaml"],
    "spec": spec,
    "check": check,
    "verified": "the drawer, phone-thread, budget and cue suites all pass",
}
m = {
    "run_name": "1a-drawer-close-fix2",
    "workdir": "/home/bcorfman/dev/ringer-work/1a-drawer-close-fix2",
    "max_parallel": 1,
    "worktrees": False,
    "repo": R,
    "tasks": [task],
}
p = Path(f"{R}/scripts/ringer/1a-password-officer/drawer-fix2-manifest.json")
p.write_text(json.dumps(m, indent=2) + "\n")
print(p)
