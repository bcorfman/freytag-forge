# ruff: noqa: E501
"""Build the two Ringer manifests for the 1A departure hold SL-1A-K: failing tests first, then the data edits."""

import json
from pathlib import Path

R = "/home/bcorfman/dev/freytag-forge"
D = f"{R}/scripts/ringer/1a-password-officer"
PY = f"{R}/.venv/bin/python"
PKG = f"{R}/data/stories/continuity-initiative"
TEST = f"{R}/tests/test_1a_departure_hold.py"
ENV = f"export TMPDIR=/tmp PYTHONPATH={R}:{R}/packages/worldkeeper/src"

BASE = "Kristin does not pull away yet. If anyone is watching the street, driving to the park now would lead them straight to the bench. She waits to see what the street does."
ON_SCENE = "Kristin does not pull away yet. The patrol is still at the house, and the truck would be the first thing they follow. If she drives to the park now, she leads them straight to the bench. She waits to see what the patrol does."
DEPARTED = "Kristin does not pull away yet. The patrol has only just left, and it could be waiting around the corner. If she drives to the park now, she may lead it straight to the bench. She waits to see what the street does."

DESIGN = f"""DESIGN (approved by Brandon, option 1). BUG: in scene 1A the engine moves the player to 1B by itself once the scene has run min_turns 13 (pacing.yaml) and three facts hold (michelle_lead_actionable, memory_card_recovered, patrol_return_pressure). A player who has read the memory card and types 'Drive to the park.' before that gets no answer at all (the narrator replays the recording). FIX: one new OPTIONAL scene-1A storylet SL-1A-K, "The Street Is Not Clear", with ONE realization SL-1A-K-R1 (knowledge record k_sl_1a_k_r1): an authored, repeatable reveal that answers an early attempt to drive to the park in the story. It changes no pacing, no transition, no floor.
Record k_sl_1a_k_r1 fields: repeatable true; voiceable false; reach_entity_ids [kristin_truck] (so it only answers when Kristin is at or in the truck, never from inside the kitchen); entity_ids [kristin, kristin_truck, park_bench]; requires michelle_lead_actionable equals true; establishes departure_held true (new fact, purpose: 'Kristin tried to drive to the park before the street was clear and held back.'); audience public player_visible; available_in_scenes [1A]; source storylet_realization SL-1A-K / SL-1A-K-R1; earn_when 'tries to drive or head to the park before the street is clear'. action_evidence (every group must match): [drive, head, ride, go, leave, pull out, pull away, set off, take the truck, get to] AND [park, bench]. It must NOT match 'Start the truck.' or 'Go out to the truck.' or 'Get in the truck.' (they contain no park/bench word). must_convey groups: [pull away, drive], [park], [bench], [waits, wait]. delivery_text (base, patrol not yet arrived), EXACTLY: {BASE}
delivery_variants (use the delivery_variants mechanism described in docs/markdown-story-authoring/knowledge-and-disclosure.md; one fact each, they are mutually exclusive): requires [patrol_on_scene] text EXACTLY: {ON_SCENE}
requires [patrol_departed] text EXACTLY: {DEPARTED}
Every variant must state every must_convey group.
Storylet SL-1A-K: scene 1A; title 'The Street Is Not Clear'; activation condition michelle_lead_actionable equals true; pacing earliest_turn 4, target_turn 10, latest_turn 12 (target 10 is deliberately not earlier than any existing 1A storylet, so it cannot block the forward activation of the others); pressure_role: 'If Kristin tries to leave for the park before the street is clear, the story holds her for a moment without ending the scene.'; ONE realization option SL-1A-K-R1 asserting departure_held true, eligible_storylet_event_id null, helps_transition_triggers [], protected_knowledge_boundaries as the other 1A storylets; complete_when departure_held equals true; abort_when scene_id_not 1A; non_coercion_note as the other 1A storylets. Protected boundary: it reveals nothing new (no JANUS, Brandon, detention, dead-drop contents) and never sets memory_card_recovered, michelle_lead_actionable, patrol_return_pressure, patrol_departed or any transition trigger."""

