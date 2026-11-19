# ruff: noqa: E501  (spec strings are prose briefs for a worker)
"""Build the Ringer manifest for round 6g: repair the 8 failing ported tests in tests/test_markdown_story_package.py."""

from __future__ import annotations

import json
from pathlib import Path

REPO = "/home/bcorfman/dev/freytag-forge"
WORK = "/home/bcorfman/dev/ringer-work/story-data-round6g"
OWNED = ["tests/test_markdown_story_package.py"]
FAILING = [
    "test_group_member_package_declares_group_and_places_member",
    "test_loader_rejects_ambiguous_knowledge_effect_and_unreachable_prerequisite",
    "test_loader_rejects_invalid_canonical_event_and_scene_entry_sources",
    "test_loader_rejects_duplicate_fact_delivery",
    "test_loader_rejects_invalid_transition_graph[loader_rejects_ambiguous_transition_priority]",
    "test_loader_rejects_delivery_for_world_only_fact",
    "test_loader_rejects_bridge_text_keys_that_do_not_match_transition_ids",
]

SPEC = (
    "You are a Python test engineer. Your current working directory IS a git worktree of "
    + REPO
    + " (detached at HEAD). Edit files here directly. NEVER git commit, never touch "
    + REPO
    + " itself, never run `uv`, never call a billed model or the network. FIRST run: [ -e .venv ] || ln -s "
    + REPO
    + """/.venv .venv ; run tests as `PYTHONPATH=$PWD:$PWD/packages/worldkeeper/src TMPDIR=/tmp .venv/bin/python -m pytest -q -p no:cacheprovider -n 0 <files>` (never pass --cov); ruff as `.venv/bin/python -m ruff check <files>` and `.venv/bin/python -m ruff format <files>` (line length 120, double quotes, Python 3.12).

YOU OWN ONLY tests/test_markdown_story_package.py. Edit no other file; storygame/, data/ and docs/ are read-only to you.

BACKGROUND. The default story (data/stories/continuity-initiative/) moved from nine legacy files (plot.md, world.yaml, storylets.md, ...) to a source tree under source/ (catalog.yaml, scenes/<id>.yaml, scenes/<id>.match.yaml, ...) compiled by `storygame.story_source.compile_source_tree`. The format is fixed by .plans/story-data-schema-contract.md (read sections 2, 4, 10 and the diagnostics table). Helpers: tests/story_source/helpers.py (`compiled_story_copy`, `patch_source`, `load_compiled_copy`; patch addresses like `reveals[sl_1a_a].variants.r1.commits`). `git show 929e8c66^:tests/test_markdown_story_package.py` and `git show a5b348ce^:tests/test_markdown_story_package.py` give the original legacy versions of these tests (they mutated the legacy files) so you can see what mistake each test guards. The legacy checks live in storygame/story_package/loader.py. Loading a source-tree story raises `SourceError` (storygame.story_source.diagnostics), whose message starts with a diagnostic code such as `L1.unknown_key` or `L2.delivery_unseen`; read storygame/story_source/l1_*.py, l2_*.py to learn the real codes and messages.

THE 7 FAILING TESTS (node names in tests/test_markdown_story_package.py): """
    + "; ".join(FAILING)
    + """.

DECISIONS ALREADY MADE (do not reopen them):
1. `test_group_member_package_declares_group_and_places_member` is a port error: the original added the group `prisoners` with an ordinary `aliases: [prisoners]`, but the port wrote `scoped_aliases: [prisoners]`, which collides with the group's own name and is correctly rejected by the new `L2.scoped_alias_collision`. Port it faithfully using `aliases`.
2. Five tests guard mistakes the source format CANNOT write because the field is derived or keyed by id: duplicate fact delivery, bridge text keys not matching transition ids, ambiguous same-scene transition priority, invalid canonical-event / scene-entry sources, and the first half of the world-only-delivery test. Scouts tried at least two ways to write each one and got layer 1 (`L1.*`) rejections. Do NOT retire them. Rewrite each so it attempts the forbidden field (for example adding a second `delivery`, a `bridge_text` key, a `priority`, an explicit `source` etc. by patching the source tree) and asserts the `SourceError` carries the right `L1.*` code (use `pytest.raises(SourceError, match=...)` matching the code, and a short phrase of the message). Find the exact way the field is rejected by actually running the mutation and reading the diagnostic, then assert exactly that. Keep each test's docstring or name meaning intact so a reader sees which legacy mistake it guards.
3. `test_loader_rejects_delivery_for_world_only_fact`: its second half (a fact with a `delivery` that no claim can convey to the player) now has the check `L2.delivery_unseen` in storygame/story_source/l2_story.py; assert that code on a faithful mutation.
4. `test_loader_rejects_ambiguous_knowledge_effect_and_unreachable_prerequisite` is a port error: its faithful source mutation is rejected for a different reason. Port it so each half mutates the source tree the way the legacy test mutated the legacy files, and asserts the diagnostic that the source route really gives for that mistake (run it and read it). If a half genuinely cannot be written in the source format, convert it to a test that attempts it and asserts the L1 rejection, as in decision 2, and say so in NOTES_r6g.txt (worktree root, never committed).

RULES. Never weaken an assertion into `pytest.raises(Exception)` or a bare `SourceError` without a code/message match. Never delete a test. Never add `pytest.skip` or xfail. Leave every currently passing test in the file untouched. All edits stay inside tests/test_markdown_story_package.py.
"""
)

