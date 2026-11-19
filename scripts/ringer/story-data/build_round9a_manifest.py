# ruff: noqa: E501  (spec strings are prose briefs for a worker)
"""Round 9a: build the committed copied-prose audit that reads the compiled package (one task).

Usage: build_round9a_manifest.py
"""

from __future__ import annotations

import json
from pathlib import Path

REPO = "/home/bcorfman/dev/freytag-forge"
WORK = "/home/bcorfman/dev/ringer-work/story-data-round9a"
EXPECTED = (
    "/tmp/claude-1000/-home-bcorfman-dev-freytag-forge/76315427-6d7d-478b-bfa4-c28ca4a170a6/scratchpad/copied.json"
)

SPEC = f"""You are a Python engineer. Your current working directory IS a git worktree of {REPO} (detached at HEAD). Edit files here directly. NEVER git commit, never touch {REPO} itself, never run `uv`, never call a billed model or the network. FIRST run: [ -e .venv ] || ln -s {REPO}/.venv .venv ; run tests as `PYTHONPATH=$PWD:$PWD/packages/worldkeeper/src TMPDIR=/tmp .venv/bin/python -m pytest -q -p no:cacheprovider -n 0 tests/test_audit_copied_prose.py` (never pass --cov); ruff as `.venv/bin/python -m ruff check <files>` and `.venv/bin/python -m ruff format <files>` (line length 120, double quotes, Python 3.12, no new dependencies).

BACKGROUND. Tests must not copy authored story sentences; they should look the text up by record address (`storygame.story_source.lookup.story_text("claim:k_sl_1a_b_r1.text")`). An old audit, .plans/story-data-phase0/copied_prose.py, counted copies but reads the nine legacy story files, which are gone. You build its replacement, reading the compiled package.

YOUR JOB: create scripts/audit_copied_prose.py and tests/test_audit_copied_prose.py. Nothing else.

scripts/audit_copied_prose.py must expose `find_copied_sentences(package, tests_dir) -> dict[str, list[tuple[str, str]]]` and a CLI `main(argv)`. Algorithm (copy it exactly, it has been run and gives 36 files and 82 pairs on the current repo):
1. `norm(s) = re.sub(r"\\s+", " ", s.replace("\\u2019", "'").replace("\\u201c", '"').replace("\\u201d", '"')).strip()`.
2. Build `passages: dict[str, str]` keyed by address. For every claim `c` in `package.knowledge.knowledge`: if `c.delivery_text` is non-empty add `f"claim:{{c.id}}.text"`; if `c.statement` is non-empty add `f"claim:{{c.id}}.says"`. For every pacing event `e` in `package.pacing.events` and index `i, r` in `enumerate(e.realizations)`: add `f"beat:{{e.id}}.say[{{i}}]"` -> `r.text`.
3. Split each normalised passage with `re.split(r"(?<=[.!?])\\s+", norm(text))`; keep sentences of length >= 45; keep the FIRST address that produced each distinct sentence (`dict.setdefault`).
4. For each `tests_dir.glob("test_*.py")` (top level only, no recursion), read the file, normalise it with `norm`, and record `(address, sentence)` for every sentence that is a substring of it. The result maps the test file NAME (for example "test_richer_1c.py") to its list of (address, sentence) pairs, only for files with at least one hit.
5. Load the package with `storygame.story_package.loader.load_story_package(Path(repo) / "data/stories/continuity-initiative")`.

CLI: `python scripts/audit_copied_prose.py [--repo DIR] [--test tests/test_x.py ...] [--json]`. `--repo` defaults to the current directory. `--test` (repeatable) restricts the report to those test files (match by file name). Default output is one line per pair, `tests/<name>: <address> :: <sentence>`, then a final summary line `<N> test files copy <M> authored sentences`. With `--json` print one JSON object mapping file name to a list of [address, sentence] pairs and nothing else. Exit 1 when any pair is reported, 0 when none. The script must run from any current directory (put the repo root on sys.path from `--repo` only if `storygame` is not already importable; do not edit sys.path otherwise).

tests/test_audit_copied_prose.py: exactly two tests, no more. (1) Build a tmp tests directory containing one file that embeds `story_text("claim:k_sl_1a_b_r1.text")` split to its first sentence of length >= 45 characters, and one file with no story text; assert `find_copied_sentences` reports only the first file and names the address `claim:k_sl_1a_b_r1.text`. Obtain the sentence through the lookup API, never by typing story prose into the test. (2) Run `main(["--json", "--repo", <repo root>, "--test", "tests/test_audit_copied_prose.py"])` through capsys and assert exit code 0 and `{{}}` output, proving this test file itself copies no authored prose.

HARD LIMITS. Create only those two files. Never edit any other file, including tests/shard_durations.json (the orchestrator owns it).
"""