tests_spec = f"""You are a test-writing worker for the freytag-forge repository at {R}. Boundary: NO model call, NO network call, never git commit. You own ONLY {TEST} (create). Edit nothing else: no data, engine, doc, or existing test.

{DESIGN}

Read {R}/tests/test_1a_officer_press.py first and {R}/tests/test_1a_phone_thread.py (copy their style: module-level PACKAGE = load_story_package(Path('data/stories/continuity-initiative')), RuntimeState.bootstrap(PACKAGE), asserting story facts with Fact(predicate=..., subject='story', value='true'), apply_world_effects, engine._activate_pacing() and engine.projector.project(state, 'player', command).candidates for candidate ids). To put Kristin at the truck, find how existing tests or bench/core.py seed her there (grep tests for 'kristin_truck' and 'truck_driver_seat'); to keep her in the kitchen just use the scene-1A start state. Read k_sl_1a_f_r2 and k_sl_1b_e_r1 in {PKG}/knowledge.yaml (the two existing repeatable records) and the SL-1A-F entry in storylet-routes.yaml.

WRITE THESE TESTS in {TEST}, exact function names (the check matches names):
1. test_departure_hold_storylet_is_declared: storylet-routes has SL-1A-K, scene_id 1A, realization ids exactly [SL-1A-K-R1], pacing 4/10/12, activation condition michelle_lead_actionable true.
2. test_departure_held_fact_is_declared_everywhere: departure_held appears in the package knowledge facts, world facts and routes new_fact_ids (used_by_storylets [SL-1A-K]).
3. test_the_hold_answers_a_departure_command_at_the_truck: with michelle_lead_actionable and memory_card_recovered true, Kristin at the truck, turn_index 8: the candidate ids for each of 'Drive to the park.', 'Drive the truck to the park.', 'Head for the park.', 'Pull away and go to the park bench.' include k_sl_1a_k_r1.
4. test_the_hold_stays_quiet_for_other_commands_and_places: it is NOT among the candidates for 'Start the truck.', 'Go out to the truck.', 'Get in the truck.', nor for 'Drive to the park.' when Kristin is in the kitchen, nor when michelle_lead_actionable is false.
5. test_the_hold_text_is_the_approved_wording_for_each_patrol_state: the delivery text the engine would append (read it from the record plus delivery_variants resolution, the way the reveal projection does) equals the BASE text with no patrol fact, the ON_SCENE text with patrol_on_scene true, and the DEPARTED text with patrol_departed true; the three strings are in the DESIGN above, copy them character for character.
6. test_the_hold_can_repeat: with departure_held already true the record is still offered for 'Drive to the park.' (repeatable).
7. test_the_hold_sets_only_its_own_fact: the record establishes departure_held true and none of memory_card_recovered, michelle_lead_actionable, patrol_return_pressure, patrol_departed, michelle_warning_known; it has voiceable false and reach_entity_ids containing kristin_truck.
8. test_the_hold_text_conveys_every_required_group_and_leaks_nothing: each of the three wordings contains at least one term of every must_convey group (case-insensitive), and none contains 'janus', 'brandon', 'memory card', 'recording', 'dead drop', 'continuity initiative'.
9. test_an_early_drive_command_keeps_the_scene_and_shows_the_hold: run a real turn through RuntimeEngine with a scripted neutral provider (copy the engine construction and neutral provider from tests/test_1a_officer_press.py): state in scene 1A at turn_index 8 with the lead facts true and Kristin at the truck, command 'Drive to the park.'; afterwards the current scene is still 1A and the BASE (or the matching variant) text is in the turn's output. If the cloud provider stub makes a full turn impractical, assert through the same selection path the officer-press test uses and say so in a comment.
10. test_the_scene_still_leaves_once_the_floor_and_triggers_hold: with turn_index at the scene floor (13 turns since entry), memory_card_recovered, michelle_lead_actionable and patrol_return_pressure true, the transition t_1a_1b is eligible exactly as before (use the same helper existing tests use, e.g. engine._apply_authored_transition or validator.eligible_transitions with transition_dependencies_available).
Because the data does not exist yet, tests 1 to 8 must FAIL against today's data for the right reason (missing storylet, fact or record: KeyError, StopIteration or an assertion on the missing id are fine, not ImportError, SyntaxError, NameError or a fixture bug). Tests 9 and 10 may fail or pass; test 10 should PASS today because it tests unchanged behaviour. Keep the file compact with shared helpers. Straight apostrophes exactly as written.
HOW TO RUN (from {R}; never bare python, never uv): `{ENV} && {PY} -m pytest {TEST} -q --no-cov -p no:cacheprovider -rA 2>&1 | tail -40`; never use --cov. Format with `{PY} -m ruff format {TEST} && {PY} -m ruff check {TEST}`. Do not make the tests pass; that is the next task."""

