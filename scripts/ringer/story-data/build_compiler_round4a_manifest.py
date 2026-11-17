# ruff: noqa: E501  (spec strings are prose briefs for a worker)
"""Build the Ringer manifest for compiler round 4a: the pass 1 compiler core (one task)."""

from __future__ import annotations

import json
from pathlib import Path

REPO = "/home/bcorfman/dev/freytag-forge"
WORK = "/home/bcorfman/dev/ringer-work/story-data-compiler"
KEY = "r4a-compiler-core"

OWNED = [
    "storygame/story_source/__init__.py",
    "storygame/story_source/compiler.py",
    "storygame/story_source/digest.py",
    "tests/story_source/test_compiler_core.py",
]
OWNED_PREFIX = ["storygame/story_source/c_"]

SPEC = f"""You are a Python engineer. Your current working directory IS a git worktree of {REPO} (detached at HEAD). Edit files here directly. NEVER git commit, never touch {REPO} itself, never run `uv`, never call a billed model or the network. FIRST run: [ -e .venv ] || ln -s {REPO}/.venv .venv ; run tests as `PYTHONPATH=$PWD:$PWD/packages/worldkeeper/src TMPDIR=/tmp .venv/bin/python -m pytest -q -p no:cacheprovider -n 0 <files>` (never pass --cov); ruff as `.venv/bin/python -m ruff check <files>` and `.venv/bin/python -m ruff format <files>` (line length 120, double quotes, Python 3.12, PyYAML and pydantic only, no new dependencies).

BACKGROUND. The game's story data is moving from nine legacy files per story (data/stories/continuity-initiative/: plot.md, storylets.md, knowledge.yaml, world.yaml, pacing.yaml, incidents.yaml, handoffs.yaml, connections.yaml, storylet-routes.yaml) to a declarative source tree that a compiler turns into the SAME `StoryPackage` (storygame/story_package/models.py). The source format is fixed by the contract at .plans/story-data-schema-contract.md: read it fully (do not edit it), especially sections 3, 4 (all per-record schemas), 5 (derivation rules), 9 (canonical JSON) and 10.1 (API names). The package `storygame/story_source/` already holds the reader (`read_source_tree`), `Diagnostic`/`SourceError`, the layer 1 and 2 validator (`check_source_tree`). Do not edit those files except `__init__.py` (to export your names). The existing loader `storygame/story_package/loader.py` builds the package from the legacy files and then runs the inherited checks (`_validate_disclosure_guards`, `_validate_knowledge`, `_validate_entry_variants`, `_validate`, `_validate_authored_handoffs`, `_validate_deliveries`, `_validate_incidents`, `_validate_connections`, `_validate_transition_trigger_sources`, `_validate_resolution_entry_guarantees`, `_validate_required_reveal_prerequisites`, `_validate_ending`; read `_load_story_package_uncached` from line 1517). Never edit storygame/story_package/*; import its private functions as they are.

YOUR JOB: build the pass 1 compiler core. `compile_source_tree(root: Path) -> StoryPackage` reads the tree, refuses to compile when `check_source_tree` returns any diagnostic (raise `SourceError` carrying them), derives every record by the contract's derivation rules (section 5; matcher lists stay written out, there is no lexicon in this pass: a scene with `lexicon: false`, or no lexicon, ignores any `lexicon.yaml`), builds the `StoryPackage`, then runs the SAME inherited loader checks listed above on it. A failed inherited check raises `SourceError` with one diagnostic: name `L2.cycles` when the failure is a cycle in transitions or prerequisites, else name `LOADER` carrying the loader message (section 10.1). Also provide `COMPILER_VERSION` (a string constant) and `source_digest(root) -> str` per section 10.1. Export `compile_source_tree`, `source_digest`, `COMPILER_VERSION` from `storygame/story_source/__init__.py`. Compilation must be deterministic: no sets or dict-order accidents in output order, no timestamps, no absolute paths.

STRUCTURE. Put the orchestration in `storygame/story_source/compiler.py` and split the work into helper modules named `storygame/story_source/c_*.py` (for example c_passages.py for part and `use` resolution, `say`/`text_when`/`additions` rules, c_scene.py, c_knowledge.py, c_world.py), `digest.py` for the digest. No function longer than about 60 lines, a docstring on each module, no story names in code (the compiler is story-agnostic; fixtures use continuity-initiative text but code must not mention it).

THE GATE (the fixture tests, read each and its tests/story_source/ambiguities_*.md note first). These must pass without skips on compile: tests/story_source/test_f01_mini_ok.py (the compile test), test_f09_cycles.py, test_f10_outcome_not_committed.py, test_f11_observes_missing.py, test_f12_passage_rules.py, test_f13_leak_null_vs_empty.py, test_f16_claim_order.py, test_f30_claimless_variant.py, test_f31_deterministic.py. Tests that need other names (`check_parity`, `check_save_identity`, `override_ratio`, `check_examples`, `story_cli`, lookup, needs typing F29, review isolation F26, manifest F14/F15) belong to later rounds and may keep skipping; do not build them. Add your own `tests/story_source/test_compiler_core.py`: at least one test that every inherited loader check really runs on a compiled F01 (for example by compiling a copy with `patch_source` that breaks one inherited rule and expecting `SourceError` named `LOADER`), a determinism test, and a test that compiled F01 has the same record ids for scenes, claims, deliveries, incidents and facts that the source declares. Do NOT edit any existing test file.

HARD LIMITS. Your files only: storygame/story_source/__init__.py, compiler.py, digest.py, c_*.py and tests/story_source/test_compiler_core.py. If the contract is ambiguous or contradicts a fixture, the fixture test wins; put a `# NOTE:` comment at the top of test_compiler_core.py naming each ambiguity and what you assumed. If a gate test cannot pass because the contract or fixture is wrong, do NOT weaken it: say so in a file NOTES_r4a.txt in the worktree root (never committed) naming the test and why, and leave that test failing.
"""


