# ruff: noqa: E501  (spec strings are prose briefs for a worker)
"""Fix round for the nightly failures whose fix needs no owner decision.

Five Luna tasks in isolated worktrees, disjoint files. Each check exports the patch, rejects
edits outside the task's files and new skips, runs the target tests (must pass) and guard
tests, and enforces a wall-time budget. The four 3C storylet journeys, the 3C probes and the
drain tests wait for Brandon's decisions and are excluded here.
Usage: build_nightly_rest_fix_manifest.py
"""

from __future__ import annotations

import json
from pathlib import Path

REPO = "/home/bcorfman/dev/freytag-forge"
WORK = "/home/bcorfman/dev/ringer-work/nightly-rest-fix"
OUT = f"{WORK}/out"
DIAG = "/home/bcorfman/dev/ringer-work/nightly-rest-failures/logs"
PYTEST = "PYTHONPATH=$PWD:$PWD/packages/worldkeeper/src TMPDIR=/tmp .venv/bin/python -m pytest -q -p no:cacheprovider --run-nightly -n 16"

COMMON = f"""Your current working directory IS a git worktree of {REPO} (detached at the branch `nightly-suite-repair`). Edit files here directly. NEVER touch {REPO} itself, never git commit, never run `uv`, never call a model or the network, never pass --cov to pytest. FIRST run: [ -e .venv ] || ln -s {REPO}/.venv .venv . Run tests as `{PYTEST} <test ids>`. Leave your changes uncommitted; the check exports them as a patch.

BACKGROUND. The nightly suite (`--run-nightly`) has failed since 2026-11-02. A read-only diagnosis proved these failures are stale tests or test harnesses after intended story changes (for example, commit 06b2ccb3 made `evacuation_complete` the 3C ending and the engine sets `state.story_complete`; later commits renamed places, retimed scenes and added storylets). The story and engine are correct: do NOT change story data under `data/stories/`, the engine under `storygame/runtime/`, or `packages/worldkeeper`. Fix the tests and harness so they assert the CURRENT intended behaviour. Never weaken an assertion so it passes without checking anything; never add skip, xfail or broad try/except; never delete a test unless the task says so. Keep the code ruff-formatted (`.venv/bin/ruff format <file>` and `.venv/bin/ruff check <file>`). Player commands you write must be short imperative sentences, like "Watch the stranger." The diagnosis report for your group is at {{report}}; read its Cause and Fix plan sections for file:line detail.

YOU MAY EDIT ONLY these files: {{files}}. Any other edited file fails the check.
TIME BUDGET: the check runs your target and guard tests with `-n 16` and fails if they take longer than {{budget}} seconds of wall time in total ({{baseline}}). Do not make the tests slower.
"""

