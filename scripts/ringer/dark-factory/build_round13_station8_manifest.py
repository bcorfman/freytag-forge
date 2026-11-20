# ruff: noqa: E501  (spec strings are prose briefs for a worker)
"""Round 13: factory station 8 (triage), no model call: failing playtest turns routed to one of four classes by engine-state signals first, judge flags second.

One Codex task. Usage: build_round13_station8_manifest.py
"""

from __future__ import annotations

import json
from pathlib import Path

REPO = "/home/bcorfman/dev/freytag-forge"
WORK = "/home/bcorfman/dev/ringer-work/factory-triage"

OWNED = [
    "factory/stations/triage.py",
    "factory/stations/__init__.py",
    "tests/test_factory_triage.py",
    "tests/test_factory_stations.py",
    "tests/shard_durations.json",
]

SPEC = """You are a Python engineer. Your current working directory IS a git worktree of @REPO@ (detached at HEAD). Edit files here directly. NEVER git commit, never touch @REPO@ itself, never run `uv`, never call a model or the network. FIRST run: [ -e .venv ] || ln -s @REPO@/.venv .venv . Ruff: `.venv/bin/python -m ruff check <files>` and `.venv/bin/python -m ruff format <files>` (line length 120, double quotes, Python 3.12, standard library only). Never pass --cov to pytest. Run tests as `PYTHONPATH=$PWD:$PWD/packages/worldkeeper/src TMPDIR=/tmp .venv/bin/python -m pytest -q -p no:cacheprovider -n 0 <test files>`.

BACKGROUND. `factory/line.py` drives tickets through fixed stations with handlers `Callable[[Ticket, datetime], StationResult]` (`StationResult(passed, check, output, tokens=0)`). `factory/stations/` already holds handlers for stations 2, 5 and 6; read `factory/stations/__init__.py`, `factory/stations/prompt_snapshot.py` (its style, its 4000-character output cap, how it never raises for bad payloads) and `tests/test_factory_stations.py` first. `factory/tickets.py` defines `TicketClass` (story_data, world_model, narrator_prompt, engine). This task builds station 8, `Station.TRIAGE`: each failed live-playtest turn is classified into exactly one of the four `TicketClass` values, by a script. A model (Sonnet) will later resolve only the turns the script cannot classify; this task builds NO model call, only the hook for it. Station 7 (live playtest) does not exist yet, so the failing-turn packet format below is the contract it will be written to.

THE FAILING-TURN PACKET (a dict; this is the input contract). Keys: `key` (str, unique turn id such as "1B/r2/t5", required), `scene` (str, required), `player_input` (str, default ""), `narration` (str, default ""), `stuck` (bool, default false: the engine state shows the scene never changed and no earned exit moved closer; computed from engine state, never by a judge), `candidates_offered` (list[str], default []), `matched_candidate` (str or null, default null), `committed` (bool or null, default null: did the matched candidate commit its effects), `engine_error` (str or null, default null: an exception or invariant message from the engine), `match_issues` (list[str], default []), `item_facts_issues` (list[str], default []), `item_facts_unplaced` (list[str], default []), `flags` (list[str], default []: judge flag names that fired as "yes"; the names are the ones in `bench/failure_report.py`, constants FACT and CONT, plus `facts_after_wrong`). A packet missing `key` or `scene`, or with a wrong type, is rejected with a plain message naming the key and field; never raise for it from the handler.

THE RULES (deterministic; engine-state evidence outranks judge flags because the judges are noisy). Evaluate in this order and stop at the first that applies:
 R1 `engine_error` non-empty -> engine.
 R2 `stuck` and `candidates_offered` empty -> story_data (nothing in the story offers this move).
 R3 `stuck`, `candidates_offered` non-empty, `matched_candidate` null, `match_issues` empty -> story_data (the matcher found no evidence for any offered candidate).
 R4 `stuck`, `candidates_offered` non-empty, `matched_candidate` null, `match_issues` non-empty -> narrator_prompt (the match call's own output was invalid).
 R5 `stuck`, `matched_candidate` set, `committed` is false -> engine (a matched candidate did not commit).
 R6 `stuck` with any other combination -> unclear.
 Otherwise (not stuck) collect classes from two sources: world_model when `item_facts_issues` or `item_facts_unplaced` is non-empty, or any flag in WORLD_FLAGS = {facts_after_wrong, missed_change, invented_change, dropped_true_condition, kept_ended_condition, state_as_place}; narrator_prompt when any flag in NARRATOR_FLAGS = {narration_contradicts_given_facts, contradicts_stated_fact, restarts_scene, command_not_finished, reveals_hidden_canon}. Exactly one class collected -> that class (rule R7 for world_model, R8 for narrator_prompt). Both collected, no signal at all, or any flag name in neither set -> unclear (rule R9, with a reason naming the conflict, the missing signal or the unknown flag).
 Each routed turn is `{"key", "scene", "class" (a TicketClass value, or "unclear"), "rule" ("R1".."R9"), "reasons": [short strings naming the exact signals that decided it]}`. Put WORLD_FLAGS, NARRATOR_FLAGS and the rule order in module constants, with the rule ids, so a later round can read them.

YOUR TASK. Create `factory/stations/triage.py` and `tests/test_factory_triage.py`; edit `factory/stations/__init__.py` to add `Station.TRIAGE: triage_handler(root)` to `build_handlers` and update its trailing comment (stations 0, 1, 3, 4, 7 and 9 remain unbuilt); edit `tests/test_factory_stations.py` ONLY where its `build_handlers` assertion expects exactly three stations (make it expect four). Add the new test file's entry to `tests/shard_durations.json` by running `PYTHONPATH=$PWD:$PWD/packages/worldkeeper/src .venv/bin/python scripts/regen_shard_durations.py --missing-only` (it must change only that file's entry). Own nothing else.

triage.py:
- `classify_turn(packet: dict) -> dict` (the routed-turn dict above; raises `ValueError(message)` for a malformed packet) and `classify_turns(packets: list[dict]) -> list[dict]` (keeps input order; a malformed packet becomes a routed turn with class "unclear", rule "R9" and the validation message as its reason, so one bad packet never hides the others).
- `unclear_packet(packets, routed, *, max_turns=20, max_narration=600) -> list[dict]`: the packet for a later Sonnet resolver. It holds only the unclear turns, at most `max_turns`, each reduced to `key`, `scene`, `player_input`, `narration` cut to `max_narration` characters, the signal fields, the `flags` names and the routed `reasons`. It must carry NO judge reasoning text and no scenario text: there is no field for them in a packet, so a test asserts that unknown extra keys on an input packet (for example `reasoning` or `scenario_text`) never appear in the output.
- `route(packets, *, resolver=None) -> tuple[list[dict], list[dict]]`: classify, then, when `resolver` is given and there are unclear turns, call `resolver(unclear_packet(...))`, which returns `dict[key, class name]`. Accept only values that are one of the four `TicketClass` values; anything else, a key not asked about, or a resolver exception leaves the turn unclear (never raise). A resolved turn gets rule "RM" and the reason "resolved by model". Returns `(routed, still_unclear)`. Never import or call any model client in this module.
- `escalations(log: list[dict], routed: list[dict], *, threshold=3) -> list[dict]`: the plan's escalation rule: three failures of the same class in one scene stop story work on that scene and send one packet to the planner. Count DISTINCT turn keys per (scene, class), over the log entries plus `routed`, ignoring class "unclear", so the same turn rerun or logged twice counts once. Return one dict per (scene, class) at or over the threshold: `{"scene", "class", "count", "keys": sorted list}`.
- `append_log(path: Path, routed: list[dict], ticket_id: str, now: datetime) -> None` and `read_log(path: Path) -> list[dict]`: a JSONL file, one line per routed turn `{"key","scene","class","rule","ticket","at"}`. `append_log` skips a key already in the file with the same class (idempotent on a retry), creates parent directories, and ignores class "unclear" entries. `read_log` returns [] for a missing file and skips a corrupt line instead of raising.
- `triage_handler(root: Path | None = None, resolver=None) -> StationHandler`. `root` defaults to the repository root. Payload keys: `turns` (REQUIRED list of packets, or the path of a JSON file holding that list, relative paths resolve against root), `log_path` (optional, default none: no log and no escalation check), `out_path` (optional: write the full routing JSON `{"routed": [...], "unclear": [...], "escalations": [...]}` there, indent 2). The handler routes the turns (with the injected resolver), appends the log when `log_path` is given, computes escalations, and returns `StationResult(passed, "triage", output)` with tokens 0. It passes when no turn is still unclear. The output is the routing summary: one line per turn `<key> <class> <rule>`, then one line `escalate <scene> <class> <count>` per escalation, cut to 4000 characters with a note of how many lines were cut. On failure (a missing or empty `turns`, an unreadable file, or still-unclear turns) it returns `StationResult(False, "triage", reason)`; the unclear case names each unclear key and says a model resolver is needed. An escalation does NOT fail the station; it only appears in the output and in `out_path`. Never raise for a bad payload.
- A CLI: `python -m factory.stations.triage --turns FILE [--log FILE] [--out FILE]` (expose `main(argv=None) -> int`): prints the same summary lines, exit 0 when every turn routed, 1 when some turn is unclear, 2 for an unreadable `--turns` file.

TESTS (`tests/test_factory_triage.py`; hermetic, tmp_path only, no network, no model, no bench, no story loading). TIME BUDGET: the whole file runs in under 10 seconds; it needs only small literal packets. Cover: each rule R1 to R9 with one packet and the exact class and rule; engine evidence outranking a judge flag (a stuck packet with a world flag still routes by R2); the conflict case (one world flag and one narrator flag is unclear R9); no signal; an unknown flag name; a malformed packet (missing `key`, wrong type) becomes unclear without hiding the others and keeps order; `unclear_packet` cut length, `max_turns`, and that extra keys like `reasoning` and `scenario_text` never appear in it; `route` with a resolver that classifies, returns a bad class, omits a key, and raises; `escalations` at 2 and at 3 distinct keys, the same key repeated counting once, "unclear" ignored, and two scenes counted apart; `append_log` idempotence, parent directory creation and `read_log` of a missing file and of a corrupt line; the handler passing with all turns routed, failing for still-unclear turns and naming them, failing for missing `turns`, loading `turns` from a file path, writing `out_path`, reporting an escalation without failing, and the 4000-character cap with a cut count; `main` exit codes 0, 1 and 2; `build_handlers` holds `Station.TRIAGE`.

HARD LIMITS. Edit only the five files above. Never edit `bench/`, `factory/config/`, `factory/checks/`, other factory modules or other tests. Do not add dependencies. Write NOTES_13.txt (worktree root, never committed) listing every rule you found ambiguous and the choice you made.
"""

