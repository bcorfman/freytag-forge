# ruff: noqa: E501  (spec strings are prose briefs for a worker)
"""Round 8b: the four remaining story CLI commands (set, rename, impact, new), one module and one test file each."""

from __future__ import annotations

import json
from pathlib import Path

from build_round8a_manifest import HEADER, REPO

WORK = "/home/bcorfman/dev/ringer-work/story-cli-8b"

COMMON = """

CONTEXT. `storygame/story_cli.py` is the `story` command line for the story source tree (data/stories/continuity-initiative/source: story.yaml, catalog.yaml, scenes/<scene>.yaml, scenes/<scene>.match.yaml). The contract is .plans/story-data-schema-contract.md: read section 8 (addresses and the CLI table in 8.3), and the record schemas in section 4 that your command touches. Commands live one per module in `storygame/story_cmds/cmd_<name>.py`; `storygame/story_cmds/__init__.py` discovers them. READ `storygame/story_cmds/cmd_fmt.py` first: it is the pattern (a module defines `add_parser(commands, add_global_options)` and `run(args, root: Path) -> int`; `args.json` is the --json flag, `root` is the source root). Your command is currently a stub in story_cli.py that exits 2 "not built yet"; creating your module replaces the stub automatically, so DO NOT edit story_cli.py or any shared module. Round-trip YAML editing goes through `storygame/story_source/yamlio.py` (`load_document`, `dump_document`, `dumps_document`: comments and key order survive; one canonical style). Read-only helpers you may use without editing them: `storygame.story_source.lookup` (`story_text`, `story_value`), `storygame.story_source.compiler.compile_source_tree(root)`, the layer 1 and 2 checks via `storygame.story_source.check_source_tree(root)` (returns a list of Diagnostic; empty means clean), `storygame.story_source.diagnostics` (`Diagnostic`, `SourceError`), the save-identity manifest tests/fixtures/save_identity/continuity-initiative.yaml (frozen ids). Exit codes: 0 success, 1 refused or checks failed, 2 usage error or unknown address.

EDIT SAFETY (for every command that writes). Work on the owning file's text in memory; write it; run `check_source_tree(root)` and `compile_source_tree(root)`; if either reports a problem, restore the original file bytes exactly, print the diagnostics to stderr and exit 1. A write must never leave a broken tree, and a failed command must leave every file byte-identical to before. Print the unified diff of each changed file on success (with --json: {"changed": [relative paths], "diff": "..."}).

TESTING. Test files use a copy of the real source tree: `shutil.copytree` of data/stories/continuity-initiative/source into tmp_path (path from Path(__file__).resolve().parents[2]); never write into the real data tree. `monkeypatch.chdir(copied_root)` so the CLI finds the source root, then call `storygame.story_cli.main([...])` with capsys, as tests/story_source/test_cli_core.py does. Every writing test also asserts `story fmt --check` still exits 0 afterwards (the writer keeps the canonical style) and that a failed edit leaves files byte-identical. Keep tests fast (the whole tree check is a few seconds; share a tree copy per module with a module-scoped fixture only if tests are read-only, otherwise copy per test).

RULES. Own only the two files listed for your task (your cmd module and your test file); edit no other file, including tests/shard_durations.json, pyproject and story data. Never weaken another test. Keep ruff check and ruff format --check clean on your files."""

