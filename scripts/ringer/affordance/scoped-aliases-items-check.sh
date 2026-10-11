#!/bin/bash
# Ringer check: runs in the task worktree (cwd).
set -u
OUT=/home/bcorfman/dev/ringer-work/scoped-aliases-items
mkdir -p "$OUT"
[ -f tests/test_scoped_aliases.py ] || { echo "FAIL: tests/test_scoped_aliases.py missing"; exit 1; }
git add -A -- . ':!notes.md'
bad=$(git diff --cached --name-only | grep -v -x -e storygame/story_package/models.py -e storygame/story_package/loader.py -e storygame/runtime/item_facts.py -e docs/markdown-story-authoring.md -e docs/world-model-grounding.md -e tests/test_markdown_story_package.py -e tests/test_bench_item_facts.py -e tests/test_scoped_aliases.py || true)
if [ -n "$bad" ]; then echo "FAIL: files changed outside the owned list:"; echo "$bad"; exit 1; fi
git diff --cached > "$OUT/change.patch"
git diff --cached -U0 -- storygame/runtime/narration_safety.py | grep -q . && { echo "FAIL: narration_safety.py must not change"; exit 1; }
TMPDIR=/tmp uv run python - <<'P' || exit 1
from pathlib import Path
from storygame.story_package.loader import load_story_package
I = load_story_package(Path("data/stories/continuity-initiative"))
assert all("scoped" not in k for k in I.knowledge_indexes.entity_alias_to_entities), "scoped alias leaked into the guard index"
g = next(g for g in I.world.groups if g.scoped_aliases)
assert set(g.scoped_aliases) >= {"prisoners", "captives"}, g.scoped_aliases
for form in g.scoped_aliases:
    assert form.casefold() not in I.knowledge_indexes.entity_alias_to_entities or g.id not in I.knowledge_indexes.entity_alias_to_entities[form.casefold()], f"group scoped alias {form} is guarded"
print("shipped story ok")
P
uv run ruff check . && uv run ruff format --check . || exit 1
TMPDIR=/tmp uv run pytest -q 2>&1 | tail -25
exit ${PIPESTATUS[0]}
