# ruff: noqa: E501
"""One Ringer task: repair the old tests the full suite showed pin the pre-glance behaviour (plan Round 2e)."""

import json
from pathlib import Path

R = "/home/bcorfman/dev/freytag-forge"
D = f"{R}/scripts/ringer/1a-password-officer"
PY = f"{R}/.venv/bin/python"
ENV = f"export TMPDIR=/tmp PYTHONPATH={R}:{R}/packages/worldkeeper/src"
FILES = [
    f"{R}/tests/test_recent_cue_reference.py",
    f"{R}/tests/test_recent_cue_unit.py",
    f"{R}/tests/test_design_review_fixtures.py",
    f"{R}/tests/shard_durations.json",
]
RUN = "tests/test_recent_cue_reference.py tests/test_recent_cue_unit.py tests/test_design_review_fixtures.py tests/test_regen_shard_durations.py tests/test_1a_arrival_glance.py"
spec = f"""You are a test-repair worker for the freytag-forge repository at {R}. Boundary: NO model call, NO network call, never git commit, do NOT edit story data ({R}/data), engine code (storygame/) or any test other than the files you own: {", ".join(FILES)}.

CONTEXT. Story change just made to scene 1A (data files already edited, do not touch them): (1) the opening entry text gained an arrival glance; (2) the scene-1A handoff cue (handoffs.yaml, fact continuity_initiative_known) is now ONLY "Kristin's initials, KMS, are carved into a drawer of Michelle's workstation." - the old cue also said "The drawer rides high in its frame. A thin gap beneath its lower edge is wide enough for Kristin's fingers.", and the gap is now found only after the drawer is opened and then closed (record k_sl_1a_f_r3), per the earlier drawer-close change; (3) a new pacing event kristin_steadies_1a fires at turn 3 and delivers the back-door deduction (k_sl_1a_a_r1's effect, fact michelle_abduction_suspicion) when the player has not already earned it. Full-suite run showed 11 failures that pin the old behaviour:
A. tests/test_recent_cue_reference.py::test_staged_cue_referent_follow_up_earns_memory_card (4 params: 'Feel in the gap.'/'Search the gap.' x semantic 0/1) and tests/test_recent_cue_unit.py::test_staged_cue_referent_is_used_by_engine (4 params): they follow the cue with 'Feel in the gap.' / 'Search the gap.' and expect the card reveal k_sl_1a_b_r0. The cue no longer mentions a gap, so 'the gap' has no antecedent from the cue. Repair narrowly: keep each test's PURPOSE (a follow-up that refers to something the cue just showed resolves through the recent-cue bridge, and an unrelated follow-up does not). Read recent_cue.py ({R}/storygame/runtime/recent_cue.py) to see what the bridge keys on. Choose follow-up commands that refer to what the NEW cue shows (the carved initials / the drawer) and that still earn the card through the bridge if the bridge supports it; if no follow-up the new cue shows can earn the card by the bridge, then change the assertion to the new truth (the follow-up 'Search the gap.' right after the cue earns nothing because the gap has not been found: selected_knowledge_ids == ()) AND keep a positive bridge test by using a state where the gap WAS found (use the _cue_state helper in test_recent_cue_unit.py, which opens then closes the drawer, or the equivalent in the reference file) so that 'Search the gap.' still earns k_sl_1a_b_r0 there. Never delete a test; never weaken an assertion that still holds.
B. tests/test_recent_cue_reference.py::test_recent_cue_owner_is_rendered_in_the_narrator_player_line: read it and repair it for the same reason (it renders the owner of a cue referent in the narrator's player line; the new cue's referent is the carving/drawer).
C. tests/test_design_review_fixtures.py::test_more_than_four_eligible: asserts len(eligible) == 10 and now gets 9. Find out why (almost certainly the test advances the engine past turn 3 so kristin_steadies_1a delivered the door deduction and k_sl_1a_a_r1 is no longer eligible - confirm by printing the eligible ids before and after on a scratch copy, not by guessing). Update the expectation to 9 and name the reason in a comment ONLY if that is the cause; if the cause is different, stop and write it to {R}/bench/results/1a-passcode-round2/arrival-glance-fix-notes.txt.
D. tests/test_regen_shard_durations.py::test_real_manifest_covers_test_files: the new file tests/test_1a_arrival_glance.py is missing from tests/shard_durations.json. Fix with the repo script exactly as the failure message says: `cd {R} && {ENV} && {PY} scripts/regen_shard_durations.py --missing-only` and check the diff of tests/shard_durations.json is only the added entry (no other file's duration changed).

HOW TO RUN (from {R}; never bare python, never uv): `{ENV} && {PY} -m pytest {RUN} -q --no-cov -p no:cacheprovider 2>&1 | tail -30`. Never use --cov (coverage runs nightly only). Then `{PY} -m ruff check tests && {PY} -m ruff format --check tests`. All must pass."""

check = f"""set -o pipefail
cd {R}
{ENV}
{PY} -m pytest {RUN} -q --no-cov -p no:cacheprovider 2>&1 | tail -25
{PY} -m pytest tests/test_recent_cue_reference.py tests/test_recent_cue_unit.py -q --no-cov -p no:cacheprovider -k "cue" 2>&1 | tail -5
{PY} -m ruff check tests && {PY} -m ruff format --check tests
"""

m = {
    "run_name": "1a-arrival-glance-fix",
    "workdir": "/home/bcorfman/dev/ringer-work/1a-arrival-glance-fix",
    "max_parallel": 1,
    "worktrees": False,
    "repo": R,
    "tasks": [
        {
            "key": "repair-old-pins-for-the-glance",
            "task_type": "code-fix",
            "engine": "codex",
            "model": "gpt-5.6-luna",
            "engine_args": ["-c", "model_reasoning_effort=medium"],
            "max_attempts": 2,
            "timeout_s": 2400,
            "check_timeout_s": 1800,
            "ownership": FILES,
            "expect_files": FILES[:3],
            "spec": spec,
            "check": check,
            "verified": "the 11 full-suite failures pass and the cue bridge keeps a positive test",
        }
    ],
}
path = Path(D) / "arrival-glance-fix-manifest.json"
path.write_text(json.dumps(m, indent=2) + "\n")
print(path)
