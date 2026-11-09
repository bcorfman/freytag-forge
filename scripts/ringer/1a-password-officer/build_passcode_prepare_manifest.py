# ruff: noqa: E501
"""Build the one-task Ringer manifest that freezes the round-2 1A passcode Stage A arms offline. No billed request."""

import json
from pathlib import Path

R = "/home/bcorfman/dev/freytag-forge"
D = f"{R}/scripts/ringer/1a-password-officer"
OUT = f"{R}/bench/results/1a-passcode-round2"
PY = f"{R}/.venv/bin/python"

spec = f"""You are a code worker for the freytag-forge repository at {R}. Boundary: NO model call, NO network call, never git commit, never edit anything under {R}/data, {R}/storygame, {R}/packages, {R}/bench/*.py, {R}/tests, and never edit or delete any existing file in {D}/ or in {R}/bench/results/1a-password-officer/ (they are the frozen record of round 1). You own only these NEW files: {D}/capture_passcode.py, {D}/replay_passcode.py, {R}/bench/variations/1a-passcode-round2.json, and everything under {OUT}/ (written by capture_passcode.py). Do NOT read or edit {D}/validate_passcode.py (the independent check, written separately); read its failure output, only run it.

GOAL: freeze, offline and from the CURRENT working tree, the scene 1A narrator payloads for the round-2 Stage A source screen: whether one extra access statement makes the narrator actually type the known passcode. Plus a guarded replay. Model on {D}/capture.py and {D}/replay.py (read them first; copy what you need, do not import them unless the import has no side effects) and use bench.frozen_prompts (fp.SCENE = '1A'; fp._prefix_states(variation, [endpoint]); fp._capture_wire_payload(state, command)) exactly as capture.py's capture_one does.

VARIATION. Create {R}/bench/variations/1a-passcode-round2.json as a copy of {R}/bench/variations/1a-password-officer.json with "name" changed to "1a-passcode-round2". Capture code overrides scripts and the package path per arm exactly as capture.py does.

FIXED STATE. Every endpoint uses the SAME prefix of two stub-reply turns, in this order: "Pick up Michelle's phone." then "Turn on the phone." (canonical imperative commands). The prefix must NOT contain any unlock command, so no arm starts from an already-unlocked phone. The endpoint command is the third input. Before writing anything else, capture the CTRL payload and print the exact phone placement line and the SCENE section in it. Write {OUT}/state-notes.txt stating, from what you actually observe: (a) whether the prefix leaves Michelle's phone held by Kristin, still on the floor, or other (quote the line), (b) which device lines (phone, laptop) appear in the payload. If the pickup command does not change the phone line, do not invent a state: keep the prefix, record the fact, and continue.

ARM PACKAGES. Copy the shipped package {R}/data/stories/continuity-initiative with shutil.copytree to {OUT}/pkg/access (rmtree first so re-runs are clean). Edit ONLY knowledge.yaml in it: insert this record immediately after the record whose id is k_scene_1a_entry (find its end by the next line that starts with '- id: '; assert exactly one match), formatted like its neighbours:
- id: k_1a_michelle_phone_access
  statement: Michelle's phone uses a passcode. Kristin knows it because Michelle is her best friend.
  entity_ids: [michelle_phone]
  aliases: [Michelle's phone passcode]
  leak_terms: []
  voiceable: false
  audience: {{kind: public, player_visible: true}}
  available_in_scenes: [1A]
  establishes: [{{op: assert, fact_id: scene_1a_entry_known, value: true}}]
  source: {{kind: scene_entry}}
Every other file in the arm package must be byte-identical to the shipped package. The CTRL arm uses the shipped package unmodified. Do NOT add prompt_entity_ids, kristin_phone, a lock axis, or any plot.md change: those are not in this screen. The arm tests only whether the statement, as the current engine renders it, changes the narration.

ENDPOINTS (three, each with arms CTRL and ACCESS, so six frozen cells):
- PW1: command "Type in the password." (historical wording)
- PW2: command "Type in the passcode."
- PW3: command "Type the passcode into Michelle's phone."
Inputs for each endpoint's script: ["Pick up Michelle's phone.", "Turn on the phone.", <endpoint command>]; endpoint index 3. For each arm and endpoint write {OUT}/frozen-<ARM>-<endpoint>.json = {{"arm": ..., "endpoint": {{"n": <id>, "command": ..., "wire_payload": <payload>, "user_sha256": sha256 of payload['user']}}}} (json ensure_ascii=False, indent=2). Also write {OUT}/provenance.json with keys: head (git rev-parse HEAD), dirty_files (git status --porcelain lines), package_sha256 (sha256 per file name of the shipped package files and of pkg/access), frozen_sha256 (sha256 of every frozen file), prefix_inputs, endpoints. Print per endpoint and arm the system/user/total char counts and the delta from control. capture_passcode.py must be re-runnable (overwrite its own outputs).
Where the statement appears in the ACCESS prompt (SCENE, CHARACTERS, THINGS or elsewhere) is a finding: print the section name and the exact line, and record it in state-notes.txt. Do not force it to a place.
If the ACCESS prompt differs from CTRL by more than the statement line(s) (for example the ordering of other lines changes), print the full line diff and record it in state-notes.txt; do not hide it.

REPLAY. {D}/replay_passcode.py: header '# ruff: noqa: E501'; function run(out, first, last, send=None, only=None) and CLI `replay_passcode.py OUT FIRST LAST [--only PW1,PW2] [--confirm]` run from {R}. Cells are arms CTRL then ACCESS crossed with endpoints PW1, PW2, PW3 (arm order CTRL, ACCESS). Samples: 0 is the unscored smoke sample, 1..12 are scored; assert 0 <= FIRST <= LAST <= 12. Row order is sample-major, then endpoint, then arm (interleaved). `only` restricts endpoints. One request per cell, no retries or replacements, every exception kept as a row (error=str(e), narration=None). Row fields: stage ('passcode-round2'), arm, n, sample, command, narration, error, raw (raw = body decoded utf-8 errors='replace', narration = bench.frozen_prompts._decode_replay_body(body)). Rewrite the whole rows JSON after every cell. Raise FileExistsError if OUT exists. Print f'requests {{count}}' (cells x samples); without --confirm print 'dry run: nothing sent' and exit 0 BEFORE building any transport. Transport (only when sending and send is None): import bench.frozen_prompts as fp; fp.SCENE = '1A'; from bench.core import load_dotenv; load_dotenv(); send = fp._default_transport({{'variation': '1a-passcode-round2'}}). Frozen payloads come verbatim from {OUT}/frozen-<ARM>-<endpoint>.json. The module must be importable without side effects (CLI under __main__) because the validator imports it with a stub transport. The full run 0..12 must report 'requests 78'.

HOW TO RUN (from {R}, never bare python): `TMPDIR=/tmp PYTHONPATH={R}:{R}/packages/worldkeeper/src {PY} scripts/ringer/1a-password-officer/capture_passcode.py`; `{PY} -m ruff format scripts/ringer/1a-password-officer/capture_passcode.py scripts/ringer/1a-password-officer/replay_passcode.py && {PY} -m ruff check scripts/ringer/1a-password-officer/capture_passcode.py scripts/ringer/1a-password-officer/replay_passcode.py`; then `TMPDIR=/tmp PYTHONPATH={R}:{R}/packages/worldkeeper/src {PY} scripts/ringer/1a-password-officer/validate_passcode.py` until it prints '1A PASSCODE FREEZE VALIDATION OK'. If a control prompt cannot be captured (an exception, or not exactly one narrator payload) report the exact error in {OUT}/capture-notes.txt and stop."""

