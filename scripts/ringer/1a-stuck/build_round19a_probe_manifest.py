# ruff: noqa: E501  (spec strings are prose briefs for a worker)
"""Round 19a: station 12, the probe (replay recorded commands on control and candidate story). FREE to build.

One Codex task. Usage: build_round19a_probe_manifest.py
Line routing, station 7 emitting the runs, and the claim-edit fix kind are later rounds (19b, 19c).
"""

from __future__ import annotations

import json
from pathlib import Path

REPO = "/home/bcorfman/dev/freytag-forge"
WORK = "/home/bcorfman/dev/ringer-work/factory-probe"
OWNED = [
    "factory/stations/probe.py",
    "factory/stations/__init__.py",
    "factory/tickets.py",
    "factory/config/allowlist.json",
    "factory/config/probe_rules.json",
    "tests/test_factory_probe.py",
    "tests/fixtures/factory/probe_turn_records.json",
    "tests/test_factory_stations.py",
    "tests/test_factory_tickets.py",
    "tests/test_factory_frozen.py",
    "tests/shard_durations.json",
]
ALLOW_RE = (
    "^(factory/stations/probe\\.py|factory/stations/__init__\\.py|factory/tickets\\.py|"
    "factory/config/allowlist\\.json|factory/config/probe_rules\\.json|"
    "tests/test_factory_[a-z0-9_]+\\.py|tests/fixtures/factory/probe_turn_records\\.json|tests/shard_durations\\.json)$"
)

