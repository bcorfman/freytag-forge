# ruff: noqa: E501
"""Round 34f: the make_case clock definition says a scene-completing incident may end a scene below min_turns (control run 1C left at clock 3 by design)."""

import json
from pathlib import Path

FF = "/home/bcorfman/dev/freytag-forge"
TOOLS = "/home/bcorfman/dev/ringer-work/qual-20261122/tools"
PY = f"{FF}/.venv/bin/python"
WORK = "/home/bcorfman/dev/ringer-work/factory-34f"

DEFINITION = (
    "turns_since_entry is the engine's own scene clock read from the game state after the turn: turns played since the player "
    "entered the scene named in scene_id (turn_index is the engine's whole-game turn counter). An ordinary exit is allowed only "
    "once the clock inside that turn reaches the scene's min_turns; a scene-completing incident (an incident with "
    "completes_scene in the story package) may end the scene earlier by design. On the turn that changes scene the recorded "
    "clock restarts in the new scene, and the exit check saw the previous turn's value plus one."
)

SPEC = (
    "You are a tooling engineer. Your current working directory IS a git worktree of the qualification tools repo ("
    + TOOLS
    + "), detached at HEAD. Edit files here directly. "
    f"NEVER git commit, never touch the original tools repo, never edit anything under {FF}, never call a model, never use the network, never run `uv`. "
    f"Use the interpreter {PY}; run tests as `PYTHONPATH=$PWD {PY} -m pytest -q -p no:cacheprovider tests`; never pass --cov. "
    f"Format and lint ONLY with `{PY} -m ruff format make_case.py tests/test_make_case.py` and `{PY} -m ruff check make_case.py tests/test_make_case.py` exactly as written.\n\n"
    "You may edit ONLY: make_case.py and tests/test_make_case.py.\n\n"
    "PROBLEM. make_case.py writes a fixed sentence into records.json under `turns_since_entry_definition`. It says a scene's exit is allowed only once the clock reaches the scene's min_turns. "
    "That is wrong for scenes with a scene-completing incident: the engine skips the min_turns floor when such an incident fires (freytag-forge storygame/runtime/engine.py, `completes_now` around line 1300). "
    "A fresh hosted run of scene 1C left the scene by its incident at clock 3 against min_turns 8, exactly as designed, and a blind reader given the current sentence would flag it as a defect.\n\n"
    "WHAT TO DO. Replace the definition text, in make_case.py and in the expected text in tests/test_make_case.py, with exactly this text: "
    + json.dumps(DEFINITION)
    + ". Change nothing else (keep how the text is split over source lines readable; the joined string must equal the text above exactly)."
)

CHECK = f"""set -e
WORK={WORK}
mkdir -p "$WORK/out"
git reset -q
git add -A -- . ':(exclude)NOTES.txt' ':(exclude).serena'
bad=$(git diff --cached --name-only --diff-filter=d | grep -vE '^(make_case\\.py|tests/test_make_case\\.py)$' || true)
[ -z "$bad" ] || {{ echo "files outside ownership staged: $bad"; exit 1; }}
PYTHONPATH=$PWD {PY} -m pytest -q -p no:cacheprovider tests > "$WORK/out/pytest.txt" 2>&1 || {{ tail -40 "$WORK/out/pytest.txt"; exit 1; }}
tail -1 "$WORK/out/pytest.txt"
{PY} -m ruff check make_case.py tests/test_make_case.py
{PY} -m ruff format --check make_case.py tests/test_make_case.py
mkdir -p "$WORK/case"
{PY} - "$WORK/report.json" <<'E'
import json, sys
json.dump({{"scene": "1C", "replicates": [{{"replicate": 1, "scene": "1C", "stuck_turns": [], "exit_cause": "play", "ending_reached": False,
          "turns": [{{"turn": 1, "scene_id": "1C", "turn_index": 1, "turns_since_entry": 1}}]}}]}}, open(sys.argv[1], "w"))
E
rm -rf "$WORK/case/c"
PYTHONPATH=$PWD {PY} make_case.py c "$WORK/report.json" HEAD "$WORK/case" > "$WORK/out/make_case.txt" 2>&1 || {{ cat "$WORK/out/make_case.txt"; exit 1; }}
{PY} - "$WORK/case/c/solver/records.json" <<'E'
import json, sys
d = json.load(open(sys.argv[1])).get("turns_since_entry_definition", "")
assert d == {json.dumps(DEFINITION)}, "definition differs: " + repr(d)
print("definition ok")
E
git diff --cached > "$WORK/out/clock-definition.patch"
test -s "$WORK/out/clock-definition.patch"
"""

manifest = {
    "run_name": "qual-controls",
    "workdir": WORK,
    "max_parallel": 1,
    "worktrees": True,
    "repo": TOOLS,
    "tasks": [
        {
            "key": "clock-definition-incidents",
            "task_type": "code-fix",
            "engine": "codex",
            "engine_args": ["-c", "model_reasoning_effort=low"],
            "max_attempts": 2,
            "timeout_s": 900,
            "check_timeout_s": 300,
            "ownership": ["make_case.py", "tests/test_make_case.py"],
            "spec": SPEC,
            "check": CHECK,
            "expect_files": [],
            "verified": "The exported clock definition says a scene-completing incident may end a scene below min_turns.",
        }
    ],
}
Path(__file__).with_name("round34f-clock-definition-manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")
