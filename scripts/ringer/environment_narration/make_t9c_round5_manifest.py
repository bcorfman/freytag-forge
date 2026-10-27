# ruff: noqa: E501
"""Generate the Ringer build manifest for T9c round 5: a repeatable entry yields to any other full match."""

from __future__ import annotations

import json
from pathlib import Path

REPO = "/home/bcorfman/dev/freytag-forge"
E = "scripts/ringer/environment_narration"
OUT = Path(REPO) / E / "build-t9c-round5.json"
PREREG = ".plans/grounded-llm-environment-narration/t9c-engine-open-prereg.md"

SPEC = (
    "You are working in freytag-forge (Python 3.12). Working directory: /home/bcorfman/dev/freytag-forge. "
    "export PYTHONPATH=/home/bcorfman/dev/freytag-forge TMPDIR=/tmp; run `.venv/bin/python` (never uv). "
    "Run tests with `env -u CLOUDFLARE_WORKER_URL -u CLOUDFLARE_WORKER_TOKEN .venv/bin/python -m pytest -q -p no:cacheprovider --no-cov <files>`. "
    "No network, no live model call, no billed call. Do not git commit. NEVER print or write any credential. NO regular expressions in new code. Story-agnostic: no story names or vocabulary in non-test code under storygame/. "
    "Write the test changes FIRST, confirm they fail for the right reason, then implement until they pass. Run ruff check and ruff format on your files at the end. "
    f"BACKGROUND. Read item 3 of {PREREG} ('A repeatable entry yields to any other full match'). Rounds 1 and 4 made `uniquely_matched_authored_handoff` and `uniquely_matched_candidate` (storygame/runtime/candidate_matcher.py) pick the full match with the most evidence groups. That breaks the existing, deliberate test tests/test_1a_research_files_eligibility.py::test_word_match_alone_cannot_break_b_r1_d_r1_tie (two NON-repeatable entries that both match in full must stay an unresolved tie). "
    "YOUR TASK: replace the group-count rule with the narrower yielding rule in BOTH functions. Among the entries that match in full: if at least one is non-repeatable, drop the repeatable ones first; then a single remaining match wins and two or more remaining matches return None (as before round 1); if all matches are repeatable, a unique match wins, otherwise None. Partial matches never count. For this, candidates must carry the flag: add `repeatable: bool = False` to `ActionEvidenceCandidate` (candidate_matcher.py) and to `RevealCandidate` (storygame/runtime/knowledge.py, `Field(default=False, exclude=True)` like `delivery_text`, populated in `KnowledgeProjector._candidate` from the definition), and pass it where `ActionEvidenceCandidate` objects are built from candidates (storygame/runtime/cloudflare.py around `_shadow`/matched candidate code near line 540; search for every `ActionEvidenceCandidate(` in storygame/ and scripts/ringer and update only storygame/ callers you own). "
    "YOU MAY EDIT ONLY: storygame/runtime/candidate_matcher.py, storygame/runtime/knowledge.py (only `RevealCandidate` and `_candidate`), storygame/runtime/cloudflare.py (only the `ActionEvidenceCandidate(` construction), tests/test_candidate_matcher.py (replace only the group-count tests added in round 1 and round 4 with yielding-rule tests; keep every other assertion), tests/test_repeatable_knowledge.py (same: replace only the group-count tests). "
    "TESTS: (a) a repeatable and a non-repeatable candidate both matching in full: the non-repeatable wins, in both functions; (b) two non-repeatable full matches: None (this is the existing b_r1/d_r1 behaviour, assert it directly with synthetic candidates of different group counts to prove group count no longer matters); (c) two repeatable full matches: None; one repeatable full match alone: it wins; (d) a repeatable full match plus a non-repeatable PARTIAL match: the repeatable one wins; (e) `RevealCandidate` carries `repeatable` from the definition and does not serialise it (the dump of an existing candidate is unchanged). Commands in tests are imperative with a direct object (docs/player-input-guide.md). "
    "Then run tests/test_candidate_matcher.py tests/test_repeatable_knowledge.py tests/test_1a_research_files_eligibility.py tests/test_1a_gap_pointer.py tests/test_1a_back_door_gap.py tests/test_1a_drawer_words.py tests/test_drawer_gap_nudge.py tests/test_invitation_report.py tests/test_knowledge_projection.py tests/test_semantic_reveal_match.py tests/test_reveal_universe.py and report each file's result; do NOT edit any file not listed above: if a test in another file fails, report the test and why."
)

CHECK = (
    "cd /home/bcorfman/dev/freytag-forge && export PYTHONPATH=/home/bcorfman/dev/freytag-forge TMPDIR=/tmp && set -o pipefail && "
    "env -u CLOUDFLARE_WORKER_URL -u CLOUDFLARE_WORKER_TOKEN .venv/bin/python -m pytest -q -p no:cacheprovider --no-cov tests/test_candidate_matcher.py tests/test_repeatable_knowledge.py tests/test_1a_research_files_eligibility.py tests/test_1a_gap_pointer.py tests/test_1a_back_door_gap.py tests/test_1a_drawer_words.py tests/test_drawer_gap_nudge.py tests/test_invitation_report.py tests/test_knowledge_projection.py tests/test_semantic_reveal_match.py tests/test_reveal_universe.py 2>&1 | tee /tmp/t9c-r5.out | tail -6 && "
    "! grep -Eq '[0-9]+ (failed|error)' /tmp/t9c-r5.out && "
    "grep -q repeatable storygame/runtime/candidate_matcher.py && "
    ".venv/bin/python -m ruff check storygame/runtime/candidate_matcher.py storygame/runtime/knowledge.py storygame/runtime/cloudflare.py tests/test_candidate_matcher.py tests/test_repeatable_knowledge.py && "
    ".venv/bin/python -m ruff format --check storygame/runtime/candidate_matcher.py storygame/runtime/knowledge.py storygame/runtime/cloudflare.py tests/test_candidate_matcher.py tests/test_repeatable_knowledge.py"
)

manifest = {
    "run_name": "grounded-environment-narration",
    "workdir": "/home/bcorfman/dev/ringer-work/grounded-environment-narration-t9c-round5",
    "max_parallel": 1,
    "worktrees": False,
    "repo": REPO,
    "tasks": [
        {
            "key": "t9c-yielding-rule",
            "task_type": "code-fix",
            "engine": "codex",
            "model": "gpt-5.6-luna",
            "engine_args": ["-c", "model_reasoning_effort=high"],
            "full_access": True,
            "max_attempts": 2,
            "timeout_s": 3600,
            "check_timeout_s": 1800,
            "ownership": [
                "storygame/runtime/candidate_matcher.py",
                "storygame/runtime/knowledge.py",
                "storygame/runtime/cloudflare.py",
                "tests/test_candidate_matcher.py",
                "tests/test_repeatable_knowledge.py",
            ],
            "expect_files": [f"{REPO}/storygame/runtime/candidate_matcher.py"],
            "spec": SPEC,
            "check": CHECK,
            "verified": "a repeatable entry yields to a non-repeatable full match and two non-repeatable matches stay a tie",
        }
    ],
}

if __name__ == "__main__":
    OUT.write_text(json.dumps(manifest, indent=2) + "\n")
