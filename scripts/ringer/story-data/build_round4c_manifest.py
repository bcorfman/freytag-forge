# ruff: noqa: E501  (spec strings are prose briefs for a worker)
"""Build the Ringer manifest for round 4c: the pass 2 lock and the story CLI (2 tasks)."""

from __future__ import annotations

import json
from pathlib import Path

REPO = "/home/bcorfman/dev/freytag-forge"
WORK = "/home/bcorfman/dev/ringer-work/story-data-round4c"

PREAMBLE = f"""You are a Python engineer. Your current working directory IS a git worktree of {REPO} (detached at HEAD). Edit files here directly. NEVER git commit, never touch {REPO} itself, never run `uv`, never call a billed model or the network. FIRST run: [ -e .venv ] || ln -s {REPO}/.venv .venv ; run tests as `PYTHONPATH=$PWD:$PWD/packages/worldkeeper/src TMPDIR=/tmp .venv/bin/python -m pytest -q -p no:cacheprovider -n 0 <files>` (never pass --cov); ruff as `.venv/bin/python -m ruff check <files>` and `.venv/bin/python -m ruff format <files>` (line length 120, double quotes, Python 3.12, PyYAML and pydantic only, no new dependencies).

BACKGROUND. The game's story data is moving from nine legacy files per story to a declarative source tree that `storygame.story_source.compile_source_tree` compiles to the same `StoryPackage` (storygame/story_package/models.py). The format is fixed by the contract .plans/story-data-schema-contract.md (read the sections named below; never edit it). The package `storygame/story_source/` already holds the reader, validator and the pass 1 compiler. Never edit any file there other than the ones you own, and never edit storygame/story_package/*. Never edit `__init__.py`. Sections 6.3, 6.4, 7, 8.3, 9 and 10.1 of the contract fix the behaviour and API names. Another worker builds the sibling piece in parallel (the lock module and the CLI); code against the names given in YOUR JOB and import across the boundary lazily (inside the function), so your module imports and your tests run when the sibling file does not exist yet. The fixtures live in tests/fixtures/story_source/ and the fixture tests in tests/story_source/ (read the named tests and tests/story_source/ambiguities_*.md notes first). Do NOT edit any existing test file (including tests/shard_durations.json and docs/); add only the new test file you own. Each module has a docstring, no function is longer than about 60 lines, and no code mentions a story by name (the engine is story-agnostic). If a fixture test and the contract disagree, the fixture test wins; if a gate test cannot pass because the contract or fixture is wrong, do NOT weaken it: say so in NOTES_<key>.txt in the worktree root (never committed) and leave it failing.
"""

