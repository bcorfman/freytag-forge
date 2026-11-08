# ruff: noqa: E501
"""Build the one-task Ringer manifest that writes the FAILING tests for trailing pacing events (plan section A). Tests only: no engine edit."""

import json
from pathlib import Path

R = "/home/bcorfman/dev/freytag-forge"
D = f"{R}/scripts/ringer/1a-password-officer"
PY = f"{R}/.venv/bin/python"
TEST = f"{R}/tests/test_trailing_pacing_events.py"

spec = f"""You are a test-writing worker for the freytag-forge repository at {R}. Boundary: NO model call, NO network call, never git commit. You own ONLY {TEST} (create). Do not edit anything else: no engine, loader, model, doc, data, or existing test file. Read {R}/tests/test_1a_patrol.py first and copy its stub style (monkeypatching urlopen so no network is used).

BACKGROUND. In RuntimeEngine._turn_active (storygame/runtime/engine.py) a pacing event whose turn arrives is fired by _activate_pacing BEFORE the narrator provider is called (so the narrator request sees the post-event world), then the post-commit lifecycle appends the event's verbatim realization text after the story. A feature is being added, tests first: a pacing event may carry an authored boolean `trailing: true` (storygame/story_package/models.py PacingEvent, default False). A trailing event must NOT fire in the pre-narration pass; it fires in the post-commit pass, so the narrator request sees the world as it was BEFORE the event, and its verbatim text is appended once after the story, and the next turn sees the post-event world. Non-trailing events keep today's behavior exactly.

WRITE THESE TESTS in {TEST}, all with the exact function names given (the check matches on names). Build the trailing variant of the package with a helper: copy {R}/data/stories/continuity-initiative to pytest's tmp_path with shutil.copytree and insert the line '  trailing: true' directly after the line '  scene_id: 1A' that follows '- id: patrol_leaves_1a' in the copied pacing.yaml (a string edit; assert the anchor occurs exactly once); a second helper does the same for '- id: patrol_enters_1a'. Load with storygame.story_package.loader.load_story_package. Drive the real engine with the canonical commands used in tests/test_1a_patrol.py style: CloudflareTurnProvider(worker_url='https://worker.example/turn', token='', state=state), RuntimeEngine(state, provider), RuntimeState.bootstrap(package), engine.opening(), then engine.turn(command, clock_seconds=...) for 'Turn on the phone.', 'Unlock the phone.', 'Type in the password.', "Type the password into Michelle's phone.", 'Turn off the phone.', 'Greet the officer.', 'Ask the officer where Dr. McGehee is.' (turn indexes 1 to 7 in scene 1A; the stub narrator returns one neutral narration segment). Inside the stubbed urlopen, record world_for(package, state.facts).parent('patrol_officer') at the moment each narrator request is built (from storygame.runtime.world_model import world_for).
1. test_pacing_event_trailing_defaults_to_false_control: loads the shipped package; every PacingEvent in package.pacing.events has trailing is False.
2. test_pacing_event_accepts_trailing_true: the trailing variant loads and the patrol_leaves_1a event has trailing is True.
3. test_pacing_event_rejects_non_boolean_trailing: a copy with 'trailing: maybe' (or any non-bool) fails to load with an exception.
4. test_trailing_departure_request_sees_pre_event_world: in the trailing-leaves variant at turn 7 the recorded officer parent at the narrator request is 'kitchen'.
5. test_trailing_departure_commits_and_appends_text_once: same run, after turn 7 the officer parent is 'patrol_staging', the returned proposal's segment texts contain 'The patrol pulls away from the curb.' exactly once and it is the LAST segment, and 'patrol_leaves_1a' is in state.fired_event_ids.
6. test_trailing_departure_next_turn_sees_post_event_world: a turn 8 command 'Look at the wall calendar.' records officer parent 'patrol_staging' at its request.
7. test_non_trailing_departure_request_sees_post_event_world_control: on the SHIPPED package, turn 7 records officer parent 'patrol_staging' at the request and the text appears exactly once (today's behavior).
8. test_trailing_arrival_request_sees_pre_event_world: trailing-enters variant: at the turn 5 request the officer parent is 'outside_house' (he arrived outside at turn 4), after turn 5 it is 'kitchen', and the entering text 'The front door opens. An officer walks in and heads straight for Michelle's workstation.' is appended once.
9. test_trailing_event_rolled_back_with_snapshot: take state.snapshot() before turn 7, run turn 7 on the trailing-leaves variant, call state.restore_snapshot(snapshot), then 'patrol_leaves_1a' is NOT in state.fired_event_ids and the officer parent is 'kitchen'; re-running turn 7 fires it once.
10. test_trailing_event_survives_snapshot_round_trip: after turn 7 on the trailing-leaves variant, snapshot and restore into the state (or the state's own serialize/restore path if one exists; read storygame/runtime/state.py) leave 'patrol_leaves_1a' in fired_event_ids, officer parent 'patrol_staging', and turn 8 does not append the leaving text again.
11. test_trailing_flag_is_documented_control: docs/markdown-story-authoring/pacing-and-incidents.md contains the word 'trailing' (this is expected to FAIL now).
Tests 1 and 7 end in '_control' and must PASS against today's code; every other test must FAIL against today's code for the right reason (the loader rejects the unknown field 'trailing', or the behavior differs), never because of an import error, a typo, or a fixture bug. If a test would fail for a reason unrelated to the feature, fix the test. Keep the file compact: share one helper that runs the 7-command prefix and returns the recorded observations. Write straight apostrophes in commands exactly as given.
HOW TO RUN (from {R}; never bare python, never uv): `TMPDIR=/tmp PYTHONPATH={R}:{R}/packages/worldkeeper/src {PY} -m pytest {TEST} -q -p no:cacheprovider -rA 2>&1 | tail -40`; format with `{PY} -m ruff format {TEST} && {PY} -m ruff check {TEST}`. Do not try to make the failing tests pass; that is a later task."""