TASKS = {
    "environment-screen": {
        "report": f"{DIAG}/environment-screen.worker.reports/report.md",
        "files": [
            "scripts/ringer/environment_narration/screen.py",
            "tests/test_environment_screen.py",
        ],
        "targets": "tests/test_environment_screen.py",
        "guards": "",
        "budget": 30,
        "baseline": "the file takes 3 s now, while failing early; about 10 s is expected once it runs fully",
        "extra": "",
        "spec": """TASK. All five tests in tests/test_environment_screen.py fail because `scripts/ringer/environment_narration/screen.py` exits 2 with `environment screen: expected one kitchen location named 'kitchen', found []`. Commit 7794e4b9 intentionally renamed the kitchen's display name to `Michelle's kitchen`; its stable location id is still `kitchen` (see `data/stories/continuity-initiative/world.yaml`).
1. In screen.py, function `_ids`, find the kitchen by its stable location id `kitchen`, not by display name, keeping the same exactly-one-match error. Do not hard-code the display name and do not change the story aliases. Leave the STARTS records for S5 and S6 keyed as `kitchen`.
2. In tests/test_environment_screen.py, add one assertion that the S5 and S6 start records have place `kitchen`.
3. `test_dry_cost_is_the_sum_of_per_call_ceilings` then fails only on an exact float comparison at about line 90 (difference about 5.6e-17 dollars from summation order). Change only that comparison to `pytest.approx(expected, rel=0, abs=1e-12)`. Keep every other assertion in that test.
All seven tests in the file must pass.""",
    },
    "cue-tests": {
        "report": f"{DIAG}/early-storylets-1a.worker.reports/report.md",
        "files": ["tests/test_recent_cue_unit.py", "tests/test_cue_escalation.py"],
        "targets": "tests/test_recent_cue_unit.py tests/test_cue_escalation.py",
        "guards": "",
        "budget": 25,
        "baseline": "both files take 15 s now",
        "extra": 'grep -q "k_sl_1a_b_r0" tests/test_recent_cue_unit.py || { echo "the B0 cue expectation was removed from test_recent_cue_unit.py"; exit 1; }',
        "spec": """TASK. Two 1A cue tests are stale after the drawer redesign and the 1A retime.
1. `tests/test_recent_cue_unit.py::test_late_scene_cue_survives_saturated_turn_record_ids` fails with `assert () == ('k_sl_1a_b_r0',)` (about line 124). Opening the drawer no longer reveals the gap by itself: the redesigned drawer separates opening, closing and pointing out the gap. Make the test play the current staged flow before searching for the gap: use the open, re-arm and close sequence that the file's `_cue_state` helper (or the existing drawer tests in the file) already uses. Keep the B0 cue expectation `('k_sl_1a_b_r0',)` and the fact assertion. Do not make opening alone reveal the gap.
2. `tests/test_cue_escalation.py::test_scene_reentry_clears_cues_and_allows_a_new_escalation` fails at about line 66: the CueStage tuples differ. The 1A retime intentionally moved the second escalation. The diagnosis measured the re-entry `last_turn` as 28 where the test expects 24. Verify that by running the test, then change only that expected value. Keep `visit_entered_at=14` and every other stage assertion.
All tests in both files must pass.""",
    },
    "leakage-matrix": {
        "report": f"{DIAG}/early-storylets-1a.worker.reports/report.md",
        "files": ["tests/test_knowledge_leakage_matrix.py"],
        "targets": "tests/test_knowledge_leakage_matrix.py",
        "guards": "tests/test_1a_departure_hold.py",
        "budget": 30,
        "baseline": "the file takes 10 s now",
        "extra": 'grep -q "expected targeted reveal" tests/test_knowledge_leakage_matrix.py || { echo "the targeted-reveal assertion was removed"; exit 1; }',
        "spec": """TASK. `tests/test_knowledge_leakage_matrix.py::test_leakage_matrix_context_snapshot_stays_within_the_declared_payload_budget` fails with `committed diff regressed at 1A/player/before:k_sl_1a_b_r1: expected targeted reveal 'k_sl_1a_b_r1', got ['k_sl_1a_b_r2', 'k_sl_1a_d_r1']` (about line 276). First bad commit a5515298 ("Scene 1A: hold the player back when they try to drive to the park too early") added storylet SL-1A-K and items that can only be reached at the truck (`kristin_truck`). The matrix fixture places the protagonist without regard to where each observed item can be reached, so a truck-only item is out of reach and its reveal never commits.
Fix the fixture: in `_positioned_state` / `_build_leakage_matrix` (or the helper that sets up each matrix row), place the protagonist where the item being observed can be reached, using the item's declared reach or place in the compiled story (as `tests/test_1a_departure_hold.py` does for the truck). If an item has no reachable place, the fixture must say so explicitly, not drop the row silently. Keep the targeted-reveal assertion and the payload budget unchanged; do not broaden the payload. Both tests in the file must pass, and `tests/test_1a_departure_hold.py` must still pass.""",
    },
    "journey-harness": {
        "report": f"{DIAG}/early-storylets-1a.worker.reports/report.md and /home/bcorfman/dev/ringer-work/nightly-rest-failures/early-storylets-later/report.md",
        "files": ["tests/test_game_path_journeys.py", "tests/journey_prefix.py"],
        "targets": " ".join(
            f"'tests/test_game_path_journeys.py::test_every_player_realization_has_an_earned_continuation_to_the_ending[{k}]'"
            for k in (
                "k_sl_1a_b_r1",
                "k_sl_1a_f_r2",
                "k_sl_1a_f_r3",
                "k_sl_1a_j_r3",
                "k_sl_1a_k_r1",
                "k_sl_1b_g_r1",
                "k_sl_2a_g_r1",
                "k_sl_2a_h_r1",
                "k_sl_2b_g_r1",
                "k_sl_2c_g_r1",
            )
        ),
        "guards": "tests/test_game_path_journeys.py tests/test_journey_prefix_equivalence.py tests/test_evidence_gap_journeys.py tests/test_three_c_prefix.py",
        "budget": 330,
        "baseline": "the three journey files take 125 s now with -n 16; test_three_c_prefix.py adds about 60 s of setup",
        "guard_allowed_failures": [
            "k_sl_3c_d_r1",
            "k_sl_3c_d_r2",
            "k_sl_3c_e_r1",
            "k_sl_3c_e_r2",
        ],
        "extra": "",
        "spec": """TASK. `tests/test_game_path_journeys.py::test_every_player_realization_has_an_earned_continuation_to_the_ending[<id>]` fails for ten ids because the scripted playthrough that prefers that storylet never gets it offered. Every one is reachable by a real player. The playthrough harness (`tests/journey_prefix.py`, the `CHAINS` table and helpers in the test file) is stale:
- `k_sl_1a_f_r2`, `k_sl_1a_f_r3`: the redesigned drawer separates opening (F-R1), closing and pointing out the gap (F-R3, sets `drawer_gap_pointed_out`), and F-R2 comes after that chain. Add the prerequisite chain to `CHAINS` (F-R1 before F-R3; F-R1 and F-R3 before F-R2) instead of blocking the siblings.
- `k_sl_1a_j_r3`: needs Michelle's text read first (`michelle_text_read`, set by J-R1 or J-R2). Add that chain.
- `k_sl_1a_b_r1`, `k_sl_1a_k_r1`: the laptop / K checks need the protagonist at the truck (`kristin_truck`), added in commit a5515298. Add a legal, placement-aware move to the truck before these checks, modelled on the truck setup in `tests/test_1a_departure_hold.py`. Do NOT seed `memory_card_recovered`, `departure_held` or any other target outcome fact; the move itself must make the item reachable.
- `k_sl_2b_g_r1`: add `"k_sl_2b_g_r1": ("k_sl_2b_f_r1", "k_sl_2b_g_r1")` to `CHAINS`. `k_sl_2c_g_r1`: add `"k_sl_2c_g_r1": ("k_sl_2b_f_r1", "k_sl_2c_g_r1")`. The diagnosis ran both and reached all nine scenes with no forced exit.
- `k_sl_1b_g_r1`, `k_sl_2a_g_r1`, `k_sl_2a_h_r1`: these are low-priority optional reveals that the empty-command replay never ranks into the four offered candidates; they are offered when the player acts on them. Make the preferred-candidate replay action-aware: when the preferred id is one of these, pass the canonical player command to `RuntimeEngine.turn` (and to the offer projection the harness uses) so action evidence ranks it in. Commands: 1B G "Watch the stranger." (proven in `tests/test_richer_1b.py`), 2A G "Trace the return line.", 2A H "Look at the camera." (proven in `tests/test_richer_2a.py`). Keep the thorough empty-command walk unchanged. Do not raise the projection cap or any storylet priority.
The journey ending check already accepts `state.story_complete` through `storygame/personas.py::_resolution_complete`; do not change personas.py or restore `resolution_complete`.
LEAVE ALONE the four 3C cases `k_sl_3c_d_r1`, `k_sl_3c_d_r2`, `k_sl_3c_e_r1`, `k_sl_3c_e_r2`: they wait on an owner decision and must still fail exactly as now. Do not add them to any table or special case.
All ten target cases must pass, and every other test in the guard files must pass except those four 3C cases.""",
    },
    "capture-tests": {
        "report": f"{DIAG}/capture-fixtures.worker.reports/report.md",
        "files": ["tests/test_hidden_bench_1b2_capture.py", "tests/test_bench_item_facts.py"],
        "targets": "tests/test_hidden_bench_1b2_capture.py::test_tampered_1b2_details_are_reported_as_exposure tests/test_bench_item_facts.py::test_invalid_proposal_after_recovery_is_a_rejected_turn",
        "guards": "tests/test_hidden_bench_1b2_capture.py tests/test_bench_item_facts.py",
        "budget": 60,
        "baseline": "both files take 31 s now with -n 16",
        "extra": 'grep -q "hidden clue Michelle photograph" tests/test_hidden_bench_1b2_capture.py || { echo "the tampered hidden-clue detail is gone"; exit 1; }',
        "spec": """TASK. Two capture tests are stale after the story-source migration.
1. `tests/test_hidden_bench_1b2_capture.py::test_tampered_1b2_details_are_reported_as_exposure` fails with `KeyError: 'outline[1B.2].details'` at `tests/story_source/helpers.py:128`. Commit 53911de2 moved it onto `compiled_story_copy()` and `patch_source()`, but the outline details live in the scene file. Call `patch_source(tampered / "source", "scenes/1B.yaml", "outline[1B.2].details", ...)`, building the new list from the CURRENT 1B.2 details in `data/stories/continuity-initiative/source/scenes/1B.yaml` (read them from the copied source in the test, do not hard-code an old list) with `hidden clue Michelle photograph` appended. Keep the package-load assertion and the Findings exposure assertion. Do not change `scripts/ringer/environment_narration/hidden_bench_1b2_capture.py`.
2. `tests/test_bench_item_facts.py::test_invalid_proposal_after_recovery_is_a_rejected_turn` fails with `assert []` at about line 3549. Commit 8f2ad1e3 gave scene 1A a fixed scripted opening, so the test's request-count fault injection no longer hits the provider call it names. Add the existing `provider_opening_story` fixture (`tests/conftest.py`, it removes `scripted_opening` from a compiled copy) to the test's parameters. Keep the assertions that the run succeeds, has turns, and records a rejected turn. If the rejection now lands at a different turn, assert that turn's INVALID_PROPOSAL record, never a bare non-empty list.
Every test in both files must pass.""",
    },
}


