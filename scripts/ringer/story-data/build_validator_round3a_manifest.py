# ruff: noqa: E501  (spec strings are prose briefs for a worker)
"""Build the Ringer manifest for validator round 3a: package skeleton, strict reader, test-helper proxy."""

from __future__ import annotations

import json
from pathlib import Path

REPO = "/home/bcorfman/dev/freytag-forge"
WORK = "/home/bcorfman/dev/ringer-work/story-data-validator"

SPEC = f"""You are a Python engineer. Your current working directory IS a git worktree of {REPO} (detached at HEAD). Edit files here directly. NEVER git commit, never touch {REPO} itself, never run `uv`, never call a billed model or the network. You own ONLY: everything under storygame/story_source/ (new), tests/story_source/helpers.py, tests/story_source/test_*.py (existing files, for one mechanical edit described below), and new test files tests/story_source/test_reader.py and tests/story_source/test_layer_registry.py. Touch nothing else: not the contract, not tests/fixtures/, not data/, not the other storygame packages. FIRST run: [ -e .venv ] || ln -s {REPO}/.venv .venv ; run tests as `PYTHONPATH=$PWD:$PWD/packages/worldkeeper/src TMPDIR=/tmp .venv/bin/python -m pytest -q -p no:cacheprovider -n 0 <files>` (never pass --cov); ruff as `.venv/bin/python -m ruff check <files>` and `.venv/bin/python -m ruff format <files>` (line length 120, double quotes, Python 3.12, PyYAML only, no new dependencies).

BACKGROUND. The game's story data is being migrated to a declarative source format (YAML scene files plus a match file per scene) that a compiler turns into the existing `StoryPackage`. The format is fixed by the contract at .plans/story-data-schema-contract.md. Read sections 2, 3, 7 and 10.1 fully (file layout, value shapes, the check table, the settled API names). Fixtures and tests for the validator already exist under tests/story_source/ and tests/fixtures/story_source/ (F01 `mini_ok` is the valid base tree; read tests/story_source/test_f01_mini_ok.py, test_f02_dup_key.py and helpers.py first). The validator and compiler package `storygame.story_source` does not exist yet. This task builds ONLY its skeleton, so later workers can add the layer 1 and layer 2 checks in separate files without editing the same file.

BUILD 1: package storygame/story_source/.
(a) `diagnostics.py`: frozen dataclass `Diagnostic(name: str, file: str, address: str, field: str, message: str)` (file is the path relative to the source root, posix style; address is a section 8.1 style address string or a stable path such as `reveal:find_card`; field is the field key) and `class SourceError(Exception)` holding `diagnostics: list[Diagnostic]` with a readable `str()` that lists one line per diagnostic.
(b) `reader.py`: a strict YAML reader. A `yaml.SafeLoader` subclass that REJECTS a repeated key in any mapping of any file but, instead of raising, records it so the reader can emit one `L1.duplicate_key` Diagnostic per repeat (name `L1.duplicate_key`, the file, an address that identifies the enclosing record, the repeated key as `field`, a message naming the key and both line numbers). The first occurrence is kept so later checks still see a tree. It also records, for every mapping key and list item, its 1-based line number so diagnostics can cite lines. API: `SourceTree` dataclass with `root: Path`, `files: dict[str, object]` (relative posix path to parsed plain Python data, in sorted path order), and `line_of(file: str, path: tuple) -> int | None`; and `read_source_tree(root: Path) -> tuple[SourceTree, list[Diagnostic]]`. It reads every `*.yaml` file under root (story.yaml, catalog.yaml, lexicon.yaml, ownership.yaml if present in root, scenes/*.yaml including *.match.yaml and *.match.lock.yaml). A YAML syntax error becomes one `L1.syntax` Diagnostic and that file parses as None; never let an exception escape.
(c) `checks.py`: a tiny registry. Decorators `layer1_check` and `layer2_check` register a function `fn(tree: SourceTree) -> list[Diagnostic]` under its module-qualified name. `run_layer1(tree)` and `run_layer2(tree)` call every registered check. `discover()` imports every module in the package whose name starts with `l1_` or `l2_` (use pkgutil.iter_modules over the package path), so a later worker adds a check by dropping in a new file `l1_<topic>.py` or `l2_<topic>.py`, with no edit to any shared file. Registration order is sorted by module name then definition order, so output is deterministic. Layer 2 checks run only when the tree read without syntax or duplicate-key problems in the files they read; keep it simple: if `read_source_tree` returned any `L1.syntax` diagnostic, skip layer 2 entirely.
(d) `__init__.py`: export `Diagnostic`, `SourceError`, `SourceTree`, `read_source_tree`, and `check_source_tree(root: Path) -> list[Diagnostic]`, which reads the tree, runs discover(), layer 1 then layer 2, and returns the diagnostics sorted by (file, address, name) for stability. Do NOT define `compile_source_tree`, `check_parity` or any other name the contract lists; later rounds add them, and tests skip while a name is missing.
Add one check file now as the registry's first user and test double: `l1_duplicate_keys_note.py` is NOT needed (duplicate keys come from the reader); instead leave the registry empty of checks. test_layer_registry.py proves discovery with a temporary package dropped on sys.path (or monkeypatching the package path) that a new `l1_*` and `l2_*` module is found and run, that ordering is deterministic, and that layer 2 is skipped after an `L1.syntax` diagnostic.

BUILD 2: tests/story_source/test_reader.py. Tests (all must pass): mini_ok reads with no diagnostics and `files` holds exactly the six files of the fixture; the F02 mutation (see test_f02_dup_key.py for the exact edit) gives exactly one `L1.duplicate_key` with non-empty file, address and field and the line number in the message; a YAML syntax error gives `L1.syntax` and does not raise; `line_of` returns the right line for a known key of mini_ok/scenes/1A.yaml; reading is deterministic (twice, same result).

BUILD 3: a test-helper proxy and one mechanical edit. In tests/story_source/helpers.py add `require_story_source()`. It calls `pytest.importorskip("storygame.story_source")` and returns a thin wrapper object whose `__getattr__(name)` returns the real module attribute if it exists, and otherwise calls `pytest.skip(f"storygame.story_source.{{name}} is not built yet")`. Then replace, in every tests/story_source/test_f*.py file, each statement of the form `story_source = pytest.importorskip("storygame.story_source")` with `story_source = require_story_source()` and fix the imports (remove `pytest` import only if it becomes unused; add `require_story_source` to the helpers import). Leave `pytest.importorskip("storygame.story_cli")` and any other importorskip untouched. Reason: once the package exists, tests that need a name that is not built yet must skip instead of erroring. Do not change any assertion.

HARD RULES. Use only the standard library and PyYAML. No global state beyond the registry. Type-annotate public functions. Keep every module small and readable, with a one-paragraph module docstring. Run the check yourself repeatedly: `bash check.sh`-style, that is the commands in the verification below.
"""

