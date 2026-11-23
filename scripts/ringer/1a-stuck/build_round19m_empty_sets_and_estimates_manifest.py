# ruff: noqa: E501  (spec strings are prose briefs for a worker)
"""Round 19m: reject a pacing beat that sets no fact (plan lint), and record an estimate on every ledger row. FREE to build.

Two independent Codex tasks, disjoint files. Usage: build_round19m_empty_sets_and_estimates_manifest.py
"""

from __future__ import annotations

import json
from pathlib import Path

REPO = "/home/bcorfman/dev/freytag-forge"
WORK = "/home/bcorfman/dev/ringer-work/factory-empty-sets-and-estimates"

COMMON = """You are a Python engineer. Your current working directory IS a git worktree of @REPO@ (detached at HEAD). Edit files here directly. NEVER git commit, never touch @REPO@ itself, never run `uv`, NEVER call a model (not `claude`, not `codex`), NEVER use the network, NEVER run `python -m bench run`. FIRST run: [ -e .venv ] || ln -s @REPO@/.venv .venv . Environment for every command: `export PYTHONPATH=$PWD:$PWD/packages/worldkeeper/src TMPDIR=/tmp`. Ruff (python files only): `.venv/bin/python -m ruff check <files>` and `.venv/bin/python -m ruff format <files>` (line length 120, Python 3.12). Never pass --cov to pytest. Run tests as `.venv/bin/python -m pytest -q -p no:cacheprovider -n 0 <files>`. Tests must be hermetic (no model call, no network, never write factory/state/). Do not add a new test file: add tests to the owned existing test files. If an OLD test pins behaviour this change deliberately changes, update that test to the new behaviour (say so in NOTES.txt); do not leave a failing test and do not weaken a test that is unrelated to the change."""

SPEC_EMPTY = (
    COMMON
    + """

BACKGROUND. The dark factory's planner (station 4) proposes a plan object; `factory/stations/fix_plan.py` lints it before any worker edits the story. For kind `add_pacing_beat` the plan has a `beat` with `when` and `sets` maps (fact name -> bool). A compiled story `PacingEvent` must have at least ONE effect, so a beat with `sets: {}` makes the whole story fail to compile (pydantic: "effects: Tuple should have at least 1 item"). In a real run the planner proposed three beats with `sets: {}`; the lint passed all of them, the worker wrote them, the story failed to compile, and the check output gave the planner nothing useful to retry with.

CHANGE 1 (lint). In the `add_pacing_beat` branch of the plan lint in `fix_plan.py` (the code near `plan.facts` and `plan.redundant_effect`), add a lint problem when `beat["sets"]` is empty. Use the problem code `plan.empty_effect` with a plain message that tells the planner what to do: a beat must set at least one declared story fact that no other pacing event or claim sets (or that it guards with `when` pinned to the opposite value); name no story-specific fact in the code. Keep every other lint as is, and make sure the new problem is reported together with the others (do not return early), in the same list and format as `plan.redundant_effect`.

CHANGE 2 (planner brief). In `factory/stations/planner.py`, in the planner brief, add exactly ONE short plain sentence right after the sentence "The beat when and sets fields map string fact names to boolean values.": a beat's sets field must name at least one story fact, because a beat with no effect cannot compile. Change no other sentence. If a test pins the brief text, update only what that one sentence requires.

TESTS. In `tests/test_factory_fix_plan.py` add: (1) an `add_pacing_beat` plan with `sets: {}` yields a problem starting `plan.empty_effect` and no other new problem for an otherwise valid plan (build the valid plan the way the existing tests in that file do); (2) the same plan with one declared fact in `sets` (no redundant or shared effect) does not yield `plan.empty_effect`; (3) the empty-sets problem and another problem (for example a bad beat id) are both reported in one call. In `tests/test_factory_planner.py` add or update the brief test so the new sentence is pinned.

HARD LIMITS. Edit only: factory/stations/fix_plan.py, factory/stations/planner.py, tests/test_factory_fix_plan.py, tests/test_factory_planner.py. NEVER edit factory/line.py, wiring.py, probe.py, guard.py, tickets.py, factory/config/*, story data under data/, bench/ or storygame/. Write NOTES.txt (worktree root, never committed) listing every ambiguity and your choice."""
)

