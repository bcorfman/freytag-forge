# ruff: noqa: E501  (spec strings are prose briefs for a worker)
"""Round 12: the carry-matrix gate as an exit search (the last free check of station 5).

For every entry state of every scene, search for an earned exit; from the default entry, also
check every single-step deviation from the found path. Each search stops at its first earned
exit and reuses points already proved. One Codex task. Usage: build_round12_manifest.py
"""

from __future__ import annotations

import json
from pathlib import Path

REPO = "/home/bcorfman/dev/freytag-forge"
WORK = "/home/bcorfman/dev/ringer-work/factory-carry-matrix"
PRIOR = f"{WORK}/attempt4"
MAP_PROBE = f"{WORK}/attempt3/map_size_probe.py"

OWNED = [
    "factory/checks/carry_matrix.py",
    "factory/stations/free_gates.py",
    "tests/test_factory_carry_matrix.py",
    "tests/test_factory_stations.py",
    ".github/workflows/carry-matrix-nightly.yml",
]

GATE_SECONDS = 240
QUICK_TEST_SECONDS = 20

SPEC = f"""You are a Python engineer. Your current working directory IS a git worktree of {REPO} (detached at HEAD). Edit files here directly. NEVER git commit, never touch {REPO} itself, never run `uv`, never call a model or the network. FIRST run: [ -e .venv ] || ln -s {REPO}/.venv .venv . Ruff: `.venv/bin/python -m ruff check <files>` and `.venv/bin/python -m ruff format <files>` (line length 120, double quotes, Python 3.12). Never pass --cov to pytest. Run tests as `PYTHONPATH=$PWD:$PWD/packages/worldkeeper/src TMPDIR=/tmp .venv/bin/python -m pytest -q -p no:cacheprovider -n 0 <test files>`.

GOAL. Station 5 of the factory (`factory/stations/free_gates.py`) must prove, for free and FAST, that no scene can leave the player stuck: a stuck point is a state inside a scene from which no sequence of player actions reaches an earned exit. Earlier designs were rejected by the owner as far too slow because they replayed the same turns many times (22 scripted runs of 1A that are identical until the one turn they differ) or tried to build every state of a scene (1A did not converge after 4600 states). This design SEARCHES instead: every search stops at its first earned exit, and a point already proved to reach an earned exit is never searched again. HARD TIME BUDGETS, enforced by the check: the whole-story gate (mode `one_branch`) must finish in under {GATE_SECONDS} seconds of wall time on this 16-core machine, and the new default-suite tests (everything not marked nightly in `tests/test_factory_carry_matrix.py` plus `tests/test_factory_stations.py`) must finish in under {QUICK_TEST_SECONDS} seconds in total. Measured costs (from a profile, {WORK}/profile-rollout/report.md): one game turn costs 105 to 150 ms (the first turn of 1A about 440 ms); `state.snapshot()` and `state.restore_snapshot()` cost 0.03 ms; `RuntimeState.bootstrap` and `RuntimeEngine(...)` about 3 ms. So turns are the only real cost: count them, and never play a turn twice from the same point.

HOW THE GAME IS PLAYED OFFLINE (copy these mechanics; see `tests/journey_prefix.py` and `storygame/personas.py`). Load a story with `storygame.story_package.loader.load_story_package`, then `_legacy_package` from `storygame.personas`; `state = RuntimeState.bootstrap(played)`; `provider = _ScriptedProvider(played, state)`; `engine = RuntimeEngine(state, provider)`. One turn: `engine._activate_pacing()`; `offered = engine.projector.project(state, "player", "").candidates`; to PICK candidate c set `provider.selected = (c.id,)`, to WAIT set `provider.selected = ()`; then `engine.turn(PERSONAS["thorough"])`. A `ProposalValidationError` or `RuntimeContractError` means that pick was rejected: the step does not exist (restore the snapshot and move on). After the turn, `state.current_scene_id` tells whether the scene changed and `engine.last_attempt.transition_cause` is `"earned"`, `"forced"` or `"timer"`; in the last scene `_resolution_complete(state)` with no forced or timer transition is the earned exit. Restore with `state.restore_snapshot(snap)` into the same engine and provider, and restore `provider.handoff_ids` too, as `tests/journey_prefix.py` does. `_select_thorough(played, state, offered)` names the strongest lead.

DEFINITIONS.
- A STEP from a point is: pick one offered candidate (each one), or wait. Order steps: the `_select_thorough` pick first, then the other offered candidates in projector order, then wait.
- SEARCH(point): depth-first over steps, turn limit `handoff_after_turns + 3` turns in the scene. Success at the first earned exit. A forced or timer exit, or the turn limit, ends that branch as a failure; keep searching other steps. Per-search budget: a number of new points (parameter `search_budget`; its default is set by measurement, see FAILURE SPEED). Result: `earned` (with the path and the exit snapshot), `no_path` (search finished, nothing earned), or `budget` (budget spent, nothing earned).
- MEMO, shared by every search in one scene within one process: points proved good (some step sequence from them reached an earned exit; mark every point on a successful path) and points proved bad (`no_path` under a complete search). A search that reaches a good point succeeds at once and reuses the exit found from it; one that reaches a bad point treats it as a failed branch. Memo key, the POINT IDENTITY: turns spent in the scene (`turn_index - scene_entered_at_turn`); the asserted facts restricted to forward-read true flags and the world-state predicates (exactly the `state_key` rule below); `active_event_ids`; `fired_event_ids`; `cue_stages` with turns made relative to scene entry; `staged_cue_fact_id`; `staged_cue_stage`; `staged_handoff_fact_ids`; `delivered_cue_ids`; and from `turn_records` of the current scene visit only: the LAST TWO records in order as `(id, reveal_ids, deadline_event_ids, transition_id)`, plus the SORTED SET of the reveal ids and deadline ids of the earlier ones. A previous probe that used the full ordered list of records never merged two orders of the same picks; read its identity code and comments at {MAP_PROBE} (`_identity_key`, `_relevant_turn_records`) and confirm from `storygame/runtime/` which record fields later turns read. Write the evidence for each field kept or dropped, with file:line, in NOTES_12.txt.
- `state_key` (merging scene ENTRY states, as before): the sorted `Fact.key` tuples of (i) asserted true flag facts (value, else object, equal to "true") whose predicate is in `forward_reads(package, T)`, and (ii) every asserted fact whose predicate is in `WORLD_STATE_PREDICATES = ("wk_parent", "wk_relation", "wk_place_text", "wk_hidden", "world_effects_applied")`. `read_fact_ids`, `reads_by_scene` and `forward_reads` keep the definitions already written in {PRIOR}/carry_matrix.py (a generic walk of the model tree; transition triggers belong to the scene they leave; reads with no scene count for every scene). Compute `forward_reads` once per scene.
- MAIN PATH of an entry state: SEARCH from it. A failure is a stuck cell `main`.
- DEVIATIONS of an entry state: for every point p_i on its main path, every step from p_i other than the one the main path took. Apply the step (one turn). If that turn exits the scene: earned is fine (the deviation's exit), forced or timer is a stuck cell. Otherwise SEARCH from the new point; a failure is a stuck cell. Label a deviation `t<i>:<candidate id or wait>`, where i is the turn in the scene.

MODES (`carry_matrix(package, *, scenes=None, mode="one_branch", search_budget=None, max_states_per_scene=None, workers=None) -> CarryReport`; the cap defaults to 200 for one_branch and 2000 for pairwise; scenes are walked in story order from `RuntimeState.bootstrap`, earlier scenes are walked even when `scenes` names later ones, and scenes after the last named one are not run).
- `one_branch` (station 5, every change). Each scene's entry states carry a choice list: `()` for the DEFAULT entry (reached by main paths only). From the default entry run the main path AND all deviations; each deviation's earned exit is a new ONE-CHOICE entry state of the next scene (choice `<scene>/<label>`). From a one-choice entry run the main path only; its exit carries forward as the same branch. Merge entry states by `state_key` (keep the first snapshot and the shortest choice list; count merged branches). More than the cap raises `CarryMatrixTooLarge(scene, count)`; never truncate silently.
- `pairwise` (nightly). As one_branch, plus all deviations from one-choice entries too; their earned exits become two-choice entries, which run the main path only.

PARALLELISM. Entry states of one scene are independent: search them in a `fork` process pool that is created ONCE for the whole run and kept alive (`workers` default `min(16, os.cpu_count())`); the memo is per process, so give each worker a batch of entries, or the main path and a share of the deviations of one entry. Send snapshots, not packages; the package is inherited through fork. When there is only one entry state (1A), split its deviations across workers.

REPORT. `CarryReport` (dataclass): `mode`, `entry_states: dict[str, int]`, `branches: dict[str, int]`, `searches: int`, `turns: int` (game turns actually played), `memo_hits: int`, `stuck: list[StuckCell]`, `seconds: float`, `seconds_by_scene: dict[str, float]`. `StuckCell`: scene, entry index, the entry's choice list, label (`main` or the deviation label), reason (`no_path`, `budget`, `forced`, `timer`), turns in the scene where it was found, and the entry's true forward-read flags, sorted. `CarryReport.lines()` gives one line per stuck cell: `STUCK <scene> entry#<i> after <choices joined by ' + ', or 'default path'> <label> <reason> at turn <t>; carried: <facts, comma separated>`.

CLI: `python -m factory.checks.carry_matrix [--story PATH] [--scene S ...] [--mode one_branch|pairwise] [--search-budget N] [--workers N] [--json OUT]`. It loads PATH (default `data/stories/continuity-initiative`), prints a line per scene (`<scene>: <n> entry states, <searches> searches, <turns> turns, <s> stuck, <x>s`), every stuck line, then `TOTAL entry_states=<n> searches=<n> turns=<n> memo_hits=<n> stuck=<n> seconds=<x>`; `--json` writes every CarryReport field. Exit 0 when nothing is stuck, 1 when something is, 2 on `CarryMatrixTooLarge` or a load error (print the reason). Expose `main(argv=None) -> int`.

free_gates.py: keep what {PRIOR}/free_gates.py does (module-level `from storygame.story_package.loader import load_story_package`, called by that name; carry matrix after the gap gate and before Ruff unless `"carry_matrix": false`; `carry_scenes` payload key; station 5 always uses `one_branch`; stuck lines through the existing 4000-character tail; `CarryMatrixTooLarge` or a load error is a plain failure, never a raise).

TESTS. Unit tests run on a SMALL story, never the full nine scenes. First try `tests/fixtures/story_source/mini_ok` (two scenes): copy it with `copy_fixture` from `tests/story_source/helpers.py`, compile it with `storygame.story_source.compile_source_tree`, and check it can be played with the mechanics above. If it cannot be played, build the smallest playable package another way (for example the real package restricted with `model_copy` to 1A and one exit), say how in a comment, and keep the time budget. Required tests: the point identity merges two orders of the same two picks and separates a different pick, and `state_key` drops an unread flag but keeps a `wk_parent` fact; a seeded defect (rewrite the triggers of the transition leaving a scene to need a fact nothing produces) is reported `main` stuck with reason `no_path` or `budget`; a seeded trap reached by one deviation only (for example an offered candidate whose effect makes the exit impossible) is reported with that deviation's label while `main` passes; the memo: a second search that reaches a proved point plays no new turns (count turns); `CarryMatrixTooLarge` with `max_states_per_scene=1`; `one_branch` entry states have choice lists of length 0 or 1 and `pairwise` has some of length 2 (this needs at least three scenes; if the fixture has two, mark only this test nightly and say so); the CLI exit codes 0 and 1 and the JSON keys; the free-gates stub test from {PRIOR}/test_factory_stations.py (keep `"carry_matrix": false` in the other free-gates tests). One nightly test (`@pytest.mark.nightly`) runs the whole real story in `one_branch` and asserts every scene has at least one entry state; it does not assert zero stuck. Delete the prior attempt's slow real-story tests; do not carry them over.

NIGHTLY WORKFLOW. Keep {PRIOR}/carry-matrix-nightly.yml as `.github/workflows/carry-matrix-nightly.yml` (schedule `47 7 * * *` plus `workflow_dispatch`, `timeout-minutes: 330`, `--mode pairwise --json carry-matrix-pairwise.json`, artifact upload with `if: always()`); check its uv steps against `.github/workflows/coverage-nightly.yml`. Touch no other workflow.

HEAD START. {PRIOR}/ holds the previous attempt of THIS design: `carry_matrix.py`, `free_gates.py`, `test_factory_carry_matrix.py`, `test_factory_stations.py`, `carry-matrix-nightly.yml` and its `NOTES_12.txt`. FIRST copy the five files into their places in this worktree (`cp {PRIOR}/carry_matrix.py factory/checks/`, `cp {PRIOR}/free_gates.py factory/stations/`, the two tests into `tests/`, the workflow into `.github/workflows/`) and NOTES_12.txt to the worktree root; then change only what this brief asks beyond it. That attempt already passes on the real story: 139 s for the whole story, 0 stuck, quick tests 13.5 s. It failed on a BROKEN story: with the transition out of 3A rewritten to need a fact nothing produces, every one of the 13 entry states of 3A spent its whole 300-point budget, and finding that took 524 s ({PRIOR}/seeded_3a_timing.out), then station 5 ran it all again. Healthy searches find an exit in about 7 turns, so the budget was far larger than any real exit needs.

MEASURE AND REPORT. Run the CLI on the whole real story with `--json {WORK}/carry-matrix.json` under `/usr/bin/time -p`, and the quick tests with `--durations=10`. If the gate exceeds {GATE_SECONDS} s or the tests exceed {QUICK_TEST_SECONDS} s, find where the turns go (searches, memo hit rate, budget exhaustion) and fix that before finishing; do not raise the budgets and do not drop deviations. Write NOTES_12.txt (worktree root, never committed): the full CLI output and wall time; the quick-test durations; the point-identity evidence; every rule you found ambiguous and the choice you made; and for each stuck cell one sentence on why the story gives no earned exit there (read the transitions and storylet activations involved). Do not change the story or the engine to make a cell pass.

FAILURE SPEED. The gate must be as fast on a broken story as on a good one: a story with a stuck scene must also finish in under {GATE_SECONDS} s. Make these changes:
1. Measure the budget a real exit needs. Count, for every search that ends `earned`, the new points it used; add `max_search_points: int` (the largest such count in the run) and `search_budget: int` (the budget used) to `CarryReport`, the JSON and the TOTAL line (`... search_budget=<n> max_search_points=<n> ...`). Run the whole real story with a large budget to measure it, then set the default `search_budget` to three times the measured largest count, at least 30, as a named module constant with a comment giving the measurement and date. `--search-budget` still overrides it.
2. Stop at the first stuck scene in `one_branch`: the scene with stuck cells finishes (all its entry states and deviations, so every stuck cell of that scene is reported), and the later scenes are not run. Add `not_run: list[str]` to `CarryReport` and the JSON, and print `NOT RUN <scenes, space separated> (stopped after stuck <scene>)` after the stuck lines in the CLI output and in `lines()`. `pairwise` keeps running the later scenes from the entries that did exit.
3. Station 5's failure output contains `CarryReport.lines()` (the stuck lines and the NOT RUN line); if it is longer than the existing 4000-character tail, keep the first stuck line and the NOT RUN line.
4. Time the seeded-defect case yourself: the real story with 3A's exit triggers rewritten (as above), all nine scenes, through station 5. Put its wall time in NOTES_12.txt. If it exceeds {GATE_SECONDS} s, find where the turns go and fix it.
Add a quick test that the default budget stops a seeded stuck search after at most `search_budget` new points, and that a stuck scene leaves the later scenes in `not_run`.

HARD LIMITS. Edit only the five files above. Never edit `storygame/`, `packages/`, `data/`, `bench/`, `factory/config/`, other factory modules, other tests or other workflows. Do not add dependencies.
"""

