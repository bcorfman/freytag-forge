# ruff: noqa: E501  (spec strings are prose briefs for a worker)
"""Round 20a/20b: qualification Phase 1 repairs D1 and D2 in factory/stations/probe.py. FREE to build and run.

Usage: build_round20a_probe_repairs_manifest.py d1|d2   (D2 is built only after the D1 patch is committed.)
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

REPO = "/home/bcorfman/dev/freytag-forge"
WORK = "/home/bcorfman/dev/ringer-work/factory-20"
AUDIT = "/home/bcorfman/dev/ringer-work/qual-20261122/qualification/foundation.md"
OWNED = ["factory/stations/probe.py", "tests/test_factory_probe.py"]

COMMON = """You are a factory engineer. Your current working directory IS a git worktree of @REPO@ (detached at HEAD). Edit files here directly. NEVER git commit, never touch @REPO@ itself, never run `uv`, NEVER call a model (not `claude`, not `codex`), NEVER use the network, never run `python -m bench run`, never write factory/state/. FIRST run: [ -e .venv ] || ln -s @REPO@/.venv .venv . Environment for every command: `export PYTHONPATH=$PWD:$PWD/packages/worldkeeper/src TMPDIR=/tmp`. Ruff (python files only): `.venv/bin/python -m ruff check <files>` / `.venv/bin/python -m ruff format <files>` (line length 120, Python 3.12). Never pass --cov to pytest. Run tests as `.venv/bin/python -m pytest -q -p no:cacheprovider -n 8 <files>`. Tests must be hermetic (fake runner, no network). The module must stay story-agnostic (an existing test checks this; do not add story names). If an OLD test pins behaviour this change deliberately changes, update it and say so in NOTES.txt. Write NOTES.txt (worktree root, never committed) listing every ambiguity and your choice. Read first: AGENTS.md, factory/stations/probe.py, tests/test_factory_probe.py, and the audit in @AUDIT@ (rows 'Failure visibility' and 'Spend: restart / quota sleep'). You may edit ONLY factory/stations/probe.py and tests/test_factory_probe.py. Other tests that import probe (tests/test_factory_probe_routing.py, tests/test_factory_line.py and any other tests/test_factory_*.py) must keep passing unchanged; if one cannot, keep your change backward compatible instead of editing it."""

D1 = """
PROBLEM (defect D1). `summarize_arm` in factory/stations/probe.py skips every bench run that is not complete (`_run_is_complete` false, the `continue` near line 174), so failed or partial replicates appear in no count. A file with one completed run and five failed runs summarizes as `replicates: 1`. The earned-exit rate divides by completed replicates only, so a candidate whose failed replicates are the ones that did not exit would score better than it should. The existing test `test_summarize_arm_counts_fixture_and_rejects_malformed` pins this dropping as expected.

CHANGE. (1) `summarize_arm` gains a key `failed_replicates`: the count of runs that are not complete (still malformed-file ValueError behaviour for non-dict runs; a not-complete run still contributes nothing else, no turns). The key must always be present, zero when none failed. (2) `judge_probe`: if either arm has `failed_replicates > 0`, add a reason that names both arms' counts ('Failed replicates: control N, candidate M.') and make the verdict `inconclusive`, exactly like the existing unknown-exit and too-few-stuck-turns cases (an inconclusive verdict must never turn into keep or reject; keep the comparison reasons from also being appended in that case, as the existing code does for other inconclusive reasons). Also expose `failed_replicates` in the verdict dict under `control`/`candidate` (they already carry the whole summary) and mention it in the one-line result text if `_line` or `_feedback` list summary counts (read them; add the count only if they already list sibling counts, keep wording short). (3) Update the old test that pins the dropping so it expects `failed_replicates: 1` for its `status: failed` run, and add hermetic tests: a failed run alone is counted and nothing else; an arm with failures forces `inconclusive` even when the candidate looks better on every other count; no failures keeps the old verdicts unchanged (the existing judge tests must still pass); the key is present on an all-ok arm. Do not change thresholds or any other rule.
"""

D2 = """
PROBLEM (defect D2). The billed-run approval is consumed only through `payload_updates` on a RETURNED `StationResult` (see `_consume_approval`, `approval_updates`). If a `LimitSleep`/`ProviderLimit` is raised from the runner mid-run, or the process dies, nothing is returned, so the approval is still valid and the next attempt bills the same replays again. Reproduced: a runner that raises `LimitSleep` is invoked twice with an unchanged payload. Completed per-run outputs are also unlinked at the start of every attempt (`(output_dir / "turn-records.json").unlink()`), so finished replays are rebilled. `billed_usd_ceiling` is optional, so nothing bounds repeats when it is unset.