SPEC_ESTIMATE = (
    COMMON
    + """

BACKGROUND. The factory spend ledger (`SpendLedger` and the `Usage` dataclass in `factory/guard.py`) writes one JSON line per billed call (fields at, provider, model_id, station, scene, ticket_id, tokens, usd, cost_kind, list_usd, paid_usage, limits). The owner wants every row to carry the ESTIMATE made before the call, next to the actual `usd`, so estimates can be compared with actuals over time.

CHANGE. (1) Add `estimate_usd: float | None = None` to `Usage` (validate like `list_usd`: None, or a non-bool number that is not negative; read how `list_usd` is validated and follow it). (2) `SpendLedger.record` always writes an `estimate_usd` key (null when unknown); `_read` reads it back with `payload.get("estimate_usd")` so old rows without the key still load. (3) `guarded_call` gets an optional keyword argument `estimate_usd: float | None = None`, placed after `rand`, and passes it into the `Usage` it records. Existing callers (planner, diagnose, fun_review) are NOT changed; they keep recording None. (4) In `factory/stations/probe.py`, `_record_probe_spend` gets a new keyword `estimate_usd: float | None` and records it; the probe handler passes its already-computed `projected` value. If `projected` is not yet computed when the `finally` block runs (an early return before it), pass None. (5) Add `SpendLedger.estimate_report(self) -> list[dict]`: group rows that have BOTH a numeric `estimate_usd` and a numeric `usd` with `cost_kind == "dollars"` by `station`, and return one dict per station sorted by station: {"station", "calls", "estimate_usd", "actual_usd", "ratio"} where ratio is actual / estimate rounded to 2 decimals, or None when the estimate sum is 0. (6) In `factory/__main__.py` `_status`, after the line "total spend: ...", print one line per entry of `ledger.estimate_report()` in the form `estimate vs actual <station>: estimated <e> USD, actual <a> USD, ratio <r> over <n> call(s)` (use `n/a` for a None ratio), and print nothing when the report is empty so existing status output is unchanged.

TESTS (add to tests/test_factory_guard.py, tests/test_factory_probe.py and tests/test_factory_entry.py; keep each new test fast): a ledger row round-trips `estimate_usd`; a row written without the key still loads with None; a negative or boolean estimate is rejected; `guarded_call` records the estimate it was given (follow the existing guarded_call tests for the fake provider setup); `estimate_report` groups by station, ignores rows lacking either number or not in dollars, and returns ratio None for a zero estimate; the probe records `estimate_usd` equal to the projected cost for a hermetic probe run (use the injectable runner and budget reader the existing probe tests use); `_status` prints the estimate line only when there is a row with an estimate (extend the existing status tests in tests/test_factory_entry.py). If an old test pins the exact JSON line or key set of a ledger row, update it to include the new key.

HARD LIMITS. Edit only: factory/guard.py, factory/stations/probe.py, factory/__main__.py, tests/test_factory_guard.py, tests/test_factory_probe.py, tests/test_factory_entry.py (the existing status tests live there). NEVER edit fix_plan.py, planner.py, line.py, wiring.py, live_playtest.py, tickets.py, factory/config/*, story data under data/, bench/ or storygame/. Write NOTES.txt (worktree root, never committed) listing every ambiguity and your choice."""
)

CHECK_COMMON = """set -eo pipefail
WORK=@WORK@
mkdir -p "$WORK/out"
export PYTHONPATH=$PWD:$PWD/packages/worldkeeper/src TMPDIR=/tmp
[ -e .venv ] || ln -s @REPO@/.venv .venv
git add -A -- factory tests
bad=$(git diff --cached --name-only | grep -vE '@ALLOW_RE@' || true)
[ -z "$bad" ] || { echo "files outside ownership staged: $bad"; exit 1; }
git status --porcelain -- data | grep . && { echo "story data changed"; exit 1; } || true
"""

CHECK_EMPTY = (
    CHECK_COMMON
    + """grep -q "plan.empty_effect" factory/stations/fix_plan.py || { echo "plan.empty_effect lint missing"; exit 1; }
start=$(date +%s)
.venv/bin/python -m pytest -q -p no:cacheprovider -n 0 tests/test_factory_fix_plan.py tests/test_factory_planner.py
took=$(( $(date +%s) - start ))
echo "fix_plan and planner tests took $took s (budget 60 s)"
[ "$took" -le 60 ] || { echo "over the 60 s budget"; exit 1; }
start=$(date +%s)
.venv/bin/python -m pytest -q -p no:cacheprovider -n 8 tests/test_factory_wiring.py tests/test_factory_line.py tests/test_factory_probe_routing.py tests/test_factory_followups.py
took=$(( $(date +%s) - start ))
echo "neighbour tests took $took s (budget 120 s)"
[ "$took" -le 120 ] || { echo "over the 120 s budget"; exit 1; }
.venv/bin/python -m ruff check factory/stations/fix_plan.py factory/stations/planner.py tests/test_factory_fix_plan.py tests/test_factory_planner.py
.venv/bin/python -m ruff format --check factory/stations/fix_plan.py factory/stations/planner.py tests/test_factory_fix_plan.py tests/test_factory_planner.py
[ ! -e factory/state/ledger.jsonl ] || { echo "a test wrote factory/state/ledger.jsonl"; exit 1; }
git diff --cached > "$WORK/out/empty-sets.patch"
test -s "$WORK/out/empty-sets.patch"
"""
)

