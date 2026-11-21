# ruff: noqa: E501  (spec strings are prose briefs for a worker)
"""Round 16: read the Cloudflare Worker's daily spend counter into the factory ledger. FREE: no model call, no network, no deploy.

Two parallel Codex tasks with disjoint files, joined by one HTTP contract:
  1. js-worker  - the Worker exposes its per-UTC-day spend counter read-only at POST /budget.
  2. py-reader  - the factory reads it before and after a billed run and writes one `cloudflare` ledger row.
Usage: build_round16_cfspend_manifest.py
"""

from __future__ import annotations

import json
from pathlib import Path

REPO = "/home/bcorfman/dev/freytag-forge"
WORK = "/home/bcorfman/dev/ringer-work/factory-cfspend"

JS_OWNED = ["worker/src/budget.js", "worker/src/index.js", "worker/test/worker.test.js"]
PY_OWNED = ["factory/cloudflare_spend.py", "factory/stations/live_playtest.py", "tests/test_factory_live_playtest.py"]

CONTRACT = """THE SHARED CONTRACT (both tasks; do not change it). The narration Worker (`worker/`) already counts what it spends: one Durable Object per UTC day (`DailyBudget`, `BudgetLedger` in `worker/src/budget.js`) holds `spent` (settled actual cost, whole micro-dollars) and open `reservations`. Every narrator call and every Jev call goes through it. There is no way to READ the counter yet. New read-only endpoint: `POST <worker origin>/budget` with header `Authorization: Bearer <DEMO_SHARED_TOKEN>` and an empty JSON body `{}`. It makes no model call and reserves and spends nothing. Success is HTTP 200 and
  {"status": "ok", "day": "YYYY-MM-DD", "spent_micro_usd": <int>, "reserved_micro_usd": <int>, "limit_micro_usd": <int>}
where `day` is the UTC day (`utcDay(new Date())`), `spent_micro_usd` is the day's settled `spent`, `reserved_micro_usd` the sum of open reservations, and `limit_micro_usd` is `dailyLimit(env.DAILY_BUDGET_USD)`. A wrong or missing token gets the same 401 every route gets; a missing DAILY_BUDGET binding gets the existing `BUDGET_UNAVAILABLE` 503. A Worker that has not been redeployed answers this path as a narration request (it is not an error JSON with `status: "ok"`), so a reader must accept only a 200 JSON object with `status == "ok"` and the three integer fields, and treat everything else as 'unknown'."""

JS_SPEC = """You are a JavaScript engineer. Your current working directory IS a git worktree of @REPO@ (detached at HEAD). Edit files here directly. NEVER git commit, never touch @REPO@ itself, NEVER call a model, NEVER use the network, NEVER run `wrangler` or deploy anything. Run tests with `cd worker && node --test test/` (no install needed; there are no dependencies).

BACKGROUND. Read `worker/src/index.js` (the `fetch` handler's order of checks, `DailyBudget`, `dailyLimit`, `handleJev`), `worker/src/budget.js` and `worker/test/worker.test.js` (how it fakes the Durable Object namespace and builds requests) first.

@CONTRACT@

BUILD. (a) `BudgetLedger.status()` in `budget.js`: runs through the same serialised `run` queue and returns `{ spent, reserved }` (whole numbers; missing storage values count 0). (b) `DailyBudget.fetch` in `index.js` accepts POST `/status` (no body needed, tolerate an empty or invalid body for this path only) and returns `json(await this.ledger.status())`; its existing `/reserve` and `/settle` behaviour does not change. (c) The Worker's `fetch` handler answers `POST /budget` AFTER the token check and BEFORE any narration, model, price or body-size logic: it gets today's Durable Object exactly the way the reserve path does (`env.DAILY_BUDGET.get(env.DAILY_BUDGET.idFromName(utcDay(new Date())))`), asks `/status`, and returns the contract JSON with `limit_micro_usd` from `dailyLimit(env.DAILY_BUDGET_USD)`, plus the `X-Worker-Revision` header like other successes. Any failure of the counter returns the existing `BUDGET_UNAVAILABLE` 503 error shape. It must not call Workers AI, must not reserve or settle, and must not read the request body as a narration request. Every other route behaves exactly as before, including a non-POST method (405) and an invalid token (401).

TESTS in `worker/test/worker.test.js`, using its existing fakes: `BudgetLedger.status` counts settled spend and open reservations separately and is serialised with a pending reserve; `POST /budget` with the right token returns 200 and the contract fields with `spent_micro_usd` equal to the settled amount after one real narration call through the existing fake; it does NOT spend or change `spent` when called repeatedly; a wrong token gives 401 and a GET gives 405; a missing DAILY_BUDGET binding gives 503 with code `BUDGET_UNAVAILABLE`; a narration request still behaves as before (the existing tests pass unchanged). The whole file passes.

HARD LIMITS. Edit only the three files above. Never edit `wrangler.jsonc`, `models.js`, `package.json`, or anything outside `worker/`. Add no dependencies. Never log or return the token. Write NOTES_16_WORKER.txt (worktree root, never committed) listing every ambiguity and your choice."""

