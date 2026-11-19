# ruff: noqa: E501  (spec strings are prose briefs for a worker)
"""Round 10c: judge calibration tooling (factory step 4): noise-corrected gates, a frozen-question lock and a second-judge agreement monitor.

All of it is free and deterministic; no billed model is called. Two parallel tasks with disjoint files.

Usage: build_round10c_manifest.py
"""

from __future__ import annotations

import json
from pathlib import Path

REPO = "/home/bcorfman/dev/freytag-forge"
WORK = "/home/bcorfman/dev/ringer-work/factory-judges"

COMMON = f"""You are a Python engineer. Your current working directory IS a git worktree of {REPO} (detached at HEAD). Edit files here directly. NEVER git commit, never touch {REPO} itself, never run `uv`, never call a model or the network. FIRST run: [ -e .venv ] || ln -s {REPO}/.venv .venv . Ruff: `.venv/bin/python -m ruff check <files>` and `.venv/bin/python -m ruff format <files>` (line length 120, double quotes, Python 3.12, no new dependencies, standard library only). Never pass --cov to pytest. Run tests as `PYTHONPATH=$PWD:$PWD/packages/worldkeeper/src TMPDIR=/tmp .venv/bin/python -m pytest -q -p no:cacheprovider -n 0 <test files>`.

BACKGROUND. The story factory runs with no human reading its output, so its judges (Jev and others, under `bench/*-judge.mjs`) must be measured and guarded. Rules from the plan: (1) judge questions are frozen when the factory starts and checked against the author's labelled sets in `bench/calibration/` (read `bench/calibration/README.md` and `bench/calibration/check_calib.py` first: labels are `yes`/`no` strings per turn per label); (2) rate gates use the judge's measured error rates on the labelled set and pass on the LOWER BOUND of the corrected rate, not the raw score; (3) a second judge re-scores a slice of every batch, and a disagreement rate above the noise already measured (about 3 in 100) pauses that judge's verdicts and falls back to the stricter one. Everything lives in the new package `factory/judges/` (already listed as frozen harness in `factory/config/frozen.json`; do not edit that file). Match the style of `factory/verdicts.py` and `factory/checks/gap_delta.py`.
"""

SPEC_A = (
    COMMON
    + """
YOUR TASK (A): create `factory/judges/__init__.py` (a docstring only), `factory/judges/stats.py`, `factory/judges/calibration.py` and `tests/test_factory_judge_calibration.py`. Own nothing else.

stats.py:
- `wilson_interval(successes: int, n: int, z: float = 1.96) -> tuple[float, float]`: the Wilson score interval; n == 0 gives (0.0, 1.0). Raise ValueError if successes is outside 0..n.
- `@dataclass(frozen=True) class ErrorRates: sensitivity_hits: int; sensitivity_n: int; specificity_hits: int; specificity_n: int` (sensitivity = share of truly-positive cells the judge called positive; specificity = share of truly-negative cells it called negative).
- `corrected_lower_bound(successes: int, n: int, rates: ErrorRates, z: float = 1.96) -> float`: the lower bound of the TRUE rate behind an observed rate of successes/n, correcting for judge error (Rogan-Gladen): true = (p + spec - 1) / (sens + spec - 1). Be conservative: use p = Wilson lower bound of successes/n, spec = Wilson LOWER bound of specificity, sens = Wilson UPPER bound of sensitivity. If the denominator (sens + spec - 1) is <= 0 return 0.0. Clip the result to [0, 1].
- `gate_passes(successes: int, n: int, target: float, rates: ErrorRates, z: float = 1.96) -> bool`: True only when corrected_lower_bound >= target.

calibration.py: measure saved judge output against labels, exactly as check_calib.py does it (same inputs, same skipping of unlabelled turns and the `superseded` block, same turn keys `replicate:turn_number`), but returning data:
- `@dataclass class LabelMeasure: label: str; agree: int; total: int; tp: int; fn: int; tn: int; fp: int` (positive means the label value is "yes"; a label whose expected values are not yes/no leaves the four counts 0). Add properties `rate`, `wilson_low`.
- `@dataclass class JudgeMeasure: block: str; agree: int; total: int; labels: dict[str, LabelMeasure]`, with `rate`, `wilson_low` and `error_rates() -> ErrorRates` (sums the confusion counts over its labels: sensitivity from tp and tp+fn, specificity from tn and tn+fp).
- `measure(labels_path: Path, judgments_dir: Path | None = None, records_path: Path | None = None) -> dict[str, JudgeMeasure]` for the blocks "continuity" and "fact" (files continuity-judgments.json and fact-tracking-judgments.json; defaults for judgments_dir and records_path come from the label file's `results_dir`, as in check_calib.py). A missing judgments file raises FileNotFoundError.
- `write_error_rates(measures, path)` and `load_error_rates(path) -> dict[str, ErrorRates]`: JSON round trip, keyed by block name.
- CLI `python -m factory.judges.calibration --labels FILE [--judgments DIR] [--records FILE] [--bar 0.9] [--raw] [--out error_rates.json]` (expose `main(argv=None) -> int`): prints per block `block: agree/total = rate (Wilson low X)` and, per label, the same; writes the error rates when --out is given; exit 1 when any block's Wilson LOWER bound is below --bar (with --raw: when the raw rate is below it, as check_calib.py does), 2 when a file is missing, else 0. Never write calibration-report.md next to the judgments (the old checker does; this tool must not modify bench/).

TESTS (tests/test_factory_judge_calibration.py, hermetic, build tiny label and judgment files in tmp_path in the formats check_calib.py reads; see how it names `all-turn-records.json` runs and turns): Wilson interval known values (e.g. 0/0, 10/10, 50/100 within 0.001 of the textbook interval 0.4038..0.5962), successes out of range, corrected_lower_bound is below the raw rate for an imperfect judge and equals roughly the Wilson lower bound for a perfect judge (sens = spec = 1 with large n), is 0.0 when sens + spec <= 1, never above 1; gate_passes both ways; measure() on a tiny corpus with a known confusion matrix (check tp/fn/tn/fp and the agree/total); unlabelled and superseded cells skipped; the error-rate JSON round trip; the CLI exit codes 0, 1 and 2 and `--raw`; and that measure() does not write any file into the judgments directory.

HARD LIMITS. Edit only the four files above. Never edit bench/, factory/config/, other factory modules or other tests. Write NOTES_10c_A.txt (worktree root, never committed) for every rule you found ambiguous and the choice you made.
"""
)

