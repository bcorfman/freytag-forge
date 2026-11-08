# ruff: noqa: E501
"""Ringer task 1 of 2 for the fused-segment repair: write the FAILING tests only."""

import json
from pathlib import Path

R = "/home/bcorfman/dev/freytag-forge"
D = f"{R}/scripts/ringer/1a-password-officer"
PY = f"{R}/.venv/bin/python"
TEST = f"{R}/tests/test_fused_segment_repair.py"
FUSED = r'''{"segments":[{"kind":"narration","text":"\"Officer Reyes, what are you doing here?\"","},{":"kind","narration":"Officer Reyes looks at the splintered back door frame and thrown deadbolt, then back at Kristin.\""}],"selected_knowledge_ids":[],"item_facts":{"Kristin":{"place":"Michelle's kitchen"},"Michelle's kitchen":{"place":"Michelle's kitchen"},"Officer Reyes":{"place":"Michelle's workstation"}}}'''
CONTROLS = [
    "test_valid_reply_is_untouched_control",
    "test_fused_object_with_a_lettered_extra_key_still_goes_to_recovery_control",
    "test_fused_object_without_text_still_goes_to_recovery_control",
    "test_blank_second_text_still_goes_to_recovery_control",
    "test_ungrounded_selection_still_goes_to_recovery_control",
    "test_recovery_reply_is_never_repaired_control",
]
FEATURES = [
    "test_fused_object_is_split_into_two_segments_without_a_recovery_request",
    "test_recorded_greeting_reply_is_repaired_by_the_real_item_facts_provider",
    "test_valid_neighbours_are_kept_and_fused_object_is_split",
    "test_repair_is_logged_once_with_shapes_only",
    "test_repaired_second_segment_carries_no_grounding_or_speaker",
]

spec = f"""You are a test-writing worker for the freytag-forge repository at {R}. Boundary: NO model call, NO network call, never git commit. You own ONLY {TEST} (create). Edit nothing else. Read {R}/tests/test_cloudflare_transport.py first (it shows how the transport is stubbed and how segment salvage is tested; copy that style) and storygame/runtime/cloudflare.py (CloudflareTurnProvider._dispatch, _salvage_malformed_segments, _recover_malformed_response) and storygame/runtime/item_facts.py (ItemFactsProvider, which allows the extra top-level key item_facts).

BACKGROUND. Sometimes the hosted model returns a first reply whose segment object is FUSED: valid 'kind' and 'text' for the first line, plus a junk key made only of punctuation (for example "}},{{") and a second line under the key 'narration'. NarrationSegment forbids extra keys, so the object is rejected; no valid segment remains, so salvage returns None and the provider spends a recovery request, which usually leaves the second speaker's line out. A feature is being added, tests first: a typed repair that runs on the FIRST reply only, before salvage. Contract (the tests encode it): for a segment object in payload['segments'] whose 'kind' is one of narration, dialogue, action and whose 'text' is a non-blank string, and whose ONLY other keys are 'narration' (a non-blank string) and any number of junk keys that contain no letter or digit, replace it with two segments: {{kind, text, plus its speaker_id and grounding_ids if it had them}} then {{'kind': 'narration', 'text': <the narration string>}} with no speaker_id and no grounding_ids. Everything else is left as is. The repair is skipped (fail closed, normal salvage and recovery behavior) when the object has any other key, lacks text, has a blank narration string, or when selected_knowledge_ids names an id that is not grounded in a segment that survives (the same condition salvage uses). Other segments in the reply are kept in order. Top-level keys other than segments are preserved. The repaired reply goes through the normal eligibility parse; the recovery request is NOT sent when the repair yields a valid proposal. Only the first reply is repaired; the reply to a recovery request is never repaired. A warning is logged once per repaired reply with the number of repaired objects and the JSON key shapes only (never the model's text).
WRITE THESE TESTS (exact function names; the check matches on them). Controls must PASS today, features must FAIL today for the right reason (the reply is not repaired, so a recovery request is sent or the segments differ), never because of an import error or a typo.
Controls: {', '.join(CONTROLS)}.
 - valid_reply_untouched: a normal two-segment reply is accepted with one request and no repair log.
 - lettered_extra_key: the fused object but the junk key is 'extra' (has letters): goes to recovery (2 requests, result is the recovery reply).
 - without_text: a fused-looking object with no 'text' key: goes to recovery.
 - blank_second_text: the 'narration' value is '   ': goes to recovery.
 - ungrounded_selection: the reply has selected_knowledge_ids naming an id with no grounding in a valid segment plus a fused object: goes to recovery (read how salvage decides this and mirror it).
 - recovery_reply_never_repaired: the first reply is unparseable (for example invalid segment shape that cannot be repaired) and the SECOND (recovery) reply is a fused object: it is not repaired (the provider raises or falls to its existing behavior; assert the existing behavior you observe).
Features: {', '.join(FEATURES)}.
 - split_into_two: a plain CloudflareTurnProvider test with one fused object: one request only, two segments, texts in order, second segment kind 'narration'.
 - recorded_greeting_reply: the REAL ItemFactsProvider subclass (see how tests build it and stub its transport) receives this exact recorded reply as the first answer: {FUSED!r}; one request; the segments are the quoted line and then the officer sentence; item_facts handling is unchanged (assert the reply still carries what ItemFactsProvider normally consumes, or that no exception is raised and the provider's item_facts state is populated as for a valid reply).
 - valid_neighbours: [valid segment, fused object, valid segment] gives four segments in order.
 - logged_once: caplog shows exactly one warning from the cloudflare logger for the repair, containing the count and the key shapes, and NOT containing any text of the reply.
 - no_grounding_or_speaker: the first part keeps a speaker_id/grounding_ids it had; the second part has neither.
Use hermetic fixtures only (no files under bench/results). Keep the file compact with shared helpers.
HOW TO RUN (from {R}; never bare python, never uv): `TMPDIR=/tmp PYTHONPATH={R}:{R}/packages/worldkeeper/src {PY} -m pytest {TEST} -q --no-cov -p no:cacheprovider -rA 2>&1 | tail -40`; `{PY} -m ruff format {TEST} && {PY} -m ruff check {TEST}`. Do NOT implement the repair and do not edit storygame."""