TASKS = {
    "set": (
        "story-set",
        """TASK: `story set <address> <yaml>`, `story set <address> --add <value>`, `story set <address> --drop <value>` in storygame/story_cmds/cmd_set.py. Contract 8.3: "Round-trip edit keeping comments and order. Refuses generated values (lock entries, entry facts, generated sections) and frozen-id fields. Compiles the affected scene and runs layers 1 and 2; on failure restores the file and prints the diagnostics. Prints the file diff." Address grammar is 8.1. Resolve the address to (owning source file, YAML path) for these kinds: scene, fact, delivery, claim, beat, exit, bridge, outline, ending, entity, reveal, variant, part, outcome; match-list fields (`aliases`, `action_evidence`, `must_convey`, `leak_terms`, `earn_when` on a claim) live in the scene's .match.yaml, so find where the schema keeps each field before writing the resolver. `<yaml>` replaces the field's value (parse it with yaml.safe_load; a plain sentence is a string); `--add v` appends to a list field (an index form like `action_evidence[1]` addresses one group of a list of groups, as in the 3B example in 4.9); `--drop v` removes the first equal element; an unknown address or a missing field exits 2 naming the address; adding an element already present or dropping an absent one exits 1 with a clear message. Refuse (exit 1, message names the reason) any field that holds generated values or a frozen id: `id`, `claim_id`, `realization_id`, `anchor`, lock-file entries, `entry` facts and generated sections. Tests: a scene `situation` set; a claim `text` set; `--add` to `action_evidence[0]` and `--drop` of the same value restoring the original bytes; a comment on a neighbouring line survives; refusal of `claim:<id>.claim_id`; an edit that breaks a check (for example a `turns` value that violates a layer 1 rule, or a dangling reference) restores bytes and exits 1; unknown address exits 2.""",
        ["storygame/story_cmds/cmd_set.py", "tests/story_source/test_cmd_set.py"],
    ),
    "rename": (
        "story-rename",
        """TASK: `story rename <kind>:<old> <new> [--retire "<reason>"]` in storygame/story_cmds/cmd_rename.py. Contract 8.3: "Free id: rewrites all references. Frozen id: refuses unless --retire "<reason>", which also adds the old id to retired_ids. Lists tests and non-source readers that mention the old id; never edits tests or frozen evidence." Frozen ids are the ids in tests/fixtures/save_identity/continuity-initiative.yaml (claims and facts; read the file's shape) plus pacing event ids and storylet/claim ids the contract marks frozen (grep the contract for "frozen"). Rewrite every reference in every *.yaml under the source root: mapping keys equal to the old id, scalar values equal to the old id (including list items such as `order` entries), and ids inside flow lists; never touch free text that merely contains the id as a substring. Ids can collide across kinds (contract 8.1 says four outcome ids equal fact ids): compute the set of scalars/keys equal to the old id; if the same string is also used as an id of a different kind, refuse with exit 1 and list the other kind, instead of guessing. Refuse if the new id already exists, or is not a valid id (lowercase letters, digits and underscore for ids, as the neighbouring ids are written; `1A.3` style for outline beats). With --retire on a frozen id, also add `kind: {old_id: reason}` to story.yaml `retired_ids` (preserve the existing map; the key is the kind name used in `<kind>:`). After writing run the edit safety flow (check and compile; restore every file on failure). Finally print the tests and non-source readers that mention the old id (a text search of tests/ plus scripts/, docs/ and storygame/, excluding the source tree and the fixtures under tests/fixtures/save_identity), without editing them; with --json include them as lists. Tests: rename a free claim-free id (pick a real free fact or beat id from the copied tree) and check every reference moved and `fmt --check` is clean; a frozen claim id refused without --retire (files unchanged) and accepted with --retire (retired_ids updated, references moved); a cross-kind collision refused; a new id that already exists refused; the listing of mentioning tests.""",
        ["storygame/story_cmds/cmd_rename.py", "tests/story_source/test_cmd_rename.py"],
    ),
    "impact": (
        "story-impact",
        """TASK: `story impact <address>` in storygame/story_cmds/cmd_impact.py. Contract 8.3: "The existing impact report, addressed the same way." The existing report is `storygame.story_package.impact_report.render_impact_report(root, subject, *, tests_dir=None) -> str` (see tests/test_impact_report.py and scripts/impact_report.py; it reads a package root and a subject such as a fact id, claim id or record id). Parse the address with the grammar in contract 8.1 (`kind:id[.field...]`); the subject is the id part; unknown address exits 2 with `unknown address: <address>` on stderr (use `story_value` from storygame.story_source.lookup on the compiled package to validate the address first). Work out what package root the report needs for a source tree (the compiled route of the loader needs ownership.yaml beside the source/ folder; for a bare source root you may compile with compile_source_tree and pass what the report needs; read impact_report.py to see whether it takes a root or a package, and extend ONLY your own module with an adapter, never edit impact_report.py). Print the report text; with --json print {"address": ..., "subject": ..., "report": "<text>"}. Tests: the impact of a real fact id and of a claim id from the copied real tree equals what `render_impact_report` prints for the same subject on the same story (if the report differs only by source-file locations, assert the sections and ids that must match); an unknown address exits 2; --json shape; it writes nothing (hash all files before and after).""",
        ["storygame/story_cmds/cmd_impact.py", "tests/story_source/test_cmd_impact.py"],
    ),
    "new": (
        "story-new",
        """TASK: `story new <kind> ...` in storygame/story_cmds/cmd_new.py. Contract 8.3: "Writes the record with every id it needs (claim_id, realization_id, anchor) so the compiler never generates one." Support three kinds: `story new fact <scene> <fact_id> --purpose "<text>"` (a fact record in that scene's `facts`, section 4.5), `story new beat <scene> <event_id> --say "<text>"` (a pacing event in `beats`, section 4.7, with one unguarded default say line), and `story new claim <scene> <reveal> <variant_key> <claim_id> --says "<text>"` (a claim on an existing reveal variant, section 4.8, with `claim_id`, `realization_id` and `anchor` all written explicitly so no id is ever generated; if the variant already has a claim, refuse). Read the sections to get the exact required keys and where in the file the record goes (append at the end of the right group, keeping the file's other content, comments and order). Validate before writing: the scene exists, the id is not already used anywhere in the tree and is a valid id in the neighbouring style, required flags are present (missing flag exits 2). A new claim also needs its match entry in scenes/<scene>.match.yaml if the schema requires one (section 4.9: check whether an empty entry is allowed or a match coverage check demands one, and write what makes the tree pass). Then run the edit safety flow (check and compile; restore every file on failure). Tests: one new fact, one new beat, one new claim on a real reveal variant that has none (pick one from the copied tree whose variant is realization-only if available; otherwise create the reveal-less case with the fixture tests/fixtures/story_source/mini_ok copied through tests/story_source/helpers.py `copy_fixture`), each leaving `check_source_tree` clean and `fmt --check` clean; a duplicate id refused with files unchanged; unknown scene exits 2; missing required flag exits 2.""",
        ["storygame/story_cmds/cmd_new.py", "tests/story_source/test_cmd_new.py"],
    ),
}


