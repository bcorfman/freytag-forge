# ruff: noqa: E501
"""Round 34d: record the engine's own scene clock in hosted blind-player turn records, and label it in make_case (owner 2026-11-24).

Replaces round 34c's derivation: on the saved hosted 1B report a clock worked out from the records gave 7 at the exit
while the engine floor is 8, so records alone cannot recover the hosted clock. The hosted state summary already
carries `turns_since_scene_entry` (storygame/web_demo.py `_state_summary`). Two one-task manifests, one per repo.
"""

import json
from pathlib import Path

FF = "/home/bcorfman/dev/freytag-forge"
TOOLS = "/home/bcorfman/dev/ringer-work/qual-20261122/tools"
PY = f"{FF}/.venv/bin/python"
WORK_A = "/home/bcorfman/dev/ringer-work/factory-34d-harness"
WORK_B = "/home/bcorfman/dev/ringer-work/factory-34d-makecase"

DEFINITION = (
    "turns_since_entry is the engine's own scene clock read from the game state after the turn: turns played since the player "
    "entered the scene named in scene_id (turn_index is the engine's whole-game turn counter). A scene's exit is allowed only "
    "once the clock inside that turn reaches the scene's min_turns, so on the turn that changes scene the recorded clock restarts "
    "in the new scene and the exit check saw the previous turn's value plus one."
)

SPEC_A = (
    "You are an engineer on freytag-forge. Your current working directory IS a git worktree of the repo (detached at HEAD). Edit files here directly. "
    "NEVER git commit, NEVER call a model, NEVER use the network, never run `uv`, never run Playwright or any browser test. Write NOTES.txt (never committed) with each ambiguity and your choice. "
    "Read AGENTS.md first.\n\n"
    "You may edit ONLY: frontend/e2e/blind-player.js and frontend/e2e/blind-player.test.js. Touch nothing else.\n\n"
    "PROBLEM. The hosted blind-player harness writes one record per turn (the object returned near the end of the turn-record mapping in frontend/e2e/blind-player.js, with fields turn, input, raw_input, profile, text, rejected, story_complete, rejection, scene_id, semantic_match, grounding_ids, candidates_offered, matched_candidate, transition_cause, outcome, game_break). "
    "Its `scene_id` comes from the turn response's `state`, which is the server's state summary (storygame/web_demo.py `_state_summary`). That summary also carries `turn_index` and `turns_since_scene_entry` (the engine's own scene clock, `state.turn_index - state.scene_entered_at_turn`), but the record drops them. "
    "Blind readers then guess the clock from the record's `turn` number and misread a scene's `min_turns` floor. Records alone cannot recover the clock (a saved hosted 1B report exits at record turn 7 while the engine floor is 8).\n\n"
    "WHAT TO BUILD. In the per-turn record add two fields right after `scene_id`: `turn_index: state?.turn_index ?? null` and `turns_since_entry: state?.turns_since_scene_entry ?? null`, read from the same `state` object `scene_id` comes from. "
    "Do not change any other field, the order of existing fields, or the stateEvidence helper. If the same record builder is used for question (clarification) turns, they get the fields too. "
    'TEST FIRST in frontend/e2e/blind-player.test.js, in the style of the existing record test there (the one that builds a payload with `state: { scene_id: "A" }` and checks the mapped record): (1) a state with turn_index 9 and turns_since_scene_entry 8 gives a record with turn_index 9 and turns_since_entry 8; (2) a state without them gives null for both; (3) update any existing deep-equality assertion on the record shape that now legitimately gains the two fields (say which in NOTES.txt). The existing test `turnLog emits the contract without prompt, delivery, or state` is one: the record still must not carry the prompt, the delivery or the rest of the state object; these two counters are a deliberate, owner-approved exception, so add them to its expected records and keep every other exclusion it checks. '
    "Run the tests with `cd frontend && node --test e2e/blind-player.test.js` and then the whole node suite `cd frontend && npm test`."
)

