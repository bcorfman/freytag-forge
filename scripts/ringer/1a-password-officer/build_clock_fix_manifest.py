# ruff: noqa: E501
"""Second Ringer task for the 1A clock retiming: update the tests that still pin the old timeline. Behavior stays; numbers and trailing semantics move."""

import json
from pathlib import Path

R = "/home/bcorfman/dev/freytag-forge"
D = f"{R}/scripts/ringer/1a-password-officer"
PY = f"{R}/.venv/bin/python"
S = f"{R}/data/stories/continuity-initiative"
FOCUS = "tests/test_recovery_after_choice.py tests/test_2c_ledger_guard.py tests/test_cue_escalation.py tests/test_attempt_bundle.py tests/test_1a_gap_pointer.py tests/test_complication_text_safety.py tests/test_richer_1a_fixes.py tests/test_trailing_pacing_events.py tests/test_1a_pacing_timeline.py tests/test_regen_shard_durations.py"

spec = f"""You are a test-maintenance worker for the freytag-forge repository at {R}. Boundary: NO model call, NO network call, never git commit. You may edit ONLY files under {R}/tests (but not tests/fixtures) and {R}/tests/shard_durations.json. Never edit anything under {R}/storygame, {R}/data, {R}/packages, {R}/bench, {R}/docs, {R}/scripts. The shipped story data and engine are CORRECT and final; make the tests agree with them.

BACKGROUND. The scene 1A clock was retimed on purpose (do not question it): arrive at turn 6, enter 7, officer_presses 7, patrol leaves 10, search narrows 11, patrol returns 13; arrive/enter/leave are `trailing: true` pacing events (skipped before the narrator is called, fired after the player's action, verbatim text appended after the story; see tests/test_1a_pacing_timeline.py, docs/markdown-story-authoring/pacing-and-incidents.md, and the PacingEvent model). Scene 1A's window is now min_turns 13, nudge_after_turns 14, handoff_after_turns 15 (it was 9, 10, 13); SL-1A-C's window is 6/8/9; the story's authored turn cap is 122 (it was 120). The baseline test suite passed before the change, so every failing test below fails only because it pins the old timeline or assumes a non-trailing event.

FAILING TESTS TO FIX (from the last full run): tests/test_recovery_after_choice.py (many parametrized cases: 2A and 2C recovery, probably walks through 1A to its handoff or counts turns), tests/test_2c_ledger_guard.py::test_2b_outcome_blocks_late_audit_recovery, tests/test_cue_escalation.py (5 tests: the 1A scene nudge is now at turn 14 and the forced handoff at 15), tests/test_attempt_bundle.py (2 tests: 1A min_turns floor now 13), tests/test_1a_gap_pointer.py::test_1a_transition_and_timer_remain_authored_values (the pinned window tuple becomes (13, 14, 15)), tests/test_richer_1a_fixes.py::test_the_neighbor_is_offered_after_the_patrol_is_in_the_house (its helper `_walk_to_the_neighbor` hard-codes five commands and assumes the patrol is already inside; with arrival 6 and entry 7 add the extra neutral turns it needs, keeping what it proves), tests/test_complication_text_safety.py::test_complication_text_is_accepted_on_event_firing_turn (every realization must still be accepted on its firing turn; for an event with trailing true the realization text is not narrated by the provider but appended after the story by the engine, so assert that the verbatim text is present exactly once in the returned proposal's segments AFTER the narrator reply, and keep the existing assertion for non-trailing events), tests/test_regen_shard_durations.py (run `{PY} scripts/regen_shard_durations.py --missing-only` from {R} to add tests/test_1a_pacing_timeline.py and tests/test_trailing_pacing_events.py to tests/shard_durations.json; that command is allowed even though it is a script).
tests/test_trailing_pacing_events.py (the 11 tests written for the feature) still assumes the OLD clock and that no shipped event is trailing. Rewrite its helpers and numbers for the shipped clock while keeping every test's purpose: the shipped package now has trailing arrive/enter/leave, so (a) the `_control` default-false test should assert that events WITHOUT the flag (for example officer_presses_1a, home_search_narrows_1a, patrol_returns_1a) have trailing False and that the model default is False; (b) build the non-trailing control variant by REMOVING the '  trailing: true' line from the copied pacing.yaml for the event under test (assert the anchor occurs once) and the trailing variant is the shipped file; (c) the departure happens at turn 10 and the arrival at turn 6 and entering at turn 7 (adapt the command prefix to those turn numbers using neutral accepted commands; officer parent at the turn-10 request is 'kitchen' for trailing and 'patrol_staging' for the non-trailing control); (d) the invalid-flag test inserts 'trailing: maybe' for a copy and must still require a message that names a boolean; (e) the doc test stays.
Run the full suite after your edits and keep going until it is green. If a test truly cannot be adapted without changing what it proves, do NOT weaken it; describe it in {D}/clock-fix-notes.txt (you may create that file) and leave it failing.
HOW TO RUN (from {R}; never bare python, never uv): `TMPDIR=/tmp PYTHONPATH={R}:{R}/packages/worldkeeper/src {PY} -m pytest -q --no-cov -p no:cacheprovider -n 4 {FOCUS} 2>&1 | tail -30`, then the full suite `TMPDIR=/tmp PYTHONPATH={R}:{R}/packages/worldkeeper/src {PY} -m pytest -q --no-cov -p no:cacheprovider -n 4 2>&1 | tail -30`; `{PY} -m ruff format tests && {PY} -m ruff check tests`."""

check = f"""set -o pipefail
cd {R}
export TMPDIR=/tmp PYTHONPATH={R}:{R}/packages/worldkeeper/src
git diff --name-only | grep -v -E '^(storygame/story_package/models.py|storygame/runtime/engine.py|docs/markdown-story-authoring/pacing-and-incidents.md|docs/testing-runbook/prompt-inspection.md|data/stories/continuity-initiative/(pacing.yaml|storylet-routes.yaml|storylets.md|plot.md)|tests/[A-Za-z0-9_]+\\.py|tests/shard_durations.json)$' && {{ echo 'unexpected tracked file changed'; exit 1; }}
{PY} -m ruff check tests storygame
{PY} -m ruff format --check tests
{PY} -m pytest -q --no-cov -p no:cacheprovider -n 4 2>&1 | tail -25
"""

task = {
    "key": "fix-pinned-1a-tests",
    "task_type": "test-hardening",
    "engine": "codex",
    "model": "gpt-5.6-luna",
    "engine_args": ["-c", "model_reasoning_effort=medium"],
    "max_attempts": 2,
    "timeout_s": 3600,
    "check_timeout_s": 1500,
    "ownership": [f"{R}/tests/", f"{D}/clock-fix-notes.txt"],
    "expect_files": [f"{R}/tests/test_trailing_pacing_events.py"],
    "spec": spec,
    "check": check,
    "verified": "the full suite is green with the retimed 1A clock; only tests changed",
}
manifest = {
    "run_name": "retime-1a-clock",
    "workdir": "/home/bcorfman/dev/ringer-work/retime-1a-clock",
    "max_parallel": 1,
    "worktrees": False,
    "repo": R,
    "tasks": [task],
}
Path(f"{D}/clock-fix-manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")
print("written")