SPEC = """You are a Python engineer. Your current working directory IS a git worktree of @REPO@ (detached at HEAD). Edit files here directly. NEVER git commit, never touch @REPO@ itself, never run `uv`, NEVER call a model (not `claude`, not `codex`), NEVER use the network, and NEVER run `python -m bench run` (it bills a real narrator; `bench describe` and `bench prompt` are free and allowed). FIRST run: [ -e .venv ] || ln -s @REPO@/.venv .venv . Environment for every command: `export PYTHONPATH=$PWD:$PWD/packages/worldkeeper/src TMPDIR=/tmp`. Ruff: `.venv/bin/python -m ruff check <files>` and `.venv/bin/python -m ruff format <files>` (line length 120, Python 3.12). Never pass --cov to pytest. Run tests as `.venv/bin/python -m pytest -q -p no:cacheprovider -n 0 <files>`.

BACKGROUND. The story factory is a Python state machine (`factory/line.py`, `factory/tickets.py`, stations in `factory/stations/`). A story-data ticket is diagnosed (station 11), a planner proposes one fix, a Luna worker applies it to a per-ticket git worktree (station 4; `factory/stations/tree.py` `ticket_tree` finds it), and free gates run (5, 6). The factory has NO step that tests whether the fix actually reduces stuck turns in play. A human did that by hand with a bench probe: replay the typed commands of the failing runs on the story as it stands (the control) and on the story with the fix applied (the candidate), many replicates each, and keep the fix only if play improved. That must be station 12, run by the factory with no human, under the spend guard, because the bench calls the Cloudflare narrator, which costs money. Read first: `factory/stations/live_playtest.py` (its `_scene_runs`, `_valid_turns`, `_pre_run_budget_gate`, `_record_cloudflare_spend`, `_safe_budget_read`, `_staged_lock_path`, `billed_run_approved` handling and the injectable runner, which are the conventions to follow), `factory/stations/fun_review.py` and `diagnose.py` (handler conventions, per-ticket record file under `<workspace>/<safe ticket id>/`, `_atomic_json_write`, `_safe_id`), `factory/stations/tree.py`, `factory/guard.py` (ledger, caps) and `factory/cloudflare_spend.py` (`read_worker_budget`), `bench/README.md` (variation format, `scripts`, `fixed_turns`, `entry_state`, `run` flags) and `python -m bench run --help`. A real bench output sample is `bench/results/world-leakfix2-1b-1c/turn-records.json` (shape: `{scene_id, package_path, runs: [{status, replicate, script, scene_id, turns: [...], rejected_turns, rejected_turn_count, scene_transitions, completed, ...}]}`; a turn has `player_input`, `narration`, `grounding_ids`, `selected_knowledge_ids`, `candidates_offered`, `match_call`, `left_scene`, `turn_number`, ...). A real live report is described by `live_playtest._scene_runs` (per scene run: `turns` with `turn`, `raw_input`, `text`, `rejected`, `game_break`, `outcome`, `transition_cause`; `stuck_turns`, `exit_cause`, `transition_turn`).

BUILD 1, the enum. `factory/tickets.py`: add `PROBE = 12` to `Station` (do NOT renumber; add NO routing in this round: `factory/line.py` is not yours).

BUILD 2, the rules as data, new `factory/config/probe_rules.json` (fixed before any run; the harness is frozen): `{"replicates": 10, "max_stuck_ratio": 0.8, "min_control_stuck_turns": 1, "estimated_usd_per_turn": 0.0015, "max_runs_per_probe": 6, "max_turns_per_run": 30}`. Document in the module docstring what each means. The keep rule, applied by the pure function `judge_probe(control, candidate, rules) -> dict` returning `{"verdict": "keep"|"reject"|"inconclusive", "reasons": [...], "control": {...}, "candidate": {...}}` where each arm is the dict returned by `summarize_arm` (below): `inconclusive` when the control's total stuck turns are below `min_control_stuck_turns` (the replay shows no problem to fix, so it cannot show a fix) or when either arm has zero completed replicates; otherwise `reject` when ANY of: candidate stuck rate (stuck turns divided by turns played) is above `max_stuck_ratio` times the control's stuck rate; candidate rejected-turn count above the control's; candidate game-break count above the control's; candidate earned-exit rate (replicates that left the scene by an earned transition divided by completed replicates) below the control's; otherwise `keep`. Every reason is one plain sentence with the two numbers.

BUILD 3, the station, new `factory/stations/probe.py`, story-agnostic (no story names, places, characters or facts in the module). Pieces:
(a) `runs_from_report(report: dict, scene: str) -> list[dict]` returns, for the scene, one dict per recorded replicate: `{"run": "<scene>-r<replicate>", "scene": scene, "inputs": [<every typed command of that run, in order, from raw_input>]}`; use the same helpers and the same validity rules as `live_playtest` (import them; do not copy). Runs with fewer than 2 inputs are dropped; the list is cut to `max_runs_per_probe // 2` runs (the first ones in report order) and each `inputs` to `max_turns_per_run`.
(b) `build_variation(*, name: str, package_path: str, scene: str, run: dict) -> dict` returns a bench variation dict (see bench/README.md): `story_package` the absolute package path, `runtime` true, `entry_state` `thorough` (offline seeding, free; the replay starts at the scene's entry exactly as a live run would), `item_facts` `{"mode": "single_call", "seed_from_package": true}`, `fixed_refusal` true, `engine_refusal` true, `fixed_turns` the number of inputs, `scripts` `{scene: [{"name": run["run"], "inputs": inputs}]}`. Copy the other switches from `bench/variations/probe-1a-control-laptop.json`, which is the known-good example of a replay variation (read it and the other `bench/variations/probe-1a-*.json` files; the hold arms there are story overlays, which you must NOT copy: the candidate differs only by `story_package`).
(c) `summarize_arm(turn_records_files: list[Path]) -> dict` reads bench `turn-records.json` files (shape above) and returns `{"replicates": n_completed, "turns": total played turns, "stuck_turns": n, "rejected_turns": n, "game_breaks": n, "earned_exits": n, "forced_exits": n}`. A turn is STUCK when it was not rejected and its `selected_knowledge_ids` is empty and it adds no `grounding_ids` entry that no earlier turn of that same run had (the bench turn record carries no fired-storylet list; this is the same idea as the live harness's stuck turn, applied identically to both arms, so it is a fair comparison even though it is not the live count; say so in the docstring). An earned exit is a run where a turn has `left_scene` true (read how the field is set in `bench/core.py` and what `scene_transitions` holds; classify a forced or timer transition as a forced exit and anything else as earned; if the record cannot tell them apart, treat `scene_transitions` with a cause field the way `live_playtest._turn_fails` treats `transition_cause`). A run with status other than `ok` or `completed` false does not count as a completed replicate, and a missing or malformed file raises `ValueError` with the path.
(c2) `projected_cost_usd(runs, replicates, rules) -> float`: arms (2) times runs times replicates times the sum of inputs per run, times `estimated_usd_per_turn`.
(d) The runner. `default_runner(root, argv, env, timeout_s)` is the ONLY place that calls `subprocess.run([<root>/.venv/bin/python, "-m", "bench", "run", ...])` (cwd `root`, never the ticket tree, so both arms use the same engine code), exactly like `live_playtest._default_runner`'s style; the handler takes `runner: Callable | None = None` so every test injects a stub that writes fake `turn-records.json` files and never starts a process. The bench `run` command needs `--variation FILE --scene S --replicates N --out DIR --confirm`; write each variation JSON under `<workspace>/<safe id>/probe/<arm>-<run>.json` and each `--out` under `<workspace>/<safe id>/probe/<arm>-<run>/`. The control arm's `story_package` is `<root>/data/stories/continuity-initiative` resolved from `payload.get("story_package")` or the same default `wiring._story_root` uses (import `_story_root` from `factory/stations/wiring.py`); the candidate arm's is the same relative path under the ticket tree from `ticket_tree(payload, ticket.id, root)`.
(e) The handler `probe_handler(root=None, *, runner=None, read_budget=None, rules=None) -> StationHandler`. Order of work, every step before the next: (1) fail with `missing payload key: runs` unless `payload` has `runs` (a list built by `runs_from_report`) or `report_path` (a string path to a live report JSON, read and converted with `runs_from_report(report, ticket.scene)`); fail with `no recorded runs to replay for scene <scene>` when none survive; (2) fail with `no ticket tree to probe` unless `ticket_tree(...)` finds a tree; (3) fail with `probe not approved: set billed_run_approved` unless `payload.get("billed_run_approved") is True` (the narrator is billed; no run starts without it), and fail with `a staged run is in progress` when the staged-run lock `live_playtest._staged_lock_path(root)` is fresh (reuse `_fresh_staged_lock`); (4) REUSE a saved result: `<workspace>/<safe id>/probe.json` holds `{input_hash, verdict...}` where `input_hash` is the sha256 of sorted-key JSON of the runs, the rules, the package hash of the tree's story package files (hash the bytes of every file under the candidate package directory, sorted by path) and a module constant `PROBE_VERSION`; a saved record with the same hash is returned with no run (the ticket was probed already; never bill twice); (5) the spend gate BEFORE any run: reuse `live_playtest._pre_run_budget_gate` (total budget, hourly rate, daily caps) with the projected cost, and when it returns a reason, raise the guard's existing limit-sleep exception the way station 7 does for a spent daily cap (read how `live_playtest_handler` turns the gate's reason into `LimitSleep` for the lane `cloudflare`, or a failed result, and copy that behaviour); also fail with `projected probe cost $x is above the remaining budget` when the projection exceeds what the caps allow; (6) read the Worker's day counter before and after the whole probe with `read_budget` (default: the same reader station 7 uses) and write ONE ledger row for lane `cloudflare`, station `probe`, with the difference, or an `unknown` row when unreadable, exactly as station 7 does; a failed reading never changes the verdict; (7) run each arm's runs: for each recorded run, control then candidate, one runner call each (`--replicates` from the rules), summarize with `summarize_arm`; a runner failure (non-zero exit, no output file) fails the station with the first 300 characters of stderr and writes NO saved result; a quota text in the output (the bench prints `AI_QUOTA_EXCEEDED` or `QUOTA`; read how station 7's `_raise_quota` detects it) raises `LimitSleep` for `cloudflare` to the next 00:00 UTC; (8) `judge_probe`, save `probe.json`, and return `StationResult(passed=(verdict == "keep"), "probe", <one line: verdict, control and candidate stuck turns over turns played, rejected, exits>, tokens=0, payload_updates={"probe": {"verdict", "reasons", "control", "candidate", "feedback": <a short plain-words block of ONLY the numbers and the verdict, never narration or player text>}})`. Never mutate `ticket.payload`.
Also a small CLI: `python -m factory.stations.probe judge CONTROL_DIR_OR_FILES... --candidate FILES...` is NOT needed; skip any CLI.
(f) `factory/stations/__init__.py`: register `Station.PROBE: probe_handler(root)` in `build_handlers`, keeping the key enumeration for older callers stable the same way as the other late stations.
(g) `factory/config/allowlist.json`: NO change (this station calls no model).

TESTS (hermetic; stubs only; no process, no network, no bench run). New `tests/test_factory_probe.py` and a small fixture `tests/fixtures/factory/probe_turn_records.json` (a trimmed real-shaped bench turn-records file with 2 runs of 4 turns each, one run with a stuck turn, written by hand to the real shape; no narration text copied from the story). Cover: `runs_from_report` on a synthetic live report (a run's inputs in order, short runs dropped, caps applied) and on `tests/fixtures/factory/stuck_packets_1a.json`-style data only if it is a report (it is not; use a synthetic report); `build_variation` fields and that it passes `bench describe` for the real story (call `.venv/bin/python -m bench describe --variation <tmp file> --json` through subprocess in ONE test; it is free; or load it with the bench's own variation loader in-process if that is faster) and that control and candidate variations differ only in `story_package` and `name`; `summarize_arm` counts (stuck rule, rejected, game breaks, earned versus forced exits, an incomplete run not counted, a malformed file raising `ValueError`); `judge_probe` for every branch (keep; reject on each of the four reasons separately; inconclusive on control with no stuck turns and on zero replicates; ratio boundary exactly at `max_stuck_ratio` keeps); the handler: every fail message above exactly; approval is required and the runner is never called without it; the staged-run lock blocks; the spend gate runs before the runner and a spent cap raises the limit-sleep exception with the runner never called; a saved `probe.json` with the same input hash returns with no runner call and a changed run or changed candidate package file recomputes; one `cloudflare` ledger row with station `probe` is written (temporary copies of the config and ledger, never the real ones) with the counter difference, and an `unknown` row when the reader returns None; a runner failure fails and saves nothing; a quota text raises the sleep; a full passing path with a stub runner writes both arms' variations and returns `payload_updates.probe.feedback` without any player text; the handler never mutates the payload; the module holds no story-specific word. The real `factory/config/probe_rules.json` loads and has exactly the six keys. Update any existing factory test the new enum member legitimately changes (minimally). Add the new test file to `tests/shard_durations.json` with `.venv/bin/python scripts/regen_shard_durations.py --missing-only` (read its usage; keep that diff to the one new entry). The new test file runs in under 15 seconds.

HARD LIMITS. Edit only the owned files: @OWNED@. Never edit `factory/line.py`, `factory/followups.py`, `factory/stations/wiring.py`, `live_playtest.py`, `planner.py`, `fix_plan.py`, `triage.py`, `deliver.py`, `fun_review.py`, `diagnose.py`, other config files, story data, `bench/` or `storygame/`. If you need a helper from `live_playtest.py` that is private, import it (a private import is fine); do not edit that file. Write NOTES_19A.txt (worktree root, never committed) listing every ambiguity and your choice."""

