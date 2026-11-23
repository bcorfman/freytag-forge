"""Round 21d: set the planner evidence limit to the measured value."""

import json
from pathlib import Path

import build_round21b_evidence_cap_and_spend_cap as b

SPEC = b.COMMON + (
    "You may edit ONLY: factory/stations/fix_plan.py and tests/test_factory_fix_plan.py.\n\n"
    "TASK (one constant). `EVIDENCE_LIMIT_CHARS` in factory/stations/fix_plan.py is 20_000. Measured on two real "
    "saved 1A cases (23 and 21 failing turns), 20_000 still cuts every beat and exit because diagnosis (5.8k), "
    "protected candidates (3.3k) and fix_menu (0.7k) are fixed overhead; 24_000 keeps every failing turn (text "
    "shortened to 150 characters), every beat and exit, and cuts only fact_readers and unprotected candidates. "
    "Change the constant to 24_000. Then check every test in tests/test_factory_fix_plan.py still describes real "
    "behaviour at that limit: a test that builds a packet to be 'over the default limit' must still be over 24_000 "
    "(grow its fixture, do not weaken its assertion), and the packet shaped like the measured case (added in the "
    "previous round) must still keep all beats and exits and at least 10 failing turns. Say in NOTES.txt which "
    "fixtures you grew. Change nothing else."
)

manifest = {
    "run_name": "factory-21d-evidence-limit-24k",
    "workdir": b.WORK,
    "max_parallel": 1,
    "worktrees": True,
    "repo": b.REPO,
    "tasks": [
        {
            "key": "evidence-limit-24k",
            "task_type": "code-fix",
            "engine": "codex",
            "engine_args": ["-c", "model_reasoning_effort=medium"],
            "max_attempts": 2,
            "timeout_s": 1800,
            "check_timeout_s": 900,
            "ownership": ["factory/stations/fix_plan.py", "tests/test_factory_fix_plan.py"],
            "spec": SPEC,
            "check": b.check(
                r"factory/stations/fix_plan\.py|tests/test_factory_fix_plan\.py",
                "tests/test_factory_fix_plan.py tests/test_factory_planner.py tests/test_factory_qualification_run_case.py",
                300,
                "grep -Eq 'EVIDENCE_LIMIT_CHARS *(: *int)? *= *24_?000' factory/stations/fix_plan.py || { echo 'EVIDENCE_LIMIT_CHARS is not 24000'; exit 1; }",
                "evidence-limit-24k",
            ),
            "expect_files": [],
            "verified": "The evidence limit is 24,000 and tests still exercise real truncation.",
        }
    ],
}
Path(__file__).with_name("round21d-evidence-limit-24k-manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")