TASKS = {
    "r4c-lock": dict(
        owned=[
            "storygame/story_source/lock.py",
            "storygame/story_source/l2_lock.py",
            "tests/story_source/test_lock_core.py",
        ],
        gate=["test_lock_core.py"],
        ignore=[],
        need="NEVER_MATCHES_ANYTHING",
        spec="""YOUR JOB: build the pass 2 lock layer per contract sections 6.3 (lock file, equivalence per field), 6.5 and 7 (`L2.lock_stale`, `L2.drop_unused`). The compiler already reads lock entries and expands lexicon values in `storygame/story_source/c_lexicon.py` (read it; you may import its functions read-only, never edit it). Build in `storygame/story_source/lock.py`: `equivalent(field, expanded, locked) -> bool` (the table in 6.3: `action_evidence` same closure as the engine matcher computes, found by reading how `_matches_one_group` in storygame/ builds it and importing that helper if it is importable, else the casefolded word-normalized set; `must_convey` same group order and byte-equal group[0] and equal casefolded rest; `leak_terms` equal casefolded sets and the None/()/list kind unchanged; `aliases` equal in order), `lock_scene(root, scene, *, adopt=False) -> LockReport` (writes `scenes/<scene>.match.lock.yaml`; with `adopt=True` it creates the first lock from the pass 1 lists and refuses, writing nothing, unless every expansion is equivalent to the list it replaces, returning each mismatch as the `add:`/`drop:` needed; without adopt it rewrites only entries no longer equivalent, with the expansion itself) and `expand_scene(root, scene) -> None` (writes the lock's plain lists into the scene's match file in place of every derived value and sets `lexicon: false`; leaves `lexicon.yaml` and the lock file in place). `LockReport` is a small dataclass with `changed` (list of `(claim_id, field)`) and `mismatches` (list of strings). In `storygame/story_source/l2_lock.py` add the layer 2 check module discovered by the existing registry (read storygame/story_source/checks.py and l2_claims.py for the pattern) emitting `L2.lock_stale` naming the claim and field (file `scenes/<scene>.match.lock.yaml`, field the field key) for a derived value not equivalent to its lock entry or with no lock entry; a scene with `lexicon: false` is never checked and its lexicon.yaml is never opened; also `L2.drop_unused` for a `drop` entry that removes nothing. Gate: tests/story_source/test_f20_lexicon_stale.py must pass with its skip removed in YOUR copy only if it cannot otherwise run; since you must not edit existing tests, make it run by building the real check: the test currently calls `pytest.skip` unconditionally before its assertions, so verify the behaviour with your own tests in tests/story_source/test_lock_core.py (copy the F20 fixture construction with `copy_fixture` and the patch helpers in tests/story_source/helpers.py and assert exactly the F20 expectations: one `L2.lock_stale`, file, field `aliases`, message names `k_sl_1a_b_r0`, `compile_source_tree` raises SourceError). Also test: adopt refuses on a non-equivalent expansion and writes nothing; adopt on F19's tree changes no compiled package byte; `expand_scene` then compile without lexicon.yaml gives the same package; `equivalent` for each of the four fields with one true and one false case. test_f19_lexicon_roundtrip.py needs the CLI from the other worker and may keep skipping.""",
    ),
    "r4c-cli": dict(
        owned=["storygame/story_cli.py", "tests/story_source/test_cli_core.py"],
        gate=["test_cli_core.py"],
        ignore=["test_f19_lexicon_roundtrip.py", "test_f20_lexicon_stale.py"],
        need="story_cli",
        spec="""YOUR JOB: build the `story` CLI skeleton in `storygame/story_cli.py` per contract section 8.3 and 10.1: `main(argv: list[str] | None = None) -> int` (returns the exit code, never calls sys.exit itself; add `if __name__ == "__main__": raise SystemExit(main())`), argparse sub-commands, global `--story <id>` (default `continuity-initiative`) and `--json`. Source root resolution: the current directory when it holds `story.yaml`, else `data/stories/<story>/source`, else the pilot location `data/story-pilot/<story>/source` (section 2). Implement these commands fully: (1) `show <address>`: prints the record as authored using `storygame.story_source.story_text`/`story_value` (built; read storygame/story_source/lookup.py) plus the owning source file and the test files under tests/ that mention the id (a plain text search of tests/); exit 2 on an unknown address (a KeyError from the lookup); (2) `parity <scene>`: compiles the source root with `compile_source_tree`, loads the legacy package with the normal loader (read storygame/story_package/loader.py for the public function), runs `storygame.story_source.parity.check_parity` (built; read it) restricted to that scene as section 9 says if the function supports it, else on the whole packages and filtered to the scene, reads the reviews file `tests/fixtures/parity/<story>/<scene>.reviewed.yaml` when it exists (use `load_review_file` from parity.py), prints one JSON object per difference then the summary, exits 0 when `unreviewed` is 0 and the knowledge indexes are equal, 1 otherwise, 2 on a compile error (a SourceError; print its diagnostics); (3) `lock <scene> [--adopt]`, `lock --all`, and `expand <scene>`: thin wrappers that import `storygame.story_source.lock` lazily inside the command and call `lock_scene(root, scene, adopt=adopt)` and `expand_scene(root, scene)` (another worker builds that module in parallel with the exact names and signatures in this sentence: `lock_scene(root, scene, *, adopt=False) -> LockReport` with `.changed` (list of (claim_id, field)) and `.mismatches` (list of str); `expand_scene(root, scene) -> None`). If the module cannot be imported print `lock layer not built` and exit 2. `lock --all` runs lock_scene over every scene in story.yaml without writing anything when `--dry-run` is given, only reporting which scenes would change (implement dry-run as: copy the tree to a temp directory, run there, report `changed`). `lock` prints each `changed` entry and each mismatch (`add:`/`drop:`) and exits 0, or 1 when there are mismatches. Every other command in the section 8.3 table (`set`, `rename`, `impact`, `new`, `fmt`) is registered, prints `<name>: not built yet` and exits 2, so the help lists the full surface. Keep the file under about 400 lines and split command bodies into small functions; if it grows past that, put the command bodies in `storygame/story_cli_commands.py` instead (you own that file name too). Add tests/story_source/test_cli_core.py (it must pass when the lock module is absent): `main(["show", "claim:k_sl_1a_b_r0.text"])` against the F01 fixture (copy with `copy_fixture`, `monkeypatch.chdir`) exits 0 and prints the text; an unknown address exits 2; `parity` of F01 against itself is not possible without a legacy package, so test `parity` through a monkeypatched legacy loader returning the compiled package: exit 0 and summary pass true; a missing source root exits 2 with a message; `set` exits 2 'not built yet'. The F19 `story expand` test is verified by the orchestrator after both workers finish; do not try to make it pass here.""",
    ),
}


def check(key: str, spec: dict) -> str:
    owned = spec["owned"]
    keep = " ".join(f"-e '^{p}$'" for p in owned)
    gate = " ".join(f"tests/story_source/{n}" for n in spec["gate"])
    ignore = " ".join(f"--ignore=tests/story_source/{n}" for n in spec["ignore"])
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
.venv/bin/python -m pytest -q -p no:cacheprovider -n 0 tests/story_source {ignore} > "$out" 2>&1 || rc=$?
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
    "max_parallel": 2,
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
    out = Path(__file__).with_name("round4c-manifest.json")
    out.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    print(out)