CHECK_A = f"""set -e
WORK={WORK_A}
mkdir -p "$WORK/out"
[ -e frontend/node_modules ] || ln -s {FF}/frontend/node_modules frontend/node_modules
git reset -q
git add -A -- . ':(exclude)NOTES.txt'
git reset -q -- frontend/node_modules 2>/dev/null || true
bad=$(git diff --cached --name-only --diff-filter=d | grep -vE '^frontend/e2e/blind-player(\\.test)?\\.js$' || true)
[ -z "$bad" ] || {{ echo "files outside ownership staged: $bad"; exit 1; }}
git diff --cached --name-only | grep -qx frontend/e2e/blind-player.js || {{ echo "blind-player.js was not changed"; exit 1; }}
git diff --cached --name-only | grep -qx frontend/e2e/blind-player.test.js || {{ echo "blind-player.test.js was not changed"; exit 1; }}
grep -q 'turns_since_entry: state?.turns_since_scene_entry' frontend/e2e/blind-player.js || {{ echo "record does not read turns_since_scene_entry from state"; exit 1; }}
grep -q 'turns_since_entry' frontend/e2e/blind-player.test.js || {{ echo "no test mentions turns_since_entry"; exit 1; }}
start=$(date +%s)
(cd frontend && PATH={FF}/.venv/bin:$PATH node --test src/*.test.js e2e/*.test.js) > "$WORK/out/node-test.txt" 2>&1 || {{ grep -nE "✖|ℹ fail" "$WORK/out/node-test.txt" | head -20; tail -40 "$WORK/out/node-test.txt"; exit 1; }}
grep -E "ℹ (pass|fail)" "$WORK/out/node-test.txt"
took=$(( $(date +%s) - start ))
echo "node tests took $took s (budget 180 s)"
[ "$took" -le 180 ] || {{ echo "over the 180 s budget"; exit 1; }}
git diff --cached > "$WORK/out/record-scene-clock.patch"
test -s "$WORK/out/record-scene-clock.patch"
"""

SPEC_B = (
    "You are a tooling engineer. Your current working directory IS a git worktree of the qualification tools repo ("
    + TOOLS
    + "), detached at HEAD. Edit files here directly. "
    f"NEVER git commit, never touch the original tools repo, never edit anything under {FF} (read it only), never call a model, never use the network, never run `uv`. "
    f"Use the interpreter {PY}; run tests as `PYTHONPATH=$PWD {PY} -m pytest -q -p no:cacheprovider tests`; never pass --cov. "
    f"Format and lint ONLY with `{PY} -m ruff format make_case.py tests/test_make_case.py` and `{PY} -m ruff check make_case.py tests/test_make_case.py` exactly as written (ruff's default settings; this repo has no ruff config). "
    "Write NOTES.txt (never committed) with each ambiguity and your choice.\n\n"
    "You may edit ONLY: make_case.py and tests/test_make_case.py (new). make_case.py is not yet ruff-clean (one-line imports, semicolons); fixing what ruff reports in it is allowed and expected.\n\n"
    "CONTEXT. make_case.py builds a sealed evaluation case from a saved scene report. It copies each replicate's `turns` list unchanged into solver/records.json. "
    "Hosted reports will soon carry two engine fields on each turn record: `turn_index` and `turns_since_entry` (the engine's own scene clock after the turn). Older reports do not have them. "
    "The clock must NOT be worked out from other record fields: that was tried and gives a wrong answer on hosted reports.\n\n"
    "WHAT TO BUILD. (1) In make_case.py, when at least one turn record in the report has an integer `turns_since_entry` (bool is not an integer here), add one top-level key `turns_since_entry_definition` to records.json with exactly this text: "
    + json.dumps(DEFINITION)
    + ". When no turn has it, records.json stays exactly as today (no key, no derived numbers). Never compute, fill in or change `turns_since_entry` or `turn_index`; copy the turn records as today. Keep the rest of make_case's behaviour and output unchanged. "
    "(2) TESTS in tests/test_make_case.py, hermetic, under 30 s, using tmp_path and a tiny synthetic report with the same top-level shape make_case reads (`scene`, `replicates` with `replicate`, `scene`, `turns`, `stuck_turns`, `exit_cause`, `ending_reached`); calling main via sys.argv or by refactoring a small helper is fine; the `git archive` of HEAD of "
    + FF
    + " that main runs is acceptable in a test: (a) turns carrying `turns_since_entry` and `turn_index` -> records.json has the definition text and every turn keeps its values unchanged; (b) turns without them -> no definition key and no added fields; (c) a turn with `turns_since_entry: true` alone does not count."
)