def check(key: str, t: dict) -> str:
    allowed = " ".join(t["files"])
    allowed_fail = "|".join(t.get("guard_allowed_failures", [])) or "NO_ALLOWED_FAILURE"
    guards = t["guards"]
    return f"""set -eo pipefail
mkdir -p {OUT}
[ -e .venv ] || ln -s {REPO}/.venv .venv
git add -A
git diff --cached > {OUT}/{key}.patch
changed=$(git diff --cached --name-only)
[ -n "$changed" ] || {{ echo "no changes made"; exit 1; }}
for f in $changed; do
  case " {allowed} " in *" $f "*) ;; *) echo "edited a file outside this task: $f"; exit 1;; esac
done
if git diff --cached -U0 | grep -E '^\\+' | grep -nE 'pytest\\.(skip|xfail)|mark\\.(skip|xfail)|except Exception: *pass'; then echo "added a skip, xfail or swallowed exception"; exit 1; fi
py=$(echo "$changed" | grep -E '\\.py$' || true)
if [ -n "$py" ]; then .venv/bin/ruff format --check $py && .venv/bin/ruff check $py; fi
{t["extra"]}
start=$SECONDS
rc=0
{PYTEST} {t["targets"]} > /tmp/nrf-{key}-targets.out 2>&1 || rc=$?
tail -15 /tmp/nrf-{key}-targets.out
[ "$rc" = 0 ] || {{ echo "target tests fail (exit $rc)"; exit 1; }}
grep -qE "[0-9]+ passed" /tmp/nrf-{key}-targets.out || {{ echo "no target test ran"; exit 1; }}
if [ -n "{guards}" ]; then
  rc=0
  {PYTEST} -rf {guards} > /tmp/nrf-{key}-guards.out 2>&1 || rc=$?
  tail -12 /tmp/nrf-{key}-guards.out
  bad=$(grep -E '^(FAILED|ERROR) ' /tmp/nrf-{key}-guards.out | grep -vE '{allowed_fail}' || true)
  [ -z "$bad" ] || {{ echo "guard tests fail:"; echo "$bad"; exit 1; }}
  [ "$rc" = 0 ] || [ "{allowed_fail}" != NO_ALLOWED_FAILURE ] || {{ echo "guard run exit $rc"; exit 1; }}
  grep -qE "[0-9]+ passed" /tmp/nrf-{key}-guards.out || {{ echo "guard run passed nothing (exit $rc)"; exit 1; }}
fi
el=$((SECONDS-start))
echo "tests took $el s (budget {t["budget"]} s)"
[ "$el" -le {t["budget"]} ] || {{ echo "over the time budget: $el s > {t["budget"]} s"; exit 1; }}
echo "PASS {key}: patch at {OUT}/{key}.patch"
"""


