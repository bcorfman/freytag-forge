# ruff: noqa: E501
"""Two small Ringer tasks: the deep-turn audit's all-alternates figure counts only variants that can be earned together."""

import json
from pathlib import Path

R = "/home/bcorfman/dev/freytag-forge"
D = f"{R}/scripts/ringer/1a-password-officer"
PY = f"{R}/.venv/bin/python"
ENV = f"export TMPDIR=/tmp PYTHONPATH={R}:{R}/packages/worldkeeper/src"
TEST = f"{R}/tests/test_audit_budget_branches.py"
SRC = f"{R}/storygame/audit_budget.py"

RULE = """RULE (approved by Brandon, option 3). storygame/audit_budget.py measures a pessimistic 'deep turn' prompt. Its `narration_chars_all_alternates` figure (built by `_state_for(..., one_per_storylet=False)` via `_selected_entries`) currently establishes EVERY knowledge entry of every storylet. Some entries of one storylet are exclusive branches that are not realistically earned together: two entries of the SAME storylet (same source.storylet_id) whose `requires` contain a predicate on the same fact_id with different non-null `equals` values (for example patrol_in_house equals false versus equals true) are alternative branches of one situation. New behaviour: in the all-alternates state, keep the first such entry in package order and skip any later entry of that storylet that is exclusive with an already-kept entry of the same storylet. Everything else stays as is: entries without contradictory requires are all still counted; the one-per-storylet figure (narration_chars) is unchanged; the pins in tests/fixtures/deep_turn_budget.json are NOT regenerated or edited (the ratchet stays at its current values; the new measurement is simply <= the old). Story-agnostic: no scene, fact or storylet ids in the code. In the real package the only effect today should be that the scene 1A all-alternates prompt no longer contains the statement of knowledge record k_sl_1a_j_r2 (its requires patrol_in_house true contradicts k_sl_1a_j_r1 requires patrol_in_house false, same storylet SL-1A-J)."""

tests_spec = f"""You are a test-writing worker for the freytag-forge repository at {R}. Boundary: NO model call, NO network call, never git commit. You own ONLY {TEST} (create). Edit nothing else.

{RULE}

Read {R}/tests/test_audit_budget.py first (its `_package` helper builds a synthetic package from the lighthouse fixture; reuse or copy its approach) and {SRC}. WRITE THESE TESTS, exact names:
1. test_contradictory_requires_count_once_in_all_alternates: build a synthetic package where one storylet has two knowledge entries with requires on the same fact with equals true and equals false; build a second package identical except the second entry has no contradictory requires; assert the all-alternates figure of the first is smaller than the second's (by about the second entry's statement), and the one-per-storylet figure `narration_chars` is the same for both. Must FAIL today.
2. test_non_contradictory_alternates_still_count_control: two entries of one storylet with no requires conflict are both counted (the all-alternates figure exceeds the one-per-storylet figure, as in test_all_alternates_are_reported_and_make_the_prompt_larger). Must PASS today.
3. test_real_1a_all_alternates_prompt_omits_the_branch_statement: for the real package at data/stories/continuity-initiative scene 1A, the statement of k_sl_1a_j_r2 does not appear in the all-alternates prompt, while the statements of k_sl_1a_j_r1 and k_sl_1a_j_r3 do (assemble the prompt the way storygame/audit_budget.py `_narration_measurement` does with the same patch of _request_item_facts, or expose nothing new in the source: the test may import the private helpers `_state_for` and its own copy of the measurement). Must FAIL today.
4. test_real_package_pins_are_unchanged_control: tests/fixtures/deep_turn_budget.json scene 1A is exactly narration_chars 5485 and narration_chars_all_alternates 5597, and every scene's current report row is <= its pin for both figures. Must PASS today.
Name controls with the suffix _control only where listed (tests 2 and 4 are named exactly as above; test 2 must end _control: use test_non_contradictory_alternates_still_count_control and test_real_package_pins_are_unchanged_control). Tests 1 and 3 must fail for the right reason (an assertion about the figure or the statement), never an ImportError, NameError or fixture bug.
HOW TO RUN (from {R}; never bare python, never uv): `{ENV} {PY} -m pytest {TEST} -q -p no:cacheprovider -rA 2>&1 | tail -30`; format with `{PY} -m ruff format {TEST} && {PY} -m ruff check {TEST}`. Do not make the failing tests pass."""

