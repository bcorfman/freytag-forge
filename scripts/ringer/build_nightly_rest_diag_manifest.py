# ruff: noqa: E501  (spec strings are prose briefs for a worker)
"""Read-only diagnosis of the 33 nightly failures left after the personas ending fix.

One Codex task per cause group. Each finds the first bad commit for one named test and
proves it (passes at the parent, fails at the commit), explains the cause, decides stale test
or real defect, and writes an exact fix plan for the whole group. Nothing is edited.
Usage: build_nightly_rest_diag_manifest.py
"""

from __future__ import annotations

import json
from pathlib import Path

REPO = "/home/bcorfman/dev/freytag-forge"
WORK = "/home/bcorfman/dev/ringer-work/nightly-rest-failures"
GOOD = "1abb54b008"
PYTEST = "PYTHONPATH=$PWD:$PWD/packages/worldkeeper/src TMPDIR=/tmp .venv/bin/python -m pytest -q -p no:cacheprovider -n 0 --run-nightly"

COMMON = f"""You are a read-only diagnostic scout. Your current working directory IS a git worktree of {REPO} (detached at HEAD, the branch `nightly-suite-repair`, which is main plus a one-line fix in `storygame/personas.py` making `_resolution_complete` also accept `state.story_complete`). You may `git checkout` other commits INSIDE THIS WORKTREE to bisect (return to the starting commit when done), and you may write scratch files under /tmp. You must NEVER edit, stage or commit any tracked file, never touch {REPO} itself, never run `uv`, never call a model or the network, and never pass --cov to pytest. FIRST run: [ -e .venv ] || ln -s {REPO}/.venv .venv . Run tests as `{PYTEST} <test ids>`. When you check out an old commit, keep the .venv symlink (it is untracked).

BACKGROUND. The workflow `coverage nightly` (`.github/workflows/coverage-nightly.yml`, whole suite with `--run-nightly`) was last green on {GOOD} (2026-11-01) and has failed every night since. Commit `06b2ccb3` ("Rebuild 3C as a finite evacuation that ends the game", in PR #745, 2026-11-02) replaced the old 3C ending fact `resolution_complete` with `evacuation_complete`; the engine sets `state.story_complete` and stops taking turns after the ending. Story source is under `data/stories/` and `source/`. Many later commits enriched scenes (new storylets, placements, plot text). Some failing tests are stale after intended changes; some may be real defects a player could hit. Your job is to tell which, with executed evidence.

YOUR GROUP and the failing tests, with the error each gives on the starting commit, are below. For the PRIMARY test: find the FIRST BAD COMMIT (the earliest single non-merge commit after {GOOD} where it fails and its parent passes; bisect with `git bisect` or by hand, walking merged branches as needed), and confirm it by running the test at the parent and at the commit. If the primary test already fails at {GOOD}, say so and pick another test from the group that does pass there. For every OTHER test in the group, say whether it has the same first bad commit (run it at the parent and the commit) or its own (find it if cheap, otherwise give a range). Then explain the cause with file:line citations for every claim, decide stale test or real defect for each test (cite the commit message, plan text in `.plans/` or `docs/PRD.md` showing what change was intended), and write an exact fix plan.

Fix-plan rules (the fix will be done by another worker from your plan, so make it precise): name each file and function to change and what the new code or expectation should be. Prefer fixing a stale test's expectation or fixture to match the intended current story over changing the story. If a test only guards removed behaviour and has no current equivalent, say to delete it and why. If the story or engine is wrong (a player can hit it), say exactly what in the story data or engine is wrong. Do not propose loosening an assertion so it passes without checking anything. World-model logic belongs in `packages/worldkeeper`. Estimate the test run time after the fix.

REPORT: write {{report}} (run `mkdir -p $(dirname {{report}})` first), plain words, with these sections:
- `## First bad commit`: a line exactly `FIRST_BAD: <full 40-character sha>` and a line exactly `TEST: <one pytest node id that passes at the parent and fails at the commit>`, then the commit subject and what it changed.
- `## Cause`: per test, where and why it now fails, with file:line.
- `## Stale test or real defect`: per test, your verdict and reasons.
- `## Fix plan`: per test, the exact change (files, functions, new expectations), or delete-with-reason, plus the decisions that need the project owner (if any).
- `## Evidence`: the commands you ran and their key output lines.
"""

