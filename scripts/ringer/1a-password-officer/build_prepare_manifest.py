# ruff: noqa: E501
"""Build the one-task Ringer manifest that freezes the 1A password/officer arms offline. No billed request."""

import json
from pathlib import Path

R = "/home/bcorfman/dev/freytag-forge"
D = f"{R}/scripts/ringer/1a-password-officer"
OUT = f"{R}/bench/results/1a-password-officer"
PY = f"{R}/.venv/bin/python"

spec = f"""You are a code worker for the freytag-forge repository at {R}. Boundary: NO model call, NO network call, never git commit, never edit anything under {R}/data, {R}/storygame, {R}/bench/*.py, {R}/tests. You own only {D}/capture.py (create), {D}/replay.py (create), {R}/bench/variations/1a-password-officer.json (create), and everything under {OUT}/ (written by capture.py). Do NOT read or edit {D}/validate_freeze.py (the independent check; read its failure output, only run it).

GOAL: freeze, from the CURRENT working tree and offline, the scene 1A narrator payloads for four comparisons, plus a guarded replay. Model on {R}/scripts/ringer/lead-up-contradictions/capture_3a.py and replay_3a.py (read them first) and use bench.frozen_prompts (fp.SCENE = '1A'; fp._prefix_states(variation, [endpoint]); fp._capture_wire_payload(state, command)).

VARIATION. Create {R}/bench/variations/1a-password-officer.json: {{"name": "1a-password-officer", "story_package": "data/stories/continuity-initiative", "fixed_turns": 7, "runtime": true, "item_facts": {{"mode": "single_call", "seed_from_package": true}}, "scripts": {{"1A": [{{"name": "placeholder", "inputs": ["Turn on the phone."]}}]}}}} (the capture code overrides scripts and the package path per case: after bench.core.load_variation, set variation['scripts'] = {{'1A': [{{'name': ..., 'inputs': [...]}}]}} and, for an arm package, variation['_package_path'] = the arm package directory; check how load_variation/resolve_variation/package_and_state use '_package_path' and follow that).

ARM PACKAGES. Copy the whole shipped package {R}/data/stories/continuity-initiative with shutil.copytree into {OUT}/pkg/officer-bio, {OUT}/pkg/walt-bio and {OUT}/pkg/officer-alias, then edit ONLY these files:
- plot.md in officer-bio and officer-alias: insert this block (copy exactly, straight apostrophes none needed) so that it sits immediately before the line '# Expanded Scene Outline', after the existing '### Imprisoned senior official' paragraph, keeping one blank line before the new heading and one blank line after the new paragraph:
### Officer Reyes

A young, polite federal patrol officer who works from a printed list and does not like what the list asks of him.

- plot.md in walt-bio: insert the same way:
### Walt Pruitt

A retired bus driver in his seventies whose wife is one of the missing. He is tired, careful with his words, and unsure what he saw.

- world.yaml in officer-alias ONLY: in npcs[patrol_officer].aliases add one new last alias line '  - officer' directly after the line '  - Reyes' (the next line is '  narrator_bio: A young, polite federal patrol officer...'). Nothing else changes.
Every other file in each arm package must be byte-identical to the shipped package. The control arms use the shipped package, unmodified.

CASES. Every case captures the REAL payload for one endpoint with the real engine path (stub reply 'Kristin looks.' for prefix turns is what fp._prefix_states already does). Canonical imperative commands only, exactly as written:
- stage 'officer' (arms CTRL = shipped package, BIO = pkg/officer-bio): script inputs ['Turn on the phone.', 'Unlock the phone.', 'Type in the password.', "Type the password into Michelle's phone.", 'Turn off the phone.', 'Greet the officer.', 'Ask the officer where Dr. McGehee is.']; endpoint OFF6 = command index 6 ('Greet the officer.'), endpoint OFF7 = index 7 ('Ask the officer where Dr. McGehee is.').
- stage 'raw' (arms BIO = pkg/officer-bio, ALIAS = pkg/officer-alias): same first six inputs, seventh input 'Officer, do you know where Dr. McGehee is?'; endpoint RAW7 = index 7 (deliberately raw vocative language).
- stage 'walt' (arms CTRL = shipped, BIO = pkg/walt-bio): inputs ['Examine the back door.', 'Look at the wall calendar.', 'Look at the photograph.', 'Search the drawer.', 'Search beneath the drawer.', 'Go outside.', 'Ask the neighbor what he saw.']; endpoint WALT = index 7.
- stage 'password' (arms CTRL = shipped; SUB and ADD derived from CTRL): inputs ['Turn on the phone.', 'Unlock the phone.', 'Type in the password.']; endpoint PW = index 3. CTRL is the captured payload. SUB is a deep copy of CTRL whose user text is changed by exactly three string edits (each target must occur exactly once, assert): replace the line "- Say who owns a thing the first time you name it: Michelle's phone, Kristin's laptop." with "- Say who owns a thing the first time you name it: Michelle's phone."; replace the line "- Michelle's phone stores only Michelle's things. Kristin's laptop stores only Kristin's things." with "- Michelle's phone stores only Michelle's things."; delete the whole line "- Kristin's laptop is on the passenger seat of Kristin's truck." (with its newline). ADD is a deep copy of CTRL with ONE new line '- Michelle's phone showed a password prompt.' inserted directly after the line "- Michelle's phone is on the kitchen floor.". The system text, max_tokens and every other wire field stay byte-identical in every arm.
Because endpoint indexes are 1-based positions in the stage's input list, use states, _ = fp._prefix_states(variation, [index]) then states[index-1] as the state before that command (as capture_3a.py does with states[0]).

OUTPUT FILES. For each stage and arm write {OUT}/frozen-<stage>-<ARM>.json = {{"stage": <stage>, "arm": <ARM>, "endpoints": [{{"n": <endpoint id>, "command": <command>, "wire_payload": <payload>, "user_sha256": sha256 of payload['user']}}]}} (json ensure_ascii=False, indent=2). Also write {OUT}/provenance.json with keys: head (git rev-parse HEAD), dirty_files (git status --porcelain lines), package_sha256 (sha256 per file name of the shipped package files), frozen_sha256 (sha256 of each frozen file), variation_script (the stage inputs used). Print per endpoint and arm the system/user/total char counts and the delta from control. capture.py must be re-runnable (overwrite its own outputs, rebuild the pkg dirs from scratch with shutil.rmtree first).

REPLAY. {D}/replay.py: header '# ruff: noqa: E501'; function run(stage, out, first, last, send=None, only=None) and CLI `replay.py STAGE OUT FIRST LAST [--only N1,N2] [--confirm]` run from {R}. Stages and their (arms, endpoints): officer: CTRL,BIO x OFF6,OFF7; raw: BIO,ALIAS x RAW7; walt: CTRL,BIO x WALT; password: CTRL,SUB,ADD x PW (arm order exactly as listed). Samples: 0 is the unscored smoke sample, 1..12 are scored; assert 0 <= FIRST <= LAST <= 12. Row order is sample-major, then endpoint, then arm. `only` restricts endpoints. One request per cell, no retries or replacements, every exception kept as a row (error=str(e), narration=None). Row fields: stage, arm, n, sample, command, narration, error, raw (raw = body decoded utf-8 errors='replace', narration = bench.frozen_prompts._decode_replay_body(body)). Rewrite the whole rows JSON after every cell. Raise FileExistsError if OUT exists. Print f'requests {{count}}' (cells x samples); without --confirm print 'dry run: nothing sent' and exit 0 BEFORE building any transport. Transport (only when sending and send is None): import bench.frozen_prompts as fp; fp.SCENE = '1A'; from bench.core import load_dotenv; load_dotenv(); send = fp._default_transport({{'variation': '1a-password-officer'}}). Frozen payloads come verbatim from {OUT}/frozen-<stage>-<ARM>.json. The module must be importable without side effects (CLI under __main__) because the validator imports it with a stub transport.

HOW TO RUN (from {R}, never bare python): `TMPDIR=/tmp PYTHONPATH={R}:{R}/packages/worldkeeper/src {PY} scripts/ringer/1a-password-officer/capture.py`; `{PY} -m ruff format scripts/ringer/1a-password-officer/capture.py scripts/ringer/1a-password-officer/replay.py && {PY} -m ruff check scripts/ringer/1a-password-officer/`; then `TMPDIR=/tmp PYTHONPATH={R}:{R}/packages/worldkeeper/src {PY} scripts/ringer/1a-password-officer/validate_freeze.py` until it prints '1A FREEZE VALIDATION OK'. Some officer/walt BIO endpoints may legitimately produce NO prompt difference from control (the character line may not be introduced when the person is absent or unnamed): that is a finding, not a bug; do not force a difference. If a control prompt cannot be captured (an exception, or not exactly one narrator payload) report the exact error in {OUT}/capture-notes.txt and stop."""