SPEC_B = (
    COMMON
    + """
YOUR TASK (B): create `factory/judges/lock.py`, `factory/judges/agreement.py`, `tests/test_factory_judge_guards.py`. Own nothing else. Do NOT create `factory/judges/__init__.py` (another worker creates it; `factory.judges` works as a namespace package in your worktree, so your tests import `factory.judges.lock` and `factory.judges.agreement` directly).

lock.py: freeze judge questions by content hash.
- `DEFAULT_PATTERNS = ("bench/*-judge.mjs", "bench/calibration/labels-*.json", "bench/calibration/check_calib.py")` and `DEFAULT_LOCK = "factory/state/judge-lock.json"`.
- `compute(root: Path, patterns=DEFAULT_PATTERNS) -> dict[str, str]`: repo-relative POSIX path -> sha256 hex of the file bytes, sorted by path, for every file the patterns match under root (use Path.glob; no pattern may escape root).
- `write(root, lock_path=None, patterns=DEFAULT_PATTERNS) -> dict[str, str]`: write the compute() result as indented JSON with a trailing newline (create parent directories) and return it.
- `check(root, lock_path=None, patterns=DEFAULT_PATTERNS) -> list[str]`: one line per difference, `changed PATH`, `missing PATH` (in the lock, gone from disk), `new PATH` (on disk, not in the lock); empty when equal. A lock file that does not exist raises FileNotFoundError.
- CLI `python -m factory.judges.lock write|check [--root DIR] [--lock FILE]` (expose `main(argv=None) -> int`; root defaults to the repository root, two parents above `factory/`): `write` prints `locked N files`, exit 0; `check` prints the difference lines or `ok`, exit 0 when equal, 1 on any difference, 2 when the lock file is missing. Do NOT commit a lock file: writing it is a pre-flight step for the owner.

agreement.py: the second-judge monitor.
- `select_slice(ids: list[str], fraction: float = 0.1, salt: str = "", minimum: int = 20) -> list[str]`: deterministic, order-independent slice of ids for the second judge: rank ids by sha256(salt + id) and take the first max(minimum, ceil(fraction * len(ids))) of them (never more than len(ids)); return them in the original input order. Raises ValueError for a fraction outside (0, 1].
- `@dataclass(frozen=True) class Pair: id: str; primary: bool; secondary: bool` (verdicts: True means the judge passed the item).
- `disagreement_rate(pairs) -> float` (0.0 for no pairs).
- `@dataclass(frozen=True) class Decision: status: str; rate: float; pairs: int; paused: bool` with status "ok", "paused" or "insufficient".
- `evaluate(pairs, noise: float = 0.03, min_pairs: int = 20) -> Decision`: fewer pairs than min_pairs gives status "insufficient" (paused False); a rate strictly above noise gives "paused" (paused True); otherwise "ok".
- `stricter(primary: bool, secondary: bool) -> bool`: the effective verdict while a judge is paused: passes only when both pass.
- `class MonitorState`: a small JSON-backed record `{judge_name: {"paused": bool, "last_rate": float, "pairs": int}}` with `__init__(path)`, `get(judge) -> dict`, `record(judge, decision: Decision)` (saves immediately; a paused judge STAYS paused on a later "ok" or "insufficient" decision until `clear(judge)` is called, because the plan has no automatic recovery), `clear(judge)`, `is_paused(judge) -> bool`, and `effective(judge, primary, secondary) -> bool` (returns `stricter(...)` when the judge is paused, else `primary`). Writes are atomic (write a temp file then os.replace).
- CLI `python -m factory.judges.agreement --pairs FILE.json --judge NAME [--state FILE] [--noise 0.03] [--min-pairs 20]` (expose `main(argv=None) -> int`; the pairs file is a JSON list of {"id", "primary", "secondary"}; the state default is `factory/state/judge-monitor.json`): prints `NAME: status rate over N pairs`, records the decision in the state, exit 0 for ok or insufficient, 1 for paused, 2 for an unreadable pairs file.

TESTS (tests/test_factory_judge_guards.py, hermetic, tmp_path only): lock: compute/write/check round trip on a tiny tree, each of changed, missing and new, the missing-lock error, the CLI exit codes 0, 1 and 2, and that a pattern cannot match outside root; slice: deterministic, order independent, respects the minimum and never exceeds the list, bad fraction; agreement: rate, evaluate at the boundaries (exactly 3 percent of 100 pairs is ok, 4 of 100 is paused, 19 pairs is insufficient), stricter truth table, MonitorState persistence across instances, a paused judge staying paused after an ok decision until cleared, effective(); the CLI including its state file.

HARD LIMITS. Edit only the three files above. Never edit bench/, factory/config/, other factory modules or other tests. Write NOTES_10c_B.txt (worktree root, never committed) for every rule you found ambiguous and the choice you made.
"""
)


