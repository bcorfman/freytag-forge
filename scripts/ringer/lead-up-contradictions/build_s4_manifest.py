# ruff: noqa: E501
"""Build the one-task Ringer manifest that prepares comparison S4 (current vs candidate lead-up boundary rule). No billed request."""

import json
from pathlib import Path

R = "/home/bcorfman/dev/freytag-forge"
D = f"{R}/scripts/ringer/lead-up-contradictions"
OUT = f"{R}/bench/results/lead-up-contradictions"
RULE_CUR = "- Write only what leads up to it. Do not have Kristin find anything else."
RULE_NEW = "- Write the lead-up to the text above. Stop before its first action or spoken words. Leave its discoveries for that text."
BIO = "- Imprisoned senior official is a senior government official whom Charles has publicly blamed for the catastrophe. He is exhausted and observant."

spec = f"""You are a code worker for the freytag-forge repository at {R}. Boundary: NO model call, NO network call, never git commit. You own only {D}/capture_s4.py (create), {D}/replay_s4.py (create), and {OUT}/frozen-S4-CUR.json and {OUT}/frozen-S4-CAND.json (written by capture_s4.py). Do not read or edit {D}/validate_s4.py (the independent check; only run it).

GOAL: freeze six narrator payloads (arm CUR) and a candidate arm CAND that differs only by one rule line, for an offline-prepared billed comparison of the lead-up boundary rule.
1. {D}/capture_s4.py (header '# ruff: noqa: E501', zero model calls). Endpoints, in this order, key n: 'c1','c2','c5','c6','c8','h2'.
 - c1, c2, c5, c6, c8 come from the live FINAL run records {R}/bench/results/shared-narrator/live/final-r1/all-turn-records.json, runs[0].turns[i] with i = 0, 1, 4, 5, 7 respectively (player_input = command, prompt_system, prompt_user). Do not replay or regenerate them from a scripted prefix. Take max_tokens and response_format from {OUT}/frozen-C0.json endpoint c1 wire_payload (all endpoints there agree; assert it).
 - Bring each FINAL user text up to the current story with exactly these text-only transforms, in this order, on whole lines: (a) after the line that starts '- Brandon Corfman is' insert one new line: {BIO}  ; (b) for c2 only, replace the line that starts '- Right after your story, the game will add this: ' by that prefix plus the CURRENT text of the delivery variant of knowledge entry k_sl_3a_f_r1 whose requires list contains held_transfers_seen (read it with yaml from {R}/data/stories/continuity-initiative/knowledge.yaml, strip()); (c) rename: 'Coded announcement' -> 'Secret message', 'coded announcement' -> 'secret message' (so plurals follow), 'Coded words' -> 'Code words', 'coded words' -> 'code words'. validate_s4.py recomputes exactly this.
 - h2 is the 1C discovery turn 'Check the loading docks for signs of activity.' captured offline from the CURRENT tree exactly as {R}/scripts/ringer/shared-narrator/baseline_capture.py captures scene 1C (variation {R}/bench/results/shared-narrator/baseline/variation-1C.json, fp.SCENE = '1C', fp._prefix_states(variation, [1, 2]), the state before the second input, RuntimeEngine turn with the stubbed provider; take the first narration payload, which must select handoff k_sl_1c_a_r1). Its system/user come from that capture; set its max_tokens/response_format to the same values as the others.
 - Every payload's user text has exactly one line equal to '{RULE_CUR}' (assert). Arm CUR is the payload unchanged; arm CAND is a deep copy whose only change is that one line replaced by '{RULE_NEW}'.
 - Write {OUT}/frozen-S4-CUR.json and {OUT}/frozen-S4-CAND.json as {{"variation": "lead-up-s4", "arm": "CUR"|"CAND", "endpoints": [{{"n":..., "command":..., "wire_payload": {{system,user,max_tokens,response_format}}, "user_sha256":...}}]}} (json ensure_ascii=False, indent=2). Print per endpoint the system/user/total character counts of CUR and CAND and the delta.
2. {D}/replay_s4.py (header '# ruff: noqa: E501'), modelled on {D}/replay_3a.py: function `run(out, first, last, send=None)` and CLI `replay_s4.py OUT FIRST LAST [--confirm]` from the repo root. Row order is sample-major, then endpoint in the order above, then arm CUR then CAND. Payloads come verbatim from the two frozen files. One request per cell, no retries or replacements, every exception kept as a row (error=str(e), narration=None). Row fields: arm, n, sample, command, narration, error, raw (raw = body decoded utf-8 errors='replace', narration = bench.frozen_prompts._decode_replay_body(body)). Rewrite the whole rows JSON after every cell. Guards: assert 1 <= FIRST <= LAST <= 12 (max 144 requests); raise FileExistsError if OUT exists; print f'requests {{count}}'; without --confirm print 'dry run: nothing sent' and exit 0 BEFORE building any transport. Transport only when sending and send is None: copy exactly what replay_3a.py does (variation 'richer-3a-live'; a 1C payload goes through the same transport because the transport only sends the payload).
HOW TO RUN (from {R}): `TMPDIR=/tmp PYTHONPATH={R}:{R}/packages/worldkeeper/src {R}/.venv/bin/python scripts/ringer/lead-up-contradictions/capture_s4.py`; `{R}/.venv/bin/python -m ruff format scripts/ringer/lead-up-contradictions/capture_s4.py scripts/ringer/lead-up-contradictions/replay_s4.py && {R}/.venv/bin/python -m ruff check scripts/ringer/lead-up-contradictions/`; then `TMPDIR=/tmp PYTHONPATH={R}:{R}/packages/worldkeeper/src {R}/.venv/bin/python scripts/ringer/lead-up-contradictions/validate_s4.py` until it prints S4 VALIDATION OK. Never use bare python."""