CHECK = """set -eo pipefail
WORK=@WORK@
mkdir -p "$WORK/out"
export PYTHONPATH=$PWD:$PWD/packages/worldkeeper/src TMPDIR=/tmp
[ -e .venv ] || ln -s @REPO@/.venv .venv
test -f factory/stations/probe.py || { echo "factory/stations/probe.py missing"; exit 1; }
git add -A -- factory tests
bad=$(git diff --cached --name-only | grep -vE '@ALLOW_RE@' || true)
[ -z "$bad" ] || { echo "files outside ownership staged: $bad"; exit 1; }
others=$(git diff --cached --name-only | grep '^factory/config/' | grep -vx 'factory/config/probe_rules.json' || true)
[ -z "$others" ] || { echo "config files touched other than probe_rules.json: $others"; exit 1; }
if grep -n -i -E "michelle|kristin|drawer|memory_card|laptop|continuity.initiative|reyes|walt|warehouse" factory/stations/probe.py; then echo "story-specific word in probe.py"; exit 1; fi
grep -q "PROBE" factory/tickets.py || { echo "PROBE missing from the Station enum"; exit 1; }
git diff --cached --name-only | grep -q 'factory/line.py' && { echo "line.py touched"; exit 1; } || true
.venv/bin/python - <<'PY'
import json, sys
rules = json.load(open("factory/config/probe_rules.json"))
want = {"replicates", "max_stuck_ratio", "min_control_stuck_turns", "estimated_usd_per_turn", "max_runs_per_probe", "max_turns_per_run"}
print("probe rules:", rules)
sys.exit(0 if set(rules) == want else 1)
PY
# the runner must be the only place that starts a process
n=$(grep -c "subprocess" factory/stations/probe.py || true)
echo "subprocess mentions in probe.py: $n"
[ "$n" -ge 1 ] || { echo "no real runner found"; exit 1; }
start=$(date +%s)
.venv/bin/python -m pytest -q -p no:cacheprovider -n 0 tests/test_factory_probe.py
took=$(( $(date +%s) - start ))
echo "probe tests took $took s (budget 15 s)"
[ "$took" -le 15 ] || { echo "over the 15 s budget"; exit 1; }
start=$(date +%s)
.venv/bin/python -m pytest -q -p no:cacheprovider -n 8 tests/test_factory_line.py tests/test_factory_stations.py tests/test_factory_tickets.py tests/test_factory_guard.py tests/test_factory_preflight.py tests/test_factory_frozen.py tests/test_factory_triage.py tests/test_factory_followups.py tests/test_factory_fun_review.py tests/test_factory_deliver.py tests/test_factory_wiring.py tests/test_factory_planner.py tests/test_factory_fix_plan.py tests/test_factory_diagnose.py
took=$(( $(date +%s) - start ))
echo "factory tests took $took s (budget 150 s)"
[ "$took" -le 150 ] || { echo "over the 150 s budget"; exit 1; }
.venv/bin/python -m ruff check factory tests/test_factory_probe.py
.venv/bin/python -m ruff format --check factory tests/test_factory_probe.py
[ ! -e factory/state/ledger.jsonl ] || { echo "a test wrote factory/state/ledger.jsonl"; exit 1; }
git diff --cached > "$WORK/out/probe.patch"
test -s "$WORK/out/probe.patch"
"""


