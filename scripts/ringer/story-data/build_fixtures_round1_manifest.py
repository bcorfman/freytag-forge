# ruff: noqa: E501  (spec strings are prose briefs for a worker)
"""Build the Ringer manifest for fixtures round 1 (schema contract section 10, fixture F01 and helpers)."""

from __future__ import annotations

import json
from pathlib import Path

REPO = "/home/bcorfman/dev/freytag-forge"
WORK = "/home/bcorfman/dev/ringer-work/story-data-fixtures"
OWNED = [
    "tests/fixtures/story_source/README.md",
    "tests/fixtures/story_source/mini_ok/**",
    "tests/story_source/__init__.py",
    "tests/story_source/helpers.py",
    "tests/story_source/test_f01_mini_ok.py",
]
CHECK_SCRIPT = f"{REPO}/scripts/ringer/story-data/check_fixture_f01.py"

SPEC = f"""You are a test-fixture author. Your current working directory IS a git worktree of {REPO} (detached at HEAD). Edit files here directly. NEVER git commit, never touch {REPO} itself, never run `uv`, never call a billed model or the network. You own ONLY these paths: tests/fixtures/story_source/README.md, everything under tests/fixtures/story_source/mini_ok/, tests/story_source/__init__.py, tests/story_source/helpers.py, tests/story_source/test_f01_mini_ok.py. Do not edit anything else, in particular not the contract, not data/, not storygame/. FIRST run: [ -e .venv ] || ln -s {REPO}/.venv .venv ; run tests as `PYTHONPATH=$PWD:$PWD/packages/worldkeeper/src TMPDIR=/tmp .venv/bin/python -m pytest -q -p no:cacheprovider -n 0 tests/story_source` (never pass --cov); ruff as `.venv/bin/python -m ruff check <files>` and `.venv/bin/python -m ruff format <files>` (line length 120, double quotes, Python 3.12, PyYAML only, no new dependencies).

BACKGROUND. The story package of this game is being migrated from nine legacy files in data/stories/continuity-initiative/ to a new declarative source format (YAML scene files plus a match file per scene) that a compiler will turn into the existing `StoryPackage`. The format is fixed by the contract at .plans/story-data-schema-contract.md (read sections 2 to 4 and 10 fully; it is the source MATERIAL, and the instructions are in this spec). No compiler or validator exists yet. Your job is the first test fixture, F01 `mini_ok`, plus a patch helper and a first test file, so that later fixtures (F02 to F31, each F01 plus one change) and the compiler tests can be written against them.

DELIVERABLES.
1. tests/fixtures/story_source/mini_ok/ : a small, VALID source tree in the new format, cut from real continuity-initiative records: story.yaml, catalog.yaml, scenes/1A.yaml, scenes/1A.match.yaml, scenes/2C.yaml, scenes/2C.match.yaml. Story scenes are [1A, 2C] (the 1A exit targets 2C; this exit target is the only change a two-scene story needs). Contents: in 1A, the reveal `find_card` exactly as in the worked example of contract section 4.8 (both variants quiet and witnessed, the `parts` pattern with {{find_lead}}, claims k_sl_1a_b_r0 and k_sl_1a_b_r0w), the pacing beats about the patrol, the exit, the facts those need, the card delivery fact `continuity_initiative_known` with its match-file `deliveries` entry, placements, and an `outline` with beat 1A.1. In 2C: the live 2C incident (outcomes, recovery reveal, missed-window beat, observed_by list) with `text_when` on one claim, `commits_common`, and the scene `ending` (copy the live 3C ending text; F01's last scene is 2C). At least two `entry_claims` across the two scenes, one with a non-public audience (`{{kind: characters, character_ids: [...]}}`). catalog.yaml needs the entities these records reference, `protected_knowledge`, and at least one `disclosure_guards` entry. Keep it small: only what F01's row in contract section 10 names. Every id must be a real id from the live package where one exists. Take every passage (entry text, says, text, intent, fallback text, notes, bridge text, ending) byte for byte from the live files in data/stories/continuity-initiative/ (plot.md, knowledge.yaml, storylet-routes.yaml, handoffs.yaml, pacing.yaml, world.yaml, incidents.yaml, connections.yaml, storylets.md). Where a two-scene story forces a text that does not exist live (for example a changed exit bridge sentence), write it, and list that passage verbatim, one per line, in tests/fixtures/story_source/mini_ok/NEW_TEXT.txt. Every other passage must exist in the live files; an external check verifies this by substring after whitespace is collapsed, and fails on anything it cannot find. Do not invent keys: every key must be in the contract's tables for its file; top-level keys must be in the contract section 2 order; every file starts with `schema: 1`; no duplicate keys anywhere.
2. tests/fixtures/story_source/README.md : (a) a one-line-per-fixture index of F01 now and a placeholder table of F02 to F31 copied from contract section 10; (b) a section "Compiler and validator API these fixtures are written against" that fixes these names and nothing more: package `storygame.story_source`; `check_source_tree(root: Path) -> list[Diagnostic]` (layers 1 and 2; an empty list means valid); `Diagnostic` is a frozen dataclass with `name` (for example "L2.fact_one_owner"), `file` (path relative to root), `address` (contract section 8.1 address or empty), `field` and `message`; `compile_source_tree(root: Path) -> StoryPackage` (raises `SourceError` carrying the diagnostics when the tree is invalid); `story_text(address, *, package=None, source=False)` and `story_value(address, *, package=None)` as in contract section 8.2.
3. tests/story_source/helpers.py : `copy_fixture(name: str, tmp_path: Path) -> Path` copies tests/fixtures/story_source/<name> into tmp_path and returns the copy; `patch_source(root: Path, file: str, address: str, value: object = DELETE)` edits one YAML file in the copy by an ID-based path, for example `patch_source(root, "scenes/1A.yaml", "reveals[find_card].variants.quiet.says", "new text")`; a `[id]` segment selects the list element whose `id` (or `claim_id`) equals id, `.key` selects a mapping key, `[0]` selects by index; `DELETE` removes the key or element; `ADD` semantics: setting a key that does not exist creates it. Unknown path raises KeyError naming the path. Loading must reject duplicate keys (use a SafeLoader subclass) and writing must keep key order (yaml.safe_dump with sort_keys=False, width large, allow_unicode=True). Also `load_tree(root) -> dict[str, object]` returning every YAML file keyed by relative path.
4. tests/story_source/test_f01_mini_ok.py : tests that pass today without any compiler: the fixture copies and loads; every file's first key is `schema`; the patch helper round-trips (patch then read back; DELETE; list selection by id; unknown path raises KeyError; duplicate keys rejected on load); the F01 claims in each scene equal the keys of that scene's match file claims. And one test that is skipped until the compiler exists: `pytest.importorskip("storygame.story_source")` inside the test body, then `assert check_source_tree(root) == []` and `compile_source_tree(root)` returns a package whose scene ids are ["1A", "2C"].

HARD RULES. Passages are copied, never paraphrased or "improved". Do not run any model or the game. If a contract point is ambiguous, pick the reading that matches the live package and note it in a `# NOTE:` comment line at the end of README.md under a heading "Ambiguities found" (one line each) so the orchestrator can fix the contract. The independent check is: `python {CHECK_SCRIPT} <worktree>` (it prints every failure; run it yourself repeatedly), then your tests, then ruff.
"""