CHECK = f"""set -eo pipefail
[ -e .venv ] || ln -s {REPO}/.venv .venv
export PYTHONPATH=$PWD:$PWD/packages/worldkeeper/src TMPDIR=/tmp
test -f storygame/story_source/__init__.py
! grep -rn 'pytest.importorskip("storygame.story_source")' tests/story_source/test_f*.py || {{ echo "bare importorskip still present"; exit 1; }}
out=$(mktemp)
rc=0
.venv/bin/python -m pytest -q -p no:cacheprovider -n 0 tests/story_source/test_reader.py tests/story_source/test_layer_registry.py tests/story_source/test_f01_mini_ok.py tests/story_source/test_f02_dup_key.py > "$out" 2>&1 || rc=$?
tail -40 "$out"
[ "$rc" -eq 0 ] || exit "$rc"
# every other fixture file must still collect, and compiler-needing tests must skip rather than fail
rc=0
.venv/bin/python -m pytest -q -p no:cacheprovider -n 0 tests/story_source -k "not (test_f03 or test_f04 or test_f05 or test_f06 or test_f07 or test_f08 or test_f11 or test_f14 or test_f18 or test_f20 or test_f22 or test_f23 or test_f24 or test_f25 or test_f27 or test_f28)" > "$out" 2>&1 || rc=$?
tail -40 "$out"
[ "$rc" -eq 0 ] || exit "$rc"
.venv/bin/python -m ruff check storygame/story_source tests/story_source
.venv/bin/python -m ruff format --check storygame/story_source tests/story_source
git add -A -- storygame/story_source tests/story_source
bad=$(git diff --cached --name-only | grep -v -e '^storygame/story_source/' -e '^tests/story_source/' || true)
[ -z "$bad" ] || {{ echo "files outside ownership staged: $bad"; exit 1; }}
git diff --cached > {WORK}/r3a.patch
test -s {WORK}/r3a.patch
"""

manifest = {
    "run_name": "story-data-validator",
    "workdir": WORK,
    "max_parallel": 1,
    "worktrees": True,
    "repo": REPO,
    "tasks": [
        {
            "key": "r3a-skeleton",
            "task_type": "code-feature",
            "engine": "codex",
            "engine_args": ["-c", "model_reasoning_effort=high"],
            "max_attempts": 2,
            "timeout_s": 2400,
            "check_timeout_s": 900,
            "ownership": [
                "storygame/story_source/**",
                "tests/story_source/helpers.py",
                "tests/story_source/test_*.py",
            ],
            "spec": SPEC,
            "check": CHECK,
            "expect_files": [],
            "verified": "Package skeleton exists, reader reports duplicate keys and syntax errors, registry discovers l1_/l2_ modules, fixture tests skip instead of erroring on unbuilt names, ruff clean, only owned files changed.",
        }
    ],
}

if __name__ == "__main__":
    out = Path(__file__).with_name("validator-round3a-manifest.json")
    out.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    print(out)