def check() -> str:
    keep = " ".join(f"-e '^{p}$'" for p in OWNED) + " -e '^storygame/story_source/c_[a-z_]*\\.py$'"
    gate = " ".join(
        f"tests/story_source/{name}"
        for name in [
            "test_f01_mini_ok.py",
            "test_f09_cycles.py",
            "test_f10_outcome_not_committed.py",
            "test_f11_observes_missing.py",
            "test_f12_passage_rules.py",
            "test_f13_leak_null_vs_empty.py",
            "test_f16_claim_order.py",
            "test_f30_claimless_variant.py",
            "test_f31_deterministic.py",
            "test_compiler_core.py",
        ]
    )
    return f"""set -eo pipefail
[ -e .venv ] || ln -s {REPO}/.venv .venv
export PYTHONPATH=$PWD:$PWD/packages/worldkeeper/src TMPDIR=/tmp
out=$(mktemp)
rc=0
.venv/bin/python -m pytest -q -p no:cacheprovider -n 0 -rs {gate} > "$out" 2>&1 || rc=$?
tail -40 "$out"
[ "$rc" -eq 0 ] || exit "$rc"
if grep -E "SKIPPED.*compile_source_tree|SKIPPED.*source_digest" "$out"; then echo "a gate test still skips on the compiler"; exit 1; fi
rc=0
.venv/bin/python -m pytest -q -p no:cacheprovider -n 0 tests/story_source > "$out" 2>&1 || rc=$?
tail -15 "$out"
[ "$rc" -eq 0 ] || exit "$rc"
.venv/bin/python -m ruff check storygame/story_source tests/story_source
.venv/bin/python -m ruff format --check storygame/story_source tests/story_source
git add -A -- storygame tests
bad=$(git diff --cached --name-only | grep -v {keep} || true)
[ -z "$bad" ] || {{ echo "files outside ownership staged: $bad"; exit 1; }}
git diff --cached > {WORK}/{KEY}.patch
test -s {WORK}/{KEY}.patch
"""


manifest = {
    "run_name": "story-data-compiler",
    "workdir": WORK,
    "max_parallel": 1,
    "worktrees": True,
    "repo": REPO,
    "tasks": [
        {
            "key": KEY,
            "task_type": "code-feature",
            "engine": "codex",
            "engine_args": ["-c", "model_reasoning_effort=high"],
            "max_attempts": 2,
            "timeout_s": 3600,
            "check_timeout_s": 1200,
            "ownership": [*OWNED, "storygame/story_source/c_*.py"],
            "spec": SPEC,
            "check": check(),
            "expect_files": [],
            "verified": "compile_source_tree builds a StoryPackage from F01 that passes every inherited loader check; gate fixture tests pass unskipped; ruff clean; only owned files changed.",
        }
    ],
}

if __name__ == "__main__":
    out = Path(__file__).with_name("compiler-round4a-manifest.json")
    out.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    print(out)
