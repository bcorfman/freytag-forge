# ruff: noqa: E501  (spec strings are prose briefs for a worker)
"""Round 19h: the owner escalation when a ticket ends after two fun blocks (Opus's follow-up 2 design). FREE to build.

Opus designed this (opus-fun-followups-19g.md, claude-opus-5-5 high, 2026-11-22). Run AFTER round 19g is applied (both edit line.py).
One Codex task. Usage: build_round19h_escalation_manifest.py
"""

from __future__ import annotations

import json
from pathlib import Path

HERE = Path(__file__).parent
REPO = "/home/bcorfman/dev/freytag-forge"
WORK = "/home/bcorfman/dev/ringer-work/factory-escalation"
OWNED = [
    "factory/line.py",
    "factory/tickets.py",
    "factory/__main__.py",
    "tests/test_factory_escalation.py",
    "tests/test_factory_line.py",
    "tests/test_factory_tickets.py",
    "tests/test_factory_entry.py",
    "tests/test_factory_fun_feedback.py",
    "tests/shard_durations.json",
]
ALLOW_RE = (
    "^(factory/line\\.py|factory/tickets\\.py|factory/__main__\\.py|"
    "tests/test_factory_[a-z0-9_]+\\.py|tests/shard_durations\\.json)$"
)

REPLY = (HERE / "opus-fun-followups-19g.md").read_text()
DESIGN = REPLY[REPLY.index("### Follow-up 2") : REPLY.index("NOT NOW:")].strip()
SUBJECT = "factory: scene {scene_id} needs your call (fun review blocked twice, {ticket_id})"

SPEC = """You are a Python engineer. Your current working directory IS a git worktree of @REPO@ (detached at HEAD). Edit files here directly. NEVER git commit, never touch @REPO@ itself, never run `uv`, NEVER call a model (not `claude`, not `codex`), NEVER use the network, NEVER send a real notification (tests use a stub notifier only). FIRST run: [ -e .venv ] || ln -s @REPO@/.venv .venv . Environment for every command: `export PYTHONPATH=$PWD:$PWD/packages/worldkeeper/src TMPDIR=/tmp`. Ruff: `.venv/bin/python -m ruff check <files>` and `.venv/bin/python -m ruff format <files>` (line length 120, Python 3.12). Never pass --cov to pytest. Run tests as `.venv/bin/python -m pytest -q -p no:cacheprovider -n 0 <files>`.

BACKGROUND. The factory's fun review (station 10) can block a repair twice; the second block ends the ladder (`factory/line.py`: `MAX_FUN_ROUNDS = 2`, OPUS_REFRESH then `record_failure`, which sets the ticket aside for 6 hours; payload `fun_history` holds both blocked plans, reasons, advice and failed checks). Today nobody is told. Opus (claude-opus-5-5) designed the owner escalation; its design is below. Implement it exactly, VERBATIM where it gives templates, subject, state keys or numbers. Read `factory/line.py` (the ladder-exhausted branch; `_next_ready`, `_next_wake`, `run`), `factory/tickets.py` (`next_ready`, `record_failure`), `factory/breakers.py` (`Notifier`, `FileNotifier`, `CommandNotifier`) and `factory/__main__.py` (where the notifier is built and `FactoryLine` is constructed). Round 19g (recording lessons) has already added a `record_lessons` call at that same ladder-exhausted branch; keep it and call the escalation AFTER it. Opus could not read the code: where it assumes a name (`stuck_summary` source, the plan's `reason`, `fix_kind`, scene id), use what the code and payload really hold and write each choice in NOTES_19H.txt.

DESIGN DECISIONS ON TOP OF OPUS'S (mine, small): the "re-queue step skips owner-wait tickets" rule goes in `FactoryLine._next_ready` AND `FactoryLine._next_wake` (a parked ticket must neither be picked nor set the wake time) and in `TicketQueue.next_ready`; a ticket is parked when `payload["owner_wait"]` is a dict whose `reply` is None. The owner's reply channel is NOT built (Opus: not now); do not add any code that reads a reply except the skip rule.

OPUS'S DESIGN (follow-up 2):
@DESIGN@

TESTS (hermetic; a stub notifier collecting calls; never a real notifier, file or command). New `tests/test_factory_escalation.py` (under 8 seconds) covering Opus's item 8 list exactly, plus: the subject text is exactly "@SUBJECT@" with the ids filled in, the parked ticket is skipped by `_next_ready`, `_next_wake` and `TicketQueue.next_ready`, a ticket without `fun_history` never escalates, `owner_notice` and `owner_wait` survive a save and load of the ticket, `__main__` passes the notifier it builds to `FactoryLine` (look at `tests/test_factory_entry.py` for how `__main__` is tested). Update existing tests only where a legitimate behaviour change requires it; never delete or weaken a test. Add the new test file to `tests/shard_durations.json` with `.venv/bin/python scripts/regen_shard_durations.py --missing-only`.

HARD LIMITS. Edit only the owned files: @OWNED@. NEVER edit `breakers.py`, `fun_review.py`, `wiring.py`, `planner.py`, `fix_plan.py`, `lessons.py`, `probe.py`, `diagnose.py`, `factory/config/*`, `factory/precedents/*`, story data, `bench/` or `storygame/`. Story-agnostic code. Write NOTES_19H.txt (worktree root, never committed) listing every ambiguity and your choice."""

