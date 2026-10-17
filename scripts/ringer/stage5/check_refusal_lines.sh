#!/usr/bin/env bash
set -u
git add -A -- . >/dev/null 2>&1
OWN='^(storygame/runtime/validation\.py|storygame/web_demo\.py|storygame/runtime/engine\.py|tests/test_refusal_lines\.py|tests/test_engine_error_line\.py|tests/test_web_demo\.py|tests/test_attempt_bundle\.py)$'
bad=$(git diff --cached --name-only | grep -Ev "$OWN")
[ -n "$bad" ] && { echo "UNOWNED FILE CHANGED:"; echo "$bad"; exit 1; }
git diff --cached --name-only | grep -qx "tests/test_refusal_lines.py" || { echo "missing tests/test_refusal_lines.py"; exit 1; }
git diff --cached --name-only | grep -qx "storygame/web_demo.py" || { echo "missing change in storygame/web_demo.py"; exit 1; }
PY=/home/bcorfman/dev/freytag-forge/.venv/bin
PYTHONPATH=$PWD TMPDIR=/tmp $PY/python - <<'PYEOF' || { echo "message constants wrong"; exit 1; }
import storygame.runtime.validation as v
assert v.REJECTED_TURN_MESSAGE == "I don't understand. Can you try something else?", v.REJECTED_TURN_MESSAGE
assert v.ITEM_NOT_VISIBLE_MESSAGE == "I don't see the item you're referring to.", v.ITEM_NOT_VISIBLE_MESSAGE
assert v.NARRATION_RETRY_MESSAGE == "Nothing comes of that. Try something else.", v.NARRATION_RETRY_MESSAGE
f = v.rejection_message
assert f("narration_known_term_leak", "rebecca", "Ask Rebecca about the desk.") == v.ITEM_NOT_VISIBLE_MESSAGE
assert f("protected_narration_leak", "janus", "Look around.") == v.NARRATION_RETRY_MESSAGE
assert f("narration_known_term_leak", None, "Look around.") == v.NARRATION_RETRY_MESSAGE
assert f("ineligible_selection", None, "Look around.") == v.REJECTED_TURN_MESSAGE
assert f("narration_known_term_leak", "card", "Open the discard pile.") == v.NARRATION_RETRY_MESSAGE, "whole-word match only"
PYEOF
PYTHONPATH=$PWD TMPDIR=/tmp $PY/python -m pytest -q --no-cov -p no:cacheprovider tests 2>&1 | tail -15; [ ${PIPESTATUS[0]} -eq 0 ] || { echo "pytest failed"; exit 1; }
F=$(git diff --cached --name-only | grep '\.py$' | tr '\n' ' ')
$PY/ruff check $F && $PY/ruff format --check $F || { echo ruff; exit 1; }
git diff --cached > /home/bcorfman/dev/ringer-work/stage5-notes/refusal-lines.patch
test -s /home/bcorfman/dev/ringer-work/stage5-notes/refusal-lines.patch || { echo "empty patch"; exit 1; }