def check(owned: list[str]) -> str:
    py = " ".join(owned)
    return f"""set -eo pipefail
[ -e .venv ] || ln -s {REPO}/.venv .venv
export PYTHONPATH=$PWD:$PWD/packages/worldkeeper/src TMPDIR=/tmp
test -f {owned[0]} && test -f {owned[1]}
.venv/bin/python -m pytest -q -p no:cacheprovider -n 4 tests/story_source 2>&1 | tail -5
.venv/bin/python -m storygame.story_cli fmt --check
.venv/bin/python -m ruff check {py}
.venv/bin/python -m ruff format --check {py}
git add -A -- storygame tests
bad=$(git diff --cached --name-only | grep -v -x {" ".join("-e " + p for p in owned)} || true)
[ -z "$bad" ] || {{ echo "files outside ownership staged: $bad"; exit 1; }}
git diff --cached --binary > {WORK}/{Path(owned[0]).stem}.patch
test -s {WORK}/{Path(owned[0]).stem}.patch
"""


def task(name: str, key: str, text: str, owned: list[str]) -> dict[str, object]:
    return {
        "key": key,
        "task_type": "code-feature",
        "engine": "codex",
        "engine_args": ["-c", "model_reasoning_effort=medium"],
        "max_attempts": 2,
        "timeout_s": 1800,
        "check_timeout_s": 600,
        "ownership": owned,
        "spec": HEADER + COMMON + "\n\n" + text,
        "check": check(owned),
        "expect_files": [],
        "verified": f"`story {name}` is built with its tests; the tree stays clean under check_source_tree and fmt --check.",
    }


manifest = {
    "run_name": "story-cli-8b",
    "workdir": WORK,
    "max_parallel": 4,
    "worktrees": True,
    "repo": REPO,
    "tasks": [task(name, key, text, owned) for name, (key, text, owned) in TASKS.items()],
}

if __name__ == "__main__":
    Path(WORK).mkdir(parents=True, exist_ok=True)
    out = Path(__file__).with_name("manifest_8b.json")
    out.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    print(out)
