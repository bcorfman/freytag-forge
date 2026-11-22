# ruff: noqa: E501  (spec strings are prose briefs for a worker)
"""Round 18e: a fun review station (Opus) between the prompt snapshot and delivery. FREE: no model call, no network.

One Codex task. The new station reads the diff a factory fix made and asks Opus three fixed questions about whether the
scene is still fun; a block keeps the fix from merging. Usage: build_round18e_fun_review_manifest.py
"""

from __future__ import annotations

import json
from pathlib import Path

REPO = "/home/bcorfman/dev/freytag-forge"
WORK = "/home/bcorfman/dev/ringer-work/factory-fun-review"

OWNED = [
    "factory/stations/fun_review.py",
    "factory/stations/__init__.py",
    "factory/line.py",
    "factory/tickets.py",
    "factory/config/allowlist.json",
    "tests/test_factory_fun_review.py",
    "tests/test_factory_line.py",
    "tests/test_factory_stations.py",
    "tests/test_factory_tickets.py",
    "tests/test_factory_guard.py",
    "tests/test_factory_preflight.py",
    "tests/shard_durations.json",
]

ALLOW_RE = (
    "^(factory/stations/fun_review\\.py|factory/stations/__init__\\.py|factory/line\\.py|factory/tickets\\.py|"
    "factory/config/allowlist\\.json|tests/test_factory_[a-z0-9_]+\\.py|tests/shard_durations\\.json)$"
)

