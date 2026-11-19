# ruff: noqa: E501  (spec strings are prose briefs for a worker)
"""Build the Ringer manifest that retires probe and experiment scripts with their tests (task 1), and adds the nightly per-test coverage report (task 2)."""

from __future__ import annotations

import json
import re
import subprocess
from pathlib import Path

REPO = "/home/bcorfman/dev/freytag-forge"
WORK = "/home/bcorfman/dev/ringer-work/probe-retire"
HERE = Path(__file__).resolve().parent

PROBE_TESTS = [
    "act2_guard_probe", "act2_probe", "act3a_probe", "act3c_probe", "boarding_probe", "defect_probe",
    "drain_condition_judge_probe", "drain_details_prose_probe", "drain_question_probe", "drain_replay_probe",
    "hidden_bench_arm_probe", "hidden_bench_matcher_probe", "hidden_bench_prose_probe", "holder_wording_probe",
    "j1_scope_probe", "j1_screen_probe", "j1c_wiring_probe", "jev_boarding_probe", "open_probe",
    "opening_truck_probe", "opening_truck_probe2", "opening_truck_probe3", "opening_truck_probe4",
    "opens_container_probe", "opens_container_probe_v2", "opens_container_probe_v3", "slice_probe",
    "under_question_probe", "under_question_probe_v2", "under_question_probe_v4",
    "frozen_decode", "rejudge_frozen",
]  # fmt: skip
WHOLE_DIRS = ("scripts/ringer/opening_truck/", "scripts/ringer/phase1/", "scripts/ringer/phase2/")
PROBE_DIRS = ("defect_probe", "drain_probe", "holder_probe", "opens_probe", "under_probe")


def tracked() -> list[str]:
    out = subprocess.run(["git", "ls-files"], cwd=REPO, capture_output=True, text=True, check=True).stdout
    return [line for line in out.splitlines() if line]


def seed_list() -> list[str]:
    files = tracked()
    keep_tests = {f"tests/test_{n}.py" for n in PROBE_TESTS}
    seed: set[str] = {f for f in files if f in keep_tests}
    seed |= {f for f in files if f.startswith("tests/fixtures/opening_truck_probe")}
    seed |= {"bench/frozen_decode.py", "bench/rejudge_frozen.py"} & set(files)
    for f in files:
        if f.startswith(WHOLE_DIRS):
            seed.add(f)
        if f.startswith(("scripts/ringer/environment_narration/", "scripts/ringer/transcript_1a/")):
            parts = f.split("/")
            if re.search(r"probe", parts[-1]) or any(p in PROBE_DIRS for p in parts[3:-1]):
                seed.add(f)
        if f.startswith("scripts/ringer/3a-open-issues/") and re.match(
            r"scripts/ringer/3a-open-issues/(stepD1V|stepA3)[-.]", f
        ):
            seed.add(f)
    return sorted(seed)


SEED = seed_list()
RETIRE_LIST = f"{WORK}/retire-list.txt"
CHECK_SCRIPT = f"{HERE}/check_retire.py"

COMMON = (
    "Your current working directory IS a git worktree of "
    + REPO
    + " (detached at HEAD). Edit files here directly. NEVER git commit, never touch "
    + REPO
    + " itself, never run `uv`, never call a billed model or the network. FIRST run: [ -e .venv ] || ln -s "
    + REPO
    + "/.venv .venv . Run tests as `PYTHONPATH=$PWD:$PWD/packages/worldkeeper/src TMPDIR=/tmp .venv/bin/python -m pytest -q -p no:cacheprovider -n 0 <files>` (never pass --cov); ruff as `.venv/bin/python -m ruff check <files>` (line length 120, double quotes)."
)

