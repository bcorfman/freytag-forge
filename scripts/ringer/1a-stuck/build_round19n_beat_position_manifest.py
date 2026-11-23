# ruff: noqa: E501  (spec strings are prose briefs for a worker)
"""Round 19n: a new pacing beat must sit before the first later-turn event (wiring spec, helper and check). FREE to build.

One Codex task. Usage: build_round19n_beat_position_manifest.py
"""

from __future__ import annotations

import json
from pathlib import Path

REPO = "/home/bcorfman/dev/freytag-forge"
WORK = "/home/bcorfman/dev/ringer-work/factory-beat-position"
OWNED = ["factory/stations/wiring.py", "tests/test_factory_wiring.py"]

COMMON = """You are a Python engineer. Your current working directory IS a git worktree of @REPO@ (detached at HEAD). Edit files here directly. NEVER git commit, never touch @REPO@ itself, never run `uv`, NEVER call a model (not `claude`, not `codex`), NEVER use the network, NEVER run `python -m bench run`. FIRST run: [ -e .venv ] || ln -s @REPO@/.venv .venv . Environment for every command: `export PYTHONPATH=$PWD:$PWD/packages/worldkeeper/src TMPDIR=/tmp`. Ruff (python files only): `.venv/bin/python -m ruff check <files>` and `.venv/bin/python -m ruff format <files>` (line length 120, Python 3.12). Never pass --cov to pytest. Run tests as `.venv/bin/python -m pytest -q -p no:cacheprovider -n 0 <files>`. Tests must be hermetic (no model call, no network, never write factory/state/). Do not add a new test file: add tests to the owned existing test files. If an OLD test pins behaviour this change deliberately changes, update that test to the new behaviour (say so in NOTES.txt); do not leave a failing test and do not weaken a test that is unrelated to the change."""

SPEC = (
    COMMON
    + """
BACKGROUND. The dark factory's wiring station (`factory/stations/wiring.py`, station 4) builds a Ringer task that makes one worker apply an already-approved plan to the story source. For plan kind `add_pacing_beat` the worker runs `storygame.story_cli new beat <scene> <id> ...`, which APPENDS the new pacing event at the END of the scene's `beats` list in `data/stories/continuity-initiative/source/scenes/<scene>.yaml`. The engine activates pacing events in LIST ORDER within one turn, and one event's effects can satisfy or break the next event's `when` in the same pass. So a beat appended after a later-turn event can be starved: in the real story a new beat at turn 9 gated on `patrol_in_house: true` sat after `patrol_leaves_1a` (turn 10), which sets `patrol_in_house: false` in the same pass, so at turn 10 the new beat never fired and `tests/test_game_path_completion.py::test_pressure_event_fires_at_its_turn_when_its_conditions_hold[1-<beat id>]` failed. In real runs the planner proposed such beats four times and the worker could not know why the test failed.

RULE. A new beat must sit in the scene's event list directly BEFORE the first other event of the same scene whose `at_turn` is greater than the new beat's `at_turn`; if no other event has a greater `at_turn`, it goes at the end. (The existing list is not fully sorted, so use exactly this rule, not "sorted order".)

CHANGE 1 (spec). In `wiring_spec`, in the `add_pacing_beat` HOW text, add one short plain paragraph that states the rule and says the CLI appends at the end, so after `new beat` and the `set` commands the worker must move the beat record in the scene file's beats list to the right place by hand (a move only: do not change the record or any other record, and keep the file's formatting; `story_cli fmt --check` must still pass). Keep the text story-neutral (no story names).

CHANGE 2 (pure helper). Add a module-level pure function in wiring.py `beat_position_error(events, beat_id, scene_id) -> str | None` taking the compiled `package.pacing.events` sequence (objects with `id`, `scene_id`, `at_turn`; read them the way `claim_evidence_change_error` or other helpers in the file read compiled objects, using plain getattr), and returning None when the beat sits where the RULE says, else a plain message such as: `beat <id> (turn T) must sit directly before event <other> (turn U), the first later-turn event of its scene; it sits at position N`. Raise nothing for a beat id that is missing: return a message.

CHANGE 3 (check). In `_check_extra`, inside the `add_pacing_beat` branch after the existing compiled-beat assertions, import and call `beat_position_error(package.pacing.events, expected["id"], plan["scene"])` and `raise SystemExit(...)` with its message when it returns one. The check script is a string template (`{{` and `}}` for literal braces in the f-string): follow the surrounding code.

TESTS (tests/test_factory_wiring.py, hermetic, fast; no model, no Ringer, use small fake event objects plus ONE test against the real compiled package loaded the way other tests in that file or tests/test_factory_fix_plan.py load it): (1) beat directly before the first later-turn event: None; (2) beat at the end when a later-turn event exists: message naming the beat, its turn and that event; (3) no later-turn event exists: end position is correct and any earlier position is an error; (4) events of OTHER scenes are ignored; (5) a missing beat id gives a message; (6) the spec text for an `add_pacing_beat` plan mentions the position rule and the CLI appending, and the other two kinds' spec text is unchanged; (7) real package: take scene 1A's real events, build the list with a fake beat of at_turn 9 inserted by the rule (it lands before the turn-10 event) and expect None, and the same fake beat appended at the end and expect an error naming the turn-10 event; do not hard-code event ids: derive the first event with at_turn > 9 from the package. If an existing test pins the exact add_pacing_beat spec text or check text, update it to the new text and say so in NOTES.txt.

HARD LIMITS. Edit only: factory/stations/wiring.py and tests/test_factory_wiring.py. NEVER edit fix_plan.py, planner.py, line.py, guard.py, probe.py, tickets.py, factory/config/*, story data under data/, bench/ or storygame/. Write NOTES.txt (worktree root, never committed) listing every ambiguity and your choice."""
)

