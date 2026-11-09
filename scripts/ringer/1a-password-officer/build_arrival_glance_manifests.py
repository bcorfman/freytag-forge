# ruff: noqa: E501
"""Build the two Ringer manifests for plan Round 2e: Kristin perceives the kitchen on arrival. Tests first, then data."""

import json
from pathlib import Path

R = "/home/bcorfman/dev/freytag-forge"
D = f"{R}/scripts/ringer/1a-password-officer"
PY = f"{R}/.venv/bin/python"
PKG = f"{R}/data/stories/continuity-initiative"
TEST = f"{R}/tests/test_1a_arrival_glance.py"
ENV = f"export TMPDIR=/tmp PYTHONPATH={R}:{R}/packages/worldkeeper/src"

OLD_ENTRY_END = "She found the back door forced and let herself into the kitchen."
GLANCE = "The kitchen was wrong at a glance. Michelle's chair lay tipped over at her workstation across the room, and her tablet and work bag were nowhere in sight. A mug sat on the workstation beside a stack of manuscript pages. The calendar and the lake photograph hung by the refrigerator, where they always had. Kristin was too frantic to read any of it yet. She called Michelle's name."
STEADY_TEXT = "Kristin makes herself stop and look properly. Michelle's phone is still here, undamaged. Then she sees the back door. The splinters around the frame point outward, away from the house. A door forced from outside would splinter inward. Someone broke this one from inside to make it look like a break-in. It looks staged."
CUE = "Kristin's initials, KMS, are carved into a drawer of Michelle's workstation."
HOUSE = "The rest of the house is quiet. Michelle is not in it."

DESIGN = f"""DESIGN (approved by Brandon, plan Round 2e in {R}/.plans/1a-password-and-officer-plan.md; read that section for the diagnosis). Problem: in scene 1A Kristin starts in the kitchen but the room is only described when the player asks, the workstation drawer hint appears before the workstation was ever mentioned, and the back-door clue arrives three turns in. Four changes, all story data:

P1. ARRIVAL GLANCE in the authored opening. In {PKG}/plot.md the 1A front matter key entry_text ends today with the sentence "{OLD_ENTRY_END}" followed by the escaped paragraph break. Keep every existing byte, then add a SECOND paragraph (separated by the same escaped paragraph break the field already ends with) whose text is EXACTLY: {GLANCE}  The field must still end with the escaped paragraph break like today. It names only what is visible from the doorway and states no meaning: it must contain none of these words (case-insensitive): splinter, outward, lukewarm, warm, glasses, Saturday, birthday, KMS, initials, carved, gap, drawer, phone, card, deadbolt. Add one sentence to the plot.md 1A.1 prose saying that Kristin takes in the room at a glance on arrival but is too frantic to read it yet, and that a few turns in, once she steadies herself, she reads the back door properly.

P2. NO FIRST-TURN DEDUCTION FROM ORIENTING COMMANDS, a timed beat instead. Do NOT change action_evidence or any field of knowledge record k_sl_1a_a_r1 or storylet SL-1A-A (examining the kitchen or the back door still earns the deduction as today). Orienting commands ('Look around.', 'Examine the room.', 'Search the house for Michelle.', 'Call out for Michelle.') must still NOT earn it. Add ONE new pacing event to {PKG}/pacing.yaml, place it FIRST in the events list, before patrol_arrives_1a. Fields: id kristin_steadies_1a, scene_id 1A, trailing true, at_turn 3, when [michelle_abduction_suspicion equals false], effects [michelle_abduction_suspicion equals true], one realization with verbatim true and text EXACTLY: {STEADY_TEXT}  It fires once at turn 3 if the player has not already earned the deduction (by examining the door or kitchen); it never fires after the deduction was earned. Mirror it in the pacing_event_review list of {PKG}/storylet-routes.yaml directly after the reyes_rams_drawer_1a entry: event_id kristin_steadies_1a, scene_id 1A, at_turn 3, effect assert michelle_abduction_suspicion true, status approved, reason 'Lets Kristin read the forced back door once the first shock passes, without naming who broke in.' If any loader rule requires more (check how reyes_rams_drawer_1a is declared everywhere: grep for it under {PKG}, {R}/storygame and {R}/docs), mirror it.

P3. DRAWER HINT WITHOUT THE GAP. In {PKG}/handoffs.yaml the cue_text of the scene-1A delivery (fact continuity_initiative_known) becomes EXACTLY: {CUE}  (the gap sentences are dropped: the gap is found only by opening then closing the drawer, per Round 2c). Nothing else in that delivery changes.

P4. THE REST OF THE HOUSE. In {PKG}/plot.md the 1A front matter setting_facts list gets a THIRD line, appended after the two existing lines, EXACTLY: {HOUSE}  Add the sentence 'The rest of the house is quiet and empty; Michelle is not in it.' to plot.md 1A.1 prose.

BUDGET (hard rule): tests/test_audit_budget.py::test_real_package_ratchet and tests/fixtures/deep_turn_budget.json must stay UNCHANGED and pass; scene 1A measures about 5330 / 5556 against pins 5485 / 5597 and the P4 line costs about 55 characters. If the ratchet fails, report the numbers in {R}/bench/results/1a-passcode-round2/arrival-glance-budget.txt and stop; never edit the fixture, the test or the limits."""

