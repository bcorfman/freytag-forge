# ruff: noqa: E501
"""Build the one-task Ringer manifest that prepares comparison 1A2 (script + payload only; no billed request)."""

import json
from pathlib import Path

R = "/home/bcorfman/dev/freytag-forge"
D = f"{R}/scripts/ringer/lead-up-contradictions"
spec = f"""You are a code worker for the freytag-forge repository at {R}. Boundary: NO model call, NO network call, never git commit. You own only {D}/build_1a2.py (create), {D}/replay.py (small edit), and {R}/bench/results/lead-up-contradictions/frozen-1A2.json (written by your script). Do not read or edit {D}/validate_1a2.py or {D}/validate_replay.py (independent checks; only run them). Do not edit any other file.

GOAL: add comparison '1A2' = the c6 prompt with the FULL senior-official bio line (control, already frozen in {R}/bench/results/lead-up-contradictions/frozen-1A.json) versus the TRIMMED bio line.
1. Write {D}/build_1a2.py (header '# ruff: noqa: E501', zero model calls): load frozen-1A.json (envelope with one endpoint n='c6'); deep-copy it into frozen-1A2.json with variation 'lead-up-contradictions-1A2' and 'control' = '1A'; in the endpoint's wire_payload.user replace, on whole lines, EXACTLY this line (assert it occurs once)
`- Imprisoned senior official is a senior government official whom Charles has publicly blamed for the catastrophe. He is exhausted, observant, and has kept one piece of emergency authority out of Charles's hands.`
with EXACTLY this line
`- Imprisoned senior official is a senior government official whom Charles has publicly blamed for the catastrophe. He is exhausted and observant.`
Everything else (system, max_tokens, response_format, command, other lines) stays byte-identical. Set control_user_sha256 (sha256 hex of the 1A user text, utf-8) and arm_user_sha256 (of the 1A2 user text) on the endpoint, replacing any inherited values. Print the user char counts of both and the first 12 hex of sha256 of json.dumps(wire_payload, sort_keys=True, ensure_ascii=False) for each.
2. Edit {D}/replay.py minimally: accept CMP '1A2' (endpoint n='c6'); for '1A2' the control arm is the endpoint from frozen-1A.json labelled arm '1A' (not 'C0') and the comparison arm is frozen-1A2.json labelled '1A2'. Row order stays sample-major, control first. Behaviour for 1A, 1B, 2A must stay byte-for-byte identical (control labelled 'C0' from frozen-C0.json). Keep the guards (<=12 samples, refuse existing OUT, dry-run without --confirm) and the CLI choices must now include 1A2.
HOW TO RUN (from {R}): `{R}/.venv/bin/python scripts/ringer/lead-up-contradictions/build_1a2.py`, then `{R}/.venv/bin/python -m ruff format scripts/ringer/lead-up-contradictions/build_1a2.py scripts/ringer/lead-up-contradictions/replay.py && {R}/.venv/bin/python -m ruff check scripts/ringer/lead-up-contradictions/`, then `TMPDIR=/tmp PYTHONPATH={R}:{R}/packages/worldkeeper/src {R}/.venv/bin/python scripts/ringer/lead-up-contradictions/validate_1a2.py` and the same for validate_replay.py; fix until both print OK. Never use bare python."""
check = f"""set -o pipefail
cd {R}
export TMPDIR=/tmp PYTHONPATH={R}:{R}/packages/worldkeeper/src
{R}/.venv/bin/python scripts/ringer/lead-up-contradictions/build_1a2.py > /dev/null
{R}/.venv/bin/python -m ruff check scripts/ringer/lead-up-contradictions/build_1a2.py scripts/ringer/lead-up-contradictions/replay.py
{R}/.venv/bin/python -m ruff format --check scripts/ringer/lead-up-contradictions/build_1a2.py scripts/ringer/lead-up-contradictions/replay.py
{R}/.venv/bin/python scripts/ringer/lead-up-contradictions/validate_1a2.py
{R}/.venv/bin/python scripts/ringer/lead-up-contradictions/validate_replay.py
"""
task = {
    "key": "prepare-1a2",
    "task_type": "code-feature",
    "engine": "codex",
    "model": "gpt-5.6-luna",
    "engine_args": ["-c", "model_reasoning_effort=medium"],
    "max_attempts": 2,
    "timeout_s": 900,
    "check_timeout_s": 300,
    "ownership": [f"{D}/build_1a2.py", f"{D}/replay.py", f"{R}/bench/results/lead-up-contradictions/frozen-1A2.json"],
    "expect_files": [f"{D}/build_1a2.py", f"{R}/bench/results/lead-up-contradictions/frozen-1A2.json"],
    "spec": spec,
    "check": check,
    "verified": "independent validators prove the 1A2 payload differs from the 1A payload by exactly the bio line and the replay keeps 1A/1B/2A behaviour",
}
m = {
    "run_name": "lead-up-contradictions-prepare-1a2",
    "workdir": "/home/bcorfman/dev/ringer-work/lead-up-contradictions-prepare-1a2",
    "max_parallel": 1,
    "worktrees": False,
    "repo": R,
    "tasks": [task],
}
Path(f"{D}/prepare-1a2-manifest.json").write_text(json.dumps(m, indent=2) + "\n")
print("written")
