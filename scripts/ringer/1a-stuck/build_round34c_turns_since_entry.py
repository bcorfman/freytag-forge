# ruff: noqa: E501
"""Round 34c: add the engine's turns_since_entry to every exported turn record in make_case.py (controls proposal item 6, owner 2026-11-24).

Code lives in the qualification workspace tools repo. No model call.
"""

import json
from pathlib import Path

WORK = "/home/bcorfman/dev/ringer-work/factory-34c"
REPO = "/home/bcorfman/dev/ringer-work/qual-20261122/tools"
FF = "/home/bcorfman/dev/freytag-forge"
PY = f"{FF}/.venv/bin/python"
REPORTS = "/home/bcorfman/dev/ringer-work/qual-20261122/reports"

SPEC = (
    "You are a tooling engineer. Your current working directory IS a git worktree of the qualification tools repo ("
    + REPO
    + "), detached at HEAD. Edit files here directly. "
    f"NEVER git commit, never touch the original tools repo, never edit anything under {FF} (read it only), never call a model, never use the network, never run `uv`. "
    f"Use the interpreter {PY}; run tests as `PYTHONPATH=$PWD {PY} -m pytest -q -p no:cacheprovider tests`; never pass --cov; ruff check and ruff format on python files (line length 120, Python 3.12). "
    "Write NOTES.txt (never committed) with each ambiguity and your choice.\n\n"
    "You may edit ONLY: make_case.py and tests/test_make_case.py (new).\n\n"
    "PROBLEM. make_case.py builds a sealed evaluation case from a saved scene report (for example "
    + REPORTS
    + "/1B.json). It writes solver/records.json with each replicate's `turns` list copied from the report. "
    "Each turn record has `turn` (the harness's command number), `outcome` (for example 'committed'), `rejected`, `scene_id`, `transition_cause` and more, but NOT the engine's own scene clock. "
    "The engine decides pacing with `turns_since_entry = state.turn_index - state.scene_entered_at_turn` ("
    + FF
    + "/storygame/runtime/engine.py around lines 1291 to 1303: a scene's exit is refused while `turns_since_entry < min_turns` from the package pacing windows). "
    "`turn_index` is incremented at the start of a turn (engine.py around lines 343 and 494); `scene_entered_at_turn` is set to `turn_index` when a scene is entered ("
    + FF
    + "/storygame/runtime/state.py `_assert_scene_entry_fact`, around line 273). Rejected turns may restore the state snapshot; find out whether they roll back turn_index. "
    "A blind reader of the 1B report saw the exit at `turn` 7 and wrongly concluded the 8-turn floor was broken; on the engine, the default 1B journey leaves at exactly 8 turns since entry. Readers need the engine's number, not a guess.\n\n"
    "WHAT TO BUILD. (1) In make_case.py add a pure function `turns_since_entry(turns: list[dict]) -> list[int]` returning, for each turn record in order, the value of the engine's `turns_since_entry` as seen at that turn's exit check (after that turn's own increment, in the scene the turn STARTED in). "
    "If a turn record already carries an integer `turns_since_entry` (future reports may record it), use it as is; otherwise derive it from the record fields. Work out the exact rule from the engine code and the bench harness that produced these reports ("
    + FF
    + "/bench/core.py and whatever it calls to start a scene and play a turn: how the scene is entered at the start of a replicate, whether the opening or any entry/handoff turn advances turn_index, what rejected or game-break turns do, and how the count restarts after a transition to the next scene). "
    "(2) records.json: add `turns_since_entry` to every exported turn record (keep every existing field unchanged) and add one top-level key `turns_since_entry_definition` with one or two plain sentences saying what the number means and that a scene's `min_turns` floor is compared against it. Keep the output otherwise identical, so cases built before stay readable. "
    "(3) TESTS in tests/test_make_case.py, hermetic, no model call, under 60 s: "
    f"(a) GROUND TRUTH: drive the real engine (add {FF} and {FF}/packages/worldkeeper to sys.path inside the test) the same way the bench starts a replicate of scene 1B, with a scripted provider (look at {FF}/tests/scene_harness.py and {FF}/bench/core.py for how a scripted or fake provider is wired; reuse rather than invent). Play a short sequence that includes at least one committed turn, one rejected turn if the harness can produce one cheaply, and, if feasible, the 1B exit to 1C. After each turn read `state.turn_index - state.scene_entered_at_turn` and build turn records with the same fields the bench writes; assert `turns_since_entry(records)` equals the engine's values turn for turn. If a full 1B exit cannot be reached cheaply, say so in NOTES.txt and cover the scene-change rule with a second hand-built case whose expected values you justify from the code. "
    "(b) a turn record that already has `turns_since_entry` keeps it; (c) make_case main on a tiny synthetic report (use tmp_path, `git archive` of HEAD of "
    + FF
    + " is fine and is what main already does) writes records.json whose every turn has an int `turns_since_entry` and whose `turns_since_entry_definition` is non-empty, and keeps the old fields.\n"
    "(4) In NOTES.txt, report what your function gives for each turn of each replicate in "
    + REPORTS
    + "/1B.json, and in one or two sentences whether this explains the reader's turn-7 reading (is the value at the exit turn 8, or something else, and why).\n"
)

