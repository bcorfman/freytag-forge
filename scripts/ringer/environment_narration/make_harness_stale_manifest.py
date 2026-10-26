# ruff: noqa: E501
"""Generate the Ringer manifest that stops the shadow harness copying a previous turn's record."""

from __future__ import annotations

import json
from pathlib import Path

REPO = "/home/bcorfman/dev/freytag-forge"
OUT = Path(REPO) / "scripts/ringer/environment_narration/build-harness-stale-record.json"
HARNESS = "scripts/ringer/transcript_1a/live_baseline.py"
TESTS = "scripts/ringer/transcript_1a/test_live_baseline.py"

SPEC = (
    "You are working in freytag-forge (Python 3.12). Working directory: /home/bcorfman/dev/freytag-forge. "
    "export PYTHONPATH=/home/bcorfman/dev/freytag-forge TMPDIR=/tmp; run `.venv/bin/python` (never uv). "
    "Run tests with `env -u CLOUDFLARE_WORKER_URL -u CLOUDFLARE_WORKER_TOKEN .venv/bin/python -m pytest -q -p no:cacheprovider --no-cov <files>`. "
    "No network, no live model call (the harness has a --dry-run mode). Do not git commit. NEVER print or write any credential. NO regular expressions in new code. "
    f"YOU MAY EDIT ONLY: {HARNESS} and {TESTS}. Never touch storygame/, data/, docs/ or worker/. "
    "Write the test FIRST, run it, confirm it fails for the right reason, then fix the harness. Run ruff check and ruff format on both files at the end. "
    "PROBLEM. In `_replicate` of live_baseline.py, with `shadow=True`, each row copies `capture.last_after['observation_shadow']` and `_observation_request(capture, state)`. "
    "On an engine-authored move turn (for example the observe route's `go outside` and `go inside`) no narrator call is made, `WorldCapture.after_commit` does not run and `before_turn` does not rebuild the request, "
    "so `capture.last_after` and `provider.observation_request` still hold the PREVIOUS turn's objects and the row wrongly carries them. A live sample counted 5 such copies among its 31 reported verifier requests (true count 26). "
    "FIX. Before each `engine.turn(command)` remember the objects `capture.last_after` and `capture.provider.observation_request` (by identity, using `is`). After the turn, if `capture.last_after` is the same object as before, record `observation_shadow` as None; "
    "if `provider.observation_request` is the same object as before AND it is not None, record `observation_request` as None. A turn that rebuilt them keeps today's behavior. "
    "Do this only inside the `if shadow:` block; with shadow off the row schema must be byte-identical to today. Also make `_summary`'s `shadow_verifier_requests` count come out right (it sums over rows' `observation_shadow`, so None rows already contribute zero; confirm and do not change it unless needed). "
    "TEST (in the existing test file, same style as its neighbors, using the dry-run observe route with --shadow): after a dry run, every row whose `narrator_called` is false and whose input is an engine-authored move (`go outside`, `go inside`) has `observation_shadow` None and `observation_request` None, "
    "while rows that did call the narrator and set a request are unchanged; and a second test with a stub capture object proves the identity rule directly (same object -> None, new object -> kept) if the dry run cannot reach that case. "
    "Then run the whole existing file to prove no other test changed."
)

CHECK = (
    "cd /home/bcorfman/dev/freytag-forge && export PYTHONPATH=/home/bcorfman/dev/freytag-forge TMPDIR=/tmp && set -o pipefail && "
    f"env -u CLOUDFLARE_WORKER_URL -u CLOUDFLARE_WORKER_TOKEN .venv/bin/python -m pytest -q -p no:cacheprovider --no-cov {TESTS} tests/test_shadow_report.py 2>&1 | tee /tmp/harness-stale.out | tail -8 && "
    "! grep -Eq '[0-9]+ (failed|error)' /tmp/harness-stale.out && "
    f"grep -q 'last_after' {HARNESS} && "
    f".venv/bin/python -m ruff check {HARNESS} {TESTS} && .venv/bin/python -m ruff format --check {HARNESS} {TESTS}"
)

manifest = {
    "run_name": "grounded-environment-narration",
    "workdir": "/home/bcorfman/dev/ringer-work/grounded-environment-narration-harness-stale",
    "max_parallel": 1,
    "worktrees": False,
    "repo": REPO,
    "tasks": [
        {
            "key": "harness-stale-shadow-record",
            "task_type": "code-fix",
            "engine": "codex",
            "model": "gpt-5.6-luna",
            "engine_args": ["-c", "model_reasoning_effort=high"],
            "full_access": True,
            "max_attempts": 2,
            "timeout_s": 3000,
            "check_timeout_s": 900,
            "ownership": [HARNESS, TESTS],
            "expect_files": [f"{REPO}/{TESTS}"],
            "spec": SPEC,
            "check": CHECK,
            "verified": "engine-authored move rows no longer carry the previous turn's shadow record or observation request",
        }
    ],
}

if __name__ == "__main__":
    OUT.write_text(json.dumps(manifest, indent=2) + "\n")
