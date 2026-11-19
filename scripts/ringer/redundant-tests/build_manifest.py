# ruff: noqa: E501  (spec strings are prose briefs for a worker)
"""Build the one-task Ringer manifest that removes five exact-duplicate tests (stage 3 of the redundant-test scan)."""

from __future__ import annotations

import json
from pathlib import Path

REPO = "/home/bcorfman/dev/freytag-forge"
WORK = "/home/bcorfman/dev/ringer-work/redundant-tests"
OWNED = [
    "tests/test_1c_closeout.py",
    "tests/test_2a_forms_words.py",
    "tests/test_cloudflare_transport.py",
    "tests/story_source/test_l1_scene.py",
]
REMOVED = [
    "test_no_other_unique_1c_handoff_changes",
    "test_2a_supervisor_diagnosis_selects_convincing_inspection",
    "test_2a_unrelated_actions_do_not_select_an_inspection_outcome",
    "test_transport_still_reasks_for_an_invalid_provider_envelope",
]
SPEC = (
    "You are a Python engineer. Your current working directory IS a git worktree of "
    + REPO
    + " (detached at HEAD). Edit files here directly. NEVER git commit, never touch "
    + REPO
    + " itself, never run `uv`, never call a billed model or the network. FIRST run: [ -e .venv ] || ln -s "
    + REPO
    + "/.venv .venv . Run tests as `PYTHONPATH=$PWD:$PWD/packages/worldkeeper/src TMPDIR=/tmp .venv/bin/python -m pytest -q -p no:cacheprovider -n 0 <files>` (never pass --cov); ruff as `.venv/bin/python -m ruff check <files>` and `.venv/bin/python -m ruff format <files>`."
    + """

TASK. Five tests are exact duplicates of another test (same body, same inputs, same helpers, same assertions; confirmed by a per-test coverage report and by reading the code). Delete the duplicate of each pair and keep its twin:
1. tests/test_1c_closeout.py: delete `test_no_other_unique_1c_handoff_changes` (twin kept: tests/test_richer_1c.py::test_existing_1c_commands_still_reach_their_reveals).
2. tests/test_2a_forms_words.py: delete `test_2a_supervisor_diagnosis_selects_convincing_inspection` (twin kept: tests/test_candidate_matcher.py::test_scene_2a_c_r5_matches_natural_player_actions).
3. tests/test_2a_forms_words.py: delete `test_2a_unrelated_actions_do_not_select_an_inspection_outcome` (twin kept: tests/test_candidate_matcher.py::test_scene_2a_unrelated_actions_match_neither_evidence_candidate).
4. tests/test_cloudflare_transport.py: delete `test_transport_still_reasks_for_an_invalid_provider_envelope` (twin kept in the same file: `test_transport_recovers_once_from_a_malformed_provider_envelope`).
5. tests/story_source/test_l1_scene.py: delete `test_mini_ok_is_clean` (twin kept: tests/story_source/test_l1_root.py::test_mini_ok_is_clean).
Delete the whole function, its decorators and any comment that only describes it. Then remove anything in the same file that only the deleted tests used: imports, module constants, helpers (check each name with a search of the file; for tests/test_2a_forms_words.py also check whether `SCENE_2A_OUTCOME_CANDIDATES`, `SCENE_2A_CANDIDATES` and the `uniquely_matched_authored_handoff` import are still used by remaining tests in that file; if the file ends up with no tests, say so in NOTES_redundant.txt at the worktree root and keep the file). Edit no other file. Never touch the twins, never weaken another test.

DONE WHEN the owned files pass, ruff check and ruff format --check are clean on them, none of the five function names exists in the repo any more, and the twins still exist."""
)


def check() -> str:
    names = " ".join(REMOVED + ["test_mini_ok_is_clean"])
    return f"""set -eo pipefail
[ -e .venv ] || ln -s {REPO}/.venv .venv
export PYTHONPATH=$PWD:$PWD/packages/worldkeeper/src TMPDIR=/tmp
F="tests/test_1c_closeout.py tests/test_richer_1c.py tests/test_2a_forms_words.py tests/test_candidate_matcher.py tests/test_cloudflare_transport.py tests/story_source/test_l1_scene.py tests/story_source/test_l1_root.py"
.venv/bin/python -m pytest -q -p no:cacheprovider -n 0 $F 2>&1 | tail -4
.venv/bin/python -m pytest --collect-only -q -p no:cacheprovider -n 0 $F 2>&1 | grep -E "tests collected" | tee /tmp/redundant_collect.txt
grep -q "219/220 tests collected" /tmp/redundant_collect.txt || {{ echo "expected 219/220 tests collected (226/227 minus 7 removed)"; exit 1; }}
.venv/bin/python -m ruff check {" ".join(OWNED)}
.venv/bin/python -m ruff format --check {" ".join(OWNED)}
for n in {names}; do
  c=$(git grep -c "def $n" -- tests | awk -F: '{{s+=$2}} END {{print s+0}}')
  case $n in test_mini_ok_is_clean) want=1;; *) want=0;; esac
  [ "$c" = "$want" ] || {{ echo "def $n appears $c times, expected $want"; exit 1; }}
done
git grep -q "def test_existing_1c_commands_still_reach_their_reveals" -- tests/test_richer_1c.py
git grep -q "def test_scene_2a_c_r5_matches_natural_player_actions" -- tests/test_candidate_matcher.py
git grep -q "def test_scene_2a_unrelated_actions_match_neither_evidence_candidate" -- tests/test_candidate_matcher.py
git grep -q "def test_transport_recovers_once_from_a_malformed_provider_envelope" -- tests/test_cloudflare_transport.py
git add -A -- tests
bad=$(git diff --cached --name-only | grep -v -x {" ".join("-e " + p for p in OWNED)} || true)
[ -z "$bad" ] || {{ echo "files outside ownership staged: $bad"; exit 1; }}
git diff --cached --binary > {WORK}/redundant.patch
test -s {WORK}/redundant.patch
"""


manifest = {
    "run_name": "redundant-tests-stage3",
    "workdir": WORK,
    "max_parallel": 1,
    "worktrees": True,
    "repo": REPO,
    "tasks": [
        {
            "key": "drop-five-duplicate-tests",
            "task_type": "code-fix",
            "engine": "codex",
            "engine_args": ["-c", "model_reasoning_effort=low"],
            "max_attempts": 2,
            "timeout_s": 900,
            "check_timeout_s": 300,
            "ownership": OWNED,
            "spec": SPEC,
            "check": check(),
            "expect_files": [],
            "verified": "the five duplicate tests are gone, their twins remain, 7 fewer tests collected in the affected files, only the four owned files changed.",
        }
    ],
}

if __name__ == "__main__":
    Path(WORK).mkdir(parents=True, exist_ok=True)
    out = Path(__file__).with_name("manifest.json")
    out.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    print(out)