CHECK = f"""set -e
WORK={WORK}
mkdir -p "$WORK/out"
git reset -q
git add -A -- . ':(exclude)NOTES.txt' ':(exclude).serena'
bad=$(git diff --cached --name-only --diff-filter=d | grep -vE '^(make_case\\.py|tests/test_make_case\\.py)$' || true)
[ -z "$bad" ] || {{ echo "files outside ownership staged: $bad"; exit 1; }}
git diff --cached --name-only | grep -qx tests/test_make_case.py || {{ echo "tests/test_make_case.py was not added"; exit 1; }}
start=$(date +%s)
PYTHONPATH=$PWD {PY} -m pytest -q -p no:cacheprovider tests > "$WORK/out/pytest.txt" 2>&1 || {{ tail -60 "$WORK/out/pytest.txt"; exit 1; }}
tail -3 "$WORK/out/pytest.txt"
took=$(( $(date +%s) - start ))
echo "tests took $took s (budget 120 s)"
[ "$took" -le 120 ] || {{ echo "tests over the 120 s budget"; exit 1; }}
PYFILES=$(git diff --cached --name-only --diff-filter=d | grep '\\.py$' || true)
{PY} -m ruff check --line-length 120 $PYFILES
{PY} -m ruff format --check --line-length 120 $PYFILES
grep -q 'state.turn_index' tests/test_make_case.py || {{ echo "ground-truth test does not read the engine's turn_index"; exit 1; }}
rm -rf "$WORK/case-check"
mkdir -p "$WORK/case-check"
PYTHONPATH=$PWD {PY} make_case.py check-1B {REPORTS}/1B.json HEAD "$WORK/case-check" > "$WORK/out/make_case.txt" 2>&1 || {{ cat "$WORK/out/make_case.txt"; exit 1; }}
{PY} - "$WORK/case-check/check-1B/solver/records.json" {REPORTS}/1B.json <<'E'
import json, sys
rec = json.load(open(sys.argv[1])); rep = json.load(open(sys.argv[2]))
assert isinstance(rec.get("turns_since_entry_definition"), str) and rec["turns_since_entry_definition"].strip(), "missing definition"
for run, src in zip(rec["runs"], rep["replicates"]):
    assert len(run["turns"]) == len(src["turns"]), "turn count changed"
    for t, s in zip(run["turns"], src["turns"]):
        assert isinstance(t.get("turns_since_entry"), int), f"turn {{t.get('turn')}} has no int turns_since_entry"
        for k, v in s.items():
            assert t.get(k) == v, f"field {{k}} changed on turn {{s.get('turn')}}"
    print("replicate", run["replicate"], [t["turns_since_entry"] for t in run["turns"]])
E
cp make_case.py tests/test_make_case.py "$WORK/out/"
[ -f NOTES.txt ] && cp NOTES.txt "$WORK/out/NOTES.txt"
git diff --cached > "$WORK/out/turns-since-entry.patch"
test -s "$WORK/out/turns-since-entry.patch"
"""

manifest = {
    "run_name": "qual-turns-since-entry",
    "workdir": WORK,
    "max_parallel": 1,
    "worktrees": True,
    "repo": REPO,
    "tasks": [
        {
            "key": "turns-since-entry",
            "task_type": "code-feature",
            "engine": "codex",
            "engine_args": ["-c", "model_reasoning_effort=high"],
            "max_attempts": 2,
            "timeout_s": 2400,
            "check_timeout_s": 600,
            "ownership": ["make_case.py", "tests/test_make_case.py"],
            "spec": SPEC,
            "check": CHECK,
            "expect_files": [],
            "verified": "Every exported turn record carries the engine's turns_since_entry, proven equal to the engine's own counter on a real engine replay.",
        }
    ],
}
Path(__file__).with_name("round34c-turns-since-entry-manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")
