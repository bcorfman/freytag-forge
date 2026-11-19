# ruff: noqa: E501  (spec strings are prose briefs for a worker)
"""Round 9c: retire the tests whose only content was a wording pin (decided by Brandon, 2026-11-19).

Usage: build_round9c_manifest.py
"""

from __future__ import annotations

import json
from pathlib import Path

REPO = "/home/bcorfman/dev/freytag-forge"
WORK = "/home/bcorfman/dev/ringer-work/story-data-round9c"

# file -> (task key, brief of the change, check fragment run in the worktree)
TASKS = {
    "tests/test_1a_phone_thread.py": (
        "r-phone_thread",
        "DELETE the whole test function `test_delivery_texts_are_exactly_the_approved_lines`. Nothing else in the file changes, except that any module constant or import that only that test used must go (ruff will tell you).",
        """! grep -q "def test_delivery_texts_are_exactly_the_approved_lines" tests/test_1a_phone_thread.py || { echo "the retired test is still there"; exit 1; }
before=$(git show HEAD:tests/test_1a_phone_thread.py | grep -cE "^def test_")
after=$(grep -cE "^def test_" tests/test_1a_phone_thread.py)
[ "$after" -eq $((before - 1)) ] || { echo "expected exactly one test fewer: $before -> $after"; exit 1; }""",
    ),
    "tests/test_1c_closeout.py": (
        "r-closeout",
        "DELETE the whole test function `test_3a_reunion_says_the_captives_are_awake`. Nothing else changes, except that any import or constant only that test used must go (ruff will tell you).",
        """! grep -q "def test_3a_reunion_says_the_captives_are_awake" tests/test_1c_closeout.py || { echo "the retired test is still there"; exit 1; }
before=$(git show HEAD:tests/test_1c_closeout.py | grep -cE "^def test_")
after=$(grep -cE "^def test_" tests/test_1c_closeout.py)
[ "$after" -eq $((before - 1)) ] || { echo "expected exactly one test fewer: $before -> $after"; exit 1; }""",
    ),
    "tests/test_1a_back_door_gap.py": (
        "r-back_door_gap",
        "DELETE the whole test function `test_scene_1a_and_card_copy_use_the_new_wording`, and then every module constant, helper and import that nothing else in the file uses any more (for example SITUATION, PATROL_CARD_DELIVERY, PATROL_CARD_DELIVERY_SENTENCES, `re`, `story_text`; confirm each with grep before removing, keep any that another test uses). Nothing else changes.",
        """! grep -q "def test_scene_1a_and_card_copy_use_the_new_wording" tests/test_1a_back_door_gap.py || { echo "the retired test is still there"; exit 1; }
before=$(git show HEAD:tests/test_1a_back_door_gap.py | grep -cE "^def test_")
after=$(grep -cE "^def test_" tests/test_1a_back_door_gap.py)
[ "$after" -eq $((before - 1)) ] || { echo "expected exactly one test fewer: $before -> $after"; exit 1; }""",
    ),
    "tests/test_delivery_echo.py": (
        "r-delivery_echo",
        "DELETE the whole test function `test_the_badge_delivery_has_no_closing_beat`. Nothing else in the file changes, except that any import or helper only that test used must go (ruff will tell you). Do NOT touch `test_the_door_delivery_is_only_the_quote`.",
        """! grep -q "def test_the_badge_delivery_has_no_closing_beat" tests/test_delivery_echo.py || { echo "the retired test is still there"; exit 1; }
grep -q "def test_the_door_delivery_is_only_the_quote" tests/test_delivery_echo.py || { echo "the door test must stay"; exit 1; }
before=$(git show HEAD:tests/test_delivery_echo.py | grep -cE "^def test_")
after=$(grep -cE "^def test_" tests/test_delivery_echo.py)
[ "$after" -eq $((before - 1)) ] || { echo "expected exactly one test fewer: $before -> $after"; exit 1; }""",
    ),
    "tests/test_richer_1c.py": (
        "r-richer_1c",
        'Keep the test function `test_michelle_glimpse_contract_is_uncertain_and_preserves_its_metadata` (it mostly checks metadata) but REMOVE only its wording assertions, which are exactly these statements at the top of the test: the `brandon = re.search(...)` line, the `delivery_text = entry.delivery_text.casefold()` line and the three asserts on `delivery_text` (`processing line`, `alive`, `michelle`), the assert `entry.statement.count(".") == 2`, the two asserts on `entry.statement.casefold()` (`living captives`, `michelle`) and the assert `entry.delivery_text.endswith(brandon)`. Keep every other assertion in that test unchanged, including the negative-term check on `uncertain_text` and everything from `assert entry.voiceable is False` on. Then remove the helper `_story_sentence` and any import (`re`, `story_text`) that nothing else in the file uses any more; confirm with grep before removing.',
        """grep -q "def test_michelle_glimpse_contract_is_uncertain_and_preserves_its_metadata" tests/test_richer_1c.py || { echo "the metadata test must stay"; exit 1; }
for kept in "assert entry.voiceable is False" "assert entry.earn_when ==" "assert entry.action_evidence ==" "assert entry.aliases ==" "assert len(entries) == 122" "uncertain_text"; do grep -qF "$kept" tests/test_richer_1c.py || { echo "a non-wording assertion was removed: $kept"; exit 1; }; done
for gone in 'in delivery_text' 'entry.statement.count(' 'living captives' 'endswith(brandon)'; do ! grep -qF "$gone" tests/test_richer_1c.py || { echo "a wording assertion is still there: $gone"; exit 1; }; done
before=$(git show HEAD:tests/test_richer_1c.py | grep -cE "^def test_")
after=$(grep -cE "^def test_" tests/test_richer_1c.py)
[ "$after" -eq "$before" ] || { echo "no test may be removed here: $before -> $after"; exit 1; }""",
    ),
}


