# ruff: noqa: E501  (spec strings are prose briefs for a worker)
"""Build the Ringer manifest for validator round 3b: layer 1 shape checks (two parallel tasks)."""

from __future__ import annotations

import json
from pathlib import Path

REPO = "/home/bcorfman/dev/freytag-forge"
WORK = "/home/bcorfman/dev/ringer-work/story-data-validator"

COMMON = f"""You are a Python engineer. Your current working directory IS a git worktree of {REPO} (detached at HEAD). Edit files here directly. NEVER git commit, never touch {REPO} itself, never run `uv`, never call a billed model or the network. FIRST run: [ -e .venv ] || ln -s {REPO}/.venv .venv ; run tests as `PYTHONPATH=$PWD:$PWD/packages/worldkeeper/src TMPDIR=/tmp .venv/bin/python -m pytest -q -p no:cacheprovider -n 0 <files>` (never pass --cov); ruff as `.venv/bin/python -m ruff check <files>` and `.venv/bin/python -m ruff format <files>` (line length 120, double quotes, Python 3.12, PyYAML only, no new dependencies).

BACKGROUND. The game's story data is moving to a declarative source format that a compiler turns into the existing `StoryPackage`. The format is fixed by the contract at .plans/story-data-schema-contract.md (read it; do not edit it). The package `storygame/story_source/` already exists with: `diagnostics.py` (`Diagnostic(name, file, address, field, message)`), `reader.py` (`read_source_tree(root) -> (SourceTree, diagnostics)`; `SourceTree.files` maps relative posix path to parsed data, `SourceTree.line_of(file, path_tuple)` gives a 1-based line), and `checks.py` (a registry: decorate `fn(tree: SourceTree) -> list[Diagnostic]` with `@layer1_check`; any module in the package named `l1_*.py` is imported automatically, so you add a file and edit no shared file). `check_source_tree(root)` (in `__init__.py`) runs every registered check. Read these four files and tests/story_source/test_reader.py first. The valid base tree is tests/fixtures/story_source/mini_ok/ (fixture F01); `check_source_tree` must return [] for it, always. Fixture tests live in tests/story_source/test_f*.py; read the ones named below.

YOUR JOB: layer 1 checks (contract section 7, the L1 rows, and the per-file key tables in sections 2, 3 and 4). Layer 1 is shape only: unknown key, missing required key, wrong value type, wrong enum value, id pattern mismatch, and the other L1 names in the section 7 table that fall in your area. Each Diagnostic carries the stable name from the table, the file, a non-empty address (a section 8.1 style address such as `reveal:find_card` or a dotted path inside the file when no record id applies), the offending key as `field`, and a message naming the key and, where useful, the allowed set. Never assert exact message wording in tests. Rules for correctness: (1) read the contract tables literally; a key marked R is required, O optional, and a key absent from the table is `L1.unknown_key`; (2) check key ORDER only where the contract says order is fixed (top-level key order in section 2: report nothing for order unless the contract names a check for it; do not invent checks); (3) never crash on malformed input: a value of the wrong type yields one diagnostic and the check moves on; a file that parsed to None is skipped (the reader already reported it); (4) F01 must stay clean, so run it constantly; (5) write at least one failing-case test per check name you implement, built by copying mini_ok with `copy_fixture` and mutating with `patch_source` or by writing the file, and assert the diagnostic NAME, a non-empty `file`, `address`, `field`; each test also asserts the unmutated tree has none of your diagnostics. Put your checks in the module files you own; keep each module readable (split into helpers, no function longer than about 60 lines), and give each a docstring.

Layer 2 (cross-record references, fact ownership, claims) is NOT yours; do not implement `L2.*` names. Tell, in a short `# NOTE:` comment at the top of your test file, any point where the contract left a shape or rule ambiguous and what you assumed.
"""