CHECK_B = f"""set -e
WORK={WORK_B}
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
echo "tests took $took s (budget 60 s)"
[ "$took" -le 60 ] || {{ echo "tests over the 60 s budget"; exit 1; }}
{PY} -m ruff check make_case.py tests/test_make_case.py
{PY} -m ruff format --check make_case.py tests/test_make_case.py
grep -nE 'def turns_since_entry|scene_entered_at_turn' make_case.py && {{ echo "make_case must not derive the clock"; exit 1; }} || true
rm -rf "$WORK/case-old" "$WORK/case-new"
mkdir -p "$WORK/case-old" "$WORK/case-new"
{PY} - "$WORK/new-report.json" <<'E'
import json, sys
rep = {{"scene": "1B", "replicates": [{{"replicate": 1, "scene": "1B", "stuck_turns": [], "exit_cause": "play", "ending_reached": True,
       "turns": [{{"turn": 1, "scene_id": "1B", "outcome": "committed", "turn_index": 9, "turns_since_entry": 1}},
                 {{"turn": 2, "scene_id": "1C", "outcome": "committed", "turn_index": 10, "turns_since_entry": 0}}]}}]}}
json.dump(rep, open(sys.argv[1], "w"))
E
PYTHONPATH=$PWD {PY} make_case.py old-1B /home/bcorfman/dev/ringer-work/qual-20261122/reports/1B.json HEAD "$WORK/case-old" > "$WORK/out/make_case_old.txt" 2>&1 || {{ cat "$WORK/out/make_case_old.txt"; exit 1; }}
PYTHONPATH=$PWD {PY} make_case.py new-1B "$WORK/new-report.json" HEAD "$WORK/case-new" > "$WORK/out/make_case_new.txt" 2>&1 || {{ cat "$WORK/out/make_case_new.txt"; exit 1; }}
{PY} - "$WORK/case-old/old-1B/solver/records.json" "$WORK/case-new/new-1B/solver/records.json" /home/bcorfman/dev/ringer-work/qual-20261122/reports/1B.json <<'E'
import json, sys
old, new, src = (json.load(open(p)) for p in sys.argv[1:4])
assert "turns_since_entry_definition" not in old, "old report must not get a definition"
for run, rep in zip(old["runs"], src["replicates"]):
    assert run["turns"] == rep["turns"], "old report turns changed"
d = new.get("turns_since_entry_definition", "")
assert d == {json.dumps(DEFINITION)}, "definition text differs: " + repr(d[:120])
assert [t["turns_since_entry"] for t in new["runs"][0]["turns"]] == [1, 0], "recorded clock changed"
assert [t["turn_index"] for t in new["runs"][0]["turns"]] == [9, 10], "recorded turn_index changed"
print("make_case end-to-end: ok")
E
cp make_case.py tests/test_make_case.py "$WORK/out/"
git diff --cached > "$WORK/out/make-case-clock-label.patch"
test -s "$WORK/out/make-case-clock-label.patch"
"""


def manifest(work, repo, key, task_type, spec, check, ownership, verified):
    return {
        "run_name": "qual-turns-since-entry",
        "workdir": work,
        "max_parallel": 1,
        "worktrees": True,
        "repo": repo,
        "tasks": [
            {
                "key": key,
                "task_type": task_type,
                "engine": "codex",
                "engine_args": ["-c", "model_reasoning_effort=medium"],
                "max_attempts": 2,
                "timeout_s": 1800,
                "check_timeout_s": 600,
                "ownership": ownership,
                "spec": spec,
                "check": check,
                "expect_files": [],
                "verified": verified,
            }
        ],
    }


here = Path(__file__).parent
(here / "round34d-harness-manifest.json").write_text(
    json.dumps(
        manifest(
            WORK_A,
            FF,
            "record-scene-clock",
            "code-feature",
            SPEC_A,
            CHECK_A,
            ["frontend/e2e/blind-player.js", "frontend/e2e/blind-player.test.js"],
            "Each hosted blind-player turn record carries the engine's turn_index and scene clock from the server state.",
        ),
        indent=2,
    )
    + "\n"
)
(here / "round34d-makecase-manifest.json").write_text(
    json.dumps(
        manifest(
            WORK_B,
            TOOLS,
            "make-case-clock-label",
            "code-feature",
            SPEC_B,
            CHECK_B,
            ["make_case.py", "tests/test_make_case.py"],
            "make_case labels a recorded scene clock and never derives one; old reports are unchanged.",
        ),
        indent=2,
    )
    + "\n"
)