check = f"""set -o pipefail
cd {R}
export TMPDIR=/tmp PYTHONPATH={R}:{R}/packages/worldkeeper/src
{PY} scripts/ringer/1a-password-officer/capture.py > /dev/null
{PY} -m ruff check scripts/ringer/1a-password-officer/
{PY} -m ruff format --check scripts/ringer/1a-password-officer/
{PY} scripts/ringer/1a-password-officer/validate_freeze.py
"""

task = {
    "key": "prepare-1a-password-officer",
    "task_type": "code-feature",
    "engine": "codex",
    "model": "gpt-5.6-luna",
    "engine_args": ["-c", "model_reasoning_effort=medium"],
    "max_attempts": 2,
    "timeout_s": 1800,
    "check_timeout_s": 600,
    "ownership": [f"{D}/capture.py", f"{D}/replay.py", f"{R}/bench/variations/1a-password-officer.json", f"{OUT}/"],
    "expect_files": [
        f"{D}/capture.py",
        f"{D}/replay.py",
        f"{R}/bench/variations/1a-password-officer.json",
        f"{OUT}/provenance.json",
    ],
    "spec": spec,
    "check": check,
    "verified": "the independent validator proves each arm differs from its control by exactly the planned bytes and the replay keeps order, caps and the dry-run guard",
}
manifest = {
    "run_name": "1a-password-officer-prepare",
    "workdir": "/home/bcorfman/dev/ringer-work/1a-password-officer-prepare",
    "max_parallel": 1,
    "worktrees": False,
    "repo": R,
    "tasks": [task],
}
Path(f"{D}/prepare-manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")
print("written")