def build() -> dict:
    tasks = []
    for key, t in TASKS.items():
        spec = (
            COMMON.replace("{report}", t["report"])
            .replace("{files}", ", ".join(t["files"]))
            .replace("{budget}", str(t["budget"]))
            .replace("{baseline}", t["baseline"])
        )
        tasks.append(
            {
                "key": key,
                "task_type": "code-fix",
                "engine": "codex",
                "model": "gpt-5.6-luna",
                "engine_args": ["-c", "model_reasoning_effort=high"],
                "max_attempts": 2,
                "timeout_s": 2700,
                "check_timeout_s": 900,
                "spec": spec + "\n" + t["spec"],
                "check": check(key, t),
                "expect_files": [f"{OUT}/{key}.patch"],
                "verified": f"Patch touches only {', '.join(t['files'])}, adds no skip or xfail, is ruff-clean; the target tests pass and the guard tests pass (bar the four 3C cases waiting on a decision) within {t['budget']} s with -n 16.",
            }
        )
    return {
        "run_name": "nightly-rest-fix",
        "workdir": WORK,
        "max_parallel": 3,
        "worktrees": True,
        "repo": REPO,
        "tasks": tasks,
    }


if __name__ == "__main__":
    out = Path(__file__).with_name("nightly-rest-fix-manifest.json")
    out.write_text(json.dumps(build(), indent=2) + "\n", encoding="utf-8")
    print(out)
