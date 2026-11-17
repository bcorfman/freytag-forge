# ruff: noqa: E501  (spec strings are prose briefs for a worker)
"""Build the Ringer manifest for round 4b: parity, save identity, override ratio, examples and lookup (4 tasks)."""

from __future__ import annotations

import json
from pathlib import Path

REPO = "/home/bcorfman/dev/freytag-forge"
WORK = "/home/bcorfman/dev/ringer-work/story-data-round4b"

PREAMBLE = f"""You are a Python engineer. Your current working directory IS a git worktree of {REPO} (detached at HEAD). Edit files here directly. NEVER git commit, never touch {REPO} itself, never run `uv`, never call a billed model or the network. FIRST run: [ -e .venv ] || ln -s {REPO}/.venv .venv ; run tests as `PYTHONPATH=$PWD:$PWD/packages/worldkeeper/src TMPDIR=/tmp .venv/bin/python -m pytest -q -p no:cacheprovider -n 0 <files>` (never pass --cov); ruff as `.venv/bin/python -m ruff check <files>` and `.venv/bin/python -m ruff format <files>` (line length 120, double quotes, Python 3.12, PyYAML and pydantic only, no new dependencies).

BACKGROUND. The game's story data is moving from nine legacy files per story to a declarative source tree that `storygame.story_source.compile_source_tree` compiles to the same `StoryPackage` (storygame/story_package/models.py). The format is fixed by the contract .plans/story-data-schema-contract.md (read the sections named below; never edit it). The package `storygame/story_source/` already holds the reader, validator and the pass 1 compiler. Never edit any file there other than the ones you own, and never edit storygame/story_package/*. The package `__init__.py` already resolves your public name lazily from your module, so you must NOT edit `__init__.py`. Section 10.1 of the contract fixes your public API names. The fixtures live in tests/fixtures/story_source/ and the fixture tests in tests/story_source/ (read the named tests and tests/story_source/ambiguities_*.md notes first). Do NOT edit any existing test file; add only the new test file you own. Each module has a docstring, no function is longer than about 60 lines, and no code mentions a story by name (the engine is story-agnostic). If a fixture test and the contract disagree, the fixture test wins; if a gate test cannot pass because the contract or fixture is wrong, do NOT weaken it: say so in NOTES_<key>.txt in the worktree root (never committed) and leave it failing.
"""

TASKS = {
    "r4b-parity": dict(
        owned=["storygame/story_source/parity.py", "tests/story_source/test_parity_core.py"],
        gate=["test_f23_parity_classes.py", "test_f24_review_digest.py", "test_parity_core.py"],
        need="check_parity",
        spec="""YOUR JOB: build `check_parity(legacy, compiled, *, reviews=None)` in `storygame/story_source/parity.py`, exactly per contract section 9 (canonical form, scope, keying by id, the eight difference classes with their proofs, the review-entry digest rule: first 12 hex of sha256 of the canonical JSON value, an entry matches only when path, class and both digests match, output objects and the summary) and section 10.1. It takes two `StoryPackage`s and an optional parsed review mapping (schema 1: `scene`, `differences[]` with path, class, legacy, compiled, reason). It returns a report with `differences` (list of the section 9 JSON objects) and `summary` (`records`, `differences`, `auto`, `reviewed`, `unreviewed`, `pass`); `pass` is False when any difference is unreviewed or the `knowledge_indexes` differ. Provide also `load_review_file(path)` for the YAML review format. Compare by canonical `model_dump(mode="json", by_alias=True)`. The gate tests are test_f23_parity_classes.py and test_f24_review_digest.py; they must pass unskipped. Add tests/story_source/test_parity_core.py with at least: identical packages give zero differences and pass; one seeded difference per class that is not covered by F23 (if any); a stale digest is unreviewed.""",
    ),
    "r4b-identity-ratio": dict(
        owned=[
            "storygame/story_source/identity.py",
            "storygame/story_source/ratio.py",
            "tests/story_source/test_identity_ratio_core.py",
        ],
        gate=["test_f25_save_identity.py", "test_f21_override_ratio.py", "test_identity_ratio_core.py"],
        need="check_save_identity|override_ratio",
        spec="""YOUR JOB: two small modules. (1) `storygame/story_source/identity.py`: `check_save_identity(package, manifest, *, retired_ids=None)` per section 10.1 and F25 (the frozen-id manifest shape is whatever test_f25_save_identity.py and the contract's section on frozen ids/`retired_ids` use; read sections 4.1, 4.2 and 7 for what is frozen). It emits one `UserWarning` (via `warnings.warn`) per frozen id missing from the package and not retired, silent otherwise, never raises. (2) `storygame/story_source/ratio.py`: `override_ratio(root)` and `pass2_gate(root)` per contract section 6.4 and 10.1 (one row per claim field with `added`, `dropped`, `expanded`, `ratio`, `status` of `ok` or `over`; `pass2_gate` is False when any row is `over`; the one-third rule). Reuse the existing expander in `storygame/story_source/c_lexicon.py` read-only (import it; do not edit it); if it lacks a function you need, implement the small piece inside ratio.py. Gate tests: test_f25_save_identity.py and test_f21_override_ratio.py must pass unskipped. Add tests/story_source/test_identity_ratio_core.py with at least one extra case per function (for example nothing missing is silent; a field with no lexicon has ratio 0 and status ok).""",
    ),
    "r4b-examples": dict(
        owned=["storygame/story_source/examples.py", "tests/story_source/test_examples_core.py"],
        gate=["test_f27_examples.py", "test_examples_core.py"],
        need="check_examples",
        spec="""YOUR JOB: build `check_examples(root, examples_path)` in `storygame/story_source/examples.py` per contract section 10.1 and fixture F27 (read test_f27_examples.py and the F27 note). The examples file (location `tests/fixtures/story_examples/<story>/<scene>.yaml`, keys `schema`, `scene`, `claims`, `shared`; each claim has `accept` and `reject` lists of player lines) is outside the source tree. The checker compiles the source tree, finds the claim's matcher (`action_evidence` groups, `aliases`, `leak_terms`, `must_convey` as the engine uses them) and runs the REAL engine matcher on each line (find it by reading how the engine checks `action_evidence`: grep storygame/ for `action_evidence`; import and call the existing function, never re-implement the matching). It returns a list of failures, empty when every line behaves. A failure is a dict or small dataclass with `claim_id`, `kind` (`accept` or `reject`), `line`, `group` (index of the matcher group that failed) and `missing` (the smallest single word to add so the accept line would pass). A `shared` section applies its lines to every claim named by it (follow the contract's examples wording). Gate test: test_f27_examples.py must pass unskipped. Add tests/story_source/test_examples_core.py with one extra case: a reject line that wrongly matches is reported as kind `reject`.""",
    ),
    "r4b-lookup": dict(
        owned=["storygame/story_source/lookup.py", "tests/story_source/test_lookup_core.py"],
        gate=["test_f28_lookup.py", "test_lookup_core.py"],
        need="story_text",
        spec="""YOUR JOB: build `story_text(address, *, package=None, source=False) -> str` and `story_value(address, *, package=None) -> object` in `storygame/story_source/lookup.py`, exactly per contract sections 8.1 and 8.2 (the address grammar, every kind and its resolvable fields, `[index]` including `[-1]`, `{parts}` pasted in for the compiled text, `source=True` returning the authored template, `part:` returning the part alone, `KeyError` naming the address for an unknown address and for an unset field, never `None`). Package-level kinds resolve against any `StoryPackage` including a legacy one; `reveal`, `variant`, `part` and `outcome` need a compiled source tree: find how the compiler keeps the authored template and parts (read storygame/story_source/compiler.py and the c_*.py files; if the compiled package does not retain them, the lookup may read the source tree through `read_source_tree` when the package carries or is given a source root; keep the design simple and document it in the module docstring). Without `package`, load the default story package once through the normal loader, cached (see storygame/story_package/loader.py for the public loader function and its default story id). No network, no model call. Gate test: test_f28_lookup.py must pass unskipped. Add tests/story_source/test_lookup_core.py with: an unknown kind raises KeyError; an unset field raises KeyError; `[-1]` returns the last list item; one address of the legacy default package resolves.""",
    ),
}