SPEC_RETIRE = (
    "You are a Python engineer retiring finished experiments. "
    + COMMON
    + f"""

WHAT AND WHY. The project owner decided to remove the probe and experiment scripts under scripts/ringer/ together with the tests that exist only to test them. They were one-off experiments, they are finished, and their tests cost about a fifth of the suite's run time. Git history keeps them. The exact starting list is in {RETIRE_LIST} (one repository-relative path per line, {len(SEED)} paths: probe tests under tests/, tests/fixtures/opening_truck_probe*, bench/frozen_decode.py, bench/rejudge_frozen.py, whole folders scripts/ringer/opening_truck, scripts/ringer/phase1, scripts/ringer/phase2, probe-named files and probe data folders inside scripts/ringer/environment_narration and scripts/ringer/transcript_1a, and the 3a-open-issues stepD1V/stepA3 scripts that import the two bench modules).

STEP 1. Remove every path in the list with `git rm -q --ignore-unmatch`. Do it in one pass from the list file.

STEP 2. Find fallout and repair it, never by editing the product. Search the SURVIVING files (everything outside scripts/ringer/ run folders counts: tests/, storygame/, bench/, factory/, packages/, docs/, .github/, pyproject.toml; also surviving Python under scripts/ringer/stage7, story-data, dark-factory, gates and environment_narration; Python in the other scripts/ringer folders is a historical run record and may keep dangling imports, leave it) for any import, path or name of a removed file (for example `scripts.ringer.phase1`, `opening_truck`, `hidden_bench_arm_probe`, `bench.frozen_decode`, `frozen_decode`, `rejudge_frozen`). For each hit decide:
  (a) the hit is only a docs or comment mention, or a historical manifest or run script under scripts/ringer outside the live folders: leave it, except fix a docs sentence under docs/ that tells a reader to run a removed script by deleting that sentence or pointing it at nothing.
  (b) a surviving test or product module really imports the removed file: RESTORE that one removed file with `git checkout HEAD -- <path>` (and whatever it needs), and record the path and the importer in NOTES_retire.txt at the worktree root (never committed). Do not delete or rewrite the surviving importer.
Also a pytest `conftest.py`, `pyproject.toml` `pythonpath`/ruff per-file-ignores or a `.github` workflow may name a removed path: remove just that entry.

STEP 3. Do NOT touch: anything under scripts/ringer/stage7 (its probes are the documented live bench procedure), bench/frozen_prompts.py and its test, bench/exit_audit.py, bench/frozen/, bench/variations/, bench/results/, tests/shard_durations.json (the orchestrator regenerates it), tests/story_source, data/, storygame/, packages/, factory/, .plans/. Never weaken a surviving test.

DONE WHEN `PYTHONPATH=$PWD:$PWD/packages/worldkeeper/src TMPDIR=/tmp .venv/bin/python -m pytest --collect-only -q -p no:cacheprovider -n 0 tests scripts/ringer/stage7` exits 0 with no import errors, `ruff check` is clean on any Python file you changed, and the surviving tests that sit closest to the removed code pass: tests/test_enforce_report*.py tests/test_enforce_drain_report.py tests/test_drain_condition_corpus.py tests/test_drain_condition_heldout.py tests/test_package_audit.py tests/test_exit_audit.py tests/test_frozen_prompts.py. If a restored file (step 2b) is the only thing blocking, that is fine; say so in NOTES_retire.txt."""
)

SPEC_COVERAGE = (
    "You are a Python engineer. "
    + COMMON
    + """

BACKGROUND. The nightly workflow .github/workflows/coverage-context-report.yml already runs the whole suite with `uv run pytest -q --cov --cov-context=test --tier-report=...` and uploads artifacts/, but the artifact has timings only; the per-test coverage data (the `.coverage` SQLite file, with one context per test such as `tests/test_x.py::test_y|run`) is thrown away. The owner wants to find redundant tests: tests whose coverage adds nothing.

YOUR JOB.
1. Create scripts/coverage_redundancy.py (stdlib plus `coverage`, already a dev dependency; check pyproject.toml). `python scripts/coverage_redundancy.py <coverage-data-file> --out <json>` reads the data with `coverage.CoverageData`, treats each distinct test id as one test (strip the phase suffix after `|`: `|run`, `|setup`, `|teardown`; merge their lines), and writes JSON with: `tests` (count), `files` (count), and a list `per_test` of objects {id, lines (count of distinct file:line it covers), unique_lines (lines no other test covers), subset_of (up to 3 ids of other tests whose covered lines are a superset; empty when none)}, sorted so tests with `unique_lines == 0` come first, then by `lines` ascending. Also a top-level list `no_unique_lines` of test ids with zero unique lines, and `identical_groups`: groups of 2+ test ids with exactly equal covered line sets. Use inverted indexes (line -> set of tests) so it stays fast for about 4,800 tests and a few hundred thousand covered lines; no all-pairs set comparison over every test (compute subset_of only for tests with zero unique lines, using the inverted index). Exit 0 on success; exit 2 with a clear message on a missing or empty data file.
2. Create tests/test_coverage_redundancy.py: hermetic tests that build a small synthetic coverage data file in tmp_path with `coverage.CoverageData(basename=...)` (`set_context`, `add_lines`, `write`), run the script's main function, and assert: a test that covers a strict subset of another is listed under no_unique_lines with that other test in subset_of; two tests with identical lines form an identical group; a test with one private line has unique_lines == 1; phase suffixes `|setup` and `|run` of one test merge into one test; a missing file exits 2. Import the script as a module (put the logic in functions and `main(argv)`), never start a subprocess that needs uv. Never pass --cov.
3. Edit .github/workflows/coverage-context-report.yml: after the "Run context coverage report" step add a step `Build per-test redundancy report` (runs `if: always()`) with `TMPDIR=/tmp uv run python scripts/coverage_redundancy.py .coverage --out artifacts/test-redundancy.json`. The existing upload step already uploads artifacts/. Change nothing else in the workflow; keep it valid YAML (the file must still parse with PyYAML).

Own only these three files: scripts/coverage_redundancy.py, tests/test_coverage_redundancy.py, .github/workflows/coverage-context-report.yml. Do not edit tests/shard_durations.json or any other file.

DONE WHEN `pytest tests/test_coverage_redundancy.py` passes, `ruff check` and `ruff format --check` pass on the two Python files, and the workflow parses."""
)


