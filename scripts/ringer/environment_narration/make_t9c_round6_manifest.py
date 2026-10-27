# ruff: noqa: E501
"""Generate the Ringer build manifest for T9c round 6: two test helpers pass the repeatable flag like the product does."""

from __future__ import annotations

import json
from pathlib import Path

REPO = "/home/bcorfman/dev/freytag-forge"
E = "scripts/ringer/environment_narration"
OUT = Path(REPO) / E / "build-t9c-round6.json"

SPEC = (
    "You are working in freytag-forge (Python 3.12). Working directory: /home/bcorfman/dev/freytag-forge. "
    "export PYTHONPATH=/home/bcorfman/dev/freytag-forge TMPDIR=/tmp; run `.venv/bin/python` (never uv). "
    "Run tests with `env -u CLOUDFLARE_WORKER_URL -u CLOUDFLARE_WORKER_TOKEN .venv/bin/python -m pytest -q -p no:cacheprovider --no-cov <files>`. "
    "No network, no model call, no billed call. Do not git commit. NEVER print or write any credential. Run ruff check and ruff format on your files at the end. "
    "BACKGROUND. `ActionEvidenceCandidate` (storygame/runtime/candidate_matcher.py) now has `repeatable: bool = False`, and `uniquely_matched_candidate` and `uniquely_matched_authored_handoff` let a repeatable candidate yield to any non-repeatable full match. The product builds its evidence candidates in storygame/runtime/cloudflare.py with `ActionEvidenceCandidate(id=candidate.id, required_groups=candidate.action_evidence, repeatable=candidate.repeatable)` (read it). Two test helpers named `_plain_match` build the same objects WITHOUT the flag, so under-form commands such as `Feel beneath the drawer.` see the repeatable drawer nudge as an equal match and return None. "
    "YOUR TASK: YOU MAY EDIT ONLY tests/test_1a_gap_pointer.py and tests/test_1a_back_door_gap.py. In both `_plain_match` helpers pass `repeatable=candidate.repeatable`, exactly as cloudflare.py does, and change nothing else. Then run tests/test_1a_gap_pointer.py tests/test_1a_back_door_gap.py tests/test_1a_drawer_words.py tests/test_1a_research_files_eligibility.py tests/test_drawer_gap_nudge.py tests/test_candidate_matcher.py tests/test_repeatable_knowledge.py: all must pass. If any still fails, do not edit anything else; report the test and your diagnosis."
)

CHECK = (
    "cd /home/bcorfman/dev/freytag-forge && export PYTHONPATH=/home/bcorfman/dev/freytag-forge TMPDIR=/tmp && set -o pipefail && "
    "env -u CLOUDFLARE_WORKER_URL -u CLOUDFLARE_WORKER_TOKEN .venv/bin/python -m pytest -q -p no:cacheprovider --no-cov tests/test_1a_gap_pointer.py tests/test_1a_back_door_gap.py tests/test_1a_drawer_words.py tests/test_1a_research_files_eligibility.py tests/test_drawer_gap_nudge.py tests/test_candidate_matcher.py tests/test_repeatable_knowledge.py 2>&1 | tee /tmp/t9c-r6.out | tail -6 && "
    "! grep -Eq '[0-9]+ (failed|error)' /tmp/t9c-r6.out && grep -c 'repeatable=candidate.repeatable' tests/test_1a_gap_pointer.py tests/test_1a_back_door_gap.py && "
    ".venv/bin/python -m ruff check tests/test_1a_gap_pointer.py tests/test_1a_back_door_gap.py && .venv/bin/python -m ruff format --check tests/test_1a_gap_pointer.py tests/test_1a_back_door_gap.py"
)

manifest = {
    "run_name": "grounded-environment-narration",
    "workdir": "/home/bcorfman/dev/ringer-work/grounded-environment-narration-t9c-round6",
    "max_parallel": 1,
    "worktrees": False,
    "repo": REPO,
    "tasks": [
        {
            "key": "t9c-test-helpers",
            "task_type": "code-fix",
            "engine": "codex",
            "model": "gpt-5.6-luna",
            "engine_args": ["-c", "model_reasoning_effort=high"],
            "full_access": True,
            "max_attempts": 2,
            "timeout_s": 1800,
            "check_timeout_s": 900,
            "ownership": ["tests/test_1a_gap_pointer.py", "tests/test_1a_back_door_gap.py"],
            "expect_files": [f"{REPO}/tests/test_1a_gap_pointer.py"],
            "spec": SPEC,
            "check": CHECK,
            "verified": "the plain-match test helpers mirror the product's candidate construction",
        }
    ],
}

if __name__ == "__main__":
    OUT.write_text(json.dumps(manifest, indent=2) + "\n")
