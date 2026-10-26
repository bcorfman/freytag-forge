# ruff: noqa: E501
"""Generate the Ringer manifest that builds the narration-defect probe (held-card re-find, seat invention)."""

from __future__ import annotations

import json
from pathlib import Path

REPO = "/home/bcorfman/dev/freytag-forge"
OUT = Path(REPO) / "scripts/ringer/environment_narration/build-defect-probe.json"
SCRIPT = "scripts/ringer/environment_narration/defect_probe.py"
TESTS = "tests/test_defect_probe.py"
PROMPTS = "scripts/ringer/environment_narration/defect_probe/prompts.json"
LOCK = "scripts/ringer/environment_narration/defect_probe/prompts.lock.json"
PREREG = ".plans/grounded-llm-environment-narration/t8-narration-defects-prereg.md"
SOURCE_SHA = "aaca5776240d1a347bc21c7c61c609ffa7be3f3ffc8f757b591ff3702e4a447b"

SPEC = (
    "You are working in freytag-forge (Python 3.12). Working directory: /home/bcorfman/dev/freytag-forge. "
    "export PYTHONPATH=/home/bcorfman/dev/freytag-forge TMPDIR=/tmp; run `.venv/bin/python` (never uv). "
    "Run tests with `env -u CLOUDFLARE_WORKER_URL -u CLOUDFLARE_WORKER_TOKEN .venv/bin/python -m pytest -q -p no:cacheprovider --no-cov <files>`. "
    "NEVER make a network call and NEVER run a live (--run --confirm) invocation: tests must patch urlopen/_call so any real call fails the test. Do not git commit. NEVER print or write any credential. NO regular expressions in new code. "
    f"YOU MAY EDIT ONLY: {SCRIPT}, {TESTS}, and the generated files {PROMPTS} and {LOCK} (the script writes them). Do not edit smoke_direct.py or anything else. "
    "Write the tests FIRST, run them, confirm they fail for the right reason, then implement. Run ruff check and ruff format on the script and the test at the end. "
    f"READ FIRST: {PREREG} (the approved design; follow it exactly) and scripts/ringer/environment_narration/smoke_direct.py and holder_wording_probe.py (reuse their conventions: _call, _stop_reason, _redact, _write_json, the VARIANTS profile 'llama-3.3-70b-default-temp' = 70B, JSON mode off, no temperature, import them with `from scripts.ringer.environment_narration.smoke_direct import ...`; lock file pattern from holder_wording_probe.py). "
    "WHAT TO BUILD: one CLI module `defect_probe.py` with these modes. "
    "(1) `--build-prompts [--rows-source PATH] [--source-sha256 HEX] [--probe-dir DIR]`: read the shadow-sample rows file (default bench/results/environment-narration/shadow-sample/full/rows/rows.json), REFUSE unless its sha256 equals "
    f"{SOURCE_SHA} (the --source-sha256 option overrides this only for tests). From replicate 0 (the first element) take the turn whose turn_index is 3 and whose input is 'feel under the drawer' (prompt id PA) and the turn whose turn_index is 8 and whose input is 'inspect the passenger seat' (prompt id PB); for each, the narrator prompt is the first entry of the turn's `prompts` whose `system` starts with 'You are the narrator' (abort with a clear error if a turn or prompt is missing). "
    "Build the 8 arms of the prereg from a module-level data table ARMS (the only place story words may appear): A0 control, A1 delete the line starting '- Dr. Michelle McGehee may say this aloud:', A2 = A1 plus delete the line starting '- Show these in your reply:', A3 = A1 plus add the line '- Nothing else is under the drawer. Searching under the drawer finds nothing more.'; B0 control, B1 delete the line starting '- What presses on Kristin now:', B2 add the line '- Nothing is left in or under the passenger seat. Searching the passenger seat finds nothing.', B3 = B1 plus B2's add. "
    "Edits touch the USER prompt only and are line based: a delete matches lines of the user text whose text starts with the given prefix and MUST match exactly one line (else abort naming the arm and prefix); an add inserts the new line immediately after the line 'CONSTRAINTS:' (that is where the product inserts constraint lines) and MUST find exactly one 'CONSTRAINTS:' line. Deleting a bullet line removes the whole line including its newline. The system prompt is never changed. "
    f"Write {PROMPTS} (sorted keys, indent 2: source_sha256, prompts PA/PB with system, user, turn_index, input; arms with id, defect letter, prompt_id, edits, system, user, and a unified diff string against the control user text) and {LOCK} ({{sha256 of the prompts.json bytes, count}}). Building twice gives byte-identical files. The directory is `defect_probe/` next to the script unless --probe-dir is given. "
    "(2) `--dry-run --stage 1|2 [--arms A1,B1] [--probe-dir DIR]`: verify the lock (refuse on mismatch or missing), print the plan: calls per arm, total calls, estimated USD, and for each arm the diff. Stage 1 = every arm x samples 0..9 (80 calls). Stage 2 requires --arms listing one or more NON-control candidate arm ids; the plan is each candidate plus its defect's control (A0 for A arms, B0 for B arms; each control once) x samples 10..24 (15 each). Call order is a deterministic shuffle: random.Random(1729) over the list of (arm, sample); call_index runs from 1. Estimated USD per call = (len(system)+len(user))/4 prompt tokens x 0.293 + 150 completion tokens x 2.253, per million. "
    "(3) `--run --confirm --stage 1|2 [--arms ...] --max-calls N --max-usd X --out ROWS.json`: refuse without --confirm, without --max-usd, when N < planned calls, when the estimate exceeds X, on a lock mismatch, or when CLOUDFLARE_ACCOUNT_ID and (CLOUDFLARE_AI_TOKEN or CF_API_TOKEN) are missing (check them after the other refusals). Run the calls sequentially with smoke_direct._call using variant 'llama-3.3-70b-default-temp' (call dict keys as smoke_direct expects: call_index, variant, model, start=prompt id, context=arm id, sample, system, user, plus request_bytes set by _call). One attempt per call, no retries, no replacement. After every call write {schema, stage, rows, stop_reason} to --out (all text passed through _redact). Stop (stop_reason set, partial rows kept) on _stop_reason (auth/429), on 3 consecutive rows with usable false, and when the running sum of rows' actual_cost_usd exceeds --max-usd (stop_reason BUDGET). "
    "(4) `--sheet --rows ROWS.json [--rows ...] --out SHEET.md --key KEY.json`: blind reading sheet. Assign each row a random id r01.. using a seeded shuffle; the sheet shows for each id only the defect letter (A or B) and the reply text (narration, else final_text, else '(no text)'); it must contain NO arm id, sample number or call index. KEY.json maps id to arm, sample, call_index, source file; print the key file's SHA-256 so it can be recorded before reading. "
    "(5) `--report --rows ROWS.json [--rows ...] --key KEY.json --labels LABELS.json --out REPORT.md`: LABELS.json is {id: {verdict: 'pass'|'fail'|'unusable', note: str}}; refuse (nonzero exit, clear message) if any key id lacks a label or a label id is not in the key. Print per arm: n, fails, passes, unusable, Wilson 95% upper bound of the failure rate, strict/repaired JSON validity if the rows carry it, latency median and max, summed actual cost. Then the prereg rules: control reproduces the defect if control fails/n >= 0.3 in stage 1 (3 of 10) [in a report over combined 25-sample rows use fails/n >= 0.25]; an arm advances at stage 1 when fails <= 1 of its n=10; the candidate per defect is the simplest advancing arm in the order A1,A2,A3 and B1,B2,B3 (print 'not reproduced' and no candidate if the control does not reproduce). If an arm has n = 25 (stage 1 + stage 2 rows) print the stage 2 gate: PASS when fails <= 1 of 25 and the control reproduced (fails/n >= 0.25); else FAIL. Use the sum of rows per arm to decide which rule applies (n == 10 -> stage 1 rules, n == 25 -> stage 2 gate). "
    "TESTS (tests/test_defect_probe.py; hermetic; build a tiny synthetic rows file in tmp_path with a different, made-up vocabulary for the arm TABLE by monkeypatching ARMS where needed so that engine logic is shown not to depend on story words; also test the real ARMS table against a synthetic rows file shaped like the real one): extraction picks turn 3 and turn 8 of replicate 0 only; wrong source hash is refused; a delete prefix matching zero or two lines aborts; an add with no CONSTRAINTS line aborts; each real arm's diff against its control is exactly the intended one line change (A3: one deletion plus one addition relative to A0, B3 likewise); build is byte-identical twice; lock mismatch refuses --dry-run and --run; stage 1 plan = 80 calls with 10 per arm, stage 2 with --arms A1,B1 = 60 calls, stage 2 without --arms or with a control id is refused; order is deterministic and interleaved (no arm's calls are contiguous for all 10 samples); --run refusals (no --confirm, no --max-usd, max-calls too small, estimate above max-usd); with _call monkeypatched to a fake: rows written after each call, stops on a 429 row, stops after 3 consecutive unusable rows, stops with BUDGET when summed cost exceeds --max-usd, partial rows kept, a credential set in the environment never appears in the rows file; urlopen patched to raise proves no real network use; sheet contains no arm id, 'sample' or call index and the key resolves every id; report: control-not-reproduced case, advance rule at 1 of 10 vs 2 of 10, simplest-candidate preference, stage 2 gate at 1 of 25 vs 2 of 25, incomplete labels refused. "
    "AFTER the tests pass, run the REAL build once offline: `.venv/bin/python scripts/ringer/environment_narration/defect_probe.py --build-prompts` (it reads the gitignored rows file already on disk; no network), then `--dry-run --stage 1` and `--dry-run --stage 2 --arms A1,B1`, and fix anything that fails. Then print the real arm diffs from the dry run so they can be read."
)

