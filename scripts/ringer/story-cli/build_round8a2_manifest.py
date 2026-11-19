# ruff: noqa: E501  (spec strings are prose briefs for a worker)
"""Round 8a-2: simplify yamlio to one canonical style and write the missing yamlio and fmt tests."""

from __future__ import annotations

import json
from pathlib import Path

from build_round8a_manifest import HEADER, REPO

WORK = "/home/bcorfman/dev/ringer-work/story-cli-8a2"
OWNED = [
    "storygame/story_source/yamlio.py",
    "storygame/story_cmds/cmd_fmt.py",
    "tests/story_source/test_yamlio.py",
    "tests/story_source/test_cmd_fmt.py",
]
SPEC = (
    HEADER
    + """

CONTEXT. Round 8a added `storygame/story_source/yamlio.py` (round-trip YAML for the story source tree), `storygame/story_cmds/cmd_fmt.py` (`story fmt [<scene>] [--check]`) and command-module dispatch in `storygame/story_cli.py`. They work, but (1) yamlio is over-built: `_configure_source_style` guesses an indent style per file and `_restore_flow_nulls` patches flow-map nulls with regexes, only to make the odd hand-made `mini_ok` test fixture round-trip byte for byte; (2) the two test files the first task required were NEVER WRITTEN. Writing them is part of this task: you MAY and MUST create tests/story_source/test_yamlio.py and tests/story_source/test_cmd_fmt.py.

Design decision: there is ONE canonical style, the one the committed tree already has: ruamel round-trip, width 10000, allow_unicode, preserve_quotes, DEFAULT indentation (block sequences are not indented under their key). `story fmt` rewrites any file into that style; a hand-made fixture in another style is simply reformatted, that is what fmt is for.

TASK.
1. Simplify `storygame/story_source/yamlio.py`: delete `_configure_source_style`, `_restore_flow_nulls`, the regexes and the `_yamlio_*` attributes; keep `make_yaml()`, `load_document(path)`, `dumps_document(document)`, `dump_document(document, path)` with the plain configuration above. Keep the public names and signatures. `cmd_fmt.py` keeps working unchanged apart from any fix you need.
2. Write tests/story_source/test_yamlio.py: (a) every `*.yaml` under data/stories/continuity-initiative/source loads and dumps back byte-identical (read the path from the repo root via Path(__file__).resolve().parents[2]); (b) a temp file with a full-line comment, a trailing comment and a specific key order keeps all three after one scalar value is changed and dumped; (c) a multi-line passage scalar (a block scalar `|` and a quoted scalar with a trailing blank line) has an identical value after load and dump (compare with yaml.safe_load of both texts).
3. Write tests/story_source/test_cmd_fmt.py. Use `compiled_story_copy(tmp_path)` or a plain `shutil.copytree` of data/stories/continuity-initiative/source into tmp_path (never write into the real data tree), `monkeypatch.chdir(root)` to the copied source root (the CLI finds the source root when the cwd holds story.yaml), and call `storygame.story_cli.main([...])` the way tests/story_source/test_cli_core.py does with capsys: (a) on the untouched copy `fmt --check` exits 0 and prints nothing to change; (b) after inserting a comment line and changing one sequence in scenes/1A.yaml to indented style, `fmt --check` exits 1 and names `scenes/1A.yaml`, writes nothing; (c) plain `fmt` then rewrites exactly that file, a following `fmt --check` exits 0, the inserted comment survives and `yaml.safe_load` values equal the pre-reformat values; (d) `fmt 1A` limits itself to the 1A files and `fmt NOPE` exits 2; (e) `--json` prints {"checked": N, "changed": [...]} with the right paths.
4. Keep everything ruff-clean and ruff-formatted.

RULES. Own only the four listed files; edit no other file. Never weaken another test.

DONE WHEN the four files are as described, the owned tests pass, the whole tests/story_source folder passes, ruff check and ruff format --check are clean on the owned files, and `.venv/bin/python -m storygame.story_cli fmt --check` from the worktree root exits 0."""
)


def check() -> str:
    py = " ".join(OWNED)
    return f"""set -eo pipefail
[ -e .venv ] || ln -s {REPO}/.venv .venv
export PYTHONPATH=$PWD:$PWD/packages/worldkeeper/src TMPDIR=/tmp
test -f tests/story_source/test_yamlio.py && test -f tests/story_source/test_cmd_fmt.py
! grep -q "_restore_flow_nulls\\|_configure_source_style" storygame/story_source/yamlio.py
.venv/bin/python -m pytest -q -p no:cacheprovider -n 0 tests/story_source 2>&1 | tail -5
.venv/bin/python -m storygame.story_cli fmt --check
.venv/bin/python -m ruff check {py}
.venv/bin/python -m ruff format --check {py}
git add -A -- storygame tests
bad=$(git diff --cached --name-only | grep -v -x {" ".join("-e " + p for p in OWNED)} || true)
[ -z "$bad" ] || {{ echo "files outside ownership staged: $bad"; exit 1; }}
git diff --cached --binary > {WORK}/round8a2.patch
test -s {WORK}/round8a2.patch
"""


manifest = {
    "run_name": "story-cli-8a2",
    "workdir": WORK,
    "max_parallel": 1,
    "worktrees": True,
    "repo": REPO,
    "tasks": [
        {
            "key": "yamlio-simplify-and-tests",
            "task_type": "code-feature",
            "engine": "codex",
            "engine_args": ["-c", "model_reasoning_effort=medium"],
            "max_attempts": 2,
            "timeout_s": 1500,
            "check_timeout_s": 600,
            "ownership": OWNED,
            "spec": SPEC,
            "check": check(),
            "expect_files": [],
            "verified": "yamlio is one plain canonical style, byte-exact on the committed tree, and yamlio and `story fmt` have their tests.",
        }
    ],
}

if __name__ == "__main__":
    Path(WORK).mkdir(parents=True, exist_ok=True)
    out = Path(__file__).with_name("manifest_8a2.json")
    out.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    print(out)