def check(key: str, spec: dict) -> str:
    owned = spec["owned"]
    keep = " ".join(f"-e '^{p}$'" for p in owned)
    gate = " ".join(f"tests/story_source/{n}" for n in spec["gate"])
    return f"""set -eo pipefail
[ -e .venv ] || ln -s {REPO}/.venv .venv
export PYTHONPATH=$PWD:$PWD/packages/worldkeeper/src TMPDIR=/tmp
out=$(mktemp)
rc=0
.venv/bin/python -m pytest -q -p no:cacheprovider -n 0 -rs {gate} > "$out" 2>&1 || rc=$?
tail -40 "$out"
[ "$rc" -eq 0 ] || exit "$rc"
if grep -E "SKIPPED.*({spec["need"]})" "$out"; then echo "a gate test still skips on the new API"; exit 1; fi
rc=0
.venv/bin/python -m pytest -q -p no:cacheprovider -n 0 tests/story_source > "$out" 2>&1 || rc=$?
tail -15 "$out"
[ "$rc" -eq 0 ] || exit "$rc"
.venv/bin/python -m ruff check storygame/story_source tests/story_source
.venv/bin/python -m ruff format --check storygame/story_source tests/story_source
git add -A -- storygame tests
bad=$(git diff --cached --name-only | grep -v {keep} || true)
[ -z "$bad" ] || {{ echo "files outside ownership staged: $bad"; exit 1; }}
git diff --cached > {WORK}/{key}.patch
test -s {WORK}/{key}.patch
"""


manifest = {
    "run_name": "story-data-round4b",
    "workdir": WORK,
    "max_parallel": 4,
    "worktrees": True,
    "repo": REPO,
    "tasks": [
        {
            "key": key,
            "task_type": "code-feature",
            "engine": "codex",
            "engine_args": ["-c", "model_reasoning_effort=high"],
            "max_attempts": 2,
            "timeout_s": 3000,
            "check_timeout_s": 1200,
            "ownership": spec["owned"],
            "spec": PREAMBLE + "\n" + spec["spec"].replace("<key>", key),
            "check": check(key, spec),
            "expect_files": [],
            "verified": f"gate tests {', '.join(spec['gate'])} pass unskipped; whole tests/story_source passes; ruff clean; only owned files changed.",
        }
        for key, spec in TASKS.items()
    ],
}

if __name__ == "__main__":
    out = Path(__file__).with_name("round4b-manifest.json")
    out.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    print(out)
