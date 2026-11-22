# ruff: noqa: E501  (spec strings are prose briefs for a worker)
"""Round 19j: apply the real findings of Opus's check of the escalation code (opus-fun-check-19j.md). FREE to build.

One Codex task. Usage: build_round19j_escalation_fixes_manifest.py
"""

from __future__ import annotations

import json
from pathlib import Path

HERE = Path(__file__).parent
REPO = "/home/bcorfman/dev/freytag-forge"
WORK = "/home/bcorfman/dev/ringer-work/factory-escalation-fixes"
OWNED = [
    "factory/line.py",
    "factory/tickets.py",
    "tests/test_factory_escalation.py",
    "tests/test_factory_line.py",
    "tests/test_factory_tickets.py",
]
ALLOW_RE = "^(factory/line\\.py|factory/tickets\\.py|tests/test_factory_(escalation|line|tickets)\\.py)$"

SPEC = """You are a Python engineer. Your current working directory IS a git worktree of @REPO@ (detached at HEAD). Edit files here directly. NEVER git commit, never touch @REPO@ itself, never run `uv`, NEVER call a model, NEVER use the network, NEVER send a real notification (tests use a stub notifier only). FIRST run: [ -e .venv ] || ln -s @REPO@/.venv .venv . Environment for every command: `export PYTHONPATH=$PWD:$PWD/packages/worldkeeper/src TMPDIR=/tmp`. Ruff: `.venv/bin/python -m ruff check <files>` and `.venv/bin/python -m ruff format <files>` (line length 120, Python 3.12). Never pass --cov to pytest. Run tests as `.venv/bin/python -m pytest -q -p no:cacheprovider -n 0 <files>`.

BACKGROUND. The working tree holds the owner escalation for a ticket that ends after two fun-review blocks (`factory/line.py`: `_escalate_fun_impasse`, `_send_owner_notice`, `_retry_owner_notifications`, `run`; `factory/tickets.py`: `record_failure`, `next_ready`). Opus designed it and then reviewed the applied code (`scripts/ringer/1a-stuck/opus-fun-check-19j.md`). Three findings are real; apply exactly these and change NOTHING else (not the notice subject or body, not the skip rules in `_next_ready`, `_next_wake` and `TicketQueue.next_ready`, not the lessons call, not the 3-attempt cap):

A. THE LINE, NOT `record_failure`, DECIDES THE TRIGGER (Opus finding 2). Today `TicketQueue.record_failure` sets `payload["owner_wait"]` whenever a ticket exhausts the ladder at station FUN_REVIEW with at least two `fun_history` entries; that guesses the trigger. Remove that block from `tickets.py` (record_failure returns to a generic failure recorder; its existing tests must pass unchanged). In `line.py`, in the branch where the second fun block ends the ladder (it forces `ladder_rung = OPUS_REFRESH` and calls `record_failure(max_attempts=1)`, so the ticket is always set aside there), set `payload["owner_wait"] = {"reason": "fun_review_blocked_twice", "since": <now as ISO UTC, the line's `now`>, "reply": None}` on the returned ticket AFTER the lessons call and BEFORE `_escalate_fun_impasse`, save it, then escalate as today. `_escalate_fun_impasse` keeps reading `since` from `owner_wait`.

B. RETRY ON EVERY PASS (Opus finding 1). `FactoryLine.run` calls `_retry_owner_notifications` only when `step_number == 0`. A failed notice must be retried on every loop iteration, before `self.step(now)`. The 3-attempt cap already bounds the cost; keep it. Keep it cheap: it only visits tickets whose payload has an `owner_wait` dict and no sent notice.

C. RETRY ONLY THE RIGHT TICKETS (Opus finding 4). `_retry_owner_notifications` must skip a ticket unless `owner_wait` is a dict with `reason == "fun_review_blocked_twice"` and `reply is None`.

TESTS (hermetic; stub notifier only). Update `tests/test_factory_escalation.py` (and `tests/test_factory_tickets.py` / `tests/test_factory_line.py` only where behaviour legitimately changed; never delete or weaken a test): the ticket gets `owner_wait` from the line at the second block and `TicketQueue.record_failure` alone never sets it (also for a FUN_REVIEW ticket with two history entries); a notifier that fails on the first send is retried on the NEXT loop iteration of ONE `run` call (not only on a new `run`), stops at 3 attempts, and a success stops the retries; a parked ticket whose `owner_wait` has another reason or a non-None `reply` gets no retried notice; a second fun block that arrives at a ladder rung below OPUS_REFRESH still parks and notifies once (the line forces the rung). New test time under 8 seconds.

HARD LIMITS. Edit only: @OWNED@. NEVER edit `breakers.py`, `__main__.py`, `lessons.py`, `fun_review.py`, `wiring.py`, `planner.py`, `fix_plan.py`, `factory/config/*`, story data, `bench/` or `storygame/`. Story-agnostic code. Write NOTES_19J.txt (worktree root, never committed) listing every ambiguity and your choice."""

CHECK = """set -eo pipefail
WORK=@WORK@
mkdir -p "$WORK/out"
export PYTHONPATH=$PWD:$PWD/packages/worldkeeper/src TMPDIR=/tmp
[ -e .venv ] || ln -s @REPO@/.venv .venv
git add -A -- factory tests
bad=$(git diff --cached --name-only | grep -vE '@ALLOW_RE@' || true)
[ -z "$bad" ] || { echo "files outside ownership staged: $bad"; exit 1; }
git diff --cached --name-only | grep -q '^factory/state/' && { echo "factory/state must not be staged"; exit 1; } || true
if grep -n "fun_review_blocked_twice" factory/tickets.py; then echo "record_failure in tickets.py must no longer decide the trigger"; exit 1; fi
grep -q "fun_review_blocked_twice" factory/line.py || { echo "the line must set owner_wait with reason fun_review_blocked_twice"; exit 1; }
if grep -n "step_number == 0" factory/line.py; then echo "retry must run on every iteration, not only the first"; exit 1; fi
grep -q "_retry_owner_notifications" factory/line.py || { echo "_retry_owner_notifications missing"; exit 1; }
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
git diff --cached > "$WORK/out/escalation-fixes.patch"
test -s "$WORK/out/escalation-fixes.patch"
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
        "run_name": "factory-escalation-fixes",
        "workdir": WORK,
        "max_parallel": 1,
        "worktrees": True,
        "repo": REPO,
        "tasks": [
            {
                "key": "escalation-fixes",
                "task_type": "code-fix",
                "engine": "codex",
                "engine_args": ["-c", "model_reasoning_effort=high"],
                "max_attempts": 2,
                "timeout_s": 3600,
                "check_timeout_s": 900,
                "ownership": OWNED,
                "spec": fill(SPEC),
                "check": fill(CHECK),
                "expect_files": [],
                "verified": "The line, not record_failure, decides the owner-wait trigger; a failed owner notice is retried on every pass; only fun-impasse tickets with no reply are retried.",
            }
        ],
    }


if __name__ == "__main__":
    out = HERE / "round19j-escalation-fixes-manifest.json"
    out.write_text(json.dumps(build(), indent=2) + "\n")
    print(out)
