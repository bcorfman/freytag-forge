# ruff: noqa: E501
"""One small Ringer task: update the five remaining old tests that pin pre-change counts, sets or the early gap hint."""

import json
from pathlib import Path

R = "/home/bcorfman/dev/freytag-forge"
PY = f"{R}/.venv/bin/python"
ENV = f"export TMPDIR=/tmp PYTHONPATH={R}:{R}/packages/worldkeeper/src"
TESTS = [
    "test_drawer_avoidance_repro.py",
    "test_design_review_fixtures.py",
    "test_live_baseline_evidence.py",
    "test_richer_1c.py",
    "test_search_opens_drawer.py",
]
FAILING = " ".join(f"tests/{t}" for t in TESTS)
RELATED = "tests/test_1a_witnessed_recovery.py tests/test_1a_drawer_close_gap.py tests/test_1a_phone_thread.py tests/test_markdown_story_package.py tests/test_voiceable_knowledge.py tests/test_audit_budget.py tests/test_1a_officer_press.py tests/test_place_scoped_feed.py"

spec = f"""You are a test-update worker for the freytag-forge repository at {R}. Boundary: NO model call, NO network call, never git commit. Edit ONLY these tests under {R}/tests: {", ".join(TESTS)}. Edit no data, source, fixture or other test. These tests pin the pre-change behaviour of scene 1A; the story data changed deliberately (a phone-thread storylet, a drawer open-then-close rule, a Reyes drawer event). Update each narrowly; never weaken an assertion that still holds.

CAUSES (diagnosed; run only these five files first):
1. test_drawer_avoidance_repro.py::test_static_drawer_dependencies_have_no_later_scene_dependents: the expected set of drawer-only facts lacks two new facts, drawer_opened and drawer_gap_rechecked. Add them.
2. test_design_review_fixtures.py::test_more_than_four_eligible: scene 1A now has 10 eligible knowledge definitions instead of 9 because of the new records (k_sl_1a_j_r1..r3 and k_sl_1a_f_r3 have different eligibility). Confirm which record accounts for the extra one from the printed ids and update the expected count (the test's point is more than four eligible, which still holds).
3. test_richer_1c.py::test_michelle_glimpse_contract_is_uncertain_and_preserves_its_metadata: the package now has 121 knowledge definitions instead of 117 (four new: k_sl_1a_j_r1, k_sl_1a_j_r2, k_sl_1a_j_r3, k_sl_1a_f_r3). Update 117 to 121.
4. test_search_opens_drawer.py::test_search_drawer_opens_it_and_keeps_gap_nudge: after 'Search the drawer.' opens the drawer, the gap nudge (k_sl_1a_f_r2) is deliberately no longer offered until the gap has been found (open then close finds it). Change the final assertion to the new behaviour (no authored handoff yet) and rename the test accordingly (for example ..._and_waits_for_the_close), keeping every other assertion.
5. test_live_baseline_evidence.py::test_real_call_cap_inside_preview_records_logical_request_without_http_call fails with 'assert 0 == 1' on verifier_requests. Diagnose first: the harness runs the first turn of the 'observe' route; find which command that is and why the turn now reaches the 4-call stop before the observation preview (likely a call-count change because the drawer examine no longer has an authored reveal handoff). Change the test minimally so it still proves its intent (a call cap hit inside the preview records one logical verifier request and no HTTP call), for example by raising the stop threshold. If the cause is not call counts, write the finding to {R}/bench/results/1a-passcode-round2/final-pins-failures.txt and stop.
After the edits run `{PY} -m ruff format {FAILING}` and `{PY} -m ruff check {FAILING}`.
HOW TO RUN (from {R}; never bare python, never uv): `{ENV} {PY} -m pytest {FAILING} -q -p no:cacheprovider 2>&1 | tail -20`, then once at the end `{ENV} {PY} -m pytest {FAILING} {RELATED} -q -p no:cacheprovider 2>&1 | tail -12`."""

check = f"""set -o pipefail
cd {R}
{ENV}
{PY} -m ruff format --check {FAILING}
{PY} -m ruff check {FAILING}
{PY} -m pytest {FAILING} {RELATED} -q -p no:cacheprovider 2>&1 | tail -12
"""
task = {
    "key": "update-final-pins",
    "task_type": "code-fix",
    "engine": "codex",
    "model": "gpt-5.6-luna",
    "engine_args": ["-c", "model_reasoning_effort=medium"],
    "max_attempts": 2,
    "timeout_s": 1200,
    "check_timeout_s": 900,
    "ownership": [f"{R}/tests/{t}" for t in TESTS],
    "expect_files": [f"{R}/tests/{TESTS[0]}"],
    "spec": spec,
    "check": check,
    "verified": "the five old tests match the new 1A data and the related suites pass",
}
m = {
    "run_name": "1a-final-pins",
    "workdir": "/home/bcorfman/dev/ringer-work/1a-final-pins",
    "max_parallel": 1,
    "worktrees": False,
    "repo": R,
    "tasks": [task],
}
p = Path(f"{R}/scripts/ringer/1a-password-officer/final-pins-manifest.json")
p.write_text(json.dumps(m, indent=2) + "\n")
print(p)