def check_a() -> str:
    return f"""set -eo pipefail
[ -e .venv ] || ln -s {REPO}/.venv .venv
export PYTHONPATH=$PWD:$PWD/packages/worldkeeper/src TMPDIR=/tmp
out=$(mktemp)
rc=0
.venv/bin/python -m pytest -q -p no:cacheprovider -n 0 -rs tests/test_factory_judge_calibration.py > "$out" 2>&1 || rc=$?
tail -6 "$out"
[ "$rc" -eq 0 ] || exit "$rc"
if grep -E "SKIPPED|XFAIL|xfailed" "$out"; then echo "a test skips or xfails"; exit 1; fi
# independent probe: the new measure() agrees with the old checker on the real round 9 corpus
before=$(git status --porcelain -- bench | wc -l)
old=$(mktemp -d); cp {REPO}/bench/results/item-facts-v10-two-scene-1a/*.json "$old"/
.venv/bin/python bench/calibration/check_calib.py --labels bench/calibration/labels-round9.json --bar 0.0 --judgments "$old" --records "$old/all-turn-records.json" | grep '^## ' | sed -E 's/ = .*//' > "$out.old"
cat "$out.old"
.venv/bin/python -m factory.judges.calibration --labels bench/calibration/labels-round9.json --judgments "$old" --records "$old/all-turn-records.json" --raw --bar 0.0 --out "$out.rates.json" | tee "$out.new"
for block in continuity fact; do
  want=$(grep "^## $block" "$out.old" | sed -E 's/.*: //')
  grep -E "^$block" "$out.new" | head -1 | grep -q "$want" || {{ echo "block $block: new tool disagrees with check_calib (wanted $want)"; exit 1; }}
done
.venv/bin/python - "$out.rates.json" <<'PY'
import json, sys
d = json.load(open(sys.argv[1]))
assert set(d) >= {{"continuity", "fact"}}, d.keys()
print("rates file ok")
PY
after=$(git status --porcelain -- bench | wc -l)
[ "$before" -eq "$after" ] || {{ echo "bench/ was modified"; exit 1; }}
.venv/bin/python -m ruff check factory/judges tests/test_factory_judge_calibration.py
.venv/bin/python -m ruff format --check factory/judges tests/test_factory_judge_calibration.py
git add -A -- factory tests
bad=$(git diff --cached --name-only | grep -v -x -e factory/judges/__init__.py -e factory/judges/stats.py -e factory/judges/calibration.py -e tests/test_factory_judge_calibration.py || true)
[ -z "$bad" ] || {{ echo "files outside ownership staged: $bad"; exit 1; }}
git diff --cached > {WORK}/judges-a.patch
test -s {WORK}/judges-a.patch
"""


