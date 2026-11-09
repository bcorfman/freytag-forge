# ruff: noqa: E501
"""Build the two Ringer manifests for plan Round 2c: the drawer gap is found only after the drawer is opened and then closed. Tests first, then data."""

import json
from pathlib import Path

R = "/home/bcorfman/dev/freytag-forge"
D = f"{R}/scripts/ringer/1a-password-officer"
PY = f"{R}/.venv/bin/python"
PKG = f"{R}/data/stories/continuity-initiative"
TEST = f"{R}/tests/test_1a_drawer_close_gap.py"
ENV = f"export TMPDIR=/tmp PYTHONPATH={R}:{R}/packages/worldkeeper/src"
RAM_TEXT = "Reyes tugs at the workstation drawer. It sticks. Frustrated, he rams it back into place with the heel of his hand, and it sits high in its frame. A thin gap shows beneath its lower edge, wide enough for Kristin's fingers. Reyes never looks down. Only Kristin sees it."
CLOSE_TEXT = "Kristin slides the drawer shut. It rides high in its frame. A thin gap beneath its lower edge is wide enough for Kristin's fingers."
OPEN_TEXT = "The drawer slides out. It holds a stapler, spare batteries, pens, and binder clips."

DESIGN = f"""DESIGN (approved by Brandon). Today scene 1A points Kristin to the thin gap beneath the workstation drawer as soon as she OPENS it (records k_sl_1a_f_r1 and k_sl_1a_b_r0w) or EXAMINES it (k_sl_1a_f_r2), all under storylet SL-1A-F, each establishing drawer_gap_pointed_out. New rule: the gap is found only after the drawer has been opened and then closed again.
- Opening the drawer (k_sl_1a_f_r1 and k_sl_1a_b_r0w) now replies with the contents only, delivery_text EXACTLY: {OPEN_TEXT}  Their statement fields drop the gap. They establish a NEW fact drawer_opened true and no longer establish drawer_gap_pointed_out. Their requires, reach, action_evidence and every other field stay as they are.
- NEW record k_sl_1a_f_r3 (realization SL-1A-F-R3 of SL-1A-F): closing the drawer. earn_when: closes or shuts the drawer. action_evidence groups: [close, shut, push in, push back, slide in, slide shut, push closed, push it closed] AND [drawer]. requires drawer_opened equals true AND memory_card_recovered equals false. Establishes drawer_gap_pointed_out true. voiceable false, reach_entity_ids [michelle_drawer], entity_ids [kristin, michelle_drawer], same audience, available_in_scenes [1A], relevance as k_sl_1a_f_r2. delivery_text EXACTLY: {CLOSE_TEXT}
- k_sl_1a_f_r2 (bare examine/inspect/look at the drawer, repeatable) now ALSO requires drawer_gap_pointed_out equals true (keep its existing memory_card_recovered false requirement): it only repeats the gap after Kristin has found it; before that, examining the drawer earns no authored reply.
- k_sl_1a_b_r0 (search under or beneath the drawer, finds the card) is UNCHANGED.
- New fact drawer_opened: "Kristin has opened Michelle's workstation drawer." Declared in the knowledge.yaml facts list, the world.yaml facts list and storylet-routes.yaml new_fact_ids (used_by_storylets [SL-1A-F]). SL-1A-F gets a third realization option SL-1A-F-R3 asserting drawer_gap_pointed_out true; its R1 operation list changes to assert drawer_opened true (not drawer_gap_pointed_out). 
- SAFETY NET, a new pacing event in pacing.yaml (same shape as patrol_enters_1a and officer_presses_1a): id reyes_rams_drawer_1a, scene_id 1A, trailing true, at_turn 8, when [patrol_in_house equals true, drawer_gap_pointed_out equals false, memory_card_recovered equals false], effects [drawer_gap_pointed_out equals true], one realization with verbatim true and text EXACTLY: {RAM_TEXT}  It fires once on the first eligible turn from turn 8 (the patrol is in the kitchen on turns 7 to 10). It does not fire if Kristin already found the gap by opening and closing the drawer, or already has the card. It states no purpose for Reyes and never says he finds the card. Add the event to the pacing event review list wherever the other 1A events are listed (find where officer_presses_1a is mentioned outside pacing.yaml and mirror it).
- BUDGET (a hard rule): tests/test_audit_budget.py::test_real_package_ratchet and tests/fixtures/deep_turn_budget.json must stay UNCHANGED and must pass. The phone-thread task left scene 1A over its pin (narration_chars 5750 vs 5485; all-alternates over its pin too). Cause found: the statement of k_sl_1a_j_r2 names Officer Reyes, which pulls his whole biography line into the audit prompt, and k_sl_1a_j_r1 and r2 set the same fact so both statements count at once. Fix: (a) k_sl_1a_j_r2 and k_sl_1a_j_r3 and r1 get terse statements with no character name besides Kristin and Michelle, each under 45 characters, for example r1 "Kristin read Michelle's 4:07am text.", r2 "Kristin read the text with the officer near.", r3 "Kristin saw her unanswered calls."; (b) k_sl_1a_j_r2 also establishes a NEW fact reyes_watched_text true in addition to michelle_text_read (declare it in the knowledge.yaml facts list, world.yaml facts and storylet-routes new_fact_ids with used_by_storylets [SL-1A-J], and in SL-1A-J-R2 operations) so it is not counted in the one-per-storylet audit state; (c) the drawer records' statements drop the gap clause (k_sl_1a_f_r1 and k_sl_1a_b_r0w: "Kristin opens the drawer."); (d) if the ratchet still fails, shorten the wording of other scene-1A knowledge statements minimally without changing their meaning or must_convey, and record every change (record id, before, after) in {R}/bench/results/1a-passcode-round2/budget-trims.txt. Never edit the fixture, the test, or the limits. Delivery texts stay exactly as specified.
- The storylets.md SL-1A-F section and the plot.md 1A.1/1A.2 drawer sentences are reworded to match: opening shows the contents, closing is when Kristin finds the thin gap."""

