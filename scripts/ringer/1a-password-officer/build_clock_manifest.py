# ruff: noqa: E501
"""Build the one-task Ringer manifest that retimes the scene 1A patrol clock (Brandon: 15 turns, arrive 6, enter 7, leave 10, narrow 11, return 13)."""

import json
from pathlib import Path

R = "/home/bcorfman/dev/freytag-forge"
D = f"{R}/scripts/ringer/1a-password-officer"
PY = f"{R}/.venv/bin/python"
S = f"{R}/data/stories/continuity-initiative"
FROZEN_TEST = f"{R}/tests/test_trailing_pacing_events.py"
FROZEN_SHA = "9ed2a2c2f0aef5274edb06abcd096e4d41f92aab56284dea94d27618f0b01842"
NEW_TEST = f"{R}/tests/test_1a_pacing_timeline.py"

spec = f"""You are a code worker for the freytag-forge repository at {R}. Boundary: NO model call, NO network call, never git commit. Never edit {FROZEN_TEST} (frozen; hash checked), anything under {R}/storygame, {R}/packages, {R}/bench, {R}/docs, or {R}/tests/fixtures. You may edit these story files: {S}/pacing.yaml, {S}/storylet-routes.yaml, {S}/storylets.md, {S}/plot.md. You may create {NEW_TEST} and edit existing tests under {R}/tests ONLY to change pinned turn numbers or scene-window numbers (never to loosen what a test asserts about behavior).

BACKGROUND. Scene 1A felt hurried. Brandon decided the new scene 1A clock (turn numbers are turns since scene entry). The engine supports an authored event flag `trailing: true` (storygame/story_package/models.py PacingEvent): a trailing event is skipped before the narrator is called and fires after the player's action, with its verbatim text appended after the story. Read {FROZEN_TEST} and docs/markdown-story-authoring/pacing-and-incidents.md to see it.

THE CHANGE (decided; do not redesign):
1. {S}/pacing.yaml events: patrol_arrives_1a at_turn 6 and `trailing: true`; patrol_enters_1a at_turn 7 and `trailing: true`; officer_presses_1a at_turn 7 (keep its `when` and everything else); patrol_leaves_1a at_turn 10 and `trailing: true`; home_search_narrows_1a at_turn 11; patrol_returns_1a at_turn 13. Add `trailing: true` as a new line directly after the event's `scene_id: 1A` line. Change no text, effect or realization. In the same file the scene window for 1A becomes min_turns 13, nudge_after_turns 14, handoff_after_turns 15 (it is 9, 10, 13 now). The loader requires every event's at_turn <= its scene's min_turns, so min_turns 13 is required. No other scene's window changes.
2. The review list in {S}/storylet-routes.yaml (`pacing_event_review`) must stay consistent with the new events: home_search_narrows_1a at_turn 11 there too; read the loader (storygame/story_package/loader.py) and the neighbor entries to see how that list is cross-checked, and update only what is required. The storylet SL-1A-C (The Welfare Check Feels Like a Search) window changes from earliest 4, target 6, latest 7 to earliest 6, target 8, latest 9 everywhere it is stated (storylet-routes.yaml AND storylets.md; find every occurrence of the three numbers for that storylet in both files). Do not change any other storylet window.
3. {S}/plot.md: the 1A row of the pacing contract table: turn ceiling 13 becomes 15 (leave its rhythm text). The sentence 'The story is built for a maximum of 120 accepted player turns.' becomes '... a maximum of 122 accepted player turns.'. The two tests that define AUTHORED_TURN_BUDGET = 120 (tests/test_game_path_journeys.py and tests/test_evidence_gap_journeys.py) become 122. Nothing else in plot.md changes (ChatGPT Desktop owns story prose).
4. Create {NEW_TEST} (tests first for the new timeline; the shipped package is the subject). Use the stubbed-urlopen pattern in tests/test_1a_patrol.py and the canonical neutral commands used there; drive scene 1A turn by turn with a neutral narrator reply, and at each narrator request record world_for(package, state.facts).parent('patrol_officer'). Assert: the package's 1A window is (13, 14, 15); event at_turn values are arrive 6, enter 7, leave 10, narrows 11, returns 13 and arrive/enter/leave are trailing; the arrival text 'A federal emergency patrol pulls up outside Michelle's house. Two officers get out. One walks to the front door. The other looks over the street.' is appended on turn 6, the entering text on turn 7, 'The patrol pulls away from the curb.' on turn 10 (each exactly once, last segment); the officer parent at the turn-7 request is 'outside_house', at the turn-8, 9 and 10 requests 'kitchen', and at the turn-11 request 'patrol_staging'; the narrows text on turn 11 and 'The patrol is coming back to the house.' on turn 13. If a turn's commands are rejected or clarified, choose commands that are accepted (read test_1a_patrol.py).
5. Existing tests that pin the OLD numbers must be updated to the NEW timeline with the same intent (for example tests/test_1a_patrol.py, tests/test_1a_officer_press.py, tests/test_scene_relative_pacing.py, tests/test_pacing_handoff.py, tests/test_canon_journey.py, tests/test_scene_progression_phase4.py, tests/test_scene_roleplay_contract.py and whatever else fails). Discover them by running the full suite after your data edits. Do not delete a test; do not weaken a behavior assertion; if a test cannot be adapted without changing what it proves, stop and describe it in {D}/clock-notes.txt (you may create that file) instead.
HOW TO RUN (from {R}; never bare python, never uv): `TMPDIR=/tmp PYTHONPATH={R}:{R}/packages/worldkeeper/src {PY} -m pytest -q --no-cov -p no:cacheprovider -n 4 2>&1 | tail -40` (full suite, several minutes; you may first run single files); `{PY} -m ruff format <changed py files> && {PY} -m ruff check <changed py files>`."""