def spec(test: str, brief: str, key: str) -> str:
    return f"""You are a Python test engineer. Your current working directory IS a git worktree of {REPO} (detached at HEAD). Edit files here directly. NEVER git commit, never touch {REPO} itself, never run `uv`, never call a billed model or the network. FIRST run: [ -e .venv ] || ln -s {REPO}/.venv .venv ; run tests as `PYTHONPATH=$PWD:$PWD/packages/worldkeeper/src TMPDIR=/tmp .venv/bin/python -m pytest -q -p no:cacheprovider -n 0 {test}` (never pass --cov); ruff as `.venv/bin/python -m ruff check {test}` and `.venv/bin/python -m ruff format {test}` (line length 120, double quotes, Python 3.12, no new dependencies).

BACKGROUND. The default story's authored wording may now change freely, so a test that only pins the wording of a record is retired. The owner decided this on 2026-11-19: the test has no behaviour left to prove.

YOUR JOB, in {test} only: {brief}

RULES. Do not edit, weaken, reorder or rename any other test or assertion. Do not add tests. Never mark a test skip or xfail. When you finish, the remaining tests in the file pass and `ruff check` and `ruff format --check` are clean. Write one line in NOTES_{key}.txt (worktree root, never committed) naming what you removed.

HARD LIMITS. Edit only {test}. Never edit other tests, tests/shard_durations.json, tests/conftest.py, docs/, data/, scripts/ or storygame/.
"""


def check(test: str, key: str, fragment: str) -> str:
    return f"""set -eo pipefail
[ -e .venv ] || ln -s {REPO}/.venv .venv
export PYTHONPATH=$PWD:$PWD/packages/worldkeeper/src TMPDIR=/tmp
out=$(mktemp)
rc=0
.venv/bin/python -m pytest -q -p no:cacheprovider -n 0 -rs {test} > "$out" 2>&1 || rc=$?
tail -8 "$out"
[ "$rc" -eq 0 ] || exit "$rc"
if grep -E "SKIPPED|XFAIL|xfailed" "$out"; then echo "a test skips or xfails"; exit 1; fi
{fragment}
.venv/bin/python -m ruff check {test}
.venv/bin/python -m ruff format --check {test}
git add -A -- storygame tests data scripts
bad=$(git diff --cached --name-only | grep -v -x -e '{test}' || true)
[ -z "$bad" ] || {{ echo "files outside ownership staged: $bad"; exit 1; }}
git diff --cached > {WORK}/{key}.patch
test -s {WORK}/{key}.patch
"""


def build() -> dict:
    tasks = []
    for test, (key, brief, fragment) in TASKS.items():
        tasks.append(
            {
                "key": key,
                "task_type": "code-fix",
                "engine": "codex",
                "engine_args": ["-c", "model_reasoning_effort=medium"],
                "max_attempts": 2,
                "timeout_s": 1800,
                "check_timeout_s": 300,
                "ownership": [test],
                "spec": spec(test, brief, key),
                "check": check(test, key, fragment),
                "expect_files": [],
                "verified": f"{test}: the wording-pin test (or assertions) is gone, nothing else removed, remaining tests pass, ruff clean, only that file changed.",
            }
        )
    return {
        "run_name": "story-data-decouple-tests",
        "workdir": WORK,
        "max_parallel": 5,
        "worktrees": True,
        "repo": REPO,
        "tasks": tasks,
    }


if __name__ == "__main__":
    out = Path(__file__).with_name("round9c-manifest.json")
    out.write_text(json.dumps(build(), indent=2) + "\n", encoding="utf-8")
    print(out)