SPEC = """You are a Python engineer. Your current working directory IS a git worktree of @REPO@ (detached at HEAD). Edit files here directly. NEVER git commit, never touch @REPO@ itself, never run `uv`, NEVER call a model (not `claude`, not `codex`), NEVER use the network, NEVER run a real `ringer.py`, `gh` or `git push`. FIRST run: [ -e .venv ] || ln -s @REPO@/.venv .venv . Environment for every command: `export PYTHONPATH=$PWD:$PWD/packages/worldkeeper/src TMPDIR=/tmp`. Ruff: `.venv/bin/python -m ruff check <files>` and `.venv/bin/python -m ruff format <files>` (line length 120, Python 3.12). Never pass --cov to pytest. Run tests as `.venv/bin/python -m pytest -q -p no:cacheprovider -n 0 <files>`.

BACKGROUND. The story factory is a Python state machine (`factory/line.py`, `factory/tickets.py`) with fixed stations. A ticket that carries `merge_to_main: True` runs stations 4 (wiring), 5 (free gates), 6 (prompt snapshot), then 9 (deliver: opens a pull request, waits for CI, merges, waits for staging), then 7. Read `factory/stations/deliver.py` (helpers `_changed_paths`, `_diff_hash`, `_atomic_json_write`, `_record`, the per-ticket tree from `factory/stations/tree.py` `ticket_tree`, and the idempotent `delivery.json` record), `factory/stations/planner.py` (`claude_call`, `make_planner`, `default_planner`: the guarded Claude call, and how it builds the guard, ledger and caps from the config files) and `factory/guard.py` (`guarded_call`, `ModelGuard`) first. Today nothing checks that a fix leaves the scene fun. You add a review station that asks Opus.

BUILD 1, the enum: in `factory/tickets.py` add `FUN_REVIEW = 10` to the `Station` enum (do NOT renumber any station).

BUILD 2, routing: in `factory/line.py`, for a ticket with `merge_to_main: True`, a PASSED station 6 now goes to `FUN_REVIEW` instead of `DELIVER`, and a PASSED `FUN_REVIEW` goes to `DELIVER`. A failed `FUN_REVIEW` takes the ordinary failure path (`record_failure`). Every other route is unchanged (a ticket without `merge_to_main` behaves exactly as today).

BUILD 3, config: in `factory/config/allowlist.json` add a station key `fun_review` pinned to `claude-opus-5-5` at effort `medium` on provider `claude_code` (the same shape as `act_contracts`). Touch nothing else in that file.

BUILD 4, the station, new file `factory/stations/fun_review.py`, story-agnostic (no story names, places, characters or facts in it):
`fun_review_handler(root: Path | None = None, *, reviewer: Callable[[Any, str, datetime], ReviewReply] | None = None, runner=None) -> StationHandler`, and `default_reviewer(root=None)` built like `default_planner` (guard from the allowlist file, ledger, caps from `factory/config/factory.json`) that calls `claude_call` from `factory/stations/planner.py` through `guarded_call` with `station="fun_review"`, `model_id="claude-opus-5-5"`, `effort="medium"`. `ReviewReply` is a small frozen dataclass `(text: str, tokens: int)`. The handler resolves `default_reviewer` lazily on first use, so building the handler never reads config or calls a model.
The handler, in order:
 (a) fail with the message `ticket is not authorized to merge to main` unless the payload has `merge_to_main` True; fail with `missing payload key: workspace` when `workspace` is not a string; fail with `ticket tree not found` when `ticket_tree(...)` is None.
 (b) list the changed paths with the same helper station 9 uses; an error fails with its message; an empty list fails with `empty diff against origin/main`. Compute the content hash with the same `_diff_hash` helper.
 (c) idempotency: a record file `<workspace>/<safe ticket id>/review.json` (use `_safe_id` as deliver does) holds `{diff_hash, verdict, reasons, checks, reviewed_at}`. When the saved `diff_hash` equals the current one, REUSE the saved verdict and make NO reviewer call. A different hash reviews again and overwrites the file (atomic write).
 (d) the packet (a prompt string, built by a pure function `build_review_prompt(...)` so tests can read it): the fixed constant `FUN_REVIEW_BRIEF` first, then the scene id, then an optional criteria text, then the failing-turn evidence, then the diff. The brief is plain words at a 12th grade reading level and says: you are the story editor for an interactive-fiction game whose scenes must stay fun; a fix was just made to the story data to repair turns where players got stuck; read the diff and judge it; answer three fixed yes/no questions: `fits_scene` (does the new or changed text fit the scene's tone and only what the player knows at that point, with no contradiction of the nearby text shown), `gives_a_reason_to_act` (does it give the player a clue, a hook or a choice, rather than filler or a dead end), `keeps_pace` (does it avoid adding dead time, stacking two pressure moments within two turns of each other, or giving away a later reveal); reply with ONE JSON object and nothing else: {"verdict": "pass" or "block", "checks": {"fits_scene": true, "gives_a_reason_to_act": true, "keeps_pace": true}, "reasons": "one to three plain sentences"}; block when any answer is no; a fix that only moves words around without a reason is a block. Criteria text: read the file named by payload `review_criteria_path` (relative to the ticket tree, or absolute) when it exists, truncated to 6000 characters; absent or unreadable means no criteria section. Evidence: from payload `failing_turns` (list of packets) the first 12, each as `key`, `player_input` and `narration` cut to 200 characters; plus the `reason` string of `<workspace>/<safe ticket id>/plan.json` when that file holds one. Diff: `git diff -U30 <merge-base with origin/main> -- <changed paths>` run in the ticket tree through the runner (untracked changed files are appended in full), capped at 16000 characters; when cut, end with the line `[diff cut at 16000 characters]`.
 (e) call the reviewer with `(ticket, prompt, now)`. Extract the first parseable JSON object from the reply text (reuse `extract_plan` from `factory/stations/planner.py`). The result is a PASS only when the object has `verdict` equal to `pass` AND `checks` is a dict whose three keys are all exactly `True` AND `reasons` is a non-empty string. Anything else with a well-formed object is a BLOCK. A reply with no parseable object, or a malformed one (verdict missing or not pass/block, checks missing), counts as a failed attempt: ask once more (the second prompt is the same prompt plus a final line `Your last reply was not valid. Reply with the JSON object only.`), and if the second reply is also invalid FAIL CLOSED with the check `fun_review` and the message `no usable verdict from the reviewer`; save no record in that case. At most 2 reviewer calls per handler run. Sum the tokens of every call into `StationResult.tokens`.
 (f) the result: PASS returns `StationResult(True, "fun_review", <the reasons>, tokens=..., payload_updates={"fun_review": {"verdict": "pass", "diff_hash": ..., "reasons": ...}})`. A block returns `StationResult(False, "fun_review", "fun review blocked the fix: " + reasons, tokens=...)` and saves the record (so a retry makes no new call and blocks again at no cost). `LimitSleep`, `BudgetExhausted` and `ModelNotAllowed` from the reviewer propagate unchanged. Redact secrets in messages the way deliver does (`_one_line`).
 (g) register the station in `factory/stations/__init__.py` `build_handlers` as `Station.FUN_REVIEW`; keep the registry's key enumeration for older callers stable the way it is already done for the other late stations (read the `_HandlerRegistry` comment) and fix any old test that enumerates stations, minimally.

TESTS (hermetic; stubs only, no model, no network, no real gh or git push; a real temporary git repo with an `origin/main` ref is fine for tree and diff tests, the way `tests/test_factory_deliver.py` does it). New `tests/test_factory_fun_review.py`: (1) pass: all three checks true gives a passed result, payload_updates carry the verdict, `review.json` holds the diff hash, the reviewer ran once and its prompt contains the brief, the scene id, the criteria text, an evidence key and the diff text; (2) block: verdict block fails with the reasons in the output and tokens counted; (3) fail closed: verdict `pass` with one check false is a block; (4) a reply with no JSON twice fails with `no usable verdict from the reviewer` after exactly 2 calls, and the second prompt ends with the retry line; garbage then a valid reply passes with tokens summed; (5) idempotency: a second handler run on the same tree makes no reviewer call and returns the same outcome, including a saved block; changing a changed file makes a new call; (6) a huge diff is cut at 16000 characters with the marker line; (7) not merge_to_main, missing workspace, no tree, empty diff all fail with the exact messages and make no reviewer call; (8) `LimitSleep` from the reviewer propagates and saves nothing; (9) `default_reviewer` with a stub `run` that returns the shape of `tests/fixtures/factory/claude_planner_stream.jsonl` (copy it to a new fixture if you need a different text): the call goes through the guard pin for `fun_review`, writes one `subscription` ledger row with station `fun_review`, and with the model swapped for a Sonnet id raises `ModelNotAllowed` before any call (use temporary copies of the config, never the real ledger); and the real `factory/config/allowlist.json` pins `claude-opus-5-5` medium for `fun_review`. In `tests/test_factory_line.py` add: a `merge_to_main` ticket passed at station 6 lands on `FUN_REVIEW`, passed there lands on `DELIVER`, a failed `FUN_REVIEW` records a failure and stays at station 10, and a ticket without `merge_to_main` still goes 6 to 7. Update any existing factory test that the new enum member or the allowlist key legitimately changes (you may edit any `tests/test_factory_*.py` and `tests/shard_durations.json` for that, and nothing else). Add the new test file to `tests/shard_durations.json` with `.venv/bin/python scripts/regen_shard_durations.py --missing-only` (read its usage first; keep that diff to the one new entry). The new test file runs in under 15 seconds.

HARD LIMITS. Edit only: @OWNED@ (plus an existing `tests/test_factory_*.py` only where the new enum member or allowlist key forces it). Never edit other `factory/config/` files, `factory/guard.py`, `factory/stations/deliver.py`, `factory/stations/planner.py`, story data or `storygame/`. Never mutate `ticket.payload` inside the handler. Write NOTES_18E.txt (worktree root, never committed) listing every ambiguity and your choice."""

