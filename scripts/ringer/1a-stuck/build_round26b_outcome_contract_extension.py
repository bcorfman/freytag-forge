# ruff: noqa: E501
"""Round 26b: qualification Step 2 task 2.7: provenance flags, character-knowledge flag, epilogue and pacing numbers. Free, no model.

Runs in the local branch worktree `pr-outcome-contract` (round 26a's commit), so the worker extends the existing module.
"""

import json
from pathlib import Path

import build_round21b_evidence_cap_and_spend_cap as b

b.WORK = "/home/bcorfman/dev/ringer-work/factory-26b"
BRANCH_REPO = "/home/bcorfman/dev/ringer-work/pr-outcome-contract"
FIX = "/home/bcorfman/dev/ringer-work/qual-20261122/qualification/outcome_contract_fixtures"
OWNED = ["factory/outcome_contract.py", "tests/test_outcome_contract.py"]

SPEC = b.COMMON + (
    "You may edit ONLY: factory/outcome_contract.py and tests/test_outcome_contract.py. NEVER edit anything under "
    "tests/fixtures/outcome_contract/ (the frozen examples; the check compares them byte for byte with the originals). "
    "No other production code, story data or existing test.\n\n"
    "BACKGROUND. factory/outcome_contract.py already holds `classify_run(run, scene)`, the pure outcome classifier (core tier: per-turn action_outcome and "
    "knowledge_progress, stall runs, confirmed_stuck, unresolved, exit, status). Read it, tests/test_outcome_contract.py and "
    "tests/fixtures/outcome_contract/README.md (the full contract) and cases.json (the frozen examples) FIRST. The core tier left three result fields as placeholders "
    "marked 'intentionally deferred': `provenance_flags` (always []), `pacing` ({}) and `epilogue` (all false). Fill them in now, exactly as the README section "
    "'Extension tier (separate task)' specifies, and nothing else.\n\n"
    "DETAILS the README leaves open (decide as stated):\n"
    '- Double-quoted segments: take text between straight double quotes `"..."` and between curly quotes; an unbalanced quote ends at the end of the text. A segment is checked on its own.\n'
    "- Whitespace normalisation: collapse runs of whitespace to one space and strip, on both sides, case-sensitive.\n"
    "- `bookkeeping_voiced` and `character_knowledge`: at most ONE flag per (turn, kind, matched string); a turn that is not a dict or has no string `text` yields no flag.\n"
    "- `provenance_flags` is sorted by turn (a flag with turn None sorts last), then kind.\n"
    "- `epilogue_not_offered` has `turn: None`. `epilogue.offered` and `.taken` are false when `scene.epilogue_candidates` is empty or no turn has `ending_latched` true.\n"
    "- `pacing.exploration_share` is a float rounded to 4 decimals; `quiet_stretch` is 0 when there is no pressure event; `turns_to_first_pressure` is the `turn` value of the first turn with `pressure_event` true, or None.\n"
    "- `status` now returns `flagged` when there are no unresolved and no confirmed_stuck turns but at least one provenance flag, as the README says.\n"
    "- Set `contract_version` to `v1`.\n"
    "- Never mutate inputs; never raise on malformed input (a non-string `text`, non-list `unlearned_terms`, a term entry that is not a dict, and so on are skipped).\n\n"
    "TESTS. In tests/test_outcome_contract.py REMOVE the skip of extension-tier cases: the parametrized test must now run every case in cases.json (27 in all), none skipped. Keep every existing test (update any that pinned "
    "`contract_version == 'v1-core'`, empty pacing, or the always-empty provenance_flags and say so in NOTES.txt). Add tests of your own: a flag is not raised when the term appears only in narration outside quotes; "
    "curly quotes work; two quoted segments in one turn each checked; an unbalanced opening quote; a turn with no `text`; `quiet_stretch` resets on a pressure_event turn and on an npc_move turn and on knowledge_progress; "
    "`exploration_share` for zero turns is 0.0; epilogue taken without ever being offered cannot happen (taken implies offered); two separate runs of the classifier on the same input give equal results.\n\n"
    "Do not touch the shard_durations file (no new test file is added)."
)

