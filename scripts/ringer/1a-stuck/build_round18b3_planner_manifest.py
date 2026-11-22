# ruff: noqa: E501  (spec strings are prose briefs for a worker)
"""Round 18b-3: the planner call for station 4 (Sonnet through the spend guard). FREE to test: no model call, no network.

Tests use recorded and stub `claude` output only; the first real call is a separate, approved smoke (round 18b-4).
One Codex task. Usage: build_round18b3_planner_manifest.py
"""

from __future__ import annotations

import json
from pathlib import Path

REPO = "/home/bcorfman/dev/freytag-forge"
WORK = "/home/bcorfman/dev/ringer-work/factory-planner"

OWNED = [
    "factory/stations/planner.py",
    "factory/stations/wiring.py",
    "factory/stations/__init__.py",
    "tests/test_factory_planner.py",
    "tests/test_factory_wiring.py",
    "tests/fixtures/factory/claude_planner_stream.jsonl",
    "tests/shard_durations.json",
]

SPEC = """You are a Python engineer. Your current working directory IS a git worktree of @REPO@ (detached at HEAD). Edit files here directly. NEVER git commit, never touch @REPO@ itself, never run `uv`, NEVER call a model (not `claude`, not `codex`, not any API), NEVER use the network, NEVER run a real `ringer.py`, npm, playwright or the bench. `claude --help` is allowed (read only). FIRST run: [ -e .venv ] || ln -s @REPO@/.venv .venv . Environment for every command: `export PYTHONPATH=$PWD:$PWD/packages/worldkeeper/src TMPDIR=/tmp`. Ruff: `.venv/bin/python -m ruff check <files>` and `.venv/bin/python -m ruff format <files>` (line length 120, Python 3.12, standard library plus what the repo already uses). Never pass --cov to pytest. Run tests as `.venv/bin/python -m pytest -q -p no:cacheprovider -n 0 <files>`.

BACKGROUND. The dark factory (`factory/`; read `factory/guard.py` (`guarded_call`, `CallResult`, `ModelGuard`, `Caps`, `SpendLedger`, `RateLimited`, `Overloaded`, `ProviderLimit`, `LimitSleep`), `factory/limits.py` (`read_claude_stream`), `factory/config/allowlist.json` and `factory/config/factory.json` (read only), `factory/stations/live_playtest.py` (how it builds `Caps`, the ledger and the guard from config), `factory/stations/fix_plan.py` (`build_evidence`, `lint_plan`, the plan format), `factory/stations/wiring.py`, `factory/stations/__init__.py` and `tests/fixtures/factory/claude_stream.jsonl` (a real recorded `claude -p --output-format stream-json --verbose` stream) first) has a station 4 wiring handler that needs a plan in its ticket payload. You build the PLANNER: the call that has Claude Sonnet read the evidence packet and propose ONE fix plan, under the spend guard, with the deterministic lint as the only judge.

BUILD `factory/stations/planner.py` (story-agnostic: no character names, fact ids or scene ids):
(1) `PLANNER_BRIEF`: the fixed instruction text sent to the model. It states the role (a story-data fixer for an interactive-fiction engine), that exactly ONE fix is wanted from the two kinds in the evidence's `fix_menu`, the plan JSON format (embed the exact key names and types from `fix_plan.py`), the decision rules the lint enforces (beat id pattern, a turn inside the scene window and before the handoff, facts must be declared, a beat may not set an exit trigger, text 20 to 600 characters in plain words with no ids or braces, evidence_keys taken from the failing turns), that the planner must prefer the smallest change that would have let the failing turns succeed, that timing and wording are its decision (nobody will be asked), and that it must reply with ONE JSON object and nothing else. Write the brief at a 12th grade reading level, one idea per sentence.
(2) `build_prompt(evidence: dict, problems: list[str] | None = None, previous_plan: dict | None = None) -> str`: the brief, then the evidence as compact JSON, then, on a retry, the previous plan and the lint problems verbatim (verdicts only; never add explanations of why a rule exists).
(3) `extract_plan(text: str) -> dict | None`: find the first balanced top-level JSON object in the text (tolerate a ```json fence and surrounding prose) and return it as a dict, else None.
(4) `claude_call(prompt: str, *, model_id: str, effort: str, run=subprocess.run, timeout: int = 900) -> CallResult`: runs headless Claude Code with the prompt on stdin: `claude -p --model <model_id> --effort <effort> --output-format stream-json --verbose` plus the minimal flags that make the call read-only and tool-free (read `claude --help`; at least no tools and no slash commands; do not use any flag whose value you cannot verify from the help text, and list your choices in the notes). Parse the stream: the answer text is the `result` event's `result` string when present, otherwise the concatenated text blocks of the assistant events; `tokens` is input plus output tokens from the `result` event's usage (cache tokens excluded, say so in a comment); `usd` is `total_cost_usd` (the guard records it as the list price for a subscription lane); `limits` is `read_claude_stream` over the stream lines. Errors: a non-zero exit whose output contains a 429 or "rate limit" raises `RateLimited`; one that says overloaded raises `Overloaded`; a `rate_limit_event` with a rejected window, or text saying a usage limit was reached, raises `ProviderLimit` carrying the report; any other failure raises `RuntimeError` with the tail of the output. Never log or return environment values.
(5) `make_planner(*, guard, ledger, caps, run=subprocess.run, sleep=time.sleep, max_attempts: int = 3, model_id="claude-sonnet-5-5", effort="high")` returns `planner(ticket, package, now) -> PlanOutcome` where `PlanOutcome` is a dataclass `(plan: dict | None, tokens: int, problems: list[str], attempts: int)`. It builds the evidence with `build_evidence(ticket.payload, package)`, then loops up to `max_attempts` times: calls `guarded_call(guard=..., ledger=..., caps=..., station="wiring", model_id=..., effort=..., scene=ticket.scene, ticket_id=ticket.id, now=now, fn=lambda: claude_call(prompt, ...), sleep=sleep)`; extracts a plan; if none, records the problem `plan.shape no JSON object in the reply` and retries; sets `plan["ticket_id"] = ticket.id` and `plan["scene"] = ticket.scene` deterministically before linting (so a trivial id slip never costs an attempt); runs `lint_plan`; a clean plan returns at once; otherwise the next prompt carries the problems. It stops early when the summed tokens pass `ticket.token_budget` (read how the ticket stores it). `LimitSleep`, `BudgetExhausted` and `ModelNotAllowed` propagate unchanged (the line handles them). Returns `PlanOutcome(plan=None, ...)` with the last problems when attempts run out.
(6) `default_planner(root=None)`: builds `ModelGuard.from_file`, `Caps.from_dict` and the `SpendLedger` from the repository's config files exactly as `live_playtest.py` does, and returns `make_planner(...)`.
`factory/stations/wiring.py`: add an optional `planner` argument to `wiring_handler`. When the payload has no `plan` and a planner was given, call it (`planner(ticket, package, now)`), put the returned plan into the working payload used for the rest of the handler, add its `tokens` to the `StationResult.tokens`, and when it returns no plan fail with `StationResult(False, "wiring", <problems, one per line>, tokens=...)`. When the payload already has a `plan`, behave exactly as today and never call the planner. Never mutate `ticket.payload`. Persist the accepted plan to `<workspace>/<safe id>/plan.json` as it already does.
`factory/stations/__init__.py`: `build_handlers(root)` registers wiring with `planner=default_planner(root)` built lazily (construct it on first use, not at import time, so building the handlers never reads the ledger or needs `claude`), and keeps every other handler as is.

TESTS (hermetic: no model, no network, no real `claude`; every `run` is a stub). New `tests/test_factory_planner.py`, plus a new fixture `tests/fixtures/factory/claude_planner_stream.jsonl` that is a trimmed copy of the shape in `claude_stream.jsonl` whose assistant text and `result` string contain a fenced plan JSON for a scene's `add_pacing_beat`: `build_prompt` carries the brief, the evidence and, on a retry, the problems verbatim and nothing else; `extract_plan` on a bare object, a fenced object, an object with surrounding prose, two objects (first wins), nested braces inside strings, and garbage (None); `claude_call` with a stub `run`: parses the fixture into the right text, tokens, usd and limits, builds the expected argv (model, effort, stream-json, verbose, tool-free) and passes the prompt on stdin, maps 429 text to `RateLimited`, overloaded text to `Overloaded`, a rejected window to `ProviderLimit`, and other failures to `RuntimeError`; `make_planner` with a stub `claude` returning (a) a clean plan first try, (b) garbage then a clean plan (two ledger rows, attempts 2), (c) a plan that fails lint then a fixed one (the second prompt contains the problems), (d) three bad replies (plan None, problems from the last attempt), (e) the token budget cut-off; an unpinned model raises `ModelNotAllowed` before any call; the ledger gets one `subscription` row per call with the list price in `list_usd`; the real default story is used for `lint_plan`. In `tests/test_factory_wiring.py` add: with no plan in the payload and a stub planner the handler uses the planner's plan, writes plan.json and reaches the same result as the existing happy path; a planner returning no plan fails the station with the problems and creates no tree; a payload with a plan never calls the planner. The planner test file runs in under 15 seconds. Update `tests/shard_durations.json` for the new test file with `.venv/bin/python scripts/regen_shard_durations.py --missing-only` (read its usage first; keep the diff to the one new entry).

HARD LIMITS. Edit only the owned files: @OWNED@. Never edit `factory/config/`, `factory/checks/`, `factory/guard.py`, `factory/limits.py`, `factory/manifests.py`, `factory/line.py`, `factory/tickets.py`, `factory/stations/fix_plan.py`, story data, `storygame/` or any other test. No model client or network library in the module (the only external call is the `claude` subprocess through the injectable `run`). Write NOTES_18B3.txt (worktree root, never committed) listing every ambiguity and your choice."""

