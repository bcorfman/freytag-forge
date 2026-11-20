# ruff: noqa: E501  (spec strings are prose briefs for a worker)
"""Round 12 attempt 6: the carry-matrix exit search made correct AND fast.

Attempt 5 (on main since PR #792) bought speed by reporting a spent search budget as stuck and by
stopping after the first stuck scene. Attempt 6 adds a static exit check, three outcomes
(earned / stuck / undecided, with undecided searched again unbounded), and no early stop.
One Codex task. Usage: build_round12_attempt6_manifest.py
"""

from __future__ import annotations

import json
from pathlib import Path

REPO = "/home/bcorfman/dev/freytag-forge"
WORK = "/home/bcorfman/dev/ringer-work/factory-carry-matrix"
OUT = f"{WORK}/attempt6-out"

OWNED = [
    "factory/checks/carry_matrix.py",
    "factory/stations/free_gates.py",
    "tests/test_factory_carry_matrix.py",
    "tests/test_factory_stations.py",
]

GATE_SECONDS = 240
QUICK_TEST_SECONDS = 20
REQUIRED_TESTS = [
    "test_static_check_proves_seeded_exit_defect_without_turns",
    "test_static_check_says_maybe_when_a_producer_can_fire",
    "test_seeded_deviation_trap_is_stuck_not_undecided",
    "test_exit_longer_than_budget_is_undecided_then_earned",
    "test_stuck_scene_makes_later_scenes_unreachable",
]