CHECK = f"""set -eo pipefail
[ -e .venv ] || ln -s {REPO}/.venv .venv
export PYTHONPATH=$PWD:$PWD/packages/worldkeeper/src TMPDIR=/tmp
out=$(mktemp)
rc=0
.venv/bin/python -m pytest -q -p no:cacheprovider -n 0 -rs tests/test_markdown_story_package.py > "$out" 2>&1 || rc=$?
tail -30 "$out"
[ "$rc" -eq 0 ] || exit "$rc"
if grep -E "SKIPPED" "$out"; then echo "a test skips"; exit 1; fi
if grep -nE "pytest\\.(skip|xfail)|raises\\(Exception" tests/test_markdown_story_package.py; then echo "forbidden skip/xfail/raises(Exception)"; exit 1; fi
before=$(git show HEAD:tests/test_markdown_story_package.py | grep -cE "^def test_")
after=$(grep -cE "^def test_" tests/test_markdown_story_package.py)
[ "$after" -ge "$before" ] || {{ echo "tests deleted: $before -> $after"; exit 1; }}
.venv/bin/python -m ruff check tests/test_markdown_story_package.py
.venv/bin/python -m ruff format --check tests/test_markdown_story_package.py
git add -A -- storygame tests data docs
bad=$(git diff --cached --name-only | grep -v -e '^tests/test_markdown_story_package.py$' || true)
[ -z "$bad" ] || {{ echo "files outside ownership staged: $bad"; exit 1; }}
git diff --cached > {WORK}/r6g-markdown-tests.patch
test -s {WORK}/r6g-markdown-tests.patch
[ ! -e NOTES_r6g.txt ] || cp NOTES_r6g.txt {WORK}/NOTES_r6g.txt
"""


def build() -> dict:
    return {
        "run_name": "story-data-round6-checks",
        "workdir": WORK,
        "max_parallel": 1,
        "worktrees": True,
        "repo": REPO,
        "tasks": [
            {
                "key": "r6g-markdown-tests",
                "task_type": "code-fix",
                "engine": "codex",
                "engine_args": ["-c", "model_reasoning_effort=high"],
                "max_attempts": 2,
                "timeout_s": 3600,
                "check_timeout_s": 600,
                "ownership": OWNED,
                "spec": SPEC,
                "check": CHECK,
                "expect_files": [],
                "verified": "all tests in tests/test_markdown_story_package.py pass, none deleted or skipped; only that file changed; ruff clean.",
            }
        ],
    }


if __name__ == "__main__":
    out = Path(__file__).with_name("round6g-manifest.json")
    out.write_text(json.dumps(build(), indent=2) + "\n", encoding="utf-8")
    print(out)
