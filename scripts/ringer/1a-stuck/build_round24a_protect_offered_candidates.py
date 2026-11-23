"""Round 24a: planner evidence keeps the candidates the failing turns offered or matched."""

import json
from pathlib import Path

import build_round21b_evidence_cap_and_spend_cap as b

b.WORK = "/home/bcorfman/dev/ringer-work/factory-24"

SPEC = b.COMMON + (
    "You may edit ONLY: factory/stations/fix_plan.py and tests/test_factory_fix_plan.py.\n\n"
    "TASK. In factory/stations/fix_plan.py, `build_evidence` passes `protected_candidates=_diagnosis_claim_ids("
    "ticket_payload)` to `_bound_evidence`. A ticket with no diagnosis rows therefore protects no candidates, and "
    "when the packet is over EVIDENCE_LIMIT_CHARS the cut removes candidates in reverse-sorted order, which can "
    "drop the very claim the failing turns offered. Real failure: tests/test_factory_claim_edit.py::"
    "test_evidence_menu_and_candidate_matcher_context_are_bounded raises KeyError for the offered claim "
    "'k_sl_1a_k_r1' because it sorts last and is cut first.\n"
    "Change: protect, in addition to the diagnosis claim ids, every claim id that appears in a failing turn's "
    "`candidates_offered` or equals its `matched_candidate` (string values only; use the turns you already built "
    "for the evidence, so the set matches what the planner sees). Protected candidates are never cut; if the "
    "packet is still over the limit after the other cuts, the existing loops already stop, so do not add new "
    "cuts. Add one test in tests/test_factory_fix_plan.py: a ticket with no diagnosis whose failing turn offers "
    "the claim that sorts LAST among the scene candidates, and a limit small enough to force candidate cuts "
    "(call build_evidence after monkeypatching fix_plan.EVIDENCE_LIMIT_CHARS, or call _bound_evidence directly "
    "with the same protected set); assert that claim is still in evidence['candidates'] and that "
    "evidence['truncated']['candidates'] shows some other candidates were cut. Do NOT edit "
    "tests/test_factory_claim_edit.py; it must pass unchanged. Change nothing else."
)

manifest = {
    "run_name": "factory-24a-protect-offered-candidates",
    "workdir": b.WORK,
    "max_parallel": 1,
    "worktrees": True,
    "repo": b.REPO,
    "tasks": [
        {
            "key": "protect-offered-candidates",
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
                "tests/test_factory_fix_plan.py tests/test_factory_claim_edit.py tests/test_factory_planner.py "
                "tests/test_factory_qualification_run_case.py",
                300,
                "grep -q 'candidates_offered' factory/stations/fix_plan.py && grep -Eq 'protected_candidates *=' factory/stations/fix_plan.py || { echo 'protected_candidates not widened'; exit 1; }",
                "protect-offered-candidates",
            ),
            "expect_files": [],
            "verified": "Candidates offered or matched by failing turns survive the evidence cut; claim_edit test passes unchanged.",
        }
    ],
}
Path(__file__).with_name("round24a-protect-offered-candidates-manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")
