# ruff: noqa: E501
"""Round 25a: qualification Step 1 tasks 1.1 (full-quote citation validator) and 1.3 (isolation check). Free, no model.

The code lives in the qualification workspace tools repo (a local git repo at qual-20261122/tools), not in freytag-forge.
"""

import json
from pathlib import Path

WORK = "/home/bcorfman/dev/ringer-work/factory-25"
REPO = "/home/bcorfman/dev/ringer-work/qual-20261122/tools"
PY = "/home/bcorfman/dev/freytag-forge/.venv/bin/python"

COMMON = (
    "You are a tooling engineer. Your current working directory IS a git worktree of "
    f"{REPO} (detached at HEAD), a small repo of Python scripts used to qualify a story-repair factory. Edit files "
    "here directly. NEVER git commit, never touch the original repo, NEVER call a model (not `claude`, not `codex`), "
    "NEVER use the network, never run `uv`, never read or write anything outside this worktree except the Python "
    f"interpreter {PY}. Run tests as `PYTHONPATH=$PWD {PY} -m pytest -q -p no:cacheprovider tests/<file>`; do not pass "
    f"--cov. Ruff on python files only: `{PY} -m ruff check <files>` and `{PY} -m ruff format <files>` (line length 120, "
    "Python 3.12). Tests must be hermetic: build every fixture in tmp_path inside the test, no network, no model, "
    "total under 10 seconds. Write NOTES.txt (worktree root, never committed) listing every ambiguity and your choice. "
    "Existing code to read first: tools/run_evaluator.py (the `validate` function is what you are strengthening) and "
    "tools/make_case.py (how a case folder is laid out)."
)

CASE_LAYOUT = (
    'CASE LAYOUT (what a case folder looks like): `<case>/solver/records.json` = {"runs": [{"replicate": int, '
    '"scene": str, "turns": [{"turn": int, "input": str, "raw_input": str, "text": str, ...}], '
    '"stuck_turns": [int], "exit_cause": str}]}; `<case>/solver/repo/...` = a snapshot of the source tree; '
    '`<case>/private/answer.json` = the evaluator\'s record, whose `evidence` list holds {"kind": "turn"|"source", '
    '"locator": str, "quote": str} items. Turn locators look like "replicate 2 turn 5"; source locators look like '
    '"data/stories/x/source/scenes/3B.yaml:332" or "relative/path:record_id" (a `solver/` prefix is allowed and '
    "stripped)."
)

SPEC_11 = COMMON + (
    "\n\nYou may edit ONLY: citation_check.py (new), tests/test_citation_check.py (new), run_evaluator.py (only so that "
    "`validate(case_dir, ans)` delegates to citation_check and keeps its exact signature and its list-of-problem-strings "
    "return value; change nothing else in it).\n\n"
    "TASK 1.1: write `citation_check.py` with `check_citations(case_dir: Path, ans: dict) -> dict` returning "
    '{"problems": [str], "quotes_checked": int, "quotes_exact": int, "paraphrases": int, "line_offsets": [{"locator": str, "offset": int}]}. '
    "Rules (the old validator only checked that the first 40 characters of a quote, cut at the first `...`, appear anywhere in the file; "
    "it checked that a turn exists but never what it says; it ignored line numbers):\n"
    "1. Normalise whitespace (collapse runs of whitespace to one space, strip) on both quote and target; matching is case-sensitive.\n"
    "2. A `turn` item resolves only when (replicate, turn) exists in records.json AND the WHOLE quote is a substring of that "
    "turn's `input`, `raw_input` or `text` (any of the three). An item with an empty quote and kind `turn` is a problem unless it is marked paraphrase.\n"
    "3. A `source` item resolves only when the file exists under solver/ (try the locator with and without a leading `solver/`). When the "
    "locator has `:LINE` with an integer, the WHOLE quote must occur in the lines from LINE-2 to LINE+2 inclusive (join those lines before "
    "matching so a quote that spans lines still works); record the smallest offset (0, 1 or 2) in `line_offsets`. When the locator has `:record_id` "
    "(non-integer), the whole quote must occur anywhere in the file AND the id string must occur in the file. A bare path with no suffix needs the whole quote somewhere in the file.\n"
    "4. A quote containing `...` (or the single character ellipsis) is split on it into fragments; every non-empty fragment must be found, in order, "
    "within the same region as above (the whole file for a bare path or record id, the +-2 line window for a line locator).\n"
    '5. An item with `"kind"` equal to `paraphrase` is not a quote: its locator must still resolve (turn exists, file exists) but no quote match is needed; count it in `paraphrases`. '
    'Note the existing evidence items use `kind` for turn versus source, so a paraphrase is marked by an extra key `"paraphrase": true`; accept both that key and `kind: "paraphrase"` with a `locator_kind` key, and document the choice in NOTES.txt.\n'
    "6. Problems are human-readable strings that say which item failed and why, e.g. `quote not found at data/x.yaml:332 (+-2 lines): 'first 60 chars...'`, "
    "so a person can fix the record. A `defect` verdict with no evidence is a problem (keep that old rule).\n"
    "7. Never raise on malformed items (missing keys, wrong types, unreadable file): report a problem string instead.\n\n"
    + CASE_LAYOUT
    + "\n\n"
    "TESTS (tests/test_citation_check.py, build the case folder in tmp_path; each must FAIL against the old validator behaviour and pass with yours): "
    "(a) a quote whose first 40 characters match the file but whose tail does not -> problem; (b) a turn quote that appears in no turn of that replicate "
    "(but does appear in another turn) -> problem; (c) a turn quote present in `input` only -> ok; (d) a source quote on a wrong line far from LINE (more than 2 away) -> problem; "
    "(e) the same quote 2 lines away -> ok with offset 2 recorded; (f) a quote that exists in another file but not the cited one -> problem; (g) an ellipsis quote with both fragments "
    "in order -> ok, and with the fragments in reverse order -> problem; (h) a record-id locator whose id is absent -> problem; (i) a paraphrase item with a resolving locator -> ok and counted, with a missing file -> problem; "
    "(j) malformed items (no locator, locator not a string, quote not a string) -> problems, no exception; (k) `defect` with no evidence -> problem; (l) `run_evaluator.validate` still returns the same list of strings as `check_citations(...)['problems']`."
)

