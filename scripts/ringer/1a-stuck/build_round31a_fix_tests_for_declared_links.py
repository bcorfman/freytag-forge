# ruff: noqa: E501
"""Round 31a: three tests assumed the real story has no `delivers` links; round 29b declared them. Update the tests so each keeps its purpose. Free, no model."""

import json
from pathlib import Path

import build_round21b_evidence_cap_and_spend_cap as b

b.WORK = "/home/bcorfman/dev/ringer-work/factory-31"
PY = ".venv/bin/python"
OWNED = ["tests/story_source/test_cli_set.py", "tests/test_pacing_replay.py"]
OWNED_RE = "|".join(p.replace(".", r"\.") for p in OWNED)

SETUP = f"""set -eo pipefail
WORK={b.WORK}
mkdir -p "$WORK/out"
export PYTHONPATH=$PWD:$PWD/packages/worldkeeper/src TMPDIR=/tmp
[ -e .venv ] || ln -s {b.REPO}/.venv .venv
git reset -q
"""

SPEC = b.COMMON + (
    "You may edit ONLY: tests/story_source/test_cli_set.py and tests/test_pacing_replay.py. No production code, nothing else.\n\n"
    "BACKGROUND. Round 29b declared `delivers` links on 12 real pacing beats through the story CLI, among them `inspection_window_2a` (scene 2A) which now delivers `k_inspection_window_missed`. "
    "Three tests were written when no real beat had `delivers` and now fail:\n"
    "1. tests/story_source/test_cli_set.py::test_set_add_missing_beat_delivers_returns_two_and_restores_bytes: it expects `set beat:inspection_window_2a.delivers --add k_x` to exit 2 because the field is missing; the field now exists. "
    "The other tests this file gained in round 29b1 (create a missing `delivers`, replace it afterwards, misspelled key, unknown beat, frozen id) also use `inspection_window_2a`; several of them now pass for the wrong reason (the field already exists, so nothing is created). "
    "Change every one of them that depends on the field being absent to use a real beat that has NO `delivers` (find one in the 2A scene source, for example `supervisor_impatience_2a`; confirm by loading the source), so each test again exercises creation of a missing field. Keep their assertions.\n"
    "2. tests/test_pacing_replay.py::test_replay_without_deliveries_has_no_null_grounding and ::test_clock_opened_storylets_are_not_null_grounding: they expect empty `null_grounding_ids` on the real package, but the real event now delivers `k_inspection_window_missed`. "
    "Keep each test's purpose: the first must still prove 'an event with no `delivers` fires but yields no null grounding' (derive a package copy whose events have `delivers` emptied, with pydantic `model_copy(update=...)`, the way the sibling test in that file derives copies, or use another real event with no `delivers`); "
    "the second must still prove that clock-opened STORYLETS never appear in `fired_event_ids` or `null_grounding_ids` (assert storylet ids and storylet knowledge ids are absent; the real declared pacing delivery may be present and should be asserted exactly as `('k_inspection_window_missed',)` if the pacing event fires at that state, otherwise adjust to what the state does).\n"
    "Run both files and tests/test_pacing_links.py, tests/test_pacing_links_story.py. Never weaken an assertion; say what you changed in NOTES.txt."
)

CHECK = (
    SETUP
    + f"""git add -A -- tests
bad=$(git diff --cached --name-only --diff-filter=d | grep -vE '^({OWNED_RE})$' || true)
[ -z "$bad" ] || {{ echo "files outside ownership staged: $bad"; exit 1; }}
start=$(date +%s)
out=$({PY} -m pytest -q -p no:cacheprovider -rs -n 4 tests/story_source tests/test_pacing_replay.py tests/test_pacing_links.py tests/test_pacing_links_story.py tests/test_turn_telemetry.py 2>&1) || {{ echo "$out"; exit 1; }}
echo "$out" | tail -4
case "$out" in *skipped*) echo "tests were skipped"; exit 1;; esac
took=$(( $(date +%s) - start ))
echo "took $took s (budget 300 s)"
[ "$took" -le 300 ] || {{ echo "over the 300 s budget"; exit 1; }}
PYFILES=$(git diff --cached --name-only --diff-filter=d | grep '\\.py$' || true)
[ -z "$PYFILES" ] || {PY} -m ruff check $PYFILES
[ -z "$PYFILES" ] || {PY} -m ruff format --check $PYFILES
git diff --cached > "$WORK/out/fix-tests.patch"
test -s "$WORK/out/fix-tests.patch"
"""
)

manifest = {
    "run_name": "factory-31a-fix-tests-for-declared-links",
    "workdir": b.WORK,
    "max_parallel": 1,
    "worktrees": True,
    "repo": b.REPO,
    "tasks": [
        {
            "key": "fix-tests",
            "task_type": "code-fix",
            "engine": "codex",
            "engine_args": ["-c", "model_reasoning_effort=medium"],
            "max_attempts": 2,
            "timeout_s": 1800,
            "check_timeout_s": 500,
            "ownership": OWNED,
            "spec": SPEC,
            "check": CHECK,
            "expect_files": [],
            "verified": "The three tests keep their purpose on a story whose beats now declare links; the creation tests really create a missing field.",
        }
    ],
}
Path(__file__).with_name("round31a-fix-tests-for-declared-links-manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")