PY_SPEC = """You are a Python engineer. Your current working directory IS a git worktree of @REPO@ (detached at HEAD). Edit files here directly. NEVER git commit, never touch @REPO@ itself, never run `uv`, NEVER call a model, NEVER use the network (tests inject a stub; no test may open a socket), NEVER run npm, playwright or the bench. FIRST run: [ -e .venv ] || ln -s @REPO@/.venv .venv . Ruff: `.venv/bin/python -m ruff check <files>` and `.venv/bin/python -m ruff format <files>` (line length 120, double quotes, Python 3.12, standard library only). Never pass --cov to pytest. Run tests as `PYTHONPATH=$PWD:$PWD/packages/worldkeeper/src TMPDIR=/tmp .venv/bin/python -m pytest -q -p no:cacheprovider -n 0 <test files>`.

BACKGROUND. `factory/stations/live_playtest.py` is the station 7 handler. After round 15b it records the blind player's OpenAI spend (`_record_player_spend`, one `openai` ledger row per call) and gates before a billed run on the total, the hourly rate, and the `openai` and `cloudflare` daily caps. The narrator's spend on Cloudflare is not recorded, so the `cloudflare` ledger lane is empty and its cap is vacuous. Read `live_playtest.py`, `factory/guard.py` (`SpendLedger`, `Usage`; frozen, never edit it) and `tests/test_factory_live_playtest.py` first.

@CONTRACT@

BUILD. (1) New module `factory/cloudflare_spend.py`, standard library only: `read_worker_budget(environment=None, *, fetch=None) -> dict | None`. It reads `CLOUDFLARE_WORKER_URL` and `CLOUDFLARE_WORKER_TOKEN` from the environment mapping (default `os.environ`), builds `<scheme>://<host>/budget` from the URL's origin (the configured URL may carry a path; drop it), POSTs `{}` with the bearer token and a 10 second timeout through `fetch` (an injectable callable `(url, token, timeout) -> (status, text)`; the default uses `urllib.request`), and returns the validated contract dict, or None for anything else: missing configuration, network error, non-200, non-JSON, `status != "ok"`, a missing or non-integer or negative field, a `day` that is not YYYY-MM-DD. It never raises, never logs and never returns the token. (2) `spend_between(before, after) -> int | None`: the micro-dollars spent between two readings: `after.spent - before.spent` when both are readings on the SAME `day` and the difference is >= 0; None when either is None, the days differ (the counter reset at 00:00 UTC, so the part before midnight is unknowable), or the difference is negative. (3) Station 7: `live_playtest_handler` gets an injectable `read_budget` argument (default `read_worker_budget`). Take one reading immediately before the runner is called (after the existing pre-run gate) and one immediately after it returns or raises, on every path that already records the player's spend. Write exactly ONE `cloudflare` ledger row per call: `Usage(at=now, provider="cloudflare", model_id="workers-ai", station="live_playtest", scene=<scene>, ticket_id=<ticket id>, tokens=0, usd=<micro / 1_000_000 as float>, cost_kind="dollars")`, or `cost_kind="unknown"` with `usd=None` when `spend_between` is None. The grade-from-`report_path` path writes no row and takes no reading. Add the narrator's spend to the summary line, for example `cloudflare $0.0021`, or `cloudflare spend unknown`. A failed or missing reading never fails the run or changes its verdict. (4) The handler's other behaviour is unchanged.

TESTS in `tests/test_factory_live_playtest.py` (extend the file; no new test file; tmp_path ledgers; stubs only): `read_worker_budget` returns the dict for a good response, and None for each failure listed above (including a 200 narration-shaped body without `status: "ok"`), never raises, and the token never appears in any return value; the origin is built from a URL with a path; `spend_between` for same day, different day, negative and None; a normal run writes one dollars row with the right usd; a day change between readings writes one unknown row; a reader that returns None writes one unknown row; the report_path grade writes none; a runner that raises still writes the row; the handler's verdict is unaffected by an unreadable budget. Update existing tests so they pass a stub `read_budget` (or unset the two environment variables) and never touch the network or the real environment. New tests run in under 10 seconds.

HARD LIMITS. Edit only the three files above. Never edit `factory/guard.py`, `factory/limits.py`, `factory/config/`, `worker/`, `frontend/`, `storygame/`, `bench/`, or any other file, and add no dependencies. Never print environment values. Write NOTES_16_READER.txt (worktree root, never committed) listing every ambiguity and your choice."""