SPEC_13 = COMMON + (
    "\n\nYou may edit ONLY: isolation_check.py (new) and tests/test_isolation_check.py (new).\n\n"
    'TASK 1.3: write `isolation_check.py` with `check_isolation(case_dir: Path) -> dict` returning {"problems": [str], "checked": {...counts...}, "limits": [str]} '
    "and a `main(argv)` CLI (`python isolation_check.py CASE_DIR`, prints the dict as JSON, exit 0 only when problems is empty). "
    "A case folder is untrusted-by-construction: the evaluator or solver model that reads it must not be able to reach the private answer, sibling cases or history. "
    "The check walks the REAL tree (no model) and reports a problem for each of:\n"
    "1. any symlink (file or directory) anywhere under `solver/` whose resolved target is outside `solver/` (or is broken);\n"
    "2. any entry named `.git`, `.plans`, `ringer`, `artifacts` or `tests` anywhere under `solver/repo` (those are the directories the case builder excludes), and any file whose name ends in `.patch`, `.orig` or `.rej`;\n"
    "3. any path under `solver/` that resolves into `private/` or into a sibling of the case folder (use os.path.realpath on every entry);\n"
    "4. a `manifest.json` next to `solver/` whose `forbidden_tokens_checked` is missing or an empty list (an empty list makes the contamination scan meaningless);\n"
    "5. any file under `solver/` that contains any token from `forbidden_tokens_checked` (read as bytes, decode with errors ignored, case-sensitive substring), reporting file and token but never printing more than 80 characters of context;\n"
    "6. a `solver/` directory that is missing, or a `private/` directory that is not a sibling of it.\n"
    "ALSO provide `derive_forbidden_tokens(answer: dict, extra_labels: list[str]) -> list[str]`, which builds the per-case token list from a private answer record: "
    "(a) identifiers that look like fix identifiers: strings matching `k_sl_[a-z0-9_]+`, `SL-[0-9A-Z]+-[A-Z](-R[0-9]+)?` or `[a-z_]+\\.yaml:[0-9]+` found in `acceptable_repairs`, `forbidden_shortcuts` and `acceptance_check`, "
    "(b) each whole string in `acceptable_repairs` and `forbidden_shortcuts` that is at least 25 characters long, "
    "(c) every string in `extra_labels` (for example `15d`, `18c`, `heldout-cand-1B`). Deduplicate, drop tokens shorter than 3 characters, sort. "
    "IMPORTANT honesty limit: put in the returned `limits` list, verbatim, the sentence: `Proves tree contents and symlink structure only; it does not prove that the evaluator's tool sandbox denies absolute-path reads (that needs a model-based canary).`\n\n"
    + CASE_LAYOUT
    + ' A `manifest.json` at the case root has {"case": str, "forbidden_tokens_checked": [str], ...}.\n\n'
    "TESTS (tests/test_isolation_check.py; build each case in tmp_path, with canaries): a clean case passes; each of rules 1 to 6 has a failing case that reports the right problem "
    "(symlink out of solver; symlink to private; a `.git` directory with a file; a `tests` directory; a `.patch` file; empty and missing `forbidden_tokens_checked`; a token present in a solver file; solver missing); "
    "a symlink that stays inside `solver/` is fine; `derive_forbidden_tokens` returns the expected fix identifiers, long strings and labels, is sorted, deduplicated and drops short tokens; "
    "`main` returns non-zero for a bad case and prints JSON containing the `limits` sentence."
)