check = f"""set -o pipefail
cd {R}
export TMPDIR=/tmp PYTHONPATH={R}:{R}/packages/worldkeeper/src
{PY} -m ruff check {TEST}
{PY} -m ruff format --check {TEST}
{PY} -m pytest {TEST} -q -p no:cacheprovider -rA > /tmp/trailing-tests-red.txt 2>&1
{PY} - <<'PY'
import re, sys
text = open('/tmp/trailing-tests-red.txt').read()
status = dict((m.group(2), m.group(1)) for m in re.finditer(r'^(PASSED|FAILED|ERROR) \\S+::(\\w+)', text, re.M))
expected = ['test_pacing_event_trailing_defaults_to_false_control','test_pacing_event_accepts_trailing_true','test_pacing_event_rejects_non_boolean_trailing','test_trailing_departure_request_sees_pre_event_world','test_trailing_departure_commits_and_appends_text_once','test_trailing_departure_next_turn_sees_post_event_world','test_non_trailing_departure_request_sees_post_event_world_control','test_trailing_arrival_request_sees_pre_event_world','test_trailing_event_rolled_back_with_snapshot','test_trailing_event_survives_snapshot_round_trip','test_trailing_flag_is_documented_control']
bad = []
for name in expected:
    got = status.get(name)
    want = 'PASSED' if name.endswith('_control') and 'documented' not in name else 'FAILED'
    if got != want:
        bad.append(f'{{name}}: expected {{want}}, got {{got}}')
if 'ERROR' in status.values() or re.search(r'ImportError|ModuleNotFoundError|SyntaxError|NameError|collection error', text):
    bad.append('errors or import/syntax/name problems present')
print(text[-3500:])
if bad:
    print('RED-CHECK FAILED'); [print(' -', b) for b in bad]; sys.exit(1)
print('RED-CHECK OK: control tests pass, every feature test fails against today code')
PY
"""

task = {
    "key": "write-trailing-tests",
    "task_type": "test-hardening",
    "engine": "codex",
    "model": "gpt-5.6-luna",
    "engine_args": ["-c", "model_reasoning_effort=medium"],
    "max_attempts": 2,
    "timeout_s": 1800,
    "check_timeout_s": 900,
    "ownership": [TEST],
    "expect_files": [TEST],
    "spec": spec,
    "check": check,
    "verified": "the new tests are red for feature reasons (controls green) before any engine change",
}
manifest = {
    "run_name": "trailing-pacing-events",
    "workdir": "/home/bcorfman/dev/ringer-work/trailing-pacing-events",
    "max_parallel": 1,
    "worktrees": False,
    "repo": R,
    "tasks": [task],
}
Path(f"{D}/trailing-tests-manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")
print("written")
