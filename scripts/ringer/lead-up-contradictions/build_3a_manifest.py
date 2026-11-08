# ruff: noqa: E501
"""Build the one-task Ringer manifest that prepares comparison 3A (current vs candidate reunion delivery at R1 and R2). No billed request."""

import json
from pathlib import Path

R = "/home/bcorfman/dev/freytag-forge"
D = f"{R}/scripts/ringer/lead-up-contradictions"
OUT = f"{R}/bench/results/lead-up-contradictions"
HEAD = 'Michelle pulls Kristin close and holds her there. "You\'re here," she says, her voice breaking. "You\'re really here." Kristin holds on just as hard. For one unhurried moment nobody asks anything of either of them.'
R1 = (
    HEAD
    + " When they let go, Michelle wipes her eyes and turns back to the captives. They are awake: the dose they were given is for the trip, and it wears off in the detention block. She returns to sending her coded messages, and she points toward the medical level where the experiment records await."
)
R2 = (
    HEAD
    + " When they let go, Michelle wipes her eyes and explains that freeing this block means little without exposing the other sites. She points toward the medical level, where the experiment records wait."
)

spec = f"""You are a code worker for the freytag-forge repository at {R}. Boundary: NO model call, NO network call, never git commit. You own only {D}/capture_3a.py (create), {D}/replay_3a.py (create), and {OUT}/frozen-3A-CUR.json and {OUT}/frozen-3A-CAND.json (written by capture_3a.py). Do not read or edit {D}/validate_3a.py (the independent check; only run it).

GOAL: freeze, from the CURRENT working tree, the two reunion-turn narrator payloads and a candidate-delivery arm, for an offline-prepared billed comparison.
1. {D}/capture_3a.py (header '# ruff: noqa: E501', zero model calls). Follow {R}/scripts/ringer/shared-narrator/gue1_capture.py exactly for how it builds payloads (bench.frozen_prompts, SCENE '3A', variation file {R}/bench/variations/richer-3a-live.json, prefix states from fp._prefix_states(variation, [1, 2]), states[0], fp._capture_wire_payload). Endpoints: R1 = command 'Free the captives.' (the variation's first scripted input; it selects k_sl_3a_a_r1) and R2 = 'Ask Michelle about the other sites.' (selects k_sl_3a_a_r2), both at the 3A entry state. For each endpoint take the real payload; the user text has exactly one line starting '- Right after your story, the game will add this: ' (assert). That payload IS arm CUR (do not edit it). Arm CAND is a deep copy whose delivery line is replaced, on that one line only, by '- Right after your story, the game will add this: ' + the candidate text below. Write {OUT}/frozen-3A-CUR.json and {OUT}/frozen-3A-CAND.json as {{"variation": "richer-3a-live", "arm": "CUR"|"CAND", "endpoints": [{{"n": "R1"|"R2", "command": ..., "wire_payload": ..., "user_sha256": ...}}]}} (json ensure_ascii=False, indent=2). Print per endpoint the system/user/total char counts of CUR and CAND and the delta. Candidate texts (use straight quotes exactly as shown):
R1: {R1}
R2: {R2}
2. {D}/replay_3a.py (header '# ruff: noqa: E501'), modelled on {D}/replay.py and {R}/scripts/ringer/shared-narrator/gue1_replay.py: function `run(out, first, last, send=None)` and CLI `replay_3a.py OUT FIRST LAST [--confirm]` from the repo root. Row order is sample-major, then endpoint R1 then R2, then arm CUR then CAND. Payloads come verbatim from frozen-3A-CUR.json / frozen-3A-CAND.json. One request per cell, no retries or replacements, every exception kept as a row (error=str(e), narration=None). Row fields: arm, n, sample, command, narration, error, raw (raw = body decoded utf-8 errors='replace', narration = bench.frozen_prompts._decode_replay_body(body)). Rewrite the whole rows JSON after every cell. Guards: assert 1 <= FIRST <= LAST <= 12 (max 48 requests); raise FileExistsError if OUT exists; print f'requests {{count}}'; without --confirm print 'dry run: nothing sent' and exit 0 BEFORE building any transport. Transport (only when sending and send is None): `import bench.frozen_prompts as fp; fp.SCENE = '3A'; from bench.core import load_dotenv; load_dotenv(); send = fp._default_transport({{'variation': 'richer-3a-live'}})`. Importable without side effects (CLI under `if __name__ == '__main__'`; repo root on sys.path).
HOW TO RUN (from {R}): `TMPDIR=/tmp PYTHONPATH={R}:{R}/packages/worldkeeper/src {R}/.venv/bin/python scripts/ringer/lead-up-contradictions/capture_3a.py`; `{R}/.venv/bin/python -m ruff format scripts/ringer/lead-up-contradictions/capture_3a.py scripts/ringer/lead-up-contradictions/replay_3a.py && {R}/.venv/bin/python -m ruff check scripts/ringer/lead-up-contradictions/`; then `TMPDIR=/tmp PYTHONPATH={R}:{R}/packages/worldkeeper/src {R}/.venv/bin/python scripts/ringer/lead-up-contradictions/validate_3a.py` until it prints 3A VALIDATION OK. Never use bare python."""

check = f"""set -o pipefail
cd {R}
export TMPDIR=/tmp PYTHONPATH={R}:{R}/packages/worldkeeper/src
{R}/.venv/bin/python scripts/ringer/lead-up-contradictions/capture_3a.py > /dev/null
{R}/.venv/bin/python -m ruff check scripts/ringer/lead-up-contradictions/capture_3a.py scripts/ringer/lead-up-contradictions/replay_3a.py
{R}/.venv/bin/python -m ruff format --check scripts/ringer/lead-up-contradictions/capture_3a.py scripts/ringer/lead-up-contradictions/replay_3a.py
{R}/.venv/bin/python scripts/ringer/lead-up-contradictions/validate_3a.py
"""

task = {
    "key": "prepare-3a",
    "task_type": "code-feature",
    "engine": "codex",
    "model": "gpt-5.6-luna",
    "engine_args": ["-c", "model_reasoning_effort=medium"],
    "max_attempts": 2,
    "timeout_s": 1200,
    "check_timeout_s": 600,
    "ownership": [f"{D}/capture_3a.py", f"{D}/replay_3a.py", f"{OUT}/frozen-3A-CUR.json", f"{OUT}/frozen-3A-CAND.json"],
    "expect_files": [
        f"{D}/capture_3a.py",
        f"{D}/replay_3a.py",
        f"{OUT}/frozen-3A-CUR.json",
        f"{OUT}/frozen-3A-CAND.json",
    ],
    "spec": spec,
    "check": check,
    "verified": "an independent validator proves CUR is the current tree, CAND differs by exactly the delivery line, and the replay keeps order, caps and the dry-run guard",
}
m = {
    "run_name": "lead-up-contradictions-prepare-3a",
    "workdir": "/home/bcorfman/dev/ringer-work/lead-up-contradictions-prepare-3a",
    "max_parallel": 1,
    "worktrees": False,
    "repo": R,
    "tasks": [task],
}
Path(f"{D}/prepare-3a-manifest.json").write_text(json.dumps(m, indent=2) + "\n")
print("written")