tests_spec = f"""You are a test-writing worker for the freytag-forge repository at {R}. Boundary: NO model call, NO network call, never git commit. You own ONLY {TEST} (create). Edit nothing else.

{DESIGN}

Read {R}/tests/test_1a_patrol.py first and copy its _Response class, its monkeypatch of storygame.runtime.cloudflare.urlopen, its RuntimeEngine/CloudflareTurnProvider construction and its helpers (_texts, _has_fact). Read {R}/tests/test_1a_kitchen_start.py (PACKAGE loading) and {R}/.plans/1a-password-and-officer/replay_first_commands.py (how a first command is run offline). Package access: PACKAGE.scenes[0].metadata.entry_text and .setting_facts; PACKAGE.pacing.events; PACKAGE.deliveries (the scene-1A one has cue_text); pacing_event_review is in PACKAGE.storylet_routes (find the attribute by reading storygame/story_package/models.py).
WRITE THESE TESTS, exact names:
1. test_entry_text_keeps_the_old_opening_and_adds_the_glance: entry_text starts with the previous opening (everything up to and including '{OLD_ENTRY_END}'), then contains the GLANCE text exactly, and still ends with a paragraph break.
2. test_the_glance_names_the_room_and_withholds_every_meaning: the glance paragraph contains 'workstation', 'chair', 'tablet', 'calendar' and none of the withheld words listed in P1 (case-insensitive), and the WHOLE entry_text contains neither 'phone' nor 'drawer' nor 'KMS' (the kitchen-start test forbids a phone mention).
3. test_kristin_steadies_event_is_declared: the exact event in P2 (id, scene, trailing, at_turn, both predicates, effect, verbatim True, text equal to the STEADY text) and the pacing_event_review entry with status approved.
4. test_kristin_steadies_at_turn_three_when_nothing_earned_it: drive the real engine with a neutral stub narrator and three 'Wait and observe.' commands; the STEADY text is absent from turns 1 and 2, is the LAST segment of turn 3 and appears once; michelle_abduction_suspicion is true afterwards.
5. test_examining_the_door_early_earns_the_deduction_and_the_beat_stays_silent_control: first command 'Inspect the back door.' then two 'Wait and observe.': the splinter sentence ('The splinters around the frame point outward') appears exactly once across the three turns and the STEADY text never appears.
6. test_orienting_commands_do_not_earn_the_deduction_on_turn_one_control: for 'Look around.', 'Examine the room.', 'Search the house for Michelle.', 'Call out for Michelle.' as a fresh first command, no segment of turn 1 contains 'splinters'.
7. test_the_drawer_hint_names_only_the_carving: the scene-1A delivery cue_text equals '{CUE}' exactly and contains neither 'gap' nor 'lower edge'; and for a fresh first command 'Look around.' the composed turn contains that cue text but no 'gap'.
8. test_the_workstation_is_named_in_the_opening_before_the_hint: 'workstation' appears in entry_text, and for a fresh 'Look around.' turn the cue is the last segment (it follows the narrator's prose).
9. test_setting_facts_gain_the_house_line: setting_facts equals exactly ('Sirens carry from the next street.', 'A dog barks behind the empty house next door.', '{HOUSE}').
10. test_the_house_line_reaches_the_narrator_on_a_house_search: capture the request body of the narrator call for the command 'Search the house for Michelle.' (stub urlopen records request.data) and assert the body contains '{HOUSE}'.
11. test_scene_1a_budget_pins_are_untouched_control: tests/fixtures/deep_turn_budget.json scene 1A has narration_chars 5485 and narration_chars_all_alternates 5597.
Tests 1, 3, 4, 7, 9, 10 must FAIL against today's data for the right reason. Test 2 may pass vacuously on the withheld words today; make it also assert the glance words so it fails today. Tests 5, 6, 8 (its cue-last half passes today; keep the 'workstation in entry_text' half so it fails today) and 11 describe unchanged behaviour: 5, 6 and 11 carry the _control suffix already and may PASS today. Fix any test failing for an unrelated reason (ImportError, SyntaxError, NameError, fixture bug).
HOW TO RUN (from {R}; never bare python, never uv): `{ENV} {PY} -m pytest {TEST} -q -p no:cacheprovider -rA 2>&1 | tail -40`; format with `{PY} -m ruff format {TEST} && {PY} -m ruff check {TEST}`. Do not make the failing tests pass; that is the next task."""

