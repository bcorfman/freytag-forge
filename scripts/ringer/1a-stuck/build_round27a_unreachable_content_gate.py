# ruff: noqa: E501
"""Round 27a: free gate for authored content no journey can reach (story gap N-3 and the next one). No model.

Owner decision 2026-11-23: the 3C epilogue must be reachable. This round does NOT fix N-3; it makes the unreachable set a
ratchet (it may only shrink) and adds a fast, free check builder the factory can run on any story-data ticket.
"""

import json
from pathlib import Path

import build_round21b_evidence_cap_and_spend_cap as b

b.WORK = "/home/bcorfman/dev/ringer-work/factory-27"
OWNED = [
    "tests/test_known_unreachable_ratchet.py",
    "tests/fixtures/known_unreachable_approved.json",
    "factory/checks/library.py",
    "tests/test_factory_checks.py",
    "tests/shard_durations.json",
]

SPEC = b.COMMON + (
    "You may edit ONLY: "
    + ", ".join(OWNED)
    + ". No story data, no other production code, no change to tests/test_game_path_journeys.py.\n\n"
    "BACKGROUND. tests/test_game_path_journeys.py plays one scripted journey per player-visible story realization (88 pass, and 4 are pinned strict xfail "
    "in the dict `KNOWN_UNREACHABLE`: the 3C aftermath storylets k_sl_3c_d_r1, k_sl_3c_d_r2, k_sl_3c_e_r1, k_sl_3c_e_r2, story gap N-3). The whole file takes about 90 s serially "
    "and is marked `nightly` (it runs only with `--run-nightly`). Owner decision (2026-11-23): those four must become reachable; the pin is a temporary honesty marker, "
    "and the unreachable set may only SHRINK. The dark factory needs (1) a ratchet so nobody adds a new unreachable entry, and (2) a fast free check it can attach to any story-data ticket.\n\n"
    'TASK 1, ratchet. Create tests/fixtures/known_unreachable_approved.json: {"decision": "owner 2026-11-23: the 3C epilogue must be reachable; repair pending; this list may only shrink", '
    '"ids": [the four ids above, sorted], "max_count": 4}. Create tests/test_known_unreachable_ratchet.py (hermetic, not marked nightly, fast): import `KNOWN_UNREACHABLE` and `PACKAGE` from tests.test_game_path_journeys. Tests: '
    "(a) every key of KNOWN_UNREACHABLE is in the approved `ids` (failure message: 'new unreachable story content: make it reachable or get an owner decision, never add it to the pin'); "
    "(b) every approved id is a real player-visible storylet realization in PACKAGE.knowledge (source.kind == 'storylet_realization', audience public and player_visible), so a renamed or deleted id fails; "
    "(c) `max_count` equals len(ids) and the ids are unique and sorted; (d) every KNOWN_UNREACHABLE reason is a non-empty string. Do NOT import-time-run any journey.\n\n"
    "TASK 2, check builder. In factory/checks/library.py add `journey_reachability_check(*, budget_s: int = 240) -> str` using the file's existing helpers (`_finish`, `_checked`, `_quote`) so the output passes `lint_check`. "
    "The script runs, from the repo root, `PYTHONPATH=$PWD:$PWD/packages/worldkeeper/src TMPDIR=/tmp .venv/bin/python -m pytest -q -p no:cacheprovider --run-nightly -n 8 tests/test_game_path_journeys.py tests/test_known_unreachable_ratchet.py`, "
    "measures wall time with `date +%s` before and after (NEVER the `SECONDS` variable: the check runs under sh where it is unset), echoes the elapsed seconds, and fails with a clear message when it exceeds `budget_s`. "
    "A non-zero pytest status fails the check with the reason 'a story realization is unreachable or the ratchet was broken'. Add tests to tests/test_factory_checks.py (extend that file; follow its style): the script contains the --run-nightly flag, `date +%s` and no `SECONDS`; it passes `lint_check`; "
    "`budget_s` appears in the generated text; a tiny fake-pytest harness (a temp directory whose `.venv/bin/python` is a shell stub that exits 0 or 1, if the file already uses `probe_unsatisfiable` or similar helpers follow that) shows exit code 0 on success and non-zero with the reason printed on failure. Keep these tests under 5 seconds and never run the real journeys.\n\n"
    "Register the new test file: run `.venv/bin/python scripts/regen_shard_durations.py --missing-only` and keep only the one new entry. Wiring the check into a factory station is NOT part of this task; say in NOTES.txt where it would plug in (station 5 free gates) and what you found."
)

OWNED_RE = "|".join(p.replace(".", r"\.") for p in OWNED)
CHECK = f"""set -eo pipefail
WORK={b.WORK}
mkdir -p "$WORK/out"
export PYTHONPATH=$PWD:$PWD/packages/worldkeeper/src TMPDIR=/tmp
[ -e .venv ] || ln -s {b.REPO}/.venv .venv
git reset -q
git add -A -- factory tests
bad=$(git diff --cached --name-only --diff-filter=d | grep -vE '^({OWNED_RE})$' || true)
[ -z "$bad" ] || {{ echo "files outside ownership staged: $bad"; exit 1; }}
test -z "$(git diff --cached --name-only -- tests/test_game_path_journeys.py)" || {{ echo "journeys file edited"; exit 1; }}
start=$(date +%s)
.venv/bin/python -m pytest -q -p no:cacheprovider -n 4 tests/test_known_unreachable_ratchet.py tests/test_factory_checks.py
took=$(( $(date +%s) - start ))
echo "tests took $took s (budget 120 s)"
[ "$took" -le 120 ] || {{ echo "over the 120 s budget"; exit 1; }}
PYFILES=$(git diff --cached --name-only --diff-filter=d | grep '\\.py$' || true)
echo "ruff files: $PYFILES"
[ -z "$PYFILES" ] || .venv/bin/python -m ruff check $PYFILES
[ -z "$PYFILES" ] || .venv/bin/python -m ruff format --check $PYFILES
.venv/bin/python - <<'PYV'
from factory.checks.library import journey_reachability_check
s = journey_reachability_check()
assert "--run-nightly" in s and "date +%s" in s and "SECONDS" not in s, s
print("builder ok")
PYV
grep -q '"tests/test_known_unreachable_ratchet.py"' tests/shard_durations.json || {{ echo "shard_durations has no entry for the new test file"; exit 1; }}
python3 -c "import json; d=json.load(open('tests/fixtures/known_unreachable_approved.json')); assert d['ids']==['k_sl_3c_d_r1','k_sl_3c_d_r2','k_sl_3c_e_r1','k_sl_3c_e_r2'] and d['max_count']==4, d"
git diff --cached > "$WORK/out/unreachable-gate.patch"
test -s "$WORK/out/unreachable-gate.patch"
"""

manifest = {
    "run_name": "factory-27a-unreachable-content-gate",
    "workdir": b.WORK,
    "max_parallel": 1,
    "worktrees": True,
    "repo": b.REPO,
    "tasks": [
        {
            "key": "unreachable-gate",
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
            "verified": "The unreachable-content set is a ratchet that can only shrink, and the factory has a fast free check that fails when a realization cannot be reached.",
        }
    ],
}
Path(__file__).with_name("round27a-unreachable-content-gate-manifest.json").write_text(
    json.dumps(manifest, indent=2) + "\n"
)
