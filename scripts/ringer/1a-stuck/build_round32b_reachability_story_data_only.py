# ruff: noqa: E501
"""Round 32b: run the station-5 journey reachability gate only for story-data tickets (explicit payload key overrides)."""

import json
from pathlib import Path

import build_round21b_evidence_cap_and_spend_cap as b

b.WORK = "/home/bcorfman/dev/ringer-work/factory-32b"
PY = ".venv/bin/python"
PATCH = "/home/bcorfman/dev/ringer-work/factory-32/out/wire-reachability.patch"
OWNED = ["factory/stations/free_gates.py", "tests/test_factory_stations.py"]
OWNED_RE = "|".join(p.replace(".", r"\.") for p in OWNED)

SPEC = b.COMMON + (
    f"FIRST, before anything else, apply the previous round's patch: `git apply {PATCH}` (it adds the `journey_reachability` gate to factory/stations/free_gates.py and its tests to tests/test_factory_stations.py; the HEAD of this worktree does not have them yet). Then read what it added.\n\n"
    "You may edit ONLY: factory/stations/free_gates.py and tests/test_factory_stations.py. Nothing else.\n\n"
    "BACKGROUND. The `journey_reachability` gate runs the ~93 s journey suite (about 240 s worst case) and is currently ON for every ticket unless the payload says `journey_reachability: false`. That is wasted time for tickets that touch no story data. "
    "Owner decision: run it only for story-data tickets.\n\n"
    "CHANGE. Add a helper in free_gates.py (for example `_touches_story_data(payload, repository_root, original_root, tree, story_root) -> bool`) and use it so the gate decision is: "
    "(1) payload `journey_reachability` is exactly True -> run; (2) exactly False -> skip; (3) key absent (or any other value) -> run only when the ticket is a story-data ticket. "
    "A ticket is a story-data ticket when its payload has a `source_root` key, OR any string entry of its `paths` list, resolved with the existing `_resolve` helper the same way the other gates resolve paths (root `repository_root`, original root only when a ticket tree is in use), lies inside the resolved `story_root` (use the existing `_inside` helper). "
    "A malformed `paths` (not a list) or a non-string entry is ignored, never an error. A ticket with no `source_root` and no path under the story root, such as a pure factory/tests ticket, skips the gate. "
    "Update the module and handler docstrings accordingly. Keep the gate's position (after the carry matrix, before ruff), command, timeout and failure text unchanged.\n\n"
    "TESTS, WRITE THEM FIRST in tests/test_factory_stations.py, extending the journey tests from the previous round: "
    "(1) payload with `source_root` and no key runs the gate; (2) payload with only a `paths` entry under the story root runs it (use a tmp story root via the payload's `story_root` key); "
    "(3) payload with only paths outside the story root (e.g. factory/foo.py, tests/test_x.py) skips it and the runner sees no journey command; (4) payload with no paths and no source_root skips it; "
    "(5) explicit True runs it even for a pure factory ticket; (6) explicit False skips it even for a story-data ticket; "
    "(7) with a ticket tree, a path under the tree's story root counts as story data; (8) a non-list `paths` and a non-string entry do not raise. "
    "The previous round's tests that relied on the gate being on by default must now either set `journey_reachability: True` or use a story-data payload; keep every assertion and list each changed test in NOTES.txt. "
    "Run the whole of tests/test_factory_stations.py and tests/test_factory_checks.py."
)

CHECK = f"""set -eo pipefail
WORK={b.WORK}
mkdir -p "$WORK/out"
export PYTHONPATH=$PWD:$PWD/packages/worldkeeper/src TMPDIR=/tmp
[ -e .venv ] || ln -s {b.REPO}/.venv .venv
git reset -q
git add -A -- factory tests
bad=$(git diff --cached --name-only --diff-filter=d | grep -vE '^({OWNED_RE})$' || true)
[ -z "$bad" ] || {{ echo "files outside ownership staged: $bad"; exit 1; }}
start=$(date +%s)
out=$({PY} -m pytest -q -p no:cacheprovider -rs -n 4 tests/test_factory_stations.py tests/test_factory_checks.py 2>&1) || {{ echo "$out"; exit 1; }}
echo "$out" | tail -6
took=$(( $(date +%s) - start ))
echo "tests took $took s (budget 120 s)"
[ "$took" -le 120 ] || {{ echo "over the 120 s budget"; exit 1; }}
case "$out" in *skipped*) echo "tests were skipped"; exit 1;; esac
grep -q 'run-nightly' factory/stations/free_gates.py || {{ echo "gate command lost"; exit 1; }}
grep -q 'source_root' factory/stations/free_gates.py || {{ echo "source_root rule missing"; exit 1; }}
grep -nE "k_sl_|k_scene_|SL-[0-9]|\\b[123][A-C]\\b" factory/stations/free_gates.py && {{ echo "story-specific names in production code"; exit 1; }} || true
PYFILES=$(git diff --cached --name-only --diff-filter=d | grep '\\.py$' || true)
[ -z "$PYFILES" ] || {PY} -m ruff check $PYFILES
[ -z "$PYFILES" ] || {PY} -m ruff format --check $PYFILES
git diff --cached > "$WORK/out/reachability-story-data.patch"
test -s "$WORK/out/reachability-story-data.patch"
"""

manifest = {
    "run_name": "factory-32b-reachability-story-data-only",
    "workdir": b.WORK,
    "max_parallel": 1,
    "worktrees": True,
    "repo": b.REPO,
    "tasks": [
        {
            "key": "story-data-only",
            "task_type": "code-feature",
            "engine": "codex",
            "engine_args": ["-c", "model_reasoning_effort=medium"],
            "max_attempts": 2,
            "timeout_s": 2400,
            "check_timeout_s": 300,
            "ownership": OWNED,
            "spec": SPEC,
            "check": CHECK,
            "expect_files": [],
            "verified": "The journey reachability gate runs only for story-data tickets, with an explicit payload override; the combined patch includes round 32a.",
        }
    ],
}
Path(__file__).with_name("round32b-reachability-story-data-manifest.json").write_text(
    json.dumps(manifest, indent=2) + "\n"
)
