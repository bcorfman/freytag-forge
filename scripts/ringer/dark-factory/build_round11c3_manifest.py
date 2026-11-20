# ruff: noqa: E501  (spec strings are prose briefs for a worker)
"""Round 11c-3: lane bookkeeping for limit waits (overdue clock from the reported reset, wake command), paid-usage breaker, honest spend in status.

One Codex task, free, no model call. Needs rounds 11c-1 and 11c-2 committed. Usage: build_round11c3_manifest.py
"""

from __future__ import annotations

import json
from pathlib import Path

REPO = "/home/bcorfman/dev/freytag-forge"
WORK = "/home/bcorfman/dev/ringer-work/factory-honest-spend-lanes"

OWNED = [
    "factory/state.py",
    "factory/line.py",
    "factory/breakers.py",
    "factory/drill.py",
    "factory/tickets.py",
    "factory/__main__.py",
    "tests/test_factory_state.py",
    "tests/test_factory_line.py",
    "tests/test_factory_breakers.py",
    "tests/test_factory_drill.py",
    "tests/test_factory_tickets.py",
    "tests/test_factory_entry.py",
]

SPEC = f"""You are a Python engineer. Your current working directory IS a git worktree of {REPO} (detached at HEAD). Edit files here directly. NEVER git commit, never touch {REPO} itself, never run `uv`, never call a model, never run `claude` or `codex`, never use the network, never read the real home directory. FIRST run: [ -e .venv ] || ln -s {REPO}/.venv .venv . Ruff: `.venv/bin/python -m ruff check <files>` and `.venv/bin/python -m ruff format <files>` (line length 120, double quotes, Python 3.12, standard library only). Never pass --cov to pytest. Run tests as `PYTHONPATH=$PWD:$PWD/packages/worldkeeper/src TMPDIR=/tmp .venv/bin/python -m pytest -q -p no:cacheprovider -n 0 <test files>`.

BACKGROUND. The dark factory (`factory/`) is a deterministic state machine. `FactoryLine.step` (`factory/line.py`) runs one ticket's station handler; when the handler raises `LimitSleep(provider, resume_at)` (from `factory/guard.py`) the line puts that provider's lane to sleep in `FactoryState.lanes` (`factory/state.py`, provider to ISO time) and marks the ticket SLEEPING; a `resume_at` of None means the provider gave no reset time, and the line probes again after `probe_s` (default 1800 s). `check_breakers` (`factory/breakers.py`) stops the factory and notifies the owner on a circuit breaker. `factory/drill.py` trips every breaker on purpose (`python -m factory drill`). `factory/__main__.py` has `preflight`, `status`, `run` and `drill`.

Both model providers are subscriptions with five-hour and weekly windows. A spent weekly window is a normal sleep of up to a week, not a fault. The `provider_overdue` breaker must fire only when a provider is still unavailable 24 hours (`BreakerConfig.provider_overdue_s`) after the reset time it reported, or after the first limit when it reported none. Today it reads `state.lanes`, but `lane_ready` deletes a lane once its time passes and the next probe sleeps it again with a later time, so no lane time ever gets 24 hours old and the breaker can never fire.

Round 11c-2 (already in this worktree; read `factory/guard.py` and `factory/limits.py` first) made the spend ledger honest: `Usage` rows have `cost_kind` (`dollars`, `subscription`, `unknown`), `usd` is None unless dollars, and `SpendLedger` gained `unknown_cost_rows()`, `last_limits(provider)` (a `LimitReport` with `windows`, each `Window(name, used, resets_at, rejected)`) and `paid_usage_reasons()` (reasons recorded when Codex credits dropped or Claude reported paid overage). Read all of `factory/state.py`, `factory/line.py`, `factory/breakers.py`, `factory/drill.py`, `factory/tickets.py`, `factory/__main__.py` and their tests before you start.

YOUR TASK.
1. `factory/state.py`: a new persisted field `limited_since: dict[str, str]` (provider to ISO time; loads as empty when the key is missing from an old state file). `sleep_lane(provider, until, *, since: datetime | str | None = None)`: sets `lanes[provider] = until` as today, and when the provider is not already in `limited_since`, records `since` (or `until` when since is None). A later sleep never moves it. New `lane_succeeded(provider)`: removes the provider from `limited_since` and `lanes`, saves. New `wake(provider) -> bool`: removes the provider from `lanes` only (True when it was sleeping), keeps `limited_since`, saves. `lane_ready` and `sleeping_lanes` keep their behaviour and never touch `limited_since`.
2. `factory/line.py`, in `step`: on `LimitSleep`, the lane is `provider` (from `provider_for`) or, when that is None, `error.provider`. Sleep it with `since=error.resume_at` when the provider reported a reset, else `since=now` (the first limit). When the handler returns normally (pass or fail) and the lane is not None, call `state.lane_succeeded(lane)`. `_next_wake` is unchanged.
3. `factory/tickets.py`: `TicketQueue.wake_provider(provider, now) -> int`: every SLEEPING ticket whose `provider` equals it gets `sleep_until` set to `now` (ISO) and `updated_at` now; returns how many.
4. `factory/breakers.py`: `provider_overdue` reads `state.limited_since` instead of `state.lanes`, firing when `since + provider_overdue_s <= now`; its reason names the provider and the time it counts from. A new breaker `paid_usage`, evaluated right after `spend_rate`, fires when `ledger.paid_usage_reasons()` is not empty; the reason is the reasons joined with `; ` (first five). The `budget_spent` reason adds ` (a minimum: N calls of unknown cost)` when `ledger.unknown_cost_rows()` is above zero. Everything else unchanged.
5. `factory/drill.py`: add `paid_usage` to the drilled breakers (inject one subscription `Usage` row with `paid_usage="drill: codex credits dropped from 10.0 to 9.5"`, `cost_kind="subscription"`, `usd=None`), and make the `provider_overdue` drill use `state.sleep_lane(provider, until, since=now - overdue)` so it trips through `limited_since`. Keep the other drills as they are; the drill must still pass on all breakers (`python -m factory drill` exit 0).
6. `factory/__main__.py`: a new `wake PROVIDER` subcommand: loads the state and ticket queue from the config paths, calls `state.wake` and `queue.wake_provider` with the current time, prints `<provider>: lane cleared, <n> ticket(s) ready` or `<provider>: lane was not sleeping, <n> ticket(s) ready`, exit 0. It does not need a preflight. `status`: print the spend line as `total spend: X USD` with ` (a minimum: N calls of unknown cost)` when there are such rows; for every provider with `last_limits`, one line `<provider> windows: five_hour 19%, seven_day 6%` (sorted by window name, percentage rounded to whole numbers); one line per `limited_since` entry: `<provider> limited since <time>`.

TESTS (keep every existing test passing, adjusting only where it pinned the old overdue mechanics or the old breaker list; add):
- state: since recorded on first sleep and not moved by later sleeps; lane_succeeded clears both; wake clears the lane and keeps since; old state files load.
- line, through real steps with a fake clock and a handler that raises LimitSleep: (a) a lane first limited with reported reset R, then probed every 30 minutes with LimitSleep(provider, None) until 25 hours past R: `check_breakers` (the real one, from breakers.py, with a real queue, state and ledger) trips `provider_overdue` only once the time passes R + 24 h, never before; (b) a lane sleeping to a weekly reset six days ahead, checked every hour until one hour before the reset, never trips; (c) after a LimitSleep, a handler that returns normally clears `limited_since`; (d) a LimitSleep with provider_for None sleeps `error.provider`'s lane.
- tickets: wake_provider wakes only that provider's sleeping tickets.
- breakers: paid_usage trips with the recorded reason; the budget reason says it is a minimum when unknown rows exist; the old "planted lanes timestamp" overdue test is replaced by one using `limited_since`.
- drill: the result list includes `paid_usage` and all pass.
- entry: `wake codex` on a state with a sleeping codex lane and a sleeping codex ticket prints the cleared line, the ticket's `sleep_until` becomes now and the next `FactoryLine.step` at that time runs it; `wake` on a provider that was not sleeping exits 0 with the not-sleeping line; `status` prints the minimum note, a windows line and a limited-since line from a prepared ledger and state.

HARD LIMITS. Edit only these files: {", ".join(OWNED)}. Never edit `factory/guard.py`, `factory/limits.py`, `factory/config/`, other factory modules or other tests. Do not add dependencies. Write NOTES_11c3.txt (worktree root, never committed) listing every rule you found ambiguous and the choice you made.
"""

