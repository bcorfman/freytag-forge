# ruff: noqa: E501  (spec strings are prose briefs for a worker)
"""Round 11c-1: readers for the two subscription limit reports (Claude stream rate_limit_event, Codex session-log rate_limits).

One Codex task, free, no model call. Usage: build_round11c1_manifest.py
"""

from __future__ import annotations

import json
from pathlib import Path

REPO = "/home/bcorfman/dev/freytag-forge"
WORK = "/home/bcorfman/dev/ringer-work/factory-limits"

OWNED = [
    "factory/limits.py",
    "tests/test_factory_limits.py",
    "tests/fixtures/factory/claude_stream.jsonl",
    "tests/fixtures/factory/codex_session.jsonl",
]

CLAUDE_FIXTURE = """{"type": "system", "subtype": "init", "session_id": "s1", "model": "claude-haiku-5-5"}
{"type": "assistant", "message": {"content": [{"type": "text", "text": "ok"}]}, "session_id": "s1"}
{"type": "rate_limit_event", "rate_limit_info": {"status": "allowed", "resetsAt": 1795138200, "rateLimitType": "five_hour", "overageStatus": "allowed", "overageResetsAt": 1796083200, "isUsingOverage": false, "unifiedWindows": {"five_hour": {"utilization": 0.1, "resetsAt": 1795138200, "status": "allowed"}, "seven_day": {"utilization": 0.19, "resetsAt": 1795442400, "status": "allowed"}}}, "uuid": "u1", "session_id": "s1"}
{"type": "result", "subtype": "success", "total_cost_usd": 0.00282399, "usage": {"input_tokens": 2, "output_tokens": 4, "cache_read_input_tokens": 9719, "cache_creation_input_tokens": 13623}, "modelUsage": {"claude-haiku-5-5": {"costUSD": 0.00282399, "costBasis": "list"}}, "session_id": "s1"}
"""

CODEX_FIXTURE = """{"timestamp": "2026-11-20T00:48:35.817Z", "ordinal": 0, "type": "session_meta", "payload": {"session_id": "01a1f66d-3849-7850-bf3f-582d9466d5e6", "id": "01a1f66d-3849-7850-bf3f-582d9466d5e6"}}
{"timestamp": "2026-11-20T00:48:39.798Z", "ordinal": 12, "type": "event_msg", "payload": {"type": "token_count", "info": {"total_token_usage": {"input_tokens": 14161, "cached_input_tokens": 10240, "output_tokens": 5, "reasoning_output_tokens": 0, "total_tokens": 14166}}, "rate_limits": {"limit_id": "codex", "limit_name": null, "primary": {"used_percent": 4.0, "window_minutes": 300, "resets_at": 1795144042}, "secondary": {"used_percent": 6.0, "window_minutes": 10080, "resets_at": 1795664398}, "credits": {"has_credits": true, "unlimited": false, "balance": "211.7238347500"}, "individual_limit": null, "spend_control_reached": null, "plan_type": "plus", "rate_limit_reached_type": null}}}
"""

