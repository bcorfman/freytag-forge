"""Build the round 21c manifest: planner evidence limit and cut order (follow-up to 21b measurement)."""

import json
from pathlib import Path

import build_round21b_evidence_cap_and_spend_cap as b

SPEC = b.COMMON + (
    "You may edit ONLY: factory/stations/fix_plan.py and tests/test_factory_fix_plan.py.\n\n"
    "PROBLEM (measured on two real saved cases, 1A with 21 to 23 failing turns). The planner evidence packet is "
    "about 38.7k and 42.4k characters before bounding: failing_turns 18.3k to 22.2k, diagnosis 5.8k, candidates "
    "10k, fact_readers 2.3k, beats 1.1k to 1.3k, exits 0.2k, fix_menu 0.7k. `_bound_evidence` (just repaired in the "
    "previous round) keeps the limit at 12,000, but the diagnosis and fix_menu alone take about 6.5k, so the cut "
    "removes ALL beats, exits and fact_readers, shortens turn text to 80 characters and keeps only 4 of 23 turns. "
    "The planner cannot choose a pacing beat or judge an exit without beats and exits, which are small structured "
    "facts.\n\n"
    "CHANGE.\n"
    "1. Raise the default `limit` of `_bound_evidence` to 20_000 characters (a module constant "
    "`EVIDENCE_LIMIT_CHARS`, used as the default).\n"
    "2. Change the cut order to: (a) unprotected candidates; (b) fact_readers; (c) shorten failing-turn text fields "
    "to 300, then 150 characters; (d) beats, then exits, from the end; (e) shorten turn text to 80; (f) drop "
    "failing turns from the end, protected turn keys last, never to zero when the input had at least one. "
    "Beats and exits are therefore cut only after turn text is already at 150 characters.\n"
    "3. Keep the `truncated` marker behaviour exactly as is (counts kept and original, `text_shortened_to` the "
    "last length applied).\n\n"
    "TESTS. Update the tests added in the previous round only where this order change requires it (say which in "
    "NOTES.txt), and add: (a) a packet shaped like the measured one (25 turns with 600-character narrations and "
    "previous narrations, 10 candidates of 500 characters, a 6,000-character `diagnosis` value, 2,300 characters of "
    "fact_readers, 8 small beats, 1 exit) bounded at the default limit keeps ALL beats and exits, keeps at least "
    "10 failing turns, is within the limit, and reports `truncated`; (b) beats and exits are still cut when the "
    "limit is so small that shortening text to 150 is not enough, and only then. Assert survival and counts, not "
    "exact strings."
)

manifest = {
    "run_name": "factory-21c-evidence-limit",
    "workdir": b.WORK,
    "max_parallel": 1,
    "worktrees": True,
    "repo": b.REPO,
    "tasks": [
        {
            "key": "evidence-limit",
            "task_type": "code-fix",
            "engine": "codex",
            "engine_args": ["-c", "model_reasoning_effort=high"],
            "max_attempts": 2,
            "timeout_s": 2400,
            "check_timeout_s": 900,
            "ownership": ["factory/stations/fix_plan.py", "tests/test_factory_fix_plan.py"],
            "spec": SPEC,
            "check": b.check(
                r"factory/stations/fix_plan\.py|tests/test_factory_fix_plan\.py",
                "tests/test_factory_fix_plan.py tests/test_factory_planner.py tests/test_factory_qualification_run_case.py",
                300,
                "grep -q 'EVIDENCE_LIMIT_CHARS' factory/stations/fix_plan.py || { echo 'no EVIDENCE_LIMIT_CHARS constant'; exit 1; }",
                "evidence-limit",
            ),
            "expect_files": [],
            "verified": "Planner evidence keeps beats, exits and at least 10 failing turns on a packet shaped like the measured 1A case.",
        }
    ],
}
Path(__file__).with_name("round21c-evidence-limit-manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")
