# ruff: noqa: E501
"""Round 24e: test the error and validation branches of the golden entry snapshot module (nightly coverage debt)."""

import json
from pathlib import Path

import build_round21b_evidence_cap_and_spend_cap as b

b.WORK = "/home/bcorfman/dev/ringer-work/factory-24"
OWNED = ["tests/test_entry_snapshot_errors.py", "tests/shard_durations.json"]
REPO = "/home/bcorfman/dev/ringer-work/pr-snapshot-tests"

MISSING_LINES = "43-44, 81-93 (odd lines), 100, 115, 176-180, 214, 220, 232-239, 247, 253-256, 277-285, 308, 384-403, 423-429, 437-439, 468-475, 492"

SPEC = b.COMMON + (
    "You may edit ONLY: tests/test_entry_snapshot_errors.py (new) and tests/shard_durations.json. No production code, no "
    "story data, no existing test.\n\n"
    "BACKGROUND. storygame/runtime/entry_snapshots.py builds, writes, loads, checks and replays the golden per-scene "
    "entry snapshots in data/stories/continuity-initiative/entry/. The nightly coverage run shows it at 79% "
    "(the nightly gate is 90% overall and is red). The existing tests/test_entry_snapshots.py covers the happy "
    "paths. These lines of storygame/runtime/entry_snapshots.py are NEVER executed by any test: " + MISSING_LINES + ". "
    "They are the validation and error branches: an unknown scene id, malformed or missing snapshot files, wrong "
    "schema shapes (a value that must be a mapping or list), a stale or mismatched fingerprint, a snapshot whose "
    "scene or story does not match, unknown predicates or entity ids on import, drift-line formatting for every kind "
    "of difference (added, removed, changed fact; world versus story fact), the carry-in report branches, and the "
    "CLI `main` paths (check with drift returns non-zero and prints the drift; write; missing story root; unknown "
    "command).\n\n"
    "TASK. Read storygame/runtime/entry_snapshots.py and tests/test_entry_snapshots.py (follow its helpers: it copies "
    "the story to tmp_path before mutating; never mutate the real data/ directory). Write tests/test_entry_snapshot_errors.py "
    "so that each listed branch is exercised through the PUBLIC functions (build_entry_snapshot, write_entry_snapshots, "
    "load_entry_snapshot, state_from_snapshot, carry_in_report, check_entry_snapshots, main) by feeding it a real "
    "defect: a deleted or truncated snapshot file, invalid JSON, a snapshot whose top-level field has the wrong type, "
    "a tampered fingerprint, an unknown scene id, a fact row with an unknown predicate, and so on. Each test asserts the "
    "specific error type and a distinctive fragment of its message (EntrySnapshotError) or the specific drift line, "
    "not just 'raises'. Do NOT use coverage tools or --cov (forbidden); instead, for each line range above, put a "
    "comment in the test naming the function and branch it covers, and list in NOTES.txt any listed line you could "
    "NOT reach through the public API and why (unreachable code is a finding, not something to force). Keep the "
    "whole file fast: under 10 seconds total, hermetic, no network, no model, no subprocess unless the CLI test needs "
    "one (prefer calling main(argv) directly with capsys). Register the new test file: run "
    "`.venv/bin/python scripts/regen_shard_durations.py --missing-only` and keep only the one new entry."
)

OWNED_RE = "|".join(p.replace(".", r"\.") for p in OWNED)
CHECK = f"""set -eo pipefail
WORK={b.WORK}
mkdir -p "$WORK/out"
export PYTHONPATH=$PWD:$PWD/packages/worldkeeper/src TMPDIR=/tmp
[ -e .venv ] || ln -s {b.REPO}/.venv .venv
git add -A -- tests
bad=$(git diff --cached --name-only | grep -vE '^({OWNED_RE})$' || true)
[ -z "$bad" ] || {{ echo "files outside ownership staged: $bad"; exit 1; }}
start=$(date +%s)
.venv/bin/python -m pytest -q -p no:cacheprovider -n 8 tests/test_entry_snapshot_errors.py tests/test_entry_snapshots.py
took=$(( $(date +%s) - start ))
echo "tests took $took s (budget 120 s)"
[ "$took" -le 120 ] || {{ echo "over the 120 s budget"; exit 1; }}
PYFILES=$(git diff --cached --name-only --diff-filter=d | grep '\\.py$' || true)
[ -z "$PYFILES" ] || .venv/bin/python -m ruff check $PYFILES
[ -z "$PYFILES" ] || .venv/bin/python -m ruff format --check $PYFILES
n=$(grep -c '^def test_' tests/test_entry_snapshot_errors.py)
[ "$n" -ge 12 ] || {{ echo "only $n tests; expected at least 12 for the listed branches"; exit 1; }}
! grep -nE '(^|[^A-Za-z])coverage([^A-Za-z]|$)|--cov' tests/test_entry_snapshot_errors.py | grep -v '^[0-9]*:\\s*#' || {{ echo "coverage tooling referenced"; exit 1; }}
test -z "$(git status --porcelain data)" || {{ echo "data/ was modified"; exit 1; }}
git diff --cached > "$WORK/out/entry-snapshot-errors.patch"
test -s "$WORK/out/entry-snapshot-errors.patch"
"""

manifest = {
    "run_name": "factory-24e-entry-snapshot-errors",
    "workdir": b.WORK,
    "max_parallel": 1,
    "worktrees": True,
    "repo": REPO,
    "tasks": [
        {
            "key": "entry-snapshot-errors",
            "task_type": "test-hardening",
            "engine": "codex",
            "engine_args": ["-c", "model_reasoning_effort=medium"],
            "max_attempts": 2,
            "timeout_s": 1800,
            "check_timeout_s": 600,
            "ownership": OWNED,
            "spec": SPEC,
            "check": CHECK,
            "expect_files": [],
            "verified": "The error and validation branches of entry_snapshots.py are exercised by tests that assert specific errors.",
        }
    ],
}
Path(__file__).with_name("round24e-entry-snapshot-errors-manifest.json").write_text(
    json.dumps(manifest, indent=2) + "\n"
)
