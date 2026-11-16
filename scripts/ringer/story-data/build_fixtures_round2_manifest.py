# ruff: noqa: E501  (spec strings are prose briefs for a worker)
"""Build the Ringer manifest for fixtures round 2 (schema contract section 10, fixtures F02 to F31)."""

from __future__ import annotations

import json
from pathlib import Path

REPO = "/home/bcorfman/dev/freytag-forge"
WORK = "/home/bcorfman/dev/ringer-work/story-data-fixtures"
CHECK_SCRIPT = f"{REPO}/scripts/ringer/story-data/check_fixtures_round2.py"

# key, first, last, contract sections to read closely, extra guidance
BATCHES = [
    (
        "f02-f08-layer-1-2-mutations",
        2,
        8,
        "sections 4.5, 4.8, 4.9, 7 and 10",
        "Each fixture is F01 plus ONE mutation made by `patch_source` on a copy. The tests assert the diagnostic NAME from the contract table in section 7 (and the `file`/`address`/`field` where section 7, 8.1 or the F-row says them). F07 needs two mutations (a narrowed claim `leak_terms` and a variant `boundaries` key) and expects two `L2.override_add_only` diagnostics. F05: the message must name the declaration block and the scene file to move it to.",
    ),
    (
        "f09-f16-loader-and-order",
        9,
        16,
        "sections 4.8, 4.9, 4.11, 4.13, 5, 7 and 10",
        "F09 to F11 expect errors the existing loader already raises after compilation (see section 7 intro): assert that `compile_source_tree` raises, and do not guess the loader's exact message; assert only what the contract fixes. F12 to F13 and F16 assert compiled package values (first `say` wins; `AMBIGUOUS` from the engine's text_when evaluation; `None` versus `()` for `leak_terms`; claim order follows the match file). F14 adds a manifest file (see section 2 and 4.1/4.9 for its shape) from inside the test, since F01 has none. F15 compares against the legacy package only through `compile_source_tree` plus a note that the comparison needs the loader of `data/stories/continuity-initiative`; keep that part behind `pytest.importorskip`.",
    ),
    (
        "f17-f22-lexicon",
        17,
        22,
        "sections 6.1 to 6.5, 7 and 10",
        "These fixtures exercise pass 2. F01 has no lexicon, so build lexicon.yaml, the `lexicon: true` scene flag, the `$memory_card` reference, lock files and plural-twin entries from inside each test (write the files into the copy) using the shapes in section 6. Valid-lexicon files must be YAML that follows section 6.1 exactly. Assert diagnostic names and ratios exactly as the F-rows and section 6.4 say; F19 asserts package equality with F01 and the `story expand` round trip as written in section 8.3 (keep CLI parts behind `pytest.importorskip` and name the module you assume in the ambiguities file).",
    ),
    (
        "f23-f26-parity-and-save-identity",
        23,
        26,
        "sections 4.1, 4.8, 7, 9 and 10",
        "Section 9 fixes the parity classes, the review file and its digest rule, and the output. Build the legacy/compiled pairs, the review entries, the frozen-id manifest and the `retired_ids` list inside the tests from small dict or dataclass stand-ins when the real classes are not available; the assertions on the real checker stay behind `pytest.importorskip` and the names you assume go in the ambiguities file. F25: `UserWarning` naming the id, then silent after `retired_ids`. F26: choose a unique marker string for the `note` fields and assert it appears nowhere in the compiled package's dump (use `dataclasses`/pydantic dump as the package class allows) or the narrator inputs; the part that runs today asserts the marker appears in the source files and nowhere else in the copy.",
    ),
    (
        "f27-f31-lookup-needs-determinism",
        27,
        31,
        "sections 4.8, 4.13, 4.12, 8.1 to 8.3, 9 and 10",
        "F27: accept/reject example lines for `k_sl_1a_b_r0` live in a separate examples test file per scene (section 4.9 or 8, wherever the contract puts `examples`), one accept line must fail on purpose; the checker names the failing group and the smallest word to add. F28: one address of every kind from section 8.1, each resolving, parts pasted in, `source=True` returns the template, unknown address raises `KeyError`. F29: `exists`, `held`, `reach` and `not` needs on one exit; only `exists` and `held` reach `required_dependencies`. F30: a variant with no `claim_id` compiles to a realization with no claim. F31: compile twice in two subprocesses, identical canonical JSON; the digest covers schema version, compiler version and every source file (the run-today part checks the subprocess helper and that the copy hashes identically twice).",
    ),
]