CHECK = f"""set -eo pipefail
[ -e .venv ] || ln -s {REPO}/.venv .venv
export PYTHONPATH=$PWD:$PWD/packages/worldkeeper/src TMPDIR=/tmp
out=$(mktemp)
rc=0
.venv/bin/python -m pytest -q -p no:cacheprovider -n 0 -rs tests/test_audit_copied_prose.py > "$out" 2>&1 || rc=$?
tail -15 "$out"
[ "$rc" -eq 0 ] || exit "$rc"
if grep -E "SKIPPED|XFAIL|xfailed" "$out"; then echo "a test skips or xfails"; exit 1; fi
n=$(grep -cE "^\\s*def test_" tests/test_audit_copied_prose.py || true)
[ "$n" -eq 2 ] || {{ echo "expected exactly 2 tests, found $n"; exit 1; }}
# the audit reproduces the measurement the orchestrator took independently
.venv/bin/python scripts/audit_copied_prose.py --json > "$out.json" || true
.venv/bin/python - "$out.json" {EXPECTED} <<'PY'
import json, sys
got = json.load(open(sys.argv[1]))
want = json.load(open(sys.argv[2]))
norm = lambda d: {{k: sorted(map(tuple, v)) for k, v in d.items()}}
if norm(got) != norm(want):
    print("audit output differs from the independent measurement")
    print("only in got:", sorted(set(got) - set(want)))
    print("only in want:", sorted(set(want) - set(got)))
    for k in sorted(set(got) & set(want)):
        if norm(got)[k] != norm(want)[k]:
            print("differs:", k)
    sys.exit(1)
print("audit matches:", len(got), "files")
PY
set +e
.venv/bin/python scripts/audit_copied_prose.py > /dev/null
[ "$?" -eq 1 ] || {{ echo "the audit must exit 1 while copies exist"; exit 1; }}
set -e
.venv/bin/python -m ruff check scripts/audit_copied_prose.py tests/test_audit_copied_prose.py
.venv/bin/python -m ruff format --check scripts/audit_copied_prose.py tests/test_audit_copied_prose.py
git add -A -- scripts tests storygame data
bad=$(git diff --cached --name-only | grep -v -x -e 'scripts/audit_copied_prose.py' -e 'tests/test_audit_copied_prose.py' || true)
[ -z "$bad" ] || {{ echo "files outside ownership staged: $bad"; exit 1; }}
git diff --cached > {WORK}/m-audit.patch
test -s {WORK}/m-audit.patch
"""

manifest = {
    "run_name": "story-data-decouple-tests",
    "workdir": WORK,
    "max_parallel": 1,
    "worktrees": True,
    "repo": REPO,
    "tasks": [
        {
            "key": "m-audit",
            "task_type": "code-feature",
            "engine": "codex",
            "engine_args": ["-c", "model_reasoning_effort=medium"],
            "max_attempts": 2,
            "timeout_s": 1800,
            "check_timeout_s": 300,
            "ownership": ["scripts/audit_copied_prose.py", "tests/test_audit_copied_prose.py"],
            "spec": SPEC,
            "check": CHECK,
            "expect_files": [],
            "verified": "The audit script reads the compiled package, reproduces the independent 36-file measurement exactly, exits 1 while copies exist; its two tests pass; only two files created.",
        }
    ],
}

if __name__ == "__main__":
    out = Path(__file__).with_name("round9a-manifest.json")
    out.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    print(out)
