# ruff: noqa: E501
"""Generate the Ringer manifest that fixes two defects found in the sample-2 report on real rows."""

from __future__ import annotations

import json
from pathlib import Path

REPO = "/home/bcorfman/dev/freytag-forge"
ENV = "scripts/ringer/environment_narration"
OUT = Path(REPO) / ENV / "build-shadow2-report-fix.json"

SPEC = (
    "You are working in freytag-forge (Python 3.12). Working directory: /home/bcorfman/dev/freytag-forge. "
    "export PYTHONPATH=/home/bcorfman/dev/freytag-forge TMPDIR=/tmp; run `.venv/bin/python` (never uv). "
    "Run tests with `env -u CLOUDFLARE_WORKER_URL -u CLOUDFLARE_WORKER_TOKEN .venv/bin/python -m pytest -q -p no:cacheprovider --no-cov tests/test_shadow_report.py`. "
    f"YOU MAY EDIT ONLY: {ENV}/shadow_report.py and tests/test_shadow_report.py. No network, no model call, never read anything under bench/results/ (gitignored; tests use synthetic rows only). Do not git commit. NO regular expressions in new code. "
    "METHOD: write the failing tests first, confirm they fail, then fix. "
    "CONTEXT. The sample-2 report (`shadow_report.py join`) was run on the REAL rows of a live run and two defects showed. "
    "DEFECT 1, clause 8 'invented object on the empty seat'. `_seat_is_empty` compares each value of the row's `places_before` (entity IDS such as 'truck_passenger_seat') with `observation_request['focus']`; in real rows the focus is the DISPLAY NAME ('passenger seat'), so nothing ever matched and every seat turn counted as empty (6 counted, 2 truly empty). Fix: a seat turn is empty exactly when the verifier required nothing at the seat, i.e. `observation_relations` is an empty list (a turn with a non-empty list has something on it, a None list is not an observation turn). Remove the places_before/focus comparison. Update the tests: build seat turns the way real rows look (focus is a display name like 'passenger seat', `places_before` maps ids to ids, a laptop-on-seat turn has one relation, an empty seat turn has an empty relations list and shadow outcome 'no_relations'); a turn with a relation on the seat must NOT count toward clause 8 even though its focus is a name; thresholds unchanged (n >= 6, at most 1). "
    "DEFECT 2, clause 6 'held-item mention relations'. Held items now yield MENTION-ONLY relations (the relation has a `thing` and an empty place and an empty holder), so selecting relations by non-empty holder always gives 0. Fix: clause 6 reports the mention-only relations (empty place AND empty holder) as a table by thing name with columns accepted-by-hand-label counts: for each thing, number labelled true and number labelled false, plus the verdict counts accept/reject/uncertain/unavailable for them. Reported only, never a pass or fail. Keep the section heading text '6 held-item mention relations' (the verifier gate line and every other output stay byte-identical). "
    "Add tests for both, run the whole tests/test_shadow_report.py and tests/test_shadow_sample2_harness.py (all must pass), then ruff check and ruff format on the two files and report exact counts."
)
CHECK = (
    "cd /home/bcorfman/dev/freytag-forge && export PYTHONPATH=/home/bcorfman/dev/freytag-forge TMPDIR=/tmp && set -o pipefail && "
    "env -u CLOUDFLARE_WORKER_URL -u CLOUDFLARE_WORKER_TOKEN .venv/bin/python -m pytest -q -p no:cacheprovider --no-cov tests/test_shadow_report.py tests/test_shadow_sample2_harness.py tests/test_observation_shadow.py 2>&1 | tee /tmp/shadow2-fix.out | tail -6 && "
    "! grep -Eq '[0-9]+ (failed|error)' /tmp/shadow2-fix.out && grep -Eq '[0-9]+ passed' /tmp/shadow2-fix.out && "
    f'! grep -n "observation_request" {ENV}/shadow_report.py | grep -q "places_before" && '
    f"! git status --porcelain | cut -c4- | grep -vE '^({ENV}/shadow_report.py|tests/test_shadow_report.py|{ENV}/[^ ]*shadow2[^ ]*)$' | grep -q . && "
    f".venv/bin/python -m ruff check {ENV}/shadow_report.py tests/test_shadow_report.py && .venv/bin/python -m ruff format --check {ENV}/shadow_report.py tests/test_shadow_report.py"
)
manifest = {
    "run_name": "grounded-environment-narration",
    "workdir": "/home/bcorfman/dev/ringer-work/grounded-environment-narration-shadow2-report-fix",
    "max_parallel": 1,
    "worktrees": False,
    "repo": REPO,
    "tasks": [
        {
            "key": "shadow2-report-real-row-fixes",
            "task_type": "code-fix",
            "engine": "codex",
            "model": "gpt-5.6-luna",
            "engine_args": ["-c", "model_reasoning_effort=high"],
            "full_access": True,
            "max_attempts": 2,
            "timeout_s": 2400,
            "check_timeout_s": 900,
            "ownership": [f"{ENV}/shadow_report.py", "tests/test_shadow_report.py"],
            "expect_files": [f"{REPO}/tests/test_shadow_report.py"],
            "spec": SPEC,
            "check": CHECK,
            "verified": "clause 8 counts only seat turns with no required relation; clause 6 reports mention-only relations by thing",
        }
    ],
}
if __name__ == "__main__":
    OUT.write_text(json.dumps(manifest, indent=2) + "\n")
