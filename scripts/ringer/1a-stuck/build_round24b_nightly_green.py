"""Round 24b: make the coverage nightly honest again (red since 2026-11-02, the 3C finite-evacuation rebuild)."""

import json
from pathlib import Path

import build_round21b_evidence_cap_and_spend_cap as b

b.WORK = "/home/bcorfman/dev/ringer-work/factory-24"

OWNED = [
    "tests/test_3c_carried_start.py",
    "tests/test_3c_item_facts_capture.py",
    "tests/test_3c_no_close_arm.py",
    "tests/test_3c_state_compare.py",
    "tests/test_3c_world_capture_wiring.py",
    "tests/test_game_path_journeys.py",
]

SPEC = b.COMMON + (
    "You may edit ONLY these six test files: " + ", ".join(OWNED) + ". No production code, no story data, no "
    "tests/shard_durations.json.\n\n"
    "BACKGROUND. The nightly suite (`pytest --run-nightly`) has been red since 2026-11-02, when commit 06b2ccb3 "
    "rebuilt scene 3C as a finite evacuation that ends the game. Ten nightly tests fail. Reproduce with: "
    "`.venv/bin/python -m pytest --run-nightly -q -p no:cacheprovider -n 8 " + " ".join(OWNED) + "`.\n\n"
    "PART 1 (delete six stale experiment tests). These nightly tests dry-run the archived Stage 7 3C probe with a "
    "scripted prefix recorded before the rebuild, so they now fail inside the probe (not in the engine): "
    "tests/test_3c_carried_start.py::test_carried_run_row_uses_scene_turns_from_one_without_network, "
    "tests/test_3c_carried_start.py::test_checker_accepts_carried_dry_run_and_rejects_tampered_cap, "
    "tests/test_3c_item_facts_capture.py::test_capture_enabled_dry_run_passes_checker, "
    "tests/test_3c_no_close_arm.py::test_existing_arm_dry_run_remains_byte_stable, "
    "tests/test_3c_state_compare.py::test_state_compare_runs_offline_end_to_end, "
    "tests/test_3c_world_capture_wiring.py::test_item_facts_dry_run_marks_world_capture_without_creating_jev_client. "
    "Delete exactly these six test functions. Then remove only the imports, helpers, fixtures and constants that "
    "became unused in each file (ruff F401/F841 must pass); if a file would end up with no tests at all, delete "
    "the file instead. Do NOT touch any other test in those files, and do NOT touch scripts/.\n\n"
    "PART 2 (pin four journeys as a named issue). In tests/test_game_path_journeys.py the four parametrized cases "
    "of test_every_player_realization_has_an_earned_continuation_to_the_ending for k_sl_3c_d_r1, k_sl_3c_d_r2, "
    "k_sl_3c_e_r1 and k_sl_3c_e_r2 fail with 'was never offered on a legal route'. Cause (verified): the optional "
    "storylets SL-3C-D and SL-3C-E need captives_reaching_surface, which only the old resolution_escape event "
    "sets, and since the rebuild the game ends (story_complete) through another resolution first. This is a real "
    "story gap, not a test bug, so do NOT make the test pass by changing the policy. Pin them the way the module "
    "docstring promises for named issues: add a module constant (for example "
    "KNOWN_UNREACHABLE: dict[str, str]) mapping those four ids to one reason string that names the cause and says "
    "'story gap N-3: the 3C aftermath storylets D and E cannot play; fix the package, then delete this entry', "
    "and build the parametrization so those four ids carry pytest.mark.xfail(strict=True, reason=...). Strict "
    "means the day the story is fixed the test fails and forces deleting the entry. Update the module docstring "
    "line that says two branches are pinned so it describes what is true now. All other cases must still pass "
    "unchanged.\n\n"
    "Report in NOTES.txt exactly which helpers and imports you removed."
)

CHECK_EXTRA = r"""
out=$(.venv/bin/python -m pytest --run-nightly -q -p no:cacheprovider -n 8 tests/test_3c_carried_start.py tests/test_3c_item_facts_capture.py tests/test_3c_no_close_arm.py tests/test_3c_state_compare.py tests/test_3c_world_capture_wiring.py tests/test_game_path_journeys.py 2>&1) || { echo "$out" | tail -30; exit 1; }
echo "$out" | tail -3
echo "$out" | grep -Eq '4 xfailed' || { echo "expected exactly 4 xfailed journey cases"; exit 1; }
! echo "$out" | grep -Eq ' failed| xpassed' || { echo "unexpected failures or xpass"; exit 1; }
grep -q 'xfail' tests/test_game_path_journeys.py && grep -q 'strict=True' tests/test_game_path_journeys.py || { echo "journey pin missing"; exit 1; }
for t in test_carried_run_row_uses_scene_turns_from_one_without_network test_checker_accepts_carried_dry_run_and_rejects_tampered_cap test_capture_enabled_dry_run_passes_checker test_existing_arm_dry_run_remains_byte_stable test_state_compare_runs_offline_end_to_end test_item_facts_dry_run_marks_world_capture_without_creating_jev_client; do
  ! grep -rq "def $t" tests/ || { echo "stale test $t still present"; exit 1; }
done
"""

owned_re = "|".join(p.replace(".", r"\.") for p in OWNED)
manifest = {
    "run_name": "factory-24b-nightly-green",
    "workdir": b.WORK,
    "max_parallel": 1,
    "worktrees": True,
    "repo": b.REPO,
    "tasks": [
        {
            "key": "nightly-green",
            "task_type": "code-fix",
            "engine": "codex",
            "engine_args": ["-c", "model_reasoning_effort=medium"],
            "max_attempts": 2,
            "timeout_s": 1800,
            "check_timeout_s": 900,
            "ownership": OWNED,
            "spec": SPEC,
            "check": b.check(
                owned_re,
                "tests/test_3c_cue_chain.py tests/test_3c_finale_journey.py",
                300,
                CHECK_EXTRA,
                "nightly-green",
            ),
            "expect_files": [],
            "verified": "Nightly 3C failures: six stale probe tests deleted, four unreachable journeys pinned strict-xfail.",
        }
    ],
}
Path(__file__).with_name("round24b-nightly-green-manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")