TASKS = [
    {
        "key": "r3b-l1-root-and-match",
        "task_type": "code-feature",
        "owned": ["storygame/story_source/l1_root.py", "tests/story_source/test_l1_root.py"],
        "text": f"""You own ONLY: storygame/story_source/l1_root.py and tests/story_source/test_l1_root.py. Touch nothing else (another worker writes l1_scene.py in parallel). If you need a helper that also exists elsewhere, define your own private copy inside your module.

YOUR AREA: every source file EXCEPT scene files `scenes/<id>.yaml`. That is: `ownership.yaml` (section 2 top-level table), `story.yaml` (4.1), `catalog.yaml` (4.2), match files `scenes/<id>.match.yaml` (4.9), match lock files `scenes/<id>.match.lock.yaml` (section 6.3), `lexicon.yaml` (6.1). Checks to implement: `L1.unknown_key`, `L1.missing_key`, `L1.type`, `L1.enum`, `L1.id_pattern` for those files; `L1.match_scene` (a match file's `scene` differs from its file name; section 7); `L1.lexicon_off` (a `{{from:}}` value or `$` reference in a match file without `lexicon: true`; sections 4.9 and 6); `L1.plural_off` (`(s)`/`(es)` in a matcher entry without `plural_twins: true`; section 6.5); and `schema: 1` as the required first key of each file (a missing or other value is `L1.missing_key` or `L1.enum`). When `lexicon: false` (or absent) in a match file, `lexicon.yaml` must not even be parsed for checks: a malformed lexicon.yaml is ignored (fixture F17: tests/story_source/test_f17_lexicon_off_ignored.py; read it).

Read first: contract sections 2, 3, 4.1, 4.2, 4.9, 6.1 to 6.5, 7. Fixture tests that your checks must satisfy (their check_source_tree parts; skip parts that need a compiler): tests/story_source/test_f18_lexicon_ref_when_off.py, test_f22_plural_twins.py (the L1.plural_off part), test_f17_lexicon_off_ignored.py (check_source_tree part).""",
        "own_tests": "tests/story_source/test_l1_root.py tests/story_source/test_f18_lexicon_ref_when_off.py",
    },
    {
        "key": "r3b-l1-scene",
        "task_type": "code-feature",
        "owned": ["storygame/story_source/l1_scene.py", "tests/story_source/test_l1_scene.py"],
        "text": f"""You own ONLY: storygame/story_source/l1_scene.py and tests/story_source/test_l1_scene.py. Touch nothing else (another worker writes l1_root.py in parallel). If you need a helper that also exists elsewhere, define your own private copy inside your module.

YOUR AREA: scene files `scenes/<id>.yaml` only. Read contract sections 3, 4.3 to 4.8 and 4.10 to 4.14 (scene header, brief and outline, facts, placements, beats, reveals with variants and claims, bridge, incidents, entry_claims, exit, ending) and the L1 rows of section 7. Checks to implement: `L1.unknown_key`, `L1.missing_key`, `L1.type`, `L1.enum`, `L1.id_pattern` (id, scene id, storylet id, realization id, outline beat id and anchor patterns from section 3), `L1.condition_value` (`false` in an all-true field such as entry additions, `text_when`, ending additions, exit `when_all`; `retract` in pacing `sets`; section 3), `L1.passage_list` (a `say` list whose last entry has a `when`, or a guarded entry after an unguarded one; section 3 and 4.7), and `L1.claim_keys_without_claim` (claim keys on a variant that has no `claim_id`; section 4.8). Variants, claims, beats, incidents and the exit nest several levels, so write a small table-driven checker (key name to required/optional and a type or enum or nested table) instead of hand-written code per key.

Fixture tests that your checks must satisfy (their check_source_tree parts; skip parts that need a compiler): tests/story_source/test_f03_unknown_key.py (a `done_when` key on a reveal gives `L1.unknown_key`), and read test_f06, test_f07 and test_f12 to see which mutations are layer 2 and must NOT be flagged by you.""",
        "own_tests": "tests/story_source/test_l1_scene.py tests/story_source/test_f03_unknown_key.py",
    },
]


def check(owned: list[str], own_tests: str, key: str) -> str:
    keep = " ".join(f"-e '^{p}$'" for p in owned)
    return f"""set -eo pipefail
[ -e .venv ] || ln -s {REPO}/.venv .venv
export PYTHONPATH=$PWD:$PWD/packages/worldkeeper/src TMPDIR=/tmp
out=$(mktemp)
rc=0
.venv/bin/python -m pytest -q -p no:cacheprovider -n 0 {own_tests} tests/story_source/test_f01_mini_ok.py tests/story_source/test_f02_dup_key.py tests/story_source/test_reader.py tests/story_source/test_layer_registry.py > "$out" 2>&1 || rc=$?
tail -40 "$out"
[ "$rc" -eq 0 ] || exit "$rc"
.venv/bin/python -m ruff check storygame/story_source tests/story_source
.venv/bin/python -m ruff format --check storygame/story_source tests/story_source
git add -A -- storygame/story_source tests/story_source
bad=$(git diff --cached --name-only | grep -v {keep} || true)
[ -z "$bad" ] || {{ echo "files outside ownership staged: $bad"; exit 1; }}
git diff --cached > {WORK}/{key}.patch
test -s {WORK}/{key}.patch
"""


manifest = {
    "run_name": "story-data-validator",
    "workdir": WORK,
    "max_parallel": 2,
    "worktrees": True,
    "repo": REPO,
    "tasks": [
        {
            "key": t["key"],
            "task_type": "code-feature",
            "engine": "codex",
            "engine_args": ["-c", "model_reasoning_effort=high"],
            "max_attempts": 2,
            "timeout_s": 2700,
            "check_timeout_s": 900,
            "ownership": t["owned"],
            "spec": COMMON + "\n" + t["text"],
            "check": check(t["owned"], t["own_tests"], t["key"]),
            "expect_files": [],
            "verified": "Layer 1 checks for the owned file kinds exist, each has a failing-case test, F01 stays clean, ruff clean, only owned files changed.",
        }
        for t in TASKS
    ],
}

if __name__ == "__main__":
    out = Path(__file__).with_name("validator-round3b-manifest.json")
    out.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    print(out)