SPEC = f"""You are a Python engineer. Your current working directory IS a git worktree of {REPO} (detached at HEAD). Edit files here directly. NEVER git commit, never touch {REPO} itself, never run `uv`, never call a model, never run `claude` or `codex`, never use the network, never read anything under the real home directory (`~/.codex`, `~/.claude`). FIRST run: [ -e .venv ] || ln -s {REPO}/.venv .venv . Ruff: `.venv/bin/python -m ruff check <files>` and `.venv/bin/python -m ruff format <files>` (line length 120, double quotes, Python 3.12, standard library only). Never pass --cov to pytest. Run tests as `PYTHONPATH=$PWD:$PWD/packages/worldkeeper/src TMPDIR=/tmp .venv/bin/python -m pytest -q -p no:cacheprovider -n 0 <test files>`.

BACKGROUND. The dark factory (`factory/`) calls two subscription model providers, Claude Code (Opus, Sonnet; `claude -p --output-format stream-json --verbose`) and Codex (Luna; `codex exec --json`, ChatGPT Plus plan). Neither costs dollars per call; each has a five-hour window and a weekly window, and reports how much of each is used. The factory must read those reports so it can sleep a provider's lane until its window resets, and stop if paid usage ever appears. This task builds ONLY the pure readers and the decision helpers, in a new module `factory/limits.py`. Nothing else in `factory/` changes in this task; a later task wires these into `factory/guard.py`.

The two report formats (real samples, captured 2026-11-19):
- Claude: one stream-json line per event. The line with `"type": "rate_limit_event"` holds `rate_limit_info`, whose `unifiedWindows` maps a window name (`five_hour`, `seven_day`; treat any other key the same way) to `{{"utilization": 0.19, "resetsAt": <epoch seconds>, "status": "allowed" | "allowed_warning" | "rejected"}}`. `utilization` is a fraction (0.19 means 19 percent). `rate_limit_info.isUsingOverage` is true when the account is drawing paid extra usage. A stream can hold several rate_limit_event lines; the last one wins. Other lines (system, assistant, result) and non-JSON lines are ignored.
- Codex: the session log of a run is `<sessions_root>/YYYY/MM/DD/rollout-<timestamp>-<thread_id>.jsonl` (sessions_root is normally `~/.codex/sessions`). Lines whose `payload` has a `rate_limits` object carry `primary` and `secondary` windows, each `{{"used_percent": 4.0, "window_minutes": 300, "resets_at": <epoch seconds>}}` (`used_percent` is a percentage, 4.0 means 4 percent), and `credits` `{{"has_credits": true, "unlimited": false, "balance": "211.7238347500"}}` (balance is a decimal STRING; it may be missing or null). Either window may be null. The last line with `rate_limits` wins.

YOUR TASK. Create exactly these four files and nothing else.

1. `tests/fixtures/factory/claude_stream.jsonl`, with exactly this content:
{CLAUDE_FIXTURE}
2. `tests/fixtures/factory/codex_session.jsonl`, with exactly this content:
{CODEX_FIXTURE}
3. `factory/limits.py` with:
- `@dataclass(frozen=True) class Window`: `name: str`, `used: float` (fraction 0 to 1; Codex `used_percent / 100`), `resets_at: datetime | None` (timezone-aware UTC, from epoch seconds; None when missing), `rejected: bool` (Claude: `status == "rejected"`; Codex: `used >= 1.0`). Codex window names are `five_hour` for `primary` and `seven_day` for `secondary`, so both providers use the same names; keep `window_minutes` out of the type.
- `@dataclass(frozen=True) class LimitReport`: `provider: str`, `windows: tuple[Window, ...]` (sorted by name), `overage: bool | None` (Claude `isUsingOverage`; None for Codex), `credits: float | None` (Codex balance as float; None for Claude or when missing).
- `read_claude_stream(lines: Iterable[str], provider: str = "claude_code") -> LimitReport | None`: the last rate_limit_event, or None when there is none. A window with a missing or non-numeric utilization is skipped.
- `find_codex_session(thread_id: str, sessions_root: Path) -> Path | None`: the file under sessions_root (any depth) whose name ends with `-<thread_id>.jsonl`; None when missing; if several match, the most recently modified.
- `read_codex_session(path: Path, provider: str = "codex") -> LimitReport | None`: the last line with `payload.rate_limits`; None when the file has none. Malformed lines are skipped, never raised.
- `@dataclass(frozen=True) class SleepDecision`: `sleep: bool`, `until: datetime | None`, `reason: str`.
- `window_sleep(report: LimitReport, ceilings: dict[str, float]) -> SleepDecision`: a window is hit when it is rejected, or when its name is in `ceilings` and `used >= ceilings[name]` (ceilings are fractions). No hit gives `SleepDecision(False, None, "")`. Otherwise sleep until the LATEST `resets_at` among the hit windows (the lane must wait for all of them); if any hit window has no `resets_at`, `until` is None (the caller probes). The reason names each hit window, its use as a percentage and its reset, for example `seven_day 91% >= ceiling 90%, resets 2026-11-23T04:00:00+00:00`, joined with `; `.
- `paid_usage(before: LimitReport | None, after: LimitReport) -> str | None`: a reason when `after.overage` is True (`"<provider> reports paid overage in use"`), or when both reports have `credits` and `after.credits < before.credits` (`"<provider> credits dropped from X to Y"`); otherwise None. A missing `before` never trips on credits.
- A module docstring, and short docstrings on the public functions.
4. `tests/test_factory_limits.py`, hermetic (tmp_path only): read_claude_stream on the fixture (two windows, used 0.1 and 0.19, resets_at as aware UTC datetimes equal to the epoch values, overage False, credits None); last event wins when two are present; no event gives None; non-JSON lines ignored; a `rejected` status sets rejected. read_codex_session on the fixture (five_hour 0.04, seven_day 0.06, credits 211.72383475, overage None); a null secondary window; a missing or null balance; malformed lines skipped; 100 percent used sets rejected. find_codex_session with nested date directories in tmp_path, a missing id, two matches. window_sleep: below ceiling, at ceiling, rejected without a ceiling, two hits sleeping to the later reset, a hit with no reset giving until None, the reason text naming the window and percentage. paid_usage: overage true, credits drop, credits equal, credits rise, missing before.

HARD LIMITS. Create only the four files above. Never edit any existing file. Do not add dependencies. Write NOTES_11c1.txt (worktree root, never committed) listing every rule you found ambiguous and the choice you made.
"""

