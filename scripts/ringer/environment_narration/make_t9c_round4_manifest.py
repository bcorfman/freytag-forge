# ruff: noqa: E501
"""Generate the Ringer build manifest for T9c round 4: bring older tests in line with Brandon's drawer rules."""

from __future__ import annotations

import json
from pathlib import Path

REPO = "/home/bcorfman/dev/freytag-forge"
E = "scripts/ringer/environment_narration"
OUT = Path(REPO) / E / "build-t9c-round4.json"
PREREG = ".plans/grounded-llm-environment-narration/t9c-engine-open-prereg.md"

COMMON = (
    "You are working in freytag-forge (Python 3.12). Working directory: /home/bcorfman/dev/freytag-forge. "
    "export PYTHONPATH=/home/bcorfman/dev/freytag-forge TMPDIR=/tmp; run `.venv/bin/python` (never uv). "
    "Run tests with `env -u CLOUDFLARE_WORKER_URL -u CLOUDFLARE_WORKER_TOKEN .venv/bin/python -m pytest -q -p no:cacheprovider --no-cov <files>`. "
    "No network, no live model call, no billed call. Do not git commit. NEVER print or write any credential. NO regular expressions in new code. Story-agnostic: no story names or vocabulary in non-test code under storygame/. "
    "Run ruff check and ruff format on your files at the end. Another worker edits OTHER files in this checkout at the same time; edit only the files you own. "
    f"BACKGROUND. Read {PREREG} first. Brandon changed the drawer rules for the continuity story: `inspect`, `examine`, `search`, `check`, `look at`, `study` on the drawer are look commands that do not open it and now earn the repeatable gap nudge `k_sl_1a_f_r2` (data/stories/continuity-initiative/knowledge.yaml: statement `Kristin looks over the drawer and is pointed toward the thin gap beneath its lower edge.`, evidence [[examine, inspect, search, check, look, study, read, trace, run my fingers], [drawer, \"drawer's\", KMS, initials, carved initials, carving, my initials]], `repeatable: true`, delivery text `The drawer rides high in its frame. A thin gap beneath its lower edge is wide enough for Kristin's fingers.`); the nudge is eligible while its storylet SL-1A-F is active or after it has been earned once, and stops when the card is recovered. Under forms (under, beneath, underneath, below) still earn the card find `k_sl_1a_b_r0`, which wins over the nudge because it has more evidence groups. The opening verbs and inside, in, into or through forms are opening commands. About 30 older tests pinned the OLD behaviour (for example `Search the drawer.` selects nothing; the old statement text of `k_sl_1a_f_r2`). "
    "RULES FOR UPDATING OLD TESTS: update an old assertion ONLY when it pins behaviour that Brandon's rules above deliberately changed, and keep the test's intent (move a command to the new expected id, update the expected text). Never delete a test, never loosen an assertion to a weaker one, never skip or xfail. If a failure is NOT explained by those rules, do not edit the test: describe the failure and your diagnosis in your final message. List every assertion you changed with the rule that justifies it in your final message. "
)