CHECK = """set -eo pipefail
WORK=@WORK@
mkdir -p "$WORK/out"
export PYTHONPATH=$PWD:$PWD/packages/worldkeeper/src TMPDIR=/tmp
[ -e .venv ] || ln -s @REPO@/.venv .venv
git add -A -- factory tests
bad=$(git diff --cached --name-only | grep -vE '^(factory/stations/wiring\\.py|tests/test_factory_wiring\\.py)$' || true)
[ -z "$bad" ] || { echo "files outside ownership staged: $bad"; exit 1; }
git status --porcelain -- data | grep . && { echo "story data changed"; exit 1; } || true
grep -q "def beat_position_error" factory/stations/wiring.py || { echo "beat_position_error missing"; exit 1; }
grep -q "beat_position_error" factory/stations/wiring.py || exit 1
if grep -n -i -E "michelle|kristin|walt|reyes|officer|patrol" factory/stations/wiring.py; then echo "story-specific word in wiring.py"; exit 1; fi
start=$(date +%s)
.venv/bin/python -m pytest -q -p no:cacheprovider -n 0 tests/test_factory_wiring.py
took=$(( $(date +%s) - start ))
echo "wiring tests took $took s (budget 60 s)"
[ "$took" -le 60 ] || { echo "over the 60 s budget"; exit 1; }
start=$(date +%s)
.venv/bin/python -m pytest -q -p no:cacheprovider -n 8 tests/test_factory_line.py tests/test_factory_probe_routing.py tests/test_factory_followups.py tests/test_factory_fix_plan.py tests/test_factory_planner.py tests/test_factory_stations.py
took=$(( $(date +%s) - start ))
echo "neighbour tests took $took s (budget 120 s)"
[ "$took" -le 120 ] || { echo "over the 120 s budget"; exit 1; }
.venv/bin/python -m ruff check factory/stations/wiring.py tests/test_factory_wiring.py
.venv/bin/python -m ruff format --check factory/stations/wiring.py tests/test_factory_wiring.py
[ ! -e factory/state/ledger.jsonl ] || { echo "a test wrote factory/state/ledger.jsonl"; exit 1; }
git diff --cached > "$WORK/out/beat-position.patch"
test -s "$WORK/out/beat-position.patch"
"""


def build() -> dict:
    def fill(text: str) -> str:
        return text.replace("@REPO@", REPO).replace("@WORK@", WORK)

    return {
        "run_name": "factory-beat-position",
        "workdir": WORK,
        "max_parallel": 1,
        "worktrees": True,
        "repo": REPO,
        "tasks": [
            {
                "key": "beat-position",
                "task_type": "code-fix",
                "engine": "codex",
                "engine_args": ["-c", "model_reasoning_effort=high"],
                "max_attempts": 2,
                "timeout_s": 3000,
                "check_timeout_s": 600,
                "ownership": OWNED,
                "spec": fill(SPEC),
                "check": fill(CHECK),
                "expect_files": [],
                "verified": "The wiring brief tells the worker where a new pacing beat must sit in the scene's event list, and the wiring check rejects a beat in the wrong place with a plain message.",
            }
        ],
    }


if __name__ == "__main__":
    out = Path(__file__).with_name("round19n-beat-position-manifest.json")
    out.write_text(json.dumps(build(), indent=2) + "\n")
    print(out)