names_fail = [
    "test_entry_text_keeps_the_old_opening_and_adds_the_glance",
    "test_the_glance_names_the_room_and_withholds_every_meaning",
    "test_kristin_steadies_event_is_declared",
    "test_kristin_steadies_at_turn_three_when_nothing_earned_it",
    "test_the_drawer_hint_names_only_the_carving",
    "test_the_workstation_is_named_in_the_opening_before_the_hint",
    "test_setting_facts_gain_the_house_line",
    "test_the_house_line_reaches_the_narrator_on_a_house_search",
]

tests_check = f"""set -o pipefail
cd {R}
{ENV}
{PY} -m ruff check {TEST}
{PY} -m ruff format --check {TEST}
{PY} -m pytest {TEST} -q -p no:cacheprovider -rA > /tmp/arrival-glance-red.txt 2>&1
{PY} - <<'PY'
import re, sys
text = open('/tmp/arrival-glance-red.txt').read()
status = dict((m.group(2), m.group(1)) for m in re.finditer(r'^(PASSED|FAILED|ERROR) \\S+::(\\w+)', text, re.M))
bad = [f'{{n}}: expected FAILED, got {{status.get(n)}}' for n in {names_fail!r} if status.get(n) != 'FAILED']
bad += [f'{{n}}: control expected PASSED, got {{s}}' for n, s in status.items() if n.endswith('_control') and s != 'PASSED']
if 'ERROR' in status.values() or re.search(r'ImportError|ModuleNotFoundError|SyntaxError|NameError|collection error', text):
    bad.append('errors or import/syntax/name problems present')
print(text[-3000:])
if bad:
    print('RED-CHECK FAILED'); [print(' -', b) for b in bad]; sys.exit(1)
print('RED-CHECK OK')
PY
"""

OLD_TESTS = [
    "test_1a_kitchen_start.py",
    "test_1a_drawer_words.py",
    "test_1a_drawer_close_gap.py",
    "test_drawer_gap_nudge.py",
    "test_1a_gap_pointer.py",
    "test_drawer_avoidance_repro.py",
    "test_1a_back_door_gap.py",
    "test_1a_officer_press.py",
    "test_1a_patrol.py",
    "test_1a_pacing_timeline.py",
    "test_1a_phone_thread.py",
    "test_invitation_report.py",
    "test_markdown_story_package.py",
    "test_place_scoped_feed.py",
    "test_trailing_pacing_events.py",
    "test_pacing_handoff.py",
    "test_scene_relative_pacing.py",
    "test_canon_journey.py",
    "test_scene_progression_phase4.py",
    "test_richer_1a_fixes.py",
    "test_audit_budget.py",
    "test_narration_corpus.py",
    "test_game_path_completion.py",
]
old_paths = " ".join(f"tests/{n}" for n in OLD_TESTS)

