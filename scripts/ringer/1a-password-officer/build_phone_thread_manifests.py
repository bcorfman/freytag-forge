# ruff: noqa: E501
"""Build the two Ringer manifests for the 1A phone-thread storylet SL-1A-J (plan Round 2b): failing tests first, then the data edits."""

import json
from pathlib import Path

R = "/home/bcorfman/dev/freytag-forge"
D = f"{R}/scripts/ringer/1a-password-officer"
PY = f"{R}/.venv/bin/python"
PKG = f"{R}/data/stories/continuity-initiative"
TEST = f"{R}/tests/test_1a_phone_thread.py"
ENV = f"export TMPDIR=/tmp PYTHONPATH={R}:{R}/packages/worldkeeper/src"

R1 = "Kristin enters Michelle's passcode, the one she has known for years, and the phone opens on a single text from Michelle, sent at 4:07am: \"Come to the house. Don't call.\""
R2 = (
    R1
    + " Officer Reyes lowers his printed list. His eyes stay on the phone in her hand, and when she looks up he glances away a moment too slowly. Kristin turns the screen toward herself, uneasy."
)
R3 = "Below the text, Kristin's own calls to Michelle fill the log, one after another, and none of them were answered."

DESIGN = f"""DESIGN (approved by Brandon). One new OPTIONAL scene-1A storylet SL-1A-J, "What Michelle's Phone Kept", gives Michelle's phone (entity michelle_phone, on the kitchen floor in 1A) authored contents, revealed in two steps: the 4:07am text first, then Kristin's unanswered calls. Three realizations, each an earned knowledge record with a fixed delivery_text:
- SL-1A-J-R1 (knowledge id k_sl_1a_j_r1): the text, patrol NOT in the house. requires patrol_in_house equals false. Establishes michelle_text_read true. delivery_text EXACTLY: {R1}
- SL-1A-J-R2 (k_sl_1a_j_r2): the same text with an officer tell, patrol IN the house. requires patrol_in_house equals true. Establishes michelle_text_read true. delivery_text EXACTLY: {R2}
- SL-1A-J-R3 (k_sl_1a_j_r3): the calls. requires michelle_text_read equals true (so calls can never come before the text). Establishes kristin_calls_read true. delivery_text EXACTLY: {R3}
New fact ids: michelle_text_read ("Kristin has read Michelle's 4:07am text on her phone.") and kristin_calls_read ("Kristin has seen her own unanswered calls to Michelle on the phone."). Storylet window: earliest_turn 0, target_turn 5, latest_turn 11, activation condition none beyond scene 1A; complete_when kristin_calls_read equals true; abort_when scene_id_not 1A. Protected boundary: no memory card, recording, files, JANUS, Brandon, dead drop, Continuity Initiative, and no stated purpose for the officer (he only watches; Kristin is uneasy). Unlocking must NOT set memory_card_recovered or any card fact."""

tests_spec = f"""You are a test-writing worker for the freytag-forge repository at {R}. Boundary: NO model call, NO network call, never git commit. You own ONLY {TEST} (create). Edit nothing else: no data, engine, doc, or existing test.

{DESIGN}

Read {R}/tests/test_richer_1a_fixes.py first and copy its style (module-level PACKAGE = load_story_package(Path('data/stories/continuity-initiative')); _candidate_ids helper using engine._activate_pacing() and engine.projector.project(state, 'player', command).candidates; uniquely_matched_authored_handoff is imported where tests/test_richer_1a_fixes.py or bench/frozen_prompts.py use it). To set the patrol or text facts build a RuntimeState.bootstrap(PACKAGE) in scene 1A and assert a story fact the way bench/core.py seeded_state_for_scene does (state.facts.assert_fact(Fact(predicate='patrol_in_house', subject='story', value='true'))). Read {R}/data/stories/continuity-initiative/knowledge.yaml records k_sl_1a_g_r1 and k_sl_1a_b_r0 and the SL-1A-G entry in storylet-routes.yaml to see the shapes you are asserting.

WRITE THESE TESTS in {TEST}, exact function names (the check matches names):
1. test_phone_thread_storylet_is_declared: storylet-routes (read via yaml like tests/test_richer_1a_fixes.py) has SL-1A-J, scene_id 1A, realization ids exactly [SL-1A-J-R1, SL-1A-J-R2, SL-1A-J-R3], pacing 0/5/11.
2. test_phone_thread_facts_are_declared_everywhere: michelle_text_read and kristin_calls_read each appear in the package knowledge facts, the world facts, and the routes new_fact_ids.
3. test_the_text_is_offered_when_the_patrol_is_away: patrol_in_house false: the candidate ids for 'Unlock Michelle's phone.' and 'Read the messages on Michelle's phone.' include k_sl_1a_j_r1 and exclude k_sl_1a_j_r2 and k_sl_1a_j_r3.
4. test_the_uneasy_text_is_offered_when_the_officer_is_in_the_kitchen: patrol_in_house true: those same commands include k_sl_1a_j_r2 and exclude k_sl_1a_j_r1 and k_sl_1a_j_r3.
5. test_the_historical_password_command_earns_the_text: patrol away, command 'Type in the password.' includes k_sl_1a_j_r1.
6. test_the_calls_need_the_text_first: with michelle_text_read false, 'Check the call log.' excludes k_sl_1a_j_r3; with michelle_text_read true it includes it.
7. test_delivery_texts_are_exactly_the_approved_lines: delivery_text of r1, r2, r3 equals the strings in the DESIGN above character for character (copy them from that section).
8. test_the_text_variants_establish_the_text_fact_and_nothing_about_the_card: r1 and r2 establish michelle_text_read true; r3 establishes kristin_calls_read true; none of the three establishes memory_card_recovered, continuity_initiative_known, michelle_warning_known or michelle_lead_actionable.
9. test_the_phone_thread_leaks_no_protected_material: lowercase delivery texts of all three contain none of: 'memory card', 'recording', 'janus', 'brandon', 'dead drop', 'continuity initiative', 'removable media'.
10. test_the_officer_text_is_not_voiceable: all three records have voiceable false and reach_entity_ids containing michelle_phone.
Because the data does not exist yet, every test must FAIL against today's data for the right reason (missing storylet, fact or record: KeyError, StopIteration or an assertion on the missing id are fine as long as the failure is not an ImportError, SyntaxError, NameError or a fixture bug). Fix any test that fails for another reason. Keep the file compact with shared helpers. Straight apostrophes exactly as written in commands.
HOW TO RUN (from {R}; never bare python, never uv): `{ENV} {PY} -m pytest {TEST} -q -p no:cacheprovider -rA 2>&1 | tail -40`; format with `{PY} -m ruff format {TEST} && {PY} -m ruff check {TEST}`. Do not make the tests pass; that is the next task."""