MATCHER_SPEC = (
    COMMON
    + "YOUR TASK A: (1) `uniquely_matched_candidate` in storygame/runtime/candidate_matcher.py (the plain evidence match; it returns a candidate only when exactly one matches) must apply the same rule that `uniquely_matched_authored_handoff` already applies: when more than one candidate matches in full, the candidate with strictly the most evidence groups wins; a tie returns None. Today a command with an under word matches both the card find (3 groups) and the nudge (2 groups) and the plain match returns None. Check where else `uniquely_matched_candidate` and similar plain matchers are used (search storygame/) and keep their meaning. "
    "(2) Then bring these tests in line with the rules, owning only: storygame/runtime/candidate_matcher.py, tests/test_candidate_matcher.py (extend with tests for (1): 3-group beats 2-group, equal groups returns None, one-group partial never wins), tests/test_1a_back_door_gap.py, tests/test_1a_gap_pointer.py, tests/test_1a_drawer_words.py, tests/test_drawer_gap_nudge.py. "
    "Known: in tests/test_1a_gap_pointer.py the commands in `test_drawer_gap_reveals_do_not_steal_unrelated_commands` that name the drawer with a look verb (`Search the workstation drawer.`, `Examine the workstation drawer.`, `Search the drawer interior.`, `Search the open drawer.`, `Search the KMS drawer.`, `Examine the drawer's interior.`, `Search the drawer.`) now earn the nudge: move them to a new parametrized test expecting `k_sl_1a_f_r2` from both the handoff and the plain match, and keep the truly unrelated ones (`Search the kitchen.`, `Inspect Michelle's workstation.`, `Read the receipt.`) expecting None. `test_drawer_gap_realizations_have_exact_deliveries_and_fact_metadata` pinned the old R2 statement and delivery text: update to the new text and assert `repeatable` is True for R2 and False for R1. Check the helpers in those files activate the storylets the way the game does (SL-1A-F active at 1A); fix the helper only if the test's intent needs it. In tests/test_drawer_gap_nudge.py (written for this change) the 8 bare-command cases fail because the state does not have SL-1A-F active: add it the way the engine does (`state.active_event_ids`), and keep the repeat tests that set it fired. In tests/test_1a_drawer_words.py make sure the 'select nothing' list still holds under the helper's state; if a command there now selects the nudge when SL-1A-F is active, state which and move it. "
    "Finish by running all six test files plus tests/test_reveal_eligibility.py, tests/test_reveal_universe.py, tests/test_repeatable_knowledge.py and report each file's result."
)

CUE_SPEC = (
    COMMON
    + "YOUR TASK B: three older tests. YOU MAY EDIT ONLY: tests/test_cue_escalation.py, tests/test_place_scoped_feed.py, tests/test_invitation_report.py and scripts/ringer/affordance/invitation_report.py (the last only if the diagnosis below shows the report mishandles a repeatable entry). "
    "(1) tests/test_cue_escalation.py::test_earned_reveal_before_nudge_never_escalates: its first command `Search the drawer.` used to select nothing; it now earns the nudge on turn 1, so the drawer cue is not delivered that turn and cue_stages is empty. Keep the intent (an earned reveal before the cue nudge never escalates): use a first command that touches nothing (`Inspect the workstation.` is already used by the later turns in that test, check it behaves) and keep every other assertion. Check the other tests in that file for the same drawer command and fix them the same way only if they fail. "
    "(2) tests/test_place_scoped_feed.py: `test_reach_scoped_committed_statements_follow_the_protagonist` asserts the old statement text of `k_sl_1a_f_r2` (`Kristin examines the carved initials and is pointed toward the thin gap ...`): update the expected text to the new statement. `test_in_scene_prompts_are_byte_identical_to_baselines` passed after the eligibility narrowing; if it still fails, diagnose before editing. "
    "(3) tests/test_invitation_report.py::test_1a_drawer_cue_has_an_eligible_response fails: the report (scripts/ringer/affordance/invitation_report.py) now labels the 1A drawer cue row without `eligible response`. Read the report code and the cue/delivery data, find out why (for example the report decides eligibility from the storylet being active or the entry being unestablished, and a repeatable entry changes that, or the cue's response set changed), and say which. If the report should treat a repeatable entry like the engine's `explain_reveal` does, fix the report and keep the test; if the row legitimately changed because of Brandon's rules, update the test and justify it. "
    "Run these three test files and tests/test_cue_lifecycle.py (if it exists) plus any test that imports invitation_report, and report each file's result."
)