def spec(key: str, first: int, last: int, sections: str, guidance: str) -> str:
    rng = f"F{first:02d} to F{last:02d}"
    return f"""You are a test-fixture author. Your current working directory IS a git worktree of {REPO} (detached at HEAD). Edit files here directly. NEVER git commit, never touch {REPO} itself, never run `uv`, never call a billed model or the network. You own ONLY: tests/story_source/test_f*.py files whose number is in {rng} (name them exactly as the check script requires, `test_fNN_<fixture name>.py`, names are in the table of contract section 10), tests/story_source/ambiguities_{key}.md, and new directories tests/fixtures/story_source/fNN_<fixture name>/ for fixtures in your range. Do not edit anything else: not tests/story_source/helpers.py, not tests/fixtures/story_source/README.md, not mini_ok, not the contract, not data/, not storygame/. If you need a helper, define it inside your own test file. FIRST run: [ -e .venv ] || ln -s {REPO}/.venv .venv ; run tests as `PYTHONPATH=$PWD:$PWD/packages/worldkeeper/src TMPDIR=/tmp .venv/bin/python -m pytest -q -p no:cacheprovider -n 0 tests/story_source` (never pass --cov); ruff as `.venv/bin/python -m ruff check <files>` and `.venv/bin/python -m ruff format <files>` (line length 120, double quotes, Python 3.12, PyYAML only, no new dependencies).

BACKGROUND. The story package of this game is being migrated to a declarative source format (YAML scene files plus a match file per scene) that a compiler will turn into the existing `StoryPackage`. The format is fixed by the contract at .plans/story-data-schema-contract.md; read {sections} fully and section 10's fixture table. The compiler and validator do not exist yet. Fixture F01 `mini_ok` (tests/fixtures/story_source/mini_ok/), the patch helper (tests/story_source/helpers.py: `copy_fixture`, `patch_source`, `DELETE`, `load_tree`) and the API names (tests/fixtures/story_source/README.md, last section) already exist; read tests/story_source/test_f01_mini_ok.py as the model of style. Your job: write the fixtures and tests for {rng}, each being F01 plus the ONE change its row in section 10 names, with the assertions the row's Expected column states, so the compiler can later be built against them.

HOW EACH FIXTURE IS BUILT. Prefer a test that copies mini_ok with `copy_fixture` and applies the change with `patch_source` (or writes an extra file into the copy). Add a directory under tests/fixtures/story_source/ only when a change cannot be expressed that way. Each test file `test_fNN_<name>.py` must have (a) at least one test that runs TODAY without the compiler and proves the fixture is built right: the mutated tree loads with `load_tree`, and it differs from mini_ok in exactly the intended place and nowhere else (compare the loaded trees); (b) tests whose body begins with `story_source = pytest.importorskip("storygame.story_source")` and then assert the expected diagnostic NAME (for example `"L2.fact_one_owner"`), plus `file`, `address` and `field` wherever the contract states them, using `story_source.check_source_tree(root)` / `story_source.compile_source_tree(root)` / `story_source.SourceError` exactly as the README fixes. Also assert that the unmutated copy of mini_ok yields no diagnostics, in the same skipped test, so a validator that flags everything fails. No unconditional skips, no xfail.

GUIDANCE FOR YOUR RANGE. {guidance}

HARD RULES. Assert only what the contract fixes. Where the contract does not determine an expected value (an address string, a message wording, an API name beyond the README), assert the part it does fix, and write one line per case in tests/story_source/ambiguities_{key}.md in the form `F<NN>: <what is unspecified>; assumed <what you assumed>` so the orchestrator can settle the contract. Never edit mini_ok to make a fixture easier. Every YAML you write must keep the contract's key order and `schema: 1` first. Do not run any model or the game. Run the independent check yourself repeatedly: `python {CHECK_SCRIPT} $PWD {first} {last}` (prints every failure), then the tests, then ruff.
"""


def check(key: str, first: int, last: int) -> str:
    return f"""set -eo pipefail
[ -e .venv ] || ln -s {REPO}/.venv .venv
export PYTHONPATH=$PWD:$PWD/packages/worldkeeper/src TMPDIR=/tmp
.venv/bin/python {CHECK_SCRIPT} "$PWD" {first} {last}
out=$(mktemp)
rc=0
.venv/bin/python -m pytest -q -p no:cacheprovider -n 0 tests/story_source > "$out" 2>&1 || rc=$?
tail -40 "$out"
[ "$rc" -eq 0 ] || exit "$rc"
.venv/bin/python -m ruff check tests/story_source
.venv/bin/python -m ruff format --check tests/story_source
test -s tests/story_source/ambiguities_{key}.md || {{ echo "ambiguities_{key}.md missing or empty (write 'none' if truly none)"; exit 1; }}
git add -A -- tests/fixtures/story_source tests/story_source
bad=$(git diff --cached --name-only | grep -v -E '^tests/story_source/(test_f({first}|{last}|[0-9]+)_.*\\.py|ambiguities_{key}\\.md)$|^tests/fixtures/story_source/f[0-9]+_' || true)
[ -z "$bad" ] || {{ echo "files outside ownership staged: $bad"; exit 1; }}
git diff --cached > {WORK}/{key}.patch
test -s {WORK}/{key}.patch
"""


tasks = []
for key, first, last, sections, guidance in BATCHES:
    owned = [
        *(f"tests/story_source/test_f{n:02d}_*.py" for n in range(first, last + 1)),
        f"tests/story_source/ambiguities_{key}.md",
        *(f"tests/fixtures/story_source/f{n:02d}_*/**" for n in range(first, last + 1)),
    ]
    tasks.append(
        {
            "key": key,
            "task_type": "code-feature",
            "engine": "codex",
            "engine_args": ["-c", "model_reasoning_effort=high"],
            "max_attempts": 2,
            "timeout_s": 3000,
            "check_timeout_s": 600,
            "ownership": owned,
            "spec": spec(key, first, last, sections, guidance),
            "check": check(key, first, last),
            "expect_files": [],
            "verified": f"Fixtures F{first:02d} to F{last:02d}: test files exist, cite the contract names, run today without the compiler, ruff is clean, only owned files changed.",
        }
    )

manifest = {
    "run_name": "story-data-fixtures",
    "workdir": WORK,
    "max_parallel": 3,
    "worktrees": True,
    "repo": REPO,
    "tasks": tasks,
}

if __name__ == "__main__":
    out = Path(__file__).with_name("fixtures-round2-manifest.json")
    out.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    print(out)