check = f"""set -o pipefail
cd {R}
export TMPDIR=/tmp PYTHONPATH={R}:{R}/packages/worldkeeper/src
{PY} scripts/ringer/1a-password-officer/capture_passcode.py > /dev/null
{PY} -m ruff check scripts/ringer/1a-password-officer/capture_passcode.py scripts/ringer/1a-password-officer/replay_passcode.py
{PY} -m ruff format --check scripts/ringer/1a-password-officer/capture_passcode.py scripts/ringer/1a-password-officer/replay_passcode.py
{PY} scripts/ringer/1a-password-officer/validate_passcode.py
"""

task = {
    "key": "prepare-1a-passcode-round2",
    "task_type": "code-feature",
    "engine": "codex",
    "model": "gpt-5.6-luna",
    "engine_args": ["-c", "model_reasoning_effort=medium"],
    "max_attempts": 2,
    "timeout_s": 1800,
    "check_timeout_s": 600,
    "ownership": [
        f"{D}/capture_passcode.py",
        f"{D}/replay_passcode.py",
        f"{R}/bench/variations/1a-passcode-round2.json",
        f"{OUT}/",
    ],
    "expect_files": [
        f"{D}/capture_passcode.py",
        f"{D}/replay_passcode.py",
        f"{R}/bench/variations/1a-passcode-round2.json",
        f"{OUT}/provenance.json",
        f"{OUT}/state-notes.txt",
    ],
    "spec": spec,
    "check": check,
    "verified": "the independent validator proves ACCESS differs from CTRL only by the planned statement and the replay keeps order, the 78-request cap and the dry-run guard",
}
manifest = {
    "run_name": "1a-passcode-round2-prepare",
    "workdir": "/home/bcorfman/dev/ringer-work/1a-passcode-round2-prepare",
    "max_parallel": 1,
    "worktrees": False,
    "repo": R,
    "tasks": [task],
}
Path(f"{D}/passcode-prepare-manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")
print("written")
