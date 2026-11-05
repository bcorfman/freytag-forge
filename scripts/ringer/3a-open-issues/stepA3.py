# ruff: noqa: E501
"""Step A leftover: rejudge a frozen bench run with the corrected judge input against the package AT ITS OWN REVISION. Judge calls only; no narrator neurons."""

import json
from pathlib import Path

REPO = "/home/bcorfman/dev/freytag-forge"
OUT = "/home/bcorfman/dev/ringer-work/3a-open-issues-stepA3"
RUN4 = f"{REPO}/bench/results/richer-3a-probe/candidate-run4"

SPEC = f"""Your current working directory IS a git worktree of {REPO} (detached at HEAD). Edit files here directly. NEVER git commit, never touch the main checkout, never run `uv`, never call a billed model, MCP indexing or the network, and never run `python -m bench run`, `node bench/*-judge*.mjs` or any script that calls a model: a later CHECK step runs the judges, you must not. FIRST run: [ -e .venv ] || ln -s {REPO}/.venv .venv ; then run tests as `PYTHONPATH=$PWD:$PWD/packages/worldkeeper/src TMPDIR=/tmp .venv/bin/python -m pytest -q -p no:cacheprovider <tests>` (PYTHONPATH must include $PWD/packages/worldkeeper/src). Ruff: `.venv/bin/python -m ruff check <py files>` and `-m ruff format <py files>`. Leave changes uncommitted. Work TESTS FIRST.

ROLE: bench engineer. You may edit/create ONLY: bench/rejudge_frozen.py (new) and tests/test_rejudge_frozen.py (new).

PURPOSE: old bench runs (for example bench/results/richer-3a-probe/candidate-run4/) saved `all-turn-records.json` whose `package_path` points at the CURRENT story package. The judges rebuild the story-authored text of each turn from that package (bench/judge_input.py `judge_turns` -> `_story_text`, which reconstructs delivery text and bridges for legacy records that have no `authored_segments`). If the package has changed since the run (it has: a delivery was reworded after run4), the reconstruction is wrong. A rejudge must therefore reconstruct against the package AT THE RUN'S OWN REVISION, and must keep the original verdicts untouched.

BUILD bench/rejudge_frozen.py (importable, plus `python -m bench.rejudge_frozen --records DIR --revision GITREV --out OUTDIR [--judges continuity,fact] [--dry-run]`):
1. Read DIR/all-turn-records.json. Extract the story package directory recorded in `package_path` (take its path relative to the repository root, e.g. data/stories/continuity-initiative) AS IT WAS at GITREV into a fresh temporary directory with `git archive GITREV -- <relative package dir>` piped into tar (run git from the repository root; raise a clear error if the revision or path does not exist; never write inside the repo's tracked tree). Use only the standard library plus what bench already imports.
2. Write OUTDIR/all-turn-records.json: a copy of the records with ONLY `package_path` rewritten to the extracted directory and a new top-level key `rejudge` = {{"source_records": DIR, "revision": GITREV, "original_package_path": ..., "provenance": "reconstructed"}}. Never modify DIR. Refuse (error) if OUTDIR equals DIR.
3. Unless --dry-run, run the judges named by --judges (default both) through the EXISTING functions in bench/core.py, `run_continuity_judges(input_path, output_path)` and `run_fact_tracking_judges(input_path, output_path)`, writing OUTDIR/continuity-judgments.json and OUTDIR/fact-tracking-judgments.json (the functions apply judge_turns themselves; do not reimplement judge input). Do not catch and hide judge errors: let a failure exit non-zero with the message. After the judges, write OUTDIR/rejudge-summary.json: per judge the `judge_calls`, the per-criterion yes counts across all turns (read the structure of the existing DIR/continuity-judgments.json and DIR/fact-tracking-judgments.json to get the field names right, for example restarts_scene, protagonist_acts_beyond_command, contradicts_stated_fact, missed_change, invented_change, facts_after_correct), the SAME counts computed from the ORIGINAL judgments in DIR, and a `deltas` list naming every (replicate, turn, criterion) whose answer changed between the original and the rejudge, with both answers. Also record the story-text provenance counts from `judge_turns` (how many turns were 'reconstructed' versus 'recorded').
4. --dry-run extracts the package, writes the records copy, prints what it would run, calls no judge, and exits 0.

TESTS (first, offline; the judge functions are monkeypatched with fakes returning a small canned judgments structure shaped like the real files; no network, no .env, no node): (a) the git archive extraction at a known revision returns the package files as of that revision, proven with a TEMPORARY git repo created in tmp_path (commit a tiny package dir, change it, commit again, extract the first revision, assert the old text); (b) the records copy changes only package_path and adds `rejudge`; the source dir is untouched; (c) OUTDIR equal to DIR is refused; (d) a bad revision raises a clear error; (e) the summary computes counts and a delta list from fake original and rejudged judgments; (f) --dry-run calls no judge. Run tests/test_rejudge_frozen.py tests/test_bench.py tests/test_judge_input.py.

FINAL MESSAGE: the CLI usage line, the extraction method, and the summary file structure.
"""