CHECK = """set -e
WORK=@WORK@
mkdir -p "$WORK/out"
export PYTHONPATH=$PWD:$PWD/packages/worldkeeper/src TMPDIR=/tmp
[ -e .venv ] || ln -s @REPO@/.venv .venv
git add -A -- factory tests
bad=$(git diff --cached --name-only | grep -vxF -e factory/stations/triage.py -e factory/stations/__init__.py -e tests/test_factory_triage.py -e tests/test_factory_stations.py -e tests/shard_durations.json || true)
[ -z "$bad" ] || { echo "files outside ownership staged: $bad"; exit 1; }
for f in factory/stations/triage.py tests/test_factory_triage.py; do [ -s "$f" ] || { echo "missing $f"; exit 1; }; done
grep -q 'test_factory_triage.py' tests/shard_durations.json || { echo "tests/shard_durations.json has no entry for test_factory_triage.py"; exit 1; }
if grep -n -i -E "anthropic|openai|claude|requests|urllib|httpx" factory/stations/triage.py; then echo "triage.py must not reference a model client or the network"; exit 1; fi
start=$(date +%s)
.venv/bin/python -m pytest -q -p no:cacheprovider -n 0 tests/test_factory_triage.py
took=$(( $(date +%s) - start ))
echo "triage tests took $took s (budget 20 s)"
[ "$took" -le 20 ] || { echo "triage tests over the 20 s budget"; exit 1; }
.venv/bin/python -m pytest -q -p no:cacheprovider -n 0 tests/test_factory_stations.py tests/test_factory_line.py tests/test_factory_frozen.py tests/test_regen_shard_durations.py
.venv/bin/python -m ruff check factory/stations tests/test_factory_triage.py tests/test_factory_stations.py
.venv/bin/python -m ruff format --check factory/stations tests/test_factory_triage.py tests/test_factory_stations.py
# independent probe through the CLI: one packet per rule, checked against the real output
out="$WORK/out/probe.out"
tmp=$(mktemp -d)
cat > "$tmp/turns.json" <<'JSON'
[
 {"key": "p/r1", "scene": "1B", "engine_error": "invariant broke"},
 {"key": "p/r2", "scene": "1B", "stuck": true, "candidates_offered": []},
 {"key": "p/r3", "scene": "1B", "stuck": true, "candidates_offered": ["a"], "matched_candidate": null},
 {"key": "p/r4", "scene": "1B", "stuck": true, "candidates_offered": ["a"], "match_issues": ["bad json"]},
 {"key": "p/r5", "scene": "1B", "stuck": true, "candidates_offered": ["a"], "matched_candidate": "a", "committed": false},
 {"key": "p/r7", "scene": "2A", "flags": ["missed_change"]},
 {"key": "p/r8", "scene": "2A", "flags": ["restarts_scene"]},
 {"key": "p/r9", "scene": "2A", "flags": ["missed_change", "restarts_scene"]},
 {"key": "p/world3", "scene": "2A", "item_facts_issues": ["x"]}
]
JSON
set +e
.venv/bin/python -m factory.stations.triage --turns "$tmp/turns.json" --log "$tmp/log.jsonl" --out "$tmp/routing.json" > "$out" 2>&1
code=$?
set -e
cat "$out"
[ "$code" -eq 1 ] || { echo "expected exit 1 (one unclear turn), got $code"; exit 1; }
.venv/bin/python - "$tmp/routing.json" "$tmp/log.jsonl" <<'PY'
import json, sys
data = json.load(open(sys.argv[1]))
got = {t["key"]: (t["class"], t["rule"]) for t in data["routed"]}
want = {
    "p/r1": ("engine", "R1"), "p/r2": ("story_data", "R2"), "p/r3": ("story_data", "R3"),
    "p/r4": ("narrator_prompt", "R4"), "p/r5": ("engine", "R5"), "p/r7": ("world_model", "R7"),
    "p/r8": ("narrator_prompt", "R8"), "p/r9": ("unclear", "R9"), "p/world3": ("world_model", "R7"),
}
assert got == want, (got, want)
assert [t["key"] for t in data["unclear"]] == ["p/r9"], data["unclear"]
assert data["escalations"] == [], data["escalations"]
lines = [json.loads(l) for l in open(sys.argv[2])]
assert all(l["class"] != "unclear" for l in lines) and len(lines) == 8, lines
print("probe ok")
PY
# a third distinct world_model turn in 2A must escalate
cat > "$tmp/more.json" <<'JSON'
[{"key": "p/w4", "scene": "2A", "flags": ["state_as_place"]}]
JSON
.venv/bin/python -m factory.stations.triage --turns "$tmp/more.json" --log "$tmp/log.jsonl" --out "$tmp/routing2.json" >> "$out" 2>&1
grep -q "escalate 2A world_model 3" "$out" || { echo "no escalation line for 2A world_model 3"; cat "$out"; exit 1; }
# rerunning the same turns must not double count
.venv/bin/python -m factory.stations.triage --turns "$tmp/more.json" --log "$tmp/log.jsonl" --out "$tmp/routing3.json" >> "$out" 2>&1
test "$(wc -l < "$tmp/log.jsonl")" -eq 9 || { echo "log was not idempotent"; cat "$tmp/log.jsonl"; exit 1; }
git diff --cached > $WORK/out/triage.patch
test -s $WORK/out/triage.patch
"""


def build() -> dict:
    return {
        "run_name": "factory-triage",
        "workdir": WORK,
        "max_parallel": 1,
        "worktrees": True,
        "repo": REPO,
        "tasks": [
            {
                "key": "station-8",
                "task_type": "code-feature",
                "engine": "codex",
                "engine_args": ["-c", "model_reasoning_effort=high"],
                "max_attempts": 2,
                "timeout_s": 2400,
                "check_timeout_s": 600,
                "ownership": OWNED,
                "spec": SPEC.replace("@REPO@", REPO),
                "check": CHECK.replace("@REPO@", REPO).replace("@WORK@", WORK),
                "expect_files": [],
                "verified": "Triage tests under a 20 s budget plus the station, line, frozen and shard suites green; the CLI probe routes one packet per rule to the exact class and rule, escalates a third same-class turn in a scene and is idempotent on rerun; no model client referenced; ruff clean; only five files changed.",
            }
        ],
    }


if __name__ == "__main__":
    out = Path(__file__).with_name("round13-station8-manifest.json")
    out.write_text(json.dumps(build(), indent=2) + "\n", encoding="utf-8")
    print(out)