names = [
    "test_phone_thread_storylet_is_declared",
    "test_phone_thread_facts_are_declared_everywhere",
    "test_the_text_is_offered_when_the_patrol_is_away",
    "test_the_uneasy_text_is_offered_when_the_officer_is_in_the_kitchen",
    "test_the_historical_password_command_earns_the_text",
    "test_the_calls_need_the_text_first",
    "test_delivery_texts_are_exactly_the_approved_lines",
    "test_the_text_variants_establish_the_text_fact_and_nothing_about_the_card",
    "test_the_phone_thread_leaks_no_protected_material",
    "test_the_officer_text_is_not_voiceable",
]

tests_check = f"""set -o pipefail
cd {R}
{ENV}
{PY} -m ruff check {TEST}
{PY} -m ruff format --check {TEST}
{PY} -m pytest {TEST} -q -p no:cacheprovider -rA > /tmp/phone-thread-red.txt 2>&1
{PY} - <<'PY'
import re, sys
text = open('/tmp/phone-thread-red.txt').read()
status = dict((m.group(2), m.group(1)) for m in re.finditer(r'^(PASSED|FAILED|ERROR) \\S+::(\\w+)', text, re.M))
expected = {names!r}
bad = [f'{{n}}: expected FAILED, got {{status.get(n)}}' for n in expected if status.get(n) != 'FAILED']
if 'ERROR' in status.values() or re.search(r'ImportError|ModuleNotFoundError|SyntaxError|NameError|collection error', text):
    bad.append('errors or import/syntax/name problems present')
print(text[-3000:])
if bad:
    print('RED-CHECK FAILED'); [print(' -', b) for b in bad]; sys.exit(1)
print('RED-CHECK OK: every phone-thread test fails against today data')
PY
"""