CHECK = """set -eo pipefail
WORK=@WORK@
mkdir -p "$WORK/out"
export PYTHONPATH=$PWD:$PWD/packages/worldkeeper/src TMPDIR=/tmp
[ -e .venv ] || ln -s @REPO@/.venv .venv
git add -A -- factory tests
bad=$(git diff --cached --name-only | grep -vxF @ALLOW_ARGS@ || true)
[ -z "$bad" ] || { echo "files outside ownership staged: $bad"; exit 1; }
n=$(git diff --cached -U0 -- tests/shard_durations.json | grep -E '^[+-][^+-]' | grep -vc 'test_factory_planner' || true)
[ "${n:-0}" -le 2 ] || { echo "shard_durations diff is more than the one new entry"; exit 1; }
if grep -n -i -E "michelle|kristin|memory_card|laptop|continuity|1A\\b" factory/stations/planner.py; then echo "story-specific word in planner.py"; exit 1; fi
if grep -n -i -E "import (openai|anthropic|requests|httpx)|from (openai|anthropic|requests|httpx)|urllib.request|socket" factory/stations/planner.py; then echo "no model client or network library in planner.py"; exit 1; fi
start=$(date +%s)
.venv/bin/python -m pytest -q -p no:cacheprovider -n 8 tests/test_factory_planner.py tests/test_factory_wiring.py tests/test_factory_stations.py tests/test_factory_fix_plan.py tests/test_factory_guard.py tests/test_factory_line.py tests/test_factory_frozen.py tests/test_factory_preflight.py
took=$(( $(date +%s) - start ))
echo "factory tests took $took s (budget 150 s)"
[ "$took" -le 150 ] || { echo "over the 150 s budget"; exit 1; }
start=$(date +%s)
.venv/bin/python scripts/quick_suite.py
took=$(( $(date +%s) - start ))
echo "quick suite took $took s (baseline 157 s, budget 450 s)"
[ "$took" -le 450 ] || { echo "quick suite over the 450 s budget"; exit 1; }
.venv/bin/python -m ruff check factory/stations tests/test_factory_planner.py tests/test_factory_wiring.py
.venv/bin/python -m ruff format --check factory/stations tests/test_factory_planner.py tests/test_factory_wiring.py
[ ! -e factory/state/ledger.jsonl ] || { echo "a test wrote factory/state/ledger.jsonl"; exit 1; }
git diff --cached > "$WORK/out/planner.patch"
test -s "$WORK/out/planner.patch"
"""


def build() -> dict:
    allow_args = " ".join(f"-e {path}" for path in OWNED)

    def fill(text: str) -> str:
        return (
            text.replace("@REPO@", REPO)
            .replace("@WORK@", WORK)
            .replace("@OWNED@", ", ".join(OWNED))
            .replace("@ALLOW_ARGS@", allow_args)
        )

    return {
        "run_name": "factory-planner",
        "workdir": WORK,
        "max_parallel": 1,
        "worktrees": True,
        "repo": REPO,
        "tasks": [
            {
                "key": "planner",
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
                "verified": "make_planner calls Sonnet only through guarded_call with the wiring pin, retries with lint verdicts, stops on token budget, records one subscription row per call; claude_call parses the recorded stream and maps limit errors; wiring_handler uses the planner only when the payload has no plan; tests use stubs only; module story-agnostic; quick suite green.",
            }
        ],
    }


if __name__ == "__main__":
    out = Path(__file__).with_name("round18b3-planner-manifest.json")
    out.write_text(json.dumps(build(), indent=2) + "\n")
    print(out)