CHECK_A = (
    "cd /home/bcorfman/dev/freytag-forge && export PYTHONPATH=/home/bcorfman/dev/freytag-forge TMPDIR=/tmp && set -o pipefail && "
    "env -u CLOUDFLARE_WORKER_URL -u CLOUDFLARE_WORKER_TOKEN .venv/bin/python -m pytest -q -p no:cacheprovider --no-cov tests/test_candidate_matcher.py tests/test_1a_back_door_gap.py tests/test_1a_gap_pointer.py tests/test_1a_drawer_words.py tests/test_drawer_gap_nudge.py tests/test_reveal_eligibility.py tests/test_reveal_universe.py tests/test_repeatable_knowledge.py 2>&1 | tee /tmp/t9c-r4-a.out | tail -6 && "
    "! grep -Eq '[0-9]+ (failed|error)' /tmp/t9c-r4-a.out && ! grep -nE 'xfail|pytest.skip|mark.skip' tests/test_1a_gap_pointer.py tests/test_1a_drawer_words.py tests/test_drawer_gap_nudge.py tests/test_1a_back_door_gap.py && "
    ".venv/bin/python -m ruff check storygame/runtime/candidate_matcher.py tests/test_candidate_matcher.py tests/test_1a_back_door_gap.py tests/test_1a_gap_pointer.py tests/test_1a_drawer_words.py tests/test_drawer_gap_nudge.py && "
    ".venv/bin/python -m ruff format --check storygame/runtime/candidate_matcher.py tests/test_candidate_matcher.py tests/test_1a_back_door_gap.py tests/test_1a_gap_pointer.py tests/test_1a_drawer_words.py tests/test_drawer_gap_nudge.py"
)

CHECK_B = (
    "cd /home/bcorfman/dev/freytag-forge && export PYTHONPATH=/home/bcorfman/dev/freytag-forge TMPDIR=/tmp && set -o pipefail && "
    "env -u CLOUDFLARE_WORKER_URL -u CLOUDFLARE_WORKER_TOKEN .venv/bin/python -m pytest -q -p no:cacheprovider --no-cov tests/test_cue_escalation.py tests/test_place_scoped_feed.py tests/test_invitation_report.py 2>&1 | tee /tmp/t9c-r4-b.out | tail -6 && "
    "! grep -Eq '[0-9]+ (failed|error)' /tmp/t9c-r4-b.out && ! grep -nE 'xfail|pytest.skip|mark.skip' tests/test_cue_escalation.py tests/test_place_scoped_feed.py tests/test_invitation_report.py && "
    ".venv/bin/python -m ruff check tests/test_cue_escalation.py tests/test_place_scoped_feed.py tests/test_invitation_report.py scripts/ringer/affordance/invitation_report.py && "
    ".venv/bin/python -m ruff format --check tests/test_cue_escalation.py tests/test_place_scoped_feed.py tests/test_invitation_report.py scripts/ringer/affordance/invitation_report.py"
)


def _task(key, spec, check, ownership, expect, verified):
    return {
        "key": key,
        "task_type": "code-fix",
        "engine": "codex",
        "model": "gpt-5.6-luna",
        "engine_args": ["-c", "model_reasoning_effort=high"],
        "full_access": True,
        "max_attempts": 2,
        "timeout_s": 3600,
        "check_timeout_s": 1800,
        "ownership": ownership,
        "expect_files": [f"{REPO}/{p}" for p in expect],
        "spec": spec,
        "check": check,
        "verified": verified,
    }


manifest = {
    "run_name": "grounded-environment-narration",
    "workdir": "/home/bcorfman/dev/ringer-work/grounded-environment-narration-t9c-round4",
    "max_parallel": 2,
    "worktrees": False,
    "repo": REPO,
    "tasks": [
        _task(
            "t9c-matcher-and-pointer-tests",
            MATCHER_SPEC,
            CHECK_A,
            [
                "storygame/runtime/candidate_matcher.py",
                "tests/test_candidate_matcher.py",
                "tests/test_1a_back_door_gap.py",
                "tests/test_1a_gap_pointer.py",
                "tests/test_1a_drawer_words.py",
                "tests/test_drawer_gap_nudge.py",
            ],
            ["tests/test_1a_gap_pointer.py"],
            "the plain match uses the most specific rule and the drawer tests follow Brandon's rules",
        ),
        _task(
            "t9c-cue-and-feed-tests",
            CUE_SPEC,
            CHECK_B,
            [
                "tests/test_cue_escalation.py",
                "tests/test_place_scoped_feed.py",
                "tests/test_invitation_report.py",
                "scripts/ringer/affordance/invitation_report.py",
            ],
            ["tests/test_cue_escalation.py"],
            "cue, feed and invitation tests follow Brandon's drawer rules",
        ),
    ],
}

if __name__ == "__main__":
    OUT.write_text(json.dumps(manifest, indent=2) + "\n")