OWNED_RE = "|".join(p.replace(".", r"\.") for p in OWNED)
CHECK = f"""set -eo pipefail
WORK={b.WORK}
mkdir -p "$WORK/out"
export PYTHONPATH=$PWD:$PWD/packages/worldkeeper/src TMPDIR=/tmp
[ -e .venv ] || ln -s {b.REPO}/.venv .venv
cmp tests/fixtures/outcome_contract/cases.json {FIX}/cases.json || {{ echo "cases.json differs from the frozen examples"; exit 1; }}
cmp tests/fixtures/outcome_contract/README.md {FIX}/README.md || {{ echo "README.md differs from the frozen contract"; exit 1; }}
git reset -q
git add -A -- factory tests
bad=$(git diff --cached --name-only --diff-filter=d | grep -vE '^({OWNED_RE})$' || true)
[ -z "$bad" ] || {{ echo "files outside ownership staged: $bad"; exit 1; }}
start=$(date +%s)
out=$(.venv/bin/python -m pytest -q -p no:cacheprovider -rs tests/test_outcome_contract.py 2>&1) || {{ echo "$out"; exit 1; }}
echo "$out" | tail -6
took=$(( $(date +%s) - start ))
echo "tests took $took s (budget 60 s)"
[ "$took" -le 60 ] || {{ echo "over the 60 s budget"; exit 1; }}
case "$out" in *skipped*) echo "tests were skipped; every frozen example must run"; exit 1;; esac
PYFILES=$(git diff --cached --name-only --diff-filter=d | grep '\\.py$' || true)
echo "ruff files: $PYFILES"
[ -z "$PYFILES" ] || .venv/bin/python -m ruff check $PYFILES
[ -z "$PYFILES" ] || .venv/bin/python -m ruff format --check $PYFILES
.venv/bin/python - <<'PYV'
import json
from factory.outcome_contract import classify_run
cases = json.load(open("tests/fixtures/outcome_contract/cases.json"))
assert len(cases) == 27, len(cases)
bad = []
for c in cases:
    r = classify_run(c["run"], c["scene"])
    if r["contract_version"] != "v1":
        bad.append(("version", c["id"]))
    for key in ("provenance_flags", "epilogue", "exit", "status", "confirmed_stuck", "unresolved"):
        if key in c["expected"] and r[key] != c["expected"][key]:
            bad.append((c["id"], key, r[key], c["expected"][key]))
    for key, val in c["expected"].get("pacing", {{}}).items():
        if r["pacing"].get(key) != val:
            bad.append((c["id"], "pacing." + key, r["pacing"].get(key), val))
assert not bad, bad
print("all 27 frozen examples match")
PYV
git diff --cached > "$WORK/out/outcome-contract-extension.patch"
test -s "$WORK/out/outcome-contract-extension.patch"
"""

manifest = {
    "run_name": "factory-26b-outcome-contract-extension",
    "workdir": b.WORK,
    "max_parallel": 1,
    "worktrees": True,
    "repo": BRANCH_REPO,
    "tasks": [
        {
            "key": "outcome-contract-extension",
            "task_type": "code-feature",
            "engine": "codex",
            "engine_args": ["-c", "model_reasoning_effort=medium"],
            "max_attempts": 2,
            "timeout_s": 1800,
            "check_timeout_s": 600,
            "ownership": OWNED,
            "spec": SPEC,
            "check": CHECK,
            "expect_files": [],
            "verified": "Provenance flags, the character-knowledge flag, the epilogue offer and pacing numbers are computed, and all 27 frozen examples pass with none skipped.",
        }
    ],
}
Path(__file__).with_name("round26b-outcome-contract-extension-manifest.json").write_text(
    json.dumps(manifest, indent=2) + "\n"
)
