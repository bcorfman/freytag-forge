# ruff: noqa: E501
"""Generate the Ringer manifest for: 20 s request timeout, and a timeout fails the call with no retry."""

from __future__ import annotations

import json
from pathlib import Path

REPO = "/home/bcorfman/dev/freytag-forge"
ENV = "scripts/ringer/environment_narration"
OUT = Path(REPO) / ENV / "build-timeout-no-retry.json"
FILES = [
    "storygame/runtime/cloudflare.py",
    "tests/test_request_timeout.py",
    "tests/test_cloudflare_transport.py",
    "tests/test_recovery_budget.py",
    "docs/cloudflare-narration-worker.md",
]

SPEC = (
    "You are working in freytag-forge (Python 3.12). Working directory: /home/bcorfman/dev/freytag-forge. "
    "export PYTHONPATH=/home/bcorfman/dev/freytag-forge TMPDIR=/tmp; run `.venv/bin/python` (never uv). "
    "Run tests with `env -u CLOUDFLARE_WORKER_URL -u CLOUDFLARE_WORKER_TOKEN .venv/bin/python -m pytest -q -p no:cacheprovider --no-cov <files>`. "
    f"YOU MAY EDIT ONLY: {', '.join(FILES)} (tests/test_request_timeout.py is NEW). No network, no model call, never read .env, do not git commit, NO regular expressions in new code. Engine code must stay story-agnostic. "
    "METHOD: write the new tests FIRST, run them, confirm they fail for the right reason, then implement. READ FIRST: docs/contributor-guide.md, storygame/runtime/cloudflare.py (`_request`, `_request_allowing_one_transient_retry`, the `urlopen(... timeout=float(getenv('CLOUDFLARE_TIMEOUT', '15')))` line, TURN_REQUEST_BUDGET), tests/test_recovery_budget.py, tests/test_cloudflare_transport.py. "
    "DECISION (Brandon, 2026-10-26). In a live run a narration call took the Worker 16.9 s, the client (15 s timeout) abandoned it, `_request_allowing_one_transient_retry` sent the same prompt again, and that retry used one of the two allowed per-turn requests (TURN_REQUEST_BUDGET = 2, counted in `_request` before each send), so the guard retry the reply then needed was refused with NARRATION_REQUEST_BUDGET_EXHAUSTED and the turn was lost. Brandon's rule: raise the default request timeout to 20 seconds, and if a request times out at that limit, just FAIL: never retry a timeout, because waiting another 20 s is too long. A fast connection failure (for example a connection reset or refused connection, which returns immediately) keeps its single retry exactly as today. "
    "BUILD. (1) The default of CLOUDFLARE_TIMEOUT becomes 20 (name the default as one module constant, for example REQUEST_TIMEOUT_SECONDS = 20.0, used by the urlopen call; the environment variable still overrides it). (2) In `_request_allowing_one_transient_retry`, a timeout is raised at once without a second send. A timeout is either a TimeoutError (socket.timeout is TimeoutError) or a URLError whose `reason` is a TimeoutError; write one small private helper `_is_timeout(error)` for this. Other URLError and OSError failures still retry exactly once, an HTTPError is still never retried, and when the retry also fails the existing `raise error from first_failure` behavior stays. The error a caller sees for a timeout must be the same exception type the second failure produced before, so the existing handling that turns it into the typed 'narration service is unavailable' failure and the exact snapshot rollback is unchanged; check that path by test. (3) Update docs/cloudflare-narration-worker.md: the CLOUDFLARE_TIMEOUT row states the default is 20 seconds, that a timeout fails the call and is not retried, and that other connection failures are retried once. "
    "TESTS in the new file tests/test_request_timeout.py (hermetic; patch `storygame.runtime.cloudflare.urlopen`; follow the helpers in tests/test_recovery_budget.py): (a) the default timeout passed to urlopen is 20.0 when CLOUDFLARE_TIMEOUT is unset and the env var still overrides it; (b) a TimeoutError on the first send raises with exactly ONE urlopen call and request_count 1; (c) a URLError(TimeoutError()) is treated the same; (d) a URLError('offline') on the first send still retries once and succeeds (two sends); (e) a connection failure on both sends raises after exactly two sends; (f) an HTTPError is never retried; (g) engine level: a timeout during a narration turn fails the turn with the existing typed unsuccessful result and restores the pre-turn snapshot (turn index and facts unchanged, no half-applied item facts), and the next turn then works; (h) after a timeout the per-turn counter is not left permanently exhausted for the next turn (begin_turn resets). Existing tests that pinned retry-on-timeout (search for TimeoutError in tests/test_cloudflare_transport.py, tests/test_jev_use.py, tests/test_semantic_reveal_match.py) must be reviewed: change only the ones in the files you own and only where the assertion was exactly 'a timeout retries'; if a test in a file you do NOT own breaks, do not edit it, report its name and message. "
    "FINALLY run `.venv/bin/python scripts/quick_suite.py` with CLOUDFLARE_WORKER_URL and CLOUDFLARE_WORKER_TOKEN unset and report exact counts, then ruff check and ruff format on every file you changed."
)
CHECK = (
    "cd /home/bcorfman/dev/freytag-forge && export PYTHONPATH=/home/bcorfman/dev/freytag-forge TMPDIR=/tmp && set -o pipefail && "
    "env -u CLOUDFLARE_WORKER_URL -u CLOUDFLARE_WORKER_TOKEN .venv/bin/python -m pytest -q -p no:cacheprovider --no-cov tests/test_request_timeout.py tests/test_recovery_budget.py tests/test_cloudflare_transport.py 2>&1 | tee /tmp/timeout-focus.out | tail -6 && "
    "! grep -Eq '[0-9]+ (failed|error)' /tmp/timeout-focus.out && grep -Eq '[0-9]+ passed' /tmp/timeout-focus.out && "
    "env -u CLOUDFLARE_WORKER_URL -u CLOUDFLARE_WORKER_TOKEN .venv/bin/python scripts/quick_suite.py 2>&1 | tee /tmp/timeout-quick.out | grep -E 'passed|failed|FAILED' | tail -4 && "
    "! grep -Eq '[0-9]+ failed|FAILED' /tmp/timeout-quick.out && grep -Eq '[0-9]+ passed' /tmp/timeout-quick.out && "
    "grep -q '20' storygame/runtime/cloudflare.py && grep -qi 'not retried\\|no retry\\|is not retried' docs/cloudflare-narration-worker.md && "
    f"! git status --porcelain | cut -c4- | grep -vE '^({'|'.join(FILES)}|{ENV}/[^ ]*timeout[^ ]*)$' | grep -q . && "
    f".venv/bin/python -m ruff check {' '.join(FILES[:3] + FILES[3:4])} && .venv/bin/python -m ruff format --check {' '.join(FILES[:4])}"
)
manifest = {
    "run_name": "grounded-environment-narration",
    "workdir": "/home/bcorfman/dev/ringer-work/grounded-environment-narration-timeout-no-retry",
    "max_parallel": 1,
    "worktrees": False,
    "repo": REPO,
    "tasks": [
        {
            "key": "timeout-20s-no-retry",
            "task_type": "code-fix",
            "engine": "codex",
            "model": "gpt-5.6-luna",
            "engine_args": ["-c", "model_reasoning_effort=high"],
            "full_access": True,
            "max_attempts": 2,
            "timeout_s": 3000,
            "check_timeout_s": 1500,
            "ownership": FILES,
            "expect_files": [f"{REPO}/tests/test_request_timeout.py"],
            "spec": SPEC,
            "check": CHECK,
            "verified": "default timeout 20 s; a timeout fails at once without a second send; a fast connection failure keeps its one retry; the failed turn rolls back; the quick suite is green",
        }
    ],
}
if __name__ == "__main__":
    OUT.write_text(json.dumps(manifest, indent=2) + "\n")
