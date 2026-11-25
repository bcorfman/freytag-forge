# ruff: noqa: E501
"""Round 32a: Step 6, wire the journey reachability check into the station-5 free gates (opt-out payload key)."""

import json
from pathlib import Path

import build_round21b_evidence_cap_and_spend_cap as b

b.WORK = "/home/bcorfman/dev/ringer-work/factory-32"
PY = ".venv/bin/python"
OWNED = ["factory/stations/free_gates.py", "tests/test_factory_stations.py"]
OWNED_RE = "|".join(p.replace(".", r"\.") for p in OWNED)

SPEC = b.COMMON + (
    "You may edit ONLY: factory/stations/free_gates.py and tests/test_factory_stations.py. Do NOT edit factory/checks/**, tests/test_game_path_journeys.py or any story data. Nothing else.\n\n"
    "BACKGROUND. The free-gates station (factory/stations/free_gates.py::free_gates_handler) runs fail-fast gates: source tree, format, entry snapshots, gap delta, the one-branch carry matrix, ruff, then listed tests. "
    "tests/test_game_path_journeys.py plays one scripted journey per player-visible storylet realization (marked nightly, so it runs only with `--run-nightly`; about 93 s serial, 240 s budget with -n 8) and tests/test_known_unreachable_ratchet.py pins the approved unreachable set. "
    "Owner decision (2026-11-23): authored content that no journey reaches must fail a free gate, so the factory finds the next unreachable storylet. The library builder `factory.checks.library.journey_reachability_check` (read it; do not edit it) already shows the exact command.\n\n"
    "CHANGE. In free_gates_handler add a `journey_reachability` gate that runs right AFTER the carry matrix gate and BEFORE ruff. It is on by default and switched off by payload key `journey_reachability: false` (same convention as `carry_matrix`). "
    "It runs, through the existing `_run_command` helper with the injected `run`, in the ticket tree (`repository_root`), with `_pytest_environment(repository_root)` and `timeout=240`: "
    "[.venv/bin/python, -m, pytest, -q, -p, no:cacheprovider, --run-nightly, -n, 8, tests/test_game_path_journeys.py, tests/test_known_unreachable_ratchet.py]. "
    "On failure return `StationResult(False, \"journey_reachability\", _tail(detail))` where detail is the command output, or 'journey reachability failed' when empty; a timeout returns the existing 'command timed out' text under the same check name, and the output must mention that a story realization is unreachable or the ratchet was broken only when the command exited non-zero for a reason other than timeout (prefix the output with 'a story realization is unreachable or the ratchet was broken: '). "
    "Update the module docstring and the handler docstring to mention the gate.\n\n"
    "TESTS, WRITE THEM FIRST in tests/test_factory_stations.py (extend that file; follow its fake `Runner` style; read the existing free_gates tests first): "
    "(1) default payload runs the journey command after the carry matrix gate (use the existing monkeypatched carry matrix to order them) and before ruff, with the exact argument list above, cwd the repository root, timeout 240, and PYTHONPATH containing the root and packages/worldkeeper/src; "
    "(2) `journey_reachability: false` skips it entirely (the runner sees no pytest call for it); "
    "(3) a non-zero exit returns check `journey_reachability` with the prefix and the output tail, and ruff and the listed tests never run after it; "
    "(4) a timeout returns check `journey_reachability` and 'command timed out'; "
    "(5) with a ticket tree the command runs in the tree, not the original root; "
    "(6) a failure in the carry matrix gate stops before the journey gate. "
    'Many OLD tests build payloads with `carry_matrix: False` and a scripted fake runner whose call list or call count would now include the journey command: update those tests (most simply by adding `journey_reachability: False` to their payloads, or via the shared helper at line ~86 that returns `{"gap_baseline": ..., "carry_matrix": False}`) and list each in NOTES.txt. Do NOT weaken any assertion. '
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
grep -q 'journey_reachability' factory/stations/free_gates.py || {{ echo "gate missing from free_gates.py"; exit 1; }}
grep -q 'run-nightly' factory/stations/free_gates.py || {{ echo "--run-nightly missing"; exit 1; }}
grep -nE "k_sl_|k_scene_|SL-[0-9]|\\b[123][A-C]\\b" factory/stations/free_gates.py && {{ echo "story-specific names in production code"; exit 1; }} || true
PYFILES=$(git diff --cached --name-only --diff-filter=d | grep '\\.py$' || true)
[ -z "$PYFILES" ] || {PY} -m ruff check $PYFILES
[ -z "$PYFILES" ] || {PY} -m ruff format --check $PYFILES
git diff --cached > "$WORK/out/wire-reachability.patch"
test -s "$WORK/out/wire-reachability.patch"
"""

manifest = {
    "run_name": "factory-32a-wire-reachability",
    "workdir": b.WORK,
    "max_parallel": 1,
    "worktrees": True,
    "repo": b.REPO,
    "tasks": [
        {
            "key": "wire-reachability",
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
            "verified": "Station 5 runs the journey reachability gate by default after the carry matrix, with opt-out and tests; old tests updated without weakened assertions.",
        }
    ],
}
Path(__file__).with_name("round32a-wire-reachability-manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")