tests_spec = f"""You are a test-writing worker for the freytag-forge repository at {R}. Boundary: NO model call, NO network call, never git commit. You own ONLY {TEST} (create). Edit nothing else.

{DESIGN}

Read {R}/tests/test_drawer_gap_nudge.py first and copy its helpers and imports (_state_at from tests.test_observation_mode, KnowledgeProjector, uniquely_matched_authored_handoff, Fact, load_story_package, the _handoff and _gap_state helpers). Set facts with state.facts.assert_fact(Fact(predicate=..., subject='story', value='true')) like those tests do.
WRITE THESE TESTS, exact names:
1. test_opening_the_drawer_shows_contents_and_no_gap: delivery_text of k_sl_1a_f_r1 and k_sl_1a_b_r0w equals the OPEN text above; neither contains 'gap' or 'lower edge'; both establish drawer_opened true; neither establishes drawer_gap_pointed_out.
2. test_closing_the_drawer_after_opening_finds_the_gap: drawer_opened true, memory_card_recovered false: the handoff for each of 'Close the drawer.', 'Shut the drawer.', 'Push the drawer closed.' is k_sl_1a_f_r3, whose delivery_text equals the CLOSE text above and which establishes drawer_gap_pointed_out true.
3. test_closing_without_opening_finds_nothing: drawer_opened false: k_sl_1a_f_r3 is not the handoff for 'Close the drawer.' and is not among the projection candidates.
4. test_closing_after_the_card_is_recovered_finds_nothing: drawer_opened true and memory_card_recovered true: k_sl_1a_f_r3 not offered.
5. test_bare_examine_gives_no_gap_before_the_drawer_is_closed: for each of the eight BARE_DRAWER_COMMANDS in tests/test_drawer_gap_nudge.py, with drawer_gap_pointed_out false k_sl_1a_f_r2 is not the handoff; with drawer_gap_pointed_out true it is.
6. test_searching_under_the_drawer_still_finds_the_card: 'Search under the drawer.' and 'Feel beneath the drawer.' give k_sl_1a_b_r0 with drawer_opened false (the card stays findable without the nudge).
7. test_drawer_opened_is_declared_everywhere_and_the_storylet_has_three_realizations: drawer_opened appears in the package knowledge facts, world facts and routes new_fact_ids; SL-1A-F realization ids are exactly [SL-1A-F-R1, SL-1A-F-R2, SL-1A-F-R3].
8. test_reyes_rams_the_drawer_event_is_declared: package.pacing.events contains reyes_rams_drawer_1a with scene_id 1A, trailing True, at_turn 8, the three when predicates above, the effect above, and a verbatim realization text equal to the RAM text above; the text contains no 'card' (case-insensitive).
9. test_reyes_rams_the_drawer_when_nobody_found_the_gap: drive the real engine through scene 1A with the same stubbed provider style as {R}/tests/test_trailing_pacing_events.py (copy its prefix of 7 commands and its recording of the officer parent at each narrator request); at turn 8 with drawer_gap_pointed_out false and the card not recovered: reyes_rams_drawer_1a is in state.fired_event_ids, drawer_gap_pointed_out is true afterwards, the RAM text is the LAST segment and appears once, and the officer parent at that turn's narrator request is 'kitchen'.
10. test_reyes_does_not_ram_the_drawer_after_the_gap_is_found_control: same drive, but assert drawer_gap_pointed_out true before turn 8: the event is NOT fired and its text does not appear.
11. test_reyes_does_not_ram_the_drawer_before_turn_8_control: at turns 5, 6 and 7 the event is not in fired_event_ids.
12. test_scene_1a_budget_pins_are_untouched_control: tests/fixtures/deep_turn_budget.json scene 1A has narration_chars 5485 and narration_chars_all_alternates 5597 (unchanged pins).
Tests 1, 2, 3, 5, 8, 9 (the with-flag half), 7 must FAIL against today's data for the right reason. Tests 4, 6, 10, 11 and 12 describe unchanged-or-vacuous behaviour and may PASS today; give each the suffix _control in the function name (already done for 10, 11, 12) (test_closing_after_the_card_is_recovered_finds_nothing_control and test_searching_under_the_drawer_still_finds_the_card_control). Test 3 may pass vacuously today (no r3 exists): make it assert something that fails today (for instance that the r3 record exists and drawer_opened gates it). Fix any test failing for an unrelated reason (ImportError, SyntaxError, NameError, fixture bug).
HOW TO RUN (from {R}; never bare python, never uv): `{ENV} {PY} -m pytest {TEST} -q -p no:cacheprovider -rA 2>&1 | tail -40`; format with `{PY} -m ruff format {TEST} && {PY} -m ruff check {TEST}`. Do not make the failing tests pass; that is the next task."""

