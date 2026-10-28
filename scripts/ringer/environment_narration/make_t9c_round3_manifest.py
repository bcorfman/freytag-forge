# ruff: noqa: E501
"""Generate the Ringer build manifest for T9c round 3: a repeatable entry keeps normal activation until it is first earned."""

from __future__ import annotations

import json
from pathlib import Path

REPO = "/home/bcorfman/dev/freytag-forge"
E = "scripts/ringer/environment_narration"
OUT = Path(REPO) / E / "build-t9c-round3.json"
PREREG = ".plans/grounded-llm-environment-narration/t9c-engine-open-prereg.md"

SPEC = (
    "You are working in freytag-forge (Python 3.12). Working directory: /home/bcorfman/dev/freytag-forge. "
    "export PYTHONPATH=/home/bcorfman/dev/freytag-forge TMPDIR=/tmp; run `.venv/bin/python` (never uv). "
    "Run tests with `env -u CLOUDFLARE_WORKER_URL -u CLOUDFLARE_WORKER_TOKEN .venv/bin/python -m pytest -q -p no:cacheprovider --no-cov <files>`. "
    "No network, no live model call, no billed call. Do not git commit. NEVER print or write any credential. NO regular expressions in new code. Story-agnostic: no story names or vocabulary in non-test code. "
    "Write the test changes FIRST, confirm they fail for the right reason, then implement until they pass. Run ruff check and ruff format on your files at the end. "
    f"BACKGROUND. {PREREG} item 2 defines `KnowledgeDefinition.repeatable`. Round 1 made `explain_reveal` (storygame/runtime/reveal_eligibility.py) skip the ALREADY_ESTABLISHED, STORYLET_SPENT and SOURCE_INACTIVE checks for every repeatable entry. That is too wide: the real continuity entry `k_sl_1a_f_r2` is now repeatable, so it became an eligible candidate at scene entry before its storylet was ever active, which changes the candidate lists and prompts of about twenty existing tests and ignores the story's pacing. "
    "YOUR TASK: narrow the rule. YOU MAY EDIT ONLY storygame/runtime/reveal_eligibility.py and tests/test_repeatable_knowledge.py (modify only the tests that pinned the wide rule; keep every other assertion). New rule in `explain_reveal`: a repeatable entry skips ALREADY_ESTABLISHED always; it skips STORYLET_SPENT and SOURCE_INACTIVE ONLY when its own `establishes` effects already hold in the state (it has been earned once, by this entry or by another route that asserts the same fact). Before it has been earned, a repeatable entry follows the normal rules exactly like any other entry, so it is NOT eligible at scene entry when its storylet is not active, and NOT eligible when its storylet is spent without the effects holding. Every other rule (audience, requires, reach) applies as before. Do not touch cloudflare.py or any other file; if `_eligible_reveal_candidates` or another place needs a matching change to keep the same meaning, say so in your final message instead of editing. "
    "TESTS in tests/test_repeatable_knowledge.py: (a) repeatable, effects hold, storylet spent and inactive: eligible; (b) repeatable, effects do not hold, storylet inactive: SOURCE_INACTIVE, same as a non-repeatable entry; (c) repeatable, effects do not hold, storylet in fired events: STORYLET_SPENT; (d) repeatable, effects hold because ANOTHER entry asserted the same fact, own storylet inactive: eligible; (e) non-repeatable behaviour unchanged; (f) requires, reach and audience still block a repeatable entry whose effects hold. "
    "Then run tests/test_reveal_eligibility.py tests/test_reveal_universe.py tests/test_drawer_gap_nudge.py tests/test_candidate_matcher.py and report the result of each file in your final message (tests/test_drawer_gap_nudge.py may need its fired-event setup to match the new rule: do NOT edit it, report what fails)."
)

CHECK = (
    "cd /home/bcorfman/dev/freytag-forge && export PYTHONPATH=/home/bcorfman/dev/freytag-forge TMPDIR=/tmp && set -o pipefail && "
    "env -u CLOUDFLARE_WORKER_URL -u CLOUDFLARE_WORKER_TOKEN .venv/bin/python -m pytest -q -p no:cacheprovider --no-cov tests/test_repeatable_knowledge.py tests/test_reveal_eligibility.py tests/test_reveal_universe.py 2>&1 | tee /tmp/t9c-r3.out | tail -6 && "
    "! grep -Eq '[0-9]+ (failed|error)' /tmp/t9c-r3.out && "
    ".venv/bin/python -m ruff check storygame/runtime/reveal_eligibility.py tests/test_repeatable_knowledge.py && "
    ".venv/bin/python -m ruff format --check storygame/runtime/reveal_eligibility.py tests/test_repeatable_knowledge.py"
)

manifest = {
    "run_name": "grounded-environment-narration",
    "workdir": "/home/bcorfman/dev/ringer-work/grounded-environment-narration-t9c-round3",
    "max_parallel": 1,
    "worktrees": False,
    "repo": REPO,
    "tasks": [
        {
            "key": "t9c-narrow-repeatable",
            "task_type": "code-fix",
            "engine": "codex",
            "model": "gpt-5.6-luna",
            "engine_args": ["-c", "model_reasoning_effort=high"],
            "full_access": True,
            "max_attempts": 2,
            "timeout_s": 3600,
            "check_timeout_s": 1800,
            "ownership": ["storygame/runtime/reveal_eligibility.py", "tests/test_repeatable_knowledge.py"],
            "expect_files": [f"{REPO}/storygame/runtime/reveal_eligibility.py"],
            "spec": SPEC,
            "check": CHECK,
            "verified": "a repeatable entry follows normal activation until it is first earned",
        }
    ],
}

if __name__ == "__main__":
    OUT.write_text(json.dumps(manifest, indent=2) + "\n")
