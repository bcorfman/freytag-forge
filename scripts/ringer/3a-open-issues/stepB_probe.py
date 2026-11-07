# ruff: noqa: E501
"""Step B probe manifest: current control vs R, 12 opening requests per arm (24 requests, ~88.8 neurons)."""

import json
from pathlib import Path

REPO = "/home/bcorfman/dev/freytag-forge"
RES = f"{REPO}/bench/results/richer-3a-probe"
PY = f"{REPO}/.venv/bin/python"

SPEC = f"""You are a probe operator on freytag-forge running a LIVE, BILLED opening-only probe against a hosted narration model. Your working directory is the real repository at {REPO}. This task runs WITHOUT a sandbox, so only your own care protects the repository.

HARD RULES. Edit, create or delete nothing except the two result files named below and {RES}/b-transcript.md. Do NOT touch storygame/, bench/*.py, bench/variations/, tests/, data/, docs/, scripts/, frontend/ or any dotfile. Do NOT run git add, commit, checkout, stash, reset, clean or push. Do NOT print, copy or echo .env (the script reads it by itself). Run each command EXACTLY ONCE: every extra run spends real money. If a command fails, do NOT edit code or retry; record exactly what happened in the transcript and stop. Do not replace or re-run a failed sample.

WHAT TO RUN (from {REPO}, in this order, one after the other):
1. TMPDIR=/tmp PYTHONPATH={REPO} {PY} {REPO}/scripts/ringer/3a-open-issues/opening_arms.py bench/variations/richer-3a-b-control.json 12 {RES}/b-control.json
2. The same command with bench/variations/richer-3a-b-r.json and output {RES}/b-r.json.
Each sample is ONE narration request (12 + 12 = 24 requests).

AFTER BOTH FINISH write {RES}/b-transcript.md with sections: ## Commands Run (exact text), ## Counts (rows, errors per arm), ## Observed Behavior (one line per sample: arm, index, the first 160 characters of the narration or the error). Do not interpret or score the narrations; the orchestrator reads them. The required observed marker is the word PROBED followed by the two row counts, e.g. `PROBED control=12 r=12`.
"""

CHECK = f"""set -o pipefail
cd {REPO}
{PY} - <<'PY'
import json, sys
rows = {{}}
for arm in ("b-control", "b-r"):
    try:
        rows[arm] = json.load(open("{RES}/" + arm + ".json"))
    except Exception as exc:
        print("WHY: cannot read", arm, exc); sys.exit(1)
    if len(rows[arm]) != 12:
        print("WHY:", arm, "has", len(rows[arm]), "rows, expected 12"); sys.exit(1)
    bad = [r["i"] for r in rows[arm] if r.get("error")]
    print(arm, "errors:", bad)
    if any(not r.get("prompt") for r in rows[arm]):
        print("WHY: a row lacks its prompt"); sys.exit(1)
c, r = rows["b-control"][0]["prompt"]["user"], rows["b-r"][0]["prompt"]["user"]
if c == r:
    print("WHY: control and R prompts are identical"); sys.exit(1)
if "Supporting the uprising is the immediate priority." not in r or "Reaching Michelle and supporting" in r:
    print("WHY: R prompt lacks the R wording"); sys.exit(1)
if "Reaching Michelle and supporting the uprising are immediate priorities." not in c:
    print("WHY: control prompt lacks the old wording"); sys.exit(1)
for arm in rows:
    if len({{json.dumps(x["prompt"], sort_keys=True) for x in rows[arm]}}) != 1:
        print("NOTE: prompts differ within", arm)
print("ok: 12+12 rows, prompts differ as intended")
PY
grep -q "PROBED control=12 r=12" {RES}/b-transcript.md || {{ echo "WHY: transcript lacks the PROBED marker"; exit 1; }}
{PY} {REPO}/bench/checks/no_source_drift.py {REPO} bench/results/ 2>&1 | tail -3
"""

manifest = {
    "run_name": "3a-open-issues-stepB-probe",
    "workdir": "/home/bcorfman/dev/ringer-work/3a-open-issues-stepB-probe",
    "max_parallel": 1,
    "worktrees": False,
    "repo": REPO,
    "tasks": [
        {
            "key": "b-probe",
            "task_type": "probe",
            "engine": "codex",
            "model": "gpt-5.6-luna",
            "full_access": True,
            "engine_args": ["-c", "model_reasoning_effort=low"],
            "max_attempts": 1,
            "timeout_s": 3000,
            "check_timeout_s": 300,
            "spec": SPEC,
            "check": CHECK,
            "expect_files": [f"{RES}/b-transcript.md"],
            "verified": "24 recorded requests, 12 per arm, prompts differ as intended, no tracked source changed",
        }
    ],
}
Path(__file__).with_name("stepB-probe-manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")
print("wrote")