CHANGE. Keep all of this inside factory/stations/probe.py (the line discards payload updates when the handler raises LimitSleep, so do NOT rely on payload; persist on disk). (1) Right after the budget and ceiling gates pass and BEFORE the first runner call, write an atomic sidecar `<workspace>/<ticket id>/probe-attempt.json` (use the module's existing `_atomic_json_write` and `_safe_id`) holding: `input_hash`, `approval_id` (the payload's `billed_run_approval_id`, or the string "default" when absent), `resumes` (int, starts 0), `started`. (2) At the start of an attempt, if that sidecar exists with the SAME `input_hash` and `approval_id` and no saved final result exists, this is a RESUME of an already-authorized run: it does not need a new approval (bypass the single-use `_approval_error` check for it), increments `resumes`, and is refused with a clear message once `resumes` would exceed 2 (`MAX_RESUMES = 2` module constant). A sidecar with a different input hash or approval id is a new run and goes through the normal approval check. After a run completes and the final `probe.json` is saved, delete the sidecar. (3) On a resume, do NOT delete an existing `turn-records.json` that holds a completed, parseable bench output for that arm/run (use `_turns_in_file` or json parsing): skip the runner call for that arm/run and reuse the file, so finished replays are not billed twice. An existing output that is missing or unparseable is deleted and rerun as today. On a fresh run the old unlink behaviour stays. (4) The cost projection for a resume covers only the arm/runs that will actually be run again; the ceiling and budget gates still run on a resume with that smaller projection. (5) Leave `billed_usd_ceiling` optional, but record in the verdict payload when a run finished that no ceiling was set? NO: do not add that; only items 1 to 4. (6) Tests (hermetic, in tests/test_factory_probe.py, using the module's existing helpers `configure_probe_root`, `make_runner`, `make_ticket`, `RULES`, `BUDGET`): a runner raising LimitSleep on its second call, then a resumed attempt with the unchanged payload and a runner that works: the first-run arm outputs are reused (count runner calls), the resumed run finishes with a verdict, the sidecar is gone afterwards, and the ledger sums only what was billed; a third resume beyond MAX_RESUMES is refused with a message and calls the runner zero times; a changed input (different runs list) after a sleep is NOT treated as a resume and, with the old approval consumed, is refused; the existing single-use test still passes unchanged.
"""

CHECK = """set -eo pipefail
WORK=@WORK@
mkdir -p "$WORK/out"
export PYTHONPATH=$PWD:$PWD/packages/worldkeeper/src TMPDIR=/tmp
[ -e .venv ] || ln -s @REPO@/.venv .venv
git add -A -- factory tests
bad=$(git diff --cached --name-only | grep -vE '^(@OWNED_RE@)$' || true)
[ -z "$bad" ] || { echo "files outside ownership staged: $bad"; exit 1; }
git diff --cached --name-only | grep -q 'factory/stations/probe.py' || { echo "probe.py unchanged"; exit 1; }
git diff --cached --name-only | grep -q 'tests/test_factory_probe.py' || { echo "tests unchanged"; exit 1; }
start=$(date +%s)
.venv/bin/python -m pytest -q -p no:cacheprovider -n 8 tests/test_factory_probe.py tests/test_factory_probe_routing.py tests/test_factory_line.py tests/test_factory_diagnose.py tests/test_factory_fix_plan.py tests/test_factory_planner.py tests/test_factory_live_playtest.py
took=$(( $(date +%s) - start ))
echo "factory tests took $took s (budget 300 s)"
[ "$took" -le 300 ] || { echo "over the 300 s budget"; exit 1; }
.venv/bin/python -m ruff check factory/stations/probe.py tests/test_factory_probe.py
.venv/bin/python -m ruff format --check factory/stations/probe.py tests/test_factory_probe.py
@EXTRA@
git diff --cached > "$WORK/out/@NAME@.patch"
test -s "$WORK/out/@NAME@.patch"
"""

EXTRA = {
    "d1": "grep -q failed_replicates factory/stations/probe.py || { echo 'failed_replicates missing'; exit 1; }",
    "d2": "grep -q probe-attempt factory/stations/probe.py || { echo 'probe-attempt sidecar missing'; exit 1; }\ngrep -q MAX_RESUMES factory/stations/probe.py || { echo 'MAX_RESUMES missing'; exit 1; }",
}


def build(which: str) -> dict:
    def fill(text: str) -> str:
        return (
            text.replace("@REPO@", REPO)
            .replace("@WORK@", WORK)
            .replace("@AUDIT@", AUDIT)
            .replace("@OWNED_RE@", "|".join(path.replace(".", "\\.") for path in OWNED))
            .replace("@EXTRA@", EXTRA[which])
            .replace("@NAME@", f"probe-{which}")
        )

    spec = COMMON + (D1 if which == "d1" else D2)
    return {
        "run_name": f"factory-20{'a' if which == 'd1' else 'b'}-probe-{which}",
        "workdir": WORK,
        "max_parallel": 1,
        "worktrees": True,
        "repo": REPO,
        "tasks": [
            {
                "key": f"probe-{which}",
                "task_type": "code-fix",
                "engine": "codex",
                "engine_args": ["-c", "model_reasoning_effort=high"],
                "max_attempts": 2,
                "timeout_s": 3600,
                "check_timeout_s": 900,
                "ownership": OWNED,
                "spec": fill(spec),
                "check": fill(CHECK),
                "expect_files": [],
                "verified": "The probe counts failed replicates and cannot rebill on a resume."
                if which == "d2"
                else "Failed replicates are counted and force an inconclusive verdict.",
            }
        ],
    }


if __name__ == "__main__":
    which = sys.argv[1] if len(sys.argv) > 1 else "d1"
    out = Path(__file__).with_name(f"round20{'a' if which == 'd1' else 'b'}-probe-{which}-manifest.json")
    out.write_text(json.dumps(build(which), indent=2) + "\n")
    print(out)
