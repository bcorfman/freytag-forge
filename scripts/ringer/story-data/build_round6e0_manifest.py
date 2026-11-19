# ruff: noqa: E501  (spec strings are prose briefs for a worker)
"""Build the Ringer manifest for round 6e-0: the parity gate must compare items even when a keyed list is reordered (1 task)."""

from __future__ import annotations

import json
from pathlib import Path

REPO = "/home/bcorfman/dev/freytag-forge"
WORK = "/home/bcorfman/dev/ringer-work/story-data-round6e0"
KEY = "r6e0-parity-hides-content"

OWNED = [
    "storygame/story_source/parity.py",
    "tests/story_source/test_parity_order_hides_content.py",
]

SPEC = (
    "You are a Python engineer. Your current working directory IS a git worktree of "
    + REPO
    + " (detached at HEAD). Edit files here directly. NEVER git commit, never touch "
    + REPO
    + " itself, never run `uv`, never call a billed model or the network. FIRST run: [ -e .venv ] || ln -s "
    + REPO
    + """/.venv .venv ; run tests as `PYTHONPATH=$PWD:$PWD/packages/worldkeeper/src TMPDIR=/tmp .venv/bin/python -m pytest -q -p no:cacheprovider -n 0 <files>` (never pass --cov); ruff as `.venv/bin/python -m ruff check <files>` and `.venv/bin/python -m ruff format <files>` (line length 120, double quotes, Python 3.12, no new dependencies).

BACKGROUND. storygame/story_source/parity.py compares the legacy-loaded StoryPackage with the compiled one and classifies every difference (see .plans/story-data-schema-contract.md section 9). It has a defect found by hand: in `_compare_lists`, when two keyed lists hold the same keys in a different ORDER, it records one `collection_order` (auto-accepted) difference and RETURNS without comparing the items themselves. So a real content difference inside a reordered list is never reported. Proof on the real story: the compiled package has extra effects on five pacing events (kristin_steadies_1a gains michelle_lead_actionable and memory_card_recovered, pursuit_1b gains transport_route_departure_ready, audit_nudge_2b gains michelle_reply_received, override_deadline_3a gains command_levels_assault_underway, destruction_3b gains broadcast_started), the collections `pacing.events`, `knowledge.facts`, `knowledge.knowledge`, `deliveries` and `storylets` are reported as `collection_order`, and the gate passes. The gate must have caught this.

YOUR JOB.
1. Fix `_compare_lists` (and any other place with the same shape; read the whole file) so that when keyed lists hold the same key set in a different order, the order difference is still recorded with its current class AND every keyed item pair is then compared deeply as it is when the order matches, adding each content difference with its own path and class. A content difference must never be absorbed by an order difference. Do not change how order-only differences are classified, and do not loosen any other rule.
2. Write tests/story_source/test_parity_order_hides_content.py (small synthetic package dumps, in the style of tests/story_source/test_parity_core.py; read it first): (a) a keyed list reordered with identical items: only the auto collection_order difference, parity passes; (b) the same reorder where one item's nested list gained an element: the content difference is reported unreviewed and `summary["pass"]` is False; (c) reorder plus a changed scalar field: reported; (d) a reorder of events where one event's `effects` gained a fact: reported (mirror the real defect); (e) the existing op_order and condition_order auto-classes still pass when the reordered items are otherwise equal.
3. After the fix, `tests/story_source/test_parity_default.py` is EXPECTED to fail, because it will now report the real differences. That is correct and is NOT yours to fix: do not edit the gate test, the compiler, the converter or any data. Write the full list of unreviewed differences it reports (scene, path, class, and legacy and compiled digests) to `DIFFS_r6e0.txt` in the worktree root, produced by running that test's logic yourself (copy its steps into a script run from the worktree root; never edit the test file).

TESTS: every other test in tests/story_source must still pass (test_parity_default.py and anything that converts and compiles the default story may fail for the reason above; list which ones fail in DIFFS_r6e0.txt and confirm each fails only on parity differences, not errors).

HARD LIMITS. Edit only the owned files. Never edit existing tests, tests/shard_durations.json, docs/, data/, the contract, the compiler, the converter or the reviewed-differences files.
"""
)


def check() -> str:
    keep = " ".join(f"-e '^{p}$'" for p in OWNED)
    return f"""set -eo pipefail
[ -e .venv ] || ln -s {REPO}/.venv .venv
export PYTHONPATH=$PWD:$PWD/packages/worldkeeper/src TMPDIR=/tmp
out=$(mktemp)
rc=0
.venv/bin/python -m pytest -q -p no:cacheprovider -n 0 -rs tests/story_source/test_parity_order_hides_content.py > "$out" 2>&1 || rc=$?
tail -25 "$out"
[ "$rc" -eq 0 ] || exit "$rc"
if grep -E "SKIPPED" "$out"; then echo "a gate test skips"; exit 1; fi
n=$(grep -cE "^def test_" tests/story_source/test_parity_order_hides_content.py)
[ "$n" -ge 5 ] || {{ echo "expected at least 5 tests, found $n"; exit 1; }}
rc=0
.venv/bin/python -m pytest -q -p no:cacheprovider -n 4 tests/story_source --deselect tests/story_source/test_parity_default.py > "$out" 2>&1 || rc=$?
tail -15 "$out"
[ "$rc" -eq 0 ] || exit "$rc"
test -s DIFFS_r6e0.txt || {{ echo "DIFFS_r6e0.txt missing"; exit 1; }}
cp DIFFS_r6e0.txt {WORK}/DIFFS_r6e0.txt
grep -q "pacing" DIFFS_r6e0.txt || {{ echo "the fix did not surface the known pacing.events differences"; exit 1; }}
.venv/bin/python -m ruff check storygame/story_source/parity.py tests/story_source/test_parity_order_hides_content.py
.venv/bin/python -m ruff format --check storygame/story_source/parity.py tests/story_source/test_parity_order_hides_content.py
git add -A -- storygame tests data
bad=$(git diff --cached --name-only | grep -v {keep} || true)
[ -z "$bad" ] || {{ echo "files outside ownership staged: $bad"; exit 1; }}
git diff --cached > {WORK}/{KEY}.patch
test -s {WORK}/{KEY}.patch
"""


manifest = {
    "run_name": "story-data-round6",
    "workdir": WORK,
    "max_parallel": 1,
    "worktrees": True,
    "repo": REPO,
    "tasks": [
        {
            "key": KEY,
            "task_type": "code-fix",
            "engine": "codex",
            "engine_args": ["-c", "model_reasoning_effort=high"],
            "max_attempts": 2,
            "timeout_s": 3000,
            "check_timeout_s": 900,
            "ownership": OWNED,
            "spec": SPEC,
            "check": check(),
            "expect_files": [],
            "verified": "a reorder of keyed items no longer hides content differences; synthetic tests prove it; the real story's hidden pacing differences are listed in DIFFS_r6e0.txt; tests/story_source otherwise green; ruff clean.",
        }
    ],
}

if __name__ == "__main__":
    out = Path(__file__).with_name("round6e0-manifest.json")
    out.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    print(out)