names_fail = [
    "test_reyes_rams_the_drawer_event_is_declared",
    "test_reyes_rams_the_drawer_when_nobody_found_the_gap",
    "test_opening_the_drawer_shows_contents_and_no_gap",
    "test_closing_the_drawer_after_opening_finds_the_gap",
    "test_closing_without_opening_finds_nothing",
    "test_bare_examine_gives_no_gap_before_the_drawer_is_closed",
    "test_drawer_opened_is_declared_everywhere_and_the_storylet_has_three_realizations",
]

tests_check = f"""set -o pipefail
cd {R}
{ENV}
{PY} -m ruff check {TEST}
{PY} -m ruff format --check {TEST}
{PY} -m pytest {TEST} -q -p no:cacheprovider -rA > /tmp/drawer-close-red.txt 2>&1
{PY} - <<'PY'
import re, sys
text = open('/tmp/drawer-close-red.txt').read()
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
    "test_drawer_gap_nudge.py",
    "test_1a_gap_pointer.py",
    "test_drawer_avoidance_repro.py",
    "test_reveal_reach.py",
    "test_cue_spent_reveal.py",
    "test_negation_scope.py",
    "test_discovery_continuity.py",
    "test_recent_cue_unit.py",
    "test_recent_cue_reference.py",
    "test_command_split_negation.py",
    "test_voiceable_knowledge.py",
    "test_knowledge_projection.py",
    "test_1a_back_door_gap.py",
    "test_1a_officer_press.py",
    "test_place_scoped_feed.py",
    "test_concealment_repro.py",
    "test_enforce_report_t9c.py",
    "test_enforce_report_t9d.py",
    "test_narration_safety_false_positives.py",
    "test_markdown_story_package.py",
    "test_1a_pacing_timeline.py",
    "test_1a_patrol.py",
    "test_pacing_handoff.py",
    "test_scene_relative_pacing.py",
    "test_canon_journey.py",
    "test_scene_progression_phase4.py",
    "test_trailing_pacing_events.py",
    "test_1a_phone_thread.py",
]
old_paths = " ".join(f"tests/{n}" for n in OLD_TESTS)

data_spec = f"""You are a story-data worker for the freytag-forge repository at {R}. Boundary: NO model call, NO network call, never git commit. Do NOT edit {TEST} (the failing tests written for this change): make them pass. You own these data files: {PKG}/knowledge.yaml, {PKG}/storylet-routes.yaml, {PKG}/storylets.md, {PKG}/world.yaml, {PKG}/plot.md, {PKG}/pacing.yaml (only to add the one new event). A previous task already added storylet SL-1A-J and records k_sl_1a_j_r1..r3 and facts michelle_text_read and kristin_calls_read to these same files: leave all of that byte-identical. You may also edit these existing tests, ONLY where an assertion fails solely because opening or examining the drawer no longer carries the gap sentence (they pin the behaviour Brandon is replacing; tests/test_1a_phone_thread.py only where an assertion fails solely because of the statement/fact changes in BUDGET (b)): {", ".join(OLD_TESTS)} (all under {R}/tests). Update such assertions narrowly to the new behaviour (opening shows contents, closing finds the gap, bare examine repeats the gap only after it was found); never weaken or delete an assertion that still holds, and never edit any other test, engine, doc or data file.

