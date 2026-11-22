# ruff: noqa: E501  (spec strings are prose briefs for a worker)
"""Round 18i-2: story-data tickets enter at diagnosis, and the planner sees the causes. FREE: no model call.

One Codex task. Usage: build_round18i2_diagnose_routing_manifest.py
"""

from __future__ import annotations

import json
from pathlib import Path

REPO = "/home/bcorfman/dev/freytag-forge"
WORK = "/home/bcorfman/dev/ringer-work/factory-diagnose-routing"
OWNED = [
    "factory/line.py",
    "factory/followups.py",
    "factory/stations/fix_plan.py",
    "factory/stations/planner.py",
    "tests/test_factory_line.py",
    "tests/test_factory_followups.py",
    "tests/test_factory_fix_plan.py",
    "tests/test_factory_planner.py",
]
ALLOW_RE = "^(factory/line\\.py|factory/followups\\.py|factory/stations/(fix_plan|planner)\\.py|tests/test_factory_[a-z0-9_]+\\.py)$"

SPEC = """You are a Python engineer. Your current working directory IS a git worktree of @REPO@ (detached at HEAD). Edit files here directly. NEVER git commit, never touch @REPO@ itself, never run `uv`, NEVER call a model (not `claude`, not `codex`), NEVER use the network. FIRST run: [ -e .venv ] || ln -s @REPO@/.venv .venv . Environment for every command: `export PYTHONPATH=$PWD:$PWD/packages/worldkeeper/src TMPDIR=/tmp`. Ruff: `.venv/bin/python -m ruff check <files>` and `.venv/bin/python -m ruff format <files>` (line length 120, Python 3.12). Never pass --cov to pytest. Run tests as `.venv/bin/python -m pytest -q -p no:cacheprovider -n 0 <files>`.

BACKGROUND. Station 11 (`factory/stations/diagnose.py`, read it first) gives every failing turn a cause and returns `payload_updates={"diagnosis": {"rows": [...], "counts": {...}}}` (each row has `key`, `cause`, `why`, `signals`). It is registered but not routed: nothing sends a ticket to it and the planner never sees its output. Read `factory/line.py` (`FactoryLine.step`, the routing after a PASSED station: `merge_to_main` special cases, `Station(ticket.station + 1)` default), `factory/followups.py` (`FOLLOWUP_STATIONS`, where follow-up tickets start), `factory/stations/fix_plan.py` (`build_evidence`) and `factory/stations/planner.py` (`PLANNER_BRIEF`) and their tests.

BUILD 1, routing. A PASSED `DIAGNOSE` station always moves the ticket to `WIRING` (explicit; never `Station(ticket.station + 1)`), regardless of `merge_to_main`, with the same reset of attempts, ladder rung, provider and sleep fields that the other advances do. A FAILED `DIAGNOSE` takes the ordinary failure path. Every other route is unchanged.

BUILD 2, entry. In `factory/followups.py` story-data follow-up tickets now start at `Station.DIAGNOSE` (narrator-prompt, world-model and engine tickets are unchanged). Ticket ids and everything else are unchanged.

BUILD 3, planner evidence. `build_evidence` adds a key `diagnosis` built from the ticket payload's `diagnosis` (the station's output): `{"counts": <counts>, "rows": [{"key", "cause", "why"} for each row]}` with each `why` cut to 160 characters, the whole value limited to 6000 characters of compact JSON (when over, drop `why` texts first, then trailing rows, always keeping `counts`); `diagnosis: null` when the payload has none or it is malformed (never an exception). Nothing else in the packet changes.

BUILD 4, brief. In `PLANNER_BRIEF` add two short plain sentences at a 12th grade reading level, story-agnostic: the evidence lists the cause of each failing turn and how many turns share each cause; choose the fix that addresses the most common cause a proven technique in the precedents can fix, and say in the reason which cause it targets. Keep every existing sentence, the JSON shape and the 400-character reason limit (keep your addition short). Keep the `Precedent:` rule exactly as it is.

TESTS (hermetic; stubs only). In `tests/test_factory_line.py`: a story-data ticket passed at `DIAGNOSE` lands on `WIRING` with attempts reset, both with and without `merge_to_main`; a failed `DIAGNOSE` records a failure and stays at station 11; existing routes (4 to 5, 5 to 6, 6 to 10 to 9 for merge tickets, 9 to 7) unchanged. In `tests/test_factory_followups.py`: a story-data follow-up starts at `DIAGNOSE`, a narrator-prompt one at `WIRING`, world-model at `WORLD_NEED` (update existing expectations). In `tests/test_factory_fix_plan.py`: `test_evidence_carries_the_diagnosis` (counts and rows with cut `why`, the size limit holds for 200 long rows, `counts` always kept), `test_evidence_diagnosis_is_null_without_it`. In `tests/test_factory_planner.py`: `test_planner_brief_mentions_the_causes` (the brief mentions causes and the most common cause) and a prompt test that a diagnosis in the payload reaches the prompt. Each test file runs in under 15 seconds.

HARD LIMITS. Edit only the owned files: @OWNED@. Never edit `factory/stations/diagnose.py`, `wiring.py`, `fun_review.py`, `deliver.py`, `triage.py`, `factory/tickets.py`, config files, story data or `storygame/`. No story names in `planner.py`. Write NOTES_18I2.txt (worktree root, never committed) listing every ambiguity and your choice."""