GROUPS = {
    "early-storylets-1a": (
        "tests/test_knowledge_leakage_matrix.py::test_leakage_matrix_context_snapshot_stays_within_the_declared_payload_budget",
        """GROUP: 1A storylets that a scripted playthrough prefers but is never offered, plus 1A cue tests that may share the cause.
- tests/test_knowledge_leakage_matrix.py::test_leakage_matrix_context_snapshot_stays_within_the_declared_payload_budget (PRIMARY): `committed diff regressed at 1A/player/before:k_sl_1a_b_r1: expected targeted reveal 'k_sl_1a_b_r1', got ['k_sl_1a_b_r2', 'k_sl_1a_d_r1']` (tests/test_knowledge_leakage_matrix.py:276).
- tests/test_game_path_journeys.py::test_every_player_realization_has_an_earned_continuation_to_the_ending[k_sl_1a_b_r1], [k_sl_1a_f_r2], [k_sl_1a_f_r3], [k_sl_1a_j_r3], [k_sl_1a_k_r1]: the preferred realization is never in the journey's realized list.
- tests/test_recent_cue_unit.py::test_late_scene_cue_survives_saturated_turn_record_ids: `assert () == ('k_sl_1a_b_r0',)` (tests/test_recent_cue_unit.py:124).
- tests/test_cue_escalation.py::test_scene_reentry_clears_cues_and_allows_a_new_escalation: CueStage tuples differ (tests/test_cue_escalation.py:66).
For the journey cases, play the journey with the preference and say at which turn the preferred storylet should have been offered and what gate (fact, turn window, item placement, earliest/target turn, phase) now blocks it. Say whether a real player could still reach that storylet in 1A.""",
    ),
    "early-storylets-later": (
        "tests/test_game_path_journeys.py::test_every_player_realization_has_an_earned_continuation_to_the_ending[k_sl_2a_g_r1]",
        """GROUP: storylets in 1B, 2A, 2B and 2C that a scripted playthrough prefers but is never offered.
- tests/test_game_path_journeys.py::test_every_player_realization_has_an_earned_continuation_to_the_ending[k_sl_2a_g_r1] (PRIMARY), [k_sl_2a_h_r1], [k_sl_2b_g_r1], [k_sl_2c_g_r1], [k_sl_1b_g_r1]: the preferred realization is never in the journey's realized list.
Play each journey with the preference and say at which turn the preferred storylet should have been offered and what gate (fact, turn window, item placement, earliest/target turn, phase) now blocks it. Say whether a real player could still reach that storylet. Note the project rule: a new optional storylet's target_turn must be >= existing forward-activated ones (earliest>0), or fast play is blocked; check whether that rule is broken.""",
    ),
    "3c-optional-storylets": (
        "tests/test_game_path_journeys.py::test_every_player_realization_has_an_earned_continuation_to_the_ending[k_sl_3c_d_r1]",
        """GROUP: four optional 3C storylets that a scripted playthrough prefers but never reaches.
- tests/test_game_path_journeys.py::test_every_player_realization_has_an_earned_continuation_to_the_ending[k_sl_3c_d_r1] (PRIMARY), [k_sl_3c_d_r2], [k_sl_3c_e_r1], [k_sl_3c_e_r2].
An earlier scout claimed they need `captives_reaching_surface`, that only the escape sequence after the ending sets it (`source/scenes/3C.yaml` around lines 876-1151 and 1241-1256), and that the game stops taking turns once the evacuation completes (`storygame/runtime/engine.py:469-474`). That claim is UNVERIFIED: trace it yourself from the story data and engine code, and by playing. Say exactly which facts gate each of the four, which beats or storylets set those facts, and whether any order of player moves lets a real player see each of the four before the ending. If they are unreachable, lay out the two fix options (drop the four storylets, or move what they need before the ending) with the exact story edits each needs and which other content or tests each would affect; the project owner will choose.""",
    ),
    "3c-probes": (
        "tests/test_3c_item_facts_capture.py::test_capture_enabled_dry_run_passes_checker",
        """GROUP: offline 3C probe harness tests (scripts/ringer/stage7/three_c_probe.py and related).
- tests/test_3c_item_facts_capture.py::test_capture_enabled_dry_run_passes_checker (PRIMARY) and tests/test_3c_world_capture_wiring.py::test_item_facts_dry_run_marks_world_capture_without_creating_jev_client: errors include `RuntimeError: control package did not retain the recorded old C-R1 statement` (scripts/ringer/stage7/three_c_probe.py:377) and `RuntimeError: postc scripted reveal k_sl_3c_c_r2 committed nothing` (three_c_probe.py:685).
- tests/test_3c_carried_start.py::test_carried_run_row_uses_scene_turns_from_one_without_network and ::test_checker_accepts_carried_dry_run_and_rejects_tampered_cap: `assert ['loaded vari...rent package'] == []` (tests/test_3c_carried_start.py:79), believed to be a stale saved 3B starting state.
- tests/test_3c_no_close_arm.py::test_existing_arm_dry_run_remains_byte_stable and tests/test_3c_state_compare.py::test_state_compare_runs_offline_end_to_end: `ProposalValidationError: selected knowledge is not eligible for this turn` (storygame/runtime/validation.py:246).
Say for each whether the probe tool is still used by any current plan step or bench (search `.plans/`, `docs/`, `scripts/`); if a probe only exercised the old 3C, say whether to update it to the new 3C or delete the probe and its tests. If a saved starting state is stale, say how it is regenerated (the exact script and command).""",
    ),
    "environment-screen": (
        "tests/test_environment_screen.py::test_dry_document_freezes_the_six_start_matrix_and_is_deterministic",
        """GROUP: the environment screen script.
- tests/test_environment_screen.py: all five tests fail because the script exits 2 instead of 0 (tests/test_environment_screen.py:31, 45, 165, 190, 216): test_dry_document_freezes_the_six_start_matrix_and_is_deterministic (PRIMARY), test_dry_cost_is_the_sum_of_per_call_ceilings, test_fake_transport_sends_model_interleaves_and_stops_on_quota, test_fake_transport_stops_on_rejection_and_echo_mismatch_without_retry, test_failed_worker_call_is_recorded_once_without_retry.
An earlier scout said the script looks for a place named `kitchen` that no longer exists. Find the script's stderr message, the commit that renamed or removed the place, and whether the screen's start matrix should name the new place (give the exact new id) or the screen is obsolete (say whether anything still uses it).""",
    ),
    "capture-fixtures": (
        "tests/test_drain_details_capture.py::test_candidate_reuses_the_existing_storm_drain_and_adds_no_world_entities",
        """GROUP: capture-bench fixtures that read old story files or formats, plus one bench item-facts test.
- tests/test_drain_details_capture.py::test_candidate_reuses_the_existing_storm_drain_and_adds_no_world_entities (PRIMARY), ::test_candidate_changes_only_affected_scene_requests_and_never_scene_1b2_or_other_scene, ::test_candidate_reaches_the_1b_requests_without_future_reveal_leak: `FileNotFoundError: .../continuity-initiative-candidate/plot.md`.
- tests/test_hidden_bench_1b2_capture.py::test_tampered_1b2_details_are_reported_as_exposure: `KeyError: 'outline[1B.2].details'` (tests/story_source/helpers.py:128).
- tests/test_bench_item_facts.py::test_invalid_proposal_after_recovery_is_a_rejected_turn: `assert []` at tests/test_bench_item_facts.py:3549.
For the drain and 1B.2 tests: say what the current story source layout is (where the plot text and outline details now live), whether the candidate scripts these tests exercise are still used, and whether to point the tests at the new layout or delete them. For the bench item-facts test, find its own first bad commit and cause.""",
    ),
}