data_spec = f"""You are a story-data worker for the freytag-forge repository at {R}. Boundary: NO model call, NO network call, never git commit. You own ONLY these files: {PKG}/storylets.md, {PKG}/storylet-routes.yaml, {PKG}/knowledge.yaml, {PKG}/world.yaml, {PKG}/plot.md, and {R}/tests/test_markdown_story_package.py (only the single storylet-count pin, 66 to 67, and any assertion that fails ONLY because SL-1A-J now exists). Do NOT edit {TEST} (the failing tests written for this change): make them pass. Do not edit any other test, engine, doc, or data file, and never edit pacing.yaml, handoffs.yaml, incidents.yaml, connections.yaml.

{DESIGN}

DO THIS. Read first: {PKG}/storylets.md (the SL-1A-G section), {PKG}/storylet-routes.yaml (the SL-1A-G entry, the SL-1A-B entry for a requires-gated second step, and the new_fact_ids list near line 160), {PKG}/knowledge.yaml (records k_sl_1a_g_r1, k_sl_1a_b_r0, k_sl_1a_b_r1 and the facts list near line 26), {PKG}/world.yaml (the facts list near line 505), {TEST}, and /home/bcorfman/dev/freytag-forge/docs/markdown-story-authoring/knowledge-and-disclosure.md. Then:
1. storylets.md: add a section '### SL-1A-J — What Michelle's Phone Kept' right after SL-1A-I's section (before SL-1A-E), in the exact heading layout of SL-1A-G (Source beats link to 1A.2, Allowed scene, Available when, Participants / items, Dramatic purpose, Possible realizations, Effects, Completion, Abort, Protected boundary, Pacing window earliest turn 0 / target turn 5 / latest turn 11).
2. storylet-routes.yaml: add the SL-1A-J storylet (three realization_options R1, R2, R3 with the operations asserting the facts above; R1 and R2 also assert michelle_abduction_suspicion true; eligible_storylet_event_id null; helps_transition_triggers []; protected_knowledge_boundaries as SL-1A-G) after the SL-1A-I storylet entry, and add both facts to new_fact_ids with used_by_storylets [SL-1A-J].
3. knowledge.yaml: declare both facts in the facts list with a purpose line, and add the three records k_sl_1a_j_r1..r3 in the shape of k_sl_1a_g_r1: reach_entity_ids [michelle_phone]; entity_ids [kristin, michelle, michelle_phone]; voiceable false; audience public player_visible; available_in_scenes [1A]; source kind storylet_realization with the matching storylet_id and realization_id; aliases; must_convey groups taken from the delivery text. earn_when and action_evidence: R1 and R2 use evidence groups [unlock, enter, type, read, open, check, view, scroll, look at] AND [phone, phone's, message, messages, text, texts, thread, passcode, password]; R3 uses [check, look at, open, read, view, scroll, see] AND [calls, call, call log, call history, missed calls, recent calls]. R1 requires patrol_in_house equals false, R2 requires patrol_in_house equals true, R3 requires michelle_text_read equals true. Establishes as in the DESIGN. Place the three records immediately after k_sl_1a_i_r1.
4. world.yaml: add michelle_text_read and kristin_calls_read to the facts list.
5. plot.md: in scene 1A.2, immediately before the paragraph that begins 'Kristin finds Michelle's memory card taped beneath the drawer' (assert exactly one match), insert two paragraphs: first 'Michelle's phone uses a passcode. Kristin knows it because Michelle is her best friend. Kristin's own phone unlocks when it recognizes her face. It has no passcode. Kristin's laptop needs no password.' then 'On Michelle's phone, Kristin finds the 4:07am text and then her own unanswered calls. If Officer Reyes is in the kitchen, his watching makes her uneasy.' Do NOT change 1A.1 Details, setting_facts, entry_text or character biographies.
6. Update the storylet count pin in tests/test_markdown_story_package.py (66 to 67) and any assertion that fails only because of the new storylet; do not weaken any assertion.
Keep every other byte of these files unchanged. Typography: straight apostrophes and straight quotes exactly as in neighbouring text; the em dash in the heading as in neighbouring headings.
HOW TO RUN (from {R}, never bare python, never uv): `{ENV} {PY} -m pytest {TEST} tests/test_markdown_story_package.py tests/test_richer_1a_fixes.py tests/test_1a_kitchen_start.py tests/test_place_scoped_feed.py tests/test_audit_budget.py -q -p no:cacheprovider 2>&1 | tail -40`. If a test outside the files you own fails because of this change, do NOT edit it; list its exact name and failure in {R}/bench/results/1a-passcode-round2/phone-thread-pin-failures.txt and stop. The loader may reject something: read its error and fix the data, never the loader."""

data_check = f"""set -o pipefail
cd {R}
{ENV}
{PY} -m pytest {TEST} -q -p no:cacheprovider 2>&1 | tail -25
{PY} -m pytest {TEST} tests/test_markdown_story_package.py tests/test_richer_1a_fixes.py tests/test_1a_kitchen_start.py tests/test_place_scoped_feed.py tests/test_audit_budget.py -q -p no:cacheprovider 2>&1 | tail -30
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
        "run_name": f"1a-phone-thread-{name}",
        "workdir": f"/home/bcorfman/dev/ringer-work/1a-phone-thread-{name}",
        "max_parallel": 1,
        "worktrees": False,
        "repo": R,
        "tasks": [task],
    }


tests_m = manifest(
    "tests",
    "write-phone-thread-tests",
    "test-hardening",
    tests_spec,
    tests_check,
    [TEST],
    [TEST],
    1800,
    "all ten phone-thread tests fail against today's data for the right reason",
)
files = [f"{PKG}/{n}" for n in ("storylets.md", "storylet-routes.yaml", "knowledge.yaml", "world.yaml", "plot.md")] + [
    f"{R}/tests/test_markdown_story_package.py"
]
data_m = manifest(
    "data",
    "add-phone-thread-storylet",
    "code-feature",
    data_spec,
    data_check,
    files,
    files[:5],
    3000,
    "the phone-thread tests and the package, kitchen, baseline and budget suites pass",
)
for name, m in (("tests", tests_m), ("data", data_m)):
    path = Path(D) / f"phone-thread-{name}-manifest.json"
    path.write_text(json.dumps(m, indent=2) + "\n")
    print(path)
