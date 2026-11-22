# ruff: noqa: E501  (spec strings are prose briefs for a worker)
"""Round 18e-2: the fun review station reuses a saved verdict that was a block. FREE: no model call, no network.

One Codex task. Usage: build_round18e2_fun_review_fix_manifest.py
"""

from __future__ import annotations

import json
from pathlib import Path

REPO = "/home/bcorfman/dev/freytag-forge"
WORK = "/home/bcorfman/dev/ringer-work/factory-fun-review-fix"
OWNED = ["factory/stations/fun_review.py", "tests/test_factory_fun_review.py", "tests/shard_durations.json"]

SPEC = """You are a Python engineer. Your current working directory IS a git worktree of @REPO@ (detached at HEAD). Edit files here directly. NEVER git commit, never touch @REPO@ itself, never run `uv`, NEVER call a model, NEVER use the network. FIRST run: [ -e .venv ] || ln -s @REPO@/.venv .venv . Environment for every command: `export PYTHONPATH=$PWD:$PWD/packages/worldkeeper/src TMPDIR=/tmp`. Ruff: `.venv/bin/python -m ruff check <files>` and `.venv/bin/python -m ruff format <files>` (line length 120, Python 3.12). Never pass --cov to pytest. Run tests as `.venv/bin/python -m pytest -q -p no:cacheprovider -n 0 <files>`.

BACKGROUND. `factory/stations/fun_review.py` (read it and `tests/test_factory_fun_review.py` first) is a review gate: Opus answers three questions and the station may pass a fix only when the verdict is `pass`, all three `checks` are exactly True and the reasons are non-empty; anything else must block. The handler saves the reviewer's raw `verdict` in `review.json`, and `_saved_result` rebuilds the result from that raw `verdict` alone. That fails OPEN: a reply with verdict `pass` but one false check is a block on the first run, is saved as `pass`, and a retry reuses it as a PASS with no new review. The same hole exists for a `pass` reply with empty reasons.

FIX. Make the saved record hold the FINAL outcome, and make reuse re-derive it. (1) In the handler, compute the final outcome once (pass only under the rule above) and save `verdict` as that final outcome (`pass` or `block`), keeping the reviewer's `checks` and the stored `reasons`. (2) `_saved_result` must itself re-apply the rule: it passes only when the saved `verdict` is `pass`, `checks` is a dict whose three keys are all exactly True and `reasons` is a non-empty string; otherwise it returns the block result (a saved record that is malformed in any way is NOT reused; the station reviews again). Keep every message and every other behaviour unchanged.

TESTS in `tests/test_factory_fun_review.py` (hermetic; stubs only). Name them exactly: `test_saved_pass_with_a_false_check_is_not_reused_as_a_pass` (first run: reviewer replies verdict pass with one false check, the station blocks and the reviewer ran once; a second handler run on the same tree makes no reviewer call and blocks again), `test_saved_record_with_pass_and_a_false_check_blocks_on_reuse` (hand-write a `review.json` for the current diff hash with verdict `pass` and one false check: the station does not pass; it blocks without a reviewer call), `test_pass_with_empty_reasons_blocks_and_stays_blocked_on_retry` (reply pass with empty reasons: blocked, and a second run blocks with no new call), `test_malformed_saved_record_is_reviewed_again` (a `review.json` with the right hash but no `checks`: the reviewer is called). The file still runs in under 15 seconds. If `tests/shard_durations.json` needs no change, leave it alone.

HARD LIMITS. Edit only the owned files: @OWNED@. Write NOTES_18E2.txt (worktree root, never committed) listing every ambiguity and your choice."""

CHECK = """set -eo pipefail
WORK=@WORK@
mkdir -p "$WORK/out"
export PYTHONPATH=$PWD:$PWD/packages/worldkeeper/src TMPDIR=/tmp
[ -e .venv ] || ln -s @REPO@/.venv .venv
git add -A -- factory tests
bad=$(git diff --cached --name-only | grep -vE '^(factory/stations/fun_review\\.py|tests/test_factory_fun_review\\.py|tests/shard_durations\\.json)$' || true)
[ -z "$bad" ] || { echo "files outside ownership staged: $bad"; exit 1; }
for name in test_saved_pass_with_a_false_check_is_not_reused_as_a_pass test_saved_record_with_pass_and_a_false_check_blocks_on_reuse test_pass_with_empty_reasons_blocks_and_stays_blocked_on_retry test_malformed_saved_record_is_reviewed_again; do
  grep -q "def $name" tests/test_factory_fun_review.py || { echo "test $name missing"; exit 1; }
done
start=$(date +%s)
.venv/bin/python -m pytest -q -p no:cacheprovider -n 0 tests/test_factory_fun_review.py
took=$(( $(date +%s) - start ))
echo "fun review tests took $took s (budget 15 s)"
[ "$took" -le 15 ] || { echo "over the 15 s budget"; exit 1; }
.venv/bin/python -m pytest -q -p no:cacheprovider -n 4 tests/test_factory_line.py tests/test_factory_stations.py tests/test_factory_deliver.py
.venv/bin/python -m ruff check factory tests/test_factory_fun_review.py
.venv/bin/python -m ruff format --check factory tests/test_factory_fun_review.py
[ ! -e factory/state/ledger.jsonl ] || { echo "a test wrote factory/state/ledger.jsonl"; exit 1; }
git diff --cached > "$WORK/out/fun-review-fix.patch"
test -s "$WORK/out/fun-review-fix.patch"
"""


def build() -> dict:
    def fill(text: str) -> str:
        return text.replace("@REPO@", REPO).replace("@WORK@", WORK).replace("@OWNED@", ", ".join(OWNED))

    return {
        "run_name": "factory-fun-review-fix",
        "workdir": WORK,
        "max_parallel": 1,
        "worktrees": True,
        "repo": REPO,
        "tasks": [
            {
                "key": "fun-review-fix",
                "task_type": "code-fix",
                "engine": "codex",
                "engine_args": ["-c", "model_reasoning_effort=high"],
                "max_attempts": 2,
                "timeout_s": 2400,
                "check_timeout_s": 600,
                "ownership": OWNED,
                "spec": fill(SPEC),
                "check": fill(CHECK),
                "expect_files": [],
                "verified": "A saved fun review verdict is reused only when it is a real pass (all checks true, reasons present); a pass with a false check or empty reasons stays blocked on retry; tests use stubs only.",
            }
        ],
    }


if __name__ == "__main__":
    out = Path(__file__).with_name("round18e2-fun-review-fix-manifest.json")
    out.write_text(json.dumps(build(), indent=2) + "\n")
    print(out)