CHECK = (
    "cd /home/bcorfman/dev/freytag-forge && export PYTHONPATH=/home/bcorfman/dev/freytag-forge TMPDIR=/tmp && set -o pipefail && "
    f"env -u CLOUDFLARE_WORKER_URL -u CLOUDFLARE_WORKER_TOKEN .venv/bin/python -m pytest -q -p no:cacheprovider --no-cov {TESTS} scripts/ringer/transcript_1a/test_live_baseline.py tests/test_holder_wording_probe.py 2>&1 | tee /tmp/defect-probe.out | tail -8 && "
    "! grep -Eq '[0-9]+ (failed|error)' /tmp/defect-probe.out && "
    f"test -s {PROMPTS} && test -s {LOCK} && "
    f".venv/bin/python scripts/ringer/environment_narration/defect_probe.py --dry-run --stage 1 2>&1 | tee /tmp/defect-dry1.out | grep -E '^80 calls|80 calls' && "
    f".venv/bin/python scripts/ringer/environment_narration/defect_probe.py --dry-run --stage 2 --arms A1,B1 2>&1 | grep -E '60 calls' && "
    "(.venv/bin/python - <<'PYX'\n"
    "import hashlib, json\n"
    f"doc = json.load(open('{PROMPTS}'))\n"
    f"lock = json.load(open('{LOCK}'))\n"
    f"assert hashlib.sha256(open('{PROMPTS}','rb').read()).hexdigest() == lock['sha256'], 'lock mismatch'\n"
    f"assert doc['source_sha256'] == '{SOURCE_SHA}'\n"
    "arms = doc['arms']\n"
    "assert sorted(arms) == ['A0','A1','A2','A3','B0','B1','B2','B3'], sorted(arms)\n"
    "for a, c in (('A1','A0'),('A2','A0'),('A3','A0'),('B1','B0'),('B2','B0'),('B3','B0')):\n"
    "    old = arms[c]['user'].splitlines(); new = arms[a]['user'].splitlines()\n"
    "    removed = [l for l in old if l not in new]; added = [l for l in new if l not in old]\n"
    "    print(a, 'removed', len(removed), 'added', len(added))\n"
    "    assert arms[a]['system'] == arms[c]['system']\n"
    "assert 'may say this aloud' not in arms['A1']['user'] and 'may say this aloud' in arms['A0']['user']\n"
    "assert 'What presses on Kristin now' not in arms['B1']['user'] and 'What presses on Kristin now' in arms['B0']['user']\n"
    "print('prompts ok')\n"
    "PYX\n"
    ") && ! .venv/bin/python scripts/ringer/environment_narration/defect_probe.py --run --stage 1 --out /tmp/defect-noconfirm.json >/dev/null 2>&1 && "
    "! grep -nE '\\bre\\.(compile|search|match|sub|findall|fullmatch)|import re\\b' scripts/ringer/environment_narration/defect_probe.py && "
    f".venv/bin/python -m ruff check {SCRIPT} {TESTS} && .venv/bin/python -m ruff format --check {SCRIPT} {TESTS}"
)

manifest = {
    "run_name": "grounded-environment-narration",
    "workdir": "/home/bcorfman/dev/ringer-work/grounded-environment-narration-defect-probe",
    "max_parallel": 1,
    "worktrees": False,
    "repo": REPO,
    "tasks": [
        {
            "key": "build-defect-probe",
            "task_type": "code-feature",
            "engine": "codex",
            "model": "gpt-5.6-luna",
            "engine_args": ["-c", "model_reasoning_effort=high"],
            "full_access": True,
            "max_attempts": 2,
            "timeout_s": 3600,
            "check_timeout_s": 1200,
            "ownership": [SCRIPT, TESTS, PROMPTS, LOCK],
            "expect_files": [f"{REPO}/{SCRIPT}", f"{REPO}/{TESTS}", f"{REPO}/{PROMPTS}", f"{REPO}/{LOCK}"],
            "spec": SPEC,
            "check": CHECK,
            "verified": "probe builds 8 single-edit arms from the frozen shadow-sample prompts, plans 80/60 calls, refuses unsafe runs, and reports by the preregistered rules",
        }
    ],
}

if __name__ == "__main__":
    OUT.write_text(json.dumps(manifest, indent=2) + "\n")