{DESIGN}

DO THIS. Read first {TEST}, {PKG}/knowledge.yaml (records k_sl_1a_b_r0, k_sl_1a_b_r0w, k_sl_1a_f_r1, k_sl_1a_f_r2, the facts list near line 26), {PKG}/storylet-routes.yaml (the SL-1A-F entry and new_fact_ids), the SL-1A-F section of {PKG}/storylets.md, the facts list in world.yaml, and the drawer paragraphs of plot.md (1A.1 'The drawer rides high in its frame...' and the 1A.2 card paragraph). Implement the DESIGN exactly. Place k_sl_1a_f_r3 immediately after k_sl_1a_f_r2. Keep every other byte unchanged. Straight apostrophes as in neighbouring text.
HOW TO RUN (from {R}; never bare python, never uv): `{ENV} {PY} -m pytest {TEST} tests/test_1a_phone_thread.py -q -p no:cacheprovider 2>&1 | tail -25`, then `{ENV} {PY} -m pytest {old_paths} tests/test_audit_budget.py tests/test_1a_kitchen_start.py tests/test_richer_1a_fixes.py -q -p no:cacheprovider -x 2>&1 | tail -40`. Fix data or the listed old tests until all pass. If a test NOT in the listed files fails because of this change, do not edit it: write its exact name and failure to {R}/bench/results/1a-passcode-round2/drawer-close-pin-failures.txt and stop."""

data_check = f"""set -o pipefail
cd {R}
{ENV}
{PY} -m pytest {TEST} tests/test_1a_phone_thread.py -q -p no:cacheprovider 2>&1 | tail -20
{PY} -m pytest {old_paths} tests/test_audit_budget.py tests/test_1a_kitchen_start.py tests/test_richer_1a_fixes.py -q -p no:cacheprovider 2>&1 | tail -30
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
        "run_name": f"1a-drawer-close-{name}",
        "workdir": f"/home/bcorfman/dev/ringer-work/1a-drawer-close-{name}",
        "max_parallel": 1,
        "worktrees": False,
        "repo": R,
        "tasks": [task],
    }


tests_m = manifest(
    "tests",
    "write-drawer-close-tests",
    "test-hardening",
    tests_spec,
    tests_check,
    [TEST],
    [TEST],
    1800,
    "the new drawer tests fail against today's data for the right reason",
)
files = [
    f"{PKG}/{n}"
    for n in ("storylets.md", "storylet-routes.yaml", "knowledge.yaml", "world.yaml", "plot.md", "pacing.yaml")
] + [f"{R}/tests/{n}" for n in OLD_TESTS]
data_m = manifest(
    "data",
    "add-drawer-close-gap",
    "code-feature",
    data_spec,
    data_check,
    files,
    files[:6],
    3000,
    "the drawer-close and phone-thread tests and the old drawer suites pass",
)
for name, m in (("tests", tests_m), ("data", data_m)):
    path = Path(D) / f"drawer-close-{name}-manifest.json"
    path.write_text(json.dumps(m, indent=2) + "\n")
    print(path)