def check(report: str, primary: str) -> str:
    return f"""set -eo pipefail
R={report}
[ -s "$R" ] || {{ echo "missing $R"; exit 1; }}
for h in "first bad commit" "cause" "stale test or real defect" "fix plan" "evidence"; do
  grep -qi "^## *$h" "$R" || {{ echo "report lacks section: $h"; exit 1; }}
done
grep -qE "[A-Za-z0-9_/.-]+\\.(py|yaml|yml|md|json):[0-9]+" "$R" || {{ echo "report cites no file:line"; exit 1; }}
sha=$(grep -oE "^FIRST_BAD: *[0-9a-f]{{40}}" "$R" | head -1 | grep -oE "[0-9a-f]{{40}}" || true)
test_id=$(grep -oE '^TEST: *[`]?tests/[^ `]+' "$R" | head -1 | sed -E 's/^TEST: *//; s/`//g' || true)
[ -n "$sha" ] || {{ echo "no FIRST_BAD: <40-char sha> line"; exit 1; }}
[ -n "$test_id" ] || {{ echo "no TEST: tests/... line"; exit 1; }}
cd {REPO}
git cat-file -e "$sha^{{commit}}" || {{ echo "FIRST_BAD $sha is not a commit"; exit 1; }}
git merge-base --is-ancestor {GOOD} "$sha" && git merge-base --is-ancestor "$sha" HEAD || {{ echo "$sha is not between {GOOD} and the branch head"; exit 1; }}
[ "$sha" != "$(git rev-parse {GOOD})" ] || {{ echo "FIRST_BAD is the green commit"; exit 1; }}
T=$(mktemp -d /tmp/nightly-rest-XXXX)
trap 'cd {REPO}; git worktree remove --force "$T/parent" 2>/dev/null; git worktree remove --force "$T/bad" 2>/dev/null; git worktree prune; rm -rf "$T"' EXIT
git worktree add -q --detach "$T/parent" "$sha^"
git worktree add -q --detach "$T/bad" "$sha"
for side in parent bad; do
  ln -s {REPO}/.venv "$T/$side/.venv"
  rc=0
  (cd "$T/$side" && PYTHONPATH=$PWD:$PWD/packages/worldkeeper/src TMPDIR=/tmp timeout 900 .venv/bin/python -m pytest -q -p no:cacheprovider -n 0 --run-nightly "$test_id" > "$T/$side.out" 2>&1) || rc=$?
  tail -4 "$T/$side.out"
  echo "$side: exit $rc"
  if [ "$side" = parent ]; then [ "$rc" = 0 ] || {{ echo "TEST does not pass at the parent of FIRST_BAD"; exit 1; }}; fi
  if [ "$side" = bad ]; then [ "$rc" = 1 ] || {{ echo "TEST does not fail (exit 1) at FIRST_BAD"; exit 1; }}; fi
done
grep -q "passed" "$T/parent.out" || {{ echo "parent run collected no passing test (wrong node id?)"; exit 1; }}
# the primary test (or its stand-in) must still fail on the branch head
rc=0
(cd {REPO} && PYTHONPATH=$PWD:$PWD/packages/worldkeeper/src TMPDIR=/tmp timeout 900 .venv/bin/python -m pytest -q -p no:cacheprovider -n 0 --run-nightly "$test_id" > "$T/head.out" 2>&1) || rc=$?
[ "$rc" = 1 ] || {{ tail -4 "$T/head.out"; echo "TEST does not fail on the branch head (exit $rc); it is not one of the failures"; exit 1; }}
echo "first bad commit proved: $sha for $test_id (primary was {primary})"
"""


def build() -> dict:
    tasks = []
    for key, (primary, group) in GROUPS.items():
        report = f"{WORK}/{key}/report.md"
        tasks.append(
            {
                "key": key,
                "task_type": "probe",
                "engine": "codex",
                "model": "gpt-5.6-luna",
                "engine_args": ["-c", "model_reasoning_effort=high"],
                "max_attempts": 2,
                "timeout_s": 3600,
                "check_timeout_s": 2400,
                "spec": COMMON.replace("{report}", report) + "\n" + group,
                "check": check(report, primary),
                "expect_files": [report],
                "verified": "Report has all five sections with file:line citations; its FIRST_BAD commit lies between the last green nightly and the branch head; the named test passes at that commit's parent, fails at the commit and still fails on the branch head, all run fresh by the check.",
            }
        )
    return {
        "run_name": "nightly-rest-failures",
        "workdir": WORK,
        "max_parallel": 3,
        "worktrees": True,
        "repo": REPO,
        "tasks": tasks,
    }


if __name__ == "__main__":
    out = Path(__file__).with_name("nightly-rest-diag-manifest.json")
    out.write_text(json.dumps(build(), indent=2) + "\n", encoding="utf-8")
    print(out)
