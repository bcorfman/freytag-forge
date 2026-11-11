"""Build the Ringer manifest that makes untested custody explicit instead of silent."""

import json
from pathlib import Path

REPO = "/home/bcorfman/dev/freytag-forge"
TRACE = f"{REPO}/storygame/story_package/situation_trace.py"
GAP = f"{REPO}/storygame/story_package/gap_rules.py"
TTEST = f"{REPO}/tests/test_situation_trace.py"
GTEST = f"{REPO}/tests/test_gap_rules.py"
ENV = f"export TMPDIR=/tmp PYTHONPATH={REPO}:{REPO}/packages/worldkeeper/src"
PY = f"{REPO}/.venv/bin/python"

SPEC = f"""You are an implementation worker for the freytag-forge repository at {REPO}. Boundary: NO model call, NO network call, never git commit, never uv or bare python, never --cov. You own ONLY {TRACE}, {GAP}, {TTEST} and {GTEST} (all exist). Touch nothing else.

BUG. `custody_checks(package, anchor)` in {GAP} returns a row only for claim/item pairs it could test. For a transition anchor (for example t_1a_1b) the baseline has no other character with the protagonist, so the hypothetical-holder move cannot run and the list is EMPTY, yet the trace in {TRACE} then prints 'No held item is named by these claims.' That is false: those claims name a held item. The trace is a blind packet for reviewers and must never state something untrue.

FIX in {GAP}: every claim/item pair the custody rule would consider (claim eligible at baseline, item named by the claim, an item the world says the protagonist holds at baseline, not fixed) must produce a CustodyCheck row, even when the hypothetical cannot run. Change CustodyCheck to: claim_id, item_id, character_id (str | None), status: Literal['checked', 'unchecked', 'untested'] where 'checked' = moving the item made the claim ineligible, 'unchecked' = the claim stayed eligible after the move, 'untested' = no other character is with the protagonist in this anchor's baseline so the move could not run (character_id None). Keep holder_checked as a read-only property (status == 'checked') if other code or tests use it. Custody FLAGS must still be produced only for status 'unchecked'; the three existing rules' flags must not change. Do not add story names to {GAP} (no memory_card, kristin, patrol, laptop, k_sl_, t_1a, continuity, not even in comments).

FIX in {TRACE}: print per row: 'checked' -> 'Claim `<c>`: the engine checks whether `<character>` holds `<item>` (tested by moving it).'; 'unchecked' -> the existing 'does not check' sentence; 'untested' -> 'Claim `<c>` names `<item>`; whether the engine checks who holds it was not tested here, because no other character is with the protagonist in this anchor's starting state.' Print 'No held item is named by these claims.' ONLY when there are truly no rows. The trace must stay data only: no flags, gaps, findings, responses.

TESTS. {TTEST}: the transition anchor 't_1a_1b' output must NOT contain 'No held item is named' and must contain the 'was not tested here' sentence naming the card item resolved from the package (take the item id from custody_checks, not a literal); 'officer_presses_1a' still shows the 'does not check' sentences; a claim set with no held item (a tmp_path copy where the claim no longer names the item in entity_ids and relevance.entity_ids) prints 'No held item is named by these claims.'. {GTEST}: custody_checks on 't_1a_1b' returns an 'untested' row for the claim and item; on 'officer_presses_1a' returns 'unchecked' rows; custody flags for 'officer_presses_1a' are unchanged and none are produced for an 'untested' row. Update existing tests that referenced holder_checked only if the property cannot stay.

HOW TO RUN (from {REPO}): `{ENV} && {PY} -m pytest {TTEST} {GTEST} -q --no-cov -p no:cacheprovider 2>&1 | tail -20`. Format and lint: `{PY} -m ruff format {TRACE} {GAP} {TTEST} {GTEST} && {PY} -m ruff check {TRACE} {GAP} {TTEST} {GTEST}`."""

CHECK = f"""set -o pipefail
cd {REPO}
{ENV}
PY={PY}
$PY -m ruff check {TRACE} {GAP} {TTEST} {GTEST}
$PY -m ruff format --check {TRACE} {GAP} {TTEST} {GTEST}
if grep -n -i -E 'memory_card|kristin|patrol|laptop|k_sl_|t_1a|continuity' {GAP}; then echo 'STORY NAMES FOUND in gap_rules'; exit 1; fi
$PY -m pytest {TTEST} {GTEST} -q --no-cov -p no:cacheprovider 2>&1 | tail -12
$PY {REPO}/scripts/situation_trace.py t_1a_1b > /tmp/trace-t1a1b-b.md
tail -6 /tmp/trace-t1a1b-b.md
if grep -q 'No held item is named' /tmp/trace-t1a1b-b.md; then echo 'false statement still present'; exit 1; fi
grep -q 'not tested here' /tmp/trace-t1a1b-b.md
if grep -n -i -E '## 4\\.|## 5\\.|\\| Response \\||flag' /tmp/trace-t1a1b-b.md; then echo 'trace is no longer blind-safe'; exit 1; fi
test "$($PY {REPO}/scripts/gap_rules.py officer_presses_1a | grep -c '^### ')" = 5
"""

manifest = {
    "run_name": "story-data-gap-rules",
    "workdir": "/home/bcorfman/dev/ringer-work/story-data-gap-rules",
    "max_parallel": 1,
    "worktrees": False,
    "repo": REPO,
    "tasks": [
        {
            "key": "untested-custody-explicit",
            "task_type": "code-fix",
            "engine": "codex",
            "model": "gpt-5.6-luna",
            "engine_args": ["-c", "model_reasoning_effort=high"],
            "max_attempts": 2,
            "timeout_s": 1800,
            "check_timeout_s": 900,
            "ownership": [TRACE, GAP, TTEST, GTEST],
            "expect_files": [TRACE, GAP],
            "spec": SPEC,
            "check": CHECK,
            "verified": "an anchor whose custody could not be tested says so instead of claiming no held item, the Reyes anchor keeps its five flags, and the trace stays free of findings",
        }
    ],
}
out = Path(__file__).with_name("slice2-untested-custody-manifest.json")
out.write_text(json.dumps(manifest, indent=2) + "\n")
print(out)