data_spec = f"""You are a story-data worker for the freytag-forge repository at {R}. Boundary: NO model call, NO network call, never git commit. Do NOT edit {TEST} (the failing tests written for this change): make them pass. You own these data files: {PKG}/plot.md, {PKG}/pacing.yaml, {PKG}/storylet-routes.yaml, {PKG}/handoffs.yaml. Earlier tasks changed these same files (phone thread SL-1A-J, drawer open-then-close, the pacing event reyes_rams_drawer_1a): leave all of that byte-identical. You may also edit these existing tests, ONLY where an assertion fails solely because of the four changes in the DESIGN (the entry text now ends with the glance instead of 'let herself into the kitchen.'; the drawer cue no longer mentions the gap; setting_facts has three lines; a new turn-3 event appends text to scene-1A turn 3): {", ".join(OLD_TESTS)} (all under {R}/tests). Update such assertions narrowly (for example test_1a_entry_text_ends_with_kitchen_entry should now assert the entry text CONTAINS that sentence and ends with the glance's last sentence; test_1a_handoff_cue_mentions_lower_edge_gap should now assert the cue is the carving sentence with no gap); never weaken or delete an assertion that still holds, and never edit any other test, engine, doc or data file. A journey test that counts turn-3 segments or compares a whole scene-1A transcript may need the new turn-3 text added to its expectation: do that narrowly.

{DESIGN}

DO THIS. Read first {TEST}, the 1A front matter of {PKG}/plot.md (entry_text, setting_facts) and the 1A.1 prose, {PKG}/pacing.yaml (first events), the pacing_event_review block of {PKG}/storylet-routes.yaml, and the scene-1A delivery in {PKG}/handoffs.yaml. Implement the DESIGN exactly. Straight apostrophes as in neighbouring text; in the YAML double-quoted entry_text keep the existing escaping (\\n\\n) style.
HOW TO RUN (from {R}; never bare python, never uv): `{ENV} {PY} -m pytest {TEST} -q -p no:cacheprovider 2>&1 | tail -25`, then `{ENV} {PY} -m pytest {old_paths} -q -p no:cacheprovider -x 2>&1 | tail -40`. Fix data or the listed old tests until all pass. If a test NOT in the listed files fails because of this change, do not edit it: write its exact name and failure to {R}/bench/results/1a-passcode-round2/arrival-glance-pin-failures.txt and stop."""

data_check = f"""set -o pipefail
cd {R}
{ENV}
{PY} -m pytest {TEST} -q -p no:cacheprovider 2>&1 | tail -20
{PY} -m pytest {old_paths} -q -p no:cacheprovider 2>&1 | tail -30
{PY} -m ruff check tests && {PY} -m ruff format --check tests
"""


def manifest(name, key, task_type, spec, check, owned, expect, timeout, verified):
    task = {
        "key": key,
        "task_type": task_type,
        "engine": "codex",
        "model": "gpt-5.6-luna",
        "engine_args": ["-c", "model_reasoning_effort=medium"],
        "max_attempts": 2,
        "timeout_s": timeout,
        "check_timeout_s": 1800,
        "ownership": owned,
        "expect_files": expect,
        "spec": spec,
        "check": check,
        "verified": verified,
    }
    return {
        "run_name": f"1a-arrival-glance-{name}",
        "workdir": f"/home/bcorfman/dev/ringer-work/1a-arrival-glance-{name}",
        "max_parallel": 1,
        "worktrees": False,
        "repo": R,
        "tasks": [task],
    }


tests_m = manifest(
    "tests",
    "write-arrival-glance-tests",
    "test-hardening",
    tests_spec,
    tests_check,
    [TEST],
    [TEST],
    1800,
    "the new arrival-glance tests fail against today's data for the right reason",
)
files = [f"{PKG}/{n}" for n in ("plot.md", "pacing.yaml", "storylet-routes.yaml", "handoffs.yaml")] + [
    f"{R}/tests/{n}" for n in OLD_TESTS
]
data_m = manifest(
    "data",
    "add-arrival-glance",
    "code-feature",
    data_spec,
    data_check,
    files,
    files[:4],
    3000,
    "the arrival-glance tests and the old scene-1A suites pass",
)
for name, m in (("tests", tests_m), ("data", data_m)):
    path = Path(D) / f"arrival-glance-{name}-manifest.json"
    path.write_text(json.dumps(m, indent=2) + "\n")
    print(path)