check = f"""set -o pipefail
cd {R}
export TMPDIR=/tmp PYTHONPATH={R}:{R}/packages/worldkeeper/src
[ "$(sha256sum {FROZEN_TEST} | cut -d' ' -f1)" = "{FROZEN_SHA}" ] || {{ echo 'frozen test file was modified'; exit 1; }}
git diff --name-only | grep -v -E '^(storygame/story_package/models.py|storygame/runtime/engine.py|docs/markdown-story-authoring/pacing-and-incidents.md|docs/testing-runbook/prompt-inspection.md|data/stories/continuity-initiative/(pacing.yaml|storylet-routes.yaml|storylets.md|plot.md)|tests/[A-Za-z0-9_]+\\.py)$' && {{ echo 'unexpected tracked file changed'; exit 1; }}
git diff -U0 -- data/stories/continuity-initiative/pacing.yaml data/stories/continuity-initiative/plot.md | grep -E '^[+-][^+-]' | head -60
{PY} -m ruff check tests storygame
{PY} -m ruff format --check tests/test_1a_pacing_timeline.py
{PY} -m pytest tests/test_1a_pacing_timeline.py tests/test_trailing_pacing_events.py -q --no-cov -p no:cacheprovider 2>&1 | tail -8
{PY} -m pytest -q --no-cov -p no:cacheprovider -n 4 2>&1 | tail -25
"""

task = {
    "key": "retime-1a-clock",
    "task_type": "code-feature",
    "engine": "codex",
    "model": "gpt-5.6-luna",
    "engine_args": ["-c", "model_reasoning_effort=medium"],
    "max_attempts": 2,
    "timeout_s": 3600,
    "check_timeout_s": 2400,
    "ownership": [
        f"{S}/pacing.yaml",
        f"{S}/storylet-routes.yaml",
        f"{S}/storylets.md",
        f"{S}/plot.md",
        NEW_TEST,
        f"{R}/tests/",
        f"{D}/clock-notes.txt",
    ],
    "expect_files": [NEW_TEST, f"{S}/pacing.yaml"],
    "spec": spec,
    "check": check,
    "verified": "new 1A timeline test and the full suite pass with the retimed clock, frozen tests untouched, only expected files changed",
}
manifest = {
    "run_name": "retime-1a-clock",
    "workdir": "/home/bcorfman/dev/ringer-work/retime-1a-clock",
    "max_parallel": 1,
    "worktrees": False,
    "repo": R,
    "tasks": [task],
}
Path(f"{D}/clock-manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")
print("written")