def check(files_re: str, test_file: str, extra: str = "") -> str:
    return f"""set -eo pipefail
WORK={WORK}
mkdir -p "$WORK/out"
git reset -q
git add -A -- . ':(exclude)NOTES.txt' ':(exclude).serena'
bad=$(git diff --cached --name-only --diff-filter=d | grep -vE '^({files_re})$' || true)
[ -z "$bad" ] || {{ echo "files outside ownership staged: $bad"; exit 1; }}
start=$(date +%s)
PYTHONPATH=$PWD {PY} -m pytest -q -p no:cacheprovider {test_file}
took=$(( $(date +%s) - start ))
echo "tests took $took s (budget 60 s)"
[ "$took" -le 60 ] || {{ echo "over the 60 s budget"; exit 1; }}
PYFILES=$(git diff --cached --name-only --diff-filter=d | grep '\\.py$' | grep -v '^run_evaluator\\.py$' || true)
echo "ruff files: $PYFILES"
[ -z "$PYFILES" ] || {PY} -m ruff check $PYFILES
[ -z "$PYFILES" ] || {PY} -m ruff format --check $PYFILES
n=$(grep -c '^def test_' {test_file})
echo "$n tests"
{extra}
"""


CHECK_11 = check(
    r"citation_check\.py|tests/test_citation_check\.py|run_evaluator\.py",
    "tests/test_citation_check.py",
    """[ "$n" -ge 10 ] || { echo "expected at least 10 tests"; exit 1; }
grep -q 'citation_check' run_evaluator.py || { echo "run_evaluator.validate does not delegate to citation_check"; exit 1; }
PYTHONPATH=$PWD """
    + PY
    + """ -c "import inspect, run_evaluator as r; assert list(inspect.signature(r.validate).parameters)==['case_dir','ans'], 'validate signature changed'"
git diff --cached > "$WORK/out/step1-1-citation.patch"
test -s "$WORK/out/step1-1-citation.patch"
""",
)
CHECK_13 = check(
    r"isolation_check\.py|tests/test_isolation_check\.py",
    "tests/test_isolation_check.py",
    """[ "$n" -ge 12 ] || { echo "expected at least 12 tests"; exit 1; }
grep -q 'Proves tree contents and symlink structure only' isolation_check.py || { echo "limits sentence missing"; exit 1; }
git diff --cached > "$WORK/out/step1-3-isolation.patch"
test -s "$WORK/out/step1-3-isolation.patch"
""",
)

manifest = {
    "run_name": "qual-step1-tools",
    "workdir": WORK,
    "max_parallel": 2,
    "worktrees": True,
    "repo": REPO,
    "tasks": [
        {
            "key": "citation-check",
            "task_type": "code-feature",
            "engine": "codex",
            "engine_args": ["-c", "model_reasoning_effort=medium"],
            "max_attempts": 2,
            "timeout_s": 1800,
            "check_timeout_s": 300,
            "ownership": ["citation_check.py", "tests/test_citation_check.py", "run_evaluator.py"],
            "spec": SPEC_11,
            "check": CHECK_11,
            "expect_files": [],
            "verified": "Citations are validated by whole-quote match at the exact turn or line window; the old weaknesses fail first.",
        },
        {
            "key": "isolation-check",
            "task_type": "code-feature",
            "engine": "codex",
            "engine_args": ["-c", "model_reasoning_effort=medium"],
            "max_attempts": 2,
            "timeout_s": 1800,
            "check_timeout_s": 300,
            "ownership": ["isolation_check.py", "tests/test_isolation_check.py"],
            "spec": SPEC_13,
            "check": CHECK_13,
            "expect_files": [],
            "verified": "A case folder is checked for symlink escape, excluded directories, private reachability and an empty token list.",
        },
    ],
}
Path(__file__).with_name("round25a-step1-tools-manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")