names_red = [
    "test_departure_hold_storylet_is_declared",
    "test_departure_held_fact_is_declared_everywhere",
    "test_the_hold_answers_a_departure_command_at_the_truck",
    "test_the_hold_stays_quiet_for_other_commands_and_places",
    "test_the_hold_text_is_the_approved_wording_for_each_patrol_state",
    "test_the_hold_can_repeat",
    "test_the_hold_sets_only_its_own_fact",
    "test_the_hold_text_conveys_every_required_group_and_leaks_nothing",
]
names_all = [
    *names_red,
    "test_an_early_drive_command_keeps_the_scene_and_shows_the_hold",
    "test_the_scene_still_leaves_once_the_floor_and_triggers_hold",
]

tests_check = f"""set -o pipefail
cd {R}
{ENV}
{PY} -m ruff check {TEST}
{PY} -m ruff format --check {TEST}
{PY} -m pytest {TEST} -q --no-cov -p no:cacheprovider -rA > /tmp/departure-hold-red.txt 2>&1
{PY} - <<'PY'
import re, sys
text = open('/tmp/departure-hold-red.txt').read()
status = dict((m.group(2), m.group(1)) for m in re.finditer(r'^(PASSED|FAILED|ERROR) \\S+::(\\w+)', text, re.M))
red = {names_red!r}
every = {names_all!r}
bad = [f'{{n}}: expected FAILED, got {{status.get(n)}}' for n in red if status.get(n) != 'FAILED']
bad += [f'{{n}}: missing from the file' for n in every if n not in status]
if 'ERROR' in status.values() or re.search(r'ImportError|ModuleNotFoundError|SyntaxError|NameError|collection error', text):
    bad.append('errors or import/syntax/name problems present')
print(text[-3000:])
if bad:
    print('RED-CHECK FAILED'); [print(' -', b) for b in bad]; sys.exit(1)
print('RED-CHECK OK')
PY
"""

RUN = f"{TEST} tests/test_markdown_story_package.py tests/test_richer_1a_fixes.py tests/test_1a_kitchen_start.py tests/test_1a_officer_press.py tests/test_1a_phone_thread.py tests/test_place_scoped_feed.py tests/test_audit_budget.py tests/test_audit_budget_branches.py tests/test_knowledge_projection.py tests/test_voiceable_knowledge.py"

