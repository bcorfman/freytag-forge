#!/usr/bin/env bash
set -u
git add -A -- . >/dev/null 2>&1
bad=$(git diff --cached --name-only | grep -Ev '^(storygame/runtime/candidate_matcher\.py|storygame/runtime/cloudflare\.py|tests/test_negation_scope\.py|tests/fixtures/raw_language_corpus\.json|tests/test_raw_language_corpus\.py)$')
[ -n "$bad" ] && { echo "UNOWNED FILE CHANGED:"; echo "$bad"; exit 1; }
for f in storygame/runtime/candidate_matcher.py tests/test_negation_scope.py tests/fixtures/raw_language_corpus.json; do git diff --cached --name-only | grep -qx "$f" || { echo "missing change in $f"; exit 1; }; done
git diff --cached -- storygame tests | grep -E '^-\s*assert' && { echo "an existing assertion was removed"; exit 1; }
PY=/home/bcorfman/dev/freytag-forge/.venv/bin
PYTHONPATH=$PWD TMPDIR=/tmp $PY/python -m pytest -q --no-cov -p no:cacheprovider tests 2>&1 | tail -15; [ ${PIPESTATUS[0]} -eq 0 ] || { echo "pytest failed"; exit 1; }
F="storygame/runtime/candidate_matcher.py storygame/runtime/cloudflare.py tests/test_negation_scope.py tests/test_raw_language_corpus.py"
$PY/ruff check $F && $PY/ruff format --check $F || { echo ruff; exit 1; }
python3 - <<'PY'
import json
d={e["id"]:e for e in json.load(open("tests/fixtures/raw_language_corpus.json"))}
for i in ("1a-restraint","2a-restraint","2c-restraint"):
    e=d[i]
    assert e["observed"]==e["intended"] and not e["note"].startswith("GAP"), f"{i} still a gap: {e}"
e=d["2c-near-miss-2"]
assert e["kind"]!="near_miss" and e["intended"]==e["observed"]=="k_sl_2c_b_r2", f"2c-near-miss-2 not relabelled: {e}"
for i in ("2a-near-miss-1","2c-pronoun"):
    assert d[i]["intended"]!=d[i]["observed"], f"{i} must stay an honest gap"
PY
[ $? -eq 0 ] || { echo "corpus expectations failed"; exit 1; }
mkdir -p /home/bcorfman/dev/ringer-work/stage5-notes
git diff --cached > /home/bcorfman/dev/ringer-work/stage5-notes/negation-scope.patch
test -s /home/bcorfman/dev/ringer-work/stage5-notes/negation-scope.patch || { echo "empty patch"; exit 1; }