def check_retire() -> str:
    return f"""set -eo pipefail
[ -e .venv ] || ln -s {REPO}/.venv .venv
export PYTHONPATH=$PWD:$PWD/packages/worldkeeper/src TMPDIR=/tmp
.venv/bin/python {CHECK_SCRIPT} {RETIRE_LIST}
.venv/bin/python -m pytest --collect-only -q -p no:cacheprovider -n 0 tests scripts/ringer/stage7 2>&1 | tail -5
.venv/bin/python -m pytest -q -p no:cacheprovider -n 0 tests/test_enforce_report.py tests/test_enforce_report_scope.py tests/test_enforce_report_t9c.py tests/test_enforce_report_t9d.py tests/test_enforce_report_t9h.py tests/test_enforce_report_timing.py tests/test_enforce_drain_report.py tests/test_drain_condition_corpus.py tests/test_drain_condition_heldout.py tests/test_package_audit.py tests/test_exit_audit.py tests/test_frozen_prompts.py 2>&1 | tail -8
git add -A -- tests scripts bench docs .github pyproject.toml
git diff --cached --name-status > {WORK}/retire-names.txt
git diff --cached --binary > {WORK}/retire.patch
test -s {WORK}/retire.patch
"""


def check_coverage() -> str:
    return f"""set -eo pipefail
[ -e .venv ] || ln -s {REPO}/.venv .venv
export PYTHONPATH=$PWD:$PWD/packages/worldkeeper/src TMPDIR=/tmp
.venv/bin/python -m pytest -q -p no:cacheprovider -n 0 tests/test_coverage_redundancy.py 2>&1 | tail -8
.venv/bin/python -m ruff check scripts/coverage_redundancy.py tests/test_coverage_redundancy.py
.venv/bin/python -m ruff format --check scripts/coverage_redundancy.py tests/test_coverage_redundancy.py
.venv/bin/python -c "import yaml,sys; d=yaml.safe_load(open('.github/workflows/coverage-context-report.yml')); s=d['jobs']['coverage-context-report']['steps']; names=[x.get('name','') for x in s]; assert any('redundancy' in n.lower() for n in names), names; print('workflow ok', names)"
git add -A -- scripts tests .github
bad=$(git diff --cached --name-only | grep -v -x -e scripts/coverage_redundancy.py -e tests/test_coverage_redundancy.py -e .github/workflows/coverage-context-report.yml || true)
[ -z "$bad" ] || {{ echo "files outside ownership staged: $bad"; exit 1; }}
git diff --cached --binary > {WORK}/coverage.patch
test -s {WORK}/coverage.patch
"""


OWN_RETIRE = [
    "tests",
    "scripts/ringer",
    "bench/frozen_decode.py",
    "bench/rejudge_frozen.py",
    "docs",
    ".github",
    "pyproject.toml",
]
OWN_COVERAGE = [
    "scripts/coverage_redundancy.py",
    "tests/test_coverage_redundancy.py",
    ".github/workflows/coverage-context-report.yml",
]

manifest = {
    "run_name": "probe-retire-and-coverage-report",
    "workdir": WORK,
    "max_parallel": 2,
    "worktrees": True,
    "repo": REPO,
    "tasks": [
        {
            "key": "retire-probe-scripts",
            "task_type": "code-fix",
            "engine": "codex",
            "engine_args": ["-c", "model_reasoning_effort=medium"],
            "max_attempts": 2,
            "timeout_s": 2400,
            "check_timeout_s": 1500,
            "ownership": OWN_RETIRE,
            "spec": SPEC_RETIRE,
            "check": check_retire(),
            "expect_files": [],
            "verified": "every listed path is gone or explained in NOTES_retire.txt, the suite still collects, the surviving tests closest to the removed code pass, protected paths untouched.",
        },
        {
            "key": "nightly-coverage-redundancy-report",
            "task_type": "code-feature",
            "engine": "codex",
            "engine_args": ["-c", "model_reasoning_effort=medium"],
            "max_attempts": 2,
            "timeout_s": 2400,
            "check_timeout_s": 600,
            "ownership": OWN_COVERAGE,
            "spec": SPEC_COVERAGE,
            "check": check_coverage(),
            "expect_files": [],
            "verified": "the script reports no-unique-line and identical tests on synthetic coverage data, the nightly workflow builds and uploads the report, only the three owned files changed.",
        },
    ],
}

if __name__ == "__main__":
    Path(WORK).mkdir(parents=True, exist_ok=True)
    Path(RETIRE_LIST).write_text("\n".join(SEED) + "\n", encoding="utf-8")
    out = HERE / "manifest.json"
    out.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    print(out, len(SEED), "seed paths")