tests_check = f"""set -o pipefail
cd {R}
{ENV}
{PY} -m ruff check {TEST}
{PY} -m ruff format --check {TEST}
{PY} -m pytest {TEST} -q -p no:cacheprovider -rA > /tmp/audit-branches-red.txt 2>&1
{PY} - <<'PY'
import re, sys
text = open('/tmp/audit-branches-red.txt').read()
status = dict((m.group(2), m.group(1)) for m in re.finditer(r'^(PASSED|FAILED|ERROR) \\S+::(\\w+)', text, re.M))
want = {{'test_contradictory_requires_count_once_in_all_alternates': 'FAILED', 'test_non_contradictory_alternates_still_count_control': 'PASSED', 'test_real_1a_all_alternates_prompt_omits_the_branch_statement': 'FAILED', 'test_real_package_pins_are_unchanged_control': 'PASSED'}}
bad = [f'{{n}}: expected {{w}}, got {{status.get(n)}}' for n, w in want.items() if status.get(n) != w]
if 'ERROR' in status.values() or re.search(r'ImportError|ModuleNotFoundError|SyntaxError|NameError|collection error', text):
    bad.append('errors or import/syntax/name problems present')
print(text[-2500:])
if bad:
    print('RED-CHECK FAILED'); [print(' -', b) for b in bad]; sys.exit(1)
print('RED-CHECK OK')
PY
"""

impl_spec = f"""You are a code worker for the freytag-forge repository at {R}. Boundary: NO model call, NO network call, never git commit. You own ONLY {SRC}. Do not edit any test, fixture (tests/fixtures/deep_turn_budget.json), data file or other source file, and do not run `python -m storygame.audit_budget --write`.

{RULE}

Make the tests in {TEST} pass by changing `_selected_entries` in {SRC} (and its docstring, plus the module docstring if it describes the figure). Contradiction test: two requires predicates conflict when they name the same fact_id and both `equals` values are not None and differ. Keep the change small and story-agnostic.
HOW TO RUN (from {R}; never bare python, never uv): `{ENV} {PY} -m pytest {TEST} tests/test_audit_budget.py -q -p no:cacheprovider 2>&1 | tail -20`; then `{PY} -m ruff format {SRC} && {PY} -m ruff check {SRC}`. Report the new scene 1A figures from `{PY} -m storygame.audit_budget 2>&1 | grep -E '^ +1A'` (read only; do not write the fixture)."""

impl_check = f"""set -o pipefail
cd {R}
{ENV}
{PY} -m ruff check {SRC}
{PY} -m ruff format --check {SRC}
{PY} -m pytest {TEST} tests/test_audit_budget.py -q -p no:cacheprovider 2>&1 | tail -15
git diff --quiet -- tests/fixtures/deep_turn_budget.json
{PY} -m storygame.audit_budget 2>&1 | grep -E '^ +[0-9][A-C]'
"""


def manifest(name, key, task_type, spec, check, owned, timeout):
    task = {
        "key": key,
        "task_type": task_type,
        "engine": "codex",
        "model": "gpt-5.6-luna",
        "engine_args": ["-c", "model_reasoning_effort=medium"],
        "max_attempts": 2,
        "timeout_s": timeout,
        "check_timeout_s": 900,
        "ownership": owned,
        "expect_files": owned,
        "spec": spec,
        "check": check,
        "verified": "the audit counts exclusive branches once; pins untouched",
    }
    return {
        "run_name": f"1a-audit-branches-{name}",
        "workdir": f"/home/bcorfman/dev/ringer-work/1a-audit-branches-{name}",
        "max_parallel": 1,
        "worktrees": False,
        "repo": R,
        "tasks": [task],
    }


for name, m in (
    ("tests", manifest("tests", "write-audit-branch-tests", "test-hardening", tests_spec, tests_check, [TEST], 1200)),
    ("impl", manifest("impl", "count-exclusive-branches-once", "code-feature", impl_spec, impl_check, [SRC], 1200)),
):
    path = Path(D) / f"audit-branches-{name}-manifest.json"
    path.write_text(json.dumps(m, indent=2) + "\n")
    print(path)
