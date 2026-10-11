#!/bin/bash
# Ringer check: runs in the task worktree (cwd).
set -u
OUT=/home/bcorfman/dev/ringer-work/narration-corpus
mkdir -p "$OUT"
for f in tests/test_narration_corpus.py tests/fixtures/narration_corpus_verdicts.json scripts/regenerate_narration_corpus_verdicts.py scripts/extract_narration_corpus.py; do
  [ -f "$f" ] || { echo "FAIL: missing $f"; exit 1; }
done
git add -A -- . ':!notes.md'
bad=$(git diff --cached --name-only | grep -v -x -e tests/test_narration_corpus.py -e tests/fixtures/narration_corpus_verdicts.json -e scripts/regenerate_narration_corpus_verdicts.py -e scripts/extract_narration_corpus.py -e docs/testing-runbook.md || true)
if [ -n "$bad" ]; then echo "FAIL: files changed outside the owned list:"; echo "$bad"; exit 1; fi
git diff --cached --quiet -- tests/fixtures/narration_corpus.json || { echo "FAIL: the corpus fixture was edited"; exit 1; }
git diff --cached > "$OUT/change.patch"
TMPDIR=/tmp uv run pytest -q tests/test_narration_corpus.py 2>&1 | tail -15 || exit 1
# mutation check: a new broad guard must make the corpus test fail
cp data/stories/continuity-initiative/world.yaml /tmp/world.yaml.bak
python3 - <<'P'
import re
p = "data/stories/continuity-initiative/world.yaml"
s = open(p).read()
assert "\nitems:\n" in s
s = s.replace("\nitems:\n", "\nitems:\n- id: corpus_mutation_probe\n  name: Kristin\n  aliases: [the corridor, the terminal, the files]\n", 1)
open(p, "w").write(s)
P
if TMPDIR=/tmp uv run pytest -q tests/test_narration_corpus.py >/dev/null 2>&1; then
  cp /tmp/world.yaml.bak data/stories/continuity-initiative/world.yaml
  echo "FAIL: the corpus test did not catch a broad new entity guard"; exit 1
fi
cp /tmp/world.yaml.bak data/stories/continuity-initiative/world.yaml
git diff --quiet -- data/stories/continuity-initiative/world.yaml || { echo "FAIL: world.yaml not restored"; exit 1; }
echo "mutation caught"
uv run ruff check . && uv run ruff format --check . || exit 1
TMPDIR=/tmp uv run pytest -q 2>&1 | tail -25
exit ${PIPESTATUS[0]}