CHECK = f"""set -eo pipefail
WORK={WORK}
mkdir -p "$WORK"
export PYTHONPATH=$PWD:$PWD/packages/worldkeeper/src TMPDIR=/tmp
[ -e .venv ] || ln -s {REPO}/.venv .venv
git add -A -- factory tests .github
bad=$(git diff --cached --name-only | grep -vxF -e factory/checks/carry_matrix.py -e factory/stations/free_gates.py -e tests/test_factory_carry_matrix.py -e tests/test_factory_stations.py -e .github/workflows/carry-matrix-nightly.yml || true)
[ -z "$bad" ] || {{ echo "files outside ownership staged: $bad"; exit 1; }}
for f in factory/checks/carry_matrix.py tests/test_factory_carry_matrix.py .github/workflows/carry-matrix-nightly.yml NOTES_12.txt; do [ -s "$f" ] || {{ echo "missing $f"; exit 1; }}; done
.venv/bin/python -m ruff check factory/checks/carry_matrix.py factory/stations tests/test_factory_carry_matrix.py tests/test_factory_stations.py
.venv/bin/python -m ruff format --check factory/checks/carry_matrix.py factory/stations tests/test_factory_carry_matrix.py tests/test_factory_stations.py
# quick tests: must pass and fit the time budget
start=$(date +%s.%N)
.venv/bin/python -m pytest -q -p no:cacheprovider -n 0 -m "not nightly" tests/test_factory_carry_matrix.py tests/test_factory_stations.py
quick=$(echo "$(date +%s.%N) - $start" | bc)
echo "quick tests: ${{quick}}s (budget {QUICK_TEST_SECONDS}s)"
awk -v t="$quick" 'BEGIN {{ exit !(t < {QUICK_TEST_SECONDS}) }}' || {{ echo "quick tests took ${{quick}}s, over the {QUICK_TEST_SECONDS}s budget"; exit 1; }}
.venv/bin/python -m pytest -q -p no:cacheprovider -n 0 tests/test_factory_line.py tests/test_factory_frozen.py
.venv/bin/python - <<'PY'
import yaml
w = yaml.safe_load(open(".github/workflows/carry-matrix-nightly.yml"))
on = w.get("on", w.get(True))
assert "schedule" in on and "workflow_dispatch" in on, on
jobs = list(w["jobs"].values())
assert len(jobs) == 1 and jobs[0]["timeout-minutes"] == 330, jobs
runs = " ".join(str(step.get("run", "")) for step in jobs[0]["steps"])
assert "factory.checks.carry_matrix" in runs and "--mode pairwise" in runs, runs
assert any("upload-artifact" in str(step.get("uses", "")) for step in jobs[0]["steps"]), "no artifact upload"
print("workflow ok")
PY
# independent probe 1: the whole real story, inside the gate's time budget
out="$WORK/probe.out"
rc=0
start=$(date +%s.%N)
timeout {GATE_SECONDS + 60} .venv/bin/python -m factory.checks.carry_matrix --json "$WORK/probe.json" > "$out" 2>&1 || rc=$?
gate=$(echo "$(date +%s.%N) - $start" | bc)
cat "$out"
echo "whole-story gate: ${{gate}}s (budget {GATE_SECONDS}s), exit $rc"
[ "$rc" = 0 ] || [ "$rc" = 1 ] || {{ echo "whole-story CLI exited $rc"; exit 1; }}
awk -v t="$gate" 'BEGIN {{ exit !(t < {GATE_SECONDS}) }}' || {{ echo "whole-story gate took ${{gate}}s, over the {GATE_SECONDS}s budget"; exit 1; }}
.venv/bin/python - "$WORK/probe.json" "$rc" <<'PY'
import json, sys
data = json.load(open(sys.argv[1]))
scenes = ["1A", "1B", "1C", "2A", "2B", "2C", "3A", "3B", "3C"]
missing = [s for s in scenes if data["entry_states"].get(s, 0) < 1]
assert not missing, f"scenes with no entry state: {{missing}}"
assert data["mode"] == "one_branch", data.get("mode")
assert max(data["entry_states"].values()) <= 200, data["entry_states"]
assert data["searches"] >= 9 and data["turns"] > 0, (data["searches"], data["turns"])
assert data["entry_states"]["1B"] > 1, "no deviation from 1A reached 1B: deviations are not being carried forward"
assert (sys.argv[2] == "1") == bool(data["stuck"]), "exit code disagrees with stuck list"
assert 30 <= data["search_budget"] < 300, ("default search budget not measured down", data.get("search_budget"))
assert 0 < data["max_search_points"] <= data["search_budget"], (data.get("max_search_points"), data.get("search_budget"))
assert data["stuck"] or data["not_run"] == [], data.get("not_run")
print("whole story ok:", data["entry_states"], "searches", data["searches"], "turns", data["turns"], "memo_hits", data["memo_hits"], "stuck", len(data["stuck"]))
PY
# independent probe 2: a seeded 3A defect, all nine scenes through station 5, fast and stopped after 3A
start=$(date +%s.%N)
timeout 300 .venv/bin/python - <<'PY'
import re, tempfile
from datetime import UTC, datetime
from pathlib import Path
import factory.stations.free_gates as fg
from factory.checks.gap_delta import DEFAULT_ROOT, all_anchors, save_baseline, snapshot
from factory.stations import build_handlers
from factory.tickets import Station, Ticket
from storygame.story_package.loader import load_story_package

real = load_story_package(Path("data/stories/continuity-initiative"))
pacing = real.pacing
bad = [t.model_copy(update={{"triggers": tuple(p.model_copy(update={{"fact_id": "probe_never_true_fact"}}) for p in t.triggers)}}) if t.source_scene_id == "3A" else t for t in pacing.transitions]
seeded = real.model_copy(update={{"pacing": pacing.model_copy(update={{"transitions": tuple(bad)}})}})
anchor = all_anchors(DEFAULT_ROOT)[0]
base = Path(tempfile.mkdtemp()) / "gaps.json"
save_baseline(snapshot(DEFAULT_ROOT, [anchor]), base)
fg.load_story_package = lambda root: seeded
now = datetime(2026, 1, 1, tzinfo=UTC).isoformat()
ticket = Ticket(id="t", scene="3A", station=Station.FREE_GATES, token_budget=1, created_at=now, updated_at=now,
                payload={{"gap_baseline": str(base), "anchors": [anchor], "carry_scenes": ["1A", "1B", "1C", "2A", "2B", "2C", "3A", "3B", "3C"]}})
r = build_handlers(Path.cwd())[Station.FREE_GATES](ticket, datetime.now(UTC))
print(r.check)
print(r.output[-1500:])
assert not r.passed and r.check == "carry_matrix", (r.passed, r.check)
assert re.search(r"STUCK 3A entry#\\d+ .* main ", r.output), "station output has no STUCK 3A ... main line"
assert not re.search(r"STUCK 3[BC] ", r.output), "3B or 3C was searched after 3A was stuck"
m = re.search(r"NOT RUN ([^(]*)\\(stopped after stuck 3A\\)", r.output)
assert m and m.group(1).split() == ["3B", "3C"], "no 'NOT RUN 3B 3C (stopped after stuck 3A)' line"
print("seeded probe ok")
PY
seeded=$(echo "$(date +%s.%N) - $start" | bc)
echo "seeded-defect gate: ${{seeded}}s (budget {GATE_SECONDS}s)"
awk -v t="$seeded" 'BEGIN {{ exit !(t < {GATE_SECONDS}) }}' || {{ echo "seeded-defect gate took ${{seeded}}s, over the {GATE_SECONDS}s budget"; exit 1; }}
git diff --cached > {WORK}/carry-matrix.patch
cp NOTES_12.txt {WORK}/NOTES_12.txt
test -s {WORK}/carry-matrix.patch
"""


def build() -> dict:
    return {
        "run_name": "factory-carry-matrix",
        "workdir": WORK,
        "max_parallel": 1,
        "worktrees": True,
        "repo": REPO,
        "tasks": [
            {
                "key": "carry-matrix",
                "task_type": "code-feature",
                "engine": "codex",
                "engine_args": ["-c", "model_reasoning_effort=high"],
                "max_attempts": 2,
                "timeout_s": 5400,
                "check_timeout_s": 1200,
                "ownership": OWNED,
                "spec": SPEC,
                "check": CHECK,
                "expect_files": [],
                "verified": f"Quick tests green in under {QUICK_TEST_SECONDS}s; ruff clean; whole real story gate under {GATE_SECONDS}s with an entry state per scene, deviations carried into 1B, and an exit code matching its stuck list; a seeded 3A defect fails station 5 in under {GATE_SECONDS}s with 3A main stuck and 3B and 3C not run; the search budget is measured below 300; nightly pairwise workflow valid; only five files changed.",
            }
        ],
    }


if __name__ == "__main__":
    out = Path(__file__).with_name("round12-manifest.json")
    out.write_text(json.dumps(build(), indent=2) + "\n", encoding="utf-8")
    print(out)