CHECK = """set -eo pipefail
WORK=@WORK@
mkdir -p "$WORK/out"
export PYTHONPATH=$PWD:$PWD/packages/worldkeeper/src TMPDIR=/tmp
[ -e .venv ] || ln -s @REPO@/.venv .venv
test -f tests/test_factory_escalation.py || { echo "tests/test_factory_escalation.py missing"; exit 1; }
git add -A -- factory tests
bad=$(git diff --cached --name-only | grep -vE '@ALLOW_RE@' || true)
[ -z "$bad" ] || { echo "files outside ownership staged: $bad"; exit 1; }
for f in factory/breakers.py factory/stations/fun_review.py factory/stations/wiring.py factory/stations/planner.py factory/stations/fix_plan.py factory/lessons.py; do
  git diff --cached --name-only | grep -qx "$f" && { echo "$f must not change"; exit 1; } || true
done
git diff --cached --name-only | grep -q '^factory/state/' && { echo "factory/state must not be staged"; exit 1; } || true
if grep -n -i -E "michelle|kristin|drawer|memory_card|laptop|continuity.initiative|reyes|walt|warehouse" factory/line.py factory/tickets.py factory/__main__.py; then echo "story-specific word"; exit 1; fi
grep -q "@SUBJECT@" factory/line.py || { echo "the exact Opus subject template is missing from factory/line.py"; exit 1; }
for t in "Nothing was merged. The ticket is parked and will not retry until you answer." "You may: (1) merge fix" "Last advice:" "fun_review_blocked_twice" "owner_notice" "owner_wait"; do
  grep -q "$t" factory/line.py || { echo "Opus text missing from factory/line.py: $t"; exit 1; }
done
grep -q "notifier" factory/__main__.py || { echo "__main__ does not pass the notifier"; exit 1; }
start=$(date +%s)
.venv/bin/python -m pytest -q -p no:cacheprovider -n 0 tests/test_factory_escalation.py
took=$(( $(date +%s) - start ))
echo "escalation tests took $took s (budget 8 s)"
[ "$took" -le 8 ] || { echo "over the 8 s budget"; exit 1; }
start=$(date +%s)
.venv/bin/python -m pytest -q -p no:cacheprovider -n 8 tests/test_factory_fun_review.py tests/test_factory_fun_feedback.py tests/test_factory_planner.py tests/test_factory_wiring.py tests/test_factory_line.py tests/test_factory_probe_routing.py tests/test_factory_fix_plan.py tests/test_factory_claim_edit.py tests/test_factory_stations.py tests/test_factory_probe.py tests/test_factory_diagnose.py tests/test_factory_followups.py tests/test_factory_frozen.py tests/test_factory_tickets.py tests/test_factory_entry.py tests/test_factory_breakers.py tests/test_factory_lessons.py
took=$(( $(date +%s) - start ))
echo "factory tests took $took s (budget 150 s)"
[ "$took" -le 150 ] || { echo "over the 150 s budget"; exit 1; }
.venv/bin/python -m ruff check factory tests/test_factory_escalation.py
.venv/bin/python -m ruff format --check factory tests/test_factory_escalation.py
[ ! -e factory/state/ledger.jsonl ] || { echo "a test wrote factory/state/ledger.jsonl"; exit 1; }
git diff --cached > "$WORK/out/escalation.patch"
test -s "$WORK/out/escalation.patch"
"""


def build() -> dict:
    def fill(text: str) -> str:
        return (
            text.replace("@DESIGN@", DESIGN)
            .replace("@SUBJECT@", SUBJECT)
            .replace("@REPO@", REPO)
            .replace("@WORK@", WORK)
            .replace("@OWNED@", ", ".join(OWNED))
            .replace("@ALLOW_RE@", ALLOW_RE)
        )

    return {
        "run_name": "factory-escalation",
        "workdir": WORK,
        "max_parallel": 1,
        "worktrees": True,
        "repo": REPO,
        "tasks": [
            {
                "key": "escalation",
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
                "verified": "A ticket that ends after two fun blocks is parked for the owner and the owner is told once, with both blocked fixes and the last advice; a notifier failure never stops the line.",
            }
        ],
    }


if __name__ == "__main__":
    out = HERE / "round19h-escalation-manifest.json"
    out.write_text(json.dumps(build(), indent=2) + "\n")
    print(out)