data_spec = f"""You are a story-data worker for the freytag-forge repository at {R}. Boundary: NO model call, NO network call, never git commit. You own ONLY these files: {PKG}/storylets.md, {PKG}/storylet-routes.yaml, {PKG}/knowledge.yaml, {PKG}/world.yaml, and the existing tests that legitimately pin counts or lists the new storylet and record change: {R}/tests/test_markdown_story_package.py, {R}/tests/test_audit_budget_branches.py, {R}/tests/test_knowledge_projection.py, {R}/tests/test_voiceable_knowledge.py, {R}/tests/test_design_review_fixtures.py (update only a count, list or expectation that fails ONLY because SL-1A-K and k_sl_1a_k_r1 now exist, and say why in a comment where the file's style allows; never weaken an assertion or delete a test). Do NOT edit {TEST} (the failing tests written for this change): make them pass. Never edit pacing.yaml, handoffs.yaml, incidents.yaml, connections.yaml, plot.md, or engine code. The working tree has unrelated uncommitted edits in knowledge.yaml and pacing.yaml (a phone-text wording change): leave every byte you are not asked to change exactly as it is.

{DESIGN}

DO THIS. Read first: {PKG}/storylets.md (SL-1A-F and SL-1A-C sections), {PKG}/storylet-routes.yaml (the SL-1A-F and SL-1A-C entries and the new_fact_ids list), {PKG}/knowledge.yaml (records k_sl_1a_f_r2 and k_sl_1a_c_r2, and the facts list near line 26), {PKG}/world.yaml (the facts list near line 640), {TEST}, and {R}/docs/markdown-story-authoring/knowledge-and-disclosure.md (delivery_variants). Then:
1. storylets.md: add '### SL-1A-K — The Street Is Not Clear' right after the SL-1A-C section (the last 1A section), in the exact heading layout of the SL-1A-C section (Source beats link to 1A.4 — The First Threat, Allowed scene, Available when, Participants / items, Dramatic purpose, Possible realizations, Effects, Completion, Abort, Protected boundary, Pacing window earliest turn 4 / target turn 10 / latest turn 12). Dramatic purpose: when Kristin tries to drive to the park before the street is clear, the story answers in the fiction and holds her for a moment instead of ignoring the command.
2. storylet-routes.yaml: add the SL-1A-K storylet after the SL-1A-C entry; add departure_held to new_fact_ids with used_by_storylets [SL-1A-K].
3. knowledge.yaml: declare departure_held in the facts list; add k_sl_1a_k_r1 right after k_sl_1a_c_r2, in the shape of k_sl_1a_f_r2 plus delivery_variants.
4. world.yaml: add departure_held to the facts list.
5. Update the pins named above only where needed.
Typography: straight apostrophes and quotes as in neighbouring text; the em dash in headings as in neighbouring headings. The loader or an audit may reject something (for example the delivery restatement audit, leak terms, must_convey coverage, or a storylet window rule): read its error and fix the DATA, never the loader. If the audit rejects a wording, change the wording minimally and list the change in {R}/bench/results/1a-passcode-round2/departure-hold-notes.txt.
HOW TO RUN (from {R}, never bare python, never uv): `{ENV} && {PY} -m pytest {RUN} -q --no-cov -p no:cacheprovider 2>&1 | tail -40`; never use --cov. Then `{PY} -m ruff check tests && {PY} -m ruff format --check tests`. If a test outside the files you own fails because of this change, do NOT edit it; list its exact name and failure in {R}/bench/results/1a-passcode-round2/departure-hold-pin-failures.txt and stop."""

data_check = f"""set -o pipefail
cd {R}
{ENV}
{PY} -m pytest {TEST} -q --no-cov -p no:cacheprovider 2>&1 | tail -25
{PY} -m pytest {RUN} -q --no-cov -p no:cacheprovider 2>&1 | tail -30
{PY} -m ruff check tests && {PY} -m ruff format --check tests
git diff --stat -- data | tail -8
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
        "run_name": f"1a-departure-hold-{name}",
        "workdir": f"/home/bcorfman/dev/ringer-work/1a-departure-hold-{name}",
        "max_parallel": 1,
        "worktrees": False,
        "repo": R,
        "tasks": [task],
    }


tests_m = manifest(
    "tests",
    "write-departure-hold-tests",
    "test-hardening",
    tests_spec,
    tests_check,
    [TEST],
    [TEST],
    1800,
    "tests 1-8 fail against today's data for the right reason; the unchanged-behaviour test passes",
)
files = [f"{PKG}/{n}" for n in ("storylets.md", "storylet-routes.yaml", "knowledge.yaml", "world.yaml")] + [
    f"{R}/tests/{n}"
    for n in (
        "test_markdown_story_package.py",
        "test_audit_budget_branches.py",
        "test_knowledge_projection.py",
        "test_voiceable_knowledge.py",
        "test_design_review_fixtures.py",
    )
]
data_m = manifest(
    "data",
    "add-departure-hold-storylet",
    "code-feature",
    data_spec,
    data_check,
    files,
    files[:4],
    3000,
    "the departure-hold tests and the package, 1A, budget and knowledge suites pass",
)
for name, m in (("tests", tests_m), ("data", data_m)):
    path = Path(D) / f"departure-hold-{name}-manifest.json"
    path.write_text(json.dumps(m, indent=2) + "\n")
    print(path)