CHECK = f"""set -eo pipefail
WORK={WORK}
mkdir -p "$WORK"
export PYTHONPATH=$PWD:$PWD/packages/worldkeeper/src TMPDIR=/tmp
[ -e .venv ] || ln -s {REPO}/.venv .venv
git add -A -- factory tests
bad=$(git diff --cached --name-only | grep -vxF -e factory/limits.py -e tests/test_factory_limits.py -e tests/fixtures/factory/claude_stream.jsonl -e tests/fixtures/factory/codex_session.jsonl || true)
[ -z "$bad" ] || {{ echo "files outside ownership staged: $bad"; exit 1; }}
for f in factory/limits.py tests/test_factory_limits.py; do [ -s "$f" ] || {{ echo "missing $f"; exit 1; }}; done
.venv/bin/python -m pytest -q -p no:cacheprovider -n 0 tests/test_factory_limits.py
.venv/bin/python -m ruff check factory/limits.py tests/test_factory_limits.py
.venv/bin/python -m ruff format --check factory/limits.py tests/test_factory_limits.py
# independent probe against the fixtures and hand-built reports
.venv/bin/python - <<'PY'
import json
from datetime import UTC, datetime
from pathlib import Path
from factory.limits import LimitReport, Window, find_codex_session, paid_usage, read_claude_stream, read_codex_session, window_sleep

c = read_claude_stream(Path("tests/fixtures/factory/claude_stream.jsonl").read_text().splitlines())
w = {{x.name: x for x in c.windows}}
assert set(w) == {{"five_hour", "seven_day"}}, w
assert abs(w["seven_day"].used - 0.19) < 1e-9 and w["seven_day"].resets_at == datetime.fromtimestamp(1795442400, UTC), w
assert c.overage is False and c.credits is None and not any(x.rejected for x in c.windows), c
assert read_claude_stream(["not json", json.dumps({{"type": "result"}})]) is None
x = read_codex_session(Path("tests/fixtures/factory/codex_session.jsonl"))
xw = {{v.name: v for v in x.windows}}
assert abs(xw["five_hour"].used - 0.04) < 1e-9 and abs(xw["seven_day"].used - 0.06) < 1e-9, xw
assert abs(x.credits - 211.72383475) < 1e-6 and x.overage is None, x
t1, t2 = datetime(2026, 11, 20, tzinfo=UTC), datetime(2026, 11, 25, tzinfo=UTC)
r = LimitReport("claude_code", (Window("five_hour", 0.95, t1, False), Window("seven_day", 0.5, t2, True)), False, None)
d = window_sleep(r, {{"five_hour": 0.9}})
assert d.sleep and d.until == t2 and "five_hour" in d.reason and "seven_day" in d.reason, d
d = window_sleep(r, {{"five_hour": 0.99}})
assert d.sleep and d.until == t2 and "five_hour" not in d.reason, d
ok = LimitReport("codex", (Window("five_hour", 0.2, t1, False),), None, 10.0)
assert window_sleep(ok, {{"five_hour": 0.9}}).sleep is False
assert window_sleep(LimitReport("codex", (Window("seven_day", 1.0, None, True),), None, None), {{}}).until is None
assert paid_usage(ok, LimitReport("codex", ok.windows, None, 9.5)) is not None
assert paid_usage(ok, ok) is None and paid_usage(None, ok) is None
assert paid_usage(None, LimitReport("claude_code", (), True, None)) is not None
import tempfile
root = Path(tempfile.mkdtemp())
p = root / "2026" / "11" / "19" / "rollout-2026-11-19T19-48-35-abc-123.jsonl"
p.parent.mkdir(parents=True)
p.write_text("")
assert find_codex_session("abc-123", root) == p and find_codex_session("zzz", root) is None
print("probe ok")
PY
git diff --cached > {WORK}/limits.patch
test -s {WORK}/limits.patch
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
                "key": "limit-readers",
                "task_type": "code-feature",
                "engine": "codex",
                "engine_args": ["-c", "model_reasoning_effort=medium"],
                "max_attempts": 2,
                "timeout_s": 1800,
                "check_timeout_s": 300,
                "ownership": OWNED,
                "spec": SPEC,
                "check": CHECK,
                "expect_files": [],
                "verified": "Limit reader tests green; probe parses both real-format fixtures, decides sleeps to the latest reset, flags overage and credit drops; ruff clean; only four new files.",
            }
        ],
    }


if __name__ == "__main__":
    out = Path(__file__).with_name("round11c1-manifest.json")
    out.write_text(json.dumps(build(), indent=2) + "\n", encoding="utf-8")
    print(out)
