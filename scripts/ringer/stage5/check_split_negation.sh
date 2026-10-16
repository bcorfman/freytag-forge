#!/usr/bin/env bash
set -u
git add -A -- . >/dev/null 2>&1
bad=$(git diff --cached --name-only | grep -Ev '^(storygame/runtime/command_split\.py|tests/test_command_split_negation\.py)$')
[ -n "$bad" ] && { echo "UNOWNED FILE CHANGED:"; echo "$bad"; exit 1; }
for f in storygame/runtime/command_split.py tests/test_command_split_negation.py; do git diff --cached --name-only | grep -qx "$f" || { echo "missing change in $f"; exit 1; }; done
git diff --cached -- storygame tests | grep -E '^-\s*assert' && { echo "an existing assertion was removed"; exit 1; }
PY=/home/bcorfman/dev/freytag-forge/.venv/bin
PYTHONPATH=$PWD TMPDIR=/tmp $PY/python - <<'PYEOF' || { echo "split expectations failed"; exit 1; }
from storygame.runtime.command_split import split_command as s
whole = ["Open the drawer, but do not take anything yet.",
         "Search Brandon's hideout for leaked documents, but do not copy anything yet.",
         "Check the copied JANUS files, but do not send anything yet.",
         "Open the drawer, but don't take anything yet.",
         "Open the drawer and do not take anything."]
for t in whole:
    assert s(t) == [t], f"negated coordinated verb must not split: {t!r} -> {s(t)!r}"
assert len(s("Open the drawer and take the key.")) == 2, s("Open the drawer and take the key.")
assert len(s("Open the drawer, take the key, then search the room.")) == 3, s("Open the drawer, take the key, then search the room.")
PYEOF
PYTHONPATH=$PWD TMPDIR=/tmp $PY/python -m pytest -q --no-cov -p no:cacheprovider tests 2>&1 | tail -15; [ ${PIPESTATUS[0]} -eq 0 ] || { echo "pytest failed"; exit 1; }
F="storygame/runtime/command_split.py tests/test_command_split_negation.py"
$PY/ruff check $F && $PY/ruff format --check $F || { echo ruff; exit 1; }
test -s /home/bcorfman/dev/ringer-work/stage5-notes/corpus-engine-path.md || { echo "missing corpus-engine-path.md"; exit 1; }
git diff --cached > /home/bcorfman/dev/ringer-work/stage5-notes/split-negation.patch
test -s /home/bcorfman/dev/ringer-work/stage5-notes/split-negation.patch || { echo "empty patch"; exit 1; }