CHECK = """set -eo pipefail
WORK=@WORK@
mkdir -p "$WORK/out"
export PYTHONPATH=$PWD:$PWD/packages/worldkeeper/src TMPDIR=/tmp
[ -e .venv ] || ln -s @REPO@/.venv .venv
test -f factory/stations/fun_review.py || { echo "factory/stations/fun_review.py missing"; exit 1; }
git add -A -- factory tests
bad=$(git diff --cached --name-only | grep -vE '@ALLOW_RE@' || true)
[ -z "$bad" ] || { echo "files outside ownership staged: $bad"; exit 1; }
if git diff --cached --name-only | grep -q '^factory/config/' ; then
  others=$(git diff --cached --name-only | grep '^factory/config/' | grep -vx 'factory/config/allowlist.json' || true)
  [ -z "$others" ] || { echo "other config files touched: $others"; exit 1; }
fi
if grep -n -i -E "michelle|kristin|drawer|memory_card|laptop|continuity|reyes" factory/stations/fun_review.py; then echo "story-specific word in fun_review.py"; exit 1; fi
grep -q "FUN_REVIEW" factory/tickets.py || { echo "FUN_REVIEW missing from the Station enum"; exit 1; }
.venv/bin/python - <<'PY'
import json, sys
data = json.load(open("factory/config/allowlist.json"))
pins = data["stations"].get("fun_review")
ok = pins == [{"model_id": "claude-opus-5-5", "effort": "medium", "provider": "claude_code"}]
print("fun_review pin:", pins)
sys.exit(0 if ok else 1)
PY
start=$(date +%s)
.venv/bin/python -m pytest -q -p no:cacheprovider -n 8 tests/test_factory_fun_review.py tests/test_factory_line.py tests/test_factory_stations.py tests/test_factory_tickets.py tests/test_factory_deliver.py tests/test_factory_guard.py tests/test_factory_preflight.py tests/test_factory_frozen.py tests/test_factory_planner.py tests/test_factory_wiring.py tests/test_factory_followups.py tests/test_factory_live_playtest.py tests/test_factory_triage.py tests/test_factory_breakers.py tests/test_factory_state.py
took=$(( $(date +%s) - start ))
echo "factory tests took $took s (budget 150 s)"
[ "$took" -le 150 ] || { echo "over the 150 s budget"; exit 1; }
start=$(date +%s)
.venv/bin/python -m pytest -q -p no:cacheprovider -n 0 tests/test_factory_fun_review.py
took=$(( $(date +%s) - start ))
echo "fun review tests took $took s (budget 15 s)"
[ "$took" -le 15 ] || { echo "new test file over the 15 s budget"; exit 1; }
.venv/bin/python -m ruff check factory tests/test_factory_fun_review.py
.venv/bin/python -m ruff format --check factory tests/test_factory_fun_review.py
[ ! -e factory/state/ledger.jsonl ] || { echo "a test wrote factory/state/ledger.jsonl"; exit 1; }
git diff --cached > "$WORK/out/fun-review.patch"
test -s "$WORK/out/fun-review.patch"
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
        "run_name": "factory-fun-review",
        "workdir": WORK,
        "max_parallel": 1,
        "worktrees": True,
        "repo": REPO,
        "tasks": [
            {
                "key": "fun-review",
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
                "verified": "A merge-to-main ticket passes a fun review station (Opus, pinned, guarded, content-hash idempotent, fail-closed) between station 6 and delivery; a block stops the merge; tests use stubs only.",
            }
        ],
    }


if __name__ == "__main__":
    out = Path(__file__).with_name("round18e-fun-review-manifest.json")
    out.write_text(json.dumps(build(), indent=2) + "\n")
    print(out)