CHECK = f"""set -eo pipefail
[ -e .venv ] || ln -s {REPO}/.venv .venv
export PYTHONPATH=$PWD:$PWD/packages/worldkeeper/src TMPDIR=/tmp
.venv/bin/python {CHECK_SCRIPT} "$PWD"
out=$(mktemp)
rc=0
.venv/bin/python -m pytest -q -p no:cacheprovider -n 0 tests/story_source > "$out" 2>&1 || rc=$?
tail -40 "$out"
[ "$rc" -eq 0 ] || exit "$rc"
.venv/bin/python -m ruff check tests/story_source
.venv/bin/python -m ruff format --check tests/story_source
git add -A -- tests/fixtures/story_source tests/story_source
bad=$(git diff --cached --name-only | grep -v -e '^tests/fixtures/story_source/' -e '^tests/story_source/' || true)
[ -z "$bad" ] || {{ echo "files outside ownership staged: $bad"; exit 1; }}
git diff --cached > {WORK}/f01.patch
test -s {WORK}/f01.patch
"""

manifest = {
    "run_name": "story-data-fixtures",
    "workdir": WORK,
    "max_parallel": 1,
    "worktrees": True,
    "repo": REPO,
    "tasks": [
        {
            "key": "f01-mini-ok",
            "task_type": "code-feature",
            "engine": "codex",
            "engine_args": ["-c", "model_reasoning_effort=high"],
            "max_attempts": 2,
            "timeout_s": 2400,
            "check_timeout_s": 600,
            "ownership": OWNED,
            "spec": SPEC,
            "check": CHECK,
            "expect_files": [],
            "verified": "F01 passes the independent shape and text-fidelity check, the helper tests pass, ruff is clean, and only owned files changed.",
        }
    ],
}

if __name__ == "__main__":
    out = Path(__file__).with_name("fixtures-round1-manifest.json")
    out.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    print(out)