check = f"""set -eo pipefail
cd {R}
export TMPDIR=/tmp PYTHONPATH={R}:{R}/packages/worldkeeper/src
{PY} -m ruff check {TEST}
{PY} -m ruff format --check {TEST}
git diff --quiet -- storygame data docs
set +e
{PY} -m pytest {TEST} -q --no-cov -p no:cacheprovider -rA > /tmp/repair-tests-red.txt 2>&1
set -e
{PY} - <<'PY'
import re, sys
text = open('/tmp/repair-tests-red.txt').read()
status = dict((m.group(2), m.group(1)) for m in re.finditer(r'^(PASSED|FAILED|ERROR) \\S+::(\\w+)', text, re.M))
controls = {CONTROLS!r}
features = {FEATURES!r}
bad = []
for name in controls:
    if status.get(name) != 'PASSED':
        bad.append(f'{{name}}: expected PASSED, got {{status.get(name)}}')
for name in features:
    if status.get(name) != 'FAILED':
        bad.append(f'{{name}}: expected FAILED, got {{status.get(name)}}')
if 'ERROR' in status.values() or re.search(r'ImportError|ModuleNotFoundError|SyntaxError|NameError|collection error', text):
    bad.append('errors or import/syntax/name problems present')
print(text[-2500:])
if bad:
    print('RED-CHECK FAILED')
    for b in bad:
        print(' -', b)
    sys.exit(1)
print('RED-CHECK OK')
PY
"""
task = {
    "key": "write-fused-repair-tests",
    "task_type": "test-hardening",
    "engine": "codex",
    "model": "gpt-5.6-luna",
    "engine_args": ["-c", "model_reasoning_effort=medium"],
    "max_attempts": 2,
    "timeout_s": 2400,
    "check_timeout_s": 900,
    "ownership": [TEST],
    "expect_files": [TEST],
    "spec": spec,
    "check": check,
    "verified": "controls green, feature tests red for feature reasons, no source touched",
}
manifest = {
    "run_name": "fused-segment-repair",
    "workdir": "/home/bcorfman/dev/ringer-work/fused-segment-repair",
    "max_parallel": 1,
    "worktrees": False,
    "repo": R,
    "tasks": [task],
}
Path(f"{D}/repair-tests-manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")
print("written")