check = f"""set -o pipefail
cd {R}
export TMPDIR=/tmp PYTHONPATH={R}:{R}/packages/worldkeeper/src
{R}/.venv/bin/python scripts/ringer/lead-up-contradictions/capture_s4.py > /dev/null
{R}/.venv/bin/python -m ruff check scripts/ringer/lead-up-contradictions/capture_s4.py scripts/ringer/lead-up-contradictions/replay_s4.py
{R}/.venv/bin/python -m ruff format --check scripts/ringer/lead-up-contradictions/capture_s4.py scripts/ringer/lead-up-contradictions/replay_s4.py
{R}/.venv/bin/python scripts/ringer/lead-up-contradictions/validate_s4.py
"""

task = {
    "key": "prepare-s4",
    "task_type": "code-feature",
    "engine": "codex",
    "model": "gpt-5.6-luna",
    "engine_args": ["-c", "model_reasoning_effort=medium"],
    "max_attempts": 2,
    "timeout_s": 1500,
    "check_timeout_s": 600,
    "ownership": [f"{D}/capture_s4.py", f"{D}/replay_s4.py", f"{OUT}/frozen-S4-CUR.json", f"{OUT}/frozen-S4-CAND.json"],
    "expect_files": [
        f"{D}/capture_s4.py",
        f"{D}/replay_s4.py",
        f"{OUT}/frozen-S4-CUR.json",
        f"{OUT}/frozen-S4-CAND.json",
    ],
    "spec": spec,
    "check": check,
    "verified": "an independent validator recomputes each CUR user text from the FINAL records, proves CAND differs by exactly the rule line, and checks the replay's order, caps and dry-run guard",
}
m = {
    "run_name": "lead-up-contradictions-prepare-s4",
    "workdir": "/home/bcorfman/dev/ringer-work/lead-up-contradictions-prepare-s4",
    "max_parallel": 1,
    "worktrees": False,
    "repo": R,
    "tasks": [task],
}
Path(f"{D}/prepare-s4-manifest.json").write_text(json.dumps(m, indent=2) + "\n")
print("written")