CHECK = f"""set -eo pipefail
WORK={WORK}
mkdir -p "$WORK"
export PYTHONPATH=$PWD:$PWD/packages/worldkeeper/src TMPDIR=/tmp
[ -e .venv ] || ln -s {REPO}/.venv .venv
git add -A -- factory tests
allowed="{" ".join(OWNED)}"
bad=$(git diff --cached --name-only | while read -r f; do case " $allowed " in *" $f "*) ;; *) echo "$f";; esac; done)
[ -z "$bad" ] || {{ echo "files outside ownership staged: $bad"; exit 1; }}
.venv/bin/python -m pytest -q -p no:cacheprovider -n 0 tests/test_factory_*.py
.venv/bin/python -m ruff check factory tests/test_factory_*.py
.venv/bin/python -m ruff format --check factory tests/test_factory_*.py
.venv/bin/python -m factory drill | tee "$WORK/drill.out"
grep -qiE "paid_usage[ |]+pass" "$WORK/drill.out" || {{ echo "drill does not pass paid_usage"; exit 1; }}
# independent probe: real line, real breakers, probes every 30 minutes past a reported reset
.venv/bin/python - <<'PY'
import tempfile
from datetime import UTC, datetime, timedelta
from pathlib import Path
from factory.breakers import BreakerConfig, check_breakers
from factory.guard import Caps, LimitSleep, SpendLedger
from factory.line import FactoryLine
from factory.state import FactoryState
from factory.tickets import Station, Ticket, TicketQueue

d = Path(tempfile.mkdtemp())
queue, state, ledger = TicketQueue(d / "t"), FactoryState.load(d / "s.json"), SpendLedger(d / "l.jsonl")
caps = Caps(total_budget_usd=10.0, daily_cap_usd={{}}, call_caps=[], rate_window_s=3600, rate_max_usd=10.0)
cfg = BreakerConfig()
t0 = datetime(2026, 11, 20, tzinfo=UTC)
reset = t0 + timedelta(days=6)
queue.add(Ticket(id="a", scene="1A", station=Station.PROSE, token_budget=1000, created_at=t0.isoformat(), updated_at=t0.isoformat(), payload={{"provider": "codex"}}))
calls = []
def handler(ticket, now):
    calls.append(now)
    raise LimitSleep("codex", reset if len(calls) == 1 else None)
def reasons(now):
    return [t.name for t in check_breakers(queue=queue, state=state, ledger=ledger, caps=caps, config=cfg, now=now)]
line = FactoryLine(queue=queue, state=state, handlers={{Station.PROSE: handler}}, provider_for=lambda t: t.payload.get("provider"), check_breakers=lambda now: [])
now = t0
line.step(now)
first_trip = None
while now < reset + timedelta(hours=25):
    now += timedelta(minutes=30)
    line.step(now)
    if "provider_overdue" in reasons(now) and first_trip is None:
        first_trip = now
assert first_trip is not None, "overdue never fired"
assert reset + timedelta(hours=24) <= first_trip <= reset + timedelta(hours=24, minutes=30), first_trip
assert len(calls) > 40, len(calls)
print("probe ok", first_trip)
PY
git diff --cached > {WORK}/lanes.patch
test -s {WORK}/lanes.patch
"""


def build() -> dict:
    return {
        "run_name": "factory-honest-spend",
        "workdir": WORK,
        "max_parallel": 1,
        "worktrees": True,
        "repo": REPO,
        "tasks": [
            {
                "key": "lanes-breakers",
                "task_type": "code-feature",
                "engine": "codex",
                "engine_args": ["-c", "model_reasoning_effort=high"],
                "max_attempts": 2,
                "timeout_s": 2400,
                "check_timeout_s": 600,
                "ownership": OWNED,
                "spec": SPEC,
                "check": CHECK,
                "expect_files": [],
                "verified": "Every factory test file green; ruff clean; drill passes including paid_usage; probe drives a real line with probes every 30 minutes and the real breakers fire provider_overdue only 24 hours after the reported reset; only owned files changed.",
            }
        ],
    }


if __name__ == "__main__":
    out = Path(__file__).with_name("round11c3-manifest.json")
    out.write_text(json.dumps(build(), indent=2) + "\n", encoding="utf-8")
    print(out)