SPEC = f"""You are a Python engineer. Your current working directory IS a git worktree of {REPO} (detached at HEAD). Edit files here directly. NEVER git commit, never touch {REPO} itself, never run `uv`, never call a model or the network. FIRST run: [ -e .venv ] || ln -s {REPO}/.venv .venv . Ruff: `.venv/bin/python -m ruff check <files>` and `.venv/bin/python -m ruff format <files>` (line length 120, double quotes, Python 3.12). Never pass --cov to pytest. Run tests as `PYTHONPATH=$PWD:$PWD/packages/worldkeeper/src TMPDIR=/tmp .venv/bin/python -m pytest -q -p no:cacheprovider -n 0 <test files>`.

YOU OWN exactly these files and may edit nothing else: factory/checks/carry_matrix.py, factory/stations/free_gates.py, tests/test_factory_carry_matrix.py, tests/test_factory_stations.py. Also write NOTES_12.txt at the worktree root (never committed). Never edit `storygame/`, `packages/`, `data/`, `bench/`, `factory/config/`, other factory modules, other tests or any workflow. Do not add dependencies.

BACKGROUND. `factory/checks/carry_matrix.py` (already in this worktree) is station 5's carry-matrix gate. For each scene it keeps the distinct entry states, and from each one runs an exit SEARCH: depth-first over player steps (pick one offered candidate, or wait), stopping at the first earned exit, with a per-scene memo of points proved good or bad. From the default entry it also searches every single-step deviation from the found path (mode `one_branch`). Read the whole module, its tests and `factory/stations/free_gates.py` before changing anything; the offline play mechanics, `state_key`, `forward_reads`, the point identity, the process pool and the nightly `pairwise` mode all stay as they are. Today on the real story it finds 69 entry states, 178 searches, 913 turns, 0 stuck, in 139 s.

The owner rejected it because it bought its speed by giving up correctness in two ways:
(a) A search that spends its budget (`DEFAULT_SEARCH_BUDGET = 39` new points) is reported as STUCK with reason `budget`. A story edit that makes a scene's shortest earned exit need more than 39 points of search is then a false failure.
(b) `one_branch` stops after the first stuck scene and lists the later scenes as `not_run`, which hides stuck cells in later scenes when only some entry states of a scene are stuck.
The owner's rule: tests must be correct AND fast. Never trade one for the other. Your job is to remove both faults while staying fast on a good story and on a broken one.

CHANGES.
1. STATIC EXIT CHECK, before any turn is played for an entry state. For the scene S and the entry state's snapshot, take each earned exit of S (the transitions whose `source_scene_id` is S; for the last scene, whatever `_resolution_complete` needs, if it can be read as fact predicates, otherwise skip the static check for the last scene and say so in NOTES_12.txt). Read in `storygame/runtime/` exactly how a transition's `triggers` are combined (all, any, or another rule) and how a predicate's `equals` is compared, and cite file:line in NOTES_12.txt. A trigger predicate is POSSIBLE when it already holds in the entry state, or when `producers(package, fact_id, value)` from `storygame/story_package/dependencies.py` returns a producer whose `scene_id` is S or None (None means it can fire in any scene). An exit is POSSIBLE when its triggers can be combined to hold under that rule using possible predicates only. If no earned exit of S is possible, every cell of that entry state is STUCK with reason `no_exit_possible`, proved with zero turns played. Otherwise the answer is MAYBE and the search runs as now. SOUNDNESS IS REQUIRED: the static check may only say stuck when no play can make the exit happen. Before trusting `producers()`, search `storygame/runtime/` (and the scripted provider in `storygame/personas.py`) for every way a fact can become asserted during offline play: pacing events, storylet realizations, deliveries, cue staging, world effects, the `wk_*` world predicates, scene entry facts, or anything else. List each path in NOTES_12.txt with file:line and say whether `producers()` covers it. For any fact a path can set that `producers()` does not cover (for example `wk_*` world facts or engine bookkeeping), the static check must treat a predicate on it as POSSIBLE. A predicate that needs a value to be false or absent, or any rule you cannot read with certainty, is POSSIBLE. Put the static check in its own function `static_exit_possible(package, state, scene) -> bool` (True means MAYBE) so it can be tested alone.
2. THREE OUTCOMES. A searched cell ends `earned`, `stuck` (reason `no_exit_possible`, `no_path` from a complete search, `forced` or `timer` from a deviation step that itself exits by force) or `undecided` (the budgeted search spent its budget). Set `DEFAULT_SEARCH_BUDGET = 300` with a comment citing the attempt 5 measurement (largest earned search used 13 new points, 2026-11-20). After the budgeted pass of a scene, search every undecided cell again with NO budget (the turn limit `handoff_after_turns + 3` per scene already makes the search finite), only those cells, reusing the scene's memo. Only the result of that unbounded search decides the cell: earned passes, a complete failure is `stuck` with reason `no_path`. The reason `budget` must no longer appear in any stuck cell. A `budget` result must never be recorded as a bad point in the memo. Add to `CarryReport` and the JSON: `undecided: int` (cells that needed the unbounded search), `static_stuck: int` (entry states proved stuck by the static check), and `max_unbounded_points: int` (the largest point count of an unbounded search, 0 if none). Add `undecided=<n> static_stuck=<n>` to the CLI TOTAL line. Keep `search_budget` and `max_search_points` in the report.
3. NO EARLY STOP. Remove the `one_branch` early stop and the `not_run` field, its JSON key, its line and every use of it. Later scenes run from every entry state that did exit. A scene left with no entry states because every way into it was stuck is reported in a new field `unreachable: dict[str, str]` (scene id to the earliest scene where its ways in were stuck) and as one line per scene in `lines()` and the CLI output, after the stuck lines: `UNREACHABLE <scene>: every way in is stuck in <stuck scene>`. An unreachable scene is a failure of the gate (CLI exit 1, station 5 fails) even though it has no stuck cell of its own. Scenes named after the last scene in `scenes` are still not run, as now, and are not unreachable.
4. STATION 5 OUTPUT (`free_gates.py`): the failure output holds `CarryReport.lines()`. If it is longer than the existing 4000-character tail, keep the first stuck line and every UNREACHABLE line. A report with only unreachable scenes also fails station 5 with check `carry_matrix`.
5. RELEVANCE PRUNING, ONLY IF NEEDED. If, after changes 1 to 3, the whole real story exceeds {GATE_SECONDS} s with `--search-budget 3` (which forces many unbounded re-searches), or a quick test exceeds its share of the budget, then and only then add relevance pruning: a step whose effects touch none of the facts the scene's exits depend on (taken transitively through the conditions of the storylets and events that produce them) counts as a wait, and the point identity keeps only relevant facts plus turn and pacing fields. It is sound only if the relevant set over-approximates, so justify it in NOTES_12.txt with file:line. If you do not need it, write "relevance pruning not needed" in NOTES_12.txt with the timings that show it.

TESTS, on the two-scene fixture story `mini_ok` (the existing `mini_package` fixture), never the full nine scenes, all in `tests/test_factory_carry_matrix.py`. Build every seeded story only by changing the package with `model_copy` (transitions, storylet realization operations, events). Do NOT monkeypatch the search, its results or `static_exit_possible` in these tests: they must exercise the real code. Required tests, with exactly these names:
- `{REQUIRED_TESTS[0]}`: 1A's exit triggers rewritten to need a fact nothing produces; the report has 1A `main` stuck with reason `no_exit_possible`, `static_stuck >= 1`, and the turns counted for 1A are 0.
- `{REQUIRED_TESTS[1]}`: the same exit rewritten to need a fact that some 1A storylet realization or event asserts (add that operation with `model_copy` if none exists); `static_exit_possible` returns True.
- `{REQUIRED_TESTS[2]}`: a trap reached by ONE deviation only (for example give one offered, non-default candidate's realization an operation that makes 1A's exit unreachable, such as retracting or changing a trigger fact that nothing re-asserts), with a budget large enough that the search completes. The cell is reported with that deviation's label and reason `no_path`, `main` is not stuck, and `undecided == 0`.
- `{REQUIRED_TESTS[3]}`: the healthy fixture with `search_budget=1` (or the smallest budget that makes some search undecided); `undecided >= 1`, nothing is stuck, and `max_unbounded_points >= 1`.
- `{REQUIRED_TESTS[4]}`: 1A's exit made impossible; the next scene of the fixture is in `unreachable` mapped to "1A", `lines()` contains its UNREACHABLE line, and the CLI or `carry_matrix` reports failure.
Update the existing tests to the new behaviour: replace the monkeypatched deviation-trap test with the real one above, delete `test_default_budget_bounds_seeded_stuck_search` or rewrite it for the undecided outcome, change any `budget` or `not_run` expectation, and update the CLI JSON-keys test and the free-gates stub test in `tests/test_factory_stations.py`. Delete tests that the new ones make redundant rather than keeping both. Keep the one nightly real-story test.

MEASURE AND REPORT in NOTES_12.txt: (i) the whole real story, `/usr/bin/time -p .venv/bin/python -m factory.checks.carry_matrix --json {OUT}/default.json`, full output and wall time; (ii) the same with `--search-budget 3 --json {OUT}/budget3.json`, full output and wall time; (iii) the seeded broken 3A (the real story with every trigger of each transition whose `source_scene_id` is "3A" rewritten to `FactPredicate(fact_id="probe_never_true_fact", equals=True)`), run through `carry_matrix(...)` for all nine scenes, with its wall time and `seconds_by_scene`; (iv) quick-test durations with `--durations=10`; (v) the fact-assertion paths and trigger rule with file:line (change 1); (vi) every rule you found ambiguous and the choice you made. Run `mkdir -p {OUT}` first. Budgets the check enforces: (i), (ii) and (iii) each under {GATE_SECONDS} s; quick tests (everything not marked nightly in the two test files) under {QUICK_TEST_SECONDS} s; the seeded 3A scene itself under 2 s in `seconds_by_scene`. If a budget is missed, find where the time goes and fix that; do not raise a budget, do not drop deviations, and do not reintroduce budget-as-stuck or an early stop. Do not change the story or the engine to make a cell pass.
"""