JS_CHECK = """set -eo pipefail
WORK=@WORK@
mkdir -p "$WORK/out"
git add -A -- worker
bad=$(git diff --cached --name-only | grep -vxF -e worker/src/budget.js -e worker/src/index.js -e worker/test/worker.test.js || true)
[ -z "$bad" ] || { echo "files outside ownership staged: $bad"; exit 1; }
grep -q "/budget" worker/src/index.js || { echo "worker has no /budget route"; exit 1; }
cd worker
start=$(date +%s)
node --test test/
took=$(( $(date +%s) - start ))
echo "worker tests took $took s (budget 30 s)"
[ "$took" -le 30 ] || { echo "worker tests over the 30 s budget"; exit 1; }
probe="$WORK/out/js-probe.out"
node --input-type=module - > "$probe" 2>&1 <<'JS'
import { BudgetLedger } from "./src/budget.js";
const data = new Map();
const storage = { get: async (k) => data.get(k), put: async (k, v) => { data.set(k, v); } };
const ledger = new BudgetLedger(storage);
const a = await ledger.reserve(100, 1000);
const b = await ledger.reserve(50, 1000);
await ledger.settle(a.id, 70);
const s = await ledger.status();
if (s.spent !== 70 || s.reserved !== 50) throw new Error("status wrong: " + JSON.stringify(s));
console.log("probe ok");
JS
cat "$probe"
grep -q "probe ok" "$probe" || { echo "probe failed"; exit 1; }
cd ..
git diff --cached > "$WORK/out/js-worker.patch"
test -s "$WORK/out/js-worker.patch"
"""