CHECK_ESTIMATE = (
    CHECK_COMMON
    + """grep -q "estimate_usd" factory/guard.py || { echo "estimate_usd missing in guard.py"; exit 1; }
grep -q "estimate_usd" factory/stations/probe.py || { echo "estimate_usd missing in probe.py"; exit 1; }
grep -q "estimate vs actual" factory/__main__.py || { echo "status line missing in __main__.py"; exit 1; }
cat > "$WORK/out/verify_estimate.py" <<'PYV'
import json
import tempfile
from datetime import UTC, datetime
from pathlib import Path

from factory.guard import SpendLedger, Usage

with tempfile.TemporaryDirectory() as directory:
    ledger = SpendLedger(Path(directory) / "ledger.jsonl")
    now = datetime.now(UTC)
    ledger.record(Usage(now, "cloudflare", "workers-ai", "probe", "1A", "t", 0, 0.5, estimate_usd=1.0))
    ledger.record(Usage(now, "cloudflare", "workers-ai", "probe", "1A", "t", 0, 0.25, estimate_usd=0.5))
    ledger.record(Usage(now, "cloudflare", "workers-ai", "playtest", "1A", "t", 0, 0.1))
    row = json.loads((Path(directory) / "ledger.jsonl").read_text().splitlines()[0])
    assert row["estimate_usd"] == 1.0, row
    report = ledger.estimate_report()
    assert report == [{"station": "probe", "calls": 2, "estimate_usd": 1.5, "actual_usd": 0.75, "ratio": 0.5}], report
print("estimate round trip ok")
PYV
.venv/bin/python "$WORK/out/verify_estimate.py"
start=$(date +%s)
.venv/bin/python -m pytest -q -p no:cacheprovider -n 8 tests/test_factory_guard.py tests/test_factory_probe.py tests/test_factory_live_playtest.py tests/test_factory_planner.py tests/test_factory_entry.py tests/test_factory_limits.py tests/test_factory_deliver.py
took=$(( $(date +%s) - start ))
echo "factory ledger tests took $took s (budget 150 s)"
[ "$took" -le 150 ] || { echo "over the 150 s budget"; exit 1; }
.venv/bin/python -m ruff check factory/guard.py factory/stations/probe.py factory/__main__.py tests/test_factory_guard.py tests/test_factory_probe.py tests/test_factory_entry.py
.venv/bin/python -m ruff format --check factory/guard.py factory/stations/probe.py factory/__main__.py tests/test_factory_guard.py tests/test_factory_probe.py tests/test_factory_entry.py
[ ! -e factory/state/ledger.jsonl ] || { echo "a test wrote factory/state/ledger.jsonl"; exit 1; }
git diff --cached > "$WORK/out/estimate-field.patch"
test -s "$WORK/out/estimate-field.patch"
"""
)

TASKS = [
    {
        "key": "empty-sets-lint",
        "owned": [
            "factory/stations/fix_plan.py",
            "factory/stations/planner.py",
            "tests/test_factory_fix_plan.py",
            "tests/test_factory_planner.py",
        ],
        "allow": "^(factory/stations/(fix_plan|planner)\\.py|tests/test_factory_(fix_plan|planner)\\.py)$",
        "spec": SPEC_EMPTY,
        "check": CHECK_EMPTY,
        "verified": "A pacing beat with no `sets` fact is rejected by the plan lint with a message the planner can act on, and the planner brief says a beat must set at least one fact.",
    },
    {
        "key": "estimate-field",
        "owned": [
            "factory/guard.py",
            "factory/stations/probe.py",
            "factory/__main__.py",
            "tests/test_factory_guard.py",
            "tests/test_factory_probe.py",
            "tests/test_factory_entry.py",
        ],
        "allow": "^(factory/(guard|__main__)\\.py|factory/stations/probe\\.py|tests/test_factory_(guard|probe|entry)\\.py)$",
        "spec": SPEC_ESTIMATE,
        "check": CHECK_ESTIMATE,
        "verified": "Every ledger row carries an estimate_usd (null when unknown), the probe records its projected cost, and the factory status prints estimate vs actual per station.",
    },
]


def build() -> dict:
    tasks = []
    for item in TASKS:

        def fill(text: str, item=item) -> str:
            return (
                text.replace("@REPO@", REPO)
                .replace("@WORK@", WORK)
                .replace("@OWNED@", ", ".join(item["owned"]))
                .replace("@ALLOW_RE@", item["allow"])
            )

        tasks.append(
            {
                "key": item["key"],
                "task_type": "code-fix",
                "engine": "codex",
                "engine_args": ["-c", "model_reasoning_effort=high"],
                "max_attempts": 2,
                "timeout_s": 3000,
                "check_timeout_s": 600,
                "ownership": item["owned"],
                "spec": fill(item["spec"]),
                "check": fill(item["check"]),
                "expect_files": [],
                "verified": item["verified"],
            }
        )
    return {
        "run_name": "factory-empty-sets-and-estimates",
        "workdir": WORK,
        "max_parallel": 2,
        "worktrees": True,
        "repo": REPO,
        "tasks": tasks,
    }


if __name__ == "__main__":
    out = Path(__file__).with_name("round19m-empty-sets-and-estimates-manifest.json")
    out.write_text(json.dumps(build(), indent=2) + "\n")
    print(out)