def build() -> dict:
    def fill(text: str) -> str:
        return (
            text.replace("@REPO@", REPO)
            .replace("@WORK@", WORK)
            .replace("@OWNED@", ", ".join(OWNED))
            .replace("@ALLOW_RE@", ALLOW_RE)
        )

    return {
        "run_name": "factory-probe",
        "workdir": WORK,
        "max_parallel": 1,
        "worktrees": True,
        "repo": REPO,
        "tasks": [
            {
                "key": "probe",
                "task_type": "code-feature",
                "engine": "codex",
                "engine_args": ["-c", "model_reasoning_effort=high"],
                "max_attempts": 2,
                "timeout_s": 3600,
                "check_timeout_s": 900,
                "ownership": OWNED,
                "spec": fill(SPEC),
                "check": fill(CHECK),
                "expect_files": [],
                "verified": "Station 12 replays the recorded typed commands of the failing runs through the bench on the unchanged story and on the ticket tree, applies a keep rule fixed in data (fewer stuck turns, no new rejections or game breaks, no earned exit lost), refuses to start without approval, a free budget and no staged run, writes one cloudflare ledger row, and reuses its saved verdict; tests use stubs only and start no process.",
            }
        ],
    }


if __name__ == "__main__":
    out = Path(__file__).with_name("round19a-probe-manifest.json")
    out.write_text(json.dumps(build(), indent=2) + "\n")
    print(out)
