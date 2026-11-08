# ruff: noqa: E501
"""Ringer task: re-freeze the 1A officer/raw arms with neutral filler turns (no earned knowledge in the officer prompt)."""

import json
from pathlib import Path

R = "/home/bcorfman/dev/freytag-forge"
D = f"{R}/scripts/ringer/1a-password-officer"
PY = f"{R}/.venv/bin/python"

spec = f"""You are a code worker for the freytag-forge repository at {R}. Boundary: NO model call, NO network call, never git commit. You own ONLY {D}/capture.py and the files it writes under {R}/bench/results/1a-password-officer/. Do NOT edit {D}/validate_freeze.py or {D}/replay.py.

WHY. The officer and raw scripts in capture.py use 'Look at the wall calendar.' and 'Look at the photograph.' as filler commands 6 and 7. Those commands EARN the kitchen-walls knowledge, which then appears in the officer's prompt as '- Officer Reyes may say this aloud: Kristin reads the kitchen walls ...'. The original session never did that, so the frozen prompt is not faithful. Replace those two filler commands with neutral ones that earn no knowledge: 'Turn on the phone.' (command 6) and 'Turn off the phone.' (command 7). The nine OFFICER_INPUTS become exactly: 'Turn on the phone.', 'Unlock the phone.', 'Type in the password.', "Type the password into Michelle's phone.", 'Turn off the phone.', 'Turn on the phone.', 'Turn off the phone.', 'Greet the officer.', 'Ask the officer where Dr. McGehee is.'. RAW_INPUTS stays the first eight of OFFICER_INPUTS plus 'Officer, do you know where Dr. McGehee is?'. Endpoints, the password script and the walt script stay as they are. Then re-run capture so frozen files, arm packages and provenance.json are regenerated, and make the validator pass.
HOW TO RUN (from {R}; never bare python): `TMPDIR=/tmp PYTHONPATH={R}:{R}/packages/worldkeeper/src {PY} {D}/capture.py`; `{PY} -m ruff format {D}/capture.py && {PY} -m ruff check {D}`; `TMPDIR=/tmp PYTHONPATH={R}:{R}/packages/worldkeeper/src {PY} {D}/validate_freeze.py` until it prints '1A FREEZE VALIDATION OK'."""

check = f"""set -o pipefail
cd {R}
export TMPDIR=/tmp PYTHONPATH={R}:{R}/packages/worldkeeper/src
{PY} {D}/capture.py > /dev/null
{PY} -m ruff check {D}
{PY} -m ruff format --check {D}
{PY} {D}/validate_freeze.py
{PY} - <<'PY'
import json
for stage, arm, n in (('officer', 'CTRL', 'OFF6'), ('officer', 'CTRL', 'OFF7'), ('raw', 'BIO', 'RAW7')):
    e = {{x['n']: x for x in json.load(open('bench/results/1a-password-officer/frozen-%s-%s.json' % (stage, arm)))['endpoints']}}[n]
    u = e['wire_payload']['user']
    assert 'may say this aloud' not in u, 'earned knowledge leaked into the officer prompt'
    assert any('patrol officer' in l and 'workstation' in l for l in u.split(chr(10))), 'officer should be at the workstation'
    print(stage, arm, n, 'ok')
PY
"""

task = {
    "key": "refreeze-neutral-1a-arms",
    "task_type": "code-fix",
    "engine": "codex",
    "model": "gpt-5.6-luna",
    "engine_args": ["-c", "model_reasoning_effort=low"],
    "max_attempts": 2,
    "timeout_s": 1200,
    "check_timeout_s": 600,
    "ownership": [f"{D}/capture.py", f"{R}/bench/results/1a-password-officer/"],
    "expect_files": [f"{D}/capture.py"],
    "spec": spec,
    "check": check,
    "verified": "officer prompts contain no earned-knowledge speaker line; validator passes",
}
manifest = {
    "run_name": "1a-password-officer-prepare",
    "workdir": "/home/bcorfman/dev/ringer-work/1a-password-officer-prepare",
    "max_parallel": 1,
    "worktrees": False,
    "repo": R,
    "tasks": [task],
}
Path(f"{D}/refreeze2-manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")
print("written")