PY_CHECK = """set -eo pipefail
WORK=@WORK@
mkdir -p "$WORK/out"
export PYTHONPATH=$PWD:$PWD/packages/worldkeeper/src TMPDIR=/tmp
[ -e .venv ] || ln -s @REPO@/.venv .venv
git add -A -- factory tests
bad=$(git diff --cached --name-only | grep -vxF -e factory/cloudflare_spend.py -e factory/stations/live_playtest.py -e tests/test_factory_live_playtest.py || true)
[ -z "$bad" ] || { echo "files outside ownership staged: $bad"; exit 1; }
if grep -n -i -E "import (openai|anthropic|requests|httpx)|from (openai|anthropic|requests|httpx)" factory/cloudflare_spend.py factory/stations/live_playtest.py; then echo "no model client or http library"; exit 1; fi
start=$(date +%s)
.venv/bin/python -m pytest -q -p no:cacheprovider -n 0 tests/test_factory_live_playtest.py
took=$(( $(date +%s) - start ))
echo "station 7 tests took $took s (budget 20 s)"
[ "$took" -le 20 ] || { echo "station 7 tests over the 20 s budget"; exit 1; }
.venv/bin/python -m pytest -q -p no:cacheprovider -n 0 tests/test_factory_stations.py tests/test_factory_triage.py tests/test_factory_line.py tests/test_factory_guard.py tests/test_factory_preflight.py tests/test_factory_frozen.py
.venv/bin/python -m ruff check factory tests/test_factory_live_playtest.py
.venv/bin/python -m ruff format --check factory/cloudflare_spend.py factory/stations tests/test_factory_live_playtest.py
[ ! -e factory/state/ledger.jsonl ] || { echo "a test wrote factory/state/ledger.jsonl"; exit 1; }
probe="$WORK/out/py-probe.out"
.venv/bin/python - > "$probe" 2>&1 <<'PY'
import json
from factory.cloudflare_spend import read_worker_budget, spend_between
env = {"CLOUDFLARE_WORKER_URL": "https://w.example.workers.dev/narrate", "CLOUDFLARE_WORKER_TOKEN": "sekrit"}
seen = {}
def good(url, token, timeout):
    seen["url"] = url
    return 200, json.dumps({"status": "ok", "day": "2026-11-21", "spent_micro_usd": 2100, "reserved_micro_usd": 0, "limit_micro_usd": 5000000})
r = read_worker_budget(env, fetch=good)
assert r and r["spent_micro_usd"] == 2100 and seen["url"] == "https://w.example.workers.dev/budget", (r, seen)
assert read_worker_budget(env, fetch=lambda u, t, to: (200, json.dumps({"narration": "x"}))) is None
assert read_worker_budget({}, fetch=good) is None
def boom(u, t, to):
    raise OSError("down")
assert read_worker_budget(env, fetch=boom) is None
a = {"day": "2026-11-21", "spent_micro_usd": 1000}
b = {"day": "2026-11-21", "spent_micro_usd": 3500}
assert spend_between(a, b) == 2500 and spend_between(b, a) is None and spend_between(a, {"day": "2026-11-22", "spent_micro_usd": 9}) is None and spend_between(None, b) is None
print("probe ok")
PY
cat "$probe"
grep -q "sekrit" "$probe" && { echo "token leaked into output"; exit 1; }
grep -q "probe ok" "$probe" || { echo "probe failed"; exit 1; }
git diff --cached > "$WORK/out/py-reader.patch"
test -s "$WORK/out/py-reader.patch"
"""


def build() -> dict:
    def fill(text: str) -> str:
        return text.replace("@CONTRACT@", CONTRACT).replace("@REPO@", REPO).replace("@WORK@", WORK)

    def task(key: str, owned: list[str], spec: str, check: str, verified: str, effort: str) -> dict:
        return {
            "key": key,
            "task_type": "code-feature",
            "engine": "codex",
            "engine_args": ["-c", f"model_reasoning_effort={effort}"],
            "max_attempts": 2,
            "timeout_s": 2400,
            "check_timeout_s": 600,
            "ownership": owned,
            "spec": fill(spec),
            "check": fill(check),
            "expect_files": [],
            "verified": verified,
        }

    return {
        "run_name": "factory-cfspend",
        "workdir": WORK,
        "max_parallel": 2,
        "worktrees": True,
        "repo": REPO,
        "tasks": [
            task(
                "js-worker",
                JS_OWNED,
                JS_SPEC,
                JS_CHECK,
                "The Worker answers an authenticated POST /budget with the day's settled and reserved micro-dollars and the limit, spends nothing, and leaves every other route unchanged; worker tests under 30 s; the ledger probe sees spent 70 and reserved 50; three files changed.",
                "medium",
            ),
            task(
                "py-reader",
                PY_OWNED,
                PY_SPEC,
                PY_CHECK,
                "read_worker_budget accepts only a valid ok response and never raises or leaks the token; spend_between is None across a day change; station 7 writes one cloudflare row per billed call (unknown when unreadable) without changing its verdict; tests under 20 s with stubs; ruff clean; real ledger untouched; three files changed.",
                "high",
            ),
        ],
    }


if __name__ == "__main__":
    out = Path(__file__).with_name("round16-cfspend-manifest.json")
    out.write_text(json.dumps(build(), indent=2) + "\n")
    print(out)