def check_b() -> str:
    return f"""set -eo pipefail
[ -e .venv ] || ln -s {REPO}/.venv .venv
export PYTHONPATH=$PWD:$PWD/packages/worldkeeper/src TMPDIR=/tmp
out=$(mktemp)
rc=0
.venv/bin/python -m pytest -q -p no:cacheprovider -n 0 -rs tests/test_factory_judge_guards.py > "$out" 2>&1 || rc=$?
tail -6 "$out"
[ "$rc" -eq 0 ] || exit "$rc"
if grep -E "SKIPPED|XFAIL|xfailed" "$out"; then echo "a test skips or xfails"; exit 1; fi
# independent probe: lock the real judge files in a scratch lock, verify, then change a copy and see it caught
lock=$(mktemp -d)/judge-lock.json
.venv/bin/python -m factory.judges.lock write --lock "$lock" | grep -q "locked" || {{ echo "lock write failed"; exit 1; }}
.venv/bin/python -m factory.judges.lock check --lock "$lock" | grep -qx ok || {{ echo "fresh lock does not check ok"; exit 1; }}
scratch=$(mktemp -d); mkdir -p "$scratch/bench/calibration"
cp bench/*-judge.mjs "$scratch/bench/"; cp bench/calibration/labels-*.json bench/calibration/check_calib.py "$scratch/bench/calibration/"
.venv/bin/python -m factory.judges.lock write --root "$scratch" --lock "$scratch/lock.json" >/dev/null
echo "// edit" >> "$scratch/bench/jev-judge.mjs"
rc=0; .venv/bin/python -m factory.judges.lock check --root "$scratch" --lock "$scratch/lock.json" > "$out" 2>&1 || rc=$?
cat "$out"
[ "$rc" -eq 1 ] || {{ echo "a changed judge file must exit 1, got $rc"; exit 1; }}
grep -q "changed bench/jev-judge.mjs" "$out" || {{ echo "change not reported"; exit 1; }}
test ! -e factory/state/judge-lock.json || {{ echo "a lock file must not be committed"; exit 1; }}
# the monitor: 4 disagreements in 100 pause the judge and it stays paused
pairs=$(mktemp --suffix=.json)
.venv/bin/python - "$pairs" <<'PY'
import json, sys
json.dump([{{"id": f"q{{i}}", "primary": True, "secondary": i >= 4}} for i in range(100)], open(sys.argv[1], "w"))
PY
state=$(mktemp -d)/monitor.json
rc=0; .venv/bin/python -m factory.judges.agreement --pairs "$pairs" --judge jev --state "$state" > "$out" 2>&1 || rc=$?
cat "$out"
[ "$rc" -eq 1 ] || {{ echo "4 of 100 disagreements must pause (exit 1), got $rc"; exit 1; }}
.venv/bin/python -m ruff check factory/judges tests/test_factory_judge_guards.py
.venv/bin/python -m ruff format --check factory/judges tests/test_factory_judge_guards.py
git add -A -- factory tests
bad=$(git diff --cached --name-only | grep -v -x -e factory/judges/lock.py -e factory/judges/agreement.py -e tests/test_factory_judge_guards.py || true)
[ -z "$bad" ] || {{ echo "files outside ownership staged: $bad"; exit 1; }}
git diff --cached > {WORK}/judges-b.patch
test -s {WORK}/judges-b.patch
"""


def task(key: str, spec: str, check: str, owned: list[str], verified: str) -> dict:
    return {
        "key": key,
        "task_type": "code-feature",
        "engine": "codex",
        "engine_args": ["-c", "model_reasoning_effort=high"],
        "max_attempts": 2,
        "timeout_s": 2400,
        "check_timeout_s": 400,
        "ownership": owned,
        "spec": spec,
        "check": check,
        "expect_files": [],
        "verified": verified,
    }


def build() -> dict:
    return {
        "run_name": "factory-judges",
        "workdir": WORK,
        "max_parallel": 2,
        "worktrees": True,
        "repo": REPO,
        "tasks": [
            task(
                "calibration",
                SPEC_A,
                check_a(),
                [
                    "factory/judges/__init__.py",
                    "factory/judges/stats.py",
                    "factory/judges/calibration.py",
                    "tests/test_factory_judge_calibration.py",
                ],
                "Wilson and corrected lower bound tests green; measure() agrees with check_calib.py on the real round 9 corpus; bench/ untouched; ruff clean; only four files changed.",
            ),
            task(
                "guards",
                SPEC_B,
                check_b(),
                [
                    "factory/judges/lock.py",
                    "factory/judges/agreement.py",
                    "tests/test_factory_judge_guards.py",
                ],
                "Lock and agreement tests green; an independent probe catches a changed judge file and pauses a judge at 4 disagreements in 100; no lock file committed; ruff clean; only three files changed.",
            ),
        ],
    }


if __name__ == "__main__":
    out = Path(__file__).with_name("round10c-manifest.json")
    out.write_text(json.dumps(build(), indent=2) + "\n", encoding="utf-8")
    print(out)