CHECK = (
    r"""set -o pipefail
[ -e .venv ] || ln -s REPO/.venv .venv
WT=$PWD
export PYTHONPATH=$WT:$WT/packages/worldkeeper/src TMPDIR=/tmp
PY=$WT/.venv/bin/python
CH=$(git status --porcelain | grep -v '^?? .venv' | awk '{print $2}' | sort)
[ -n "$CH" ] || { echo "WHY: nothing changed"; exit 1; }
for f in $CH; do case "$f" in bench/rejudge_frozen.py|tests/test_rejudge_frozen.py) ;; *) echo "WHY: edited file outside ownership: $f"; exit 1;; esac; done
$PY -m pytest -q -p no:cacheprovider tests/test_rejudge_frozen.py tests/test_bench.py tests/test_judge_input.py > /tmp/ta3.out 2>&1; rc=$?; tail -15 /tmp/ta3.out; [ $rc -eq 0 ] || { echo "WHY: suites failed"; exit 1; }
PYF=$(echo "$CH" | grep '\.py$')
$PY -m ruff check $PYF || { echo "WHY: ruff check failed"; exit 1; }
$PY -m ruff format --check $PYF || { echo "WHY: ruff format failed"; exit 1; }
# dry run first (no judge call), from the MAIN checkout so .env and the run records resolve
rm -rf OUTDIR/run4-rejudged
( cd REPO && PYTHONPATH=$WT:$WT/packages/worldkeeper/src $PY -m bench.rejudge_frozen --records RUN4 --revision 7c7f1f6d --out OUTDIR/run4-rejudged --dry-run ) || { echo "WHY: dry run failed"; exit 1; }
test -s OUTDIR/run4-rejudged/all-turn-records.json || { echo "WHY: dry run wrote no records copy"; exit 1; }
rm -rf OUTDIR/run4-rejudged
( cd REPO && PYTHONPATH=$WT:$WT/packages/worldkeeper/src $PY -m bench.rejudge_frozen --records RUN4 --revision 7c7f1f6d --out OUTDIR/run4-rejudged ) || { echo "WHY: rejudge failed"; exit 1; }
$PY - <<'E' || exit 1
import json
s=json.load(open('OUTDIR/run4-rejudged/rejudge-summary.json'))
txt=json.dumps(s)
for k in ('deltas','judge_calls'):
    assert k in txt, f'summary lacks {k}'
c=json.load(open('OUTDIR/run4-rejudged/continuity-judgments.json')); f=json.load(open('OUTDIR/run4-rejudged/fact-tracking-judgments.json'))
assert len(c['judgments'])==4 and len(f['judgments'])==4, 'expected 4 replicates judged by both'
print('rejudge ok; judge_calls', c.get('judge_calls'), f.get('judge_calls'))
E
git add bench/rejudge_frozen.py tests/test_rejudge_frozen.py && git diff --cached > OUTDIR/stepA3.patch && wc -l OUTDIR/stepA3.patch && git diff --cached --stat | tail -4
""".replace("OUTDIR", OUT)
    .replace("REPO", REPO)
    .replace("RUN4", RUN4)
)

manifest = {
    "run_name": "3a-open-issues-stepA3",
    "workdir": OUT,
    "max_parallel": 1,
    "worktrees": True,
    "repo": REPO,
    "tasks": [
        {
            "key": "rejudge-run4",
            "task_type": "code-fix",
            "engine": "codex",
            "model": "gpt-5.6-luna",
            "engine_args": ["-c", "model_reasoning_effort=high"],
            "max_attempts": 1,
            "timeout_s": 3000,
            "check_timeout_s": 1800,
            "ownership": ["bench/rejudge_frozen.py", "tests/test_rejudge_frozen.py"],
            "spec": SPEC,
            "check": CHECK,
            "expect_files": [],
            "verified": "tool built tests-first; run4 rejudged against its own package revision; summary lists changed verdicts",
        }
    ],
}
Path(__file__).with_name("stepA3-manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")
print("wrote")
