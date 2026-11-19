# ruff: noqa: E501  (spec strings are prose briefs for a worker)
"""Round 9a2: make the copied-prose audit see sentences split across wrapped or joined string literals (one task).

Usage: build_round9a_manifest.py
"""

from __future__ import annotations

import json
from pathlib import Path

REPO = "/home/bcorfman/dev/freytag-forge"
WORK = "/home/bcorfman/dev/ringer-work/story-data-round9a2"
EXPECTED = (
    "/tmp/claude-1000/-home-bcorfman-dev-freytag-forge/76315427-6d7d-478b-bfa4-c28ca4a170a6/scratchpad/copied2.json"
)

SPEC = f"""You are a Python engineer. Your current working directory IS a git worktree of {REPO} (detached at HEAD). Edit files here directly. NEVER git commit, never touch {REPO} itself, never run `uv`, never call a billed model or the network. FIRST run: [ -e .venv ] || ln -s {REPO}/.venv .venv ; cp {REPO}/scripts/audit_copied_prose.py scripts/audit_copied_prose.py ; cp {REPO}/tests/test_audit_copied_prose.py tests/test_audit_copied_prose.py (the two files exist uncommitted in the main checkout and are your starting point); run tests as `PYTHONPATH=$PWD:$PWD/packages/worldkeeper/src TMPDIR=/tmp .venv/bin/python -m pytest -q -p no:cacheprovider -n 0 tests/test_audit_copied_prose.py` (never pass --cov); ruff as `.venv/bin/python -m ruff check <files>` and `.venv/bin/python -m ruff format <files>` (line length 120, double quotes, Python 3.12, no new dependencies).

BACKGROUND. scripts/audit_copied_prose.py (with tests/test_audit_copied_prose.py) reports test files that copy authored story sentences. It misses a copy when the test source wraps the sentence over several adjacent string literals ("first half " "second half"), splits it into a tuple joined with " ".join(...), or otherwise breaks it across string constants. Workers fixing copies have escaped the audit by exactly that. You close the hole.

YOUR JOB: edit only scripts/audit_copied_prose.py and tests/test_audit_copied_prose.py. In `find_copied_sentences`, a sentence now counts as copied when EITHER of these is true (the first is today's rule, keep it):
1. The normalised sentence is a substring of the normalised test source (unchanged).
2. It matches the test's string constants joined. Parse the test file with `ast`; if it has a SyntaxError use an empty blob. Collect every `ast.Constant` whose value is a `str` from `ast.walk(tree)` (this includes the literal pieces of f-strings; order of `ast.walk` does not matter for this rule only if you do what follows) in source order (sort by `(node.lineno, node.col_offset)`), join them with a single space, and turn the result into `blob = " " + " ".join(words(joined)) + " "`, where `words(s)` is `re.sub(r"[^a-z0-9' ]+", " ", norm(s).lower()).split()` and `norm` is the existing normaliser. The sentence matches when `" " + " ".join(words(sentence)) + " "` is a substring of `blob`.
Everything else is unchanged (sentences of length >= 45 characters from claim delivery text, statements and pacing realizations, first address per sentence, same CLI, same JSON shape, one entry per (address, sentence) per file). Extend the second test in tests/test_audit_copied_prose.py with nothing; add a THIRD test that writes a tmp test file with a sentence taken through `story_text` (first sentence of length >= 45 of "claim:k_sl_1a_b_r1.text") split in the middle across two adjacent string literals, and another sentence of the same kind joined with `" ".join((part_one, part_two))` written as literals, and asserts both are reported. Build those files with code that splits the looked-up sentence at its middle space, so no story prose is typed into the test file; write the generated file text with repr() of the halves. For the adjacent-literal case, Python merges neighbouring literals with no separator, so, as wrapped code does, put the space at the END of the first half (`repr(first_one + " ")` then `repr(first_two)`, separated in the file text by a newline and indent inside parentheses or by one space). Pick the two sentences from the audit's own sentence list for that claim (the sentences the audit itself would produce: normalised, split on `(?<=[.!?])\\s+`, length >= 45), by calling the audit module's own helper if you factor one out, so the test cannot disagree with the audit about what a sentence is.

HARD LIMITS. Edit only those two files. Never edit any other file, including tests/shard_durations.json.
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
[ "$n" -eq 3 ] || {{ echo "expected exactly 3 tests, found $n"; exit 1; }}
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
git diff --cached > {WORK}/m-audit2.patch
test -s {WORK}/m-audit2.patch
"""

manifest = {
    "run_name": "story-data-decouple-tests",
    "workdir": WORK,
    "max_parallel": 1,
    "worktrees": True,
    "repo": REPO,
    "tasks": [
        {
            "key": "m-audit2",
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
            "verified": "The audit script reads the compiled package, reproduces the independent 40-file measurement (wrapped literals included) exactly, exits 1 while copies exist; its three tests pass; only those two files edited.",
        }
    ],
}

if __name__ == "__main__":
    out = Path(__file__).with_name("round9a2-manifest.json")
    out.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    print(out)