CHECK = """set -eo pipefail
WORK=@WORK@
mkdir -p "$WORK/out"
export PYTHONPATH=$PWD:$PWD/packages/worldkeeper/src TMPDIR=/tmp
[ -e .venv ] || ln -s @REPO@/.venv .venv
test -f factory/stations/diagnose.py || { echo "diagnose.py missing from the base tree"; exit 1; }
git add -A -- factory tests
bad=$(git diff --cached --name-only | grep -vE '@ALLOW_RE@' || true)
[ -z "$bad" ] || { echo "files outside ownership staged: $bad"; exit 1; }
if grep -n -i -E "michelle|kristin|drawer|memory_card|laptop|continuity.initiative|reyes|walt" factory/stations/planner.py; then echo "story-specific word in planner.py"; exit 1; fi
grep -q "DIAGNOSE" factory/line.py || { echo "DIAGNOSE not routed in line.py"; exit 1; }
grep -q "DIAGNOSE" factory/followups.py || { echo "DIAGNOSE not used in followups.py"; exit 1; }
for name in test_evidence_carries_the_diagnosis test_evidence_diagnosis_is_null_without_it test_planner_brief_mentions_the_causes; do
  grep -rq "def $name" tests || { echo "test $name missing"; exit 1; }
done
start=$(date +%s)
.venv/bin/python -m pytest -q -p no:cacheprovider -n 8 tests/test_factory_line.py tests/test_factory_followups.py tests/test_factory_fix_plan.py tests/test_factory_planner.py tests/test_factory_diagnose.py tests/test_factory_stations.py tests/test_factory_wiring.py tests/test_factory_deliver.py tests/test_factory_fun_review.py tests/test_factory_triage.py tests/test_factory_tickets.py tests/test_factory_live_playtest.py
took=$(( $(date +%s) - start ))
echo "factory tests took $took s (budget 150 s)"
[ "$took" -le 150 ] || { echo "over the 150 s budget"; exit 1; }
.venv/bin/python -m ruff check factory tests/test_factory_line.py tests/test_factory_followups.py tests/test_factory_fix_plan.py tests/test_factory_planner.py
.venv/bin/python -m ruff format --check factory tests/test_factory_line.py tests/test_factory_followups.py tests/test_factory_fix_plan.py tests/test_factory_planner.py
[ ! -e factory/state/ledger.jsonl ] || { echo "a test wrote factory/state/ledger.jsonl"; exit 1; }
git diff --cached > "$WORK/out/diagnose-routing.patch"
test -s "$WORK/out/diagnose-routing.patch"
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
        "run_name": "factory-diagnose-routing",
        "workdir": WORK,
        "max_parallel": 1,
        "worktrees": True,
        "repo": REPO,
        "tasks": [
            {
                "key": "diagnose-routing",
                "task_type": "code-feature",
                "engine": "codex",
                "engine_args": ["-c", "model_reasoning_effort=high"],
                "max_attempts": 2,
                "timeout_s": 3000,
                "check_timeout_s": 900,
                "ownership": OWNED,
                "spec": fill(SPEC),
                "check": fill(CHECK),
                "expect_files": [],
                "verified": "Story-data tickets start at diagnosis, a passed diagnosis always goes to wiring, and the planner's evidence and brief carry the causes; tests use stubs only.",
            }
        ],
    }


if __name__ == "__main__":
    out = Path(__file__).with_name("round18i2-diagnose-routing-manifest.json")
    out.write_text(json.dumps(build(), indent=2) + "\n")
    print(out)