CHECK = f"""set -eo pipefail
OUT={OUT}
mkdir -p "$OUT"
export PYTHONPATH=$PWD:$PWD/packages/worldkeeper/src TMPDIR=/tmp
[ -e .venv ] || ln -s {REPO}/.venv .venv
git add -A -- factory tests .github storygame packages data bench
bad=$(git diff --cached --name-only | grep -vxF -e factory/checks/carry_matrix.py -e factory/stations/free_gates.py -e tests/test_factory_carry_matrix.py -e tests/test_factory_stations.py || true)
[ -z "$bad" ] || {{ echo "files outside ownership staged: $bad"; exit 1; }}
git diff --cached --quiet -- factory/checks/carry_matrix.py && {{ echo "carry_matrix.py unchanged"; exit 1; }}
[ -s NOTES_12.txt ] || {{ echo "missing NOTES_12.txt"; exit 1; }}
grep -qi "relevance pruning" NOTES_12.txt || {{ echo "NOTES_12.txt does not say whether relevance pruning was needed"; exit 1; }}
.venv/bin/python -m ruff check factory/checks/carry_matrix.py factory/stations tests/test_factory_carry_matrix.py tests/test_factory_stations.py
.venv/bin/python -m ruff format --check factory/checks/carry_matrix.py factory/stations tests/test_factory_carry_matrix.py tests/test_factory_stations.py
for t in {" ".join(REQUIRED_TESTS)}; do grep -q "def $t(" tests/test_factory_carry_matrix.py || {{ echo "missing required test $t"; exit 1; }}; done
.venv/bin/python - <<'PY'
import re
src = open("tests/test_factory_carry_matrix.py").read()
for name in {REQUIRED_TESTS!r}:
    body = re.search(rf"def {{name}}\\(.*?(?=\\ndef |\\n@|\\Z)", src, re.S).group(0)
    assert "monkeypatch" not in body, f"{{name}} monkeypatches; it must exercise the real search"
code = open("factory/checks/carry_matrix.py").read()
assert "not_run" not in code, "not_run is still in carry_matrix.py"
assert re.search(r"^DEFAULT_SEARCH_BUDGET = 300\\b", code, re.M), "DEFAULT_SEARCH_BUDGET is not 300"
assert "def static_exit_possible(" in code, "no static_exit_possible function"
print("source rules ok")
PY
# quick tests: must pass and fit the time budget
start=$(date +%s.%N)
.venv/bin/python -m pytest -q -p no:cacheprovider -n 0 -m "not nightly" tests/test_factory_carry_matrix.py tests/test_factory_stations.py
quick=$(echo "$(date +%s.%N) - $start" | bc)
echo "quick tests: ${{quick}}s (budget {QUICK_TEST_SECONDS}s)"
awk -v t="$quick" 'BEGIN {{ exit !(t < {QUICK_TEST_SECONDS}) }}' || {{ echo "quick tests took ${{quick}}s, over the {QUICK_TEST_SECONDS}s budget"; exit 1; }}
.venv/bin/python -m pytest -q -p no:cacheprovider -n 0 tests/test_factory_line.py tests/test_factory_frozen.py
# probes 1 and 2: the whole real story at the default budget and at budget 3, each inside the gate budget
for run in default budget3; do
  args=""; [ "$run" = budget3 ] && args="--search-budget 3"
  rc=0
  start=$(date +%s.%N)
  timeout {GATE_SECONDS + 60} .venv/bin/python -m factory.checks.carry_matrix $args --json "$OUT/probe-$run.json" > "$OUT/probe-$run.out" 2>&1 || rc=$?
  gate=$(echo "$(date +%s.%N) - $start" | bc)
  cat "$OUT/probe-$run.out"
  echo "whole-story gate ($run): ${{gate}}s (budget {GATE_SECONDS}s), exit $rc"
  [ "$rc" = 0 ] || {{ echo "whole-story CLI ($run) exited $rc; the real story passed attempt 5 with 0 stuck"; exit 1; }}
  awk -v t="$gate" 'BEGIN {{ exit !(t < {GATE_SECONDS}) }}' || {{ echo "whole-story gate ($run) took ${{gate}}s, over the {GATE_SECONDS}s budget"; exit 1; }}
  .venv/bin/python - "$OUT/probe-$run.json" "$run" <<'PY'
import json, sys
data = json.load(open(sys.argv[1])); run = sys.argv[2]
scenes = ["1A", "1B", "1C", "2A", "2B", "2C", "3A", "3B", "3C"]
missing = [s for s in scenes if data["entry_states"].get(s, 0) < 1]
assert not missing, f"scenes with no entry state: {{missing}}"
assert data["mode"] == "one_branch", data.get("mode")
assert data["entry_states"]["1B"] > 1, "no deviation from 1A reached 1B"
assert not data["stuck"] and not data["unreachable"], (data["stuck"], data["unreachable"])
assert "not_run" not in data, "not_run key still in JSON"
for key in ("undecided", "static_stuck", "max_unbounded_points", "search_budget", "max_search_points"):
    assert key in data, f"JSON lacks {{key}}"
if run == "default":
    assert data["search_budget"] == 300, data["search_budget"]
    assert data["undecided"] == 0, ("a healthy story should need no unbounded search at budget 300", data["undecided"])
else:
    assert data["search_budget"] == 3, data["search_budget"]
    assert data["undecided"] >= 1 and data["max_unbounded_points"] >= 1, ("budget 3 forced no unbounded search", data["undecided"])
print(run, "ok:", data["entry_states"], "searches", data["searches"], "turns", data["turns"], "undecided", data["undecided"])
PY
done
# probe 3: a seeded broken 3A through station 5: caught statically, fast, 3B and 3C unreachable
start=$(date +%s.%N)
timeout 300 .venv/bin/python - "$OUT/seeded-3a.json" <<'PY'
import json, re, sys, tempfile
from datetime import UTC, datetime
from pathlib import Path
import factory.stations.free_gates as fg
from factory.checks.gap_delta import DEFAULT_ROOT, all_anchors, save_baseline, snapshot
from factory.stations import build_handlers
from factory.tickets import Station, Ticket
from storygame.story_package.loader import load_story_package
from storygame.story_package.models import FactPredicate

real = load_story_package(Path("data/stories/continuity-initiative"))
pacing = real.pacing
bad = [t.model_copy(update={{"triggers": tuple(FactPredicate(fact_id="probe_never_true_fact", equals=True) for _ in t.triggers)}}) if t.source_scene_id == "3A" else t for t in pacing.transitions]
seeded = real.model_copy(update={{"pacing": pacing.model_copy(update={{"transitions": tuple(bad)}})}})
anchor = all_anchors(DEFAULT_ROOT)[0]
base = Path(tempfile.mkdtemp()) / "gaps.json"
save_baseline(snapshot(DEFAULT_ROOT, [anchor]), base)
fg.load_story_package = lambda root: seeded
seen = []
real_carry = fg.carry_matrix
def recording(*args, **kwargs):
    report = real_carry(*args, **kwargs)
    seen.append(report)
    return report
fg.carry_matrix = recording
now = datetime(2026, 1, 1, tzinfo=UTC).isoformat()
ticket = Ticket(id="t", scene="3A", station=Station.FREE_GATES, token_budget=1, created_at=now, updated_at=now,
                payload={{"gap_baseline": str(base), "anchors": [anchor], "carry_scenes": ["1A", "1B", "1C", "2A", "2B", "2C", "3A", "3B", "3C"]}})
r = build_handlers(Path.cwd())[Station.FREE_GATES](ticket, datetime.now(UTC))
print(r.check)
print(r.output[-1500:])
assert not r.passed and r.check == "carry_matrix", (r.passed, r.check)
assert len(seen) == 1, f"station 5 ran the carry matrix {{len(seen)}} times"
rep = seen[0]
json.dump({{"stuck": [c.__dict__ for c in rep.stuck], "unreachable": rep.unreachable, "seconds_by_scene": rep.seconds_by_scene, "static_stuck": rep.static_stuck, "undecided": rep.undecided}}, open(sys.argv[1], "w"), indent=2, default=list)
stuck_3a = [c for c in rep.stuck if c.scene == "3A"]
assert stuck_3a and all(c.reason == "no_exit_possible" for c in stuck_3a), [(c.label, c.reason) for c in stuck_3a]
assert rep.static_stuck == rep.entry_states["3A"] >= 1, (rep.static_stuck, rep.entry_states.get("3A"))
assert rep.seconds_by_scene["3A"] < 2, ("3A was not caught statically", rep.seconds_by_scene["3A"])
assert rep.unreachable == {{"3B": "3A", "3C": "3A"}}, rep.unreachable
assert not any(c.reason == "budget" for c in rep.stuck)
assert re.search(r"STUCK 3A entry#\\d+ .* no_exit_possible", r.output), "station output has no STUCK 3A ... no_exit_possible line"
for s in ("3B", "3C"):
    assert re.search(rf"UNREACHABLE {{s}}: every way in is stuck in 3A", r.output), f"no UNREACHABLE {{s}} line in station output"
print("seeded probe ok")
PY
seeded=$(echo "$(date +%s.%N) - $start" | bc)
echo "seeded-defect gate: ${{seeded}}s (budget {GATE_SECONDS}s)"
awk -v t="$seeded" 'BEGIN {{ exit !(t < {GATE_SECONDS}) }}' || {{ echo "seeded-defect gate took ${{seeded}}s, over the {GATE_SECONDS}s budget"; exit 1; }}
git diff --cached > "$OUT/carry-matrix-attempt6.patch"
cp NOTES_12.txt "$OUT/NOTES_12.txt"
test -s "$OUT/carry-matrix-attempt6.patch"
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
                "key": "carry-matrix-attempt6",
                "task_type": "code-feature",
                "engine": "codex",
                "engine_args": ["-c", "model_reasoning_effort=high"],
                "max_attempts": 2,
                "timeout_s": 5400,
                "check_timeout_s": 1500,
                "ownership": OWNED,
                "spec": SPEC,
                "check": CHECK,
                "expect_files": [],
                "verified": f"Quick tests green in under {QUICK_TEST_SECONDS}s with five named real (unpatched) tests; ruff clean; the real story passes with 0 stuck under {GATE_SECONDS}s at budget 300 (no undecided) and at budget 3 (undecided resolved unbounded); a seeded broken 3A fails station 5 once, caught statically in under 2 s for 3A, with 3B and 3C unreachable; no budget-as-stuck and no not_run; only four files changed.",
            }
        ],
    }


if __name__ == "__main__":
    out = Path(__file__).with_name("round12-attempt6-manifest.json")
    out.write_text(json.dumps(build(), indent=2) + "\n", encoding="utf-8")
    print(out)
